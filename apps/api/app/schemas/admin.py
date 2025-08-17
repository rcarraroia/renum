"""
Admin panel Pydantic schemas for multi-agent system
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class FeatureToggleSchema(BaseModel):
    """Schema for feature toggle configuration"""
    id: UUID
    feature_name: str
    description: str
    enabled_globally: bool = False
    tenant_rules: Dict[str, Any] = Field(default_factory=dict)
    rollout_percentage: int = Field(0, ge=0, le=100)
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class CreateFeatureToggleSchema(BaseModel):
    """Schema for creating feature toggle"""
    feature_name: str = Field(..., description="Unique feature name")
    description: str = Field(..., description="Feature description")
    enabled_globally: bool = Field(False, description="Enable for all tenants")
    tenant_rules: Optional[Dict[str, Any]] = Field(None, description="Tenant-specific rules")
    rollout_percentage: int = Field(0, ge=0, le=100, description="Rollout percentage")
    
    @validator('feature_name')
    def validate_feature_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Feature name must be alphanumeric with underscores or hyphens')
        return v.lower()


class UpdateFeatureToggleSchema(BaseModel):
    """Schema for updating feature toggle"""
    description: Optional[str] = None
    enabled_globally: Optional[bool] = None
    tenant_rules: Optional[Dict[str, Any]] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)


class SystemKeySchema(BaseModel):
    """Schema for system keys (public keys only)"""
    id: UUID
    key_id: str
    key_type: str
    public_key: str
    status: str
    expires_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    
    # Note: private_key_hash is intentionally excluded for security
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class CreateSystemKeySchema(BaseModel):
    """Schema for creating system key"""
    key_id: str = Field(..., description="Unique key identifier")
    key_type: str = Field('RSA256', description="Key type")
    public_key: str = Field(..., description="Public key in PEM format")
    private_key_hash: str = Field(..., description="Hash of private key for verification")
    expires_at: Optional[datetime] = Field(None, description="Key expiration time")
    
    @validator('key_id')
    def validate_key_id(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Key ID must be alphanumeric with hyphens or underscores')
        return v


class AuditLogSchema(BaseModel):
    """Schema for audit log entries"""
    id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class SystemMetricsSchema(BaseModel):
    """Schema for system-wide metrics"""
    total_users: int = 0
    active_users_24h: int = 0
    total_agents: int = 0
    approved_agents: int = 0
    total_integrations: int = 0
    active_integrations: int = 0
    total_executions_24h: int = 0
    successful_executions_24h: int = 0
    failed_executions_24h: int = 0
    avg_execution_time_ms: Optional[float] = None
    total_webhook_requests_24h: int = 0
    system_health_score: float = Field(..., ge=0, le=100)
    
    @property
    def success_rate_24h(self) -> float:
        if self.total_executions_24h == 0:
            return 0.0
        return (self.successful_executions_24h / self.total_executions_24h) * 100


class UserManagementSchema(BaseModel):
    """Schema for user management"""
    id: UUID
    email: str
    role: str
    status: str
    last_sign_in: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Additional computed fields
    total_integrations: Optional[int] = None
    total_executions: Optional[int] = None
    last_activity: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class UpdateUserRoleSchema(BaseModel):
    """Schema for updating user role"""
    user_id: UUID
    new_role: str = Field(..., description="New user role")
    reason: Optional[str] = Field(None, description="Reason for role change")
    
    @validator('new_role')
    def validate_role(cls, v):
        allowed_roles = ['user', 'admin', 'superadmin']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v


class SystemHealthCheck(BaseModel):
    """Schema for system health check"""
    component: str
    status: str = Field(..., description="Status: healthy, degraded, unhealthy")
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    last_check: datetime
    uptime_percentage: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemConfiguration(BaseModel):
    """Schema for system configuration"""
    config_key: str
    config_value: Any
    description: str
    is_sensitive: bool = False
    updated_by: Optional[UUID] = None
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class DataPurgeRequest(BaseModel):
    """Schema for data purge request"""
    tenant_id: Optional[UUID] = Field(None, description="Specific tenant ID")
    entity_type: str = Field(..., description="Type of entity to purge")
    before_date: datetime = Field(..., description="Purge data before this date")
    reason: str = Field(..., description="Reason for purge")
    dry_run: bool = Field(True, description="Perform dry run first")
    
    @validator('entity_type')
    def validate_entity_type(cls, v):
        allowed_types = [
            'webhook_logs', 'audit_logs', 'sandbox_executions', 
            'user_credentials', 'integration_analytics', 'all'
        ]
        if v not in allowed_types:
            raise ValueError(f'Entity type must be one of: {", ".join(allowed_types)}')
        return v


class DataPurgeResult(BaseModel):
    """Schema for data purge result"""
    request_id: UUID
    entity_type: str
    records_affected: int
    dry_run: bool
    success: bool
    error_message: Optional[str] = None
    executed_at: datetime
    executed_by: UUID
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class AdminDashboardData(BaseModel):
    """Schema for admin dashboard data"""
    system_metrics: SystemMetricsSchema
    health_checks: List[SystemHealthCheck]
    recent_audit_logs: List[AuditLogSchema]
    active_feature_toggles: List[FeatureToggleSchema]
    system_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class IntegrationOverview(BaseModel):
    """Schema for integration overview in admin panel"""
    total_integrations: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)
    top_users_by_integrations: List[Dict[str, Any]] = Field(default_factory=list)
    webhook_volume_24h: int = 0
    error_rate_24h: float = 0.0


class AgentOverview(BaseModel):
    """Schema for agent overview in admin panel"""
    total_agents: int = 0
    by_status: Dict[str, int] = Field(default_factory=dict)
    most_used_agents: List[Dict[str, Any]] = Field(default_factory=list)
    recent_approvals: List[Dict[str, Any]] = Field(default_factory=list)
    pending_approvals: int = 0


class ExecutionOverview(BaseModel):
    """Schema for execution overview in admin panel"""
    total_executions_24h: int = 0
    success_rate_24h: float = 0.0
    avg_execution_time_ms: Optional[float] = None
    most_active_users: List[Dict[str, Any]] = Field(default_factory=list)
    execution_trends: List[Dict[str, Any]] = Field(default_factory=list)


class SystemAlert(BaseModel):
    """Schema for system alerts"""
    id: UUID
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    title: str
    message: str
    component: Optional[str] = None
    resolved: bool = False
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    @validator('severity')
    def validate_severity(cls, v):
        allowed_severities = ['low', 'medium', 'high', 'critical']
        if v not in allowed_severities:
            raise ValueError(f'Severity must be one of: {", ".join(allowed_severities)}')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class CreateSystemAlert(BaseModel):
    """Schema for creating system alert"""
    alert_type: str
    severity: str
    title: str
    message: str
    component: Optional[str] = None


class BulkOperationRequest(BaseModel):
    """Schema for bulk operations"""
    operation: str = Field(..., description="Operation to perform")
    entity_type: str = Field(..., description="Type of entities")
    entity_ids: List[UUID] = Field(..., description="List of entity IDs")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_operations = ['approve', 'reject', 'activate', 'deactivate', 'delete']
        if v not in allowed_operations:
            raise ValueError(f'Operation must be one of: {", ".join(allowed_operations)}')
        return v


class BulkOperationResult(BaseModel):
    """Schema for bulk operation result"""
    operation: str
    entity_type: str
    total_requested: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    executed_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }