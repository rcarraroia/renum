"""
Multi-Agent Executions API endpoints
Handles execution planning, coordination, and monitoring
"""
from typiapi import APIRouter, HTTPException, status, Depends, Query
from typing import Dict, Any, Optional
from uuid import UUID

from app.schemas.execution import (
    ExecutionCreate, ExecutionResponse, ExecutionListItem, ExecutionStartResponse,
    ExecutionCancelResponse, ExecutionStatus
)
from app.usecases.execution_service import ExecutionService, get_execution_service
from app.usecases.team_service import TeamService, get_team_service
from app.core.security import get_current_user
from app.infra.suna.client import get_suna_client, SunaClient

router = APIRouter(prefix="/teams", tags=["Executions"])


@router.post("/{team_id}/execute", response_model=ExecutionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_team_execution(
    team_id: UUID,
    execution_data: ExecutionCreate,
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Inicia execução de uma equipe.
    
    Args:
        team_id: ID da equipe a ser executada
        execution_data: Dados de entrada e configuração da execução
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Informações da execução iniciada
        
    Raises:
        HTTPException: Se houver erro na criação ou equipe não encontrada
    """
    try:
        team_service = get_team_service(suna_client)
        execution_service = get_execution_service(suna_client, team_service)
        user_id = UUID(current_user["id"])
        
        execution = await execution_service.start_execution(team_id, user_id, execution_data)
        return execution
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found or access denied"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start execution: {str(e)}"
        )


# Endpoints de execuções (não específicos de equipe)
executions_router = APIRouter(prefix="/executions", tags=["Executions"])


@executions_router.get("", response_model=Dict[str, Any])
async def list_executions(
    team_id: Optional[UUID] = Query(None, description="Filtrar por equipe"),
    status: Optional[ExecutionStatus] = Query(None, description="Filtrar por status"),
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=50, description="Itens por página"),
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Lista execuções do usuário com filtros e paginação.
    
    Args:
        team_id: ID da equipe para filtrar (opcional)
        status: Status para filtrar (opcional)
        page: Número da página (padrão: 1)
        limit: Itens por página (padrão: 10, máximo: 50)
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Lista paginada de execuções
    """
    try:
        team_service = get_team_service(suna_client)
        execution_service = get_execution_service(suna_client, team_service)
        user_id = UUID(current_user["id"])
        
        result = await execution_service.list_executions(user_id, team_id, status, page, limit)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list executions: {str(e)}"
        )


@executions_router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: UUID,
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Obtém detalhes de uma execução específica.
    
    Args:
        execution_id: ID da execução
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Detalhes completos da execução
        
    Raises:
        HTTPException: Se a execução não for encontrada ou não pertencer ao usuário
    """
    try:
        team_service = get_team_service(suna_client)
        execution_service = get_execution_service(suna_client, team_service)
        user_id = UUID(current_user["id"])
        
        execution = await execution_service.get_execution(execution_id, user_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        return execution
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution: {str(e)}"
        )


@executions_router.post("/{execution_id}/cancel", response_model=ExecutionCancelResponse)
async def cancel_execution(
    execution_id: UUID,
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Cancela uma execução em andamento.
    
    Args:
        execution_id: ID da execução
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Confirmação do cancelamento
        
    Raises:
        HTTPException: Se a execução não for encontrada ou não pertencer ao usuário
    """
    try:
        team_service = get_team_service(suna_client)
        execution_service = get_execution_service(suna_client, team_service)
        user_id = UUID(current_user["id"])
        
        result = await execution_service.cancel_execution(execution_id, user_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found or cannot be cancelled"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel execution: {str(e)}"
        )