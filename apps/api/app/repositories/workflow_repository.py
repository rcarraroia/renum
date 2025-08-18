"""
Repository for workflow data access
Camada de infraestrutura para acesso aos dados de workflows no Supabase
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

class WorkflowRepository:
    """Repository para acesso aos dados de workflows no Supabase"""
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
    
    async def save_workflow(self, workflow) -> 'Workflow':
        """Salvar workflow no banco de dados"""
        # Converter domain object para formato do banco
        workflow_data = {
            'id': str(workflow.id),
            'user_id': str(workflow.user_id),
            'name': workflow.name,
            'description': workflow.description,
            'workflow_data': {
                'steps': [step.to_dict() for step in workflow.steps],
                'config': workflow.config.to_dict() if workflow.config else {}
            },
            'agents_used': workflow.agents_used,
            'status': workflow.status.value if hasattr(workflow.status, 'value') else workflow.status,
            'updated_at': workflow.updated_at.isoformat()
        }
        
        # Se é novo workflow, incluir created_at
        if not await self.workflow_exists(workflow.id):
            workflow_data['created_at'] = workflow.created_at.isoformat()
        
        # Upsert no Supabase
        if self.supabase:
            result = self.supabase.table('workflows').upsert(workflow_data).execute()
            if result.data:
                return await self._map_workflow_to_domain(result.data[0])
        
        return workflow
    
    async def find_workflow_by_id(self, workflow_id: UUID) -> Optional['Workflow']:
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
    ) -> List['Workflow']:
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
    
    async def save_workflow_run(self, workflow_run) -> 'WorkflowRun':
        """Salvar execução de workflow"""
        # Converter domain object para formato do banco
        run_data = {
            'id': str(workflow_run.id),
            'workflow_id': str(workflow_run.workflow_id),
            'user_id': str(workflow_run.user_id),
            'status': workflow_run.status.value if hasattr(workflow_run.status, 'value') else workflow_run.status,
            'input_data': workflow_run.input_data,
            'results': [result.to_dict() for result in workflow_run.results],
            'execution_logs': [log.to_dict() for log in workflow_run.execution_logs],
            'error_message': workflow_run.error_message,
            'started_at': workflow_run.started_at.isoformat() if workflow_run.started_at else None,
            'completed_at': workflow_run.completed_at.isoformat() if workflow_run.completed_at else None,
            'updated_at': workflow_run.updated_at.isoformat()
        }
        
        # Se é nova execução, incluir created_at
        if not await self.workflow_run_exists(workflow_run.id):
            run_data['created_at'] = workflow_run.created_at.isoformat()
        
        # Upsert no Supabase
        if self.supabase:
            result = self.supabase.table('workflow_runs').upsert(run_data).execute()
            if result.data:
                return await self._map_workflow_run_to_domain(result.data[0])
        
        return workflow_run
    
    async def find_workflow_run_by_id(self, run_id: UUID) -> Optional['WorkflowRun']:
        """Buscar execução por ID"""
        if not self.supabase:
            return None
        
        result = (
            self.supabase.table('workflow_runs')
            .select('*')
            .eq('id', str(run_id))
            .execute()
        )
        
        if result.data:
            return await self._map_workflow_run_to_domain(result.data[0])
        return None
    
    async def find_workflow_runs_by_workflow(
        self,
        workflow_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List['WorkflowRun']:
        """Buscar execuções por workflow"""
        if not self.supabase:
            return []
        
        query = (
            self.supabase.table('workflow_runs')
            .select('*')
            .eq('workflow_id', str(workflow_id))
        )
        
        if status:
            query = query.eq('status', status)
        
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        runs = []
        for row in result.data:
            runs.append(await self._map_workflow_run_to_domain(row))
        return runs
    
    async def find_running_workflows(self) -> List['WorkflowRun']:
        """Buscar workflows em execução"""
        if not self.supabase:
            return []
        
        result = (
            self.supabase.table('workflow_runs')
            .select('*')
            .eq('status', 'running')
            .execute()
        )
        
        runs = []
        for row in result.data:
            runs.append(await self._map_workflow_run_to_domain(row))
        return runs
    
    async def get_workflow_stats(self, workflow_id: UUID) -> Dict[str, Any]:
        """Obter estatísticas de um workflow"""
        # Esta seria uma query mais complexa no Supabase
        # Por enquanto, implementação mock
        return {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'avg_execution_time_ms': 0.0,
            'success_rate': 0.0,
            'last_run': None
        }
    
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
    
    async def workflow_run_exists(self, run_id: UUID) -> bool:
        """Verificar se execução existe"""
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('workflow_runs')
            .select('id')
            .eq('id', str(run_id))
            .limit(1)
            .execute()
        )
        return len(result.data) > 0
    
    async def _map_workflow_to_domain(self, row: Dict[str, Any]) -> 'Workflow':
        """Mapear linha do banco para domain object de workflow"""
        from app.domain.workflow import Workflow, WorkflowConfig, WorkflowStep, WorkflowStatus
        
        # Converter datas
        created_at = None
        if row.get('created_at'):
            created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        
        updated_at = None
        if row.get('updated_at'):
            updated_at = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
        
        # Extrair dados do workflow
        workflow_data = row.get('workflow_data', {})
        steps_data = workflow_data.get('steps', [])
        config_data = workflow_data.get('config', {})
        
        # Converter steps
        steps = []
        for step_data in steps_data:
            steps.append(WorkflowStep.from_dict(step_data))
        
        # Converter config
        config = WorkflowConfig.from_dict(config_data) if config_data else None
        
        # Converter status
        status = WorkflowStatus(row.get('status', 'draft'))
        
        return Workflow(
            id=UUID(row['id']),
            user_id=UUID(row['user_id']),
            name=row['name'],
            description=row.get('description'),
            steps=steps,
            config=config,
            agents_used=row.get('agents_used', []),
            status=status,
            created_at=created_at,
            updated_at=updated_at
        )
    
    async def _map_workflow_run_to_domain(self, row: Dict[str, Any]) -> 'WorkflowRun':
        """Mapear linha do banco para domain object de execução"""
        from app.domain.workflow import WorkflowRun, WorkflowStepResult, WorkflowExecutionLog, WorkflowRunStatus
        
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
        
        # Converter results
        results = []
        for result_data in row.get('results', []):
            results.append(WorkflowStepResult.from_dict(result_data))
        
        # Converter logs
        execution_logs = []
        for log_data in row.get('execution_logs', []):
            execution_logs.append(WorkflowExecutionLog.from_dict(log_data))
        
        # Converter status
        status = WorkflowRunStatus(row.get('status', 'pending'))
        
        return WorkflowRun(
            id=UUID(row['id']),
            workflow_id=UUID(row['workflow_id']),
            user_id=UUID(row['user_id']),
            status=status,
            input_data=row.get('input_data', {}),
            results=results,
            execution_logs=execution_logs,
            error_message=row.get('error_message'),
            started_at=started_at,
            completed_at=completed_at,
            created_at=created_at,
            updated_at=updated_at
        )