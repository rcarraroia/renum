"""
Casos de uso para gerenciamento de execuções.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from math import ceil
from datetime import datetime, timedelta
import asyncio
import json

from app.schemas.execution import (
    ExecutionCreate, ExecutionResponse, ExecutionListItem, ExecutionStartResponse,
    ExecutionCancelResponse, ExecutionStatus, AgentExecutionStatus, ExecutionConfig,
    ExecutionProgress, AgentResult, ExecutionLog
)
from app.schemas.team import TeamResponse
from app.usecases.team_service import TeamService
from app.infra.suna.client import SunaClient
from app.core.security import get_supabase_client


class ExecutionService:
    """Serviço para gerenciamento de execuções."""
    
    def __init__(self, suna_client: SunaClient, team_service: TeamService):
        self.suna_client = suna_client
        self.team_service = team_service
        self.supabase = get_supabase_client()
    
    async def start_execution(
        self, 
        team_id: UUID, 
        user_id: UUID, 
        execution_data: ExecutionCreate
    ) -> ExecutionStartResponse:
        """Inicia uma nova execução de equipe."""
        
        # Verifica se a equipe existe e pertence ao usuário
        team = await self.team_service.get_team(team_id, user_id)
        if not team:
            raise Exception("Team not found or access denied")
        
        # Cria configuração padrão se não fornecida
        config = execution_data.execution_config or ExecutionConfig()
        
        # Calcula estimativa de conclusão
        estimated_completion = datetime.utcnow() + timedelta(minutes=config.timeout_minutes)
        
        # Cria progresso inicial
        progress = ExecutionProgress(
            completed_agents=0,
            total_agents=len(team.agents),
            current_step="Initializing execution",
            percentage=0.0
        )
        
        # Prepara dados para inserção
        execution_id = uuid4()
        execution_db_data = {
            "id": str(execution_id),
            "team_id": str(team_id),
            "user_id": str(user_id),
            "status": ExecutionStatus.PENDING.value,
            "input_data": execution_data.input_data,
            "execution_config": {
                "timeout_minutes": config.timeout_minutes,
                "parallel_limit": config.parallel_limit,
                "retry_failed": config.retry_failed,
                "max_retries": config.max_retries
            },
            "progress": {
                "completed_agents": progress.completed_agents,
                "total_agents": progress.total_agents,
                "current_step": progress.current_step,
                "percentage": progress.percentage
            },
            "results": [],
            "logs": [{
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": "Execution created",
                "agent_id": None,
                "data": {"team_name": team.name}
            }],
            "started_at": datetime.utcnow().isoformat(),
            "estimated_completion": estimated_completion.isoformat()
        }
        
        try:
            # Insere no banco
            response = self.supabase.table('executions').insert(execution_db_data).execute()
            
            if not response.data:
                raise Exception("Failed to create execution in database")
            
            # Inicia execução assíncrona
            asyncio.create_task(self._execute_team_workflow(execution_id, team, execution_data.input_data, config))
            
            return ExecutionStartResponse(
                execution_id=execution_id,
                team_id=team_id,
                status=ExecutionStatus.PENDING,
                started_at=datetime.utcnow(),
                estimated_completion=estimated_completion,
                progress=progress
            )
            
        except Exception as e:
            raise Exception(f"Failed to start execution: {str(e)}")
    
    async def get_execution(self, execution_id: UUID, user_id: UUID) -> Optional[ExecutionResponse]:
        """Obtém uma execução por ID."""
        try:
            response = self.supabase.table('executions').select('*').eq('id', str(execution_id)).eq('user_id', str(user_id)).execute()
            
            if response.data:
                return self._db_to_response(response.data[0])
            return None
            
        except Exception:
            return None
    
    async def list_executions(
        self,
        user_id: UUID,
        team_id: Optional[UUID] = None,
        status: Optional[ExecutionStatus] = None,
        page: int = 1,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Lista execuções do usuário com filtros."""
        try:
            # Query base
            query = self.supabase.table('executions').select('*, teams(name)').eq('user_id', str(user_id))
            
            # Aplica filtros
            if team_id:
                query = query.eq('team_id', str(team_id))
            if status:
                query = query.eq('status', status.value)
            
            # Conta total
            count_response = query.execute()
            total = len(count_response.data) if count_response.data else 0
            
            # Aplica paginação
            start = (page - 1) * limit
            paginated_query = query.range(start, start + limit - 1).order('created_at', desc=True)
            
            response = paginated_query.execute()
            
            # Converte para response
            executions_response = [self._db_to_list_item(exec_data) for exec_data in response.data] if response.data else []
            
            return {
                "executions": executions_response,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": ceil(total / limit) if total > 0 else 0
                }
            }
            
        except Exception as e:
            return {
                "executions": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "pages": 0
                }
            }
    
    async def cancel_execution(self, execution_id: UUID, user_id: UUID) -> Optional[ExecutionCancelResponse]:
        """Cancela uma execução."""
        try:
            # Atualiza status no banco
            update_data = {
                "status": ExecutionStatus.CANCELLED.value,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table('executions').update(update_data).eq('id', str(execution_id)).eq('user_id', str(user_id)).execute()
            
            if response.data:
                return ExecutionCancelResponse(
                    execution_id=execution_id,
                    status=ExecutionStatus.CANCELLED,
                    cancelled_at=datetime.utcnow()
                )
            return None
            
        except Exception:
            return None
    
    async def _execute_team_workflow(
        self, 
        execution_id: UUID, 
        team: TeamResponse, 
        input_data: Dict[str, Any], 
        config: ExecutionConfig
    ):
        """Executa o workflow da equipe de forma assíncrona."""
        try:
            # Atualiza status para running
            await self._update_execution_status(execution_id, ExecutionStatus.RUNNING, "Starting agent execution")
            
            results = []
            
            if team.workflow_type.value == "sequential":
                results = await self._execute_sequential(execution_id, team, input_data, config)
            elif team.workflow_type.value == "parallel":
                results = await self._execute_parallel(execution_id, team, input_data, config)
            else:
                # Para outros tipos, usa sequential como fallback
                results = await self._execute_sequential(execution_id, team, input_data, config)
            
            # Verifica se todos os agentes foram executados com sucesso
            all_completed = all(result.status == AgentExecutionStatus.COMPLETED for result in results)
            final_status = ExecutionStatus.COMPLETED if all_completed else ExecutionStatus.FAILED
            
            # Atualiza execução final
            await self._update_execution_final(execution_id, final_status, results)
            
        except Exception as e:
            # Em caso de erro, marca como failed
            await self._update_execution_status(execution_id, ExecutionStatus.FAILED, f"Execution failed: {str(e)}")
    
    async def _execute_sequential(
        self, 
        execution_id: UUID, 
        team: TeamResponse, 
        input_data: Dict[str, Any], 
        config: ExecutionConfig
    ) -> List[AgentResult]:
        """Executa agentes sequencialmente."""
        results = []
        current_input = input_data
        
        # Ordena agentes por ordem
        sorted_agents = sorted(team.agents, key=lambda x: x.order)
        
        for i, agent in enumerate(sorted_agents):
            try:
                # Atualiza progresso
                progress_msg = f"Executing agent {i+1}/{len(sorted_agents)}: {agent.agent_id}"
                await self._update_execution_progress(execution_id, i, len(sorted_agents), progress_msg)
                
                # Executa agente
                result = await self._execute_single_agent(agent.agent_id, current_input, config)
                results.append(result)
                
                # Se o agente falhou e não deve continuar, para a execução
                if result.status == AgentExecutionStatus.FAILED and not config.retry_failed:
                    break
                
                # Usa a saída do agente como entrada do próximo (se houver saída)
                if result.output:
                    try:
                        # Tenta parsear como JSON, senão usa como string
                        parsed_output = json.loads(result.output)
                        if isinstance(parsed_output, dict):
                            current_input.update(parsed_output)
                        else:
                            current_input["previous_output"] = result.output
                    except:
                        current_input["previous_output"] = result.output
                
            except Exception as e:
                # Cria resultado de erro para o agente
                error_result = AgentResult(
                    agent_id=agent.agent_id,
                    status=AgentExecutionStatus.FAILED,
                    error_message=str(e),
                    execution_time_ms=0,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    retry_count=0
                )
                results.append(error_result)
                
                if not config.retry_failed:
                    break
        
        return results
    
    async def _execute_parallel(
        self, 
        execution_id: UUID, 
        team: TeamResponse, 
        input_data: Dict[str, Any], 
        config: ExecutionConfig
    ) -> List[AgentResult]:
        """Executa agentes em paralelo."""
        # Cria tasks para todos os agentes
        tasks = []
        for agent in team.agents:
            task = asyncio.create_task(self._execute_single_agent(agent.agent_id, input_data, config))
            tasks.append(task)
        
        # Executa todos em paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Converte exceções em resultados de erro
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = AgentResult(
                    agent_id=team.agents[i].agent_id,
                    status=AgentExecutionStatus.FAILED,
                    error_message=str(result),
                    execution_time_ms=0,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    retry_count=0
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        return final_results
    
    async def _execute_single_agent(
        self, 
        agent_id: UUID, 
        input_data: Dict[str, Any], 
        config: ExecutionConfig
    ) -> AgentResult:
        """Executa um único agente."""
        start_time = datetime.utcnow()
        
        try:
            # Executa agente via Suna
            suna_response = await self.suna_client.execute_agent(str(agent_id), input_data)
            
            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)
            
            return AgentResult(
                agent_id=agent_id,
                status=AgentExecutionStatus.COMPLETED,
                output=suna_response.get("output", ""),
                execution_time_ms=execution_time,
                started_at=start_time,
                completed_at=end_time,
                retry_count=0
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)
            
            return AgentResult(
                agent_id=agent_id,
                status=AgentExecutionStatus.FAILED,
                error_message=str(e),
                execution_time_ms=execution_time,
                started_at=start_time,
                completed_at=end_time,
                retry_count=0
            )
    
    async def _update_execution_status(self, execution_id: UUID, status: ExecutionStatus, message: str):
        """Atualiza status da execução."""
        try:
            update_data = {
                "status": status.value,
                "progress": {
                    "current_step": message
                }
            }
            
            self.supabase.table('executions').update(update_data).eq('id', str(execution_id)).execute()
        except Exception:
            pass  # Ignora erros de atualização
    
    async def _update_execution_progress(self, execution_id: UUID, completed: int, total: int, message: str):
        """Atualiza progresso da execução."""
        try:
            percentage = (completed / total) * 100 if total > 0 else 0
            
            update_data = {
                "progress": {
                    "completed_agents": completed,
                    "total_agents": total,
                    "current_step": message,
                    "percentage": percentage
                }
            }
            
            self.supabase.table('executions').update(update_data).eq('id', str(execution_id)).execute()
        except Exception:
            pass  # Ignora erros de atualização
    
    async def _update_execution_final(self, execution_id: UUID, status: ExecutionStatus, results: List[AgentResult]):
        """Atualiza execução com resultado final."""
        try:
            results_json = []
            for result in results:
                result_dict = {
                    "agent_id": str(result.agent_id),
                    "status": result.status.value,
                    "output": result.output,
                    "error_message": result.error_message,
                    "execution_time_ms": result.execution_time_ms,
                    "started_at": result.started_at.isoformat() if result.started_at else None,
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                    "retry_count": result.retry_count
                }
                results_json.append(result_dict)
            
            completed_count = sum(1 for r in results if r.status == AgentExecutionStatus.COMPLETED)
            
            update_data = {
                "status": status.value,
                "completed_at": datetime.utcnow().isoformat(),
                "results": results_json,
                "progress": {
                    "completed_agents": completed_count,
                    "total_agents": len(results),
                    "current_step": "Execution completed",
                    "percentage": 100.0 if status == ExecutionStatus.COMPLETED else (completed_count / len(results)) * 100
                }
            }
            
            self.supabase.table('executions').update(update_data).eq('id', str(execution_id)).execute()
        except Exception:
            pass  # Ignora erros de atualização
    
    def _db_to_response(self, exec_data: Dict[str, Any]) -> ExecutionResponse:
        """Converte dados do banco para schema de resposta."""
        # Converte results
        results = []
        for result_data in exec_data.get('results', []):
            result = AgentResult(
                agent_id=UUID(result_data['agent_id']),
                status=AgentExecutionStatus(result_data['status']),
                output=result_data.get('output'),
                error_message=result_data.get('error_message'),
                execution_time_ms=result_data.get('execution_time_ms', 0),
                started_at=datetime.fromisoformat(result_data['started_at'].replace('Z', '+00:00')) if result_data.get('started_at') else None,
                completed_at=datetime.fromisoformat(result_data['completed_at'].replace('Z', '+00:00')) if result_data.get('completed_at') else None,
                retry_count=result_data.get('retry_count', 0)
            )
            results.append(result)
        
        # Converte logs
        logs = []
        for log_data in exec_data.get('logs', []):
            log = ExecutionLog(
                timestamp=datetime.fromisoformat(log_data['timestamp'].replace('Z', '+00:00')),
                level=log_data['level'],
                message=log_data['message'],
                agent_id=UUID(log_data['agent_id']) if log_data.get('agent_id') else None,
                data=log_data.get('data')
            )
            logs.append(log)
        
        # Converte progress
        progress_data = exec_data.get('progress', {})
        progress = ExecutionProgress(
            completed_agents=progress_data.get('completed_agents', 0),
            total_agents=progress_data.get('total_agents', 1),
            current_step=progress_data.get('current_step', 'Unknown'),
            percentage=progress_data.get('percentage', 0.0)
        )
        
        # Converte config
        config_data = exec_data.get('execution_config', {})
        config = ExecutionConfig(
            timeout_minutes=config_data.get('timeout_minutes', 30),
            parallel_limit=config_data.get('parallel_limit', 3),
            retry_failed=config_data.get('retry_failed', True),
            max_retries=config_data.get('max_retries', 3)
        )
        
        return ExecutionResponse(
            id=UUID(exec_data['id']),
            team_id=UUID(exec_data['team_id']),
            user_id=UUID(exec_data['user_id']),
            status=ExecutionStatus(exec_data['status']),
            input_data=exec_data['input_data'],
            execution_config=config,
            progress=progress,
            results=results,
            logs=logs,
            started_at=datetime.fromisoformat(exec_data['started_at'].replace('Z', '+00:00')) if exec_data.get('started_at') else None,
            completed_at=datetime.fromisoformat(exec_data['completed_at'].replace('Z', '+00:00')) if exec_data.get('completed_at') else None,
            error_message=exec_data.get('error_message'),
            estimated_completion=datetime.fromisoformat(exec_data['estimated_completion'].replace('Z', '+00:00')) if exec_data.get('estimated_completion') else None,
            created_at=datetime.fromisoformat(exec_data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(exec_data['updated_at'].replace('Z', '+00:00'))
        )
    
    def _db_to_list_item(self, exec_data: Dict[str, Any]) -> ExecutionListItem:
        """Converte dados do banco para item de lista."""
        progress_data = exec_data.get('progress', {})
        progress = ExecutionProgress(
            completed_agents=progress_data.get('completed_agents', 0),
            total_agents=progress_data.get('total_agents', 1),
            current_step=progress_data.get('current_step', 'Unknown'),
            percentage=progress_data.get('percentage', 0.0)
        )
        
        # Pega nome da equipe se disponível
        team_name = "Unknown Team"
        if 'teams' in exec_data and exec_data['teams']:
            team_name = exec_data['teams']['name']
        
        return ExecutionListItem(
            id=UUID(exec_data['id']),
            team_id=UUID(exec_data['team_id']),
            team_name=team_name,
            status=ExecutionStatus(exec_data['status']),
            progress=progress,
            started_at=datetime.fromisoformat(exec_data['started_at'].replace('Z', '+00:00')) if exec_data.get('started_at') else None,
            completed_at=datetime.fromisoformat(exec_data['completed_at'].replace('Z', '+00:00')) if exec_data.get('completed_at') else None,
            created_at=datetime.fromisoformat(exec_data['created_at'].replace('Z', '+00:00'))
        )


# Instância global do serviço (temporário)
_execution_service: Optional[ExecutionService] = None


def get_execution_service(suna_client: SunaClient, team_service: TeamService) -> ExecutionService:
    """Dependency injection para o serviço de execuções."""
    global _execution_service
    if _execution_service is None:
        _execution_service = ExecutionService(suna_client, team_service)
    return _execution_service