"""
Admin Panel API endpoints
Handles administrative operations for agents, integrations, and system monitoring
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer

from app.schemas.admin import (
    AdminAgentSchema,
    AdminIntegrationSchema,
    AdminUserSchema,
    SystemHealthSchema,
    FeatureToggleSchema,
    AdminStatsSchema,
    AgentApprovalSchema,
    IntegrationAnalyticsSchema
)
from app.services.admin_service import AdminService
from app.middleware.admin_auth import require_admin_auth, get_current_admin_user

router = APIRouter(prefix="/admin", tags=["Admin Panel"])
security = HTTPBearer()

def get_admin_service() -> AdminService:
    """Get admin service instance"""
    return AdminService()

# Agent Management Endpoints
@router.get("/agents", response_model=List[AdminAgentSchema])
async def list_all_agents(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """List all agents with admin details"""
    try:
        agents = await admin_service.list_agents(
            status=status,
            category=category,
            limit=limit,
            offset=offset
        )
        
        return [
            AdminAgentSchema(
                id=agent['id'],
                agent_id=agent['agent_id'],
                name=agent['name'],
                description=agent['description'],
                version=agent['version'],
                status=agent['status'],
                category=agent['category'],
                capabilities_count=agent['capabilities_count'],
                usage_count=agent['usage_count'],
                success_rate=agent['success_rate'],
                created_by=agent['created_by'],
                approved_by=agent.get('approved_by'),
                created_at=agent['created_at'],
                updated_at=agent['updated_at'],
                approved_at=agent.get('approved_at')
            ) for agent in agents
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar agentes: {str(e)}"
        )

@router.get("/agents/{agent_id}", response_model=AdminAgentSchema)
async def get_agent_details(
    agent_id: str,
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Get detailed agent information"""
    try:
        agent = await admin_service.get_agent_details(agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agente '{agent_id}' não encontrado"
            )
        
        return AdminAgentSchema(
            id=agent['id'],
            agent_id=agent['agent_id'],
            name=agent['name'],
            description=agent['description'],
            version=agent['version'],
            status=agent['status'],
            category=agent['category'],
            capabilities_count=agent['capabilities_count'],
            usage_count=agent['usage_count'],
            success_rate=agent['success_rate'],
            created_by=agent['created_by'],
            approved_by=agent.get('approved_by'),
            created_at=agent['created_at'],
            updated_at=agent['updated_at'],
            approved_at=agent.get('approved_at')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter detalhes do agente: {str(e)}"
        )

@router.post("/agents/{agent_id}/approve", response_model=AdminAgentSchema)
async def approve_agent(
    agent_id: str,
    approval_data: AgentApprovalSchema,
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Approve agent for production use"""
    try:
        agent = await admin_service.approve_agent(
            agent_id=agent_id,
            approved_by=current_admin['user_id'],
            notes=approval_data.notes
        )
        
        return AdminAgentSchema(
            id=agent['id'],
            agent_id=agent['agent_id'],
            name=agent['name'],
            description=agent['description'],
            version=agent['version'],
            status=agent['status'],
            category=agent['category'],
            capabilities_count=agent['capabilities_count'],
            usage_count=agent['usage_count'],
            success_rate=agent['success_rate'],
            created_by=agent['created_by'],
            approved_by=agent.get('approved_by'),
            created_at=agent['created_at'],
            updated_at=agent['updated_at'],
            approved_at=agent.get('approved_at')
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao aprovar agente: {str(e)}"
        )

@router.post("/agents/{agent_id}/deprecate")
async def deprecate_agent(
    agent_id: str,
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Deprecate agent"""
    try:
        success = await admin_service.deprecate_agent(
            agent_id=agent_id,
            deprecated_by=current_admin['user_id']
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agente '{agent_id}' não encontrado"
            )
        
        return {"message": f"Agente '{agent_id}' marcado como depreciado"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao depreciar agente: {str(e)}"
        )

# Integration Management Endpoints
@router.get("/integrations", response_model=List[AdminIntegrationSchema])
async def list_all_integrations(
    status: Optional[str] = Query(None, description="Filter by status"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """List all integrations with admin details"""
    try:
        integrations = await admin_service.list_integrations(
            status=status,
            provider=provider,
            limit=limit,
            offset=offset
        )
        
        return [
            AdminIntegrationSchema(
                id=integration['id'],
                user_id=integration['user_id'],
                name=integration['name'],
                provider=integration['provider'],
                status=integration['status'],
                webhook_url=integration.get('webhook_url'),
                usage_count=integration['usage_count'],
                success_rate=integration['success_rate'],
                last_used_at=integration.get('last_used_at'),
                created_at=integration['created_at'],
                updated_at=integration['updated_at']
            ) for integration in integrations
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar integrações: {str(e)}"
        )

@router.get("/integrations/{integration_id}/analytics", response_model=IntegrationAnalyticsSchema)
async def get_integration_analytics(
    integration_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Get integration analytics"""
    try:
        analytics = await admin_service.get_integration_analytics(
            integration_id=integration_id,
            days=days
        )
        
        return IntegrationAnalyticsSchema(
            integration_id=integration_id,
            period_days=days,
            total_requests=analytics['total_requests'],
            successful_requests=analytics['successful_requests'],
            failed_requests=analytics['failed_requests'],
            success_rate=analytics['success_rate'],
            avg_response_time_ms=analytics['avg_response_time_ms'],
            error_breakdown=analytics['error_breakdown'],
            usage_by_day=analytics['usage_by_day'],
            top_endpoints=analytics['top_endpoints']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter analytics: {str(e)}"
        )

# User Management Endpoints
@router.get("/users", response_model=List[AdminUserSchema])
async def list_users(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """List all users"""
    try:
        users = await admin_service.list_users(
            status=status,
            limit=limit,
            offset=offset
        )
        
        return [
            AdminUserSchema(
                id=user['id'],
                email=user['email'],
                full_name=user.get('full_name'),
                status=user['status'],
                role=user.get('role', 'user'),
                integrations_count=user['integrations_count'],
                executions_count=user['executions_count'],
                last_login_at=user.get('last_login_at'),
                created_at=user['created_at'],
                updated_at=user['updated_at']
            ) for user in users
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar usuários: {str(e)}"
        )

# Feature Toggle Endpoints
@router.get("/feature-toggles", response_model=List[FeatureToggleSchema])
async def list_feature_toggles(
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """List all feature toggles"""
    try:
        toggles = await admin_service.list_feature_toggles()
        
        return [
            FeatureToggleSchema(
                id=toggle['id'],
                feature_name=toggle['feature_name'],
                enabled=toggle['enabled'],
                description=toggle['description'],
                target_users=toggle.get('target_users', []),
                rollout_percentage=toggle.get('rollout_percentage', 100),
                created_by=toggle['created_by'],
                created_at=toggle['created_at'],
                updated_at=toggle['updated_at']
            ) for toggle in toggles
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar feature toggles: {str(e)}"
        )

@router.put("/feature-toggles/{toggle_id}", response_model=FeatureToggleSchema)
async def update_feature_toggle(
    toggle_id: UUID,
    toggle_data: FeatureToggleSchema,
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Update feature toggle"""
    try:
        toggle = await admin_service.update_feature_toggle(
            toggle_id=toggle_id,
            enabled=toggle_data.enabled,
            target_users=toggle_data.target_users,
            rollout_percentage=toggle_data.rollout_percentage,
            updated_by=current_admin['user_id']
        )
        
        return FeatureToggleSchema(
            id=toggle['id'],
            feature_name=toggle['feature_name'],
            enabled=toggle['enabled'],
            description=toggle['description'],
            target_users=toggle.get('target_users', []),
            rollout_percentage=toggle.get('rollout_percentage', 100),
            created_by=toggle['created_by'],
            created_at=toggle['created_at'],
            updated_at=toggle['updated_at']
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar feature toggle: {str(e)}"
        )

# System Monitoring Endpoints
@router.get("/health", response_model=SystemHealthSchema)
async def get_system_health(
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Get comprehensive system health status"""
    try:
        health = await admin_service.get_system_health()
        
        return SystemHealthSchema(
            overall_status=health['overall_status'],
            database_status=health['database_status'],
            redis_status=health.get('redis_status', 'unknown'),
            external_apis_status=health['external_apis_status'],
            agents_status=health['agents_status'],
            active_connections=health['active_connections'],
            memory_usage_mb=health['memory_usage_mb'],
            cpu_usage_percent=health['cpu_usage_percent'],
            disk_usage_percent=health['disk_usage_percent'],
            uptime_seconds=health['uptime_seconds'],
            last_check_at=health['last_check_at']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter status do sistema: {str(e)}"
        )

@router.get("/stats", response_model=AdminStatsSchema)
async def get_admin_stats(
    period_days: int = Query(30, ge=1, le=365, description="Period in days"),
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Get administrative statistics"""
    try:
        stats = await admin_service.get_admin_stats(period_days)
        
        return AdminStatsSchema(
            total_users=stats['total_users'],
            active_users=stats['active_users'],
            total_agents=stats['total_agents'],
            approved_agents=stats['approved_agents'],
            total_integrations=stats['total_integrations'],
            active_integrations=stats['active_integrations'],
            total_executions=stats['total_executions'],
            successful_executions=stats['successful_executions'],
            total_webhooks=stats['total_webhooks'],
            successful_webhooks=stats['successful_webhooks'],
            avg_response_time_ms=stats['avg_response_time_ms'],
            error_rate_percent=stats['error_rate_percent'],
            top_agents=stats['top_agents'],
            top_integrations=stats['top_integrations'],
            period_days=period_days
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas: {str(e)}"
        )

# Maintenance Endpoints
@router.post("/maintenance/cleanup")
async def run_system_cleanup(
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Run system cleanup tasks"""
    try:
        results = await admin_service.run_system_cleanup()
        
        return {
            "message": "Limpeza do sistema executada com sucesso",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na limpeza do sistema: {str(e)}"
        )

@router.post("/maintenance/cache/clear")
async def clear_system_cache(
    cache_type: Optional[str] = Query(None, description="Type of cache to clear"),
    admin_service: AdminService = Depends(get_admin_service),
    current_admin = Depends(require_admin_auth)
):
    """Clear system caches"""
    try:
        results = await admin_service.clear_cache(cache_type)
        
        return {
            "message": "Cache limpo com sucesso",
            "cleared_caches": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao limpar cache: {str(e)}"
        )