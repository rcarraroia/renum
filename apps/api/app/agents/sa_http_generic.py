"""
HTTP Generic Agent (sa-http-generic)
Advanced generic agent for custom API integrations with fallback capabilities
"""
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
import json
import re
import time
from datetime import datetime
import asyncio

from app.agents.base_agent import BaseAgent, AgentCapability, AgentExecutionResult
from app.domain.credentials import ProviderType

class HTTPGenericAgent(BaseAgent):
    """Agente genérico para integração com APIs HTTP customizadas"""
    
    def __init__(self):
        super().__init__(
            agent_id="sa-http-generic",
            name="HTTP Generic Agent",
            description="Advanced generic agent for custom API integrations with intelligent fallback capabilities",
            version="2.0.0"
        )
        
        # Rate limiting and retry configuration
        self.rate_limits = {}
        self.retry_config = {
            'max_retries': 3,
            'backoff_factor': 2,
            'retry_status_codes': [429, 500, 502, 503, 504]
        }
        
        # Response transformation templates
        self.transformation_templates = {
            'extract_data': lambda response, path: self._extract_json_path(response, path),
            'map_fields': lambda response, mapping: self._map_response_fields(response, mapping),
            'filter_array': lambda response, condition: self._filter_array_response(response, condition)
        }
    
    def _define_capabilities(self) -> List[AgentCapability]:
        """Define capacidades do HTTP Generic Agent"""
        return [
            AgentCapability(
                name="http_request",
                description="Fazer requisição HTTP genérica",
                input_schema={
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
                            "description": "Método HTTP"
                        },
                        "url": {"type": "string", "description": "URL completa ou path relativo"},
                        "headers": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Headers customizados"
                        },
                        "params": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Query parameters"
                        },
                        "json": {
                            "type": "object",
                            "description": "Dados JSON para enviar no body"
                        },
                        "data": {
                            "type": "object",
                            "description": "Dados form para enviar no body"
                        },
                        "timeout": {"type": "integer", "default": 30, "description": "Timeout em segundos"},
                        "follow_redirects": {"type": "boolean", "default": True, "description": "Seguir redirects"},
                        "verify_ssl": {"type": "boolean", "default": True, "description": "Verificar SSL"}
                    },
                    "required": ["method", "url"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "headers": {"type": "object"},
                        "data": {"description": "Response data (JSON ou texto)"},
                        "response_time_ms": {"type": "integer"},
                        "url": {"type": "string"}
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="rest_get",
                description="Fazer requisição GET REST",
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "Endpoint da API"},
                        "params": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Query parameters"
                        },
                        "headers": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Headers adicionais"
                        }
                    },
                    "required": ["endpoint"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "data": {"description": "Response data"},
                        "response_time_ms": {"type": "integer"}
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="rest_post",
                description="Fazer requisição POST REST",
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "Endpoint da API"},
                        "data": {"type": "object", "description": "Dados para enviar"},
                        "headers": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Headers adicionais"
                        }
                    },
                    "required": ["endpoint", "data"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "data": {"description": "Response data"},
                        "response_time_ms": {"type": "integer"}
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="rest_put",
                description="Fazer requisição PUT REST",
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "Endpoint da API"},
                        "data": {"type": "object", "description": "Dados para atualizar"},
                        "headers": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Headers adicionais"
                        }
                    },
                    "required": ["endpoint", "data"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "data": {"description": "Response data"},
                        "response_time_ms": {"type": "integer"}
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="rest_delete",
                description="Fazer requisição DELETE REST",
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "Endpoint da API"},
                        "headers": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Headers adicionais"
                        }
                    },
                    "required": ["endpoint"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "data": {"description": "Response data"},
                        "response_time_ms": {"type": "integer"}
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="webhook_call",
                description="Chamar webhook com payload específico",
                input_schema={
                    "type": "object",
                    "properties": {
                        "webhook_url": {"type": "string", "description": "URL do webhook"},
                        "payload": {"type": "object", "description": "Payload para enviar"},
                        "headers": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Headers customizados"
                        },
                        "secret": {"type": "string", "description": "Segredo para assinatura"},
                        "signature_header": {"type": "string", "default": "X-Signature", "description": "Header da assinatura"}
                    },
                    "required": ["webhook_url", "payload"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "response": {"description": "Response do webhook"},
                        "response_time_ms": {"type": "integer"}
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="batch_requests",
                description="Executar múltiplas requisições HTTP em lote",
                input_schema={
                    "type": "object",
                    "properties": {
                        "requests": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "ID único da requisição"},
                                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                                    "url": {"type": "string", "description": "URL ou endpoint"},
                                    "headers": {"type": "object"},
                                    "params": {"type": "object"},
                                    "json": {"type": "object"},
                                    "data": {"type": "object"}
                                },
                                "required": ["id", "method", "url"]
                            },
                            "description": "Lista de requisições para executar"
                        },
                        "concurrent": {"type": "boolean", "default": True, "description": "Executar em paralelo"},
                        "max_concurrent": {"type": "integer", "default": 5, "description": "Máximo de requisições simultâneas"},
                        "fail_fast": {"type": "boolean", "default": False, "description": "Parar na primeira falha"}
                    },
                    "required": ["requests"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "success": {"type": "boolean"},
                                    "status_code": {"type": "integer"},
                                    "data": {},
                                    "error": {"type": "string"},
                                    "response_time_ms": {"type": "integer"}
                                }
                            }
                        },
                        "summary": {
                            "type": "object",
                            "properties": {
                                "total": {"type": "integer"},
                                "successful": {"type": "integer"},
                                "failed": {"type": "integer"},
                                "total_time_ms": {"type": "integer"}
                            }
                        }
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="api_discovery",
                description="Descobrir endpoints e estrutura de uma API",
                input_schema={
                    "type": "object",
                    "properties": {
                        "base_url": {"type": "string", "description": "URL base da API"},
                        "discovery_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": ["/", "/api", "/v1", "/docs", "/swagger", "/openapi.json"],
                            "description": "Caminhos para tentar descobrir"
                        },
                        "max_depth": {"type": "integer", "default": 2, "description": "Profundidade máxima de descoberta"}
                    },
                    "required": ["base_url"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "api_info": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "version": {"type": "string"},
                                "description": {"type": "string"},
                                "base_url": {"type": "string"}
                            }
                        },
                        "endpoints": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string"},
                                    "method": {"type": "string"},
                                    "description": {"type": "string"},
                                    "parameters": {"type": "array"},
                                    "responses": {"type": "object"}
                                }
                            }
                        },
                        "authentication": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "required": {"type": "boolean"}
                            }
                        }
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="response_transform",
                description="Transformar resposta da API usando templates",
                input_schema={
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                        "url": {"type": "string", "description": "URL da API"},
                        "request_data": {"type": "object", "description": "Dados da requisição"},
                        "transform": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["extract_data", "map_fields", "filter_array", "custom"],
                                    "description": "Tipo de transformação"
                                },
                                "config": {"type": "object", "description": "Configuração da transformação"}
                            },
                            "required": ["type", "config"]
                        }
                    },
                    "required": ["method", "url", "transform"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "original_response": {"description": "Resposta original da API"},
                        "transformed_data": {"description": "Dados transformados"},
                        "transformation_applied": {"type": "string"},
                        "status_code": {"type": "integer"},
                        "response_time_ms": {"type": "integer"}
                    }
                },
                required_credentials=["custom_api"]
            ),
            
            AgentCapability(
                name="retry_with_backoff",
                description="Executar requisição com retry automático e backoff",
                input_schema={
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                        "url": {"type": "string", "description": "URL da API"},
                        "request_data": {"type": "object", "description": "Dados da requisição"},
                        "retry_config": {
                            "type": "object",
                            "properties": {
                                "max_retries": {"type": "integer", "default": 3},
                                "backoff_factor": {"type": "number", "default": 2},
                                "retry_status_codes": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "default": [429, 500, 502, 503, 504]
                                },
                                "max_backoff_seconds": {"type": "integer", "default": 60}
                            }
                        }
                    },
                    "required": ["method", "url"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "final_response": {"description": "Resposta final (sucesso ou último erro)"},
                        "attempts": {"type": "integer"},
                        "total_time_ms": {"type": "integer"},
                        "retry_history": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "attempt": {"type": "integer"},
                                    "status_code": {"type": "integer"},
                                    "error": {"type": "string"},
                                    "backoff_seconds": {"type": "number"}
                                }
                            }
                        }
                    }
                },
                required_credentials=["custom_api"]
            )
        ]
    
    async def execute_capability(
        self,
        capability_name: str,
        input_data: Dict[str, Any],
        user_id: UUID,
        credential_id: Optional[UUID] = None
    ) -> AgentExecutionResult:
        """Executa capacidade do HTTP Generic Agent"""
        start_time = datetime.utcnow()
        
        try:
            # Validar entrada
            is_valid, error_msg = await self.validate_input(capability_name, input_data)
            if not is_valid:
                return AgentExecutionResult(
                    success=False,
                    error_message=error_msg
                )
            
            # Obter credenciais
            credentials = await self.get_user_credential(
                user_id, ProviderType.CUSTOM_API, credential_id
            )
            
            if not credentials:
                return AgentExecutionResult(
                    success=False,
                    error_message="Credenciais da API customizada não encontradas"
                )
            
            # Executar capacidade específica
            if capability_name == "http_request":
                result = await self._http_request(input_data, credentials)
            elif capability_name == "rest_get":
                result = await self._rest_get(input_data, credentials)
            elif capability_name == "rest_post":
                result = await self._rest_post(input_data, credentials)
            elif capability_name == "rest_put":
                result = await self._rest_put(input_data, credentials)
            elif capability_name == "rest_delete":
                result = await self._rest_delete(input_data, credentials)
            elif capability_name == "webhook_call":
                result = await self._webhook_call(input_data, credentials)
            elif capability_name == "batch_requests":
                result = await self._batch_requests(input_data, credentials)
            elif capability_name == "api_discovery":
                result = await self._api_discovery(input_data, credentials)
            elif capability_name == "response_transform":
                result = await self._response_transform(input_data, credentials)
            elif capability_name == "retry_with_backoff":
                result = await self._retry_with_backoff(input_data, credentials)
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Capacidade '{capability_name}' não implementada"
                )
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Log da execução
            await self.log_execution(capability_name, input_data, result, user_id)
            
            result.execution_time_ms = execution_time
            return result
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            result = AgentExecutionResult(
                success=False,
                error_message=f"Erro na execução: {str(e)}",
                execution_time_ms=execution_time
            )
            
            await self.log_execution(capability_name, input_data, result, user_id)
            return result
    
    async def _http_request(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Fazer requisição HTTP genérica"""
        try:
            method = input_data['method'].upper()
            url = input_data['url']
            
            # Se URL é relativa, usar base_url das credenciais
            if not url.startswith('http'):
                base_url = credentials.get('base_url', '')
                if not base_url:
                    return AgentExecutionResult(
                        success=False,
                        error_message="URL relativa fornecida mas base_url não configurada nas credenciais"
                    )
                url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
            
            # Preparar headers
            headers = input_data.get('headers', {}).copy()
            
            # Adicionar autenticação das credenciais
            if credentials.get('api_key'):
                headers['Authorization'] = f"Bearer {credentials['api_key']}"
            elif credentials.get('username') and credentials.get('password'):
                import base64
                auth_string = f"{credentials['username']}:{credentials['password']}"
                auth_bytes = base64.b64encode(auth_string.encode()).decode()
                headers['Authorization'] = f"Basic {auth_bytes}"
            
            # Adicionar headers das credenciais
            if credentials.get('headers'):
                headers.update(credentials['headers'])
            
            # Preparar parâmetros da requisição
            request_params = {
                'timeout': input_data.get('timeout', 30),
                'follow_redirects': input_data.get('follow_redirects', True)
            }
            
            if input_data.get('params'):
                request_params['params'] = input_data['params']
            
            if input_data.get('json'):
                request_params['json'] = input_data['json']
                headers['Content-Type'] = 'application/json'
            elif input_data.get('data'):
                request_params['data'] = input_data['data']
            
            if headers:
                request_params['headers'] = headers
            
            # Fazer requisição
            start_time = datetime.utcnow()
            
            if method == 'GET':
                response = await self.http_client.get(url, **request_params)
            elif method == 'POST':
                response = await self.http_client.post(url, **request_params)
            elif method == 'PUT':
                response = await self.http_client.put(url, **request_params)
            elif method == 'PATCH':
                response = await self.http_client.patch(url, **request_params)
            elif method == 'DELETE':
                response = await self.http_client.delete(url, **request_params)
            elif method == 'HEAD':
                response = await self.http_client.head(url, **request_params)
            elif method == 'OPTIONS':
                response = await self.http_client.options(url, **request_params)
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Método HTTP '{method}' não suportado"
                )
            
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Processar resposta
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return AgentExecutionResult(
                success=True,
                data={
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'data': response_data,
                    'response_time_ms': response_time,
                    'url': str(response.url)
                }
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro na requisição HTTP: {str(e)}"
            )
    
    async def _rest_get(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Fazer requisição GET REST"""
        # Converter para formato http_request
        http_data = {
            'method': 'GET',
            'url': input_data['endpoint'],
            'params': input_data.get('params', {}),
            'headers': input_data.get('headers', {})
        }
        
        return await self._http_request(http_data, credentials)
    
    async def _rest_post(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Fazer requisição POST REST"""
        # Converter para formato http_request
        http_data = {
            'method': 'POST',
            'url': input_data['endpoint'],
            'json': input_data['data'],
            'headers': input_data.get('headers', {})
        }
        
        return await self._http_request(http_data, credentials)
    
    async def _rest_put(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Fazer requisição PUT REST"""
        # Converter para formato http_request
        http_data = {
            'method': 'PUT',
            'url': input_data['endpoint'],
            'json': input_data['data'],
            'headers': input_data.get('headers', {})
        }
        
        return await self._http_request(http_data, credentials)
    
    async def _rest_delete(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Fazer requisição DELETE REST"""
        # Converter para formato http_request
        http_data = {
            'method': 'DELETE',
            'url': input_data['endpoint'],
            'headers': input_data.get('headers', {})
        }
        
        return await self._http_request(http_data, credentials)
    
    async def _webhook_call(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Chamar webhook com payload específico"""
        try:
            webhook_url = input_data['webhook_url']
            payload = input_data['payload']
            headers = input_data.get('headers', {}).copy()
            
            # Adicionar Content-Type se não especificado
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
            
            # Adicionar assinatura se segredo fornecido
            if input_data.get('secret'):
                import hmac
                import hashlib
                
                secret = input_data['secret']
                signature_header = input_data.get('signature_header', 'X-Signature')
                
                # Criar assinatura HMAC
                payload_bytes = json.dumps(payload, sort_keys=True).encode()
                signature = hmac.new(
                    secret.encode(),
                    payload_bytes,
                    hashlib.sha256
                ).hexdigest()
                
                headers[signature_header] = f"sha256={signature}"
            
            # Fazer requisição
            start_time = datetime.utcnow()
            
            response = await self.http_client.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Processar resposta
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return AgentExecutionResult(
                success=True,
                data={
                    'status_code': response.status_code,
                    'response': response_data,
                    'response_time_ms': response_time
                }
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao chamar webhook: {str(e)}"
            )
    
    async def _batch_requests(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Executar múltiplas requisições HTTP em lote"""
        try:
            requests = input_data['requests']
            concurrent = input_data.get('concurrent', True)
            max_concurrent = input_data.get('max_concurrent', 5)
            fail_fast = input_data.get('fail_fast', False)
            
            start_time = datetime.utcnow()
            results = []
            
            if concurrent:
                # Executar em paralelo com limite de concorrência
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def execute_single_request(req):
                    async with semaphore:
                        return await self._execute_single_batch_request(req, credentials)
                
                tasks = [execute_single_request(req) for req in requests]
                
                if fail_fast:
                    # Parar na primeira falha
                    for task in asyncio.as_completed(tasks):
                        result = await task
                        results.append(result)
                        if not result['success']:
                            # Cancelar tarefas restantes
                            for remaining_task in tasks:
                                if not remaining_task.done():
                                    remaining_task.cancel()
                            break
                else:
                    # Executar todas, independente de falhas
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Processar exceções
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            results[i] = {
                                'id': requests[i]['id'],
                                'success': False,
                                'error': str(result),
                                'response_time_ms': 0
                            }
            else:
                # Executar sequencialmente
                for req in requests:
                    result = await self._execute_single_batch_request(req, credentials)
                    results.append(result)
                    
                    if fail_fast and not result['success']:
                        break
            
            total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Calcular resumo
            successful = sum(1 for r in results if r.get('success', False))
            failed = len(results) - successful
            
            return AgentExecutionResult(
                success=True,
                data={
                    'results': results,
                    'summary': {
                        'total': len(results),
                        'successful': successful,
                        'failed': failed,
                        'total_time_ms': total_time
                    }
                }
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro na execução em lote: {str(e)}"
            )
    
    async def _execute_single_batch_request(
        self,
        request: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executar uma única requisição do lote"""
        try:
            # Converter para formato http_request
            http_data = {
                'method': request['method'],
                'url': request['url'],
                'headers': request.get('headers', {}),
                'params': request.get('params', {}),
                'json': request.get('json'),
                'data': request.get('data')
            }
            
            result = await self._http_request(http_data, credentials)
            
            return {
                'id': request['id'],
                'success': result.success,
                'status_code': result.data.get('status_code') if result.success else None,
                'data': result.data.get('data') if result.success else None,
                'error': result.error_message if not result.success else None,
                'response_time_ms': result.data.get('response_time_ms') if result.success else 0
            }
            
        except Exception as e:
            return {
                'id': request['id'],
                'success': False,
                'error': str(e),
                'response_time_ms': 0
            }
    
    async def _api_discovery(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Descobrir endpoints e estrutura de uma API"""
        try:
            base_url = input_data['base_url'].rstrip('/')
            discovery_paths = input_data.get('discovery_paths', [
                '/', '/api', '/v1', '/docs', '/swagger', '/openapi.json'
            ])
            max_depth = input_data.get('max_depth', 2)
            
            api_info = {}
            endpoints = []
            authentication = {}
            
            # Tentar descobrir documentação OpenAPI/Swagger
            openapi_data = await self._discover_openapi(base_url, discovery_paths, credentials)
            if openapi_data:
                api_info = {
                    'title': openapi_data.get('info', {}).get('title', 'Unknown API'),
                    'version': openapi_data.get('info', {}).get('version', '1.0.0'),
                    'description': openapi_data.get('info', {}).get('description', ''),
                    'base_url': base_url
                }
                
                # Extrair endpoints
                for path, methods in openapi_data.get('paths', {}).items():
                    for method, details in methods.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                            endpoints.append({
                                'path': path,
                                'method': method.upper(),
                                'description': details.get('summary', details.get('description', '')),
                                'parameters': details.get('parameters', []),
                                'responses': details.get('responses', {})
                            })
                
                # Extrair informações de autenticação
                security_schemes = openapi_data.get('components', {}).get('securitySchemes', {})
                if security_schemes:
                    auth_scheme = list(security_schemes.values())[0]
                    authentication = {
                        'type': auth_scheme.get('type', 'unknown'),
                        'description': auth_scheme.get('description', ''),
                        'required': bool(openapi_data.get('security'))
                    }
            
            # Se não encontrou OpenAPI, tentar descoberta básica
            if not endpoints:
                endpoints = await self._basic_api_discovery(base_url, discovery_paths, credentials, max_depth)
                api_info = {
                    'title': 'Discovered API',
                    'version': 'unknown',
                    'description': f'API discovered at {base_url}',
                    'base_url': base_url
                }
            
            return AgentExecutionResult(
                success=True,
                data={
                    'api_info': api_info,
                    'endpoints': endpoints,
                    'authentication': authentication
                }
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro na descoberta da API: {str(e)}"
            )
    
    async def _discover_openapi(
        self,
        base_url: str,
        discovery_paths: List[str],
        credentials: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Tentar descobrir documentação OpenAPI/Swagger"""
        openapi_paths = [
            '/openapi.json', '/swagger.json', '/api-docs', '/docs/swagger.json',
            '/v1/openapi.json', '/api/v1/openapi.json', '/swagger/v1/swagger.json'
        ]
        
        for path in openapi_paths:
            try:
                http_data = {
                    'method': 'GET',
                    'url': f"{base_url}{path}",
                    'headers': {'Accept': 'application/json'}
                }
                
                result = await self._http_request(http_data, credentials)
                if result.success and result.data.get('status_code') == 200:
                    data = result.data.get('data')
                    if isinstance(data, dict) and ('openapi' in data or 'swagger' in data):
                        return data
                        
            except Exception:
                continue
        
        return None
    
    async def _basic_api_discovery(
        self,
        base_url: str,
        discovery_paths: List[str],
        credentials: Dict[str, Any],
        max_depth: int
    ) -> List[Dict[str, Any]]:
        """Descoberta básica de endpoints"""
        endpoints = []
        
        for path in discovery_paths:
            try:
                http_data = {
                    'method': 'GET',
                    'url': f"{base_url}{path}",
                    'headers': {'Accept': 'application/json'}
                }
                
                result = await self._http_request(http_data, credentials)
                if result.success and result.data.get('status_code') == 200:
                    endpoints.append({
                        'path': path,
                        'method': 'GET',
                        'description': f'Discovered endpoint at {path}',
                        'parameters': [],
                        'responses': {'200': {'description': 'Success'}}
                    })
                    
            except Exception:
                continue
        
        return endpoints
    
    async def _response_transform(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Transformar resposta da API usando templates"""
        try:
            # Primeiro, fazer a requisição
            http_data = {
                'method': input_data['method'],
                'url': input_data['url']
            }
            
            if input_data.get('request_data'):
                if input_data['method'] in ['POST', 'PUT', 'PATCH']:
                    http_data['json'] = input_data['request_data']
                else:
                    http_data['params'] = input_data['request_data']
            
            result = await self._http_request(http_data, credentials)
            
            if not result.success:
                return result
            
            original_response = result.data.get('data')
            transform_config = input_data['transform']
            transform_type = transform_config['type']
            config = transform_config['config']
            
            # Aplicar transformação
            if transform_type == 'extract_data':
                transformed_data = self._extract_json_path(original_response, config.get('path', ''))
            elif transform_type == 'map_fields':
                transformed_data = self._map_response_fields(original_response, config.get('mapping', {}))
            elif transform_type == 'filter_array':
                transformed_data = self._filter_array_response(original_response, config.get('condition', {}))
            elif transform_type == 'custom':
                # Para transformações customizadas, aplicar função personalizada
                transformed_data = self._apply_custom_transform(original_response, config)
            else:
                transformed_data = original_response
            
            return AgentExecutionResult(
                success=True,
                data={
                    'original_response': original_response,
                    'transformed_data': transformed_data,
                    'transformation_applied': transform_type,
                    'status_code': result.data.get('status_code'),
                    'response_time_ms': result.data.get('response_time_ms')
                }
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro na transformação da resposta: {str(e)}"
            )
    
    async def _retry_with_backoff(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Executar requisição com retry automático e backoff"""
        try:
            retry_config = input_data.get('retry_config', {})
            max_retries = retry_config.get('max_retries', 3)
            backoff_factor = retry_config.get('backoff_factor', 2)
            retry_status_codes = retry_config.get('retry_status_codes', [429, 500, 502, 503, 504])
            max_backoff_seconds = retry_config.get('max_backoff_seconds', 60)
            
            # Preparar dados da requisição
            http_data = {
                'method': input_data['method'],
                'url': input_data['url']
            }
            
            if input_data.get('request_data'):
                if input_data['method'] in ['POST', 'PUT', 'PATCH']:
                    http_data['json'] = input_data['request_data']
                else:
                    http_data['params'] = input_data['request_data']
            
            start_time = datetime.utcnow()
            retry_history = []
            
            for attempt in range(max_retries + 1):
                try:
                    result = await self._http_request(http_data, credentials)
                    
                    if result.success:
                        status_code = result.data.get('status_code', 200)
                        
                        # Verificar se precisa retry baseado no status code
                        if status_code not in retry_status_codes:
                            total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                            
                            return AgentExecutionResult(
                                success=True,
                                data={
                                    'success': True,
                                    'final_response': result.data,
                                    'attempts': attempt + 1,
                                    'total_time_ms': total_time,
                                    'retry_history': retry_history
                                }
                            )
                    
                    # Adicionar ao histórico de retry
                    backoff_seconds = min(backoff_factor ** attempt, max_backoff_seconds)
                    retry_history.append({
                        'attempt': attempt + 1,
                        'status_code': result.data.get('status_code') if result.success else None,
                        'error': result.error_message if not result.success else f"Status code {status_code}",
                        'backoff_seconds': backoff_seconds
                    })
                    
                    # Se não é a última tentativa, aguardar backoff
                    if attempt < max_retries:
                        await asyncio.sleep(backoff_seconds)
                    
                except Exception as e:
                    backoff_seconds = min(backoff_factor ** attempt, max_backoff_seconds)
                    retry_history.append({
                        'attempt': attempt + 1,
                        'status_code': None,
                        'error': str(e),
                        'backoff_seconds': backoff_seconds
                    })
                    
                    if attempt < max_retries:
                        await asyncio.sleep(backoff_seconds)
            
            # Todas as tentativas falharam
            total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return AgentExecutionResult(
                success=True,
                data={
                    'success': False,
                    'final_response': retry_history[-1] if retry_history else {'error': 'No attempts made'},
                    'attempts': len(retry_history),
                    'total_time_ms': total_time,
                    'retry_history': retry_history
                }
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro no retry com backoff: {str(e)}"
            )
    
    def _extract_json_path(self, data: Any, path: str) -> Any:
        """Extrair dados usando JSON path"""
        if not path:
            return data
        
        try:
            parts = path.split('.')
            current = data
            
            for part in parts:
                if '[' in part and ']' in part:
                    # Array access
                    key = part.split('[')[0]
                    index = int(part.split('[')[1].split(']')[0])
                    current = current[key][index]
                else:
                    current = current[part]
            
            return current
            
        except (KeyError, IndexError, TypeError):
            return None
    
    def _map_response_fields(self, data: Any, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Mapear campos da resposta"""
        if not isinstance(data, dict):
            return data
        
        mapped = {}
        for new_key, old_path in mapping.items():
            mapped[new_key] = self._extract_json_path(data, old_path)
        
        return mapped
    
    def _filter_array_response(self, data: Any, condition: Dict[str, Any]) -> List[Any]:
        """Filtrar array baseado em condição"""
        if not isinstance(data, list):
            return data
        
        if not condition:
            return data
        
        field = condition.get('field')
        operator = condition.get('operator', '==')
        value = condition.get('value')
        
        if not field:
            return data
        
        filtered = []
        for item in data:
            if isinstance(item, dict) and field in item:
                item_value = item[field]
                
                if operator == '==' and item_value == value:
                    filtered.append(item)
                elif operator == '!=' and item_value != value:
                    filtered.append(item)
                elif operator == '>' and item_value > value:
                    filtered.append(item)
                elif operator == '<' and item_value < value:
                    filtered.append(item)
                elif operator == 'contains' and value in str(item_value):
                    filtered.append(item)
        
        return filtered
    
    def _apply_custom_transform(self, data: Any, config: Dict[str, Any]) -> Any:
        """Aplicar transformação customizada"""
        # Implementação básica de transformações customizadas
        transform_type = config.get('type')
        
        if transform_type == 'flatten':
            return self._flatten_dict(data) if isinstance(data, dict) else data
        elif transform_type == 'keys_to_lowercase':
            return self._keys_to_lowercase(data) if isinstance(data, dict) else data
        elif transform_type == 'remove_nulls':
            return self._remove_nulls(data)
        else:
            return data
    
    def _flatten_dict(self, data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Achatar dicionário aninhado"""
        items = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _keys_to_lowercase(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Converter chaves para minúsculas"""
        return {k.lower(): v for k, v in data.items()}
    
    def _remove_nulls(self, data: Any) -> Any:
        """Remover valores nulos"""
        if isinstance(data, dict):
            return {k: self._remove_nulls(v) for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            return [self._remove_nulls(item) for item in data if item is not None]
        else:
            return data
    
    def _get_supported_providers(self) -> List[str]:
        """Provedores suportados"""
        return ['custom_api']
    
    def _get_category(self) -> str:
        """Categoria do agente"""
        return 'integration'