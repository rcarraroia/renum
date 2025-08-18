"""
Tests for Specialized Sub-Agents
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.agents.base_agent import BaseAgent, AgentCapability, AgentExecutionResult
from app.agents.sa_gmail import GmailAgent
from app.agents.sa_supabase import SupabaseAgent
from app.agents.sa_whatsapp import WhatsAppAgent
from app.agents.sa_telegram import TelegramAgent
from app.agents.sa_http_generic import HTTPGenericAgent
from app.agents.agent_registry import AgentRegistry
from app.domain.credentials import ProviderType

class TestBaseAgent:
    
    @pytest.fixture
    def mock_credentials_service(self):
        """Mock credentials service"""
        return AsyncMock()
    
    @pytest.fixture
    def base_agent(self, mock_credentials_service):
        """Base agent for testing"""
        class TestAgent(BaseAgent):
            def _define_capabilities(self):
                return [
                    AgentCapability(
                        name="test_capability",
                        description="Test capability",
                        input_schema={"type": "object", "properties": {"test": {"type": "string"}}, "required": ["test"]},
                        output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
                        required_credentials=["test_provider"]
                    )
                ]
            
            async def execute_capability(self, capability_name, input_data, user_id, credential_id=None):
                return AgentExecutionResult(success=True, data={"result": "test"})
            
            def _get_supported_providers(self):
                return ["test_provider"]
            
            def _get_category(self):
                return "test"
        
        return TestAgent(
            agent_id="test-agent",
            name="Test Agent",
            description="Test agent for unit tests",
            credentials_service=mock_credentials_service
        )
    
    def test_agent_initialization(self, base_agent):
        """Test agent initialization"""
        assert base_agent.agent_id == "test-agent"
        assert base_agent.name == "Test Agent"
        assert base_agent.version == "1.0.0"
        assert len(base_agent.capabilities) == 1
        assert base_agent.capabilities[0].name == "test_capability"
    
    def test_has_capability(self, base_agent):
        """Test capability checking"""
        assert base_agent.has_capability("test_capability") == True
        assert base_agent.has_capability("nonexistent_capability") == False
    
    def test_get_capability(self, base_agent):
        """Test getting capability"""
        capability = base_agent.get_capability("test_capability")
        assert capability is not None
        assert capability.name == "test_capability"
        
        nonexistent = base_agent.get_capability("nonexistent")
        assert nonexistent is None
    
    @pytest.mark.asyncio
    async def test_validate_input_success(self, base_agent):
        """Test successful input validation"""
        is_valid, error = await base_agent.validate_input("test_capability", {"test": "value"})
        assert is_valid == True
        assert error is None
    
    @pytest.mark.asyncio
    async def test_validate_input_missing_field(self, base_agent):
        """Test input validation with missing required field"""
        is_valid, error = await base_agent.validate_input("test_capability", {})
        assert is_valid == False
        assert "test" in error
    
    @pytest.mark.asyncio
    async def test_validate_input_nonexistent_capability(self, base_agent):
        """Test input validation for nonexistent capability"""
        is_valid, error = await base_agent.validate_input("nonexistent", {"test": "value"})
        assert is_valid == False
        assert "não encontrada" in error
    
    def test_get_manifest(self, base_agent):
        """Test getting agent manifest"""
        manifest = base_agent.get_manifest()
        
        assert manifest['agent_id'] == "test-agent"
        assert manifest['name'] == "Test Agent"
        assert manifest['version'] == "1.0.0"
        assert len(manifest['capabilities']) == 1
        assert manifest['supported_providers'] == ["test_provider"]
        assert manifest['metadata']['category'] == "test"
    
    @pytest.mark.asyncio
    async def test_health_check(self, base_agent):
        """Test agent health check"""
        with patch.object(base_agent.http_client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            health = await base_agent.health_check()
            
            assert health['status'] == 'healthy'
            assert health['agent_id'] == "test-agent"
            assert 'response_time_ms' in health
            assert 'capabilities_count' in health

class TestGmailAgent:
    
    @pytest.fixture
    def gmail_agent(self):
        """Gmail agent for testing"""
        return GmailAgent()
    
    def test_gmail_agent_initialization(self, gmail_agent):
        """Test Gmail agent initialization"""
        assert gmail_agent.agent_id == "sa-gmail"
        assert gmail_agent.name == "Gmail Agent"
        assert len(gmail_agent.capabilities) > 0
        assert gmail_agent.has_capability("send_email")
        assert gmail_agent.has_capability("read_emails")
        assert "google" in gmail_agent._get_supported_providers()
    
    def test_gmail_capabilities(self, gmail_agent):
        """Test Gmail agent capabilities"""
        capabilities = [cap.name for cap in gmail_agent.capabilities]
        
        expected_capabilities = [
            "send_email",
            "read_emails", 
            "create_draft",
            "send_draft"
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities
    
    @pytest.mark.asyncio
    async def test_send_email_validation(self, gmail_agent):
        """Test send_email input validation"""
        # Valid input
        valid_input = {
            "to": ["test@example.com"],
            "subject": "Test Subject",
            "body": "Test Body"
        }
        is_valid, error = await gmail_agent.validate_input("send_email", valid_input)
        assert is_valid == True
        
        # Missing required field
        invalid_input = {
            "to": ["test@example.com"],
            "subject": "Test Subject"
            # Missing body
        }
        is_valid, error = await gmail_agent.validate_input("send_email", invalid_input)
        assert is_valid == False

class TestSupabaseAgent:
    
    @pytest.fixture
    def supabase_agent(self):
        """Supabase agent for testing"""
        return SupabaseAgent()
    
    def test_supabase_agent_initialization(self, supabase_agent):
        """Test Supabase agent initialization"""
        assert supabase_agent.agent_id == "sa-supabase"
        assert supabase_agent.name == "Supabase Agent"
        assert len(supabase_agent.capabilities) > 0
        assert supabase_agent.has_capability("select_data")
        assert supabase_agent.has_capability("insert_data")
        assert "supabase" in supabase_agent._get_supported_providers()
    
    def test_supabase_capabilities(self, supabase_agent):
        """Test Supabase agent capabilities"""
        capabilities = [cap.name for cap in supabase_agent.capabilities]
        
        expected_capabilities = [
            "select_data",
            "insert_data",
            "update_data",
            "delete_data",
            "execute_rpc",
            "get_table_schema"
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities
    
    @pytest.mark.asyncio
    async def test_select_data_validation(self, supabase_agent):
        """Test select_data input validation"""
        # Valid input
        valid_input = {
            "table": "users"
        }
        is_valid, error = await supabase_agent.validate_input("select_data", valid_input)
        assert is_valid == True
        
        # Missing required field
        invalid_input = {}
        is_valid, error = await supabase_agent.validate_input("select_data", invalid_input)
        assert is_valid == False

class TestWhatsAppAgent:
    
    @pytest.fixture
    def whatsapp_agent(self):
        """WhatsApp agent for testing"""
        return WhatsAppAgent()
    
    def test_whatsapp_agent_initialization(self, whatsapp_agent):
        """Test WhatsApp agent initialization"""
        assert whatsapp_agent.agent_id == "sa-whatsapp"
        assert whatsapp_agent.name == "WhatsApp Agent"
        assert len(whatsapp_agent.capabilities) > 0
        assert whatsapp_agent.has_capability("send_text_message")
        assert whatsapp_agent.has_capability("send_template_message")
        assert "whatsapp_business" in whatsapp_agent._get_supported_providers()
    
    def test_whatsapp_capabilities(self, whatsapp_agent):
        """Test WhatsApp agent capabilities"""
        capabilities = [cap.name for cap in whatsapp_agent.capabilities]
        
        expected_capabilities = [
            "send_text_message",
            "send_template_message",
            "send_media_message",
            "send_interactive_message",
            "get_message_status",
            "upload_media"
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities
    
    @pytest.mark.asyncio
    async def test_send_text_message_validation(self, whatsapp_agent):
        """Test send_text_message input validation"""
        # Valid input
        valid_input = {
            "to": "5511999999999",
            "message": "Test message"
        }
        is_valid, error = await whatsapp_agent.validate_input("send_text_message", valid_input)
        assert is_valid == True
        
        # Missing required field
        invalid_input = {
            "to": "5511999999999"
            # Missing message
        }
        is_valid, error = await whatsapp_agent.validate_input("send_text_message", invalid_input)
        assert is_valid == False

class TestTelegramAgent:
    
    @pytest.fixture
    def telegram_agent(self):
        """Telegram agent for testing"""
        return TelegramAgent()
    
    def test_telegram_agent_initialization(self, telegram_agent):
        """Test Telegram agent initialization"""
        assert telegram_agent.agent_id == "sa-telegram"
        assert telegram_agent.name == "Telegram Agent"
        assert len(telegram_agent.capabilities) > 0
        assert telegram_agent.has_capability("send_message")
        assert telegram_agent.has_capability("send_photo")
        assert "telegram" in telegram_agent._get_supported_providers()
    
    def test_telegram_capabilities(self, telegram_agent):
        """Test Telegram agent capabilities"""
        capabilities = [cap.name for cap in telegram_agent.capabilities]
        
        expected_capabilities = [
            "send_message",
            "send_photo",
            "send_document",
            "send_keyboard",
            "get_updates",
            "get_chat_info"
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities
    
    @pytest.mark.asyncio
    async def test_send_message_validation(self, telegram_agent):
        """Test send_message input validation"""
        # Valid input
        valid_input = {
            "chat_id": "123456789",
            "text": "Test message"
        }
        is_valid, error = await telegram_agent.validate_input("send_message", valid_input)
        assert is_valid == True
        
        # Missing required field
        invalid_input = {
            "chat_id": "123456789"
            # Missing text
        }
        is_valid, error = await telegram_agent.validate_input("send_message", invalid_input)
        assert is_valid == False

class TestHTTPGenericAgent:
    
    @pytest.fixture
    def http_agent(self):
        """HTTP Generic agent for testing"""
        return HTTPGenericAgent()
    
    def test_http_agent_initialization(self, http_agent):
        """Test HTTP Generic agent initialization"""
        assert http_agent.agent_id == "sa-http-generic"
        assert http_agent.name == "HTTP Generic Agent"
        assert len(http_agent.capabilities) > 0
        assert http_agent.has_capability("http_request")
        assert http_agent.has_capability("rest_get")
        assert "custom_api" in http_agent._get_supported_providers()
    
    def test_http_capabilities(self, http_agent):
        """Test HTTP Generic agent capabilities"""
        capabilities = [cap.name for cap in http_agent.capabilities]
        
        expected_capabilities = [
            "http_request",
            "rest_get",
            "rest_post",
            "rest_put",
            "rest_delete",
            "webhook_call"
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities
    
    @pytest.mark.asyncio
    async def test_http_request_validation(self, http_agent):
        """Test http_request input validation"""
        # Valid input
        valid_input = {
            "method": "GET",
            "url": "https://api.example.com/test"
        }
        is_valid, error = await http_agent.validate_input("http_request", valid_input)
        assert is_valid == True
        
        # Missing required field
        invalid_input = {
            "method": "GET"
            # Missing url
        }
        is_valid, error = await http_agent.validate_input("http_request", invalid_input)
        assert is_valid == False

class TestAgentRegistry:
    
    @pytest.fixture
    def agent_registry(self):
        """Agent registry for testing"""
        return AgentRegistry()
    
    def test_registry_initialization(self, agent_registry):
        """Test agent registry initialization"""
        assert len(agent_registry._agents) > 0
        assert "sa-gmail" in agent_registry._agents
        assert "sa-supabase" in agent_registry._agents
        assert "sa-whatsapp" in agent_registry._agents
        assert "sa-telegram" in agent_registry._agents
        assert "sa-http-generic" in agent_registry._agents
    
    def test_get_agent(self, agent_registry):
        """Test getting agent by ID"""
        gmail_agent = agent_registry.get_agent("sa-gmail")
        assert gmail_agent is not None
        assert gmail_agent.agent_id == "sa-gmail"
        
        nonexistent = agent_registry.get_agent("nonexistent")
        assert nonexistent is None
    
    def test_list_agents(self, agent_registry):
        """Test listing all agents"""
        agents = agent_registry.list_agents()
        assert len(agents) >= 5  # At least the 5 implemented agents
        
        agent_ids = [agent.agent_id for agent in agents]
        assert "sa-gmail" in agent_ids
        assert "sa-supabase" in agent_ids
    
    def test_get_agents_by_category(self, agent_registry):
        """Test getting agents by category"""
        messaging_agents = agent_registry.get_agents_by_category("messaging")
        assert len(messaging_agents) >= 2  # WhatsApp and Telegram
        
        messaging_ids = [agent.agent_id for agent in messaging_agents]
        assert "sa-whatsapp" in messaging_ids
        assert "sa-telegram" in messaging_ids
    
    def test_get_agents_by_provider(self, agent_registry):
        """Test getting agents by provider"""
        google_agents = agent_registry.get_agents_by_provider("google")
        assert len(google_agents) >= 1  # Gmail agent
        
        google_ids = [agent.agent_id for agent in google_agents]
        assert "sa-gmail" in google_ids
    
    def test_search_agents_by_capability(self, agent_registry):
        """Test searching agents by capability"""
        # Search for a capability that multiple agents might have
        agents_with_send = agent_registry.search_agents_by_capability("send_text_message")
        assert len(agents_with_send) >= 1  # WhatsApp agent
        
        # Search for specific capability
        gmail_agents = agent_registry.search_agents_by_capability("send_email")
        assert len(gmail_agents) == 1
        assert gmail_agents[0].agent_id == "sa-gmail"
    
    def test_get_registry_stats(self, agent_registry):
        """Test getting registry statistics"""
        stats = agent_registry.get_registry_stats()
        
        assert 'total_agents' in stats
        assert 'categories' in stats
        assert 'supported_providers' in stats
        assert 'total_capabilities' in stats
        assert 'agents' in stats
        
        assert stats['total_agents'] >= 5
        assert len(stats['agents']) >= 5
        assert 'messaging' in stats['categories']
        assert 'google' in stats['supported_providers']
    
    def test_get_agent_manifest(self, agent_registry):
        """Test getting agent manifest"""
        manifest = agent_registry.get_agent_manifest("sa-gmail")
        
        assert manifest is not None
        assert manifest['agent_id'] == "sa-gmail"
        assert manifest['name'] == "Gmail Agent"
        assert 'capabilities' in manifest
        assert 'supported_providers' in manifest
    
    def test_get_all_manifests(self, agent_registry):
        """Test getting all agent manifests"""
        manifests = agent_registry.get_all_manifests()
        
        assert len(manifests) >= 5
        assert "sa-gmail" in manifests
        assert "sa-supabase" in manifests
        
        for agent_id, manifest in manifests.items():
            assert manifest['agent_id'] == agent_id
            assert 'capabilities' in manifest
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, agent_registry):
        """Test health check for all agents"""
        with patch('app.agents.base_agent.BaseAgent.health_check') as mock_health:
            mock_health.return_value = {
                'status': 'healthy',
                'agent_id': 'test',
                'version': '1.0.0',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            health_results = await agent_registry.health_check_all()
            
            assert len(health_results) >= 5
            for agent_id, health in health_results.items():
                assert 'status' in health
                assert 'agent_id' in health
    
    def test_register_unregister_agent(self, agent_registry):
        """Test dynamic agent registration and unregistration"""
        # Create a mock agent
        mock_agent = MagicMock()
        mock_agent.agent_id = "test-dynamic-agent"
        
        # Register agent
        initial_count = len(agent_registry._agents)
        agent_registry.register_agent(mock_agent)
        
        assert len(agent_registry._agents) == initial_count + 1
        assert agent_registry.get_agent("test-dynamic-agent") == mock_agent
        
        # Unregister agent
        success = agent_registry.unregister_agent("test-dynamic-agent")
        assert success == True
        assert len(agent_registry._agents) == initial_count
        assert agent_registry.get_agent("test-dynamic-agent") is None
        
        # Try to unregister nonexistent agent
        success = agent_registry.unregister_agent("nonexistent")
        assert success == False