"""
Serviço para processamento de webhooks.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from app.domain.integration import Integration, WebhookCall, IntegrationStatus
from app.repositories.integration_repository import IntegrationRepository, get_integration_repository
from app.infra.suna.client import SunaClient, get_suna_client
from app.core.logger import get_logger

logger = get_logger(__name__)


class WebhookService:
    """Serviço para processamento de webhooks."""
    
    def __init__(
        self,
        integration_repository: IntegrationRepository,
        suna_client: SunaClient
    ):
        self.integration_repository = integration_repository
        self.suna_client = suna_client
        self.rate_limit_cache = {}  # TODO: Usar Redis em produção
    
    async def validate_webhook_token(
        self, 
        token: str, 
        agent_id: UUID
    ) -> Optional[Integration]:
        """Valida token de webhook e retorna a integração."""
        try:
            integration = await self.integration_repository.get_integration_by_token(token)
            
            if not integration:
                logger.warning(f"Token inválido: {token[:10]}...")
                return None
            
            if str(integration.agent_id) != str(agent_id):
                logger.warning(f"Agent ID não corresponde: {agent_id} != {integration.agent_id}")
                return None
            
            if not integration.can_receive_webhook():
                logger.warning(f"Integração não pode receber webhooks: {integration.status}")
                return None
            
            return integration
            
        except Exception as e:
            logger.error(f"Erro na validação do token: {str(e)}")
            return None
    
    async def check_rate_limit(
        self, 
        integration: Integration, 
        ip_address: str
    ) -> Dict[str, Any]:
        """Verifica rate limiting."""
        try:
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(minutes=1)
            
            # Chave para rate limiting
            rate_key = f"{integration.id}:{ip_address}"
            
            # TODO: Implementar com Redis para produção
            # Por enquanto, usar cache em memória simples
            if rate_key not in self.rate_limit_cache:
                self.rate_limit_cache[rate_key] = []
            
            # Limpar entradas antigas
            self.rate_limit_cache[rate_key] = [
                timestamp for timestamp in self.rate_limit_cache[rate_key]
                if timestamp > window_start
            ]
            
            current_count = len(self.rate_limit_cache[rate_key])
            
            if current_count >= integration.rate_limit_per_minute:
                return {
                    "allowed": False,
                    "limit": integration.rate_limit_per_minute,
                    "remaining": 0,
                    "reset_time": int((window_start + timedelta(minutes=1)).timestamp())
                }
            
            # Adicionar timestamp atual
            self.rate_limit_cache[rate_key].append(current_time)
            
            return {
                "allowed": True,
                "limit": integration.rate_limit_per_minute,
                "remaining": integration.rate_limit_per_minute - current_count - 1,
                "reset_time": int((window_start + timedelta(minutes=1)).timestamp())
            }
            
        except Exception as e:
            logger.error(f"Erro no rate limiting: {str(e)}")
            # Em caso de erro, permitir a requisição
            return {
                "allowed": True,
                "limit": integration.rate_limit_per_minute,
                "remaining": integration.rate_limit_per_minute - 1,
                "reset_time": int((datetime.utcnow() + timedelta(minutes=1)).timestamp())
            }
    
    async def process_webhook(
        self,
        integration: Integration,
        payload: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """Processa uma chamada de webhook."""
        start_time = time.time()
        webhook_call = None
        
        try:
            # Validar payload básico
            if not payload:
                raise ValueError("Payload vazio")
            
            # Extrair mensagem do payload
            message = self._extract_message_from_payload(payload, integration.channel.value)
            
            if not message:
                raise ValueError("Mensagem não encontrada no payload")
            
            # Executar agente via Suna
            logger.info(f"Executando agente {integration.agent_id} com mensagem: {message[:100]}...")
            
            execution_result = await self.suna_client.execute_agent(
                agent_id=str(integration.agent_id),
                message=message,
                context=payload
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Registrar chamada bem-sucedida
            webhook_call = WebhookCall(
                integration_id=integration.id,
                agent_id=integration.agent_id,
                payload=payload,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=200,
                response_data=execution_result,
                execution_time_ms=execution_time_ms
            )
            
            await self.integration_repository.create_webhook_call(webhook_call)
            await self.integration_repository.update_last_used(integration.id)
            
            logger.info(f"Webhook processado com sucesso em {execution_time_ms}ms")
            
            return {
                "success": True,
                "data": execution_result,
                "execution_time_ms": execution_time_ms
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            
            logger.error(f"Erro no processamento do webhook: {error_message}")
            
            # Registrar chamada com erro
            webhook_call = WebhookCall(
                integration_id=integration.id,
                agent_id=integration.agent_id,
                payload=payload,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=500,
                error_message=error_message,
                execution_time_ms=execution_time_ms
            )
            
            await self.integration_repository.create_webhook_call(webhook_call)
            
            return {
                "success": False,
                "error": error_message,
                "execution_time_ms": execution_time_ms
            }
    
    def _extract_message_from_payload(self, payload: Dict[str, Any], channel: str) -> Optional[str]:
        """Extrai mensagem do payload baseado no canal."""
        try:
            if channel == "whatsapp":
                return payload.get("message") or payload.get("text")
            elif channel == "telegram":
                return payload.get("message") or payload.get("text")
            elif channel == "zapier":
                return payload.get("message") or payload.get("data", {}).get("message")
            elif channel == "n8n":
                return payload.get("message") or payload.get("data", {}).get("message")
            elif channel == "make":
                return payload.get("message") or payload.get("data", {}).get("message")
            else:  # custom
                # Tentar várias possibilidades
                return (
                    payload.get("message") or
                    payload.get("text") or
                    payload.get("content") or
                    payload.get("data", {}).get("message") or
                    payload.get("data", {}).get("text")
                )
        except Exception as e:
            logger.error(f"Erro ao extrair mensagem do payload: {str(e)}")
            return None
    
    async def test_integration(
        self,
        integration: Integration,
        test_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Testa uma integração com payload simulado."""
        try:
            if not integration.is_active():
                return {
                    "success": False,
                    "error": "Integração não está ativa"
                }
            
            # Processar webhook de teste
            result = await self.process_webhook(
                integration=integration,
                payload=test_payload,
                ip_address="127.0.0.1",  # IP de teste
                user_agent="Renum-Test/1.0"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Erro no teste de integração: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_integration_health(self, integration: Integration) -> Dict[str, Any]:
        """Verifica a saúde de uma integração."""
        try:
            # Buscar chamadas recentes
            recent_calls = await self.integration_repository.get_webhook_calls(
                integration_id=integration.id,
                limit=100,
                start_date=datetime.utcnow() - timedelta(hours=24)
            )
            
            if not recent_calls:
                return {
                    "status": "unknown",
                    "message": "Nenhuma chamada recente",
                    "last_successful_call": None,
                    "recent_error_rate": 0.0,
                    "recommendations": ["Teste a integração para verificar se está funcionando"]
                }
            
            # Calcular métricas de saúde
            successful_calls = [c for c in recent_calls if c.is_successful()]
            failed_calls = [c for c in recent_calls if not c.is_successful()]
            
            error_rate = len(failed_calls) / len(recent_calls) if recent_calls else 0.0
            avg_response_time = sum(c.execution_time_ms for c in recent_calls) / len(recent_calls)
            
            last_successful = max(
                (c.created_at for c in successful_calls),
                default=None
            )
            
            # Determinar status de saúde
            if error_rate > 0.5:
                status = "unhealthy"
            elif error_rate > 0.2:
                status = "degraded"
            else:
                status = "healthy"
            
            recommendations = []
            if error_rate > 0.2:
                recommendations.append("Taxa de erro alta - verificar logs de erro")
            if avg_response_time > 5000:
                recommendations.append("Tempo de resposta alto - otimizar agente")
            if not last_successful or (datetime.utcnow() - last_successful).days > 1:
                recommendations.append("Nenhuma chamada bem-sucedida recente")
            
            return {
                "status": status,
                "last_successful_call": last_successful.isoformat() if last_successful else None,
                "recent_error_rate": error_rate,
                "avg_response_time_24h": avg_response_time,
                "total_calls_24h": len(recent_calls),
                "successful_calls_24h": len(successful_calls),
                "failed_calls_24h": len(failed_calls),
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar saúde da integração: {str(e)}")
            return {
                "status": "error",
                "message": f"Erro ao verificar saúde: {str(e)}",
                "recommendations": ["Verificar logs do sistema"]
            }


def get_webhook_service(
    integration_repository: IntegrationRepository = None,
    suna_client: SunaClient = None
) -> WebhookService:
    """Dependency injection para o serviço de webhook."""
    if integration_repository is None:
        integration_repository = get_integration_repository()
    if suna_client is None:
        suna_client = get_suna_client()
    
    return WebhookService(integration_repository, suna_client)