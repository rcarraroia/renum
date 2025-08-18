"""
Schemas Pydantic para integrações e conexões
Baseado na estrutura real da tabela tenant_connections no Supabase
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ConnectionCredentialsSchema(BaseModel):
    """Schema base para credenciais de conexão"""
    pass


class OAuthCredentialsSchema(ConnectionCredentialsSchema):
    """Credenciais OAuth"""
    
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    scope: Optional[str] = None


class APIKeyCredentialsSchema(ConnectionCredentialsSchema):
    """Credenciais de API Key"""
    
    api_key: str
    api_secret: Optional[str] = None


class DatabaseCredentialsSchema(ConnectionCredentialsSchema):
    """Credenciais de banco de dados"""
    
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "require"


class WhatsAppCredentialsSchema(ConnectionCredentialsSchema):
    """Credenciais WhatsApp Business"""
    
    access_token: str
    business_phone_number: str
    webhook_verify_token: str
    app_id: str
    app_secret: str


class TelegramCredentialsSchema(ConnectionCredentialsSchema):
    """Credenciais Telegram Bot"""
    
    bot_token: str
    webhook_secret: Optional[str] = None


class GmailCredentialsSchema(ConnectionCredentialsSchema):
    """Credenciais Gmail API"""
    
    client_id: str
    client_secret: str
    refresh_token: str
    access_token: Optional[str] = None


class SupabaseCredentialsSchema(ConnectionCredentialsSchema):
    """Credenciais Supabase"""
    
    project_url: str
    anon_key: str
    service_role_key: Optional[str] = None


class CreateConnectionSchema(BaseModel):
    """Schema para criação de conexão"""
    
    service_name: str = Field(..., min_length=1, max_length=100, description="Nome do serviço")
    connection_type: str = Field(..., description="Tipo de conexão")
    credentials: Union[
        OAuthCredentialsSchema,
        APIKeyCredentialsSchema,
        DatabaseCredentialsSchema,
        WhatsAppCredentialsSchema,
        TelegramCredentialsSchema,
        GmailCredentialsSchema,
        SupabaseCredentialsSchema,
        Dict[str, Any]
    ] = Field(..., description="Credenciais da conexão")
    scopes: List[str] = Field(default_factory=list, description="Escopos de acesso")
    expires_at: Optional[datetime] = Field(None, description="Data de expiração")
    
    @validator('connection_type')
    def validate_connection_type(cls, v):
        """Validar tipos de conexão suportados"""
        allowed_types = [
            'oauth', 'api_key', 'database', 'whatsapp', 
            'telegram', 'gmail', 'supabase', 'custom'
        ]
        if v not in allowed_types:
            raise ValueError(f'Tipo de conexão deve ser um de: {", ".join(allowed_types)}')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "Gmail Principal",
                "connection_type": "gmail",
                "credentials": {
                    "client_id": "123456789.apps.googleusercontent.com",
                    "client_secret": "GOCSPX-...",
                    "refresh_token": "1//04..."
                },
                "scopes": ["https://www.googleapis.com/auth/gmail.send"]
            }
        }


class UpdateConnectionSchema(BaseModel):
    """Schema para atualização de conexão"""
    
    service_name: Optional[str] = Field(None, min_length=1, max_length=100)
    credentials: Optional[Dict[str, Any]] = None
    scopes: Optional[List[str]] = None
    status: Optional[str] = Field(None, regex="^(active|inactive|expired|error)$")
    expires_at: Optional[datetime] = None


class ConnectionSchema(BaseModel):
    """Schema completo de conexão (response)"""
    
    id: UUID
    tenant_id: UUID
    service_name: str
    connection_type: str
    credentials: Dict[str, Any]  # Sempre mascarado na resposta
    scopes: List[str]
    status: str
    expires_at: Optional[datetime]
    last_validated: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    @validator('credentials', pre=True)
    def mask_credentials(cls, v):
        """Mascarar credenciais sensíveis na resposta"""
        if isinstance(v, dict):
            masked = {}
            for key, value in v.items():
                if any(sensitive in key.lower() for sensitive in ['token', 'secret', 'password', 'key']):
                    if isinstance(value, str) and len(value) > 8:
                        masked[key] = value[:4] + '*' * (len(value) - 8) + value[-4:]
                    else:
                        masked[key] = '***'
                else:
                    masked[key] = value
            return masked
        return v
    
    class Config:
        from_attributes = True


class ConnectionTestSchema(BaseModel):
    """Schema para teste de conexão"""
    
    test_type: str = Field(..., description="Tipo de teste")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Dados para teste")
    
    @validator('test_type')
    def validate_test_type(cls, v):
        """Validar tipos de teste"""
        allowed_types = ['connectivity', 'authentication', 'permissions', 'full']
        if v not in allowed_types:
            raise ValueError(f'Tipo de teste deve ser um de: {", ".join(allowed_types)}')
        return v


class ConnectionTestResult(BaseModel):
    """Schema para resultado de teste de conexão"""
    
    connection_id: UUID
    test_type: str
    success: bool
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None
    tested_at: Optional[datetime] = None


class WebhookPayloadSchema(BaseModel):
    """Schema base para payloads de webhook"""
    
    timestamp: Optional[datetime] = None
    source: Optional[str] = None


class WhatsAppWebhookPayload(WebhookPayloadSchema):
    """Payload específico do WhatsApp"""
    
    object: str
    entry: List[Dict[str, Any]]


class TelegramWebhookPayload(WebhookPayloadSchema):
    """Payload específico do Telegram"""
    
    update_id: int
    message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None


class ZapierWebhookPayload(WebhookPayloadSchema):
    """Payload específico do Zapier"""
    
    data: Dict[str, Any]
    zap_id: Optional[str] = None


class N8nWebhookPayload(WebhookPayloadSchema):
    """Payload específico do n8n"""
    
    data: Dict[str, Any]
    workflow_id: Optional[str] = None


class MakeWebhookPayload(WebhookPayloadSchema):
    """Payload específico do Make (Integromat)"""
    
    data: Dict[str, Any]
    scenario_id: Optional[str] = None


class CustomWebhookPayload(WebhookPayloadSchema):
    """Payload genérico para webhooks customizados"""
    
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class WebhookResponse(BaseModel):
    """Schema para resposta de webhook"""
    
    success: bool
    data: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    message: Optional[str] = None


class WebhookErrorResponse(BaseModel):
    """Schema para resposta de erro de webhook"""
    
    error: str
    code: Optional[str] = None
    execution_time_ms: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class IntegrationAnalytics(BaseModel):
    """Schema para analytics de integração"""
    
    connection_id: UUID
    period_days: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time_ms: float
    total_cost: float
    daily_data: List[Dict[str, Any]]