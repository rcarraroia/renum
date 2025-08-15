"""
Endpoints para agentes (proxy para Suna Backend).
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from uuid import UUID

from app.core.security import get_current_user
from app.infra.suna.client import get_suna_client, SunaClient

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_agents(
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Lista agentes disponíveis no Suna Backend.
    
    Args:
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Lista de agentes disponíveis
        
    Raises:
        HTTPException: Se houver erro na comunicação com Suna
    """
    try:
        agents = await suna_client.list_agents()
        return agents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch agents from Suna Backend: {str(e)}"
        )


@router.get("/{agent_id}", response_model=Dict[str, Any])
async def get_agent(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Obtém detalhes de um agente específico.
    
    Args:
        agent_id: ID do agente
        current_user: Usuário atual autenticado
        suna_client: Cliente para comunicação com Suna Backend
        
    Returns:
        Detalhes do agente
        
    Raises:
        HTTPException: Se o agente não for encontrado ou houver erro na comunicação
    """
    try:
        agent = await suna_client.get_agent(str(agent_id))
        return agent
    except Exception as e:
        # Se for erro 404, propaga como tal
        if "404" in str(e) or "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch agent from Suna Backend: {str(e)}"
        )