"""
Repository for orchestrator data access
Camada de infraestrutura para workflows e execuções no Supabase
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.orchestrator import (
    Workflow, WorkflowExecution, ConversationSession,
    WorkflowStep, WorkflowConfig, WorkflowStatus, ExecutionStatus
)


class OrchestratorRepository:
    """Repository para dados do orquestrador no Supabase"""
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
    
    # Workflow methods
    
    async def save_workflow(self, workflow: Workflow) -> Workflow:
        """Salvar workflow no banco de dados"""
        
        workflow_data = {
            'id': str(workflow.id),
            'user_id': str(workflow.user_id),
            'name': workflow.name,
            'description': workflow.description,
            'workflow_data': {
                'steps': [step.to_dict() for step in workflow.steps],
                'config': workflow.config.to_dict()
            },
            'agents_used': workflow.get_agents_used(),
            'status': workflow.status.value,
            'updated_at': workflow.updated_at.isoformat()
        }
        
        # Se é novo workflow, incluir created_at
        if not await self.workflow_exists(workflow.id):
            workflow_data['created_at'] = workflow.created_at.isoformat()
        
        if self.supabase:
            result = self.supabase.table('workflows').upsert(workflow_data).execute()
            if result.data:
                return await self._map_workflow_to_domain(result.data[0])
        
        return workflow
    
    async def find_workflow_by_id(self, workflow_id: UUID) -> Optional[Workflow]:
        """Buscar workflow por ID"""
        
        if not self.supabase:
            return None
        
        result = (
            self.supabase.table('workflows')
            .select('*')
            .eq('id', str(workflow_id))
            .execute()
        )
        
        if result.data:
            return await self._map_workflow_to_domain(result.data[0])
        
        return None
    
    async def find_workflows_by_user(
        self, 
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Workflow]:
        """Buscar workflows por usuário"""
        
        if not self.supabase:
            return []
        
        query = (
            self.supabase.table('workflows')
            .select('*')
            .eq('user_id', str(user_id))
        )
        
        if status:
            query = query.eq('status', status)
        
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        workflows = []
        for row in result.data:
            workflows.append(await self._map_workflow_to_domain(row))
        
        return workflows
    
    async def delete_workflow(self, workflow_id: UUID) -> bool:
        """Deletar workflow"""
        
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('workflows')
            .delete()
            .eq('id', str(workflow_id))
            .execute()
        )
        
        return len(result.data) > 0
    
    async def workflow_exists(self, workflow_id: UUID) -> bool:
        """Verificar se workflow existe"""
        
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('workflows')
            .select('id')
            .eq('id', str(workflow_id))
            .limit(1)
            .execute()
        )
        
        return len(result.data) > 0
    
    # Workflow Execution methods
    
    async def save_workflow_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Salvar execução de workflow"""
        
        execution_data = {
            'id': str(execution.id),
            'workflow_id': str(execution.workflow_id),
            'user_id': str(execution.user_id),
            'status': execution.status.value,
            'input_data': execution.input_data,
            'results': execution.results,
            'execution_logs': execution.execution_logs,
            'error_message': execution.error_message,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'updated_at': execution.updated_at.isoformat()
        }
        
        # Se é nova execução, incluir created_at
        if not await self.execution_exists(execution.id):
            execution_data['created_at'] = execution.created_at.isoformat()
        
        if self.supabase:
            result = self.supabase.table('workflow_runs').upsert(execution_data).execute()
            if result.data:
                return await self._map_execution_to_domain(result.data[0])
        
        return execution
    
    async def find_execution_by_id(self, execution_id: UUID) -> Optional[WorkflowExecution]:
        """Buscar execução por ID"""
        
        if not self.supabase:
            return None
        
        result = (
            self.supabase.table('workflow_runs')
            .select('*')
            .eq('id', str(execution_id))
            .execute()
        )
        
        if result.data:
            return await self._map_execution_to_domain(result.data[0])
        
        return None
    
    async def find_executions_by_user(
        self, 
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkflowExecution]:
        """Buscar execuções por usuário"""
        
        if not self.supabase:
            return []
        
        query = (
            self.supabase.table('workflow_runs')
            .select('*')
            .eq('user_id', str(user_id))
        )
        
        if status:
            query = query.eq('status', status)
        
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        executions = []
        for row in result.data:
            executions.append(await self._map_execution_to_domain(row))
        
        return executions
    
    async def find_executions_by_workflow(
        self, 
        workflow_id: UUID,
        limit: int = 50
    ) -> List[WorkflowExecution]:
        """Buscar execuções por workflow"""
        
        if not self.supabase:
            return []
        
        result = (
            self.supabase.table('workflow_runs')
            .select('*')
            .eq('workflow_id', str(workflow_id))
            .order('created_at', desc=True)
            .limit(limit)
            .execute()
        )
        
        executions = []
        for row in result.data:
            executions.append(await self._map_execution_to_domain(row))
        
        return executions
    
    async def execution_exists(self, execution_id: UUID) -> bool:
        """Verificar se execução existe"""
        
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('workflow_runs')
            .select('id')
            .eq('id', str(execution_id))
            .limit(1)
            .execute()
        )
        
        return len(result.data) > 0
    
    # Conversation Session methods (in-memory for now)
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self._sessions: Dict[str, ConversationSession] = {}
    
    async def save_conversation_session(self, session: ConversationSession) -> ConversationSession:
        """Salvar sessão de conversa (em memória por enquanto)"""
        self._sessions[session.session_id] = session
        return session
    
    async def find_conversation_session(self, session_id: str) -> Optional[ConversationSession]:
        """Buscar sessão de conversa"""
        return self._sessions.get(session_id)
    
    async def find_sessions_by_user(self, user_id: UUID) -> List[ConversationSession]:
        """Buscar sessões por usuário"""
        return [
            session for session in self._sessions.values()
            if session.user_id == user_id
        ]
    
    async def delete_conversation_session(self, session_id: str) -> bool:
        """Deletar sessão de conversa"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    async def cleanup_expired_sessions(self, timeout_minutes: int = 30):
        """Limpar sessões expiradas"""
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if session.is_expired(timeout_minutes)
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
    
    # Statistics methods
    
    async def get_workflow_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Obter estatísticas de workflows do usuário"""
        
        # Esta seria uma query mais complexa no Supabase
        # Por enquanto, implementação mock
        return {
            'total_workflows': 5,
            'active_workflows': 3,
            'total_executions': 25,
            'successful_executions': 22,
            'failed_executions': 3,
            'avg_execution_time_seconds': 45.2,
            'total_cost': 12.50
        }
    
    async def get_execution_stats(
        self, 
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Obter estatísticas de execuções"""
        
        # Mock implementation
        return {
            'period_days': days,
            'total_executions': 25,
            'successful_executions': 22,
            'failed_executions': 3,
            'success_rate': 88.0,
            'avg_execution_time_seconds': 45.2,
            'total_cost': 12.50,
            'executions_by_day': [
                {'date': '2024-01-01', 'count': 3, 'success_rate': 100.0},
                {'date': '2024-01-02', 'count': 5, 'success_rate': 80.0}
            ]
        }
    
    # Private helper methods
    
    async def _map_workflow_to_domain(self, row: Dict[str, Any]) -> Workflow:
        """Mapear linha do banco para domain object de workflow"""
        
        # Converter datas
        created_at = None
        if row.get('created_at'):
            created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        
        updated_at = None
        if row.get('updated_at'):
            updated_at = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
        
        # Converter workflow_data
        workflow_data = row.get('workflow_data', {})
        
        # Converter steps
        steps = []
        for step_data in workflow_data.get('steps', []):
            step = WorkflowStep(
                step_id=step_data['step_id'],
                agent_id=step_data['agent_id'],
                agent_version=step_data.get('agent_version', 'latest'),
                action=step_data.get('action', ''),
                input_data=step_data.get('input_data', {}),
                depends_on=step_data.get('depends_on', []),
                timeout_seconds=step_data.get('timeout_seconds', 300),
                retry_count=step_data.get('retry_count', 0),
                condition=step_data.get('condition')
            )
            steps.append(step)
        
        # Converter config
        config_data = workflow_data.get('config', {})
        config = WorkflowConfig.from_dict(config_data)
        
        return Workflow(
            id=UUID(row['id']),
            user_id=UUID(row['user_id']),
            name=row['name'],
            description=row.get('description'),
            steps=steps,
            config=config,
            status=WorkflowStatus(row.get('status', 'draft')),
            created_at=created_at,
            updated_at=updated_at
        )
    
    async def _map_execution_to_domain(self, row: Dict[str, Any]) -> WorkflowExecution:
        """Mapear linha do banco para domain object de execução"""
        
        # Converter datas
        created_at = None
        if row.get('created_at'):
            created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        
        updated_at = None
        if row.get('updated_at'):
            updated_at = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
        
        started_at = None
        if row.get('started_at'):
            started_at = datetime.fromisoformat(row['started_at'].replace('Z', '+00:00'))
        
        completed_at = None
        if row.get('completed_at'):
            completed_at = datetime.fromisoformat(row['completed_at'].replace('Z', '+00:00'))
        
        execution = WorkflowExecution(
            id=UUID(row['id']),
            workflow_id=UUID(row['workflow_id']),
            user_id=UUID(row['user_id']),
            input_data=row.get('input_data', {}),
            status=ExecutionStatus(row.get('status', 'pending')),
            started_at=started_at,
            completed_at=completed_at,
            created_at=created_at,
            updated_at=updated_at
        )
        
        # Definir estado de execução
        execution.results = row.get('results', [])
        execution.execution_logs = row.get('execution_logs', [])
        execution.error_message = row.get('error_message')
        
        return execution