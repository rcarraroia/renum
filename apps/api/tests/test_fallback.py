"""
Testes para Sistema de Fallback
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timedelta

from app.main import app
from app.services.fallback_service import FallbackService, IntegrationCategory
from app.services.suggestion_engine import SuggestionEngine, MatchingStrategy
from app.services.third_party_connectors import ThirdPartyConnectorsService, ConnectorType

client = TestClient(app)

class TestFallbackService:
    """Testes para FallbackService"""
    
    @pytest.fixture
    def fallback_service(self):
        """Fixture do FallbackService"""
        return FallbackService()
    
    @pytest.mark.asyncio
    async def test_handle_unsupported_integration(self, fallback_service):
        """Teste para lidar com integração não suportada"""
        user_id = uuid4()
        
        with patch.object(fallback_service, '_analyze_integration_request') as mock_analyze, \
             patch.object(fallback_service, '_generate_suggestions') as mock_suggestions, \
             patch.object(fallback_service, '_record_integration_request') as mock_record:
            
            mock_analyze.return_value = {
                'integration_name': 'slack',
                'detected_category': IntegrationCategory.MESSAGING,
                'has_api': True,
                'estimated_dev_time': '2-4 weeks'
            }
            
            mock_suggestions.return_value = [
                MagicMock(
                    suggestion_id='test-suggestion',
                    suggestion_type=MagicMock(value='direct_alternative'),
                    title='Use Telegram instead',
                    description='Telegram provides similar messaging functionality',
                    confidence_score=0.8,
                    implementation_effort='low',
                    available_now=True,
                    details={'test': 'data'},
                    alternatives=['telegram']
                )
            ]
            
            result = await fallback_service.handle_unsupported_integration(
                'slack', user_id, {'use_case': 'team communication'}
            )
            
            assert result['integration_name'] == 'slack'
            assert result['supported'] is False
            assert len(result['suggestions']) == 1
            assert result['suggestions'][0]['title'] == 'Use Telegram instead'
            
            mock_analyze.assert_called_once()
            mock_suggestions.assert_called_once()
            mock_record.assert_called_once()
    
    def test_detect_category(self, fallback_service):
        """Teste para detecção de categoria"""
        # Test messaging category
        assert fallback_service._detect_category('slack') == IntegrationCategory.MESSAGING
        assert fallback_service._detect_category('discord chat') == IntegrationCategory.MESSAGING
        
        # Test CRM category
        assert fallback_service._detect_category('salesforce') == IntegrationCategory.CRM
        assert fallback_service._detect_category('hubspot crm') == IntegrationCategory.CRM
        
        # Test ecommerce category
        assert fallback_service._detect_category('shopify') == IntegrationCategory.ECOMMERCE
        
        # Test default category
        assert fallback_service._detect_category('unknown service') == IntegrationCategory.OTHER
    
    def test_likely_has_api(self, fallback_service):
        """Teste para verificar se serviço provavelmente tem API"""
        # Known services with APIs
        assert fallback_service._likely_has_api('slack') is True
        assert fallback_service._likely_has_api('github') is True
        assert fallback_service._likely_has_api('stripe payment') is True
        
        # Unknown services
        assert fallback_service._likely_has_api('unknown service') is False
    
    def test_get_common_use_cases(self, fallback_service):
        """Teste para obter casos de uso comuns"""
        messaging_cases = fallback_service._get_common_use_cases('slack')
        assert 'Send messages' in messaging_cases
        assert 'Receive webhooks' in messaging_cases
        
        crm_cases = fallback_service._get_common_use_cases('salesforce')
        assert 'Sync contacts' in crm_cases
        assert 'Update deals' in crm_cases
    
    def test_calculate_complexity_score(self, fallback_service):
        """Teste para cálculo de score de complexidade"""
        # Simple services
        assert fallback_service._calculate_complexity_score('webhook') == 0.2
        assert fallback_service._calculate_complexity_score('rest api') == 0.2
        
        # Well-documented services
        assert fallback_service._calculate_complexity_score('slack') == 0.4
        assert fallback_service._calculate_complexity_score('stripe') == 0.4
        
        # Enterprise services
        assert fallback_service._calculate_complexity_score('salesforce') == 0.8
        assert fallback_service._calculate_complexity_score('sap') == 0.8
        
        # Unknown services
        assert fallback_service._calculate_complexity_score('unknown') == 0.6
    
    @pytest.mark.asyncio
    async def test_create_integration_request(self, fallback_service):
        """Teste para criar solicitação de integração"""
        user_id = uuid4()
        
        with patch('app.services.fallback_service.analytics_service') as mock_analytics:
            request_id = await fallback_service.create_integration_request(
                user_id=user_id,
                integration_name='notion',
                description='Need Notion integration for documentation',
                use_case='Team documentation management',
                priority='high',
                business_impact='High productivity impact',
                expected_volume=500
            )
            
            assert request_id in fallback_service.integration_requests
            request = fallback_service.integration_requests[request_id]
            
            assert request.integration_name == 'notion'
            assert request.user_id == user_id
            assert request.priority == 'high'
            assert request.status == 'pending'
            assert request.votes == 0
            
            mock_analytics.metrics_collector.increment_counter.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vote_for_integration_request(self, fallback_service):
        """Teste para votar em solicitação de integração"""
        user_id = uuid4()
        
        # Create a request first
        request_id = await fallback_service.create_integration_request(
            user_id=user_id,
            integration_name='notion',
            description='Test description',
            use_case='Test use case'
        )
        
        with patch('app.services.fallback_service.analytics_service') as mock_analytics:
            # Vote for the request
            success = await fallback_service.vote_for_integration_request(request_id, user_id)
            
            assert success is True
            assert fallback_service.integration_requests[request_id].votes == 1
            
            mock_analytics.metrics_collector.increment_counter.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_integration_requests(self, fallback_service):
        """Teste para obter solicitações de integração"""
        user_id = uuid4()
        
        # Create some requests
        await fallback_service.create_integration_request(
            user_id=user_id,
            integration_name='notion',
            description='Notion integration',
            use_case='Documentation',
            priority='high'
        )
        
        await fallback_service.create_integration_request(
            user_id=user_id,
            integration_name='airtable',
            description='Airtable integration',
            use_case='Database',
            priority='medium'
        )
        
        # Get all requests
        requests = await fallback_service.get_integration_requests()
        assert len(requests) == 2
        
        # Filter by priority
        high_priority = await fallback_service.get_integration_requests(status='pending')
        assert len(high_priority) == 2
        
        # Test pagination
        paginated = await fallback_service.get_integration_requests(limit=1, offset=0)
        assert len(paginated) == 1
    
    @pytest.mark.asyncio
    async def test_get_integration_roadmap(self, fallback_service):
        """Teste para obter roadmap de integrações"""
        user_id = uuid4()
        
        # Create some requests with votes
        request1_id = await fallback_service.create_integration_request(
            user_id=user_id,
            integration_name='notion',
            description='Notion integration',
            use_case='Documentation',
            priority='high'
        )
        
        request2_id = await fallback_service.create_integration_request(
            user_id=user_id,
            integration_name='airtable',
            description='Airtable integration',
            use_case='Database',
            priority='medium'
        )
        
        # Add votes
        await fallback_service.vote_for_integration_request(request1_id, user_id)
        await fallback_service.vote_for_integration_request(request1_id, uuid4())
        await fallback_service.vote_for_integration_request(request2_id, user_id)
        
        roadmap = await fallback_service.get_integration_roadmap()
        
        assert roadmap['total_requests'] == 2
        assert roadmap['by_status']['pending'] == 2
        assert len(roadmap['top_requested']) == 2
        assert roadmap['top_requested'][0]['integration_name'] == 'notion'  # Most voted
        assert roadmap['top_requested'][0]['votes'] == 2

class TestSuggestionEngine:
    """Testes para SuggestionEngine"""
    
    @pytest.fixture
    def suggestion_engine(self):
        """Fixture do SuggestionEngine"""
        return SuggestionEngine()
    
    def test_infer_capabilities_from_name(self, suggestion_engine):
        """Teste para inferir capacidades do nome"""
        # Email service
        email_caps = suggestion_engine._infer_capabilities_from_name('gmail')
        assert 'send_message' in email_caps
        assert 'receive_message' in email_caps
        assert 'manage_contacts' in email_caps
        
        # Database service
        db_caps = suggestion_engine._infer_capabilities_from_name('postgresql database')
        assert 'create_record' in db_caps
        assert 'read_record' in db_caps
        assert 'update_record' in db_caps
        assert 'delete_record' in db_caps
        
        # Messaging service
        msg_caps = suggestion_engine._infer_capabilities_from_name('slack messaging')
        assert 'send_message' in msg_caps
        assert 'receive_message' in msg_caps
        assert 'manage_contacts' in msg_caps
        assert 'upload_file' in msg_caps
    
    def test_calculate_capability_similarity(self, suggestion_engine):
        """Teste para calcular similaridade de capacidades"""
        # Exact match
        assert suggestion_engine._calculate_capability_similarity('send_message', 'send_message') == 1.0
        
        # Similar capabilities
        similarity = suggestion_engine._calculate_capability_similarity('send_message', 'send')
        assert similarity > 0.5
        
        # Unrelated capabilities
        similarity = suggestion_engine._calculate_capability_similarity('send_message', 'delete_record')
        assert similarity < 0.5
    
    def test_calculate_semantic_similarity(self, suggestion_engine):
        """Teste para calcular similaridade semântica"""
        # Similar services
        similarity = suggestion_engine._calculate_semantic_similarity('gmail', 'email service')
        assert similarity > 0.5
        
        similarity = suggestion_engine._calculate_semantic_similarity('slack', 'messaging app')
        assert similarity > 0.5
        
        # Unrelated services
        similarity = suggestion_engine._calculate_semantic_similarity('gmail', 'database')
        assert similarity < 0.5
    
    @pytest.mark.asyncio
    async def test_suggest_alternatives(self, suggestion_engine):
        """Teste para sugerir alternativas"""
        matches = await suggestion_engine.suggest_alternatives(
            target_integration='slack',
            required_capabilities=['send_message', 'receive_message'],
            use_case='team communication',
            strategy=MatchingStrategy.HYBRID
        )
        
        assert len(matches) > 0
        
        # Check that matches have required fields
        for match in matches:
            assert hasattr(match, 'integration_id')
            assert hasattr(match, 'match_score')
            assert hasattr(match, 'capability_matches')
            assert hasattr(match, 'pros')
            assert hasattr(match, 'cons')
            assert match.match_score >= 0.0
            assert match.match_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_target_requirements(self, suggestion_engine):
        """Teste para analisar requisitos do target"""
        analysis = await suggestion_engine._analyze_target_requirements(
            'slack',
            ['send_message', 'receive_message'],
            'team communication',
            {'complexity_preference': 'simple'}
        )
        
        assert analysis['target_integration'] == 'slack'
        assert 'send_message' in analysis['required_capabilities']
        assert 'receive_message' in analysis['required_capabilities']
        assert analysis['use_case'] == 'team communication'
        assert len(analysis['inferred_capabilities']) > 0
        assert 'all_capabilities' in analysis

class TestThirdPartyConnectorsService:
    """Testes para ThirdPartyConnectorsService"""
    
    @pytest.fixture
    def connectors_service(self):
        """Fixture do ThirdPartyConnectorsService"""
        return ThirdPartyConnectorsService()
    
    def test_validate_webhook_url(self, connectors_service):
        """Teste para validação de URL de webhook"""
        template = {}  # Empty template for basic validation
        
        # Valid URLs
        assert connectors_service._validate_webhook_url('https://hooks.zapier.com/hooks/catch/123/', template) is True
        assert connectors_service._validate_webhook_url('http://localhost:3000/webhook', template) is True
        
        # Invalid URLs
        assert connectors_service._validate_webhook_url('not-a-url', template) is False
        assert connectors_service._validate_webhook_url('ftp://invalid.com', template) is False
    
    @pytest.mark.asyncio
    async def test_create_connector(self, connectors_service):
        """Teste para criar conector"""
        user_id = uuid4()
        
        with patch.object(connectors_service, '_test_connector') as mock_test:
            mock_test.return_value = {'success': True, 'error': None}
            
            connector_id = await connectors_service.create_connector(
                user_id=user_id,
                connector_type=ConnectorType.ZAPIER,
                name='Test Zapier Connector',
                webhook_url='https://hooks.zapier.com/hooks/catch/123/',
                authentication={'type': 'none'},
                settings={'timeout': 30}
            )
            
            assert connector_id in connectors_service.connectors
            connector = connectors_service.connectors[connector_id]
            
            assert connector.name == 'Test Zapier Connector'
            assert connector.connector_type == ConnectorType.ZAPIER
            assert connector.webhook_url == 'https://hooks.zapier.com/hooks/catch/123/'
            assert connector.status.value in ['active', 'error']  # Depends on test result
    
    @pytest.mark.asyncio
    async def test_execute_connector(self, connectors_service):
        """Teste para executar conector"""
        user_id = uuid4()
        
        # Create a connector first
        with patch.object(connectors_service, '_test_connector') as mock_test:
            mock_test.return_value = {'success': True, 'error': None}
            
            connector_id = await connectors_service.create_connector(
                user_id=user_id,
                connector_type=ConnectorType.ZAPIER,
                name='Test Connector',
                webhook_url='https://hooks.zapier.com/hooks/catch/123/'
            )
        
        # Mock the webhook call
        with patch.object(connectors_service, '_execute_webhook_call') as mock_webhook:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {'status': 'success', 'message': 'Webhook executed'}
            mock_result.error_message = None
            mock_webhook.return_value = mock_result
            
            execution = await connectors_service.execute_connector(
                connector_id=connector_id,
                trigger_data={'test': 'data', 'timestamp': datetime.utcnow().isoformat()},
                user_id=user_id
            )
            
            assert execution.success is True
            assert execution.connector_id == connector_id
            assert execution.trigger_data['test'] == 'data'
            assert execution.response_data is not None
            assert execution.execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_get_connectors(self, connectors_service):
        """Teste para obter conectores"""
        user_id = uuid4()
        
        # Create some connectors
        with patch.object(connectors_service, '_test_connector') as mock_test:
            mock_test.return_value = {'success': True, 'error': None}
            
            connector1_id = await connectors_service.create_connector(
                user_id=user_id,
                connector_type=ConnectorType.ZAPIER,
                name='Zapier Connector',
                webhook_url='https://hooks.zapier.com/hooks/catch/123/'
            )
            
            connector2_id = await connectors_service.create_connector(
                user_id=user_id,
                connector_type=ConnectorType.MAKE,
                name='Make Connector',
                webhook_url='https://hook.integromat.com/abc123'
            )
        
        # Get all connectors
        connectors = await connectors_service.get_connectors(user_id)
        assert len(connectors) == 2
        
        # Filter by type
        zapier_connectors = await connectors_service.get_connectors(
            user_id, connector_type=ConnectorType.ZAPIER
        )
        assert len(zapier_connectors) == 1
        assert zapier_connectors[0]['name'] == 'Zapier Connector'
    
    @pytest.mark.asyncio
    async def test_get_connector_templates(self, connectors_service):
        """Teste para obter templates de conectores"""
        templates = await connectors_service.get_connector_templates()
        
        assert 'templates' in templates
        assert 'total_templates' in templates
        assert templates['total_templates'] > 0
        
        # Check that all expected connector types are present
        template_types = [t['connector_type'] for t in templates['templates']]
        assert 'zapier' in template_types
        assert 'make' in template_types
        assert 'n8n' in template_types
        assert 'pipedream' in template_types
        assert 'custom_webhook' in template_types
        
        # Check template structure
        zapier_template = next(t for t in templates['templates'] if t['connector_type'] == 'zapier')
        assert 'name' in zapier_template
        assert 'description' in zapier_template
        assert 'webhook_url_pattern' in zapier_template
        assert 'setup_instructions' in zapier_template
        assert 'popular_integrations' in zapier_template
    
    @pytest.mark.asyncio
    async def test_delete_connector(self, connectors_service):
        """Teste para deletar conector"""
        user_id = uuid4()
        
        # Create a connector
        with patch.object(connectors_service, '_test_connector') as mock_test:
            mock_test.return_value = {'success': True, 'error': None}
            
            connector_id = await connectors_service.create_connector(
                user_id=user_id,
                connector_type=ConnectorType.ZAPIER,
                name='Test Connector',
                webhook_url='https://hooks.zapier.com/hooks/catch/123/'
            )
        
        # Delete the connector
        success = await connectors_service.delete_connector(connector_id, user_id)
        
        assert success is True
        assert connector_id not in connectors_service.connectors
        
        # Try to delete non-existent connector
        success = await connectors_service.delete_connector('non-existent', user_id)
        assert success is False

class TestFallbackAPI:
    """Testes para Fallback API endpoints"""
    
    @pytest.fixture
    def mock_user_token(self):
        """Mock token de usuário válido"""
        return "valid-user-token"
    
    @pytest.fixture
    def user_headers(self, mock_user_token):
        """Headers com token de usuário"""
        return {"Authorization": f"Bearer {mock_user_token}"}
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_handle_unsupported_integration(self, mock_get_user, user_headers):
        """Teste para endpoint de integração não suportada"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        request_data = {
            "integration_name": "slack",
            "context": {
                "use_case": "team communication",
                "required_features": ["send_message", "receive_message"]
            }
        }
        
        with patch('app.api.v1.fallback.fallback_service') as mock_service:
            mock_service.handle_unsupported_integration.return_value = {
                'integration_name': 'slack',
                'supported': False,
                'analysis': {'detected_category': 'messaging', 'has_api': True},
                'suggestions': [
                    {
                        'suggestion_id': 'test-suggestion',
                        'type': 'direct_alternative',
                        'title': 'Use Telegram instead',
                        'description': 'Telegram provides similar functionality',
                        'confidence_score': 0.8,
                        'implementation_effort': 'low',
                        'available_now': True,
                        'details': {},
                        'alternatives': ['telegram']
                    }
                ],
                'can_use_generic_http': True,
                'third_party_options': [],
                'request_integration_url': '/api/v1/integrations/request',
                'estimated_development_time': '2-4 weeks'
            }
            
            response = client.post(
                "/api/v1/fallback/unsupported",
                json=request_data,
                headers=user_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['integration_name'] == 'slack'
            assert data['supported'] is False
            assert len(data['suggestions']) == 1
            assert data['can_use_generic_http'] is True
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_get_integration_suggestions(self, mock_get_user, user_headers):
        """Teste para endpoint de sugestões de integração"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        request_data = {
            "target_integration": "slack",
            "required_capabilities": ["send_message", "receive_message"],
            "use_case": "team communication",
            "strategy": "hybrid"
        }
        
        with patch('app.api.v1.fallback.suggestion_engine') as mock_engine:
            mock_match = MagicMock()
            mock_match.integration_id = 'telegram'
            mock_match.integration_name = 'Telegram'
            mock_match.match_score = 0.8
            mock_match.capability_matches = []
            mock_match.pros = ['Easy setup', 'Free to use']
            mock_match.cons = ['Smaller user base']
            mock_match.setup_complexity = 'Low'
            mock_match.estimated_setup_time = '15-30 minutes'
            mock_match.cost_comparison = {'setup_cost': 0, 'monthly_cost': 0}
            
            mock_engine.suggest_alternatives.return_value = [mock_match]
            
            response = client.post(
                "/api/v1/fallback/suggestions",
                json=request_data,
                headers=user_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['integration_id'] == 'telegram'
            assert data[0]['match_score'] == 0.8
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_create_integration_request(self, mock_get_user, user_headers):
        """Teste para criar solicitação de integração"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        request_data = {
            "integration_name": "notion",
            "description": "Need Notion integration for team documentation",
            "use_case": "Documentation management",
            "priority": "high",
            "business_impact": "High productivity impact",
            "expected_volume": 500
        }
        
        with patch('app.api.v1.fallback.fallback_service') as mock_service:
            mock_service.create_integration_request.return_value = 'request-123'
            
            response = client.post(
                "/api/v1/fallback/requests",
                json=request_data,
                headers=user_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['request_id'] == 'request-123'
            assert 'created successfully' in data['message']
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_list_integration_requests(self, mock_get_user, user_headers):
        """Teste para listar solicitações de integração"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        with patch('app.api.v1.fallback.fallback_service') as mock_service:
            mock_service.get_integration_requests.return_value = [
                {
                    'request_id': 'request-1',
                    'integration_name': 'notion',
                    'integration_url': None,
                    'category': 'productivity',
                    'description': 'Notion integration',
                    'use_case': 'Documentation',
                    'priority': 'high',
                    'business_impact': 'High impact',
                    'expected_volume': 500,
                    'votes': 5,
                    'status': 'pending',
                    'requested_at': datetime.utcnow().isoformat(),
                    'comments_count': 2
                }
            ]
            
            response = client.get(
                "/api/v1/fallback/requests?limit=10&offset=0",
                headers=user_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['integration_name'] == 'notion'
            assert data[0]['votes'] == 5
    
    def test_fallback_endpoints_require_auth(self):
        """Teste que endpoints de fallback requerem autenticação"""
        response = client.post("/api/v1/fallback/unsupported", json={"integration_name": "test"})
        assert response.status_code == 403  # Unauthorized