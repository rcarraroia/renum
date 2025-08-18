"""
Schemas Pydantic para agentes
Baseado na estrutura real da tabela agents_registry no Supabase
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class AgentCapabilitySchema(BaseModel):
    """Schema para capacidade de agente"""
    
    name: str = Field(..., description="Nome da capacidade")
    description: str = Field(..., description="Descrição da capacidade")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Schema de entrada")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="Schema de saída")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "send_email",
                "description": "Enviar email via SMTP ou API",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "format": "email"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"}
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "status": {"type": "string"}
                    }
                }
            }
        }


class AgentPolicySchema(BaseModel):
    """Schema para políticas de agente"""
    
    max_requests_per_minute: int = Field(default=60, description="Máximo de requisições por minuto")
    max_concurrent_executions: int = Field(default=5, description="Máximo de execuções concorrentes")
    timeout_seconds: int = Field(default=30, description="Timeout em segundos")
    allowed_domains: List[str] = Field(default_factory=list, description="Domínios permitidos")
    require_confirmation: bool = Field(default=False, description="Requer confirmação do usuário")
    cost_per_execution: float = Field(default=0.0, description="Custo por execução")
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_requests_per_minute": 100,
                "max_concurrent_executions": 3,
                "timeout_seconds": 45,
                "allowed_domains": ["gmail.com", "outlook.com"],
                "require_confirmation": True,
                "cost_per_execution": 0.01
            }
        }


class AgentDependencySchema(BaseModel):
    """Schema para dependências de agente"""
    
    agent_id: str = Field(..., description="ID do agente dependente")
    version: str = Field(..., description="Versão mínima requerida")
    optional: bool = Field(default=False, description="Dependência opcional")


class CreateAgentSchema(BaseModel):
    """Schema para criação de agente"""
    
    agent_id: str = Field(..., min_length=1, max_length=100, description="ID único do agente")
    version: str = Field(default="1.0.0", description="Versão semântica")
    name: str = Field(..., min_length=1, max_length=200, description="Nome do agente")
    description: Optional[str] = Field(None, description="Descrição do agente")
    capabilities: List[AgentCapabilitySchema] = Field(default_factory=list, description="Capacidades do agente")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Schema de entrada geral")
    policy: AgentPolicySchema = Field(default_factory=AgentPolicySchema, description="Políticas do agente")
    dependencies: List[AgentDependencySchema] = Field(default_factory=list, description="Dependências do agente")
    
    @validator('agent_id')
    def validate_agent_id(cls, v):
        """Validar formato do agent_id"""
        if not v.startswith('sa-'):
            raise ValueError('agent_id deve começar com "sa-"')
        return v
    
    @validator('version')
    def validate_version(cls, v):
        """Validar formato de versão semântica"""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('Versão deve seguir formato semântico (x.y.z)')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "sa-email-basic",
                "version": "1.0.0",
                "name": "Basic Email Agent",
                "description": "Agente para envio de emails via SMTP ou API",
                "capabilities": [
                    {
                        "name": "send_email",
                        "description": "Enviar email",
                        "input_schema": {"type": "object"},
                        "output_schema": {"type": "object"}
                    }
                ]
            }
        }


class UpdateAgentSchema(BaseModel):
    """Schema para atualização de agente"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    capabilities: Optional[List[AgentCapabilitySchema]] = None
    input_schema: Optional[Dict[str, Any]] = None
    policy: Optional[AgentPolicySchema] = None
    dependencies: Optional[List[AgentDependencySchema]] = None
    status: Optional[str] = Field(None, regex="^(active|inactive|deprecated)$")


class AgentSchema(BaseModel):
    """Schema completo de agente (response)"""
    
    id: UUID
    agent_id: str
    version: str
    name: str
    description: Optional[str]
    capabilities: List[AgentCapabilitySchema]
    input_schema: Dict[str, Any]
    policy: AgentPolicySchema
    dependencies: List[AgentDependencySchema]
    status: str
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AgentDetailSchema(AgentSchema):
    """Schema detalhado de agente com informações extras"""
    
    usage_stats: Optional[Dict[str, Any]] = None
    last_execution: Optional[datetime] = None


class AgentListSchema(BaseModel):
    """Schema para lista paginada de agentes"""
    
    agents: List[AgentSchema]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class AgentManifest(BaseModel):
    """Schema para manifesto de agente (usado pelo orquestrador)"""
    
    agent_id: str
    version: str
    name: str
    description: Optional[str]
    capabilities: List[AgentCapabilitySchema]
    input_schema: Dict[str, Any]
    policy: AgentPolicySchema
    dependencies: List[AgentDependencySchema]
    checksum: Optional[str] = None
    signature: Optional[str] = None
    signature_key_id: Optional[str] = None


class AgentApprovalSchema(BaseModel):
    """Schema para aprovação de agente"""
    
    approval_notes: Optional[str] = Field(None, description="Notas da aprovação")
    approved_by: Optional[UUID] = Field(None, description="ID do aprovador")


class AgentMetrics(BaseModel):
    """Schema para métricas de agente"""
    
    agent_id: str
    version: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    avg_execution_time_ms: float
    total_cost: float
    last_execution: Optional[datetime]


class AgentHealthCheck(BaseModel):
    """Schema para health check de agente"""
    
    agent_id: str
    version: str
    status: str  # healthy, degraded, unhealthy
    last_check: datetime
    response_time_ms: Optional[int]
    error_message: Optional[str]