"""
Endpoints para gerenciamento de integrações.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status

from app.schemas.integration import (
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationResponse,
    IntegrationListResponse,
    IntegrationAnalytics,
    IntegrationHealth
)
from app.domain.integration import IntegrationChannel, IntegrationStatus
from app.repositories.integration_repository import IntegrationRepository, get_integration_repository
from app.services.webhook_service import WebhookService, get_webhook_service
from app.core.security import get_current_user

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post(
    "",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar integração",
    description="Cria uma nova integração de webhook para um agente"
)
async def create_integration(
    integration_data: IntegrationCreate,
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository)
):
    """Cria uma nova integração."""
    try:
        user_id = UUID(current_user["id"])
        
        # TODO: Verificar se o usuário tem acesso ao agente
        # TODO: Verificar limites de integrações por usuário
        
        integration = await repository.create_integration(user_id, integration_data)
        
        return IntegrationResponse(
            id=integration.id,
            user_id=integration.user_id,
            agent_id=integration.agent_id,
            name=integration.name,
            description=integration.description,
            channel=integration.channel,
            status=integration.status,
            webhook_token=integration.webhook_token,
            webhook_url=integration.webhook_url,
            rate_limit_per_minute=integration.rate_limit_per_minute,
            metadata=integration.metadata,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            last_used_at=integration.last_used_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao criar integração: {str(e)}"
        )


@router.get(
    "",
    response_model=IntegrationListResponse,
    summary="Listar integrações",
    description="Lista integrações do usuário com filtros e paginação"
)
async def list_integrations(
    agent_id: Optional[UUID] = Query(None, description="Filtrar por agente"),
    channel: Optional[IntegrationChannel] = Query(None, description="Filtrar por canal"),
    status: Optional[IntegrationStatus] = Query(None, description="Filtrar por status"),
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository)
):
    """Lista integrações do usuário."""
    try:
        user_id = UUID(current_user["id"])
        offset = (page - 1) * per_page
        
        integrations = await repository.list_integrations(
            user_id=user_id,
            agent_id=agent_id,
            channel=channel,
            status=status,
            limit=per_page,
            offset=offset
        )
        
        total = await repository.count_integrations(
            user_id=user_id,
            agent_id=agent_id,
            channel=channel,
            status=status
        )
        
        pages = (total + per_page - 1) // per_page
        
        integration_responses = []
        for integration in integrations:
            integration_responses.append(IntegrationResponse(
                id=integration.id,
                user_id=integration.user_id,
                agent_id=integration.agent_id,
                name=integration.name,
                description=integration.description,
                channel=integration.channel,
                status=integration.status,
                webhook_token=integration.webhook_token,
                webhook_url=integration.webhook_url,
                rate_limit_per_minute=integration.rate_limit_per_minute,
                metadata=integration.metadata,
                created_at=integration.created_at,
                updated_at=integration.updated_at,
                last_used_at=integration.last_used_at
            ))
        
        return IntegrationListResponse(
            integrations=integration_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar integrações: {str(e)}"
        )


@router.get(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Obter integração",
    description="Obtém detalhes de uma integração específica"
)
async def get_integration(
    integration_id: UUID = Path(..., description="ID da integração"),
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository)
):
    """Obtém uma integração específica."""
    try:
        user_id = UUID(current_user["id"])
        
        integration = await repository.get_integration(integration_id, user_id)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integração não encontrada"
            )
        
        return IntegrationResponse(
            id=integration.id,
            user_id=integration.user_id,
            agent_id=integration.agent_id,
            name=integration.name,
            description=integration.description,
            channel=integration.channel,
            status=integration.status,
            webhook_token=integration.webhook_token,
            webhook_url=integration.webhook_url,
            rate_limit_per_minute=integration.rate_limit_per_minute,
            metadata=integration.metadata,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            last_used_at=integration.last_used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter integração: {str(e)}"
        )


@router.put(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Atualizar integração",
    description="Atualiza uma integração existente"
)
async def update_integration(
    integration_id: UUID = Path(..., description="ID da integração"),
    integration_data: IntegrationUpdate = ...,
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository)
):
    """Atualiza uma integração."""
    try:
        user_id = UUID(current_user["id"])
        
        integration = await repository.update_integration(integration_id, user_id, integration_data)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integração não encontrada"
            )
        
        return IntegrationResponse(
            id=integration.id,
            user_id=integration.user_id,
            agent_id=integration.agent_id,
            name=integration.name,
            description=integration.description,
            channel=integration.channel,
            status=integration.status,
            webhook_token=integration.webhook_token,
            webhook_url=integration.webhook_url,
            rate_limit_per_minute=integration.rate_limit_per_minute,
            metadata=integration.metadata,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            last_used_at=integration.last_used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao atualizar integração: {str(e)}"
        )


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir integração",
    description="Exclui uma integração permanentemente"
)
async def delete_integration(
    integration_id: UUID = Path(..., description="ID da integração"),
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository)
):
    """Exclui uma integração."""
    try:
        user_id = UUID(current_user["id"])
        
        success = await repository.delete_integration(integration_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integração não encontrada"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir integração: {str(e)}"
        )


@router.post(
    "/{integration_id}/regenerate-token",
    response_model=IntegrationResponse,
    summary="Regenerar token",
    description="Regenera o token de webhook de uma integração"
)
async def regenerate_integration_token(
    integration_id: UUID = Path(..., description="ID da integração"),
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository)
):
    """Regenera o token de uma integração."""
    try:
        user_id = UUID(current_user["id"])
        
        integration = await repository.regenerate_token(integration_id, user_id)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integração não encontrada"
            )
        
        return IntegrationResponse(
            id=integration.id,
            user_id=integration.user_id,
            agent_id=integration.agent_id,
            name=integration.name,
            description=integration.description,
            channel=integration.channel,
            status=integration.status,
            webhook_token=integration.webhook_token,
            webhook_url=integration.webhook_url,
            rate_limit_per_minute=integration.rate_limit_per_minute,
            metadata=integration.metadata,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            last_used_at=integration.last_used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao regenerar token: {str(e)}"
        )


@router.post(
    "/{integration_id}/test",
    summary="Testar integração",
    description="Testa uma integração com payload simulado"
)
async def test_integration(
    integration_id: UUID = Path(..., description="ID da integração"),
    test_payload: Dict[str, Any] = ...,
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Testa uma integração."""
    try:
        user_id = UUID(current_user["id"])
        
        integration = await repository.get_integration(integration_id, user_id)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integração não encontrada"
            )
        
        result = await webhook_service.test_integration(integration, test_payload)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao testar integração: {str(e)}"
        )


@router.get(
    "/{integration_id}/analytics",
    response_model=IntegrationAnalytics,
    summary="Analytics da integração",
    description="Obtém analytics detalhados de uma integração"
)
async def get_integration_analytics(
    integration_id: UUID = Path(..., description="ID da integração"),
    period_hours: int = Query(24, ge=1, le=8760, description="Período em horas"),
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository)
):
    """Obtém analytics de uma integração."""
    try:
        user_id = UUID(current_user["id"])
        
        # Verificar se a integração existe e pertence ao usuário
        integration = await repository.get_integration(integration_id, user_id)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integração não encontrada"
            )
        
        analytics = await repository.get_integration_analytics(integration_id, period_hours)
        
        return IntegrationAnalytics(**analytics)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter analytics: {str(e)}"
        )


@router.get(
    "/{integration_id}/health",
    response_model=IntegrationHealth,
    summary="Saúde da integração",
    description="Verifica o status de saúde de uma integração"
)
async def get_integration_health(
    integration_id: UUID = Path(..., description="ID da integração"),
    current_user: dict = Depends(get_current_user),
    repository: IntegrationRepository = Depends(get_integration_repository),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Verifica a saúde de uma integração."""
    try:
        user_id = UUID(current_user["id"])
        
        integration = await repository.get_integration(integration_id, user_id)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integração não encontrada"
            )
        
        health_data = await webhook_service.get_integration_health(integration)
        
        return IntegrationHealth(
            integration_id=integration_id,
            status=health_data["status"],
            last_successful_call=health_data.get("last_successful_call"),
            last_failed_call=None,  # TODO: Implementar
            recent_error_rate=health_data.get("recent_error_rate", 0.0),
            avg_response_time_24h=health_data.get("avg_response_time_24h", 0.0),
            rate_limit_status={},  # TODO: Implementar
            agent_availability=True,  # TODO: Verificar com Suna
            recommendations=health_data.get("recommendations", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao verificar saúde: {str(e)}"
        )