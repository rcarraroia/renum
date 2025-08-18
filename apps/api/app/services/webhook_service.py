"""
Webhook Service for processing incoming webhooks
Handles webhook validation, processing, and routing with platform-specific processors
"""

import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from app.domain.integration import Connection
from app.services.integration_service import IntegrationService
from app.repositories.integration_repository import IntegrationRepository
from app.services.webhook_processors import (
    BaseWebhookProcessor,
    WhatsAppWebhookProcessor,
    TelegramWebhookProcessor,
    ZapierWebhookProcessor,
    N8nWebhookProcessor,
    MakeWebhookProcessor
)


class WebhookService:
    """Service for processing incoming webhooks with platform-specific processors"""
    
    def __init__(
        self, 
        integration_service: Optional[IntegrationService] = None,
        integration_repository: Optional[IntegrationRepository] = None
    ):
        self.integration_service = integration_service or IntegrationService()
        self.integration_repo = integration_repository or IntegrationRepository()
        
        # Initialize platform-specific processors
        self.processors = {
            'whatsapp': WhatsAppWebhookProcessor(),
            'telegram': TelegramWebhookProcessor(),
            'zapier': ZapierWebhookProcessor(),
            'n8n': N8nWebhookProcessor(),
            'make': MakeWebhookProcessor()
        }
    
    async def validate_webhook_token(self, token: str, connection_id: UUID) -> Optional[Connection]:
        """Validate webhook token and return associated connection"""
        
        return await self.integration_service.validate_webhook_token(token, connection_id)
    
    async def check_rate_limit(self, connection: Connection, ip_address: str) -> Dict[str, Any]:
        """Check rate limiting for webhook requests"""
        
        # Use connection-specific rate limit or default
        rate_limit = getattr(connection, 'rate_limit_per_minute', 60)
        
        return await self.integration_service.check_rate_limit(connection.id, rate_limit)
    
    async def process_webhook(
        self,
        connection: Connection,
        payload: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """Process incoming webhook with platform-specific processor"""
        
        start_time = datetime.utcnow()
        
        try:
            # Increment rate limit counter
            await self.integration_service.increment_rate_limit(connection.id)
            
            # Get appropriate processor for connection type
            processor = self.processors.get(connection.connection_type)
            
            if processor:
                # Use platform-specific processor
                result = await processor.process_webhook(
                    connection=connection,
                    payload=payload,
                    metadata={
                        'ip_address': ip_address,
                        'user_agent': user_agent
                    }
                )
                
                # Convert processor result to service format
                service_result = {
                    'success': result.success,
                    'data': {
                        'processed_events': result.processed_events,
                        'platform': connection.connection_type,
                        'processor_metadata': result.metadata
                    },
                    'execution_time_ms': result.execution_time_ms,
                    'error': result.error_message
                }
            else:
                # Fallback to generic processing
                service_result = await self.integration_service.process_webhook(
                    connection=connection,
                    payload=payload,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            # Log webhook processing
            await self._log_webhook_request(
                connection=connection,
                payload=payload,
                result=service_result,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return service_result
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            error_result = {
                'success': False,
                'error': str(e),
                'execution_time_ms': execution_time
            }
            
            # Log error
            await self._log_webhook_request(
                connection=connection,
                payload=payload,
                result=error_result,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return error_result
    
    async def verify_webhook_signature(
        self,
        connection: Connection,
        payload_body: str,
        signature: str
    ) -> bool:
        """Verify webhook signature for security"""
        
        if connection.connection_type == 'whatsapp':
            return self._verify_whatsapp_signature(connection, payload_body, signature)
        elif connection.connection_type == 'telegram':
            return self._verify_telegram_signature(connection, payload_body, signature)
        else:
            return self._verify_generic_signature(connection, payload_body, signature)
    
    async def handle_webhook_verification(
        self,
        connection: Connection,
        verify_token: str,
        challenge: str
    ) -> Optional[str]:
        """Handle webhook verification challenge (for platforms like WhatsApp)"""
        
        if connection.connection_type == 'whatsapp':
            expected_token = connection.credentials.get('webhook_verify_token')
            if verify_token == expected_token:
                return challenge
        
        return None
    
    async def get_webhook_logs(
        self,
        connection_id: UUID,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get webhook logs for a connection"""
        
        # Verify connection ownership
        connection = await self.integration_service.get_connection_by_id(connection_id, tenant_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # This would query webhook_logs table
        # For now, return mock data
        logs = []
        for i in range(min(limit, 10)):
            logs.append({
                'id': f"log_{i}",
                'connection_id': str(connection_id),
                'timestamp': datetime.utcnow().isoformat(),
                'method': 'POST',
                'status_code': 200 if i % 5 != 0 else 400,
                'processing_time_ms': 150 + i * 10,
                'payload_size': 1024 + i * 100,
                'success': i % 5 != 0
            })
        
        return logs
    
    async def get_webhook_stats(
        self,
        connection_id: UUID,
        tenant_id: UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get webhook statistics for a connection"""
        
        # Verify connection ownership
        connection = await self.integration_service.get_connection_by_id(connection_id, tenant_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # This would aggregate from webhook_logs table
        # For now, return mock stats
        return {
            'connection_id': str(connection_id),
            'period_days': days,
            'total_requests': 1250,
            'successful_requests': 1180,
            'failed_requests': 70,
            'success_rate': 94.4,
            'avg_response_time_ms': 245.5,
            'requests_per_day': 178.6,
            'peak_hour': '14:00',
            'most_common_errors': [
                {'error': 'Invalid payload', 'count': 25},
                {'error': 'Rate limit exceeded', 'count': 20},
                {'error': 'Authentication failed', 'count': 15}
            ]
        }
    
    async def retry_failed_webhook(
        self,
        webhook_log_id: str,
        connection_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Retry a failed webhook processing"""
        
        # Verify connection ownership
        connection = await self.integration_service.get_connection_by_id(connection_id, tenant_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # This would retrieve the original webhook data and retry processing
        # For now, return mock retry result
        return {
            'webhook_log_id': webhook_log_id,
            'retry_success': True,
            'retry_timestamp': datetime.utcnow().isoformat(),
            'original_error': 'Rate limit exceeded',
            'retry_result': 'Successfully processed on retry'
        }
    
    async def get_supported_platforms(self) -> List[Dict[str, Any]]:
        """Get list of supported webhook platforms"""
        
        platforms = []
        
        for platform_name, processor in self.processors.items():
            event_types = await processor.get_supported_event_types()
            
            platforms.append({
                'platform': platform_name,
                'processor_class': processor.__class__.__name__,
                'supported_event_types': event_types,
                'description': self._get_platform_description(platform_name)
            })
        
        return platforms
    
    async def validate_connection_for_platform(
        self,
        connection: Connection
    ) -> Dict[str, Any]:
        """Validate connection configuration for its platform"""
        
        processor = self.processors.get(connection.connection_type)
        
        if not processor:
            return {
                'valid': False,
                'error': f'No processor available for platform: {connection.connection_type}'
            }
        
        try:
            is_valid = await processor.validate_connection_config(connection)
            
            return {
                'valid': is_valid,
                'platform': connection.connection_type,
                'processor': processor.__class__.__name__
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'platform': connection.connection_type
            }
    
    async def get_platform_capabilities(self, platform: str) -> Dict[str, Any]:
        """Get capabilities of a specific platform processor"""
        
        processor = self.processors.get(platform)
        
        if not processor:
            return {
                'platform': platform,
                'available': False,
                'error': 'Platform not supported'
            }
        
        event_types = await processor.get_supported_event_types()
        
        return {
            'platform': platform,
            'available': True,
            'processor_class': processor.__class__.__name__,
            'supported_event_types': event_types,
            'description': self._get_platform_description(platform),
            'validation_required': True
        }
    
    def _get_platform_description(self, platform: str) -> str:
        """Get description for platform"""
        
        descriptions = {
            'whatsapp': 'WhatsApp Business API webhook processor for handling messages, status updates, and account alerts',
            'telegram': 'Telegram Bot API webhook processor for handling messages, commands, and inline queries',
            'zapier': 'Zapier webhook processor for handling automation triggers and form submissions',
            'n8n': 'n8n workflow webhook processor for handling workflow executions and data processing',
            'make': 'Make (Integromat) scenario webhook processor for handling scenario executions and data sync'
        }
        
        return descriptions.get(platform, f'Webhook processor for {platform} platform')
    
    # Private helper methods
    
    async def _log_webhook_request(
        self,
        connection: Connection,
        payload: Dict[str, Any],
        result: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ):
        """Log webhook request for audit and debugging"""
        
        log_entry = {
            'connection_id': str(connection.id),
            'tenant_id': str(connection.tenant_id),
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'payload_size': len(json.dumps(payload)),
            'success': result.get('success', False),
            'execution_time_ms': result.get('execution_time_ms', 0),
            'error': result.get('error') if not result.get('success') else None
        }
        
        # In real implementation, would save to webhook_logs table
        print(f"WEBHOOK LOG: {json.dumps(log_entry)}")
    
    def _verify_whatsapp_signature(
        self,
        connection: Connection,
        payload_body: str,
        signature: str
    ) -> bool:
        """Verify WhatsApp webhook signature"""
        
        app_secret = connection.credentials.get('app_secret')
        if not app_secret:
            return False
        
        # WhatsApp uses SHA256 HMAC
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # WhatsApp sends signature as 'sha256=<hash>'
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _verify_telegram_signature(
        self,
        connection: Connection,
        payload_body: str,
        signature: str
    ) -> bool:
        """Verify Telegram webhook signature"""
        
        webhook_secret = connection.credentials.get('webhook_secret')
        if not webhook_secret:
            return True  # Telegram doesn't require signature if no secret set
        
        # Telegram uses SHA256 HMAC
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _verify_generic_signature(
        self,
        connection: Connection,
        payload_body: str,
        signature: str
    ) -> bool:
        """Verify generic webhook signature"""
        
        secret = connection.credentials.get('webhook_secret')
        if not secret:
            return True  # No signature verification if no secret
        
        # Generic SHA256 HMAC
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


def get_webhook_service() -> WebhookService:
    """Dependency injection for webhook service"""
    return WebhookService()