"""
Configuração de Testes - pytest conftest.py
Fixtures e configurações compartilhadas para todos os testes
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta
import os
import tempfile
import json

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_user():
    """Mock user for authentication tests"""
    return {
        'user_id': str(uuid4()),
        'email': 'test@example.com',
        'role': 'user',
        'created_at': datetime.utcnow(),
        'is_active': True
    }

@pytest.fixture
def mock_admin_user():
    """Mock admin user for authorization tests"""
    return {
        'user_id': str(uuid4()),
        'email': 'admin@example.com',
        'role': 'admin',
        'created_at': datetime.utcnow(),
        'is_active': True
    }

@pytest.fixture
def mock_auth_headers(mock_user):
    """Mock authentication headers"""
    return {
        "Authorization": f"Bearer test-token-{mock_user['user_id']}"
    }

@pytest.fixture
def mock_admin_headers(mock_admin_user):
    """Mock admin authentication headers"""
    return {
        "Authorization": f"Bearer admin-token-{mock_admin_user['user_id']}"
    }

@pytest.fixture
def sample_workflow_definition():
    """Sample workflow definition for testing"""
    return {
        "name": "Test Workflow",
        "description": "A workflow for testing purposes",
        "execution_strategy": "sequential",
        "steps": [
            {
                "id": "step1",
                "agent_id": "sa-whatsapp",
                "capability": "send_message",
                "input": {
                    "phone_number": "+5511999999999",
                    "message": "Hello from test workflow!"
                }
            },
            {
                "id": "step2",
                "agent_id": "sa-gmail",
                "capability": "send_email",
                "input": {
                    "to": "test@example.com",
                    "subject": "Test Email",
                    "body": "This is a test email from the workflow."
                }
            }
        ]
    }

@pytest.fixture
def sample_parallel_workflow():
    """Sample parallel workflow for testing"""
    return {
        "name": "Parallel Test Workflow",
        "description": "A parallel workflow for testing",
        "execution_strategy": "parallel",
        "steps": [
            {
                "id": "whatsapp_step",
                "agent_id": "sa-whatsapp",
                "capability": "send_message",
                "input": {
                    "phone_number": "+5511999999999",
                    "message": "Parallel message 1"
                }
            },
            {
                "id": "telegram_step",
                "agent_id": "sa-telegram",
                "capability": "send_message",
                "input": {
                    "chat_id": "123456789",
                    "message": "Parallel message 2"
                }
            },
            {
                "id": "email_step",
                "agent_id": "sa-gmail",
                "capability": "send_email",
                "input": {
                    "to": "test@example.com",
                    "subject": "Parallel Email",
                    "body": "This is a parallel email."
                }
            }
        ]
    }

@pytest.fixture
def mock_agent_response():
    """Mock successful agent response"""
    return {
        'success': True,
        'data': {
            'message_id': f'msg-{uuid4()}',
            'status': 'sent',
            'timestamp': datetime.utcnow().isoformat()
        },
        'execution_time_ms': 150,
        'cost': 0.01
    }

@pytest.fixture
def mock_failed_agent_response():
    """Mock failed agent response"""
    return {
        'success': False,
        'error': 'Rate limit exceeded',
        'error_code': 'RATE_LIMIT',
        'execution_time_ms': 50,
        'cost': 0.0
    }

@pytest.fixture
def mock_webhook_payload():
    """Mock webhook payload for testing"""
    return {
        "event": "message_received",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "from": "+5511999999999",
            "message": "Hello, this is a test message",
            "message_id": str(uuid4())
        }
    }

@pytest.fixture
def mock_credentials():
    """Mock credentials for agent testing"""
    return {
        'whatsapp': {
            'access_token': 'test-whatsapp-token',
            'phone_number_id': '1234567890'
        },
        'telegram': {
            'bot_token': 'test-telegram-token'
        },
        'gmail': {
            'email': 'test@gmail.com',
            'app_password': 'test-app-password'
        },
        'http_generic': {
            'api_key': 'test-api-key',
            'base_url': 'https://api.example.com'
        }
    }

@pytest.fixture
def temp_file():
    """Create a temporary file for testing"""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_database():
    """Mock database connection"""
    db_mock = AsyncMock()
    
    # Mock common database operations
    db_mock.execute.return_value = AsyncMock()
    db_mock.fetch.return_value = []
    db_mock.fetchrow.return_value = None
    db_mock.fetchval.return_value = None
    
    return db_mock

@pytest.fixture
def mock_redis():
    """Mock Redis connection"""
    redis_mock = AsyncMock()
    
    # Mock common Redis operations
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    redis_mock.expire.return_value = True
    
    return redis_mock

@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external API calls"""
    http_mock = AsyncMock()
    
    # Mock successful response
    response_mock = MagicMock()
    response_mock.status_code = 200
    response_mock.json.return_value = {'success': True, 'data': {}}
    response_mock.text = '{"success": true, "data": {}}'
    response_mock.headers = {'content-type': 'application/json'}
    
    http_mock.get.return_value = response_mock
    http_mock.post.return_value = response_mock
    http_mock.put.return_value = response_mock
    http_mock.delete.return_value = response_mock
    
    return http_mock

@pytest.fixture
def mock_analytics_service():
    """Mock analytics service"""
    analytics_mock = AsyncMock()
    
    analytics_mock.track_execution.return_value = None
    analytics_mock.track_agent_usage.return_value = None
    analytics_mock.get_dashboard_data.return_value = {
        'total_executions': 100,
        'success_rate': 95.5,
        'avg_execution_time': 2500,
        'total_cost': 15.75
    }
    
    return analytics_mock

@pytest.fixture
def mock_billing_service():
    """Mock billing service"""
    billing_mock = AsyncMock()
    
    billing_mock.track_usage.return_value = None
    billing_mock.get_usage_summary.return_value = {
        'total_cost': 10.50,
        'executions_count': 50,
        'current_period_cost': 5.25
    }
    billing_mock.check_quota.return_value = True
    
    return billing_mock

@pytest.fixture
def mock_orchestrator_service():
    """Mock orchestrator service"""
    orchestrator_mock = AsyncMock()
    
    orchestrator_mock.execute_workflow.return_value = {
        'execution_id': str(uuid4()),
        'status': 'completed',
        'results': {
            'step1': {'success': True, 'message_id': 'msg-123'},
            'step2': {'success': True, 'message_id': 'msg-456'}
        },
        'execution_time_ms': 2500,
        'total_cost': 0.05
    }
    
    return orchestrator_mock

@pytest.fixture
def mock_fallback_service():
    """Mock fallback service"""
    fallback_mock = AsyncMock()
    
    fallback_mock.handle_unsupported_integration.return_value = {
        'fallback_used': True,
        'alternative_agent': 'sa-http-generic',
        'suggestion': 'Use HTTP Generic agent with custom API endpoint',
        'confidence': 0.8
    }
    
    return fallback_mock

@pytest.fixture(autouse=True)
def mock_external_services():
    """Auto-mock external services to prevent real API calls during tests"""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock HTTP client for external API calls
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_response.text = '{"success": true}'
        
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value.put.return_value = mock_response
        mock_client.return_value.__aenter__.return_value.delete.return_value = mock_response
        
        yield mock_client

@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None
        
        def __enter__(self):
            self.start()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.stop()
    
    return Timer()

@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing"""
    test_env = {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_ANON_KEY': 'test-anon-key',
        'SUPABASE_SERVICE_ROLE_KEY': 'test-service-key',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'SUNA_API_URL': 'http://test-suna-api:8000/api',
        'SUNA_WS_URL': 'ws://test-suna-api:8000/ws',
        'SUNA_API_KEY': 'test-suna-key',
        'REDIS_URL': 'redis://test-redis:6379',
        'DEBUG': 'false',
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        yield test_env

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file names"""
    for item in items:
        # Add markers based on test file names
        if "test_performance" in item.fspath.basename:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        
        if "test_security" in item.fspath.basename:
            item.add_marker(pytest.mark.security)
        
        if "test_integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        
        if "test_unit" in item.fspath.basename or "test_" in item.fspath.basename:
            if not any(marker.name in ['integration', 'performance'] for marker in item.iter_markers()):
                item.add_marker(pytest.mark.unit)

# Test data factories
class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_execution_record(user_id=None, status='completed'):
        """Create a test execution record"""
        return {
            'execution_id': str(uuid4()),
            'user_id': user_id or str(uuid4()),
            'workflow_name': 'Test Workflow',
            'status': status,
            'created_at': datetime.utcnow(),
            'completed_at': datetime.utcnow() + timedelta(seconds=30),
            'execution_time_ms': 2500,
            'total_cost': 0.05,
            'results': {
                'step1': {'success': True, 'message_id': 'msg-123'}
            }
        }
    
    @staticmethod
    def create_agent_record(agent_id=None):
        """Create a test agent record"""
        return {
            'agent_id': agent_id or f'sa-test-{uuid4()}',
            'name': 'Test Agent',
            'description': 'Agent for testing purposes',
            'version': '1.0.0',
            'capabilities': [
                {
                    'name': 'test_capability',
                    'description': 'Test capability',
                    'input_schema': {'type': 'object', 'properties': {}},
                    'output_schema': {'type': 'object', 'properties': {}}
                }
            ],
            'status': 'active',
            'created_at': datetime.utcnow()
        }
    
    @staticmethod
    def create_integration_record(integration_id=None):
        """Create a test integration record"""
        return {
            'integration_id': integration_id or f'test-integration-{uuid4()}',
            'name': 'Test Integration',
            'description': 'Integration for testing',
            'provider': 'test-provider',
            'category': 'messaging',
            'status': 'active',
            'configuration_schema': {
                'type': 'object',
                'properties': {
                    'api_key': {'type': 'string'},
                    'base_url': {'type': 'string'}
                }
            },
            'created_at': datetime.utcnow()
        }

@pytest.fixture
def test_data_factory():
    """Provide test data factory"""
    return TestDataFactory