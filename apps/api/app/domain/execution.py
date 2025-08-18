"""
Domain models for multi-agent execution engine
Entidades de negócio para execução coordenada de múltiplos agentes
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
from enum import Enum
import json

class ExecutionStatus(Enum):
    """Status de execução"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class StepStatus(Enum):
    """Status de um passo de execução"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"

class ExecutionStrategy(Enum):
    """Estratégias de execução"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"
    HYBRID = "hybrid"

class FailureHandling(Enum):
    """Estratégias de tratamento de falhas"""
    STOP_ON_FAILURE = "stop_on_failure"
    CONTINUE_ON_FAILURE = "continue_on_failure"
    RETRY_ON_FAILURE = "retry_on_failure"
    ROLLBACK_ON_FAILURE = "rollback_on_failure"

class ExecutionStep:
    """Passo individual de execução"""
    
    def __init__(
        self,
        step_id: str,
        agent_id: str,
        capability_name: str,
        input_data: Dict[str, Any],
        depends_on: Optional[List[str]] = None,
        timeout_seconds: int = 300,
        retry_count: int = 0,
        retry_delay_seconds: int = 5,
        condition: Optional[str] = None,
        credential_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.step_id = step_id
        self.agent_id = agent_id
        self.capability_name = capability_name
        self.input_data = input_data
        self.depends_on = depends_on or []
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.retry_delay_seconds = retry_delay_seconds
        self.condition = condition
        self.credential_id = credential_id
        self.metadata = metadata or {}
        
        # Estado de execução
        self.status = StepStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.output_data: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None
        self.execution_time_ms: Optional[int] = None
        self.attempts = 0
    
    def can_execute(self, completed_steps: List[str], context: Dict[str, Any]) -> bool:
        """Verifica se o passo pode ser executado"""
        # Verificar dependências
        if not all(dep in completed_steps for dep in self.depends_on):
            return False
        
        # Verificar condição
        if self.condition:
            return self._evaluate_condition(context)
        
        return True
    
    def _evaluate_condition(self, context: Dict[str, Any]) -> bool:
        """Avalia condição de execução"""
        if not self.condition:
            return True
        
        try:
            # Substituir variáveis no contexto
            condition = self.condition
            for key, value in context.items():
                condition = condition.replace(f"${{{key}}}", str(value))
            
            # Avaliação segura de expressões simples
            # Em produção, usar um parser mais robusto
            return eval(condition)
        except:
            return True
    
    def start_execution(self):
        """Iniciar execução do passo"""
        self.status = StepStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.attempts += 1
    
    def complete_execution(self, output_data: Dict[str, Any]):
        """Completar execução com sucesso"""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.output_data = output_data
        
        if self.started_at:
            self.execution_time_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
    
    def fail_execution(self, error_message: str):
        """Falhar execução"""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        
        if self.started_at:
            self.execution_time_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
    
    def should_retry(self) -> bool:
        """Verifica se deve tentar novamente"""
        return self.attempts < self.retry_count + 1 and self.status == StepStatus.FAILED
    
    def prepare_retry(self):
        """Preparar para nova tentativa"""
        self.status = StepStatus.RETRYING
        self.error_message = None
        self.started_at = None
        self.completed_at = None
    
    def skip_execution(self, reason: str):
        """Pular execução"""
        self.status = StepStatus.SKIPPED
        self.completed_at = datetime.utcnow()
        self.error_message = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'step_id': self.step_id,
            'agent_id': self.agent_id,
            'capability_name': self.capability_name,
            'input_data': self.input_data,
            'depends_on': self.depends_on,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'retry_delay_seconds': self.retry_delay_seconds,
            'condition': self.condition,
            'credential_id': str(self.credential_id) if self.credential_id else None,
            'metadata': self.metadata,
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'output_data': self.output_data,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'attempts': self.attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionStep':
        """Criar a partir de dicionário"""
        step = cls(
            step_id=data['step_id'],
            agent_id=data['agent_id'],
            capability_name=data['capability_name'],
            input_data=data['input_data'],
            depends_on=data.get('depends_on', []),
            timeout_seconds=data.get('timeout_seconds', 300),
            retry_count=data.get('retry_count', 0),
            retry_delay_seconds=data.get('retry_delay_seconds', 5),
            condition=data.get('condition'),
            credential_id=UUID(data['credential_id']) if data.get('credential_id') else None,
            metadata=data.get('metadata', {})
        )
        
        # Restaurar estado
        step.status = StepStatus(data.get('status', 'pending'))
        step.attempts = data.get('attempts', 0)
        step.output_data = data.get('output_data')
        step.error_message = data.get('error_message')
        step.execution_time_ms = data.get('execution_time_ms')
        
        if data.get('started_at'):
            step.started_at = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
        
        if data.get('completed_at'):
            step.completed_at = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
        
        return step

class ExecutionPlan:
    """Plano de execução multi-agente"""
    
    def __init__(
        self,
        plan_id: str,
        name: str,
        description: str,
        steps: List[ExecutionStep],
        strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
        failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE,
        max_parallel_steps: int = 5,
        global_timeout_minutes: int = 60,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.plan_id = plan_id
        self.name = name
        self.description = description
        self.steps = steps
        self.strategy = strategy
        self.failure_handling = failure_handling
        self.max_parallel_steps = max_parallel_steps
        self.global_timeout_minutes = global_timeout_minutes
        self.metadata = metadata or {}
        
        # Validar plano
        self._validate()
    
    def _validate(self):
        """Validar plano de execução"""
        if not self.steps:
            raise ValueError("Plano deve ter pelo menos um passo")
        
        # Verificar IDs únicos
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("IDs dos passos devem ser únicos")
        
        # Verificar dependências válidas
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(f"Dependência '{dep}' não encontrada nos passos")
        
        # Verificar dependências circulares
        if self._has_circular_dependencies():
            raise ValueError("Dependências circulares detectadas")
    
    def _has_circular_dependencies(self) -> bool:
        """Verificar dependências circulares"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = next((s for s in self.steps if s.step_id == step_id), None)
            if not step:
                return False
            
            for dep in step.depends_on:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(step_id)
            return False
        
        for step in self.steps:
            if step.step_id not in visited:
                if has_cycle(step.step_id):
                    return True
        
        return False
    
    def get_execution_levels(self) -> List[List[str]]:
        """Obter níveis de execução baseados em dependências"""
        levels = []
        remaining_steps = {step.step_id: step for step in self.steps}
        completed_steps = set()
        
        while remaining_steps:
            # Encontrar passos que podem ser executados agora
            ready_steps = []
            for step_id, step in remaining_steps.items():
                if all(dep in completed_steps for dep in step.depends_on):
                    ready_steps.append(step_id)
            
            if not ready_steps:
                # Deadlock - não deveria acontecer se validação estiver correta
                break
            
            levels.append(ready_steps)
            
            # Remover passos prontos
            for step_id in ready_steps:
                del remaining_steps[step_id]
                completed_steps.add(step_id)
        
        return levels
    
    def get_step(self, step_id: str) -> Optional[ExecutionStep]:
        """Obter passo por ID"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def estimate_execution_time(self) -> int:
        """Estimar tempo de execução em segundos"""
        if self.strategy == ExecutionStrategy.SEQUENTIAL:
            return sum(step.timeout_seconds for step in self.steps)
        else:
            # Para execução paralela, usar o caminho mais longo
            levels = self.get_execution_levels()
            total_time = 0
            
            for level in levels:
                level_steps = [self.get_step(step_id) for step_id in level]
                max_time = max(step.timeout_seconds for step in level_steps if step)
                total_time += max_time
            
            return total_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'plan_id': self.plan_id,
            'name': self.name,
            'description': self.description,
            'steps': [step.to_dict() for step in self.steps],
            'strategy': self.strategy.value,
            'failure_handling': self.failure_handling.value,
            'max_parallel_steps': self.max_parallel_steps,
            'global_timeout_minutes': self.global_timeout_minutes,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionPlan':
        """Criar a partir de dicionário"""
        steps = [ExecutionStep.from_dict(step_data) for step_data in data['steps']]
        
        return cls(
            plan_id=data['plan_id'],
            name=data['name'],
            description=data['description'],
            steps=steps,
            strategy=ExecutionStrategy(data.get('strategy', 'sequential')),
            failure_handling=FailureHandling(data.get('failure_handling', 'stop_on_failure')),
            max_parallel_steps=data.get('max_parallel_steps', 5),
            global_timeout_minutes=data.get('global_timeout_minutes', 60),
            metadata=data.get('metadata', {})
        )

class ExecutionRun:
    """Execução de um plano multi-agente"""
    
    def __init__(
        self,
        execution_plan: ExecutionPlan,
        user_id: UUID,
        input_context: Optional[Dict[str, Any]] = None,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.execution_plan = execution_plan
        self.user_id = user_id
        self.input_context = input_context or {}
        self.created_at = created_at or datetime.utcnow()
        
        # Estado de execução
        self.status = ExecutionStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.paused_at: Optional[datetime] = None
        
        # Contexto de execução (compartilhado entre passos)
        self.execution_context = self.input_context.copy()
        
        # Logs e métricas
        self.execution_logs: List[Dict[str, Any]] = []
        self.cost_tracking: Dict[str, Any] = {
            'total_cost': 0.0,
            'cost_by_agent': {},
            'cost_by_step': {}
        }
        
        # Controle de execução
        self._cancel_requested = False
        self._pause_requested = False
    
    def start_execution(self):
        """Iniciar execução"""
        if self.status != ExecutionStatus.PENDING:
            raise ValueError(f"Execução não pode ser iniciada. Status atual: {self.status.value}")
        
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.add_log("info", "Execução iniciada")
    
    def complete_execution(self):
        """Completar execução"""
        if self.status != ExecutionStatus.RUNNING:
            raise ValueError(f"Execução não está em andamento. Status atual: {self.status.value}")
        
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.add_log("info", "Execução completada com sucesso")
    
    def fail_execution(self, error_message: str):
        """Falhar execução"""
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.add_log("error", f"Execução falhou: {error_message}")
    
    def cancel_execution(self):
        """Cancelar execução"""
        self._cancel_requested = True
        if self.status == ExecutionStatus.RUNNING:
            self.status = ExecutionStatus.CANCELLED
            self.completed_at = datetime.utcnow()
            self.add_log("warning", "Execução cancelada")
    
    def pause_execution(self):
        """Pausar execução"""
        if self.status == ExecutionStatus.RUNNING:
            self._pause_requested = True
            self.status = ExecutionStatus.PAUSED
            self.paused_at = datetime.utcnow()
            self.add_log("info", "Execução pausada")
    
    def resume_execution(self):
        """Retomar execução"""
        if self.status == ExecutionStatus.PAUSED:
            self.status = ExecutionStatus.RUNNING
            self.paused_at = None
            self._pause_requested = False
            self.add_log("info", "Execução retomada")
    
    def is_cancelled(self) -> bool:
        """Verificar se cancelamento foi solicitado"""
        return self._cancel_requested
    
    def is_pause_requested(self) -> bool:
        """Verificar se pausa foi solicitada"""
        return self._pause_requested
    
    def add_log(self, level: str, message: str, step_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Adicionar log de execução"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'step_id': step_id,
            'metadata': metadata or {}
        }
        self.execution_logs.append(log_entry)
    
    def update_context(self, key: str, value: Any):
        """Atualizar contexto de execução"""
        self.execution_context[key] = value
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Obter valor do contexto"""
        return self.execution_context.get(key, default)
    
    def add_cost(self, agent_id: str, step_id: str, cost: float):
        """Adicionar custo de execução"""
        self.cost_tracking['total_cost'] += cost
        
        if agent_id not in self.cost_tracking['cost_by_agent']:
            self.cost_tracking['cost_by_agent'][agent_id] = 0.0
        self.cost_tracking['cost_by_agent'][agent_id] += cost
        
        if step_id not in self.cost_tracking['cost_by_step']:
            self.cost_tracking['cost_by_step'][step_id] = 0.0
        self.cost_tracking['cost_by_step'][step_id] += cost
    
    def get_completed_steps(self) -> List[str]:
        """Obter lista de passos completados"""
        return [
            step.step_id for step in self.execution_plan.steps
            if step.status == StepStatus.COMPLETED
        ]
    
    def get_failed_steps(self) -> List[str]:
        """Obter lista de passos que falharam"""
        return [
            step.step_id for step in self.execution_plan.steps
            if step.status == StepStatus.FAILED
        ]
    
    def get_progress_percentage(self) -> float:
        """Calcular porcentagem de progresso"""
        total_steps = len(self.execution_plan.steps)
        if total_steps == 0:
            return 100.0
        
        completed_steps = len([
            step for step in self.execution_plan.steps
            if step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
        ])
        
        return (completed_steps / total_steps) * 100.0
    
    def calculate_execution_time(self) -> Optional[int]:
        """Calcular tempo total de execução em milissegundos"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return int((end_time - self.started_at).total_seconds() * 1000)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Obter resumo da execução"""
        return {
            'execution_id': str(self.id),
            'plan_id': self.execution_plan.plan_id,
            'status': self.status.value,
            'progress_percentage': self.get_progress_percentage(),
            'total_steps': len(self.execution_plan.steps),
            'completed_steps': len(self.get_completed_steps()),
            'failed_steps': len(self.get_failed_steps()),
            'execution_time_ms': self.calculate_execution_time(),
            'total_cost': self.cost_tracking['total_cost'],
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'logs_count': len(self.execution_logs)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'id': str(self.id),
            'execution_plan': self.execution_plan.to_dict(),
            'user_id': str(self.user_id),
            'input_context': self.input_context,
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'paused_at': self.paused_at.isoformat() if self.paused_at else None,
            'execution_context': self.execution_context,
            'execution_logs': self.execution_logs,
            'cost_tracking': self.cost_tracking,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionRun':
        """Criar a partir de dicionário"""
        execution_plan = ExecutionPlan.from_dict(data['execution_plan'])
        
        run = cls(
            id=UUID(data['id']),
            execution_plan=execution_plan,
            user_id=UUID(data['user_id']),
            input_context=data.get('input_context', {}),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        )
        
        # Restaurar estado
        run.status = ExecutionStatus(data.get('status', 'pending'))
        run.execution_context = data.get('execution_context', {})
        run.execution_logs = data.get('execution_logs', [])
        run.cost_tracking = data.get('cost_tracking', {'total_cost': 0.0, 'cost_by_agent': {}, 'cost_by_step': {}})
        
        if data.get('started_at'):
            run.started_at = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
        
        if data.get('completed_at'):
            run.completed_at = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
        
        if data.get('paused_at'):
            run.paused_at = datetime.fromisoformat(data['paused_at'].replace('Z', '+00:00'))
        
        return run