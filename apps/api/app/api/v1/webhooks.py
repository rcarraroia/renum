"""
Endpoints para processamento de webhooks.
"""

import time
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from fastapi.responses import JSONResponse

from app.schemas.integration import (
    WebhookResponse,
    WebhookErrorResponse,
    WhatsAppWebhookPayload,
    TelegramWebhookPayload,
    ZapierWebhookPayload,
    N8nWebhookPayload,
    MakeWebhookPayload,
    CustomWebhookPayload
)
from app.services.webhook_service import WebhookService, get_webhook_service
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["webhooks"])


def get_client_ip(request: Request) -> str:
    """Obtém o IP do cliente considerando proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def create_error_response(
    error_message: str,
    error_code: Optional[str] = None,
    status_code: int = 400,
    execution_time_ms: Optional[int] = None
) -> JSONResponse:
    """Cria uma resposta de erro padronizada."""
    error_response = WebhookErrorResponse(
        error=error_message,
        code=error_code,
        execution_time_ms=execution_time_ms
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )


async def process_webhook_request(
    agent_id: UUID,
    channel: str,
    payload: Dict[str, Any],
    request: Request,
    authorization: Optional[str],
    webhook_service: WebhookService
) -> JSONResponse:
    """Processa uma requisição de webhook."""
    start_time = time.time()
    
    try:
        # 1. Validar token de autorização
        if not authorization:
            return create_error_response(
                "Token de autorização requerido no header Authorization",
                "MISSING_AUTHORIZATION",
                status.HTTP_401_UNAUTHORIZED,
                int((time.time() - start_time) * 1000)
            )
        
        if not authorization.startswith("Bearer "):
            return create_error_response(
                "Token deve usar formato 'Bearer <token>'",
                "INVALID_TOKEN_FORMAT",
                status.HTTP_401_UNAUTHORIZED,
                int((time.time() - start_time) * 1000)
            )
        
        token = authorization[7:]  # Remove "Bearer "
        
        # 2. Validar token e obter integração
        integration = await webhook_service.validate_webhook_token(token, agent_id)
        if not integration:
            return create_error_response(
                "Token inválido ou agente não autorizado",
                "INVALID_TOKEN",
                status.HTTP_403_FORBIDDEN,
                int((time.time() - start_time) * 1000)
            )
        
        # 3. Verificar rate limiting
        ip_address = get_client_ip(request)
        rate_limit_result = await webhook_service.check_rate_limit(integration, ip_address)
        
        if not rate_limit_result["allowed"]:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=WebhookErrorResponse(
                    error="Rate limit excedido",
                    code="RATE_LIMIT_EXCEEDED",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                ).dict(),
                headers={
                    "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_result["remaining"]),
                    "X-RateLimit-Reset": str(rate_limit_result["reset_time"])
                }
            )
        
        # 4. Processar webhook
        user_agent = request.headers.get("User-Agent", "")
        result = await webhook_service.process_webhook(
            integration=integration,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 5. Preparar resposta
        if result["success"]:
            response = WebhookResponse(
                success=True,
                data=result["data"],
                execution_time_ms=result["execution_time_ms"]
            )
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.dict(),
                headers={
                    "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_result["remaining"]),
                    "X-RateLimit-Reset": str(rate_limit_result["reset_time"])
                }
            )
        else:
            return create_error_response(
                result["error"],
                "PROCESSING_ERROR",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                result["execution_time_ms"]
            )
    
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Erro não tratado no webhook: {str(e)}")
        
        return create_error_response(
            "Erro interno do servidor",
            "INTERNAL_SERVER_ERROR",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            execution_time_ms
        )


# Endpoints específicos por canal

@router.post(
    "/webhook/{agent_id}/whatsapp",
    response_model=WebhookResponse,
    summary="Webhook WhatsApp",
    description="Endpoint específico para webhooks do WhatsApp Business"
)
async def whatsapp_webhook(
    agent_id: UUID,
    payload: WhatsAppWebhookPayload,
    request: Request,
    authorization: Optional[str] = Header(None),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Processa webhook do WhatsApp."""
    return await process_webhook_request(
        agent_id=agent_id,
        channel="whatsapp",
        payload=payload.dict(),
        request=request,
        authorization=authorization,
        webhook_service=webhook_service
    )


@router.post(
    "/webhook/{agent_id}/telegram",
    response_model=WebhookResponse,
    summary="Webhook Telegram",
    description="Endpoint específico para webhooks do Telegram Bot"
)
async def telegram_webhook(
    agent_id: UUID,
    payload: TelegramWebhookPayload,
    request: Request,
    authorization: Optional[str] = Header(None),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Processa webhook do Telegram."""
    return await process_webhook_request(
        agent_id=agent_id,
        channel="telegram",
        payload=payload.dict(),
        request=request,
        authorization=authorization,
        webhook_service=webhook_service
    )


@router.post(
    "/webhook/{agent_id}/zapier",
    response_model=WebhookResponse,
    summary="Webhook Zapier",
    description="Endpoint específico para webhooks do Zapier"
)
async def zapier_webhook(
    agent_id: UUID,
    payload: ZapierWebhookPayload,
    request: Request,
    authorization: Optional[str] = Header(None),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Processa webhook do Zapier."""
    return await process_webhook_request(
        agent_id=agent_id,
        channel="zapier",
        payload=payload.dict(),
        request=request,
        authorization=authorization,
        webhook_service=webhook_service
    )


@router.post(
    "/webhook/{agent_id}/n8n",
    response_model=WebhookResponse,
    summary="Webhook n8n",
    description="Endpoint específico para webhooks do n8n"
)
async def n8n_webhook(
    agent_id: UUID,
    payload: N8nWebhookPayload,
    request: Request,
    authorization: Optional[str] = Header(None),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Processa webhook do n8n."""
    return await process_webhook_request(
        agent_id=agent_id,
        channel="n8n",
        payload=payload.dict(),
        request=request,
        authorization=authorization,
        webhook_service=webhook_service
    )


@router.post(
    "/webhook/{agent_id}/make",
    response_model=WebhookResponse,
    summary="Webhook Make",
    description="Endpoint específico para webhooks do Make (Integromat)"
)
async def make_webhook(
    agent_id: UUID,
    payload: MakeWebhookPayload,
    request: Request,
    authorization: Optional[str] = Header(None),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Processa webhook do Make."""
    return await process_webhook_request(
        agent_id=agent_id,
        channel="make",
        payload=payload.dict(),
        request=request,
        authorization=authorization,
        webhook_service=webhook_service
    )


@router.post(
    "/webhook/{agent_id}",
    response_model=WebhookResponse,
    summary="Webhook genérico",
    description="""
    Endpoint genérico para webhooks customizados.
    
    ## Autenticação
    Requer token Bearer no header Authorization:
    ```
    Authorization: Bearer whk_your_webhook_token_here
    ```
    
    ## Rate Limiting
    - Limite configurável por integração (padrão: 60 chamadas/minuto)
    - Headers de resposta informam status do limite
    - Retorna 429 quando limite excedido
    
    ## Payload
    Aceita qualquer estrutura JSON válida. Campos comuns:
    - `message`: Mensagem de texto
    - `data`: Dados estruturados
    - `user_id`: ID do usuário externo
    - `session_id`: ID da sessão
    """
)
async def generic_webhook(
    agent_id: UUID,
    payload: CustomWebhookPayload,
    request: Request,
    authorization: Optional[str] = Header(None, description="Token Bearer para autenticação"),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Processa webhook genérico."""
    return await process_webhook_request(
        agent_id=agent_id,
        channel="custom",
        payload=payload.dict(),
        request=request,
        authorization=authorization,
        webhook_service=webhook_service
    )


# Endpoints utilitários

@router.get(
    "/webhook/{agent_id}/health",
    summary="Health check do webhook",
    description="Verifica se o endpoint de webhook está funcionando"
)
async def webhook_health_check(agent_id: UUID):
    """Health check do webhook."""
    return {
        "status": "healthy",
        "agent_id": str(agent_id),
        "timestamp": time.time(),
        "message": "Webhook endpoint está funcionando"
    }


@router.get(
    "/webhook/platforms",
    summary="Plataformas suportadas",
    description="Lista todas as plataformas de webhook suportadas"
)
async def get_supported_platforms(
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Lista plataformas de webhook suportadas."""
    
    try:
        platforms = await webhook_service.get_supported_platforms()
        return {
            "platforms": platforms,
            "total_platforms": len(platforms)
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get platforms: {str(e)}"}
        )


@router.get(
    "/webhook/platforms/{platform}",
    summary="Capacidades da plataforma",
    description="Obter capacidades de uma plataforma específica"
)
async def get_platform_capabilities(
    platform: str,
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Obter capacidades de uma plataforma específica."""
    
    try:
        capabilities = await webhook_service.get_platform_capabilities(platform)
        return capabilities
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get platform capabilities: {str(e)}"}
        )


@router.options("/webhook/{agent_id}")
async def webhook_options(agent_id: UUID):
    """Endpoint OPTIONS para CORS."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"methods": ["POST", "OPTIONS"]},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Max-Age": "86400"
        }
    )


@router.options("/webhook/{agent_id}/{channel}")
async def webhook_channel_options(agent_id: UUID, channel: str):
    """Endpoint OPTIONS para CORS específico por canal."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"methods": ["POST", "OPTIONS"]},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Max-Age": "86400"
        }
    )