"""
Casos de uso para gerenciamento de equipes.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from math import ceil

from app.domain.team import Team, TeamAgent, AgentConfig
from app.schemas.team import (
    TeamCreate, TeamUpdate, TeamResponse, TeamListItem, 
    WorkflowType, TeamStatus, AgentRole
)
from app.infra.suna.client import SunaClient


class TeamService:
    """Serviço para gerenciamento de equipes."""
    
    def __init__(self, suna_client: SunaClient):
        self.suna_client = suna_client
        # Armazenamento em memória (temporário - substituir por banco)
        self._teams: Dict[UUID, Team] = {}
    
    async def create_team(self, user_id: UUID, team_data: TeamCreate) -> TeamResponse:
        """Cria uma nova equipe."""
        # Converte agentes do schema para entidade
        agents = []
        for agent_data in team_data.agents:
            # Busca detalhes do agente no Suna
            try:
                agent_details = await self.suna_client.get_agent(agent_data.agent_id)
            except Exception:
                agent_details = None
            
            agent = TeamAgent(
                agent_id=agent_data.agent_id,
                role=agent_data.role,
                order=agent_data.order,
                config=AgentConfig(
                    input_source=agent_data.config.input_source,
                    conditions=agent_data.config.conditions,
                    parameters=agent_data.config.parameters,
                    timeout_seconds=agent_data.config.timeout_seconds
                ),
                agent_details=agent_details
            )
            agents.append(agent)
        
        # Cria a equipe
        team = Team(
            name=team_data.name,
            description=team_data.description,
            workflow_type=team_data.workflow_type,
            user_id=user_id,
            agents=agents
        )
        
        # Armazena
        self._teams[team.id] = team
        
        return self._team_to_response(team)
    
    async def get_team(self, team_id: UUID, user_id: UUID) -> Optional[TeamResponse]:
        """Obtém uma equipe por ID."""
        team = self._teams.get(team_id)
        if not team or team.user_id != user_id:
            return None
        
        return self._team_to_response(team)
    
    async def list_teams(
        self, 
        user_id: UUID, 
        page: int = 1, 
        limit: int = 10, 
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista equipes do usuário com paginação."""
        # Filtra equipes do usuário
        user_teams = [team for team in self._teams.values() if team.user_id == user_id]
        
        # Aplica filtro de busca
        if search:
            search_lower = search.lower()
            user_teams = [
                team for team in user_teams 
                if search_lower in team.name.lower() or 
                (team.description and search_lower in team.description.lower())
            ]
        
        # Paginação
        total = len(user_teams)
        start = (page - 1) * limit
        end = start + limit
        teams_page = user_teams[start:end]
        
        # Converte para response
        teams_response = [self._team_to_list_item(team) for team in teams_page]
        
        return {
            "teams": teams_response,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": ceil(total / limit) if total > 0 else 0
            }
        }
    
    async def update_team(
        self, 
        team_id: UUID, 
        user_id: UUID, 
        team_data: TeamUpdate
    ) -> Optional[TeamResponse]:
        """Atualiza uma equipe."""
        team = self._teams.get(team_id)
        if not team or team.user_id != user_id:
            return None
        
        # Atualiza campos básicos
        update_data = {}
        if team_data.name is not None:
            update_data["name"] = team_data.name
        if team_data.description is not None:
            update_data["description"] = team_data.description
        if team_data.workflow_type is not None:
            update_data["workflow_type"] = team_data.workflow_type
        if team_data.status is not None:
            update_data["status"] = team_data.status
        
        # Atualiza agentes se fornecidos
        if team_data.agents is not None:
            agents = []
            for agent_data in team_data.agents:
                # Busca detalhes do agente no Suna
                try:
                    agent_details = await self.suna_client.get_agent(agent_data.agent_id)
                except Exception:
                    agent_details = None
                
                agent = TeamAgent(
                    agent_id=agent_data.agent_id,
                    role=agent_data.role,
                    order=agent_data.order,
                    config=AgentConfig(
                        input_source=agent_data.config.input_source,
                        conditions=agent_data.config.conditions,
                        parameters=agent_data.config.parameters,
                        timeout_seconds=agent_data.config.timeout_seconds
                    ),
                    agent_details=agent_details
                )
                agents.append(agent)
            update_data["agents"] = agents
        
        team.update(**update_data)
        return self._team_to_response(team)
    
    async def delete_team(self, team_id: UUID, user_id: UUID) -> bool:
        """Remove uma equipe."""
        team = self._teams.get(team_id)
        if not team or team.user_id != user_id:
            return False
        
        del self._teams[team_id]
        return True
    
    def _team_to_response(self, team: Team) -> TeamResponse:
        """Converte entidade Team para schema de resposta."""
        from app.schemas.team import TeamAgentConfig, TeamAgent as TeamAgentSchema
        
        agents_response = []
        for agent in team.agents:
            agent_schema = TeamAgentSchema(
                id=agent.id,
                agent_id=agent.agent_id,
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