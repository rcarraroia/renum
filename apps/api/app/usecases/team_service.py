"""
Casos de uso para gerenciamento de equipes.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from math import ceil
from datetime import datetime

from app.domain.team import Team, TeamAgent, AgentConfig
from app.schemas.team import (
    TeamCreate, TeamUpdate, TeamResponse, TeamListItem, 
    WorkflowType, TeamStatus, AgentRole, TeamAgentCreate
)
from app.infra.suna.client import SunaClient
from app.core.security import get_supabase_client


class TeamService:
    """Serviço para gerenciamento de equipes."""
    
    def __init__(self, suna_client: SunaClient):
        self.suna_client = suna_client
        self.supabase = get_supabase_client()
    
    async def create_team(self, user_id: UUID, team_data: TeamCreate) -> TeamResponse:
        """Cria uma nova equipe."""
        # Converte agentes para JSON
        agents_json = []
        for agent_data in team_data.agents:
            # Busca detalhes do agente no Suna
            try:
                agent_details = await self.suna_client.get_agent(str(agent_data.agent_id))
            except Exception:
                agent_details = None
            
            agent_json = {
                "agent_id": str(agent_data.agent_id),
                "role": agent_data.role.value,
                "order": agent_data.order,
                "config": {
                    "input_source": agent_data.config.input_source,
                    "conditions": agent_data.config.conditions,
                    "timeout_minutes": agent_data.config.timeout_minutes
                },
                "agent_details": agent_details
            }
            agents_json.append(agent_json)
        
        # Insere no Supabase
        try:
            response = self.supabase.table('teams').insert({
                "name": team_data.name,
                "description": team_data.description,
                "workflow_type": team_data.workflow_type.value,
                "user_id": str(user_id),
                "agents": agents_json,
                "status": "active"
            }).execute()
            
            if response.data:
                team_data_db = response.data[0]
                return self._db_to_response(team_data_db)
            else:
                raise Exception("No data returned from database")
                
        except Exception as e:
            raise Exception(f"Failed to create team in database: {str(e)}")
    
    async def get_team(self, team_id: UUID, user_id: UUID) -> Optional[TeamResponse]:
        """Obtém uma equipe por ID."""
        try:
            response = self.supabase.table('teams').select('*').eq('id', str(team_id)).eq('user_id', str(user_id)).execute()
            
            if response.data:
                return self._db_to_response(response.data[0])
            return None
            
        except Exception:
            return None
    
    async def list_teams(
        self, 
        user_id: UUID, 
        page: int = 1, 
        limit: int = 10, 
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista equipes do usuário com paginação."""
        try:
            # Query base
            query = self.supabase.table('teams').select('*').eq('user_id', str(user_id))
            
            # Aplica filtro de busca
            if search:
                query = query.or_(f'name.ilike.%{search}%,description.ilike.%{search}%')
            
            # Conta total
            count_response = query.execute()
            total = len(count_response.data) if count_response.data else 0
            
            # Aplica paginação
            start = (page - 1) * limit
            paginated_query = query.range(start, start + limit - 1).order('created_at', desc=True)
            
            response = paginated_query.execute()
            
            # Converte para response
            teams_response = [self._db_to_list_item(team_data) for team_data in response.data] if response.data else []
            
            return {
                "teams": teams_response,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": ceil(total / limit) if total > 0 else 0
                }
            }
            
        except Exception as e:
            # Fallback para lista vazia se houver erro
            return {
                "teams": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "pages": 0
                }
            }
    
    async def update_team(
        self, 
        team_id: UUID, 
        user_id: UUID, 
        team_data: TeamUpdate
    ) -> Optional[TeamResponse]:
        """Atualiza uma equipe."""
        try:
            # Prepara dados para atualização
            update_data = {}
            
            if team_data.name is not None:
                update_data["name"] = team_data.name
            if team_data.description is not None:
                update_data["description"] = team_data.description
            if team_data.workflow_type is not None:
                update_data["workflow_type"] = team_data.workflow_type.value
            if team_data.status is not None:
                update_data["status"] = team_data.status.value
            
            # Atualiza agentes se fornecidos
            if team_data.agents is not None:
                agents_json = []
                for agent_data in team_data.agents:
                    # Busca detalhes do agente no Suna
                    try:
                        agent_details = await self.suna_client.get_agent(str(agent_data.agent_id))
                    except Exception:
                        agent_details = None
                    
                    agent_json = {
                        "agent_id": str(agent_data.agent_id),
                        "role": agent_data.role.value,
                        "order": agent_data.order,
                        "config": {
                            "input_source": agent_data.config.input_source,
                            "conditions": agent_data.config.conditions,
                            "timeout_minutes": agent_data.config.timeout_minutes
                        },
                        "agent_details": agent_details
                    }
                    agents_json.append(agent_json)
                update_data["agents"] = agents_json
            
            # Atualiza no banco
            response = self.supabase.table('teams').update(update_data).eq('id', str(team_id)).eq('user_id', str(user_id)).execute()
            
            if response.data:
                return self._db_to_response(response.data[0])
            return None
            
        except Exception:
            return None
    
    async def delete_team(self, team_id: UUID, user_id: UUID) -> bool:
        """Remove uma equipe."""
        try:
            response = self.supabase.table('teams').delete().eq('id', str(team_id)).eq('user_id', str(user_id)).execute()
            return len(response.data) > 0 if response.data else False
        except Exception:
            return False
    
    def _team_to_response(self, team: Team) -> TeamResponse:
        """Converte entidade Team para schema de resposta."""
        from app.schemas.team import TeamAgentConfig, TeamAgent as TeamAgentSchema
        
        agents_response = []
        for agent in team.agents:
            agent_schema = TeamAgentSchema(
                id=agent.id,
                agent_id=UUID(agent.agent_id),
                role=agent.role,
                order=agent.order,
                config=TeamAgentConfig(
                    input_source=agent.config.input_source,
                    conditions=agent.config.conditions,
                    timeout_minutes=agent.config.timeout_seconds // 60 if agent.config.timeout_seconds else None
                )
            )
            agents_response.append(agent_schema)
        
        return TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            workflow_type=team.workflow_type,
            user_id=team.user_id,
            agents=agents_response,
            status=team.status,
            agents_count=team.agents_count,
            created_at=team.created_at,
            updated_at=team.updated_at
        )
    
    def _db_to_response(self, team_data: Dict[str, Any]) -> TeamResponse:
        """Converte dados do banco para schema de resposta."""
        from app.schemas.team import TeamAgentConfig, TeamAgent as TeamAgentSchema
        
        agents_response = []
        for agent_data in team_data.get('agents', []):
            agent_schema = TeamAgentSchema(
                id=UUID(agent_data.get('id', str(UUID('00000000-0000-0000-0000-000000000000')))),
                agent_id=UUID(agent_data['agent_id']),
                role=AgentRole(agent_data['role']),
                order=agent_data['order'],
                config=TeamAgentConfig(
                    input_source=agent_data['config']['input_source'],
                    conditions=agent_data['config'].get('conditions', []),
                    timeout_minutes=agent_data['config'].get('timeout_minutes')
                )
            )
            agents_response.append(agent_schema)
        
        return TeamResponse(
            id=UUID(team_data['id']),
            name=team_data['name'],
            description=team_data.get('description'),
            workflow_type=WorkflowType(team_data['workflow_type']),
            user_id=UUID(team_data['user_id']),
            agents=agents_response,
            status=TeamStatus(team_data.get('status', 'active')),
            agents_count=len(agents_response),
            created_at=datetime.fromisoformat(team_data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(team_data['updated_at'].replace('Z', '+00:00'))
        )
    
    def _db_to_list_item(self, team_data: Dict[str, Any]) -> TeamListItem:
        """Converte dados do banco para item de lista."""
        return TeamListItem(
            id=UUID(team_data['id']),
            name=team_data['name'],
            description=team_data.get('description'),
            workflow_type=WorkflowType(team_data['workflow_type']),
            agents_count=len(team_data.get('agents', [])),
            status=TeamStatus(team_data.get('status', 'active')),
            created_at=datetime.fromisoformat(team_data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(team_data['updated_at'].replace('Z', '+00:00'))
        )
    
    def _team_to_list_item(self, team: Team) -> TeamListItem:
        """Converte entidade Team para item de lista."""
        return TeamListItem(
            id=team.id,
            name=team.name,
            description=team.description,
            workflow_type=team.workflow_type,
            agents_count=team.agents_count,
            status=team.status,
            created_at=team.created_at,
            updated_at=team.updated_at
        )


# Instância global do serviço (temporário)
_team_service: Optional[TeamService] = None


def get_team_service(suna_client: SunaClient) -> TeamService:
    """Dependency injection para o serviço de equipes."""
    global _team_service
    if _team_service is None:
        _team_service = TeamService(suna_client)
    return _team_service