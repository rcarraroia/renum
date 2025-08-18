"""
Third-Party Connectors Service
Support for third-party integration platforms like Pipedream, n8n, Zapier, Make
"""
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import hashlib
import hmac
from dataclasses import dataclass

from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class ConnectorType(Enum):
    """Types of third-party connectors"""
    ZAPIER = "zapier"
    MAKE = "make"
    N8N = "n8n"
    PIPEDREAM = "pipedream"
    CUSTOM_WEBHOOK = "custom_webhook"

class ConnectorStatus(Enum):
    """Status of connector connections"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"

@dataclass
class ConnectorConfig:
    """Configuration for a third-party connector"""
    connector_id: str
    connector_type: ConnectorType
    name: str
    description: str
    webhook_url: str
    authentication: Dict[str, Any]
    settings: Dict[str, Any]
    status: ConnectorStatus
    created_at: datetime
    last_used_at: Optional[datetime] = None

@dataclass
class ConnectorExecution:
    """Execution record for connector"""
    execution_id: str
    connector_id: str
    trigger_data: Dict[str, Any]
    response_data: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]
    execution_time_ms: int
    executed_at: datetime

class ThirdPartyConnectorsService:
    """Service for managing third-party connectors"""
    
    def __init__(self):
        # Connector configurations storage
        self.connectors: Dict[str, ConnectorConfig] = {}
        
        # Execution history
        self.executions: List[ConnectorExecution] = []
        
        # Supported connector templates
        self.connector_templates = self._initialize_connector_templates()
        
        # Webhook signature verification
        self.signature_methods = {
            'sha256': lambda secret, payload: hmac.new(
                secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest(),
            'sha1': lambda secret, payload: hmac.new(
                secret.encode(), payload.encode(), hashlib.sha1
            ).hexdigest()
        }
    
    def _initialize_connector_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize connector templates with default configurations"""
        return {
            'zapier': {
                'name': 'Zapier',
                'description': 'Connect with 5000+ apps through Zapier webhooks',
                'webhook_url_pattern': 'https://hooks.zapier.com/hooks/catch/{hook_id}/',
                'authentication': {
                    'type': 'none',
                    'description': 'Zapier handles authentication through the platform'
                },
                'supported_methods': ['POST'],
                'content_type': 'application/json',
                'signature_verification': False,
                'rate_limits': {
                    'requests_per_minute': 100,
                    'requests_per_hour': 1000
                },
                'setup_instructions': [
                    'Create a new Zap in Zapier',
                    'Choose "Webhooks by Zapier" as the trigger',
                    'Select "Catch Hook" trigger',
                    'Copy the webhook URL provided',
                    'Configure the webhook URL in Renum'
                ],
                'popular_integrations': [
                    'Google Sheets', 'Slack', 'Gmail', 'Trello', 'Asana',
                    'Salesforce', 'HubSpot', 'Mailchimp', 'Airtable'
                ]
            },
            'make': {
                'name': 'Make (Integromat)',
                'description': 'Visual automation platform with 1000+ integrations',
                'webhook_url_pattern': 'https://hook.integromat.com/{webhook_key}',
                'authentication': {
                    'type': 'api_key',
                    'description': 'API key for Make webhook authentication'
                },
                'supported_methods': ['POST', 'GET'],
                'content_type': 'application/json',
                'signature_verification': True,
                'rate_limits': {
                    'requests_per_minute': 60,
                    'requests_per_hour': 1000
                },
                'setup_instructions': [
                    'Create a new scenario in Make',
                    'Add a Webhook module as the trigger',
                    'Copy the webhook URL',
                    'Configure authentication if required',
                    'Set up the webhook URL in Renum'
                ],
                'popular_integrations': [
                    'Google Workspace', 'Microsoft 365', 'Shopify', 'WooCommerce',
                    'Facebook', 'Instagram', 'Twitter', 'LinkedIn'
                ]
            },
            'n8n': {
                'name': 'n8n',
                'description': 'Open-source workflow automation with 200+ integrations',
                'webhook_url_pattern': 'https://{instance_url}/webhook/{webhook_id}',
                'authentication': {
                    'type': 'custom',
                    'description': 'Configurable authentication based on n8n setup'
                },
                'supported_methods': ['POST', 'GET', 'PUT', 'PATCH', 'DELETE'],
                'content_type': 'application/json',
                'signature_verification': True,
                'rate_limits': {
                    'requests_per_minute': 120,
                    'requests_per_hour': 2000
                },
                'setup_instructions': [
                    'Create a new workflow in n8n',
                    'Add a Webhook node as the trigger',
                    'Configure the webhook settings',
                    'Copy the webhook URL',
                    'Set up authentication if needed',
                    'Configure the webhook in Renum'
                ],
                'popular_integrations': [
                    'GitHub', 'GitLab', 'Discord', 'Telegram', 'Notion',
                    'Airtable', 'PostgreSQL', 'MySQL', 'Redis'
                ]
            },
            'pipedream': {
                'name': 'Pipedream',
                'description': 'Developer-first integration platform with 1000+ apps',
                'webhook_url_pattern': 'https://webhook.pipedream.com/{endpoint_id}',
                'authentication': {
                    'type': 'bearer_token',
                    'description': 'Bearer token for Pipedream API authentication'
                },
                'supported_methods': ['POST', 'GET', 'PUT', 'PATCH', 'DELETE'],
                'content_type': 'application/json',
                'signature_verification': True,
                'rate_limits': {
                    'requests_per_minute': 100,
                    'requests_per_hour': 1000
                },
                'setup_instructions': [
                    'Create a new workflow in Pipedream',
                    'Add an HTTP trigger',
                    'Copy the endpoint URL',
                    'Configure authentication if needed',
                    'Set up the webhook URL in Renum'
                ],
                'popular_integrations': [
                    'Twitter', 'YouTube', 'Twilio', 'SendGrid', 'Stripe',
                    'PayPal', 'AWS', 'Google Cloud', 'Azure'
                ]
            },
            'custom_webhook': {
                'name': 'Custom Webhook',
                'description': 'Generic webhook connector for custom integrations',
                'webhook_url_pattern': '{custom_url}',
                'authentication': {
                    'type': 'configurable',
                    'description': 'Configurable authentication (API key, Bearer token, etc.)'
                },
                'supported_methods': ['POST', 'GET', 'PUT', 'PATCH', 'DELETE'],
                'content_type': 'configurable',
                'signature_verification': True,
                'rate_limits': {
                    'requests_per_minute': 60,
                    'requests_per_hour': 1000
                },
                'setup_instructions': [
                    'Obtain webhook URL from your service',
                    'Configure authentication method',
                    'Set up signature verification if supported',
                    'Test the webhook connection',
                    'Configure the webhook in Renum'
                ],
                'popular_integrations': [
                    'Custom APIs', 'Internal services', 'Legacy systems',
                    'Microservices', 'Third-party platforms'
                ]
            }
        }
    
    async def create_connector(
        self,
        user_id: UUID,
        connector_type: ConnectorType,
        name: str,
        webhook_url: str,
        authentication: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new third-party connector"""
        try:
            connector_id = str(uuid4())
            
            # Validate webhook URL format
            template = self.connector_templates.get(connector_type.value, {})
            if not self._validate_webhook_url(webhook_url, template):
                raise ValueError(f"Invalid webhook URL format for {connector_type.value}")
            
            connector = ConnectorConfig(
                connector_id=connector_id,
                connector_type=connector_type,
                name=name,
                description=f"{connector_type.value.title()} connector: {name}",
                webhook_url=webhook_url,
                authentication=authentication or {},
                settings=settings or {},
                status=ConnectorStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            self.connectors[connector_id] = connector
            
            # Test the connector
            test_result = await self._test_connector(connector)
            if test_result['success']:
                connector.status = ConnectorStatus.ACTIVE
            else:
                connector.status = ConnectorStatus.ERROR
                logger.warning(f"Connector test failed: {test_result['error']}")
            
            # Record analytics
            await analytics_service.metrics_collector.increment_counter(
                'third_party_connectors_created',
                tags={
                    'connector_type': connector_type.value,
                    'user_id': str(user_id)
                }
            )
            
            logger.info(f"Created {connector_type.value} connector: {connector_id}")
            
            return connector_id
            
        except Exception as e:
            logger.error(f"Failed to create connector: {e}")
            raise
    
    def _validate_webhook_url(self, webhook_url: str, template: Dict[str, Any]) -> bool:
        """Validate webhook URL format"""
        if not webhook_url.startswith('http'):
            return False
        
        # Basic URL validation
        import re
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, webhook_url))
    
    async def _test_connector(self, connector: ConnectorConfig) -> Dict[str, Any]:
        """Test connector connection"""
        try:
            # Prepare test payload
            test_payload = {
                'test': True,
                'message': 'Test connection from Renum',
                'timestamp': datetime.utcnow().isoformat(),
                'connector_id': connector.connector_id
            }
            
            # Execute test webhook call
            result = await self._execute_webhook_call(
                connector,
                test_payload,
                is_test=True
            )
            
            return {
                'success': result.success,
                'error': result.error_message if not result.success else None,
                'response_time_ms': result.execution_time_ms
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time_ms': 0
            }
    
    async def execute_connector(
        self,
        connector_id: str,
        trigger_data: Dict[str, Any],
        user_id: UUID
    ) -> ConnectorExecution:
        """Execute a third-party connector"""
        try:
            connector = self.connectors.get(connector_id)
            if not connector:
                raise ValueError(f"Connector {connector_id} not found")
            
            if connector.status != ConnectorStatus.ACTIVE:
                raise ValueError(f"Connector {connector_id} is not active")
            
            # Execute webhook call
            start_time = datetime.utcnow()
            result = await self._execute_webhook_call(connector, trigger_data)
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Create execution record
            execution = ConnectorExecution(
                execution_id=str(uuid4()),
                connector_id=connector_id,
                trigger_data=trigger_data,
                response_data=result.data if result.success else None,
                success=result.success,
                error_message=result.error_message if not result.success else None,
                execution_time_ms=execution_time,
                executed_at=datetime.utcnow()
            )
            
            self.executions.append(execution)
            
            # Update connector last used time
            connector.last_used_at = datetime.utcnow()
            
            # Record analytics
            await analytics_service.metrics_collector.increment_counter(
                'third_party_connector_executions',
                tags={
                    'connector_type': connector.connector_type.value,
                    'success': str(result.success),
                    'user_id': str(user_id)
                }
            )
            
            await analytics_service.metrics_collector.record_metric(
                'third_party_connector_execution_time_ms',
                execution_time,
                tags={
                    'connector_type': connector.connector_type.value,
                    'connector_id': connector_id
                }
            )
            
            return execution
            
        except Exception as e:
            # Create failed execution record
            execution = ConnectorExecution(
                execution_id=str(uuid4()),
                connector_id=connector_id,
                trigger_data=trigger_data,
                response_data=None,
                success=False,
                error_message=str(e),
                execution_time_ms=0,
                executed_at=datetime.utcnow()
            )
            
            self.executions.append(execution)
            logger.error(f"Connector execution failed: {e}")
            
            return execution
    
    async def _execute_webhook_call(
        self,
        connector: ConnectorConfig,
        payload: Dict[str, Any],
        is_test: bool = False
    ) -> Any:  # Would return AgentExecutionResult in real implementation
        """Execute webhook call to third-party connector"""
        try:
            import httpx
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Renum-Integration/1.0'
            }
            
            # Add authentication
            auth = connector.authentication
            if auth.get('type') == 'api_key':
                headers['X-API-Key'] = auth.get('api_key', '')
            elif auth.get('type') == 'bearer_token':
                headers['Authorization'] = f"Bearer {auth.get('token', '')}"
            elif auth.get('type') == 'basic_auth':
                import base64
                credentials = f"{auth.get('username', '')}:{auth.get('password', '')}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers['Authorization'] = f"Basic {encoded}"
            
            # Add signature if required
            if connector.connector_type != ConnectorType.ZAPIER:  # Zapier doesn't use signatures
                signature = self._generate_webhook_signature(
                    connector, json.dumps(payload, sort_keys=True)
                )
                if signature:
                    headers['X-Signature'] = signature
            
            # Add test header if this is a test
            if is_test:
                headers['X-Test-Request'] = 'true'
            
            # Make HTTP request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    connector.webhook_url,
                    json=payload,
                    headers=headers
                )
                
                # Process response
                try:
                    response_data = response.json()
                except:
                    response_data = response.text
                
                # Mock AgentExecutionResult
                class MockResult:
                    def __init__(self, success, data=None, error_message=None, execution_time_ms=0):
                        self.success = success
                        self.data = data
                        self.error_message = error_message
                        self.execution_time_ms = execution_time_ms
                
                if response.status_code < 400:
                    return MockResult(
                        success=True,
                        data={
                            'status_code': response.status_code,
                            'response': response_data,
                            'headers': dict(response.headers)
                        }
                    )
                else:
                    return MockResult(
                        success=False,
                        error_message=f"HTTP {response.status_code}: {response_data}"
                    )
                    
        except Exception as e:
            class MockResult:
                def __init__(self, success, error_message):
                    self.success = success
                    self.error_message = error_message
                    self.execution_time_ms = 0
                    self.data = None
            
            return MockResult(success=False, error_message=str(e))
    
    def _generate_webhook_signature(
        self,
        connector: ConnectorConfig,
        payload: str
    ) -> Optional[str]:
        """Generate webhook signature for verification"""
        auth = connector.authentication
        secret = auth.get('webhook_secret')
        
        if not secret:
            return None
        
        signature_method = auth.get('signature_method', 'sha256')
        
        if signature_method in self.signature_methods:
            signature = self.signature_methods[signature_method](secret, payload)
            return f"{signature_method}={signature}"
        
        return None
    
    async def get_connectors(
        self,
        user_id: UUID,
        connector_type: Optional[ConnectorType] = None,
        status: Optional[ConnectorStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get user's connectors"""
        connectors = []
        
        for connector in self.connectors.values():
            # Apply filters
            if connector_type and connector.connector_type != connector_type:
                continue
            if status and connector.status != status:
                continue
            
            # Get execution stats
            connector_executions = [
                ex for ex in self.executions 
                if ex.connector_id == connector.connector_id
            ]
            
            successful_executions = sum(1 for ex in connector_executions if ex.success)
            total_executions = len(connector_executions)
            
            connectors.append({
                'connector_id': connector.connector_id,
                'connector_type': connector.connector_type.value,
                'name': connector.name,
                'description': connector.description,
                'webhook_url': connector.webhook_url,
                'status': connector.status.value,
                'created_at': connector.created_at.isoformat(),
                'last_used_at': connector.last_used_at.isoformat() if connector.last_used_at else None,
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0
            })
        
        return connectors
    
    async def get_connector_templates(self) -> Dict[str, Any]:
        """Get available connector templates"""
        return {
            'templates': [
                {
                    'connector_type': connector_type,
                    'name': template['name'],
                    'description': template['description'],
                    'webhook_url_pattern': template['webhook_url_pattern'],
                    'authentication': template['authentication'],
                    'supported_methods': template['supported_methods'],
                    'setup_instructions': template['setup_instructions'],
                    'popular_integrations': template['popular_integrations'],
                    'rate_limits': template['rate_limits']
                }
                for connector_type, template in self.connector_templates.items()
            ],
            'total_templates': len(self.connector_templates)
        }
    
    async def get_connector_executions(
        self,
        connector_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get execution history for a connector"""
        connector_executions = [
            ex for ex in self.executions 
            if ex.connector_id == connector_id
        ]
        
        # Sort by execution time (most recent first)
        connector_executions.sort(key=lambda x: x.executed_at, reverse=True)
        
        # Apply pagination
        paginated_executions = connector_executions[offset:offset + limit]
        
        return [
            {
                'execution_id': ex.execution_id,
                'success': ex.success,
                'error_message': ex.error_message,
                'execution_time_ms': ex.execution_time_ms,
                'executed_at': ex.executed_at.isoformat(),
                'trigger_data_size': len(json.dumps(ex.trigger_data)),
                'response_data_size': len(json.dumps(ex.response_data)) if ex.response_data else 0
            }
            for ex in paginated_executions
        ]
    
    async def delete_connector(self, connector_id: str, user_id: UUID) -> bool:
        """Delete a connector"""
        try:
            if connector_id not in self.connectors:
                return False
            
            connector = self.connectors[connector_id]
            
            # Remove connector
            del self.connectors[connector_id]
            
            # Remove execution history (optional, might want to keep for analytics)
            self.executions = [
                ex for ex in self.executions 
                if ex.connector_id != connector_id
            ]
            
            # Record analytics
            await analytics_service.metrics_collector.increment_counter(
                'third_party_connectors_deleted',
                tags={
                    'connector_type': connector.connector_type.value,
                    'user_id': str(user_id)
                }
            )
            
            logger.info(f"Deleted connector: {connector_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete connector: {e}")
            return False
    
    async def get_connector_analytics(
        self,
        connector_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get analytics for a specific connector"""
        try:
            connector = self.connectors.get(connector_id)
            if not connector:
                raise ValueError(f"Connector {connector_id} not found")
            
            # Get executions for the period
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_executions = [
                ex for ex in self.executions
                if ex.connector_id == connector_id and ex.executed_at >= cutoff_date
            ]
            
            # Calculate metrics
            total_executions = len(recent_executions)
            successful_executions = sum(1 for ex in recent_executions if ex.success)
            failed_executions = total_executions - successful_executions
            
            avg_execution_time = (
                sum(ex.execution_time_ms for ex in recent_executions) / total_executions
                if total_executions > 0 else 0
            )
            
            # Group by day
            daily_stats = {}
            for ex in recent_executions:
                day = ex.executed_at.date().isoformat()
                if day not in daily_stats:
                    daily_stats[day] = {'total': 0, 'successful': 0, 'failed': 0}
                
                daily_stats[day]['total'] += 1
                if ex.success:
                    daily_stats[day]['successful'] += 1
                else:
                    daily_stats[day]['failed'] += 1
            
            return {
                'connector_id': connector_id,
                'connector_name': connector.name,
                'connector_type': connector.connector_type.value,
                'period_days': days,
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'failed_executions': failed_executions,
                'success_rate_percent': (successful_executions / total_executions * 100) if total_executions > 0 else 0,
                'avg_execution_time_ms': round(avg_execution_time, 2),
                'daily_stats': daily_stats,
                'status': connector.status.value,
                'last_used_at': connector.last_used_at.isoformat() if connector.last_used_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get connector analytics: {e}")
            raise

# Global third-party connectors service instance
third_party_connectors_service = ThirdPartyConnectorsService()