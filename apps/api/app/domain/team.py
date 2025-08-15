"""
Entidades de domínio para Team.
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from app.schemas.team import WorkflowType, TeamStatus, AgentRole


@dataclass
class AgentConfig:
    """Configuração de um agente na equipe."""
    input_source: str
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: Optional[int] = None


@dataclass
class TeamAgent:
    """Agente membro de uma equipe."""
    agent_id: str
    role: AgentRole
    order: int
    config: AgentConfig
    id: UUID = field(default_factory=uuid4)
    agent_details: Optional[Dict[str, Any]] = None


@dataclass
class Team:
    """Entidade Team."""
    name: str
    user_id: UUID
    workflow_type: WorkflowType
    description: Optional[str] = None
    agents: List[TeamAgent] = field(default_factory=list)
    status: TeamStatus = TeamStatus.ACTIVE
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update(self, **kwargs):
        """Atualiza os campos da equipe."""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
    
    @property
    def agents_count(self) -> int:
        """Retorna o número de agentes na equipe."""
        return len(self.agents)