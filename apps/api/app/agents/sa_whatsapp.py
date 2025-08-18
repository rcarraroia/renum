"""
WhatsApp Agent (sa-whatsapp)
Agente especializado para operações com WhatsApp Business API
"""
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

from app.agents.base_agent import BaseAgent, AgentCapability, AgentExecutionResult
from app.domain.credentials import ProviderType

class WhatsAppAgent(BaseAgent):
    """Agente para integração com WhatsApp Business API"""
    
    def __init__(self):
        super().__init__(
            agent_id="sa-whatsapp",
            name="WhatsApp Agent",
            description="Agente especializado para envio de mensagens via WhatsApp Business API",
            version="1.0.0"
        )
    
    def _define_capabilities(self) -> List[AgentCapability]:
        """Define capacidades do WhatsApp Agent"""
        return [
            AgentCapability(
                name="send_text_message",
                description="Enviar mensagem de texto",
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Número do destinatário (formato internacional)"},
                        "message": {"type": "string", "description": "Texto da mensagem"},
                        "preview_url": {"type": "boolean", "default": False, "description": "Mostrar preview de URLs"}
                    },
                    "required": ["to", "message"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "status": {"type": "string"},
                        "recipient": {"type": "string"}
                    }
                },
                required_credentials=["whatsapp_business"]
            ),
            
            AgentCapability(
                name="send_template_message",
                description="Enviar mensagem usando template aprovado",
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Número do destinatário"},
                        "template_name": {"type": "string", "description": "Nome do template"},
                        "language_code": {"type": "string", "default": "pt_BR", "description": "Código do idioma"},
                        "parameters": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Parâmetros do template"
                        }
                    },
                    "required": ["to", "template_name"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "status": {"type": "string"},
                        "recipient": {"type": "string"}
                    }
                },
                required_credentials=["whatsapp_business"]
            ),
            
            AgentCapability(
                name="send_media_message",
                description="Enviar mensagem com mídia (imagem, documento, etc.)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Número do destinatário"},
                        "media_type": {
                            "type": "string",
                            "enum": ["image", "document", "audio", "video"],
                            "description": "Tipo de mídia"
                        },
                        "media_url": {"type": "string", "description": "URL da mídia"},
                        "media_id": {"type": "string", "description": "ID da mídia (alternativa à URL)"},
                        "caption": {"type": "string", "description": "Legenda da mídia"},
                        "filename": {"type": "string", "description": "Nome do arquivo (para documentos)"}
                    },
                    "required": ["to", "media_type"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "status": {"type": "string"},
                        "recipient": {"type": "string"}
                    }
                },
                required_credentials=["whatsapp_business"]
            ),
            
            AgentCapability(
                name="send_interactive_message",
                description="Enviar mensagem interativa (botões ou lista)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Número do destinatário"},
                        "type": {
                            "type": "string",
                            "enum": ["button", "list"],
                            "description": "Tipo de mensagem interativa"
                        },
                        "header": {"type": "string", "description": "Cabeçalho da mensagem"},
                        "body": {"type": "string", "description": "Corpo da mensagem"},
                        "footer": {"type": "string", "description": "Rodapé da mensagem"},
                        "buttons": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "title": {"type": "string"}
                                }
                            },
                            "description": "Botões (para tipo button)"
                        },
                        "list_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "title": {"type": "string"},
                                    "description": {"type": "string"}
                                }
                            },
                            "description": "Itens da lista (para tipo list)"
                        },
                        "button_text": {"type": "string", "description": "Texto do botão da lista"}
                    },
                    "required": ["to", "type", "body"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "status": {"type": "string"},
                        "recipient": {"type": "string"}
                    }
                },
                required_credentials=["whatsapp_business"]
            ),
            
            AgentCapability(
                name="get_message_status",
                description="Verificar status de uma mensagem",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string", "description": "ID da mensagem"}
                    },
                    "required": ["message_id"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "status": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "recipient": {"type": "string"}
                    }
                },
                required_credentials=["whatsapp_business"]
            ),
            
            AgentCapability(
                name="upload_media",
                description="Fazer upload de mídia para usar em mensagens",
                input_schema={
                    "type": "object",
                    "properties": {
                        "media_url": {"type": "string", "description": "URL da mídia para upload"},
                        "media_type": {"type": "string", "description": "Tipo MIME da mídia"}
                    },
                    "required": ["media_url", "media_type"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "media_id": {"type": "string", "description": "ID da mídia uploadada"}
                    }
                },
                required_credentials=["whatsapp_business"]
            )
        ]
    
    async def execute_capability(
        self,
        capability_name: str,
        input_data: Dict[str, Any],
        user_id: UUID,
        credential_id: Optional[UUID] = None
    ) -> AgentExecutionResult:
        """Executa capacidade do WhatsApp Agent"""
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
                user_id, ProviderType.WHATSAPP_BUSINESS, credential_id
            )
            
            if not credentials:
                return AgentExecutionResult(
                    success=False,
                    error_message="Credenciais do WhatsApp Business não encontradas"
                )
            
            # Executar capacidade específica
            if capability_name == "send_text_message":
                result = await self._send_text_message(input_data, credentials)
            elif capability_name == "send_template_message":
                result = await self._send_template_message(input_data, credentials)
            elif capability_name == "send_media_message":
                result = await self._send_media_message(input_data, credentials)
            elif capability_name == "send_interactive_message":
                result = await self._send_interactive_message(input_data, credentials)
            elif capability_name == "get_message_status":
                result = await self._get_message_status(input_data, credentials)
            elif capability_name == "upload_media":
                result = await self._upload_media(input_data, credentials)
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
    
    async def _send_text_message(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar mensagem de texto"""
        try:
            access_token = credentials.get('access_token')
            phone_number_id = credentials.get('phone_number_id')
            
            if not access_token or not phone_number_id:
                return AgentExecutionResult(
                    success=False,
                    error_message="Access token ou phone_number_id não encontrados"
                )
            
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': input_data['to'],
                'type': 'text',
                'text': {
                    'body': input_data['message']
                }
            }
            
            if input_data.get('preview_url', False):
                payload['text']['preview_url'] = True
            
            response = await self.http_client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                message_id = result_data.get('messages', [{}])[0].get('id')
                
                return AgentExecutionResult(
                    success=True,
                    data={
                        'message_id': message_id,
                        'status': 'sent',
                        'recipient': input_data['to']
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da WhatsApp API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar mensagem: {str(e)}"
            )
    
    async def _send_template_message(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar mensagem usando template"""
        try:
            access_token = credentials.get('access_token')
            phone_number_id = credentials.get('phone_number_id')
            
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            template_data = {
                'name': input_data['template_name'],
                'language': {
                    'code': input_data.get('language_code', 'pt_BR')
                }
            }
            
            # Adicionar parâmetros se fornecidos
            if input_data.get('parameters'):
                template_data['components'] = [{
                    'type': 'body',
                    'parameters': [
                        {'type': 'text', 'text': param} 
                        for param in input_data['parameters']
                    ]
                }]
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': input_data['to'],
                'type': 'template',
                'template': template_data
            }
            
            response = await self.http_client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                message_id = result_data.get('messages', [{}])[0].get('id')
                
                return AgentExecutionResult(
                    success=True,
                    data={
                        'message_id': message_id,
                        'status': 'sent',
                        'recipient': input_data['to']
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da WhatsApp API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar template: {str(e)}"
            )
    
    async def _send_media_message(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar mensagem com mídia"""
        try:
            access_token = credentials.get('access_token')
            phone_number_id = credentials.get('phone_number_id')
            
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            media_type = input_data['media_type']
            media_data = {}
            
            # URL ou ID da mídia
            if input_data.get('media_url'):
                media_data['link'] = input_data['media_url']
            elif input_data.get('media_id'):
                media_data['id'] = input_data['media_id']
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message="media_url ou media_id deve ser fornecido"
                )
            
            # Adicionar legenda se fornecida
            if input_data.get('caption'):
                media_data['caption'] = input_data['caption']
            
            # Adicionar nome do arquivo para documentos
            if media_type == 'document' and input_data.get('filename'):
                media_data['filename'] = input_data['filename']
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': input_data['to'],
                'type': media_type,
                media_type: media_data
            }
            
            response = await self.http_client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                message_id = result_data.get('messages', [{}])[0].get('id')
                
                return AgentExecutionResult(
                    success=True,
                    data={
                        'message_id': message_id,
                        'status': 'sent',
                        'recipient': input_data['to']
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da WhatsApp API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar mídia: {str(e)}"
            )
    
    async def _send_interactive_message(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar mensagem interativa"""
        try:
            access_token = credentials.get('access_token')
            phone_number_id = credentials.get('phone_number_id')
            
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            interactive_type = input_data['type']
            
            interactive_data = {
                'type': interactive_type,
                'body': {
                    'text': input_data['body']
                }
            }
            
            # Adicionar cabeçalho se fornecido
            if input_data.get('header'):
                interactive_data['header'] = {
                    'type': 'text',
                    'text': input_data['header']
                }
            
            # Adicionar rodapé se fornecido
            if input_data.get('footer'):
                interactive_data['footer'] = {
                    'text': input_data['footer']
                }
            
            # Configurar ação baseada no tipo
            if interactive_type == 'button':
                if not input_data.get('buttons'):
                    return AgentExecutionResult(
                        success=False,
                        error_message="Botões são obrigatórios para mensagem do tipo button"
                    )
                
                interactive_data['action'] = {
                    'buttons': [
                        {
                            'type': 'reply',
                            'reply': {
                                'id': btn['id'],
                                'title': btn['title']
                            }
                        } for btn in input_data['buttons']
                    ]
                }
                
            elif interactive_type == 'list':
                if not input_data.get('list_items'):
                    return AgentExecutionResult(
                        success=False,
                        error_message="list_items são obrigatórios para mensagem do tipo list"
                    )
                
                interactive_data['action'] = {
                    'button': input_data.get('button_text', 'Ver opções'),
                    'sections': [{
                        'title': 'Opções',
                        'rows': [
                            {
                                'id': item['id'],
                                'title': item['title'],
                                'description': item.get('description', '')
                            } for item in input_data['list_items']
                        ]
                    }]
                }
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': input_data['to'],
                'type': 'interactive',
                'interactive': interactive_data
            }
            
            response = await self.http_client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                message_id = result_data.get('messages', [{}])[0].get('id')
                
                return AgentExecutionResult(
                    success=True,
                    data={
                        'message_id': message_id,
                        'status': 'sent',
                        'recipient': input_data['to']
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da WhatsApp API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar mensagem interativa: {str(e)}"
            )
    
    async def _get_message_status(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Verificar status de uma mensagem"""
        try:
            # Esta funcionalidade normalmente seria implementada via webhooks
            # Por enquanto, retorna status mock
            message_id = input_data['message_id']
            
            return AgentExecutionResult(
                success=True,
                data={
                    'message_id': message_id,
                    'status': 'delivered',
                    'timestamp': datetime.utcnow().isoformat(),
                    'recipient': 'unknown'
                },
                metadata={'note': 'Status mock - implementar via webhooks'}
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao verificar status: {str(e)}"
            )
    
    async def _upload_media(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Fazer upload de mídia"""
        try:
            access_token = credentials.get('access_token')
            phone_number_id = credentials.get('phone_number_id')
            
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/media"
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Fazer download da mídia primeiro
            media_response = await self.http_client.get(input_data['media_url'])
            
            if media_response.status_code != 200:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro ao baixar mídia: {media_response.status_code}"
                )
            
            # Fazer upload para WhatsApp
            files = {
                'file': ('media', media_response.content, input_data['media_type']),
                'messaging_product': (None, 'whatsapp')
            }
            
            response = await self.http_client.post(url, headers=headers, files=files)
            
            if response.status_code == 200:
                result_data = response.json()
                
                return AgentExecutionResult(
                    success=True,
                    data={
                        'media_id': result_data.get('id')
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da WhatsApp API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao fazer upload: {str(e)}"
            )
    
    def _get_supported_providers(self) -> List[str]:
        """Provedores suportados"""
        return ['whatsapp_business']
    
    def _get_category(self) -> str:
        """Categoria do agente"""
        return 'messaging'