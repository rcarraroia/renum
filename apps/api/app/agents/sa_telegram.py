"""
Telegram Agent (sa-telegram)
Agente especializado para operações com Telegram Bot API
"""
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

from app.agents.base_agent import BaseAgent, AgentCapability, AgentExecutionResult
from app.domain.credentials import ProviderType

class TelegramAgent(BaseAgent):
    """Agente para integração com Telegram Bot API"""
    
    def __init__(self):
        super().__init__(
            agent_id="sa-telegram",
            name="Telegram Agent",
            description="Agente especializado para envio de mensagens via Telegram Bot API",
            version="1.0.0"
        )
    
    def _define_capabilities(self) -> List[AgentCapability]:
        """Define capacidades do Telegram Agent"""
        return [
            AgentCapability(
                name="send_message",
                description="Enviar mensagem de texto",
                input_schema={
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string", "description": "ID do chat ou username"},
                        "text": {"type": "string", "description": "Texto da mensagem"},
                        "parse_mode": {
                            "type": "string",
                            "enum": ["HTML", "Markdown", "MarkdownV2"],
                            "description": "Modo de formatação"
                        },
                        "disable_web_page_preview": {"type": "boolean", "default": False},
                        "disable_notification": {"type": "boolean", "default": False}
                    },
                    "required": ["chat_id", "text"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "integer"},
                        "chat_id": {"type": "integer"},
                        "date": {"type": "integer"}
                    }
                },
                required_credentials=["telegram"]
            ),
            
            AgentCapability(
                name="send_photo",
                description="Enviar foto",
                input_schema={
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string", "description": "ID do chat"},
                        "photo": {"type": "string", "description": "URL da foto ou file_id"},
                        "caption": {"type": "string", "description": "Legenda da foto"},
                        "parse_mode": {"type": "string", "enum": ["HTML", "Markdown", "MarkdownV2"]}
                    },
                    "required": ["chat_id", "photo"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "integer"},
                        "chat_id": {"type": "integer"},
                        "photo": {"type": "array"}
                    }
                },
                required_credentials=["telegram"]
            ),
            
            AgentCapability(
                name="send_document",
                description="Enviar documento",
                input_schema={
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string", "description": "ID do chat"},
                        "document": {"type": "string", "description": "URL do documento ou file_id"},
                        "caption": {"type": "string", "description": "Legenda do documento"},
                        "filename": {"type": "string", "description": "Nome do arquivo"}
                    },
                    "required": ["chat_id", "document"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "integer"},
                        "chat_id": {"type": "integer"},
                        "document": {"type": "object"}
                    }
                },
                required_credentials=["telegram"]
            ),
            
            AgentCapability(
                name="send_keyboard",
                description="Enviar mensagem com teclado inline",
                input_schema={
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string", "description": "ID do chat"},
                        "text": {"type": "string", "description": "Texto da mensagem"},
                        "keyboard": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "callback_data": {"type": "string"},
                                        "url": {"type": "string"}
                                    }
                                }
                            },
                            "description": "Teclado inline (array de arrays de botões)"
                        }
                    },
                    "required": ["chat_id", "text", "keyboard"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "integer"},
                        "chat_id": {"type": "integer"}
                    }
                },
                required_credentials=["telegram"]
            ),
            
            AgentCapability(
                name="get_updates",
                description="Obter atualizações do bot",
                input_schema={
                    "type": "object",
                    "properties": {
                        "offset": {"type": "integer", "description": "Offset para atualizações"},
                        "limit": {"type": "integer", "default": 100, "description": "Limite de atualizações"},
                        "timeout": {"type": "integer", "default": 0, "description": "Timeout para long polling"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "updates": {"type": "array", "description": "Lista de atualizações"}
                    }
                },
                required_credentials=["telegram"]
            ),
            
            AgentCapability(
                name="get_chat_info",
                description="Obter informações de um chat",
                input_schema={
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string", "description": "ID do chat"}
                    },
                    "required": ["chat_id"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "username": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"}
                    }
                },
                required_credentials=["telegram"]
            )
        ]
    
    async def execute_capability(
        self,
        capability_name: str,
        input_data: Dict[str, Any],
        user_id: UUID,
        credential_id: Optional[UUID] = None
    ) -> AgentExecutionResult:
        """Executa capacidade do Telegram Agent"""
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
                user_id, ProviderType.TELEGRAM, credential_id
            )
            
            if not credentials:
                return AgentExecutionResult(
                    success=False,
                    error_message="Credenciais do Telegram não encontradas"
                )
            
            # Executar capacidade específica
            if capability_name == "send_message":
                result = await self._send_message(input_data, credentials)
            elif capability_name == "send_photo":
                result = await self._send_photo(input_data, credentials)
            elif capability_name == "send_document":
                result = await self._send_document(input_data, credentials)
            elif capability_name == "send_keyboard":
                result = await self._send_keyboard(input_data, credentials)
            elif capability_name == "get_updates":
                result = await self._get_updates(input_data, credentials)
            elif capability_name == "get_chat_info":
                result = await self._get_chat_info(input_data, credentials)
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
    
    async def _send_message(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar mensagem de texto"""
        try:
            bot_token = credentials.get('bot_token')
            if not bot_token:
                return AgentExecutionResult(
                    success=False,
                    error_message="Bot token não encontrado"
                )
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            payload = {
                'chat_id': input_data['chat_id'],
                'text': input_data['text']
            }
            
            # Parâmetros opcionais
            if input_data.get('parse_mode'):
                payload['parse_mode'] = input_data['parse_mode']
            
            if input_data.get('disable_web_page_preview'):
                payload['disable_web_page_preview'] = True
            
            if input_data.get('disable_notification'):
                payload['disable_notification'] = True
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    message = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'message_id': message.get('message_id'),
                            'chat_id': message.get('chat', {}).get('id'),
                            'date': message.get('date')
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar mensagem: {str(e)}"
            )
    
    async def _send_photo(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar foto"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            
            payload = {
                'chat_id': input_data['chat_id'],
                'photo': input_data['photo']
            }
            
            if input_data.get('caption'):
                payload['caption'] = input_data['caption']
            
            if input_data.get('parse_mode'):
                payload['parse_mode'] = input_data['parse_mode']
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    message = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'message_id': message.get('message_id'),
                            'chat_id': message.get('chat', {}).get('id'),
                            'photo': message.get('photo', [])
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar foto: {str(e)}"
            )
    
    async def _send_document(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar documento"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            
            payload = {
                'chat_id': input_data['chat_id'],
                'document': input_data['document']
            }
            
            if input_data.get('caption'):
                payload['caption'] = input_data['caption']
            
            if input_data.get('filename'):
                payload['filename'] = input_data['filename']
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    message = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'message_id': message.get('message_id'),
                            'chat_id': message.get('chat', {}).get('id'),
                            'document': message.get('document', {})
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar documento: {str(e)}"
            )
    
    async def _send_keyboard(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar mensagem com teclado inline"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Construir teclado inline
            inline_keyboard = []
            for row in input_data['keyboard']:
                keyboard_row = []
                for button in row:
                    btn = {'text': button['text']}
                    if button.get('callback_data'):
                        btn['callback_data'] = button['callback_data']
                    elif button.get('url'):
                        btn['url'] = button['url']
                    keyboard_row.append(btn)
                inline_keyboard.append(keyboard_row)
            
            payload = {
                'chat_id': input_data['chat_id'],
                'text': input_data['text'],
                'reply_markup': {
                    'inline_keyboard': inline_keyboard
                }
            }
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    message = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'message_id': message.get('message_id'),
                            'chat_id': message.get('chat', {}).get('id')
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar teclado: {str(e)}"
            )
    
    async def _get_updates(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Obter atualizações do bot"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            
            params = {}
            
            if input_data.get('offset'):
                params['offset'] = input_data['offset']
            
            if input_data.get('limit'):
                params['limit'] = input_data['limit']
            
            if input_data.get('timeout'):
                params['timeout'] = input_data['timeout']
            
            response = await self.http_client.get(url, params=params)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'updates': result_data.get('result', [])
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao obter atualizações: {str(e)}"
            )
    
    async def _get_chat_info(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Obter informações de um chat"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/getChat"
            
            params = {
                'chat_id': input_data['chat_id']
            }
            
            response = await self.http_client.get(url, params=params)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    chat = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'id': chat.get('id'),
                            'type': chat.get('type'),
                            'title': chat.get('title'),
                            'username': chat.get('username'),
                            'first_name': chat.get('first_name'),
                            'last_name': chat.get('last_name')
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao obter info do chat: {str(e)}"
            )
    
    def _get_supported_providers(self) -> List[str]:
        """Provedores suportados"""
        return ['telegram']
    
    def _get_category(self) -> str:
        """Categoria do agente"""
        return 'messaging'
    
    async def _send_photo(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar foto"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            
            payload = {
                'chat_id': input_data['chat_id'],
                'photo': input_data['photo']
            }
            
            # Parâmetros opcionais
            if input_data.get('caption'):
                payload['caption'] = input_data['caption']
            
            if input_data.get('parse_mode'):
                payload['parse_mode'] = input_data['parse_mode']
            
            if input_data.get('disable_notification'):
                payload['disable_notification'] = input_data['disable_notification']
            
            if input_data.get('reply_to_message_id'):
                payload['reply_to_message_id'] = input_data['reply_to_message_id']
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    message = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'message_id': message.get('message_id'),
                            'chat_id': message.get('chat', {}).get('id'),
                            'photo': message.get('photo', [])
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar foto: {str(e)}"
            )
    
    async def _send_document(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar documento"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            
            payload = {
                'chat_id': input_data['chat_id'],
                'document': input_data['document']
            }
            
            # Parâmetros opcionais
            if input_data.get('caption'):
                payload['caption'] = input_data['caption']
            
            if input_data.get('parse_mode'):
                payload['parse_mode'] = input_data['parse_mode']
            
            if input_data.get('disable_notification'):
                payload['disable_notification'] = input_data['disable_notification']
            
            if input_data.get('reply_to_message_id'):
                payload['reply_to_message_id'] = input_data['reply_to_message_id']
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    message = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'message_id': message.get('message_id'),
                            'chat_id': message.get('chat', {}).get('id'),
                            'document': message.get('document', {})
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar documento: {str(e)}"
            )
    
    async def _send_inline_keyboard(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar mensagem com teclado inline"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Construir teclado inline
            inline_keyboard = []
            for row in input_data['keyboard']:
                keyboard_row = []
                for button in row:
                    btn_data = {'text': button['text']}
                    
                    if button.get('callback_data'):
                        btn_data['callback_data'] = button['callback_data']
                    elif button.get('url'):
                        btn_data['url'] = button['url']
                    
                    keyboard_row.append(btn_data)
                
                inline_keyboard.append(keyboard_row)
            
            payload = {
                'chat_id': input_data['chat_id'],
                'text': input_data['text'],
                'reply_markup': {
                    'inline_keyboard': inline_keyboard
                }
            }
            
            if input_data.get('parse_mode'):
                payload['parse_mode'] = input_data['parse_mode']
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    message = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'message_id': message.get('message_id'),
                            'chat_id': message.get('chat', {}).get('id'),
                            'text': message.get('text')
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar teclado: {str(e)}"
            )
    
    async def _get_chat_info(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Obter informações de um chat"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/getChat"
            
            payload = {
                'chat_id': input_data['chat_id']
            }
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    chat = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'id': chat.get('id'),
                            'type': chat.get('type'),
                            'title': chat.get('title'),
                            'username': chat.get('username'),
                            'first_name': chat.get('first_name'),
                            'last_name': chat.get('last_name')
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao obter info do chat: {str(e)}"
            )
    
    async def _get_bot_info(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Obter informações do bot"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                result_data = response.json()
                
                if result_data.get('ok'):
                    bot = result_data.get('result', {})
                    return AgentExecutionResult(
                        success=True,
                        data={
                            'id': bot.get('id'),
                            'is_bot': bot.get('is_bot'),
                            'first_name': bot.get('first_name'),
                            'username': bot.get('username'),
                            'can_join_groups': bot.get('can_join_groups'),
                            'can_read_all_group_messages': bot.get('can_read_all_group_messages'),
                            'supports_inline_queries': bot.get('supports_inline_queries')
                        }
                    )
                else:
                    return AgentExecutionResult(
                        success=False,
                        error_message=result_data.get('description', 'Erro desconhecido')
                    )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao obter info do bot: {str(e)}"
            )
    
    async def _set_webhook(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Configurar webhook do bot"""
        try:
            bot_token = credentials.get('bot_token')
            url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
            
            payload = {
                'url': input_data['url']
            }
            
            # Parâmetros opcionais
            if input_data.get('max_connections'):
                payload['max_connections'] = input_data['max_connections']
            
            if input_data.get('allowed_updates'):
                payload['allowed_updates'] = input_data['allowed_updates']
            
            if input_data.get('drop_pending_updates'):
                payload['drop_pending_updates'] = input_data['drop_pending_updates']
            
            response = await self.http_client.post(url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                return AgentExecutionResult(
                    success=result_data.get('ok', False),
                    data={
                        'ok': result_data.get('ok'),
                        'description': result_data.get('description', '')
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Telegram API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao configurar webhook: {str(e)}"
            )
    
    def _get_supported_providers(self) -> List[str]:
        """Provedores suportados"""
        return ['telegram']
    
    def _get_category(self) -> str:
        """Categoria do agente"""
        return 'messaging'