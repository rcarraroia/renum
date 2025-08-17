"""
Endpoints para gerenciamento de equipes.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Dict, Any, Optional
from uuid import UUID

from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse, TeamListItem
from app.usecases.team_service import TeamService, get_team_service
from app.core.security import get_current_user
from app.infra.suna.client import get_suna_client, SunaClient

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Cria uma nova equipe de agentes.
    
    Args:
        team_data: Dados da equipe a ser criada
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Equipe criada com todos os detalhes
        
    Raises:
        HTTPException: Se houver erro na criação
    """
    try:
        team_service = get_team_service(suna_client)
        user_id = UUID(current_user["id"])
        
        team = await team_service.create_team(user_id, team_data)
        return team
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create team: {str(e)}"
        )


@router.get("", response_model=Dict[str, Any])
async def list_teams(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=50, description="Itens por página"),
    search: Optional[str] = Query(None, description="Termo de busca"),
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Lista equipes do usuário com paginação e busca.
    
    Args:
        page: Número da página (padrão: 1)
        limit: Itens por página (padrão: 10, máximo: 50)
        search: Termo de busca opcional
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Lista paginada de equipes
    """
    try:
        team_service = get_team_service(suna_client)
        user_id = UUID(current_user["id"])
        
        result = await team_service.list_teams(user_id, page, limit, search)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list teams: {str(e)}"
        )


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: UUID,
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Obtém detalhes de uma equipe específica.
    
    Args:
        team_id: ID da equipe
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Detalhes completos da equipe
        
    Raises:
        HTTPException: Se a equipe não for encontrada ou não pertencer ao usuário
    """
    try:
        team_service = get_team_service(suna_client)
        user_id = UUID(current_user["id"])
        
        team = await team_service.get_team(team_id, user_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get team: {str(e)}"
        )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: UUID,
    team_data: TeamUpdate,
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Atualiza uma equipe existente.
    
    Args:
        team_id: ID da equipe
        team_data: Dados para atualização
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Equipe atualizada
        
    Raises:
        HTTPException: Se a equipe não for encontrada ou não pertencer ao usuário
    """
    try:
        team_service = get_team_service(suna_client)
        user_id = UUID(current_user["id"])
        
        team = await team_service.update_team(team_id, user_id, team_data)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update team: {str(e)}"
        )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Remove uma equipe.
    
    Args:
        team_id: ID da equipe
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Raises:
        HTTPException: Se a equipe não for encontrada ou não pertencer ao usuário
    """
    try:
        team_service = get_team_service(suna_client)
        user_id = UUID(current_user["id"])
        
        success = await team_service.delete_team(team_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete team: {str(e)}"
        )