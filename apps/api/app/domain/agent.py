"""
Agent domain models for multi-agent system
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentCapability:
    """Domain model for agent capability"""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None
    ):
        self.name = name.lower().strip()
        self.description = description.strip()
        self.input_schema = input_schema
        self.output_schema = output_schema or {}
        
        self._validate()
    
    def _validate(self):
        """Validate capability data"""
        if not self.name:
            raise ValueError("Capability name cannot be empty")
        
        if not self.name.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Capability name must be alphanumeric with underscores or hyphens")
        
        if not self.description:
            raise ValueError("Capability description cannot be empty")
        
        if not isinstance(self.input_schema, dict):
            raise ValueError("Input schema must be a dictionary")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'name': self.name,
            'description': self.description,
            'input_schema': self.input_schema,
            'output_schema': self.output_schema
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCapability':
        """Create from dictionary representation"""
        return cls(
            name=data['name'],
            description=data['description'],
            input_schema=data['input_schema'],
            output_schema=data.get('output_schema')
        )


class AgentPolicy:
    """Domain model for agent execution policy"""
    
    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_concurrent_executions: int = 5,
        timeout_seconds: int = 300,
        allowed_domains: Optional[List[str]] = None,
        require_confirmation: bool = False,
        cost_per_execution: Optional[Decimal] = None
    ):
        self.max_requests_per_minute = max_requests_per_minute
        self.max_concurrent_executions = max_concurrent_executions
        self.timeout_seconds = timeout_seconds
        self.allowed_domains = allowed_domains or ["*"]
        self.require_confirmation = require_confirmation
        self.cost_per_execution = cost_per_execution
        
        self._validate()
    
    def _validate(self):
        """Validate policy data"""
        if self.max_requests_per_minute <= 0:
            raise ValueError("Max requests per minute must be positive")
        
        if self.max_concurrent_executions <= 0:
            raise ValueError("Max concurrent executions must be positive")
        
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout seconds must be positive")
        
        if self.cost_per_execution is not None and self.cost_per_execution < 0:
            raise ValueError("Cost per execution cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'max_requests_per_minute': self.max_requests_per_minute,
            'max_concurrent_executions': self.max_concurrent_executions,
            'timeout_seconds': self.timeout_seconds,
            'allowed_domains': self.allowed_domains,
            'require_confirmation': self.require_confirmation,
            'cost_per_execution': str(self.cost_per_execution) if self.cost_per_execution else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentPolicy':
        """Create from dictionary representation"""
        cost = None
        if data.get('cost_per_execution'):
            cost = Decimal(str(data['cost_per_execution']))
        
        return cls(
            max_requests_per_minute=data.get('max_requests_per_minute', 60),
            max_concurrent_executions=data.get('max_concurrent_executions', 5),
            timeout_seconds=data.get('timeout_seconds', 300),
            allowed_domains=data.get('allowed_domains', ["*"]),
            require_confirmation=data.get('require_confirmation', False),
            cost_per_execution=cost
        )


class Agent:
    """Domain model for agent"""
    
    def __init__(
        self,
        agent_id: str,
        version: str,
        name: str,
        description: str,
        capabilities: List[AgentCapability],
        required_credentials: Optional[List[str]] = None,
        policy: Optional[AgentPolicy] = None,
        status: str = 'draft',
        id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        manifest_checksum: Optional[str] = None,
        manifest_signature: Optional[str] = None,
        signature_key_id: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.agent_id = agent_id.lower().strip()
        self.version = version.strip()
        self.name = name.strip()
        self.description = description.strip()
        self.capabilities = capabilities
        self.required_credentials = required_credentials or []
        self.policy = policy or AgentPolicy()
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.manifest_checksum = manifest_checksum
        self.manifest_signature = manifest_signature
        self.signature_key_id = signature_key_id
        
        self._validate()
    
    def _validate(self):
        """Validate agent data"""
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")
        
        if not self.agent_id.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Agent ID must be alphanumeric with hyphens or underscores")
        
        if not self.version:
            raise ValueError("Version cannot be empty")
        
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', self.version):
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        
        if not self.name:
            raise ValueError("Agent name cannot be empty")
        
        if not self.description:
            raise ValueError("Agent description cannot be empty")
        
        if not self.capabilities:
            raise ValueError("Agent must have at least one capability")
        
        allowed_statuses = ['draft', 'staged', 'approved', 'deprecated']
        if self.status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
    
    def add_capability(self, capability: AgentCapability):
        """Add a new capability to the agent"""
        # Check for duplicate capability names
        existing_names = [cap.name for cap in self.capabilities]
        if capability.name in existing_names:
            raise ValueError(f"Capability '{capability.name}' already exists")
        
        self.capabilities.append(capability)
        self.updated_at = datetime.utcnow()
    
    def remove_capability(self, capability_name: str):
        """Remove a capability from the agent"""
        self.capabilities = [cap for cap in self.capabilities if cap.name != capability_name]
        self.updated_at = datetime.utcnow()
    
    def update_policy(self, policy: AgentPolicy):
        """Update agent policy"""
        self.policy = policy
        self.updated_at = datetime.utcnow()
    
    def approve(self, approved_by: UUID):
        """Approve the agent for production use"""
        if self.status != 'staged':
            raise ValueError("Only staged agents can be approved")
        
        self.status = 'approved'
        self.updated_at = datetime.utcnow()
    
    def deprecate(self, deprecated_by: UUID):
        """Deprecate the agent"""
        if self.status != 'approved':
            raise ValueError("Only approved agents can be deprecated")
        
        self.status = 'deprecated'
        self.updated_at = datetime.utcnow()
    
    def stage(self):
        """Stage the agent for approval"""
        if self.status != 'draft':
            raise ValueError("Only draft agents can be staged")
        
        self.status = 'staged'
        self.updated_at = datetime.utcnow()
    
    def generate_manifest(self) -> Dict[str, Any]:
        """Generate agent manifest for distribution"""
        return {
            'agent_id': self.agent_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'capabilities': [cap.to_dict() for cap in self.capabilities],
            'required_credentials': self.required_credentials,
            'policy': self.policy.to_dict(),
            'checksum': self.manifest_checksum,
            'signature': self.manifest_signature,
            'signature_key_id': self.signature_key_id
        }
    
    def calculate_checksum(self) -> str:
        """Calculate manifest checksum"""
        import hashlib
        import json
        
        manifest_data = {
            'agent_id': self.agent_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'capabilities': [cap.to_dict() for cap in self.capabilities],
            'required_credentials': sorted(self.required_credentials),
            'policy': self.policy.to_dict()
        }
        
        manifest_json = json.dumps(manifest_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(manifest_json.encode()).hexdigest()
    
    def sign_manifest(self, signature: str, key_id: str):
        """Sign the agent manifest"""
        self.manifest_checksum = self.calculate_checksum()
        self.manifest_signature = signature
        self.signature_key_id = key_id
        self.updated_at = datetime.utcnow()
    
    def verify_signature(self, public_key: str) -> bool:
        """Verify manifest signature"""
        if not self.manifest_signature or not self.manifest_checksum:
            return False
        
        # Implementation would use cryptographic library to verify signature
        # This is a placeholder for the actual verification logic
        return True
    
    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability"""
        return any(cap.name == capability_name for cap in self.capabilities)
    
    def get_capability(self, capability_name: str) -> Optional[AgentCapability]:
        """Get a specific capability by name"""
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap
        return None
    
    def is_production_ready(self) -> bool:
        """Check if agent is ready for production use"""
        return (
            self.status == 'approved' and
            self.manifest_signature is not None and
            self.manifest_checksum is not None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'id': str(self.id),
            'agent_id': self.agent_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'capabilities': [cap.to_dict() for cap in self.capabilities],
            'required_credentials': self.required_credentials,
            'policy': self.policy.to_dict(),
            'status': self.status,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'manifest_checksum': self.manifest_checksum,
            'manifest_signature': self.manifest_signature,
            'signature_key_id': self.signature_key_id
        }


class AgentTemplate:
    """Domain model for agent template"""
    
    def __init__(
        self,
        name: str,
        description: str,
        template_data: Dict[str, Any],
        category: Optional[str] = None,
        is_public: bool = False,
        id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.name = name.strip()
        self.description = description.strip()
        self.category = category.strip() if category else None
        self.template_data = template_data
        self.is_public = is_public
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        self._validate()
    
    def _validate(self):
        """Validate template data"""
        if not self.name:
            raise ValueError("Template name cannot be empty")
        
        if not self.description:
            raise ValueError("Template description cannot be empty")
        
        if not self.template_data:
            raise ValueError("Template data cannot be empty")
        
        # Validate that template_data has required fields for agent creation
        required_fields = ['agent_id', 'capabilities']
        for field in required_fields:
            if field not in self.template_data:
                raise ValueError(f"Template data must include '{field}' field")
    
    def create_agent_from_template(
        self,
        agent_id: Optional[str] = None,
        version: str = '1.0.0',
        overrides: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """Create an agent instance from this template"""
        data = self.template_data.copy()
        
        # Apply overrides
        if overrides:
            data.update(overrides)
        
        # Use provided agent_id or generate from template
        if agent_id:
            data['agent_id'] = agent_id
        
        data['version'] = version
        
        # Convert capabilities from dict to AgentCapability objects
        capabilities = []
        for cap_data in data['capabilities']:
            capabilities.append(AgentCapability.from_dict(cap_data))
        
        # Convert policy if present
        policy = None
        if 'policy' in data:
            policy = AgentPolicy.from_dict(data['policy'])
        
        return Agent(
            agent_id=data['agent_id'],
            version=data['version'],
            name=data.get('name', self.name),
            description=data.get('description', self.description),
            capabilities=capabilities,
            required_credentials=data.get('required_credentials', []),
            policy=policy
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'template_data': self.template_data,
            'is_public': self.is_public,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }