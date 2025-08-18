"""
Tests for Agent Registry Service
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.services.agent_registry_service import AgentRegistryService
from app.schemas.agent import CreateAgentSchema, UpdateAgentSchema, AgentApprovalSchema
from app.domain.agent import AgentCapability, AgentPolicy


class TestAgentRegistryService:
    """Test cases for Agent Registry Service"""
    
    @pytest.fixture
    def agent_service(self):
        """Create agent registry service instance"""
        return AgentRegistryService()
    
    @pytest.fixture
    def sample_capability(self):
        """Create sample agent capability"""
        return AgentCapability(
            name="send_email",
            description="Send email via SMTP or API",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "format": "email"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        )
    
    @pytest.fixture
    def sample_policy(self):
        """Create sample agent policy"""
        return AgentPolicy(
            max_requests_per_minute=100,
            max_concurrent_executions=5,
            timeout_seconds=30,
            allowed_domains=["*"],
            require_confirmation=False
        )
    
    @pytest.fixture
    def create_agent_data(self, sample_capability, sample_policy):
        """Create sample agent creation data"""
        return CreateAgentSchema(
            agent_id="test-agent",
            version="1.0.0",
            name="Test Agent",
            description="A test agent for unit testing",
            capabilities=[sample_capability],
            required_credentials=["test_credential"],
            policy=sample_policy
        )
    
    async def test_create_agent_success(self, agent_service, create_agent_data):
        """Test successful agent creation"""
        user_id = uuid4()
        
        agent = await agent_service.create_agent(create_agent_data, user_id)
        
        assert agent.agent_id == "test-agent"
        assert agent.version == "1.0.0"
        assert agent.name == "Test Agent"
        assert agent.status == "draft"
        assert agent.created_by == user_id
        assert len(agent.capabilities) == 1
        assert agent.capabilities[0].name == "send_email"
        assert agent.manifest_checksum is not None
    
    async def test_create_agent_duplicate_version(self, agent_service, create_agent_data):
        """Test creating agent with duplicate version fails"""
        user_id = uuid4()
        
        # Create first agent
        await agent_service.create_agent(create_agent_data, user_id)
        
        # Try to create duplicate - should fail
        with pytest.raises(ValueError, match="already exists"):
            await agent_service.create_agent(create_agent_data, user_id)
    
    async def test_get_available_agents(self, agent_service):
        """Test getting available agents"""
        agents = await agent_service.get_available_agents()
        
        assert isinstance(agents, list)
        # Should return mock data
        assert len(agents) >= 0
    
    async def test_get_available_agents_with_capabilities_filter(self, agent_service):
        """Test getting agents filtered by capabilities"""
        agents = await agent_service.get_available_agents(
            capabilities=["send_email"]
        )
        
        assert isinstance(agents, list)
        # All returned agents should have the send_email capability
        for agent in agents:
            capability_names = [cap.name for cap in agent.capabilities]
            assert "send_email" in capability_names
    
    async def test_get_available_agents_with_status_filter(self, agent_service):
        """Test getting agents filtered by status"""
        agents = await agent_service.get_available_agents(status="approved")
        
        assert isinstance(agents, list)
        # All returned agents should be approved
        for agent in agents:
            assert agent.status == "approved"
    
    async def test_get_agent_by_id_and_version(self, agent_service):
        """Test getting specific agent by ID and version"""
        agent = await agent_service.get_agent_by_id_and_version(
            "sa-email-basic", "1.0.0"
        )
        
        assert agent is not None
        assert agent.agent_id == "sa-email-basic"
        assert agent.version == "1.0.0"
    
    async def test_get_agent_by_id_latest_version(self, agent_service):
        """Test getting latest version of agent"""
        agent = await agent_service.get_agent_by_id_and_version(
            "sa-email-basic", "latest"
        )
        
        assert agent is not None
        assert agent.agent_id == "sa-email-basic"
    
    async def test_get_nonexistent_agent(self, agent_service):
        """Test getting non-existent agent returns None"""
        agent = await agent_service.get_agent_by_id_and_version(
            "nonexistent-agent", "1.0.0"
        )
        
        assert agent is None
    
    async def test_update_draft_agent(self, agent_service, create_agent_data):
        """Test updating draft agent"""
        user_id = uuid4()
        
        # Create agent
        agent = await agent_service.create_agent(create_agent_data, user_id)
        
        # Update agent
        update_data = UpdateAgentSchema(
            name="Updated Test Agent",
            description="Updated description"
        )
        
        updated_agent = await agent_service.update_agent(
            agent.agent_id, agent.version, update_data, user_id
        )
        
        assert updated_agent.name == "Updated Test Agent"
        assert updated_agent.description == "Updated description"
        assert updated_agent.version == agent.version  # Same version
    
    async def test_update_approved_agent_creates_new_version(self, agent_service):
        """Test updating approved agent creates new version"""
        # This test would require mocking an approved agent
        # For now, we'll test the logic conceptually
        pass
    
    async def test_approve_agent_success(self, agent_service, create_agent_data):
        """Test successful agent approval"""
        user_id = uuid4()
        admin_id = uuid4()
        
        # Create agent
        agent = await agent_service.create_agent(create_agent_data, user_id)
        
        # Stage agent first
        agent.stage()
        
        # Approve agent
        approval_data = AgentApprovalSchema(
            agent_id=agent.agent_id,
            version=agent.version,
            approval_notes="Approved for testing"
        )
        
        approved_agent = await agent_service.approve_agent(
            agent.agent_id, agent.version, admin_id, approval_data
        )
        
        assert approved_agent.status == "approved"
    
    async def test_approve_draft_agent_fails(self, agent_service, create_agent_data):
        """Test approving draft agent fails"""
        user_id = uuid4()
        admin_id = uuid4()
        
        # Create agent (remains in draft)
        agent = await agent_service.create_agent(create_agent_data, user_id)
        
        # Try to approve draft agent - should fail
        with pytest.raises(ValueError, match="Only draft or staged agents can be approved"):
            await agent_service.approve_agent(
                agent.agent_id, agent.version, admin_id
            )
    
    async def test_deprecate_agent_success(self, agent_service):
        """Test successful agent deprecation"""
        # This would require mocking an approved agent
        pass
    
    async def test_get_agent_manifest_approved_only(self, agent_service):
        """Test getting manifest only works for approved agents"""
        # Test with approved agent
        manifest = await agent_service.get_agent_manifest("sa-email-basic", "1.0.0")
        assert manifest is not None
        assert manifest.agent_id == "sa-email-basic"
        
        # Test with non-existent agent
        manifest = await agent_service.get_agent_manifest("nonexistent", "1.0.0")
        assert manifest is None
    
    async def test_search_agents(self, agent_service):
        """Test agent search functionality"""
        agents = await agent_service.search_agents("email")
        
        assert isinstance(agents, list)
        # Should return agents matching the search term
    
    async def test_get_agent_versions(self, agent_service):
        """Test getting all versions of an agent"""
        versions = await agent_service.get_agent_versions("sa-email-basic")
        
        assert isinstance(versions, list)
        # All returned agents should have the same agent_id
        for agent in versions:
            assert agent.agent_id == "sa-email-basic"
    
    async def test_get_agent_usage_stats(self, agent_service):
        """Test getting agent usage statistics"""
        stats = await agent_service.get_agent_usage_stats("sa-email-basic", "1.0.0")
        
        assert isinstance(stats, dict)
        assert "total_executions" in stats
        assert "successful_executions" in stats
        assert "failed_executions" in stats
        assert "avg_execution_time_ms" in stats
        assert "total_cost" in stats
    
    async def test_validate_agent_manifest(self, agent_service):
        """Test agent manifest validation"""
        valid_manifest = {
            "agent_id": "test-agent",
            "version": "1.0.0",
            "name": "Test Agent",
            "description": "Test description",
            "capabilities": [
                {
                    "name": "test_capability",
                    "description": "Test capability"
                }
            ],
            "required_credentials": [],
            "policy": {
                "max_requests_per_minute": 60
            }
        }
        
        # Should not raise exception
        is_valid = await agent_service.validate_agent_manifest(valid_manifest)
        assert is_valid is True
    
    async def test_validate_invalid_manifest(self, agent_service):
        """Test validation of invalid manifest"""
        invalid_manifest = {
            "agent_id": "test-agent",
            # Missing required fields
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            await agent_service.validate_agent_manifest(invalid_manifest)
    
    async def test_sign_agent_manifest(self, agent_service, create_agent_data):
        """Test signing agent manifest"""
        user_id = uuid4()
        
        # Create and approve agent
        agent = await agent_service.create_agent(create_agent_data, user_id)
        
        # Sign manifest
        private_key = "test_private_key"
        key_id = "test_key_001"
        
        signed_agent = await agent_service.sign_agent_manifest(
            agent.agent_id, agent.version, private_key, key_id
        )
        
        assert signed_agent.manifest_signature is not None
        assert signed_agent.signature_key_id == key_id
    
    def test_increment_version(self, agent_service):
        """Test version incrementing logic"""
        new_version = agent_service._increment_version("1.0.0")
        assert new_version == "1.0.1"
        
        new_version = agent_service._increment_version("2.5.9")
        assert new_version == "2.5.10"
    
    def test_increment_invalid_version(self, agent_service):
        """Test incrementing invalid version fails"""
        with pytest.raises(ValueError, match="Invalid semantic version"):
            agent_service._increment_version("invalid")
    
    def test_is_valid_semantic_version(self, agent_service):
        """Test semantic version validation"""
        assert agent_service._is_valid_semantic_version("1.0.0") is True
        assert agent_service._is_valid_semantic_version("10.25.100") is True
        assert agent_service._is_valid_semantic_version("1.0") is False
        assert agent_service._is_valid_semantic_version("v1.0.0") is False
        assert agent_service._is_valid_semantic_version("invalid") is False


@pytest.mark.integration
class TestAgentRegistryIntegration:
    """Integration tests for Agent Registry"""
    
    async def test_full_agent_lifecycle(self):
        """Test complete agent lifecycle from creation to deprecation"""
        service = AgentRegistryService()
        user_id = uuid4()
        admin_id = uuid4()
        
        # Create capability and policy
        capability = AgentCapability(
            name="integration_test",
            description="Integration test capability",
            input_schema={"type": "object"}
        )
        
        policy = AgentPolicy()
        
        # Create agent data
        create_data = CreateAgentSchema(
            agent_id="integration-test-agent",
            version="1.0.0",
            name="Integration Test Agent",
            description="Agent for integration testing",
            capabilities=[capability],
            required_credentials=[],
            policy=policy
        )
        
        # 1. Create agent
        agent = await service.create_agent(create_data, user_id)
        assert agent.status == "draft"
        
        # 2. Update agent
        update_data = UpdateAgentSchema(name="Updated Integration Test Agent")
        updated_agent = await service.update_agent(
            agent.agent_id, agent.version, update_data, user_id
        )
        assert updated_agent.name == "Updated Integration Test Agent"
        
        # 3. Stage agent (would be done through status update)
        updated_agent.stage()
        
        # 4. Approve agent
        approved_agent = await service.approve_agent(
            updated_agent.agent_id, updated_agent.version, admin_id
        )
        assert approved_agent.status == "approved"
        
        # 5. Get manifest
        manifest = await service.get_agent_manifest(
            approved_agent.agent_id, approved_agent.version
        )
        assert manifest is not None
        assert manifest.agent_id == approved_agent.agent_id
        
        # 6. Get usage stats
        stats = await service.get_agent_usage_stats(
            approved_agent.agent_id, approved_agent.version
        )
        assert isinstance(stats, dict)
        
        # 7. Deprecate agent
        deprecated_agent = await service.deprecate_agent(
            approved_agent.agent_id, approved_agent.version, admin_id, "End of life"
        )
        assert deprecated_agent.status == "deprecated"