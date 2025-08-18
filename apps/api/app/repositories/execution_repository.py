"""
Repository for multi-agent execution data access
Camada de infraestrutura para acesso aos dados de execuções no Supabase
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.execution import MultiAgentExecution, ExecutionPlan, ExecutionStatus

class ExecutionRepository:
    """Repository para acesso aos dados de execuções multi-agente no Supabase"""
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
    
    async def save_execution(self, execution: MultiAgentExecution) -> MultiAgentExecution:
        """Salvar execução no banco de dados"""
        execution_data = {
            'id': str(execution.execution_id),
            'user_id': str(execution.user_id),
            'plan_data': execution.plan.to_dict(),
            'input_data': execution.input_data,
            'context': execution.context,
            'status': execution.status.value,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'error_message': execution.error_message,
            'results': execution.results,
            'execution_logs': execution.execution_logs,
            'updated_at': execution.updated_at.isoformat()
        }
        
        # Se é nova execução, incluir created_at
        if not await self.execution_exists(execution.execution_id):
            execution_data['created_at'] = execution.created_at.isoformat()
        
        # Upsert no Supabase
        if self.supabase:
            result = self.supabase.table('multi_agent_executions').upsert(execution_data).execute()
            if result.data:
                return await self._map_execution_to_domain(result.data[0])
        
        return execution
    
    async def find_execution_by_id(self, execution_id: UUID) -> Optional[MultiAgentExecution]:
        """Buscar execução por ID"""
        if not self.supabase:
            return None
        
        result = (
            self.supabase.table('multi_agent_executions')
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
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MultiAgentExecution]:
        """Buscar execuções por usuário"""
        if not self.supabase:
            return []
        
        query = (
            self.supabase.table('multi_agent_executions')
            .select('*')
            .eq('user_id', str(user_id))
        )
        
        if status:
            query = query.eq('status', status.value)
        
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        executions = []
        for row in result.data:
            executions.append(await self._map_execution_to_domain(row))
        return executions
    
    async def find_running_executions(self) -> List[MultiAgentExecution]:
        """Buscar execuções em andamento"""
        if not self.supabase:
            return []
        
        result = (
            self.supabase.table('multi_agent_executions')
            .select('*')
            .eq('status', 'running')
            .execute()
        )
        
        executions = []
        for row in result.data:
            executions.append(await self._map_execution_to_domain(row))
        return executions
    
    async def find_executions_by_status(
        self,
        status: ExecutionStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[MultiAgentExecution]:
        """Buscar execuções por status"""
        if not self.supabase:
            return []
        
        result = (
            self.supabase.table('multi_agent_executions')
            .select('*')
            .eq('status', status.value)
            .order('created_at', desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        
        executions = []
        for row in result.data:
            executions.append(await self._map_execution_to_domain(row))
        return executions
    
    async def find_executions_by_date_range(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0
    ) -> List[MultiAgentExecution]:
        """Buscar execuções por período"""
        if not self.supabase:
            return []
        
        result = (
            self.supabase.table('multi_agent_executions')
            .select('*')
            .eq('user_id', str(user_id))
            .gte('created_at', start_date.isoformat())
            .lte('created_at', end_date.isoformat())
            .order('created_at', desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        
        executions = []
        for row in result.data:
            executions.append(await self._map_execution_to_domain(row))
        return executions
    
    async def get_execution_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Obter estatísticas de execuções do usuário"""
        if not self.supabase:
            return {
                'total_executions': 0,
                'completed_executions': 0,
                'failed_executions': 0,
                'running_executions': 0,
                'success_rate': 0.0,
                'avg_execution_time_ms': 0.0
            }
        
        # Query para estatísticas básicas
        result = (
            self.supabase.table('multi_agent_executions')
            .select('status, started_at, completed_at')
            .eq('user_id', str(user_id))
            .execute()
        )
        
        stats = {
            'total_executions': len(result.data),
            'completed_executions': 0,
            'failed_executions': 0,
            'running_executions': 0,
            'cancelled_executions': 0,
            'success_rate': 0.0,
            'avg_execution_time_ms': 0.0
        }
        
        execution_times = []
        
        for row in result.data:
            status = row['status']
            
            if status == 'completed':
                stats['completed_executions'] += 1
                
                # Calcular tempo de execução
                if row.get('started_at') and row.get('completed_at'):
                    started = datetime.fromisoformat(row['started_at'].replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(row['completed_at'].replace('Z', '+00:00'))
                    execution_time = int((completed - started).total_seconds() * 1000)
                    execution_times.append(execution_time)
                    
            elif status == 'failed':
                stats['failed_executions'] += 1
            elif status == 'running':
                stats['running_executions'] += 1
            elif status == 'cancelled':
                stats['cancelled_executions'] += 1
        
        # Calcular taxa de sucesso
        if stats['total_executions'] > 0:
            stats['success_rate'] = (stats['completed_executions'] / stats['total_executions']) * 100
        
        # Calcular tempo médio de execução
        if execution_times:
            stats['avg_execution_time_ms'] = sum(execution_times) / len(execution_times)
        
        return stats
    
    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """Limpar execuções antigas"""
        if not self.supabase:
            return 0
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
        
        result = (
            self.supabase.table('multi_agent_executions')
            .delete()
            .lt('created_at', cutoff_date)
            .in_('status', ['completed', 'failed', 'cancelled'])
            .execute()
        )
        
        return len(result.data)
    
    async def execution_exists(self, execution_id: UUID) -> bool:
        """Verificar se execução existe"""
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('multi_agent_executions')
            .select('id')
            .eq('id', str(execution_id))
            .limit(1)
            .execute()
        )
        return len(result.data) > 0
    
    async def _map_execution_to_domain(self, row: Dict[str, Any]) -> MultiAgentExecution:
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
        
        # Reconstruir plano de execução
        plan_data = row.get('plan_data', {})
        plan = ExecutionPlan.from_dict(plan_data)
        
        # Criar execução
        execution = MultiAgentExecution(
            execution_id=UUID(row['id']),
            user_id=UUID(row['user_id']),
            plan=plan,
            input_data=row.get('input_data', {}),
            context=row.get('context', {})
        )
        
        # Restaurar estado
        execution.status = ExecutionStatus(row.get('status', 'pending'))
        execution.error_message = row.get('error_message')
        execution.results = row.get('results', {})
        execution.execution_logs = row.get('execution_logs', [])
        execution.started_at = started_at
        execution.completed_at = completed_at
        execution.created_at = created_at or datetime.utcnow()
        execution.updated_at = updated_at or datetime.utcnow()
        
        return execution