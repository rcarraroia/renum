"""
Entidades de domínio para equipes.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class WorkflowType(str, Enum):
    """Tipos de workflow de equipe."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"


class TeamStatus(str, Enum):
    """Status de uma equipe."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class AgentRole(str, Enum):
    """Papel de um agente na equipe."""
    LEADER = "leader"
    MEMBER = "member"
    REVIEWER = "reviewer"


@dataclass
class AgentConfig:
    """Configuração de um agente na equipe."""
    input_source: str
    conditions: List[Dict[str, Any]]
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.timeout_seconds is None:
            self.timeout_seconds = 1800  # 30 minutos padrão


@dataclass
class TeamAgent:
    """Agente membro de uma equipe."""
    id: UUID
    agent_id: str
    role: AgentRole
    order: int
    config: AgentConfig
    
    def __post_init__(self):
        if not isinstance(self.role, AgentRole):
            self.role = AgentRole(self.role)


@dataclass
class Team:
    """Entidade de equipe de agentes."""
    id: UUID
    name: str
    description: Optional[str]
    workflow_type: WorkflowType
    user_id: UUID
    agents: List[TeamAgent]
    status: TeamStatus
    created_at: datetime
    updated_at: datetime
    
    def __post_init__(self):
        if not isinstance(self.workflow_type, WorkflowType):
            self.workflow_type = WorkflowType(self.workflow_type)
        if not isinstance(self.status, TeamStatus):
            self.status = TeamStatus(self.status)
    
    @property
    def agents_count(self) -> int:
        """Número de agentes na equipe."""
        return len(self.agents)
    
    @property
    def leader_agents(self) -> List[TeamAgent]:
        """Agentes com papel de líder."""
        return [agent for agent in self.agents if agent.role == AgentRole.LEADER]
    
    @property
    def member_agents(self) -> List[TeamAgent]:
        """Agentes com papel de membro."""
        return [agent for agent in self.agents if agent.role == AgentRole.MEMBER]
    
    def validate(self) -> List[str]:
        """Valida a equipe e retorna lista de erros."""
        errors = []
        
        # Validações básicas
        if not self.name or len(self.name.strip()) == 0:
            errors.append("Team name is required")
        
        if len(self.name) > 100:
            errors.append("Team name must be 100 characters or less")
        
        if self.description and len(self.description) > 500:
            errors.append("Team description must be 500 characters or less")
        
        # Validações de agentes
        if not self.agents:
            errors.append("Team must have at least one agent")
        
        if len(self.agents) > 10:
            errors.append("Team cannot have more than 10 agents")
        
        # Verifica ordens duplicadas
        orders = [agent.order for agent in self.agents]
        if len(orders) != len(set(orders)):
            errors.append("Agent orders must be unique")
        
        # Verifica se há pelo menos um líder para workflows sequenciais
        if self.workflow_type == WorkflowType.SEQUENTIAL:
            if not self.leader_agents:
                errors.append("Sequential workflow requires at least one leader agent")
        
        return errors
    
    def is_valid(self) -> bool:
        """Verifica se a equipe é válida."""
        return len(self.validate()) == 0