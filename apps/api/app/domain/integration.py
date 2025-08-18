"""
Domain models para integrações e conexões
Entidades de negócio com lógica de domínio
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4


class Connection:
    """Entidade de domínio para conexão BYOC"""
    
    def __init__(
        self,
        tenant_id: UUID,
        service_name: str,
        connection_type: str,
        credentials: Dict[str, Any],
        scopes: Optional[List[str]] = None,
        status: str = "active",
        expires_at: Optional[datetime] = None,
        id: Optional[UUID] = None,
        last_validated: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.tenant_id = tenant_id
        self.service_name = service_name
        self.connection_type = connection_type
        self.credentials = credentials
        self.scopes = scopes or []
        self.status = status
        self.expires_at = expires_at
        self.last_validated = last_validated
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Validar na criação
        self._validate()
    
    def _validate(self):
        """Validar regras de negócio da conexão"""
        allowed_types = [
            'oauth', 'api_key', 'database', 'whatsapp', 
            'telegram', 'gmail', 'supabase', 'custom'
        ]
        if self.connection_type not in allowed_types:
            raise ValueError(f"Tipo de conexão inválido: {self.connection_type}")
        
        allowed_statuses = ['active', 'inactive', 'expired', 'error']
        if self.status not in allowed_statuses:
            raise ValueError(f"Status inválido: {self.status}")
        
        if not self.credentials:
            raise ValueError("Credenciais são obrigatórias")
    
    def is_expired(self) -> bool:
        """Verificar se conexão está expirada"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def days_until_expiration(self) -> Optional[int]:
        """Dias até expiração"""
        if not self.expires_at:
            return None
        
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def needs_validation(self, validation_interval_hours: int = 24) -> bool:
        """Verificar se precisa de validação"""
        if not self.last_validated:
            return True
        
        threshold = datetime.utcnow() - timedelta(hours=validation_interval_hours)
        return self.last_validated < threshold
    
    def activate(self):
        """Ativar conexão"""
        if self.is_expired():
            raise ValueError("Conexão expirada não pode ser ativada")
        
        self.status = 'active'
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Desativar conexão"""
        self.status = 'inactive'
        self.updated_at = datetime.utcnow()
    
    def mark_as_expired(self):
        """Marcar como expirada"""
        self.status = 'expired'
        self.updated_at = datetime.utcnow()
    
    def mark_as_error(self, error_message: Optional[str] = None):
        """Marcar como erro"""
        self.status = 'error'
        self.updated_at = datetime.utcnow()
        # Em implementação completa, salvaria error_message
    
    def update_credentials(self, new_credentials: Dict[str, Any]):
        """Atualizar credenciais"""
        self.credentials = new_credentials
        self.status = 'active'  # Reset status ao atualizar
        self.last_validated = None  # Forçar nova validação
        self.updated_at = datetime.utcnow()
    
    def mark_validated(self, success: bool = True):
        """Marcar como validada"""
        self.last_validated = datetime.utcnow()
        if success and self.status == 'error':
            self.status = 'active'
        elif not success:
            self.status = 'error'
        self.updated_at = datetime.utcnow()
    
    def supports_webhooks(self) -> bool:
        """Verificar se suporta webhooks"""
        webhook_types = ['whatsapp', 'telegram', 'custom', 'zapier', 'n8n', 'make']
        return self.connection_type in webhook_types
    
    def get_masked_credentials(self) -> Dict[str, Any]:
        """Obter credenciais mascaradas para resposta"""
        masked = {}
        for key, value in self.credentials.items():
            if any(sensitive in key.lower() for sensitive in ['token', 'secret', 'password', 'key']):
                if isinstance(value, str) and len(value) > 8:
                    masked[key] = value[:4] + '*' * (len(value) - 8) + value[-4:]
                else:
                    masked[key] = '***'
            else:
                masked[key] = value
        return masked
    
    def to_dict(self, mask_credentials: bool = True) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'service_name': self.service_name,
            'connection_type': self.connection_type,
            'credentials': self.get_masked_credentials() if mask_credentials else self.credentials,
            'scopes': self.scopes,
            'status': self.status,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_validated': self.last_validated.isoformat() if self.last_validated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Integration:
    """Entidade de domínio para integração (legacy - mantida para compatibilidade)"""
    
    def __init__(
        self,
        user_id: UUID,
        name: str,
        type: str,
        config: Dict[str, Any],
        rate_limit_per_minute: int = 60,
        token: Optional[str] = None,
        webhook_url: Optional[str] = None,
        status: str = "active",
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.user_id = user_id
        self.name = name
        self.type = type
        self.config = config
        self.rate_limit_per_minute = rate_limit_per_minute
        self.token = token or self._generate_token()
        self.webhook_url = webhook_url
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Validar na criação
        self._validate()
    
    def _validate(self):
        """Validar regras de negócio da integração"""
        allowed_types = ['whatsapp', 'telegram', 'zapier', 'n8n', 'make', 'gmail', 'supabase']
        if self.type not in allowed_types:
            raise ValueError(f"Tipo de integração inválido: {self.type}")
        
        allowed_statuses = ['active', 'inactive', 'error']
        if self.status not in allowed_statuses:
            raise ValueError(f"Status inválido: {self.status}")
    
    def _generate_token(self) -> str:
        """Gerar token único para integração"""
        return f"renum_{secrets.token_hex(16)}"
    
    def regenerate_token(self) -> str:
        """Regenerar token da integração"""
        old_token = self.token
        self.token = self._generate_token()
        self.updated_at = datetime.utcnow()
        return old_token
    
    def update_config(self, new_config: Dict[str, Any]):
        """Atualizar configuração"""
        self.config = new_config
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """Ativar integração"""
        self.status = 'active'
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Desativar integração"""
        self.status = 'inactive'
        self.updated_at = datetime.utcnow()
    
    def mark_error(self):
        """Marcar como erro"""
        self.status = 'error'
        self.updated_at = datetime.utcnow()
    
    def supports_webhooks(self) -> bool:
        """Verificar se suporta webhooks"""
        return self.type in ['whatsapp', 'telegram', 'zapier', 'n8n', 'make']
    
    def generate_webhook_url(self, base_url: str) -> str:
        """Gerar URL do webhook"""
        return f"{base_url}/webhook/{self.id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'name': self.name,
            'type': self.type,
            'config': self.config,
            'token': self.token,
            'webhook_url': self.webhook_url,
            'status': self.status,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WebhookLog:
    """Entidade para log de webhook"""
    
    def __init__(
        self,
        integration_id: UUID,
        method: str,
        headers: Dict[str, Any],
        payload: Dict[str, Any],
        response_status: int,
        response_body: Dict[str, Any],
        processing_time_ms: int,
        request_id: Optional[str] = None,
        error_message: Optional[str] = None,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.integration_id = integration_id
        self.request_id = request_id or secrets.token_hex(8)
        self.method = method
        self.headers = headers
        self.payload = payload
        self.response_status = response_status
        self.response_body = response_body
        self.processing_time_ms = processing_time_ms
        self.error_message = error_message
        self.created_at = created_at or datetime.utcnow()
    
    def is_successful(self) -> bool:
        """Verificar se webhook foi processado com sucesso"""
        return 200 <= self.response_status < 300
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'id': str(self.id),
            'integration_id': str(self.integration_id),
            'request_id': self.request_id,
            'method': self.method,
            'headers': self.headers,
            'payload': self.payload,
            'response_status': self.response_status,
            'response_body': self.response_body,
            'processing_time_ms': self.processing_time_ms,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class IntegrationAnalytics:
    """Entidade para analytics de integração"""
    
    def __init__(
        self,
        integration_id: UUID,
        date: datetime,
        total_requests: int = 0,
        successful_requests: int = 0,
        failed_requests: int = 0,
        avg_response_time_ms: float = 0.0,
        total_cost: float = 0.0,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.integration_id = integration_id
        self.date = date.date() if isinstance(date, datetime) else date
        self.total_requests = total_requests
        self.successful_requests = successful_requests
        self.failed_requests = failed_requests
        self.avg_response_time_ms = avg_response_time_ms
        self.total_cost = total_cost
        self.created_at = created_at or datetime.utcnow()
    
    @property
    def success_rate(self) -> float:
        """Taxa de sucesso"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def error_rate(self) -> float:
        """Taxa de erro"""
        return 100.0 - self.success_rate
    
    def add_request(self, success: bool, response_time_ms: int, cost: float = 0.0):
        """Adicionar requisição às métricas"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Atualizar média de tempo de resposta
        if self.total_requests == 1:
            self.avg_response_time_ms = response_time_ms
        else:
            self.avg_response_time_ms = (
                (self.avg_response_time_ms * (self.total_requests - 1) + response_time_ms) 
                / self.total_requests
            )
        
        self.total_cost += cost
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'id': str(self.id),
            'integration_id': str(self.integration_id),
            'date': self.date.isoformat(),
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'avg_response_time_ms': self.avg_response_time_ms,
            'total_cost': self.total_cost,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }