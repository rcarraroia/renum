"""
Endpoints de health check para monitoramento da aplicação.
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any

from app.infra.suna.client import get_suna_client, SunaClient

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Verificação básica de saúde da aplicação.
    
    Returns:
        Status básico da aplicação
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "renum-api"
    }


@router.get("/health/services")
async def services_health_check(
    suna_client: SunaClient = Depends(get_suna_client)
):
    """
    Verificação detalhada de saúde dos serviços.
    
    Returns:
        Status detalhado de todos os serviços integrados
    """
    health_status = {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {}
    }
    
    # Verifica Suna Backend
    try:
        suna_health = await suna_client.health_check()
        health_status["services"]["suna_backend"] = suna_health
    except Exception as e:
        health_status["services"]["suna_backend"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # TODO: Adicionar verificações para outros serviços
    # - Supabase
    # - Redis (se usado)
    # - WebSocket manager
    
    # Determina status geral
    all_services_healthy = all(
        service.get("status") == "healthy" 
        for service in health_status["services"].values()
    )
    
    if not all_services_healthy:
        health_status["status"] = "degraded"
    
    return health_status