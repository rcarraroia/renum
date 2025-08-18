"""
Multi-Agent Execution Service
Handles coordination and execution of multi-agent workflows
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
import structlog

from app.domain.execution import (
    MultiAgentExecution, ExecutionPlan, ExecutionStep,
    ExecutionStatus, StepStatus, ExecutionStrategy, FailureHandling
)
from app.repositories.execution_repository import ExecutionRepository
from app.agents.agent_registry import AgentRegistry, get_agent_registry
from app.services.user_credentials_service import UserCredentialsService

logger = structlog.get_logger(__name__)

class ExecutionService:
    """Service for coordinating multi-agent executions"""
    
    def __init__(
        self,
        execution_repository: Optional[ExecutionRepository] = None,
        agent_registry: Optional[AgentRegistry] = None,
        credentials_service: Optional[UserCredentialsService] = None
    ):
        self.execution_repo = execution_repository or ExecutionRepository()
        self.agent_registry = agent_registry or get_agent_registry()
        self.credentials_service = credentials_service or UserCredentialsService()
        
        # Execuções ativas (em produção seria Redis/cache distribuído)
        self._active_executions: Dict[UUID, MultiAgentExecution] = {}
        
        # Semáforo para controlar execuções paralelas
        self._execution_semaphore = asyncio.Semaphore(10)
    
    async def create_execution_plan(
        self,
        user_id: UUID,
        plan_data: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create execution plan from data"""
        try:
            # Extrair dados do plano
            plan_id = plan_data.get('plan_id', str(uuid4()))
            name = plan_data.get('name', 'Unnamed Plan')
            description = plan_data.get('description', '')
            
            # Converter steps
            steps = []
            for step_data in plan_data.get('steps', []):
                step = ExecutionStep(
                    step_id=step_data['step_id'],
                    agent_id=step_data['agent_id'],
                    capability_name=step_data['capability_name'],
                    input_data=step_data.get('input_data', {}),
                    depends_on=step_data.get('depends_on', []),
                    timeout_seconds=step_data.get('timeout_seconds', 300),
                    retry_count=step_data.get('retry_count', 0),
                    retry_delay_seconds=step_data.get('retry_delay_seconds', 5),
                    condition=step_data.get('condition'),
                    credential_id=UUID(step_data['credential_id']) if step_data.get('credential_id') else None,
                    metadata=step_data.get('metadata', {})
                )
                steps.append(step)
            
            # Validar agentes e capacidades
            await self._validate_plan_agents(steps)
            
            # Criar plano
            plan = ExecutionPlan(
                plan_id=plan_id,
                name=name,
                description=description,
                steps=steps,
                strategy=ExecutionStrategy(plan_data.get('strategy', 'sequential')),
                failure_handling=FailureHandling(plan_data.get('failure_handling', 'stop_on_failure')),
                max_parallel_steps=plan_data.get('max_parallel_steps', 5),
                timeout_minutes=plan_data.get('timeout_minutes', 60),
                metadata=plan_data.get('metadata', {})
            )
            
            return plan
            
        except Exception as e:
            raise ValueError(f"Falha ao criar plano de execução: {str(e)}")
    
    async def execute_plan(
        self,
        user_id: UUID,
        plan: ExecutionPlan,
        input_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MultiAgentExecution:
        """Execute multi-agent plan"""
        execution_id = uuid4()
        
        # Criar execução
        execution = MultiAgentExecution(
            execution_id=execution_id,
            user_id=user_id,
            plan=plan,
            input_data=input_data or {},
            context=context or {}
        )
        
        # Salvar execução inicial
        execution = await self.execution_repo.save_execution(execution)
        
        # Adicionar à lista de execuções ativas
        self._active_executions[execution_id] = execution
        
        # Executar em background
        asyncio.create_task(self._execute_plan_async(execution))
        
        return execution
    
    async def _execute_plan_async(self, execution: MultiAgentExecution):
        """Execute plan asynchronously"""
        async with self._execution_semaphore:
            try:
                # Iniciar execução
                execution.start()
                await self.execution_repo.save_execution(execution)
                
                logger.info(
                    "Iniciando execução multi-agente",
                    execution_id=str(execution.execution_id),
                    plan_id=execution.plan.plan_id,
                    strategy=execution.plan.strategy.value,
                    total_steps=len(execution.plan.steps)
                )
                
                # Executar baseado na estratégia
                if execution.plan.strategy == ExecutionStrategy.SEQUENTIAL:
                    await self._execute_sequential(execution)
                elif execution.plan.strategy == ExecutionStrategy.PARALLEL:
                    await self._execute_parallel(execution)
                elif execution.plan.strategy == ExecutionStrategy.PIPELINE:
                    await self._execute_pipeline(execution)
                elif execution.plan.strategy == ExecutionStrategy.CONDITIONAL:
                    await self._execute_conditional(execution)
                elif execution.plan.strategy == ExecutionStrategy.BATCH:
                    await self._execute_batch(execution)
                
                # Completar execução se não foi cancelada
                if not execution.is_cancelled():
                    execution.complete()
                
            except Exception as e:
                execution.fail(str(e))
                logger.error(
                    "Erro na execução multi-agente",
                    execution_id=str(execution.execution_id),
                    error=str(e)
                )
            finally:
                # Remover da lista de execuções ativas
                if execution.execution_id in self._active_executions:
                    del self._active_executions[execution.execution_id]
                
                # Salvar estado final
                await self.execution_repo.save_execution(execution)
    
    async def _execute_sequential(self, execution: MultiAgentExecution):
        """Execute steps sequentially"""
        execution.add_log("info", "Iniciando execução sequencial")
        
        for step in execution.plan.steps:
            if execution.is_cancelled():
                break
            
            # Aguardar se pausado
            while execution.is_paused():
                await asyncio.sleep(1)
            
            # Executar passo
            await self._execute_step(execution, step)
            
            # Verificar falha
            if step.status == StepStatus.FAILED:
                if execution.plan.failure_handling == FailureHandling.STOP_ON_FAILURE:
                    raise Exception(f"Passo '{step.step_id}' falhou: {step.error_message}")
                elif execution.plan.failure_handling == FailureHandling.RETRY_ON_FAILURE:
                    await self._retry_step(execution, step)
    
    async def _execute_parallel(self, execution: MultiAgentExecution):
        """Execute steps in parallel (respecting dependencies)"""
        execution.add_log("info", "Iniciando execução paralela")
        
        # Obter ordem de execução por níveis
        execution_levels = execution.plan.get_execution_order()
        
        for level_index, level_steps in enumerate(execution_levels):
            if execution.is_cancelled():
                break
            
            execution.add_log("info", f"Executando nível {level_index + 1}: {level_steps}")
            
            # Executar passos do nível em paralelo
            tasks = []
            for step_id in level_steps:
                step = execution.plan.get_step(step_id)
                if step:
                    task = asyncio.create_task(self._execute_step(execution, step))
                    tasks.append((step_id, task))
            
            # Aguardar conclusão de todos os passos do nível
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Processar resultados
            for (step_id, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    execution.add_log("error", f"Erro no passo '{step_id}': {str(result)}")
                    if execution.plan.failure_handling == FailureHandling.STOP_ON_FAILURE:
                        raise result
    
    async def _execute_pipeline(self, execution: MultiAgentExecution):
        """Execute steps as pipeline (output feeds into next)"""
        execution.add_log("info", "Iniciando execução em pipeline")
        
        context = execution.context.copy()
        context.update(execution.input_data)
        
        for step in execution.plan.steps:
            if execution.is_cancelled():
                break
            
            # Aguardar se pausado
            while execution.is_paused():
                await asyncio.sleep(1)
            
            # Usar output do passo anterior como input
            step_input = {**step.input_data, **context}
            
            # Executar passo
            await self._execute_step_with_input(execution, step, step_input)
            
            # Atualizar contexto com output
            if step.output_data:
                context.update(step.output_data)
            
            # Verificar falha
            if step.status == StepStatus.FAILED:
                if execution.plan.failure_handling == FailureHandling.STOP_ON_FAILURE:
                    raise Exception(f"Pipeline falhou no passo '{step.step_id}': {step.error_message}")
    
    async def _execute_conditional(self, execution: MultiAgentExecution):
        """Execute steps with conditional logic"""
        execution.add_log("info", "Iniciando execução condicional")
        
        context = execution.context.copy()
        context.update(execution.input_data)
        completed_steps = set()
        
        while len(completed_steps) < len(execution.plan.steps):
            if execution.is_cancelled():
                break
            
            executed_in_round = False
            
            for step in execution.plan.steps:
                if step.step_id in completed_steps:
                    continue
                
                # Verificar dependências
                if not step.can_execute(list(completed_steps)):
                    continue
                
                # Verificar condição
                if not step.evaluate_condition(context):
                    execution.add_log("info", f"Passo '{step.step_id}' pulado por condição")
                    step.skip_execution("Condição não atendida")
                    completed_steps.add(step.step_id)
                    executed_in_round = True
                    continue
                
                # Executar passo
                await self._execute_step_with_input(execution, step, context)
                completed_steps.add(step.step_id)
                executed_in_round = True
                
                # Atualizar contexto
                if step.output_data:
                    context.update(step.output_data)
                
                # Verificar falha
                if step.status == StepStatus.FAILED:
                    if execution.plan.failure_handling == FailureHandling.STOP_ON_FAILURE:
                        raise Exception(f"Passo '{step.step_id}' falhou: {step.error_message}")
            
            # Evitar loop infinito
            if not executed_in_round:
                break
    
    async def _execute_batch(self, execution: MultiAgentExecution):
        """Execute steps in batches"""
        execution.add_log("info", "Iniciando execução em lote")
        
        batch_size = execution.plan.max_parallel_steps
        steps = execution.plan.steps
        
        for i in range(0, len(steps), batch_size):
            if execution.is_cancelled():
                break
            
            batch = steps[i:i + batch_size]
            execution.add_log("info", f"Executando lote {i//batch_size + 1}: {[s.step_id for s in batch]}")
            
            # Executar lote em paralelo
            tasks = []
            for step in batch:
                task = asyncio.create_task(self._execute_step(execution, step))
                tasks.append((step.step_id, task))
            
            # Aguardar conclusão do lote
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Processar resultados
            for (step_id, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    execution.add_log("error", f"Erro no passo '{step_id}': {str(result)}")
                    if execution.plan.failure_handling == FailureHandling.STOP_ON_FAILURE:
                        raise result
    
    async def _execute_step(self, execution: MultiAgentExecution, step: ExecutionStep):
        """Execute individual step"""
        return await self._execute_step_with_input(execution, step, step.input_data)
    
    async def _execute_step_with_input(
        self,
        execution: MultiAgentExecution,
        step: ExecutionStep,
        input_data: Dict[str, Any]
    ):
        """Execute step with specific input data"""
        step.start_execution()
        execution.add_log("info", f"Iniciando passo '{step.step_id}'", step.step_id)
        
        try:
            # Obter agente
            agent = self.agent_registry.get_agent(step.agent_id)
            if not agent:
                raise Exception(f"Agente '{step.agent_id}' não encontrado")
            
            # Verificar capacidade
            if not agent.has_capability(step.capability_name):
                raise Exception(f"Agente '{step.agent_id}' não tem capacidade '{step.capability_name}'")
            
            # Executar com timeout
            result = await asyncio.wait_for(
                agent.execute_capability(
                    capability_name=step.capability_name,
                    input_data=input_data,
                    user_id=execution.user_id,
                    credential_id=step.credential_id
                ),
                timeout=step.timeout_seconds
            )
            
            if result.success:
                step.complete_execution(result.data)
                execution.add_step_result(step.step_id, result.to_dict())
                execution.add_log("info", f"Passo '{step.step_id}' completado", step.step_id)
            else:
                step.fail_execution(result.error_message or "Erro desconhecido")
                execution.add_log("error", f"Passo '{step.step_id}' falhou: {result.error_message}", step.step_id)
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout de {step.timeout_seconds}s excedido"
            step.fail_execution(error_msg)
            execution.add_log("error", f"Passo '{step.step_id}' falhou: {error_msg}", step.step_id)
        except Exception as e:
            step.fail_execution(str(e))
            execution.add_log("error", f"Passo '{step.step_id}' falhou: {str(e)}", step.step_id)
        
        # Salvar progresso
        await self.execution_repo.save_execution(execution)
    
    async def _retry_step(self, execution: MultiAgentExecution, step: ExecutionStep):
        """Retry failed step"""
        if step.retry_attempts >= step.retry_count:
            return
        
        execution.add_log("info", f"Tentando novamente passo '{step.step_id}' (tentativa {step.retry_attempts + 1})")
        
        # Aguardar delay
        if step.retry_delay_seconds > 0:
            await asyncio.sleep(step.retry_delay_seconds)
        
        step.retry_execution()
        await self._execute_step(execution, step)
        
        # Se ainda falhou e tem mais tentativas, tentar novamente
        if step.status == StepStatus.FAILED and step.retry_attempts < step.retry_count:
            await self._retry_step(execution, step)
    
    async def _validate_plan_agents(self, steps: List[ExecutionStep]):
        """Validate that all agents and capabilities exist"""
        for step in steps:
            agent = self.agent_registry.get_agent(step.agent_id)
            if not agent:
                raise ValueError(f"Agente '{step.agent_id}' não encontrado")
            
            if not agent.has_capability(step.capability_name):
                raise ValueError(f"Agente '{step.agent_id}' não tem capacidade '{step.capability_name}'")
    
    async def get_execution_by_id(self, execution_id: UUID, user_id: UUID) -> Optional[MultiAgentExecution]:
        """Get execution by ID"""
        # Verificar execuções ativas primeiro
        if execution_id in self._active_executions:
            execution = self._active_executions[execution_id]
            if execution.user_id == user_id:
                return execution
        
        # Buscar no banco
        execution = await self.execution_repo.find_execution_by_id(execution_id)
        if execution and execution.user_id != user_id:
            raise ValueError("Usuário não tem permissão para ver esta execução")
        
        return execution
    
    async def cancel_execution(self, execution_id: UUID, user_id: UUID) -> bool:
        """Cancel running execution"""
        execution = await self.get_execution_by_id(execution_id, user_id)
        if not execution:
            return False
        
        if execution.status not in [ExecutionStatus.RUNNING, ExecutionStatus.PENDING]:
            return False
        
        execution.cancel()
        await self.execution_repo.save_execution(execution)
        
        return True
    
    async def pause_execution(self, execution_id: UUID, user_id: UUID) -> bool:
        """Pause running execution"""
        execution = await self.get_execution_by_id(execution_id, user_id)
        if not execution:
            return False
        
        if execution.status != ExecutionStatus.RUNNING:
            return False
        
        execution.pause()
        await self.execution_repo.save_execution(execution)
        
        return True
    
    async def resume_execution(self, execution_id: UUID, user_id: UUID) -> bool:
        """Resume paused execution"""
        execution = await self.get_execution_by_id(execution_id, user_id)
        if not execution:
            return False
        
        if execution.status != ExecutionStatus.PAUSED:
            return False
        
        execution.resume()
        await self.execution_repo.save_execution(execution)
        
        return True
    
    async def list_user_executions(
        self,
        user_id: UUID,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MultiAgentExecution]:
        """List user executions"""
        return await self.execution_repo.find_executions_by_user(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    async def get_execution_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get execution statistics"""
        return await self.execution_repo.get_execution_stats(user_id)
    
    async def get_active_executions(self) -> List[Dict[str, Any]]:
        """Get currently active executions"""
        active_executions = []
        
        for execution_id, execution in self._active_executions.items():
            progress = execution.get_progress()
            active_executions.append({
                'execution_id': str(execution_id),
                'user_id': str(execution.user_id),
                'plan_name': execution.plan.name,
                'status': execution.status.value,
                'progress': progress,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'running_time_ms': execution.calculate_execution_time()
            })
        
        return active_executions
    
    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """Clean up old completed executions"""
        return await self.execution_repo.cleanup_old_executions(days_old)

def get_execution_service() -> ExecutionService:
    """Get execution service instance"""
    return ExecutionService()