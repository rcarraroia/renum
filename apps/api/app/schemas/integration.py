"""
Integration-related Pydantic schemas for multi-agent system
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator, root_validator


class IntegrationConfigBase(BaseModel):
    """Base configuration for integrations"""
    pass


class WhatsAppConfig(IntegrationConfigBase):
    """WhatsApp Business API configuration"""
    business_phone_number: str = Field(..., description="WhatsApp Business phone number")
    access_token: str = Field(..., description="WhatsApp Business API access token")
    webhook_verify_token: str = Field(..., description="Webhook verification token")
    
    @validator('business_phone_number')
    def validate_phone_number(cls, v):
        # Remove non-digits and validate format
        digits_only = ''.join(filter(str.isdigit, v))
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must be between 10 and 15 digits')
        return v


class TelegramConfig(IntegrationConfigBase):
    """Telegram Bot API configuration"""
    bot_token: str = Field(..., description="Telegram bot token")
    webhook_secret: Optional[str] = Field(None, description="Webhook secret for security")
    
    @validator('bot_token')
    def validate_bot_token(cls, v):
        if not v or ':' not in v:
            raise ValueError('Invalid Telegram bot token format')
        return v


class ZapierConfig(IntegrationConfigBase):
    """Zapier webhook configuration"""
    webhook_url: str = Field(..., description="Zapier webhook URL")
    secret_key: Optional[str] = Field(None, description="Secret key for webhook validation")
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        if not v.startswith('https://hooks.zapier.com/'):
            raise ValueError('Invalid Zapier webhook URL')
        return v


class N8nConfig(IntegrationConfigBase):
    """n8n webhook configuration"""
    webhook_url: str = Field(..., description="n8n webhook URL")
    api_key: Optional[str] = Field(None, description="n8n API key")
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Invalid webhook URL format')
        return v


class MakeConfig(IntegrationConfigBase):
    """Make (Integromat) webhook configuration"""
    webhook_url: str = Field(..., description="Make webhook URL")
    scenario_id: Optional[str] = Field(None, description="Make scenario ID")
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        if not v.startswith('https://hook.'):
            raise ValueError('Invalid Make webhook URL')
        return v


class GmailConfig(IntegrationConfigBase):
    """Gmail API configuration"""
    client_id: str = Field(..., description="Google OAuth client ID")
    client_secret: str = Field(..., description="Google OAuth client secret")
    refresh_token: str = Field(..., description="OAuth refresh token")
    
    @validator('client_id')
    def validate_client_id(cls, v):
        if not v.endswith('.apps.googleusercontent.com'):
            raise ValueError('Invalid Google client ID format')
        return v


class SupabaseConfig(IntegrationConfigBase):
    """Supabase database configuration"""
    project_url: str = Field(..., description="Supabase project URL")
    api_key: str = Field(..., description="Supabase API key")
    service_role_key: Optional[str] = Field(None, description="Supabase service role key")
    
    @validator('project_url')
    def validate_project_url(cls, v):
        if not v.startswith('https://') or not v.endswith('.supabase.co'):
            raise ValueError('Invalid Supabase project URL')
        return v


class GenericConfig(IntegrationConfigBase):
    """Generic integration configuration"""
    base_url: str = Field(..., description="Base URL for the API")
    api_key: Optional[str] = Field(None, description="API key")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")
    auth_type: Optional[str] = Field('api_key', description="Authentication type")
    
    @validator('base_url')
    def validate_base_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Invalid base URL format')
        return v


# Union type for all integration configurations
IntegrationConfig = Union[
    WhatsAppConfig,
    TelegramConfig,
    ZapierConfig,
    N8nConfig,
    MakeConfig,
    GmailConfig,
    SupabaseConfig,
    GenericConfig
]


class CreateIntegrationSchema(BaseModel):
    """Schema for creating new integration"""
    name: str = Field(..., description="Integration name")
    type: str = Field(..., description="Integration type")
    config: Dict[str, Any] = Field(..., description="Integration configuration")
    rate_limit_per_minute: Optional[int] = Field(60, description="Rate limit per minute")
    
    @validator('type')
    def validate_type(cls, v):
        allowed_types = [
            'whatsapp', 'telegram', 'zapier', 'n8n', 'make', 
            'gmail', 'supabase', 'generic'
        ]
        if v not in allowed_types:
            raise ValueError(f'Integration type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Integration name must be at least 3 characters')
        return v.strip()


class UpdateIntegrationSchema(BaseModel):
    """Schema for updating existing integration"""
    name: Optional[str] = Field(None, description="Integration name")
    config: Optional[Dict[str, Any]] = Field(None, description="Integration configuration")
    rate_limit_per_minute: Optional[int] = Field(None, description="Rate limit per minute")
    status: Optional[str] = Field(None, description="Integration status")
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['active', 'inactive', 'error', 'expired']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v


class IntegrationSchema(BaseModel):
    """Complete integration schema for API responses"""
    id: UUID
    user_id: UUID
    name: str
    type: str
    config: Dict[str, Any]
    token: str
    webhook_url: Optional[str] = None
    status: str
    rate_limit_per_minute: int
    last_used_at: Optional[datetime] = None
    error_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class IntegrationDetailSchema(IntegrationSchema):
    """Detailed integration schema with analytics"""
    analytics: Optional[Dict[str, Any]] = Field(None, description="Integration analytics")
    recent_logs: Optional[List[Dict[str, Any]]] = Field(None, description="Recent webhook logs")
    health_status: Optional[str] = Field(None, description="Health check status")


class IntegrationListSchema(BaseModel):
    """Schema for integration list responses"""
    integrations: List[IntegrationSchema]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class WebhookLogSchema(BaseModel):
    """Schema for webhook log entries"""
    id: UUID
    integration_id: UUID
    request_id: Optional[str] = None
    method: str
    headers: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    response_status: Optional[int] = None
    response_body: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class IntegrationAnalyticsSchema(BaseModel):
    """Schema for integration analytics"""
    integration_id: UUID
    date: date
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
            UUID: str,
            Decimal: str
        }


class IntegrationHealthCheck(BaseModel):
    """Schema for integration health check"""
    integration_id: UUID
    status: str = Field(..., description="Status: healthy, degraded, unhealthy")
    last_check: datetime
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    checks_performed: Dict[str, bool] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class RegenerateTokenSchema(BaseModel):
    """Schema for token regeneration request"""
    integration_id: UUID
    reason: Optional[str] = Field(None, description="Reason for token regeneration")


class IntegrationTypeSchema(BaseModel):
    """Schema for integration type configuration"""
    type: str
    display_name: str
    description: str
    config_schema: Dict[str, Any]
    webhook_supported: bool = False
    oauth_supported: bool = False
    api_key_supported: bool = False
    documentation_url: Optional[str] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class WebhookPayloadSchema(BaseModel):
    """Schema for incoming webhook payloads"""
    integration_id: UUID
    payload: Dict[str, Any]
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    
    class Config:
        json_encoders = {
            UUID: str
        }


class IntegrationTestSchema(BaseModel):
    """Schema for testing integration connectivity"""
    integration_id: UUID
    test_type: str = Field(..., description="Type of test to perform")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Test data payload")
    
    @validator('test_type')
    def validate_test_type(cls, v):
        allowed_types = ['connectivity', 'webhook', 'authentication', 'full']
        if v not in allowed_types:
            raise ValueError(f'Test type must be one of: {", ".join(allowed_types)}')
        return v


class IntegrationTestResult(BaseModel):
    """Schema for integration test results"""
    integration_id: UUID
    test_type: str
    success: bool
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    tested_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }