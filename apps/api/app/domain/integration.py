"""
Integration domain models for multi-agent system
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import secrets
import string


class Integration:
    """Domain model for external service integration"""
    
    def __init__(
        self,
        user_id: UUID,
        name: str,
        type: str,
        config: Dict[str, Any],
        rate_limit_per_minute: int = 60,
        token: Optional[str] = None,
        webhook_url: Optional[str] = None,
        status: str = 'active',
        id: Optional[UUID] = None,
        last_used_at: Optional[datetime] = None,
        error_count: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.user_id = user_id
        self.name = name.strip()
        self.type = type.lower().strip()
        self.config = config
        self.rate_limit_per_minute = rate_limit_per_minute
        self.token = token or self._generate_token()
        self.webhook_url = webhook_url or f"/webhook/{self.id}"
        self.status = status
        self.last_used_at = last_used_at
        self.error_count = error_count
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        self._validate()
    
    def _validate(self):
        """Validate integration data"""
        if not self.name:
            raise ValueError("Integration name cannot be empty")
        
        allowed_types = [
            'whatsapp', 'telegram', 'zapier', 'n8n', 'make', 
            'gmail', 'supabase', 'generic'
        ]
        if self.type not in allowed_types:
            raise ValueError(f"Integration type must be one of: {', '.join(allowed_types)}")
        
        allowed_statuses = ['active', 'inactive', 'error', 'expired']
        if self.status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        
        if self.rate_limit_per_minute <= 0:
            raise ValueError("Rate limit must be positive")
        
        if not self.config:
            raise ValueError("Integration config cannot be empty")
        
        # Type-specific validation
        self._validate_config_by_type()
    
    def _validate_config_by_type(self):
        """Validate configuration based on integration type"""
        if self.type == 'whatsapp':
            required_fields = ['business_phone_number', 'access_token']
            for field in required_fields:
                if field not in self.config:
                    raise ValueError(f"WhatsApp integration requires '{field}' in config")
        
        elif self.type == 'telegram':
            if 'bot_token' not in self.config:
                raise ValueError("Telegram integration requires 'bot_token' in config")
        
        elif self.type == 'gmail':
            required_fields = ['client_id', 'client_secret', 'refresh_token']
            for field in required_fields:
                if field not in self.config:
                    raise ValueError(f"Gmail integration requires '{field}' in config")
        
        elif self.type == 'supabase':
            required_fields = ['project_url', 'api_key']
            for field in required_fields:
                if field not in self.config:
                    raise ValueError(f"Supabase integration requires '{field}' in config")
        
        elif self.type in ['zapier', 'n8n', 'make']:
            if 'webhook_url' not in self.config:
                raise ValueError(f"{self.type.title()} integration requires 'webhook_url' in config")
    
    def _generate_token(self) -> str:
        """Generate secure integration token"""
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(32))
        return f"renum_{token}"
    
    def regenerate_token(self) -> str:
        """Regenerate integration token"""
        old_token = self.token
        self.token = self._generate_token()
        self.updated_at = datetime.utcnow()
        return old_token
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update integration configuration"""
        # Merge with existing config
        self.config.update(new_config)
        self.updated_at = datetime.utcnow()
        
        # Re-validate after update
        self._validate_config_by_type()
    
    def activate(self):
        """Activate the integration"""
        if self.status == 'error':
            self.error_count = 0
        self.status = 'active'
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Deactivate the integration"""
        self.status = 'inactive'
        self.updated_at = datetime.utcnow()
    
    def mark_error(self, error_message: str):
        """Mark integration as having an error"""
        self.status = 'error'
        self.error_count += 1
        self.updated_at = datetime.utcnow()
    
    def mark_used(self):
        """Mark integration as recently used"""
        self.last_used_at = datetime.utcnow()
    
    def is_rate_limited(self, current_requests: int) -> bool:
        """Check if integration is currently rate limited"""
        return current_requests >= self.rate_limit_per_minute
    
    def is_healthy(self) -> bool:
        """Check if integration is healthy"""
        return self.status == 'active' and self.error_count < 5
    
    def get_webhook_endpoint(self, base_url: str) -> str:
        """Get full webhook endpoint URL"""
        return f"{base_url.rstrip('/')}{self.webhook_url}"
    
    def supports_webhooks(self) -> bool:
        """Check if integration type supports webhooks"""
        webhook_supported_types = ['whatsapp', 'telegram', 'zapier', 'n8n', 'make']
        return self.type in webhook_supported_types
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
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
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'error_count': self.error_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WebhookLog:
    """Domain model for webhook log entry"""
    
    def __init__(
        self,
        integration_id: UUID,
        method: str,
        headers: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.integration_id = integration_id
        self.request_id = request_id or str(uuid4())
        self.method = method.upper()
        self.headers = headers or {}
        self.payload = payload or {}
        self.response_status = response_status
        self.response_body = response_body or {}
        self.processing_time_ms = processing_time_ms
        self.error_message = error_message
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.created_at = created_at or datetime.utcnow()
        
        self._validate()
    
    def _validate(self):
        """Validate webhook log data"""
        allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if self.method not in allowed_methods:
            raise ValueError(f"Method must be one of: {', '.join(allowed_methods)}")
        
        if self.response_status is not None:
            if not (100 <= self.response_status <= 599):
                raise ValueError("Response status must be a valid HTTP status code")
    
    def is_successful(self) -> bool:
        """Check if webhook processing was successful"""
        return (
            self.response_status is not None and
            200 <= self.response_status < 300 and
            self.error_message is None
        )
    
    def is_client_error(self) -> bool:
        """Check if webhook had a client error (4xx)"""
        return (
            self.response_status is not None and
            400 <= self.response_status < 500
        )
    
    def is_server_error(self) -> bool:
        """Check if webhook had a server error (5xx)"""
        return (
            self.response_status is not None and
            500 <= self.response_status < 600
        )
    
    def mask_sensitive_data(self):
        """Mask sensitive data in headers and payload"""
        # Mask sensitive headers
        sensitive_headers = ['authorization', 'x-api-key', 'x-auth-token']
        for header in sensitive_headers:
            if header in self.headers:
                self.headers[header] = '***MASKED***'
        
        # Mask sensitive payload fields
        sensitive_fields = ['password', 'token', 'secret', 'key', 'credential']
        for field in sensitive_fields:
            if field in self.payload:
                self.payload[field] = '***MASKED***'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
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
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class IntegrationAnalytics:
    """Domain model for integration analytics"""
    
    def __init__(
        self,
        integration_id: UUID,
        date: date,
        total_requests: int = 0,
        successful_requests: int = 0,
        failed_requests: int = 0,
        avg_response_time_ms: Optional[Decimal] = None,
        total_cost: Optional[Decimal] = None,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.integration_id = integration_id
        self.date = date
        self.total_requests = total_requests
        self.successful_requests = successful_requests
        self.failed_requests = failed_requests
        self.avg_response_time_ms = avg_response_time_ms
        self.total_cost = total_cost or Decimal('0')
        self.created_at = created_at or datetime.utcnow()
        
        self._validate()
    
    def _validate(self):
        """Validate analytics data"""
        if self.total_requests < 0:
            raise ValueError("Total requests cannot be negative")
        
        if self.successful_requests < 0:
            raise ValueError("Successful requests cannot be negative")
        
        if self.failed_requests < 0:
            raise ValueError("Failed requests cannot be negative")
        
        if self.successful_requests + self.failed_requests > self.total_requests:
            raise ValueError("Sum of successful and failed requests cannot exceed total")
        
        if self.avg_response_time_ms is not None and self.avg_response_time_ms < 0:
            raise ValueError("Average response time cannot be negative")
        
        if self.total_cost < 0:
            raise ValueError("Total cost cannot be negative")
    
    def add_request(
        self,
        is_successful: bool,
        response_time_ms: Optional[int] = None,
        cost: Optional[Decimal] = None
    ):
        """Add a request to the analytics"""
        self.total_requests += 1
        
        if is_successful:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Update average response time
        if response_time_ms is not None:
            if self.avg_response_time_ms is None:
                self.avg_response_time_ms = Decimal(str(response_time_ms))
            else:
                # Calculate new average
                total_time = self.avg_response_time_ms * (self.total_requests - 1)
                total_time += Decimal(str(response_time_ms))
                self.avg_response_time_ms = total_time / self.total_requests
        
        # Add cost
        if cost is not None:
            self.total_cost += cost
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def get_error_rate(self) -> float:
        """Calculate error rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'id': str(self.id),
            'integration_id': str(self.integration_id),
            'date': self.date.isoformat(),
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'avg_response_time_ms': str(self.avg_response_time_ms) if self.avg_response_time_ms else None,
            'total_cost': str(self.total_cost),
            'success_rate': self.get_success_rate(),
            'error_rate': self.get_error_rate(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class IntegrationType:
    """Domain model for integration type configuration"""
    
    def __init__(
        self,
        type: str,
        display_name: str,
        description: str,
        config_schema: Dict[str, Any],
        webhook_supported: bool = False,
        oauth_supported: bool = False,
        api_key_supported: bool = False,
        documentation_url: Optional[str] = None,
        is_active: bool = True
    ):
        self.type = type.lower().strip()
        self.display_name = display_name.strip()
        self.description = description.strip()
        self.config_schema = config_schema
        self.webhook_supported = webhook_supported
        self.oauth_supported = oauth_supported
        self.api_key_supported = api_key_supported
        self.documentation_url = documentation_url
        self.is_active = is_active
        
        self._validate()
    
    def _validate(self):
        """Validate integration type data"""
        if not self.type:
            raise ValueError("Integration type cannot be empty")
        
        if not self.display_name:
            raise ValueError("Display name cannot be empty")
        
        if not self.description:
            raise ValueError("Description cannot be empty")
        
        if not self.config_schema:
            raise ValueError("Config schema cannot be empty")
        
        # Validate that at least one authentication method is supported
        if not (self.oauth_supported or self.api_key_supported):
            raise ValueError("At least one authentication method must be supported")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate a configuration against this type's schema"""
        # This would typically use a JSON schema validator
        # For now, we'll do basic validation
        
        if 'required' in self.config_schema:
            required_fields = self.config_schema['required']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Required field '{field}' missing from config")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'type': self.type,
            'display_name': self.display_name,
            'description': self.description,
            'config_schema': self.config_schema,
            'webhook_supported': self.webhook_supported,
            'oauth_supported': self.oauth_supported,
            'api_key_supported': self.api_key_supported,
            'documentation_url': self.documentation_url,
            'is_active': self.is_active
        }