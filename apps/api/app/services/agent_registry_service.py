"""
Agent Registry Service for multi-agent system
Handles agent CRUD operations, versioning, and approval workflow
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from app.domain.agent import Agent, AgentCapability, AgentPolicy, AgentDependency
from app.schemas.agent import (
    CreateAgentSchema, 
    UpdateAgentSchema, 
    AgentManifest,
    AgentApprovalSchema
)
from app.repositories.agent_repository import AgentRepository


class AgentRegistryService:
    """Service for managing agent registry with versioning and approval workflow"""
    
    def __init__(self, agent_repository: Optional[AgentRepository] = None):
        self.agent_repo = agent_repository or AgentRepository()
    
    async def create_agent(self, agent_data: CreateAgentSchema, created_by: UUID) -> Agent:
        """Create new agent with versioning"""
        
        # Check if agent_id + version combination already exists
        if await self.agent_repo.exists_agent_version(agent_data.agent_id, agent_data.version):
            raise ValueError(f"Agent {agent_data.agent_id} version {agent_data.version} already exists")
        
        # Convert schemas to domain objects
        capabilities = []
        for cap_schema in agent_data.capabilities:
            capability = AgentCapability(
                name=cap_schema.name,
                description=cap_schema.description,
                input_schema=cap_schema.input_schema,
                output_schema=cap_schema.output_schema
            )
            capabilities.append(capability)
        
        # Convert policy
        policy = AgentPolicy(
            max_requests_per_minute=agent_data.policy.max_requests_per_minute,
            max_concurrent_executions=agent_data.policy.max_concurrent_executions,
            timeout_seconds=agent_data.policy.timeout_seconds,
            allowed_domains=agent_data.policy.allowed_domains,
            require_confirmation=agent_data.policy.require_confirmation,
            cost_per_execution=agent_data.policy.cost_per_execution
        )
        
        # Convert dependencies
        dependencies = []
        for dep_schema in agent_data.dependencies:
            dependency = AgentDependency(
                agent_id=dep_schema.agent_id,
                version=dep_schema.version,
                optional=dep_schema.optional
            )
            dependencies.append(dependency)
        
        # Create agent domain object
        agent = Agent(
            agent_id=agent_data.agent_id,
            version=agent_data.version,
            name=agent_data.name,
            description=agent_data.description,
            capabilities=capabilities,
            input_schema=agent_data.input_schema,
            policy=policy,
            dependencies=dependencies,
            status='active',  # New agents start as active
            created_by=created_by
        )
        
        # Calculate checksum
        agent.manifest_checksum = agent.calculate_checksum()
        
        # Save to database
        return await self.agent_repo.save(agent)
    
    async def update_agent(
        self, 
        agent_id: str, 
        version: str, 
        update_data: UpdateAgentSchema,
        updated_by: UUID
    ) -> Agent:
        """Update existing agent (creates new version if needed)"""
        
        existing_agent = await self.agent_repo.find_by_agent_id_and_version(agent_id, version)
        if not existing_agent:
            raise ValueError(f"Agent {agent_id} version {version} not found")
        
        # If agent is in use, create new version instead of updating
        if existing_agent.status == 'active' and self._should_create_new_version(update_data):
            new_version = self._increment_version(version)
            
            # Create new version with updates
            create_data = CreateAgentSchema(
                agent_id=agent_id,
                version=new_version,
                name=update_data.name or existing_agent.name,
                description=update_data.description or existing_agent.description,
                capabilities=update_data.capabilities or [
                    self._capability_to_schema(cap) for cap in existing_agent.capabilities
                ],
                input_schema=update_data.input_schema or existing_agent.input_schema,
                policy=update_data.policy or self._policy_to_schema(existing_agent.policy),
                dependencies=update_data.dependencies or [
                    self._dependency_to_schema(dep) for dep in existing_agent.dependencies
                ]
            )
            
            return await self.create_agent(create_data, updated_by)
        
        # Update existing agent in place
        if update_data.name:
            existing_agent.name = update_data.name
        if update_data.description is not None:
            existing_agent.description = update_data.description
        if update_data.capabilities:
            existing_agent.capabilities = [
                AgentCapability(
                    name=cap.name,
                    description=cap.description,
                    input_schema=cap.input_schema,
                    output_schema=cap.output_schema
                ) for cap in update_data.capabilities
            ]
        if update_data.input_schema:
            existing_agent.input_schema = update_data.input_schema
        if update_data.policy:
            existing_agent.policy = AgentPolicy(
                max_requests_per_minute=update_data.policy.max_requests_per_minute,
                max_concurrent_executions=update_data.policy.max_concurrent_executions,
                timeout_seconds=update_data.policy.timeout_seconds,
                allowed_domains=update_data.policy.allowed_domains,
                require_confirmation=update_data.policy.require_confirmation,
                cost_per_execution=update_data.policy.cost_per_execution
            )
        if update_data.dependencies:
            existing_agent.dependencies = [
                AgentDependency(
                    agent_id=dep.agent_id,
                    version=dep.version,
                    optional=dep.optional
                ) for dep in update_data.dependencies
            ]
        if update_data.status:
            existing_agent.status = update_data.status
        
        existing_agent.updated_at = datetime.utcnow()
        existing_agent.manifest_checksum = existing_agent.calculate_checksum()
        
        # Save to database
        return await self.agent_repo.save(existing_agent)
    
    async def get_available_agents(
        self, 
        capabilities: Optional[List[str]] = None,
        status: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> List[Agent]:
        """Get agents matching specified criteria"""
        
        return await self.agent_repo.find_all(
            status=status,
            capabilities=capabilities
        )
    
    async def get_agent_by_id_and_version(
        self, 
        agent_id: str, 
        version: str = "latest"
    ) -> Optional[Agent]:
        """Get specific agent by ID and version"""
        
        return await self.agent_repo.find_by_agent_id_and_version(agent_id, version)
    
    async def get_agent_versions(self, agent_id: str) -> List[Agent]:
        """Get all versions of a specific agent"""
        
        return await self.agent_repo.find_versions(agent_id)
    
    async def search_agents(
        self,
        query: str,
        capabilities: Optional[List[str]] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Agent]:
        """Search agents by name, description, or capabilities"""
        
        return await self.agent_repo.search(
            query=query,
            capabilities=capabilities,
            status=status,
            limit=limit
        )
    
    async def approve_agent(
        self, 
        agent_id: str, 
        version: str, 
        approved_by: UUID,
        approval_data: Optional[AgentApprovalSchema] = None
    ) -> Agent:
        """Approve agent for production use"""
        
        agent = await self.agent_repo.find_by_agent_id_and_version(agent_id, version)
        if not agent:
            raise ValueError(f"Agent {agent_id} version {version} not found")
        
        if agent.status not in ['active', 'inactive']:
            raise ValueError(f"Only active or inactive agents can be approved. Current status: {agent.status}")
        
        # Validate agent is ready for approval
        if not agent.capabilities:
            raise ValueError("Agent must have at least one capability")
        
        if not agent.manifest_checksum:
            agent.manifest_checksum = agent.calculate_checksum()
        
        # Approve the agent
        agent.approve(approved_by)
        
        # Save to database
        saved_agent = await self.agent_repo.save(agent)
        
        # Log approval (in real implementation, would use audit service)
        await self._log_agent_action(
            agent_id=agent.id,
            action='approve',
            performed_by=approved_by,
            details={
                'version': version,
                'notes': approval_data.approval_notes if approval_data else None
            }
        )
        
        return saved_agent
    
    async def deprecate_agent(
        self, 
        agent_id: str, 
        version: str, 
        deprecated_by: UUID,
        reason: Optional[str] = None
    ) -> Agent:
        """Deprecate an active agent"""
        
        agent = await self.agent_repo.find_by_agent_id_and_version(agent_id, version)
        if not agent:
            raise ValueError(f"Agent {agent_id} version {version} not found")
        
        if agent.status not in ['active']:
            raise ValueError("Only active agents can be deprecated")
        
        # Deprecate the agent
        agent.deprecate(deprecated_by)
        
        # Save to database
        saved_agent = await self.agent_repo.save(agent)
        
        # Log deprecation
        await self._log_agent_action(
            agent_id=agent.id,
            action='deprecate',
            performed_by=deprecated_by,
            details={
                'version': version,
                'reason': reason
            }
        )
        
        return saved_agent
    
    async def delete_agent(self, agent_id: str, version: str, deleted_by: UUID) -> bool:
        """Delete agent (only if not in use)"""
        
        agent = await self.agent_repo.find_by_agent_id_and_version(agent_id, version)
        if not agent:
            raise ValueError(f"Agent {agent_id} version {version} not found")
        
        # Check if agent is in use (would check executions table)
        # For now, only allow deletion of inactive agents
        if agent.status == 'active':
            raise ValueError("Cannot delete active agent. Deprecate it first.")
        
        # Log deletion
        await self._log_agent_action(
            agent_id=agent.id,
            action='delete',
            performed_by=deleted_by,
            details={
                'version': version,
                'agent_name': agent.name
            }
        )
        
        return await self.agent_repo.delete(agent.id)
    
    async def get_agent_manifest(
        self, 
        agent_id: str, 
        version: str = "latest"
    ) -> Optional[AgentManifest]:
        """Get agent manifest for execution"""
        
        agent = await self.agent_repo.find_by_agent_id_and_version(agent_id, version)
        if not agent:
            return None
        
        if agent.status not in ['active']:
            raise ValueError("Only active agents can have manifests generated")
        
        manifest_data = agent.generate_manifest()
        
        return AgentManifest(
            agent_id=manifest_data['agent_id'],
            version=manifest_data['version'],
            name=manifest_data['name'],
            description=manifest_data['description'],
            capabilities=[
                self._capability_dict_to_schema(cap) for cap in manifest_data['capabilities']
            ],
            input_schema=manifest_data['input_schema'],
            policy=self._policy_dict_to_schema(manifest_data['policy']),
            dependencies=[
                self._dependency_dict_to_schema(dep) for dep in manifest_data['dependencies']
            ],
            checksum=manifest_data['checksum'],
            signature=manifest_data['signature'],
            signature_key_id=manifest_data['signature_key_id']
        )
    
    async def get_agent_usage_stats(self, agent_id: str, version: str) -> Dict[str, Any]:
        """Get usage statistics for an agent"""
        
        return await self.agent_repo.get_usage_stats(agent_id, version)
    
    async def validate_agent_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Validate agent manifest structure and integrity"""
        
        required_fields = [
            'agent_id', 'version', 'name', 'description', 
            'capabilities', 'policy'
        ]
        
        for field in required_fields:
            if field not in manifest:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate semantic versioning
        version = manifest['version']
        if not self._is_valid_semantic_version(version):
            raise ValueError(f"Invalid semantic version: {version}")
        
        # Validate capabilities structure
        capabilities = manifest['capabilities']
        if not isinstance(capabilities, list) or not capabilities:
            raise ValueError("Capabilities must be a non-empty list")
        
        for cap in capabilities:
            if not isinstance(cap, dict) or 'name' not in cap:
                raise ValueError("Each capability must have a 'name' field")
        
        return True
    
    async def sign_agent_manifest(
        self, 
        agent_id: str, 
        version: str, 
        private_key: str,
        key_id: str
    ) -> Agent:
        """Sign agent manifest with digital signature"""
        
        agent = await self.agent_repo.find_by_agent_id_and_version(agent_id, version)
        if not agent:
            raise ValueError(f"Agent {agent_id} version {version} not found")
        
        # Generate manifest for signing
        manifest = agent.generate_manifest()
        manifest_json = json.dumps(manifest, sort_keys=True, separators=(',', ':'))
        
        # Calculate signature (placeholder - would use actual cryptographic signing)
        signature = self._calculate_signature(manifest_json, private_key)
        
        # Update agent with signature
        agent.sign_manifest(signature, key_id)
        
        # Save to database
        return await self.agent_repo.save(agent)
    
    def _should_create_new_version(self, update_data: UpdateAgentSchema) -> bool:
        """Determine if update requires new version"""
        
        # Create new version if capabilities or policy change
        return (
            update_data.capabilities is not None or 
            update_data.policy is not None or
            update_data.input_schema is not None
        )
    
    def _increment_version(self, version: str) -> str:
        """Increment semantic version"""
        parts = version.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid semantic version format")
        
        major, minor, patch = map(int, parts)
        
        # Increment patch version
        patch += 1
        
        return f"{major}.{minor}.{patch}"
    
    def _is_valid_semantic_version(self, version: str) -> bool:
        """Check if version follows semantic versioning"""
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
    
    def _calculate_signature(self, data: str, private_key: str) -> str:
        """Calculate digital signature (placeholder implementation)"""
        # In real implementation, would use cryptographic library like cryptography
        # For now, return a mock signature
        return hashlib.sha256(f"{data}{private_key}".encode()).hexdigest()
    
    async def _log_agent_action(
        self, 
        agent_id: UUID, 
        action: str, 
        performed_by: UUID,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log agent-related actions for audit trail"""
        
        log_entry = {
            'agent_id': str(agent_id),
            'action': action,
            'performed_by': str(performed_by),
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # In real implementation, save to audit_logs table
        print(f"AUDIT LOG: {json.dumps(log_entry)}")
    
    # Helper methods to convert between domain objects and schemas
    
    def _capability_to_schema(self, capability: AgentCapability):
        """Convert capability domain object to schema"""
        from app.schemas.agent import AgentCapabilitySchema
        return AgentCapabilitySchema(
            name=capability.name,
            description=capability.description,
            input_schema=capability.input_schema,
            output_schema=capability.output_schema
        )
    
    def _policy_to_schema(self, policy: AgentPolicy):
        """Convert policy domain object to schema"""
        from app.schemas.agent import AgentPolicySchema
        return AgentPolicySchema(
            max_requests_per_minute=policy.max_requests_per_minute,
            max_concurrent_executions=policy.max_concurrent_executions,
            timeout_seconds=policy.timeout_seconds,
            allowed_domains=policy.allowed_domains,
            require_confirmation=policy.require_confirmation,
            cost_per_execution=policy.cost_per_execution
        )
    
    def _dependency_to_schema(self, dependency: AgentDependency):
        """Convert dependency domain object to schema"""
        from app.schemas.agent import AgentDependencySchema
        return AgentDependencySchema(
            agent_id=dependency.agent_id,
            version=dependency.version,
            optional=dependency.optional
        )
    
    def _capability_dict_to_schema(self, cap_dict: Dict[str, Any]):
        """Convert capability dict to schema"""
        from app.schemas.agent import AgentCapabilitySchema
        return AgentCapabilitySchema(
            name=cap_dict['name'],
            description=cap_dict['description'],
            input_schema=cap_dict['input_schema'],
            output_schema=cap_dict['output_schema']
        )
    
    def _policy_dict_to_schema(self, policy_dict: Dict[str, Any]):
        """Convert policy dict to schema"""
        from app.schemas.agent import AgentPolicySchema
        return AgentPolicySchema(
            max_requests_per_minute=policy_dict['max_requests_per_minute'],
            max_concurrent_executions=policy_dict['max_concurrent_executions'],
            timeout_seconds=policy_dict['timeout_seconds'],
            allowed_domains=policy_dict['allowed_domains'],
            require_confirmation=policy_dict['require_confirmation'],
            cost_per_execution=policy_dict['cost_per_execution']
        )
    
    def _dependency_dict_to_schema(self, dep_dict: Dict[str, Any]):
        """Convert dependency dict to schema"""
        from app.schemas.agent import AgentDependencySchema
        return AgentDependencySchema(
            agent_id=dep_dict['agent_id'],
            version=dep_dict['version'],
            optional=dep_dict['optional']
        )