"""
Schemas para entidades de Team.
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any
from enum import Enum

from .base import BaseSchema, TimestampedSchema


class WorkflowType(str, Enum):
    """Tipos de workflow suportados."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    PIPELINE = "pipeline"


class AgentRole(str, Enum):
    """Papéis de agente em uma equipe."""
    LEADER = "leader"
    MEMBER = "member"
    COORDINATOR = "coordinator"


class TeamStatus(str, Enum):
    """Status de uma equipe."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class TeamAgentConfig(BaseSchema):
    """Configuração de um agente na equipe."""
    
    input_source: str = Field(..., description="Fonte de entrada do agente")
    conditions: List[Dict[str, Any]] = Field(default=[], description="Condições para execução")
    timeout_minutes: Optional[int] = Field(None, ge=1, le=60, description="Timeout em minutos")


class TeamAgent(BaseSchema):
    """Agente membro de uma equipe."""
    
    id: UUID = Field(..., description="ID único do membro")
    agent_id: UUID = Field(..., description="ID do agente no Suna")
    role: AgentRole = Field(..., description="Papel do agente na equipe")
    order: int = Field(..., ge=1, description="Ordem de execução")
    config: TeamAgentConfig = Field(..., description="Configuração do agente")


class TeamCreate(BaseSchema):
    """Schema para criação de equipe."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Nome da equipe")
    description: Optional[str] = Field(None, max_length=500, description="Descrição da equipe")
    workflow_type: WorkflowType = Field(..., description="Tipo de workflow")
    agents: List[TeamAgent] = Field(..., min_items=1, max_items=10, description="Agentes da equipe")
    
    @validator('agents')
    def validate_agents_order(cls, v):
        """Valida que a ordem dos agentes é sequencial."""
        orders = [agent.order for agent in v]
        if len(set(orders)) != len(orders):
            raise ValueError("Agent orders must be unique")
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise ValueError("Agent orders must be sequential starting from 1")
        return v


class TeamUpdate(BaseSchema):
    """Schema para atualização de equipe."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    workflow_type: Optional[WorkflowType] = None
    agents: Optional[List[TeamAgent]] = Field(None, min_items=1, max_items=10)
    status: Optional[TeamStatus] = None


class TeamResponse(TimestampedSchema):
    """Schema de resposta para equipe."""
    
    id: UUID
    name: str
    description: Optional[str]
    workflow_type: WorkflowType
    user_id: UUID
    agents: List[TeamAgent]
    status: TeamStatus
    agents_count: int = Field(..., description="Número de agentes na equipe")


class TeamListItem(BaseSchema):
    """Item da lista de equipes."""
    
    id: UUID
    name: str
    description: Optional[str]
    workflow_type: WorkflowType
    agents_count: int
    status: TeamStatus
    created_at: datetime
    updated_at: datetime