"""
Integration API endpoints
Handles CRUD operations for connections and integrations
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.integration import (
    ConnectionSchema,
    CreateConnectionSchema,
    UpdateConnectionSchema,
    ConnectionTestSchema,
    ConnectionTestResult,
    IntegrationAnalytics
)
from app.services.integration_service import IntegrationService
from app.repositories.integration_repository import IntegrationRepository

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def get_integration_service() -> IntegrationService:
    """Get integration service instance"""
    # In real implementation, would inject Supabase client
    integration_repo = IntegrationRepository()
    return IntegrationService(integration_repo)


@router.get("/connections", response_model=List[ConnectionSchema])
async def list_connections(
    connection_type: Optional[str] = Query(None, description="Filter by connection type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """List user's connections"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        connections = await integration_service.get_tenant_connections(
            tenant_id=mock_tenant_id,
            connection_type=connection_type,
            status=status
        )
        
        # Convert to schemas
        connection_schemas = []
        for conn in connections:
            connection_schema = ConnectionSchema(
                id=conn.id,
                tenant_id=conn.tenant_id,
                service_name=conn.service_name,
                connection_type=conn.connection_type,
                credentials=conn.get_masked_credentials(),  # Always masked
                scopes=conn.scopes,
                status=conn.status,
                expires_at=conn.expires_at,
                last_validated=conn.last_validated,
                created_at=conn.created_at,
                updated_at=conn.updated_at
            )
            connection_schemas.append(connection_schema)
        
        return connection_schemas
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connections: {str(e)}"
        )


@router.post("/connections", response_model=ConnectionSchema)
async def create_connection(
    connection_data: CreateConnectionSchema,
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Create new connection"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        connection = await integration_service.create_connection(mock_tenant_id, connection_data)
        
        return ConnectionSchema(
            id=connection.id,
            tenant_id=connection.tenant_id,
            service_name=connection.service_name,
            connection_type=connection.connection_type,
            credentials=connection.get_masked_credentials(),
            scopes=connection.scopes,
            status=connection.status,
            expires_at=connection.expires_at,
            last_validated=connection.last_validated,
            created_at=connection.created_at,
            updated_at=connection.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection: {str(e)}"
        )


@router.get("/connections/{connection_id}", response_model=ConnectionSchema)
async def get_connection(
    connection_id: UUID,
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get specific connection details"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        connection = await integration_service.get_connection_by_id(connection_id, mock_tenant_id)
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )
        
        return ConnectionSchema(
            id=connection.id,
            tenant_id=connection.tenant_id,
            service_name=connection.service_name,
            connection_type=connection.connection_type,
            credentials=connection.get_masked_credentials(),
            scopes=connection.scopes,
            status=connection.status,
            expires_at=connection.expires_at,
            last_validated=connection.last_validated,
            created_at=connection.created_at,
            updated_at=connection.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection: {str(e)}"
        )


@router.put("/connections/{connection_id}", response_model=ConnectionSchema)
async def update_connection(
    connection_id: UUID,
    update_data: UpdateConnectionSchema,
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Update existing connection"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        connection = await integration_service.update_connection(
            connection_id, mock_tenant_id, update_data
        )
        
        return ConnectionSchema(
            id=connection.id,
            tenant_id=connection.tenant_id,
            service_name=connection.service_name,
            connection_type=connection.connection_type,
            credentials=connection.get_masked_credentials(),
            scopes=connection.scopes,
            status=connection.status,
            expires_at=connection.expires_at,
            last_validated=connection.last_validated,
            created_at=connection.created_at,
            updated_at=connection.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update connection: {str(e)}"
        )


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: UUID,
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Delete connection"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        success = await integration_service.delete_connection(connection_id, mock_tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )
        
        return {"message": f"Connection {connection_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete connection: {str(e)}"
        )


@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(
    connection_id: UUID,
    test_data: ConnectionTestSchema,
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Test connection connectivity and functionality"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        result = await integration_service.test_connection(
            connection_id, mock_tenant_id, test_data
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {str(e)}"
        )


@router.get("/connections/{connection_id}/analytics")
async def get_connection_analytics(
    connection_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days for analytics"),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get connection analytics"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        analytics = await integration_service.get_connection_analytics(
            connection_id, mock_tenant_id, days
        )
        
        return analytics
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection analytics: {str(e)}"
        )


@router.post("/connections/{connection_id}/refresh")
async def refresh_connection(
    connection_id: UUID,
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Refresh connection credentials (OAuth)"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        connection = await integration_service.refresh_connection_credentials(
            connection_id, mock_tenant_id
        )
        
        return {
            "message": f"Connection {connection_id} credentials refreshed successfully",
            "connection_id": str(connection.id),
            "status": connection.status,
            "last_validated": connection.last_validated
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh connection: {str(e)}"
        )


@router.get("/connections/{connection_id}/rate-limit")
async def check_connection_rate_limit(
    connection_id: UUID,
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Check connection rate limit status"""
    
    try:
        rate_limit_info = await integration_service.check_rate_limit(connection_id)
        
        return rate_limit_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check rate limit: {str(e)}"
        )


@router.get("/health")
async def integration_health_check():
    """Health check for integration service"""
    
    return {
        "status": "healthy",
        "service": "integration_service",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }


@router.get("/stats")
async def get_integration_stats(
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get overall integration statistics"""
    
    try:
        # For now, use a mock tenant ID
        mock_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
        
        # This would be implemented in the repository
        stats = {
            'total_connections': 15,
            'active_connections': 12,
            'expired_connections': 2,
            'error_connections': 1,
            'by_type': {
                'oauth': 6,
                'api_key': 4,
                'database': 2,
                'webhook': 3
            },
            'most_used_services': [
                {'service': 'Gmail', 'count': 5},
                {'service': 'WhatsApp', 'count': 4},
                {'service': 'Telegram', 'count': 3}
            ]
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integration stats: {str(e)}"
        )