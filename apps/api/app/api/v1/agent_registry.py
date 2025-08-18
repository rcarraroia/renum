"""
Agent Registry API endpoints
Handles agent CRUD operations, versioning, and approval workflow
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.agent import (
    AgentSchema,
    AgentDetailSchema,
    AgentListSchema,
    CreateAgentSchema,
    UpdateAgentSchema,
    AgentApprovalSchema,
    AgentManifest,
    AgentMetrics,
    AgentHealthCheck
)
from app.services.agent_registry_service import AgentRegistryService
from app.repositories.agent_repository import AgentRepository

router = APIRouter(prefix="/agent-registry", tags=["Agent Registry"])


def get_agent_registry_service() -> AgentRegistryService:
    """Get agent registry service instance"""
    # In real implementation, would inject Supabase client
    agent_repo = AgentRepository()
    return AgentRegistryService(agent_repo)


@router.get("/agents", response_model=AgentListSchema)
async def list_agents(
    status: Optional[str] = Query(None, description="Filter by status"),
    capabilities: Optional[str] = Query(None, description="Comma-separated capabilities"),
    search: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """List available agents from registry"""
    
    try:
        # Parse capabilities
        capability_list = None
        if capabilities:
            capability_list = [cap.strip() for cap in capabilities.split(",")]
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        if search:
            agents = await agent_service.search_agents(
                query=search,
                capabilities=capability_list,
                status=status,
                limit=per_page
            )
        else:
            agents = await agent_service.get_available_agents(
                capabilities=capability_list,
                status=status
            )
        
        # Apply pagination manually for now
        paginated_agents = agents[offset:offset + per_page]
        
        # Convert to schemas
        agent_schemas = []
        for agent in paginated_agents:
            agent_schema = AgentSchema(
                id=agent.id,
                agent_id=agent.agent_id,
                version=agent.version,
                name=agent.name,
                description=agent.description,
                capabilities=[
                    {
                        'name': cap.name,
                        'description': cap.description,
                        'input_schema': cap.input_schema,
                        'output_schema': cap.output_schema
                    } for cap in agent.capabilities
                ],
                input_schema=agent.input_schema,
                policy={
                    'max_requests_per_minute': agent.policy.max_requests_per_minute,
                    'max_concurrent_executions': agent.policy.max_concurrent_executions,
                    'timeout_seconds': agent.policy.timeout_seconds,
                    'allowed_domains': agent.policy.allowed_domains,
                    'require_confirmation': agent.policy.require_confirmation,
                    'cost_per_execution': agent.policy.cost_per_execution
                },
                dependencies=[
                    {
                        'agent_id': dep.agent_id,
                        'version': dep.version,
                        'optional': dep.optional
                    } for dep in agent.dependencies
                ],
                status=agent.status,
                created_by=agent.created_by,
                created_at=agent.created_at,
                updated_at=agent.updated_at
            )
            agent_schemas.append(agent_schema)
        
        # Calculate pagination info
        total = len(agents)
        has_next = offset + per_page < total
        has_prev = page > 1
        
        return AgentListSchema(
            agents=agent_schemas,
            total=total,
            page=page,
            per_page=per_page,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.get("/agents/{agent_id}", response_model=AgentDetailSchema)
async def get_agent(
    agent_id: str,
    version: Optional[str] = Query("latest", description="Agent version"),
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Get specific agent details"""
    
    try:
        agent = await agent_service.get_agent_by_id_and_version(agent_id, version)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} version {version} not found"
            )
        
        # Get usage statistics
        usage_stats = await agent_service.get_agent_usage_stats(agent_id, agent.version)
        
        return AgentDetailSchema(
            id=agent.id,
            agent_id=agent.agent_id,
            version=agent.version,
            name=agent.name,
            description=agent.description,
            capabilities=[
                {
                    'name': cap.name,
                    'description': cap.description,
                    'input_schema': cap.input_schema,
                    'output_schema': cap.output_schema
                } for cap in agent.capabilities
            ],
            input_schema=agent.input_schema,
            policy={
                'max_requests_per_minute': agent.policy.max_requests_per_minute,
                'max_concurrent_executions': agent.policy.max_concurrent_executions,
                'timeout_seconds': agent.policy.timeout_seconds,
                'allowed_domains': agent.policy.allowed_domains,
                'require_confirmation': agent.policy.require_confirmation,
                'cost_per_execution': agent.policy.cost_per_execution
            },
            dependencies=[
                {
                    'agent_id': dep.agent_id,
                    'version': dep.version,
                    'optional': dep.optional
                } for dep in agent.dependencies
            ],
            status=agent.status,
            created_by=agent.created_by,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            usage_stats=usage_stats,
            last_execution=usage_stats.get('last_execution')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {str(e)}"
        )


@router.post("/agents", response_model=AgentSchema)
async def create_agent(
    agent_data: CreateAgentSchema,
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Create new agent"""
    
    try:
        # For now, use a mock user ID
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        agent = await agent_service.create_agent(agent_data, mock_user_id)
        
        return AgentSchema(
            id=agent.id,
            agent_id=agent.agent_id,
            version=agent.version,
            name=agent.name,
            description=agent.description,
            capabilities=[
                {
                    'name': cap.name,
                    'description': cap.description,
                    'input_schema': cap.input_schema,
                    'output_schema': cap.output_schema
                } for cap in agent.capabilities
            ],
            input_schema=agent.input_schema,
            policy={
                'max_requests_per_minute': agent.policy.max_requests_per_minute,
                'max_concurrent_executions': agent.policy.max_concurrent_executions,
                'timeout_seconds': agent.policy.timeout_seconds,
                'allowed_domains': agent.policy.allowed_domains,
                'require_confirmation': agent.policy.require_confirmation,
                'cost_per_execution': agent.policy.cost_per_execution
            },
            dependencies=[
                {
                    'agent_id': dep.agent_id,
                    'version': dep.version,
                    'optional': dep.optional
                } for dep in agent.dependencies
            ],
            status=agent.status,
            created_by=agent.created_by,
            created_at=agent.created_at,
            updated_at=agent.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.put("/agents/{agent_id}", response_model=AgentSchema)
async def update_agent(
    agent_id: str,
    version: str,
    update_data: UpdateAgentSchema,
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Update existing agent"""
    
    try:
        # For now, use a mock user ID
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        agent = await agent_service.update_agent(
            agent_id, version, update_data, mock_user_id
        )
        
        return AgentSchema(
            id=agent.id,
            agent_id=agent.agent_id,
            version=agent.version,
            name=agent.name,
            description=agent.description,
            capabilities=[
                {
                    'name': cap.name,
                    'description': cap.description,
                    'input_schema': cap.input_schema,
                    'output_schema': cap.output_schema
                } for cap in agent.capabilities
            ],
            input_schema=agent.input_schema,
            policy={
                'max_requests_per_minute': agent.policy.max_requests_per_minute,
                'max_concurrent_executions': agent.policy.max_concurrent_executions,
                'timeout_seconds': agent.policy.timeout_seconds,
                'allowed_domains': agent.policy.allowed_domains,
                'require_confirmation': agent.policy.require_confirmation,
                'cost_per_execution': agent.policy.cost_per_execution
            },
            dependencies=[
                {
                    'agent_id': dep.agent_id,
                    'version': dep.version,
                    'optional': dep.optional
                } for dep in agent.dependencies
            ],
            status=agent.status,
            created_by=agent.created_by,
            created_at=agent.created_at,
            updated_at=agent.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )


@router.post("/agents/{agent_id}/approve")
async def approve_agent(
    agent_id: str,
    version: str,
    approval_data: Optional[AgentApprovalSchema] = None,
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Approve agent for production use"""
    
    try:
        # For now, use a mock user ID
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        agent = await agent_service.approve_agent(
            agent_id, version, mock_user_id, approval_data
        )
        
        return {
            "message": f"Agent {agent_id} version {version} approved successfully",
            "agent_id": agent.agent_id,
            "version": agent.version,
            "status": agent.status,
            "approved_at": agent.updated_at
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve agent: {str(e)}"
        )


@router.post("/agents/{agent_id}/deprecate")
async def deprecate_agent(
    agent_id: str,
    version: str,
    reason: Optional[str] = None,
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Deprecate an active agent"""
    
    try:
        # For now, use a mock user ID
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        agent = await agent_service.deprecate_agent(
            agent_id, version, mock_user_id, reason
        )
        
        return {
            "message": f"Agent {agent_id} version {version} deprecated successfully",
            "agent_id": agent.agent_id,
            "version": agent.version,
            "status": agent.status,
            "deprecated_at": agent.updated_at,
            "reason": reason
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deprecate agent: {str(e)}"
        )


@router.get("/agents/{agent_id}/manifest", response_model=AgentManifest)
async def get_agent_manifest(
    agent_id: str,
    version: Optional[str] = Query("latest", description="Agent version"),
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Get agent manifest for execution"""
    
    try:
        manifest = await agent_service.get_agent_manifest(agent_id, version)
        
        if not manifest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} version {version} not found or not active"
            )
        
        return manifest
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent manifest: {str(e)}"
        )


@router.get("/agents/{agent_id}/versions", response_model=List[AgentSchema])
async def get_agent_versions(
    agent_id: str,
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Get all versions of a specific agent"""
    
    try:
        agents = await agent_service.get_agent_versions(agent_id)
        
        agent_schemas = []
        for agent in agents:
            agent_schema = AgentSchema(
                id=agent.id,
                agent_id=agent.agent_id,
                version=agent.version,
                name=agent.name,
                description=agent.description,
                capabilities=[
                    {
                        'name': cap.name,
                        'description': cap.description,
                        'input_schema': cap.input_schema,
                        'output_schema': cap.output_schema
                    } for cap in agent.capabilities
                ],
                input_schema=agent.input_schema,
                policy={
                    'max_requests_per_minute': agent.policy.max_requests_per_minute,
                    'max_concurrent_executions': agent.policy.max_concurrent_executions,
                    'timeout_seconds': agent.policy.timeout_seconds,
                    'allowed_domains': agent.policy.allowed_domains,
                    'require_confirmation': agent.policy.require_confirmation,
                    'cost_per_execution': agent.policy.cost_per_execution
                },
                dependencies=[
                    {
                        'agent_id': dep.agent_id,
                        'version': dep.version,
                        'optional': dep.optional
                    } for dep in agent.dependencies
                ],
                status=agent.status,
                created_by=agent.created_by,
                created_at=agent.created_at,
                updated_at=agent.updated_at
            )
            agent_schemas.append(agent_schema)
        
        return agent_schemas
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent versions: {str(e)}"
        )


@router.get("/agents/{agent_id}/metrics", response_model=AgentMetrics)
async def get_agent_metrics(
    agent_id: str,
    version: str,
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Get agent usage metrics"""
    
    try:
        stats = await agent_service.get_agent_usage_stats(agent_id, version)
        
        return AgentMetrics(
            agent_id=agent_id,
            version=version,
            total_executions=stats['total_executions'],
            successful_executions=stats['successful_executions'],
            failed_executions=stats['failed_executions'],
            avg_execution_time_ms=stats['avg_execution_time_ms'],
            total_cost=stats['total_cost'],
            last_execution=stats['last_execution']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent metrics: {str(e)}"
        )


@router.get("/stats")
async def get_registry_stats(
    agent_service: AgentRegistryService = Depends(get_agent_registry_service)
):
    """Get overall agent registry statistics"""
    
    try:
        # This would be implemented in the service
        stats = {
            'total_agents': 25,
            'by_status': {
                'active': 18,
                'inactive': 5,
                'deprecated': 2
            },
            'pending_approvals': 0,
            'most_used_capabilities': [
                {'name': 'send_email', 'count': 15},
                {'name': 'query_database', 'count': 12},
                {'name': 'send_message', 'count': 10}
            ]
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get registry stats: {str(e)}"
        )