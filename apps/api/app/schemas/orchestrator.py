"""
Orchestrator-related Pydantic schemas for multi-agent system
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ChatMessage(BaseModel):
    """Schema for chat messages with orchestrator"""
    message: str = Field(..., description="User message content")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    @validator('message')
    def validate_message(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        if len(v) > 10000:
            raise ValueError('Message too long (max 10000 characters)')
        return v.strip()


class OrchestratorResponse(BaseModel):
    """Schema for orchestrator responses"""
    message: str = Field(..., description="Orchestrator response message")
    session_id: str = Field(..., description="Chat session ID")
    requires_input: bool = Field(False, description="Whether orchestrator needs more input")
    suggested_plan: Optional['ExecutionPlan'] = Field(None, description="Suggested execution plan")
    missing_credentials: Optional[List[str]] = Field(None, description="Missing credential types")
    conversation_stage: str = Field('initial', description="Current conversation stage")
    confidence_score: Optional[float] = Field(None, description="Confidence in understanding (0-1)")
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Confidence score must be between 0 and 1')
        return v


class ExecutionStep(BaseModel):
    """Schema for individual execution step"""
    step_id: str = Field(..., description="Unique step identifier")
    agent_id: str = Field(..., description="Agent to execute")
    agent_version: str = Field(..., description="Agent version")
    action: str = Field(..., description="Action to perform")
    parameters: Dict[str, Any] = Field(..., description="Action parameters")
    depends_on: Optional[List[str]] = Field(None, description="Step dependencies")
    timeout_seconds: Optional[int] = Field(300, description="Step timeout")
    retry_count: Optional[int] = Field(3, description="Number of retries")
    
    @validator('step_id')
    def validate_step_id(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Step ID must be alphanumeric with hyphens or underscores')
        return v


class ExecutionPlan(BaseModel):
    """Schema for multi-agent execution plan"""
    plan_id: str = Field(..., description="Unique plan identifier")
    description: str = Field(..., description="Human-readable plan description")
    steps: List[ExecutionStep] = Field(..., description="Execution steps")
    execution_strategy: str = Field('sequential', description="Execution strategy")
    estimated_cost: Optional[Decimal] = Field(None, description="Estimated execution cost")
    estimated_duration_seconds: Optional[int] = Field(None, description="Estimated duration")
    required_credentials: List[str] = Field(default_factory=list, description="Required credential types")
    risk_level: str = Field('low', description="Risk level: low, medium, high")
    
    @validator('execution_strategy')
    def validate_strategy(cls, v):
        allowed_strategies = ['sequential', 'parallel', 'pipeline', 'conditional']
        if v not in allowed_strategies:
            raise ValueError(f'Execution strategy must be one of: {", ".join(allowed_strategies)}')
        return v
    
    @validator('risk_level')
    def validate_risk_level(cls, v):
        allowed_levels = ['low', 'medium', 'high']
        if v not in allowed_levels:
            raise ValueError(f'Risk level must be one of: {", ".join(allowed_levels)}')
        return v
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class ExecutionApproval(BaseModel):
    """Schema for execution plan approval"""
    plan_id: str = Field(..., description="Plan ID to approve")
    approved: bool = Field(..., description="Whether plan is approved")
    modifications: Optional[Dict[str, Any]] = Field(None, description="Requested modifications")
    approval_notes: Optional[str] = Field(None, description="Approval notes")


class MultiAgentExecution(BaseModel):
    """Schema for multi-agent execution"""
    id: UUID
    user_id: UUID
    orchestrator_session_id: Optional[str] = None
    plan: ExecutionPlan
    status: str = Field(..., description="Status: pending, running, completed, failed, cancelled")
    agents_used: List[str] = Field(default_factory=list, description="List of agents used")
    total_cost: Optional[Decimal] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
            Decimal: str
        }


class AgentExecutionStep(BaseModel):
    """Schema for individual agent execution step"""
    id: UUID
    execution_id: UUID
    agent_id: str
    agent_version: str
    step_order: int
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    status: str = Field(..., description="Status: pending, running, completed, failed, skipped")
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    cost: Optional[Decimal] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
            Decimal: str
        }


class ExecutionRequest(BaseModel):
    """Schema for execution request"""
    plan: ExecutionPlan = Field(..., description="Execution plan to run")
    dry_run: bool = Field(False, description="Whether to perform dry run")
    notify_on_completion: bool = Field(True, description="Send notification on completion")
    
    @validator('plan')
    def validate_plan(cls, v):
        if not v.steps:
            raise ValueError('Execution plan must have at least one step')
        return v


class ExecutionResult(BaseModel):
    """Schema for execution result"""
    execution_id: UUID
    status: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    skipped_steps: int
    total_cost: Optional[Decimal] = None
    execution_time_ms: Optional[int] = None
    results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100
    
    class Config:
        json_encoders = {
            UUID: str,
            Decimal: str
        }


class OrchestratorSession(BaseModel):
    """Schema for orchestrator session"""
    session_id: str
    user_id: UUID
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_stage: str = Field('initial', description="Current conversation stage")
    collected_requirements: Dict[str, Any] = Field(default_factory=dict)
    suggested_agents: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class RequirementAnalysis(BaseModel):
    """Schema for requirement analysis result"""
    user_intent: str = Field(..., description="Analyzed user intent")
    required_actions: List[str] = Field(..., description="Required actions to fulfill intent")
    suggested_agents: List[str] = Field(..., description="Suggested agents for actions")
    missing_information: List[str] = Field(default_factory=list, description="Missing information needed")
    confidence_score: float = Field(..., description="Confidence in analysis (0-1)")
    complexity_level: str = Field(..., description="Complexity: simple, medium, complex")
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v
    
    @validator('complexity_level')
    def validate_complexity(cls, v):
        allowed_levels = ['simple', 'medium', 'complex']
        if v not in allowed_levels:
            raise ValueError(f'Complexity level must be one of: {", ".join(allowed_levels)}')
        return v


class AgentRecommendation(BaseModel):
    """Schema for agent recommendation"""
    agent_id: str
    agent_version: str
    agent_name: str
    recommended_action: str
    confidence_score: float
    reasoning: str
    required_credentials: List[str] = Field(default_factory=list)
    estimated_cost: Optional[Decimal] = None
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class ExecutionMonitoring(BaseModel):
    """Schema for execution monitoring"""
    execution_id: UUID
    current_step: Optional[int] = None
    total_steps: int
    progress_percentage: float
    current_agent: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    real_time_logs: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class ExecutionCancellation(BaseModel):
    """Schema for execution cancellation request"""
    execution_id: UUID
    reason: Optional[str] = Field(None, description="Reason for cancellation")
    force: bool = Field(False, description="Force cancellation even if in critical step")


class OrchestratorMetrics(BaseModel):
    """Schema for orchestrator metrics"""
    total_sessions: int = 0
    active_sessions: int = 0
    completed_executions: int = 0
    failed_executions: int = 0
    avg_session_duration_minutes: Optional[float] = None
    avg_execution_time_minutes: Optional[float] = None
    most_used_agents: List[Dict[str, Any]] = Field(default_factory=list)
    success_rate: float = 0.0
    
    class Config:
        json_encoders = {
            Decimal: str
        }


# Forward reference resolution
OrchestratorResponse.model_rebuild()