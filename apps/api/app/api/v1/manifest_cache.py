"""
Endpoints para gerenciamento de cache de manifests
Permite controle e monitoramento do cache de manifests de agentes
"""
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.services.manifest_cache_service import manifest_cache_service, CacheEventType
from app.middleware.auth import get_current_user, require_admin
from app.schemas.base import BaseResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/manifest-cache", tags=["Manifest Cache"])

@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_stats(
    current_user = Depends(get_current_user)
):
    """
    Obter estatísticas do cache de manifests.
    
    Retorna informações detalhadas sobre performance, uso de memória,
    hit rate e outros indicadores de saúde do cache.
    
    Requer autenticação de usuário.
    """
    try:
        logger.info(
            "Getting cache stats",
            user_id=current_user.get('user_id')
        )
        
        stats = await manifest_cache_service.get_cache_stats()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": "2024-12-15T14:30:22Z"
        }
        
    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve cache statistics"
        )

@router.post("/warm")
async def warm_cache(
    agent_ids: Optional[List[str]] = Body(None, description="Lista de agent IDs para pré-carregar"),
    current_user = Depends(require_admin)
):
    """
    Pré-carregar cache com manifests específicos ou mais usados.
    
    Se agent_ids não for fornecido, fará warming dos agentes mais
    frequentemente acessados automaticamente.
    
    Requer privilégios de administrador.
    """
    try:
        logger.info(
            "Warming cache",
            agent_ids=agent_ids,
            user_id=current_user.get('user_id')
        )
        
        await manifest_cache_service.warm_cache(agent_ids)
        
        return {
            "status": "success",
            "message": f"Cache warming initiated for {len(agent_ids) if agent_ids else 'auto-selected'} agents",
            "agent_ids": agent_ids
        }
        
    except Exception as e:
        logger.error("Failed to warm cache", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to warm cache"
        )

@router.delete("/invalidate/{agent_id}")
async def invalidate_agent_cache(
    agent_id: str,
    version: Optional[str] = Query(None, description="Versão específica ou todas se omitido"),
    reason: str = Query("manual_invalidation", description="Motivo da invalidação"),
    current_user = Depends(require_admin)
):
    """
    Invalidar cache de um agente específico.
    
    Remove o manifest do cache forçando nova busca no registry
    na próxima requisição.
    
    - **agent_id**: ID do agente para invalidar
    - **version**: Versão específica ou todas se omitido
    - **reason**: Motivo da invalidação para auditoria
    
    Requer privilégios de administrador.
    """
    try:
        logger.info(
            "Invalidating agent cache",
            agent_id=agent_id,
            version=version,
            reason=reason,
            user_id=current_user.get('user_id')
        )
        
        await manifest_cache_service.invalidate_manifest(agent_id, version, reason)
        
        return {
            "status": "success",
            "message": f"Cache invalidated for agent {agent_id}" + (f" version {version}" if version else " (all versions)"),
            "agent_id": agent_id,
            "version": version,
            "reason": reason
        }
        
    except Exception as e:
        logger.error("Failed to invalidate cache", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to invalidate cache"
        )

@router.delete("/clear")
async def clear_cache(
    reason: str = Query("manual_clear", description="Motivo da limpeza"),
    current_user = Depends(require_admin)
):
    """
    Limpar todo o cache de manifests.
    
    Remove todas as entradas do cache. Use com cuidado pois
    pode impactar performance temporariamente.
    
    Requer privilégios de administrador.
    """
    try:
        logger.info(
            "Clearing entire cache",
            reason=reason,
            user_id=current_user.get('user_id')
        )
        
        await manifest_cache_service.clear_cache(reason)
        
        return {
            "status": "success",
            "message": "Cache cleared successfully",
            "reason": reason
        }
        
    except Exception as e:
        logger.error("Failed to clear cache", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to clear cache"
        )

@router.post("/events/agent-approved")
async def handle_agent_approved_event(
    agent_id: str = Body(..., description="ID do agente aprovado"),
    version: str = Body("latest", description="Versão do agente"),
    current_user = Depends(require_admin)
):
    """
    Processar evento de agente aprovado.
    
    Invalida cache existente e faz warming da nova versão.
    Normalmente chamado automaticamente pelo sistema de aprovação.
    
    Requer privilégios de administrador.
    """
    try:
        logger.info(
            "Processing agent approved event",
            agent_id=agent_id,
            version=version,
            user_id=current_user.get('user_id')
        )
        
        await manifest_cache_service.handle_agent_event(
            CacheEventType.AGENT_APPROVED,
            agent_id,
            version
        )
        
        return {
            "status": "success",
            "message": f"Agent approved event processed for {agent_id}",
            "event_type": "agent_approved",
            "agent_id": agent_id,
            "version": version
        }
        
    except Exception as e:
        logger.error("Failed to process agent approved event", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to process agent event"
        )

@router.post("/events/agent-deprecated")
async def handle_agent_deprecated_event(
    agent_id: str = Body(..., description="ID do agente depreciado"),
    version: str = Body("latest", description="Versão do agente"),
    current_user = Depends(require_admin)
):
    """
    Processar evento de agente depreciado.
    
    Invalida cache do agente depreciado.
    Normalmente chamado automaticamente pelo sistema.
    
    Requer privilégios de administrador.
    """
    try:
        logger.info(
            "Processing agent deprecated event",
            agent_id=agent_id,
            version=version,
            user_id=current_user.get('user_id')
        )
        
        await manifest_cache_service.handle_agent_event(
            CacheEventType.AGENT_DEPRECATED,
            agent_id,
            version
        )
        
        return {
            "status": "success",
            "message": f"Agent deprecated event processed for {agent_id}",
            "event_type": "agent_deprecated",
            "agent_id": agent_id,
            "version": version
        }
        
    except Exception as e:
        logger.error("Failed to process agent deprecated event", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to process agent event"
        )

@router.get("/health")
async def cache_health_check():
    """
    Health check do serviço de cache de manifests.
    
    Verifica se o cache está funcionando corretamente e
    retorna indicadores de saúde.
    
    Endpoint público para monitoramento.
    """
    try:
        stats = await manifest_cache_service.get_cache_stats()
        cache_health = stats.get("cache_health", {})
        
        status_code = 200
        if cache_health.get("health_status") == "degraded":
            status_code = 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": cache_health.get("health_status", "unknown"),
                "service": "manifest-cache",
                "timestamp": "2024-12-15T14:30:22Z",
                "metrics": {
                    "hit_rate": cache_health.get("hit_rate", 0),
                    "total_entries": cache_health.get("total_entries", 0),
                    "memory_usage_mb": cache_health.get("memory_usage_mb", 0)
                }
            }
        )
        
    except Exception as e:
        logger.error("Cache health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "manifest-cache",
                "timestamp": "2024-12-15T14:30:22Z",
                "error": "Service unavailable"
            }
        )

@router.get("/config")
async def get_cache_config(
    current_user = Depends(get_current_user)
):
    """
    Obter configuração atual do cache.
    
    Retorna configurações como TTL, tamanho máximo,
    thresholds de warming, etc.
    
    Requer autenticação de usuário.
    """
    try:
        config = {
            "default_ttl_minutes": manifest_cache_service.default_ttl.total_seconds() / 60,
            "max_cache_size": manifest_cache_service.max_cache_size,
            "warming_threshold": manifest_cache_service.warming_threshold,
            "cleanup_interval_minutes": manifest_cache_service.cleanup_interval.total_seconds() / 60,
            "service_running": manifest_cache_service._running
        }
        
        return {
            "status": "success",
            "data": config
        }
        
    except Exception as e:
        logger.error("Failed to get cache config", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve cache configuration"
        )

@router.post("/webhook/agent-event")
async def webhook_agent_event(
    event_type: str = Body(..., description="Tipo do evento"),
    agent_id: str = Body(..., description="ID do agente"),
    version: str = Body("latest", description="Versão do agente"),
    webhook_secret: str = Body(..., description="Secret do webhook")
):
    """
    Webhook para eventos de agente externos.
    
    Permite que sistemas externos notifiquem mudanças
    em agentes para invalidação automática do cache.
    
    Requer secret válido para autenticação.
    """
    try:
        # Verificar secret do webhook
        expected_secret = settings.MANIFEST_CACHE_WEBHOOK_SECRET
        if not expected_secret or webhook_secret != expected_secret:
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook secret"
            )
        
        # Mapear tipo de evento
        event_type_map = {
            "approved": CacheEventType.AGENT_APPROVED,
            "updated": CacheEventType.AGENT_UPDATED,
            "deprecated": CacheEventType.AGENT_DEPRECATED,
            "revoked": CacheEventType.AGENT_REVOKED
        }
        
        if event_type not in event_type_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type: {event_type}"
            )
        
        logger.info(
            "Processing webhook agent event",
            event_type=event_type,
            agent_id=agent_id,
            version=version
        )
        
        await manifest_cache_service.handle_agent_event(
            event_type_map[event_type],
            agent_id,
            version
        )
        
        return {
            "status": "success",
            "message": f"Webhook event {event_type} processed for {agent_id}",
            "event_type": event_type,
            "agent_id": agent_id,
            "version": version
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process webhook event", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to process webhook event"
        )