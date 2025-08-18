"""
Middleware para Mascaramento Automático de PII
Aplica mascaramento automático de dados sensíveis em logs e métricas
"""
import json
import time
from typing import Callable, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog

from app.services.pii_service import pii_service

logger = structlog.get_logger(__name__)

class PIIMaskingMiddleware:
    """Middleware para mascaramento automático de PII"""
    
    def __init__(self):
        self.sensitive_headers = {
            'authorization', 'x-api-key', 'x-auth-token', 
            'cookie', 'set-cookie', 'x-forwarded-for'
        }
        
        self.sensitive_query_params = {
            'token', 'api_key', 'password', 'secret', 'key'
        }
        
        self.mask_request_body = True
        self.mask_response_body = True
        self.mask_query_params = True
        self.mask_headers = True
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Processar requisição com mascaramento de PII"""
        start_time = time.time()
        
        # Mascarar dados da requisição para logging
        masked_request_data = await self._mask_request_data(request)
        
        # Log da requisição (com dados mascarados)
        logger.info(
            "Request received",
            method=request.method,
            url=str(request.url.path),
            query_params=masked_request_data.get('query_params', {}),
            headers=masked_request_data.get('headers', {}),
            client_ip=masked_request_data.get('client_ip', 'unknown')
        )
        
        # Processar requisição
        try:
            response = await call_next(request)
            
            # Mascarar dados da resposta para logging
            masked_response_data = await self._mask_response_data(response)
            
            # Log da resposta (com dados mascarados)
            process_time = time.time() - start_time
            logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url.path),
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                response_size=masked_response_data.get('content_length', 0)
            )
            
            return response
            
        except Exception as e:
            # Log de erro (mascarando dados sensíveis)
            process_time = time.time() - start_time
            error_message = str(e)
            masked_error, _ = pii_service.mask_text(error_message)
            
            logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url.path),
                error=masked_error,
                process_time_ms=round(process_time * 1000, 2)
            )
            
            raise
    
    async def _mask_request_data(self, request: Request) -> Dict[str, Any]:
        """Mascarar dados sensíveis da requisição"""
        masked_data = {}
        
        try:
            # Mascarar query parameters
            if self.mask_query_params and request.query_params:
                masked_params = {}
                for key, value in request.query_params.items():
                    if key.lower() in self.sensitive_query_params:
                        masked_params[key] = "***MASKED***"
                    else:
                        # Mascarar PII no valor
                        masked_value, _ = pii_service.mask_text(str(value))
                        masked_params[key] = masked_value
                
                masked_data['query_params'] = masked_params
            
            # Mascarar headers
            if self.mask_headers and request.headers:
                masked_headers = {}
                for key, value in request.headers.items():
                    if key.lower() in self.sensitive_headers:
                        if key.lower() == 'authorization':
                            # Mostrar apenas o tipo (Bearer, Basic, etc.)
                            parts = value.split(' ', 1)
                            masked_headers[key] = f"{parts[0]} ***MASKED***" if len(parts) > 1 else "***MASKED***"
                        else:
                            masked_headers[key] = "***MASKED***"
                    else:
                        # Mascarar PII no valor do header
                        masked_value, _ = pii_service.mask_text(str(value))
                        masked_headers[key] = masked_value
                
                masked_data['headers'] = masked_headers
            
            # Mascarar IP do cliente
            client_ip = request.client.host if request.client else "unknown"
            if client_ip != "unknown":
                masked_ip, _ = pii_service.mask_text(client_ip)
                masked_data['client_ip'] = masked_ip
            
            # Mascarar body da requisição (se aplicável)
            if self.mask_request_body and request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    # Tentar ler o body (cuidado para não consumir o stream)
                    body = await request.body()
                    if body:
                        body_str = body.decode('utf-8')
                        
                        # Se for JSON, mascarar estruturadamente
                        try:
                            body_json = json.loads(body_str)
                            masked_body, found_piis = pii_service.mask_dict(body_json)
                            
                            if found_piis:
                                masked_data['request_body_pii_found'] = len(found_piis)
                                masked_data['request_body_pii_types'] = list(set(pii['type'] for pii in found_piis))
                            
                        except json.JSONDecodeError:
                            # Se não for JSON, mascarar como texto
                            masked_body_str, found_piis = pii_service.mask_text(body_str)
                            
                            if found_piis:
                                masked_data['request_body_pii_found'] = len(found_piis)
                
                except Exception as e:
                    logger.debug("Could not mask request body", error=str(e))
            
        except Exception as e:
            logger.debug("Error masking request data", error=str(e))
        
        return masked_data
    
    async def _mask_response_data(self, response: Response) -> Dict[str, Any]:
        """Mascarar dados sensíveis da resposta"""
        masked_data = {}
        
        try:
            # Obter tamanho da resposta
            if hasattr(response, 'headers') and 'content-length' in response.headers:
                masked_data['content_length'] = int(response.headers['content-length'])
            
            # Mascarar headers de resposta
            if self.mask_headers and hasattr(response, 'headers'):
                masked_headers = {}
                for key, value in response.headers.items():
                    if key.lower() in self.sensitive_headers:
                        masked_headers[key] = "***MASKED***"
                    else:
                        # Mascarar PII no valor do header
                        masked_value, _ = pii_service.mask_text(str(value))
                        masked_headers[key] = masked_value
                
                masked_data['headers'] = masked_headers
            
            # Para JSONResponse, mascarar conteúdo se necessário
            if isinstance(response, JSONResponse) and self.mask_response_body:
                try:
                    # Não mascarar respostas de sucesso por padrão para não impactar performance
                    # Apenas logar se houver erro ou dados sensíveis detectados
                    pass
                except Exception as e:
                    logger.debug("Could not mask response body", error=str(e))
        
        except Exception as e:
            logger.debug("Error masking response data", error=str(e))
        
        return masked_data

# Função para aplicar o middleware
async def pii_masking_middleware(request: Request, call_next: Callable) -> Response:
    """Função middleware para mascaramento de PII"""
    middleware = PIIMaskingMiddleware()
    return await middleware(request, call_next)

# Função para mascarar dados em logs estruturados
def mask_log_data(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mascarar dados sensíveis em logs estruturados
    
    Args:
        log_data: Dados do log para mascarar
        
    Returns:
        Dados do log com PII mascarado
    """
    try:
        masked_data, found_piis = pii_service.mask_dict(log_data.copy())
        
        # Adicionar informação sobre PII encontrado (para auditoria)
        if found_piis:
            masked_data['_pii_masked'] = True
            masked_data['_pii_types_found'] = list(set(pii['type'] for pii in found_piis))
            masked_data['_pii_count'] = len(found_piis)
        
        return masked_data
        
    except Exception as e:
        logger.debug("Error masking log data", error=str(e))
        return log_data

# Configurar structlog para usar mascaramento automático
def configure_pii_masking_for_structlog():
    """Configurar structlog para mascaramento automático de PII"""
    import structlog
    
    def pii_masking_processor(logger, method_name, event_dict):
        """Processor do structlog para mascarar PII"""
        return mask_log_data(event_dict)
    
    # Adicionar processor ao structlog
    structlog.configure(
        processors=[
            pii_masking_processor,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )