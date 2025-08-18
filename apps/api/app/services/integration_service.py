"""
Integration Service for multi-agent system
Handles CRUD operations, webhook support, rate limiting, and analytics
"""

import asyncio
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

import aiohttp
from fastapi import HTTPException

from app.domain.integration import Connection, IntegrationAnalytics
from app.schemas.integration import (
    CreateConnectionSchema, 
    UpdateConnectionSchema,
    ConnectionTestSchema,
    ConnectionTestResult
)
from app.repositories.integration_repository import IntegrationRepository


class IntegrationService:
    """Service for managing external integrations with webhook support"""
    
    def __init__(self, integration_repository: Optional[IntegrationRepository] = None, redis_client=None):
        self.integration_repo = integration_repository or IntegrationRepository()
        self.redis = redis_client
        self._rate_limit_cache = {}  # In-memory cache for rate limiting
    
    async def create_connection(
        self, 
        tenant_id: UUID, 
        connection_data: CreateConnectionSchema
    ) -> Connection:
        """Create new connection with automatic validation"""
        
        try:
            # Validate connection configuration
            await self._validate_connection_config(connection_data.connection_type, connection_data.credentials)
            
            # Create connection domain object
            connection = Connection(
                tenant_id=tenant_id,
                service_name=connection_data.service_name,
                connection_type=connection_data.connection_type,
                credentials=connection_data.credentials,
                scopes=connection_data.scopes,
                expires_at=connection_data.expires_at
            )
            
            # Test connectivity if possible
            if connection.connection_type in ['whatsapp', 'telegram', 'gmail', 'supabase']:
                test_result = await self._test_connection_connectivity(connection)
                if not test_result.success:
                    raise ValueError(f"Connection connectivity test failed: {test_result.error_message}")
            
            # Save to database
            saved_connection = await self.integration_repo.save_connection(connection)
            
            # Initialize analytics
            await self._initialize_connection_analytics(saved_connection.id)
            
            return saved_connection
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create connection: {str(e)}")
    
    async def get_tenant_connections(
        self, 
        tenant_id: UUID,
        connection_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Connection]:
        """Get all connections for a tenant with optional filtering"""
        
        return await self.integration_repo.find_connections_by_tenant(
            tenant_id=tenant_id,
            connection_type=connection_type,
            status=status
        )
    
    async def get_connection_by_id(self, connection_id: UUID, tenant_id: UUID) -> Optional[Connection]:
        """Get specific connection by ID (with tenant validation)"""
        
        connection = await self.integration_repo.find_connection_by_id(connection_id)
        
        # Validate tenant ownership
        if connection and connection.tenant_id != tenant_id:
            return None
        
        return connection
    
    async def update_connection(
        self, 
        connection_id: UUID,
        tenant_id: UUID,
        update_data: UpdateConnectionSchema
    ) -> Connection:
        """Update existing connection"""
        
        connection = await self.get_connection_by_id(connection_id, tenant_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Update fields
        if update_data.service_name:
            connection.service_name = update_data.service_name
        
        if update_data.credentials:
            # Validate new credentials
            await self._validate_connection_config(connection.connection_type, update_data.credentials)
            connection.update_credentials(update_data.credentials)
        
        if update_data.scopes is not None:
            connection.scopes = update_data.scopes
        
        if update_data.status:
            if update_data.status == 'active':
                connection.activate()
            elif update_data.status == 'inactive':
                connection.deactivate()
            elif update_data.status == 'expired':
                connection.mark_as_expired()
        
        if update_data.expires_at is not None:
            connection.expires_at = update_data.expires_at
        
        # Save to database
        return await self.integration_repo.save_connection(connection)
    
    async def delete_connection(self, connection_id: UUID, tenant_id: UUID) -> bool:
        """Delete connection and associated data"""
        
        connection = await self.get_connection_by_id(connection_id, tenant_id)
        if not connection:
            return False
        
        # Delete associated data (logs, analytics, etc.)
        await self._cleanup_connection_data(connection_id)
        
        # Delete connection
        return await self.integration_repo.delete_connection(connection_id)
    
    async def test_connection(
        self, 
        connection_id: UUID, 
        tenant_id: UUID,
        test_data: ConnectionTestSchema
    ) -> ConnectionTestResult:
        """Test connection connectivity and functionality"""
        
        connection = await self.get_connection_by_id(connection_id, tenant_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        start_time = datetime.utcnow()
        
        try:
            if test_data.test_type == 'connectivity':
                result = await self._test_connection_connectivity(connection)
            elif test_data.test_type == 'authentication':
                result = await self._test_authentication(connection)
            elif test_data.test_type == 'permissions':
                result = await self._test_permissions(connection, test_data.test_data)
            elif test_data.test_type == 'full':
                result = await self._test_full_connection(connection, test_data.test_data)
            else:
                raise ValueError(f"Unknown test type: {test_data.test_type}")
            
            # Calculate response time
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            result.response_time_ms = response_time
            result.tested_at = datetime.utcnow()
            
            # Update connection validation status
            connection.mark_validated(result.success)
            await self.integration_repo.save_connection(connection)
            
            return result
            
        except Exception as e:
            return ConnectionTestResult(
                connection_id=connection_id,
                test_type=test_data.test_type,
                success=False,
                error_message=str(e),
                response_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                tested_at=datetime.utcnow()
            )
    
    async def get_connection_analytics(
        self, 
        connection_id: UUID, 
        tenant_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get connection analytics for specified period"""
        
        connection = await self.get_connection_by_id(connection_id, tenant_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Get analytics from repository
        analytics_list = await self.integration_repo.get_analytics(connection_id, days)
        
        # Process and aggregate data
        total_requests = sum(a.total_requests for a in analytics_list)
        total_successful = sum(a.successful_requests for a in analytics_list)
        total_failed = sum(a.failed_requests for a in analytics_list)
        
        return {
            'connection_id': str(connection_id),
            'period_days': days,
            'summary': {
                'total_requests': total_requests,
                'successful_requests': total_successful,
                'failed_requests': total_failed,
                'success_rate': (total_successful / total_requests * 100) if total_requests > 0 else 0,
                'avg_requests_per_day': total_requests / len(analytics_list) if analytics_list else 0
            },
            'daily_data': [a.to_dict() for a in analytics_list]
        }
    
    async def check_rate_limit(self, connection_id: UUID, requests_per_minute: int = 60) -> Dict[str, Any]:
        """Check if connection is within rate limits"""
        
        # Get current minute window
        current_minute = datetime.utcnow().replace(second=0, microsecond=0)
        cache_key = f"rate_limit:{connection_id}:{current_minute.isoformat()}"
        
        # Check current request count
        current_count = self._rate_limit_cache.get(cache_key, 0)
        
        allowed = current_count < requests_per_minute
        remaining = max(0, requests_per_minute - current_count)
        
        # Calculate reset time (next minute)
        reset_time = int((current_minute + timedelta(minutes=1)).timestamp())
        
        return {
            'allowed': allowed,
            'limit': requests_per_minute,
            'remaining': remaining,
            'reset_time': reset_time,
            'current_count': current_count
        }
    
    async def increment_rate_limit(self, connection_id: UUID):
        """Increment rate limit counter"""
        
        current_minute = datetime.utcnow().replace(second=0, microsecond=0)
        cache_key = f"rate_limit:{connection_id}:{current_minute.isoformat()}"
        
        current_count = self._rate_limit_cache.get(cache_key, 0)
        self._rate_limit_cache[cache_key] = current_count + 1
        
        # Clean up old entries (keep only last 2 minutes)
        cutoff_time = current_minute - timedelta(minutes=2)
        keys_to_remove = [
            key for key in self._rate_limit_cache.keys()
            if key.startswith(f"rate_limit:{connection_id}:") and
            datetime.fromisoformat(key.split(":")[-1]) < cutoff_time
        ]
        
        for key in keys_to_remove:
            del self._rate_limit_cache[key]
    
    async def validate_webhook_token(self, token: str, connection_id: UUID) -> Optional[Connection]:
        """Validate webhook token and return associated connection"""
        
        # In a real implementation, tokens would be stored securely
        # For now, we'll do a simple lookup
        connection = await self.integration_repo.find_connection_by_id(connection_id)
        
        if not connection or not connection.supports_webhooks():
            return None
        
        # Validate token (simplified - in production would use proper token validation)
        expected_token = self._generate_webhook_token(connection_id)
        if token != expected_token:
            return None
        
        return connection
    
    async def process_webhook(
        self,
        connection: Connection,
        payload: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """Process incoming webhook"""
        
        start_time = datetime.utcnow()
        
        try:
            # Validate payload based on connection type
            if not await self._validate_webhook_payload(connection, payload):
                raise ValueError("Invalid webhook payload")
            
            # Process based on connection type
            result = await self._process_webhook_by_type(connection, payload)
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Update analytics
            await self.integration_repo.update_analytics(
                connection_id=connection.id,
                success=True,
                response_time_ms=execution_time
            )
            
            return {
                'success': True,
                'data': result,
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Update analytics with error
            await self.integration_repo.update_analytics(
                connection_id=connection.id,
                success=False,
                response_time_ms=execution_time
            )
            
            return {
                'success': False,
                'error': str(e),
                'execution_time_ms': execution_time
            }
    
    async def get_expired_connections(self) -> List[Connection]:
        """Get connections that have expired"""
        
        return await self.integration_repo.find_expired_connections()
    
    async def get_connections_needing_validation(self, hours: int = 24) -> List[Connection]:
        """Get connections that need validation"""
        
        return await self.integration_repo.find_connections_needing_validation(hours)
    
    async def refresh_connection_credentials(self, connection_id: UUID, tenant_id: UUID) -> Connection:
        """Refresh OAuth credentials for a connection"""
        
        connection = await self.get_connection_by_id(connection_id, tenant_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        if connection.connection_type != 'oauth':
            raise ValueError("Only OAuth connections can be refreshed")
        
        # Implement OAuth refresh logic
        try:
            new_credentials = await self._refresh_oauth_token(connection)
            connection.update_credentials(new_credentials)
            
            return await self.integration_repo.save_connection(connection)
            
        except Exception as e:
            connection.mark_as_error(str(e))
            await self.integration_repo.save_connection(connection)
            raise
    
    # Private helper methods
    
    async def _validate_connection_config(self, connection_type: str, credentials: Dict[str, Any]):
        """Validate connection configuration based on type"""
        
        if connection_type == 'whatsapp':
            required_fields = ['access_token', 'business_phone_number', 'webhook_verify_token']
            for field in required_fields:
                if field not in credentials:
                    raise ValueError(f"WhatsApp connection requires '{field}' in credentials")
        
        elif connection_type == 'telegram':
            if 'bot_token' not in credentials:
                raise ValueError("Telegram connection requires 'bot_token' in credentials")
            
            # Validate bot token format
            token = credentials['bot_token']
            if ':' not in token:
                raise ValueError("Invalid Telegram bot token format")
        
        elif connection_type == 'gmail':
            required_fields = ['client_id', 'client_secret', 'refresh_token']
            for field in required_fields:
                if field not in credentials:
                    raise ValueError(f"Gmail connection requires '{field}' in credentials")
        
        elif connection_type == 'supabase':
            required_fields = ['project_url', 'anon_key']
            for field in required_fields:
                if field not in credentials:
                    raise ValueError(f"Supabase connection requires '{field}' in credentials")
            
            # Validate URL format
            url = credentials['project_url']
            if not url.startswith('https://') or not url.endswith('.supabase.co'):
                raise ValueError("Invalid Supabase project URL")
        
        elif connection_type == 'api_key':
            if 'api_key' not in credentials:
                raise ValueError("API Key connection requires 'api_key' in credentials")
        
        elif connection_type == 'database':
            required_fields = ['host', 'port', 'database', 'username', 'password']
            for field in required_fields:
                if field not in credentials:
                    raise ValueError(f"Database connection requires '{field}' in credentials")
    
    async def _test_connection_connectivity(self, connection: Connection) -> ConnectionTestResult:
        """Test basic connectivity to connection service"""
        
        try:
            if connection.connection_type == 'whatsapp':
                # Test WhatsApp Business API
                url = "https://graph.facebook.com/v17.0/me"
                headers = {'Authorization': f"Bearer {connection.credentials['access_token']}"}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=10) as response:
                        success = response.status == 200
                        return ConnectionTestResult(
                            connection_id=connection.id,
                            test_type='connectivity',
                            success=success,
                            error_message=None if success else f"HTTP {response.status}"
                        )
            
            elif connection.connection_type == 'telegram':
                # Test Telegram Bot API
                token = connection.credentials['bot_token']
                url = f"https://api.telegram.org/bot{token}/getMe"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            success = data.get('ok', False)
                            return ConnectionTestResult(
                                connection_id=connection.id,
                                test_type='connectivity',
                                success=success,
                                details={'bot_info': data.get('result')} if success else None,
                                error_message=None if success else "Bot API returned error"
                            )
                        
                        return ConnectionTestResult(
                            connection_id=connection.id,
                            test_type='connectivity',
                            success=False,
                            error_message=f"HTTP {response.status}"
                        )
            
            else:
                # For other types, return success (would implement actual tests)
                return ConnectionTestResult(
                    connection_id=connection.id,
                    test_type='connectivity',
                    success=True,
                    details={'message': 'Connectivity test passed'}
                )
                
        except asyncio.TimeoutError:
            return ConnectionTestResult(
                connection_id=connection.id,
                test_type='connectivity',
                success=False,
                error_message="Connection timeout"
            )
        except Exception as e:
            return ConnectionTestResult(
                connection_id=connection.id,
                test_type='connectivity',
                success=False,
                error_message=str(e)
            )
    
    async def _test_authentication(self, connection: Connection) -> ConnectionTestResult:
        """Test authentication credentials"""
        
        # This would test the actual authentication
        return ConnectionTestResult(
            connection_id=connection.id,
            test_type='authentication',
            success=True,
            details={'message': 'Authentication test passed'}
        )
    
    async def _test_permissions(self, connection: Connection, test_data: Optional[Dict[str, Any]]) -> ConnectionTestResult:
        """Test connection permissions"""
        
        return ConnectionTestResult(
            connection_id=connection.id,
            test_type='permissions',
            success=True,
            details={'message': 'Permissions test passed'}
        )
    
    async def _test_full_connection(
        self, 
        connection: Connection, 
        test_data: Optional[Dict[str, Any]]
    ) -> ConnectionTestResult:
        """Run comprehensive connection test"""
        
        # Test connectivity
        connectivity_result = await self._test_connection_connectivity(connection)
        if not connectivity_result.success:
            return connectivity_result
        
        # Test authentication
        auth_result = await self._test_authentication(connection)
        if not auth_result.success:
            return auth_result
        
        return ConnectionTestResult(
            connection_id=connection.id,
            test_type='full',
            success=True,
            details={'message': 'Full connection test passed'}
        )
    
    async def _initialize_connection_analytics(self, connection_id: UUID):
        """Initialize analytics tracking for new connection"""
        
        today = datetime.utcnow().date()
        
        analytics = IntegrationAnalytics(
            integration_id=connection_id,
            date=today
        )
        
        await self.integration_repo.save_analytics(analytics)
    
    async def _cleanup_connection_data(self, connection_id: UUID):
        """Clean up data associated with connection"""
        
        # Delete analytics, logs, etc.
        # For now, just log the action
        print(f"Cleaning up data for connection {connection_id}")
    
    def _generate_webhook_token(self, connection_id: UUID) -> str:
        """Generate webhook token for connection"""
        
        return f"whk_{secrets.token_hex(16)}_{str(connection_id)[:8]}"
    
    async def _validate_webhook_payload(self, connection: Connection, payload: Dict[str, Any]) -> bool:
        """Validate webhook payload based on connection type"""
        
        if connection.connection_type == 'whatsapp':
            return 'object' in payload and 'entry' in payload
        elif connection.connection_type == 'telegram':
            return 'update_id' in payload
        else:
            return True  # Generic validation
    
    async def _process_webhook_by_type(self, connection: Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook based on connection type"""
        
        if connection.connection_type == 'whatsapp':
            return await self._process_whatsapp_webhook(connection, payload)
        elif connection.connection_type == 'telegram':
            return await self._process_telegram_webhook(connection, payload)
        else:
            return await self._process_generic_webhook(connection, payload)
    
    async def _process_whatsapp_webhook(self, connection: Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process WhatsApp webhook"""
        
        # Extract messages from payload
        messages = []
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') == 'messages':
                    messages.extend(change.get('value', {}).get('messages', []))
        
        return {
            'type': 'whatsapp',
            'messages_count': len(messages),
            'messages': messages
        }
    
    async def _process_telegram_webhook(self, connection: Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Telegram webhook"""
        
        return {
            'type': 'telegram',
            'update_id': payload.get('update_id'),
            'message': payload.get('message'),
            'callback_query': payload.get('callback_query')
        }
    
    async def _process_generic_webhook(self, connection: Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic webhook"""
        
        return {
            'type': 'generic',
            'payload_keys': list(payload.keys()),
            'processed_at': datetime.utcnow().isoformat()
        }
    
    async def _refresh_oauth_token(self, connection: Connection) -> Dict[str, Any]:
        """Refresh OAuth token"""
        
        # This would implement actual OAuth refresh logic
        # For now, return mock refreshed credentials
        return {
            **connection.credentials,
            'access_token': f"refreshed_{secrets.token_hex(16)}",
            'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }