"""
Schemas Pydantic para funcionalidades administrativas
Baseado nas tabelas de logs, métricas e billing do Supabase
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ExecutionLogSchema(BaseModel):
    """Schema para logs de execução"""
    
    id: UUID
    run_id: UUID
    agent_id: Optional[str]
    step_number: Optional[int]
    log_level: str
    message: str
    metadata: Dict[str, Any]
    timestamp: datetime
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validar nível de log"""
        allowed_levels = ['debug', 'info', 'warning', 'error', 'critical']
        if v.lower() not in allowed_levels:
            raise ValueError(f'Nível de log deve ser um de: {", ".join(allowed_levels)}')
        return v.lower()
    
    class Config:
        from_attributes = True


class CreateExecutionLogSchema(BaseModel):
    """Schema para criação de log de execução"""
    
    run_id: UUID = Field(..., description="ID da execução")
    agent_id: Optional[str] = Field(None, description="ID do agente")
    step_number: Optional[int] = Field(None, description="Número do passo")
    log_level: str = Field(default="info", description="Nível do log")
    message: str = Field(..., description="Mensagem do log")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")


class BillingMetricSchema(BaseModel):
    """Schema para métricas de billing"""
    
    id: UUID
    user_id: UUID
    run_id: Optional[UUID]
    metric_type: str
    agent_id: Optional[str]
    quantity: int
    cost_cents: int
    metadata: Dict[str, Any]
    created_at: datetime
    
    @property
    def cost_dollars(self) -> float:
        """Converter centavos para dólares"""
        return self.cost_cents / 100.0
    
    class Config:
        from_attributes = True


class CreateBillingMetricSchema(BaseModel):
    """Schema para criação de métrica de billing"""
    
    user_id: UUID = Field(..., description="ID do usuário")
    run_id: Optional[UUID] = Field(None, description="ID da execução")
    metric_type: str = Field(..., description="Tipo de métrica")
    agent_id: Optional[str] = Field(None, description="ID do agente")
    quantity: int = Field(default=1, description="Quantidade")
    cost_cents: int = Field(default=0, description="Custo em centavos")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados")
    
    @validator('metric_type')
    def validate_metric_type(cls, v):
        """Validar tipo de métrica"""
        allowed_types = [
            'agent_execution', 'api_call', 'storage_usage', 
            'bandwidth_usage', 'webhook_call', 'custom'
        ]
        if v not in allowed_types:
            raise ValueError(f'Tipo de métrica deve ser um de: {", ".join(allowed_types)}')
        return v


class SystemStatsSchema(BaseModel):
    """Schema para estatísticas do sistema"""
    
    total_users: int
    active_users_24h: int
    total_agents: int
    active_agents: int
    total_workflows: int
    total_executions: int
    executions_24h: int
    success_rate_24h: float
    avg_execution_time_ms: float
    total_cost_24h: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_users": 150,
                "active_users_24h": 45,
                "total_agents": 25,
                "active_agents": 18,
                "total_workflows": 89,
                "total_executions": 1250,
                "executions_24h": 156,
                "success_rate_24h": 94.5,
                "avg_execution_time_ms": 2340.5,
                "total_cost_24h": 12.45
            }
        }


class UserStatsSchema(BaseModel):
    """Schema para estatísticas de usuário"""
    
    user_id: UUID
    total_workflows: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    total_cost: float
    avg_execution_time_ms: float
    most_used_agents: List[Dict[str, Any]]
    last_activity: Optional[datetime]
    
    class Config:
        from_attributes = True


class AgentStatsSchema(BaseModel):
    """Schema para estatísticas de agente"""
    
    agent_id: str
    version: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    avg_execution_time_ms: float
    total_cost: float
    unique_users: int
    last_execution: Optional[datetime]
    error_rate: float
    
    class Config:
        from_attributes = True


class SystemHealthSchema(BaseModel):
    """Schema para saúde do sistema"""
    
    status: str  # healthy, degraded, unhealthy
    uptime_seconds: int
    database_status: str
    api_response_time_ms: float
    active_connections: int
    queue_size: int
    error_rate_1h: float
    memory_usage_percent: float
    cpu_usage_percent: float
    disk_usage_percent: float
    last_check: datetime
    
    @validator('status')
    def validate_status(cls, v):
        """Validar status de saúde"""
        allowed_statuses = ['healthy', 'degraded', 'unhealthy']
        if v not in allowed_statuses:
            raise ValueError(f'Status deve ser um de: {", ".join(allowed_statuses)}')
        return v


class FeatureToggleSchema(BaseModel):
    """Schema para feature toggles"""
    
    feature_name: str
    description: Optional[str]
    enabled_globally: bool
    tenant_rules: Dict[str, Any]
    rollout_percentage: int
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    @validator('rollout_percentage')
    def validate_rollout_percentage(cls, v):
        """Validar porcentagem de rollout"""
        if not 0 <= v <= 100:
            raise ValueError('Porcentagem de rollout deve estar entre 0 e 100')
        return v
    
    class Config:
        from_attributes = True


class CreateFeatureToggleSchema(BaseModel):
    """Schema para criação de feature toggle"""
    
    feature_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    enabled_globally: bool = Field(default=False)
    tenant_rules: Dict[str, Any] = Field(default_factory=dict)
    rollout_percentage: int = Field(default=0, ge=0, le=100)


class UpdateFeatureToggleSchema(BaseModel):
    """Schema para atualização de feature toggle"""
    
    description: Optional[str] = None
    enabled_globally: Optional[bool] = None
    tenant_rules: Optional[Dict[str, Any]] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)


class AuditLogSchema(BaseModel):
    """Schema para logs de auditoria"""
    
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class CreateAuditLogSchema(BaseModel):
    """Schema para criação de log de auditoria"""
    
    user_id: Optional[UUID] = None
    action: str = Field(..., description="Ação realizada")
    resource_type: str = Field(..., description="Tipo de recurso")
    resource_id: Optional[str] = Field(None, description="ID do recurso")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detalhes da ação")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class DataPurgeRequestSchema(BaseModel):
    """Schema para solicitação de purga de dados"""
    
    tenant_id: Optional[UUID] = Field(None, description="ID do tenant (opcional)")
    entity_type: str = Field(..., description="Tipo de entidade")
    before_date: datetime = Field(..., description="Purgar dados antes desta data")
    reason: str = Field(..., description="Motivo da purga")
    dry_run: bool = Field(default=True, description="Execução de teste")
    
    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validar tipo de entidade"""
        allowed_types = [
            'execution_logs', 'billing_metrics', 'audit_logs', 
            'workflow_runs', 'webhook_logs', 'all'
        ]
        if v not in allowed_types:
            raise ValueError(f'Tipo de entidade deve ser um de: {", ".join(allowed_types)}')
        return v


class DataPurgeResultSchema(BaseModel):
    """Schema para resultado de purga de dados"""
    
    request_id: UUID
    entity_type: str
    records_found: int
    records_purged: int
    dry_run: bool
    execution_time_ms: int
    purged_at: datetime
    details: Dict[str, Any]


class SystemConfigSchema(BaseModel):
    """Schema para configuração do sistema"""
    
    config_key: str
    config_value: Any
    description: Optional[str]
    is_sensitive: bool
    updated_by: Optional[UUID]
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UpdateSystemConfigSchema(BaseModel):
    """Schema para atualização de configuração do sistema"""
    
    config_value: Any = Field(..., description="Novo valor da configuração")
    description: Optional[str] = None


class MaintenanceModeSchema(BaseModel):
    """Schema para modo de manutenção"""
    
    enabled: bool
    message: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    allowed_users: List[UUID] = Field(default_factory=list)
    enabled_by: Optional[UUID] = None
    enabled_at: Optional[datetime] = None