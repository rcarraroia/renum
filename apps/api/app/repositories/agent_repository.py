"""
Repository for agent data access
Camada de infraestrutura para acesso aos dados de agentes no Supabase
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.agent import Agent, AgentCapability, AgentPolicy, AgentDependency


class AgentRepository:
    """Repository para acesso aos dados de agentes no Supabase"""
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
    
    async def save(self, agent: Agent) -> Agent:
        """Salvar agente no banco de dados"""
        
        # Converter domain object para formato do banco
        agent_data = {
            'id': str(agent.id),
            'agent_id': agent.agent_id,
            'version': agent.version,
            'name': agent.name,
            'description': agent.description,
            'capabilities': [cap.to_dict() for cap in agent.capabilities],
            'input_schema': agent.input_schema,
            'policy': agent.policy.to_dict(),
            'dependencies': [dep.to_dict() for dep in agent.dependencies],
            'status': agent.status,
            'created_by': str(agent.created_by) if agent.created_by else None,
            'updated_at': agent.updated_at.isoformat()
        }
        
        # Se é novo agente, incluir created_at
        if not await self.exists(agent.id):
            agent_data['created_at'] = agent.created_at.isoformat()
        
        # Upsert no Supabase
        if self.supabase:
            result = self.supabase.table('agents_registry').upsert(agent_data).execute()
            if result.data:
                return await self._map_to_domain(result.data[0])
        
        return agent
    
    async def find_by_id(self, agent_id: UUID) -> Optional[Agent]:
        """Buscar agente por ID"""
        
        if not self.supabase:
            return None
        
        result = self.supabase.table('agents_registry').select('*').eq('id', str(agent_id)).execute()
        
        if result.data:
            return await self._map_to_domain(result.data[0])
        
        return None
    
    async def find_by_agent_id_and_version(
        self, 
        agent_id: str, 
        version: str = "latest"
    ) -> Optional[Agent]:
        """Buscar agente por agent_id e versão"""
        
        if not self.supabase:
            return None
        
        query = self.supabase.table('agents_registry').select('*').eq('agent_id', agent_id)
        
        if version == "latest":
            # Buscar a versão mais recente ativa
            query = query.eq('status', 'active').order('created_at', desc=True).limit(1)
        else:
            query = query.eq('version', version)
        
        result = query.execute()
        
        if result.data:
            return await self._map_to_domain(result.data[0])
        
        return None
    
    async def find_all(
        self, 
        status: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Agent]:
        """Buscar todos os agentes com filtros"""
        
        if not self.supabase:
            return []
        
        query = self.supabase.table('agents_registry').select('*')
        
        # Aplicar filtros
        if status:
            query = query.eq('status', status)
        
        # Para capabilities, precisaríamos usar operadores JSONB do PostgreSQL
        # Por simplicidade, vamos filtrar depois
        
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        agents = []
        for row in result.data:
            agent = await self._map_to_domain(row)
            
            # Filtrar por capabilities se especificado
            if capabilities:
                agent_capabilities = [cap.name for cap in agent.capabilities]
                if not any(cap in agent_capabilities for cap in capabilities):
                    continue
            
            agents.append(agent)
        
        return agents
    
    async def find_versions(self, agent_id: str) -> List[Agent]:
        """Buscar todas as versões de um agente"""
        
        if not self.supabase:
            return []
        
        result = (
            self.supabase.table('agents_registry')
            .select('*')
            .eq('agent_id', agent_id)
            .order('created_at', desc=True)
            .execute()
        )
        
        agents = []
        for row in result.data:
            agents.append(await self._map_to_domain(row))
        
        return agents
    
    async def search(
        self, 
        query: str, 
        capabilities: Optional[List[str]] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Agent]:
        """Buscar agentes por texto"""
        
        if not self.supabase:
            return []
        
        # Busca por nome, descrição ou agent_id
        supabase_query = (
            self.supabase.table('agents_registry')
            .select('*')
            .or_(f'name.ilike.%{query}%,description.ilike.%{query}%,agent_id.ilike.%{query}%')
        )
        
        if status:
            supabase_query = supabase_query.eq('status', status)
        
        supabase_query = supabase_query.order('created_at', desc=True).limit(limit)
        
        result = supabase_query.execute()
        
        agents = []
        for row in result.data:
            agent = await self._map_to_domain(row)
            
            # Filtrar por capabilities se especificado
            if capabilities:
                agent_capabilities = [cap.name for cap in agent.capabilities]
                if not any(cap in agent_capabilities for cap in capabilities):
                    continue
            
            agents.append(agent)
        
        return agents
    
    async def delete(self, agent_id: UUID) -> bool:
        """Deletar agente"""
        
        if not self.supabase:
            return False
        
        result = self.supabase.table('agents_registry').delete().eq('id', str(agent_id)).execute()
        
        return len(result.data) > 0
    
    async def exists(self, agent_id: UUID) -> bool:
        """Verificar se agente existe"""
        
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('agents_registry')
            .select('id')
            .eq('id', str(agent_id))
            .limit(1)
            .execute()
        )
        
        return len(result.data) > 0
    
    async def exists_agent_version(self, agent_id: str, version: str) -> bool:
        """Verificar se combinação agent_id + version existe"""
        
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('agents_registry')
            .select('id')
            .eq('agent_id', agent_id)
            .eq('version', version)
            .limit(1)
            .execute()
        )
        
        return len(result.data) > 0
    
    async def get_usage_stats(self, agent_id: str, version: str) -> Dict[str, Any]:
        """Obter estatísticas de uso do agente"""
        
        # Esta implementação seria mais complexa, consultando outras tabelas
        # Por enquanto, retornamos dados mock
        return {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'avg_execution_time_ms': 0.0,
            'total_cost': 0.0,
            'last_execution': None,
            'success_rate': 0.0
        }
    
    async def _map_to_domain(self, row: Dict[str, Any]) -> Agent:
        """Mapear linha do banco para domain object"""
        
        # Converter capabilities
        capabilities = []
        for cap_data in row.get('capabilities', []):
            capabilities.append(AgentCapability.from_dict(cap_data))
        
        # Converter policy
        policy_data = row.get('policy', {})
        policy = AgentPolicy.from_dict(policy_data)
        
        # Converter dependencies
        dependencies = []
        for dep_data in row.get('dependencies', []):
            dependencies.append(AgentDependency.from_dict(dep_data))
        
        # Converter datas
        created_at = None
        if row.get('created_at'):
            created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        
        updated_at = None
        if row.get('updated_at'):
            updated_at = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
        
        created_by = None
        if row.get('created_by'):
            created_by = UUID(row['created_by'])
        
        return Agent(
            id=UUID(row['id']),
            agent_id=row['agent_id'],
            version=row['version'],
            name=row['name'],
            description=row.get('description'),
            capabilities=capabilities,
            input_schema=row.get('input_schema', {}),
            policy=policy,
            dependencies=dependencies,
            status=row.get('status', 'active'),
            created_by=created_by,
            created_at=created_at,
            updated_at=updated_at
        )