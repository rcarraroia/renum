"""
Agent-related Pydantic schemas for multi-agent system
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class AgentCapability(BaseModel):
    """Schema for agent capability definition"""
    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="Capability description")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for input validation")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for output validation")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Capability name must be alphanumeric with underscores or hyphens')
        return v.lower()


class AgentPolicy(BaseModel):
    """Schema for agent execution policy"""
    max_requests_per_minute: Optional[int] = Field(60, description="Rate limit per minute")
    max_concurrent_executions: Optional[int] = Field(5, description="Max concurrent executions")
    timeout_seconds: Optional[int] = Field(300, description="Execution timeout in seconds")
    allowed_domains: Optional[List[str]] = Field(["*"], description="Allowed domains for external calls")
    require_confirmation: Optional[bool] = Field(False, description="Require user confirmation before execution")
    cost_per_execution: Optional[Decimal] = Field(None, description="Cost per execution in credits")
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class AgentManifest(BaseModel):
    """Complete agent manifest for distribution"""
    agent_id: str = Field(..., description="Unique agent identifier")
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="Agent description")
    capabilities: List[AgentCapability] = Field(..., description="List of agent capabilities")
    required_credentials: List[str] = Field(default_factory=list, description="Required credential types")
    policy: AgentPolicy = Field(default_factory=AgentPolicy, description="Agent execution policy")
    checksum: Optional[str] = Field(None, description="Manifest checksum for integrity")
    signature: Optional[str] = Field(None, description="Digital signature")
    signature_key_id: Optional[str] = Field(None, description="Key ID used for signing")
    
    @validator('agent_id')
    def validate_agent_id(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Agent ID must be alphanumeric with hyphens or underscores')
        return v.lower()
    
    @validator('version')
    def validate_version(cls, v):
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('Version must follow semantic versioning (e.g., 1.0.0)')
        return v


class CreateAgentSchema(BaseModel):
    """Schema for creating new agent"""
    agent_id: str = Field(..., description="Unique agent identifier")
    version: str = Field(..., description="Semantic version")
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="Agent description")
    capabilities: List[AgentCapability] = Field(..., description="List of agent capabilities")
    required_credentials: List[str] = Field(default_factory=list, description="Required credential types")
    policy: AgentPolicy = Field(default_factory=AgentPolicy, description="Agent execution policy")
    
    @validator('agent_id')
    def validate_agent_id(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Agent ID must be alphanumeric with hyphens or underscores')
        return v.lower()


class UpdateAgentSchema(BaseModel):
    """Schema for updating existing agent"""
    name: Optional[str] = Field(None, description="Human-readable agent name")
    description: Optional[str] = Field(None, description="Agent description")
    capabilities: Optional[List[AgentCapability]] = Field(None, description="List of agent capabilities")
    required_credentials: Optional[List[str]] = Field(None, description="Required credential types")
    policy: Optional[AgentPolicy] = Field(None, description="Agent execution policy")


class AgentSchema(BaseModel):
    """Complete agent schema for API responses"""
    id: UUID
    agent_id: str
    version: str
    name: str
    description: str
    capabilities: List[AgentCapability]
    required_credentials: List[str]
    policy: AgentPolicy
    status: str = Field(..., description="Agent status: draft, staged, approved, deprecated")
    manifest_checksum: Optional[str] = None
    manifest_signature: Optional[str] = None
    signature_key_id: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
            Decimal: str
        }


class AgentDetailSchema(AgentSchema):
    """Detailed agent schema with additional metadata"""
    manifest: Optional[AgentManifest] = Field(None, description="Complete agent manifest")
    usage_stats: Optional[Dict[str, Any]] = Field(None, description="Usage statistics")
    last_execution: Optional[datetime] = Field(None, description="Last execution timestamp")


class AgentListSchema(BaseModel):
    """Schema for agent list responses"""
    agents: List[AgentSchema]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class AgentApprovalSchema(BaseModel):
    """Schema for agent approval request"""
    agent_id: str
    version: str
    approval_notes: Optional[str] = Field(None, description="Notes for approval")


class AgentTemplateSchema(BaseModel):
    """Schema for agent templates"""
    id: UUID
    name: str
    description: str
    category: Optional[str] = None
    template_data: Dict[str, Any]
    is_public: bool = False
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class CreateAgentTemplateSchema(BaseModel):
    """Schema for creating agent template"""
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: Optional[str] = Field(None, description="Template category")
    template_data: Dict[str, Any] = Field(..., description="Template data structure")
    is_public: bool = Field(False, description="Whether template is public")


class AgentExecutionRequest(BaseModel):
    """Schema for agent execution request"""
    agent_id: str
    agent_version: str
    action: str
    parameters: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    
    @validator('action')
    def validate_action(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Action must be alphanumeric with underscores')
        return v


class AgentExecutionResponse(BaseModel):
    """Schema for agent execution response"""
    execution_id: str
    agent_id: str
    agent_version: str
    action: str
    status: str = Field(..., description="Status: pending, running, completed, failed")
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    cost: Optional[Decimal] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: str
        }


class AgentHealthCheck(BaseModel):
    """Schema for agent health check"""
    agent_id: str
    version: str
    status: str = Field(..., description="Status: healthy, degraded, unhealthy")
    last_check: datetime
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentMetrics(BaseModel):
    """Schema for agent metrics"""
    agent_id: str
    version: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time_ms: Optional[float] = None
    total_cost: Optional[Decimal] = None
    last_execution: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: str
        }