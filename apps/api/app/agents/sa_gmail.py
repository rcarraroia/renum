"""
Gmail Agent (sa-gmail)
Agente especializado para operações com Gmail API
"""
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

from app.agents.base_agent import BaseAgent, AgentCapability, AgentExecutionResult
from app.domain.credentials import ProviderType

class GmailAgent(BaseAgent):
    """Agente para integração com Gmail API"""
    
    def __init__(self):
        super().__init__(
            agent_id="sa-gmail",
            name="Gmail Agent",
            description="Agente especializado para envio e gerenciamento de emails via Gmail API",
            version="1.0.0"
        )
    
    def _define_capabilities(self) -> List[AgentCapability]:
        """Define capacidades do Gmail Agent"""
        return [
            AgentCapability(
                name="send_email",
                description="Enviar email via Gmail API",
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "array", "items": {"type": "string"}, "description": "Destinatários"},
                        "subject": {"type": "string", "description": "Assunto do email"},
                        "body": {"type": "string", "description": "Corpo do email"},
                        "cc": {"type": "array", "items": {"type": "string"}, "description": "Cópia"},
                        "bcc": {"type": "array", "items": {"type": "string"}, "description": "Cópia oculta"},
                        "html": {"type": "boolean", "description": "Se o corpo é HTML"},
                        "attachments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "filename": {"type": "string"},
                                    "content": {"type": "string", "description": "Base64 encoded"},
                                    "mime_type": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["to", "subject", "body"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "thread_id": {"type": "string"},
                        "status": {"type": "string"}
                    }
                },
                required_credentials=["google"]
            ),
            
            AgentCapability(
                name="read_emails",
                description="Ler emails da caixa de entrada",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Query de busca Gmail"},
                        "max_results": {"type": "integer", "default": 10, "description": "Máximo de emails"},
                        "include_body": {"type": "boolean", "default": False, "description": "Incluir corpo do email"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "emails": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "thread_id": {"type": "string"},
                                    "subject": {"type": "string"},
                                    "from": {"type": "string"},
                                    "to": {"type": "array"},
                                    "date": {"type": "string"},
                                    "body": {"type": "string"},
                                    "snippet": {"type": "string"}
                                }
                            }
                        },
                        "total_count": {"type": "integer"}
                    }
                },
                required_credentials=["google"]
            ),
            
            AgentCapability(
                name="create_draft",
                description="Criar rascunho de email",
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "array", "items": {"type": "string"}},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                        "cc": {"type": "array", "items": {"type": "string"}},
                        "bcc": {"type": "array", "items": {"type": "string"}},
                        "html": {"type": "boolean"}
                    },
                    "required": ["to", "subject", "body"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "draft_id": {"type": "string"},
                        "message_id": {"type": "string"}
                    }
                },
                required_credentials=["google"]
            ),
            
            AgentCapability(
                name="send_draft",
                description="Enviar rascunho existente",
                input_schema={
                    "type": "object",
                    "properties": {
                        "draft_id": {"type": "string", "description": "ID do rascunho"}
                    },
                    "required": ["draft_id"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "thread_id": {"type": "string"},
                        "status": {"type": "string"}
                    }
                },
                required_credentials=["google"]
            )
        ]
    
    async def execute_capability(
        self,
        capability_name: str,
        input_data: Dict[str, Any],
        user_id: UUID,
        credential_id: Optional[UUID] = None
    ) -> AgentExecutionResult:
        """Executa capacidade do Gmail Agent"""
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
                user_id, ProviderType.GOOGLE, credential_id
            )
            
            if not credentials:
                return AgentExecutionResult(
                    success=False,
                    error_message="Credenciais do Google não encontradas"
                )
            
            # Executar capacidade específica
            if capability_name == "send_email":
                result = await self._send_email(input_data, credentials)
            elif capability_name == "read_emails":
                result = await self._read_emails(input_data, credentials)
            elif capability_name == "create_draft":
                result = await self._create_draft(input_data, credentials)
            elif capability_name == "send_draft":
                result = await self._send_draft(input_data, credentials)
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
    
    async def _send_email(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar email via Gmail API"""
        try:
            # Construir mensagem
            message = self._build_email_message(input_data)
            
            # Enviar via Gmail API
            access_token = credentials.get('access_token')
            if not access_token:
                return AgentExecutionResult(
                    success=False,
                    error_message="Access token não encontrado"
                )
            
            # Fazer requisição para Gmail API
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Codificar mensagem em base64
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            payload = {
                'raw': raw_message
            }
            
            response = await self.http_client.post(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result_data = response.json()
                return AgentExecutionResult(
                    success=True,
                    data={
                        'message_id': result_data.get('id'),
                        'thread_id': result_data.get('threadId'),
                        'status': 'sent'
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Gmail API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar email: {str(e)}"
            )
    
    async def _read_emails(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Ler emails da caixa de entrada"""
        try:
            access_token = credentials.get('access_token')
            if not access_token:
                return AgentExecutionResult(
                    success=False,
                    error_message="Access token não encontrado"
                )
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Parâmetros da busca
            params = {
                'maxResults': input_data.get('max_results', 10)
            }
            
            if input_data.get('query'):
                params['q'] = input_data['query']
            
            # Buscar lista de mensagens
            response = await self.http_client.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages',
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Gmail API: {response.status_code}"
                )
            
            messages_data = response.json()
            messages = messages_data.get('messages', [])
            
            # Se incluir corpo, buscar detalhes de cada mensagem
            emails = []
            if input_data.get('include_body', False):
                for msg in messages:
                    msg_response = await self.http_client.get(
                        f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg["id"]}',
                        headers=headers
                    )
                    
                    if msg_response.status_code == 200:
                        msg_data = msg_response.json()
                        email_info = self._parse_email_message(msg_data)
                        emails.append(email_info)
            else:
                # Apenas informações básicas
                for msg in messages:
                    emails.append({
                        'id': msg['id'],
                        'thread_id': msg['threadId']
                    })
            
            return AgentExecutionResult(
                success=True,
                data={
                    'emails': emails,
                    'total_count': len(emails)
                }
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao ler emails: {str(e)}"
            )
    
    async def _create_draft(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Criar rascunho de email"""
        try:
            access_token = credentials.get('access_token')
            if not access_token:
                return AgentExecutionResult(
                    success=False,
                    error_message="Access token não encontrado"
                )
            
            # Construir mensagem
            message = self._build_email_message(input_data)
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Codificar mensagem
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            payload = {
                'message': {
                    'raw': raw_message
                }
            }
            
            response = await self.http_client.post(
                'https://gmail.googleapis.com/gmail/v1/users/me/drafts',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result_data = response.json()
                return AgentExecutionResult(
                    success=True,
                    data={
                        'draft_id': result_data.get('id'),
                        'message_id': result_data.get('message', {}).get('id')
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Gmail API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao criar rascunho: {str(e)}"
            )
    
    async def _send_draft(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Enviar rascunho existente"""
        try:
            access_token = credentials.get('access_token')
            draft_id = input_data['draft_id']
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = await self.http_client.post(
                f'https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}/send',
                headers=headers
            )
            
            if response.status_code == 200:
                result_data = response.json()
                return AgentExecutionResult(
                    success=True,
                    data={
                        'message_id': result_data.get('id'),
                        'thread_id': result_data.get('threadId'),
                        'status': 'sent'
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Gmail API: {response.status_code}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao enviar rascunho: {str(e)}"
            )
    
    def _build_email_message(self, input_data: Dict[str, Any]) -> MIMEMultipart:
        """Constrói mensagem de email"""
        message = MIMEMultipart()
        
        # Cabeçalhos
        message['To'] = ', '.join(input_data['to'])
        message['Subject'] = input_data['subject']
        
        if input_data.get('cc'):
            message['Cc'] = ', '.join(input_data['cc'])
        
        if input_data.get('bcc'):
            message['Bcc'] = ', '.join(input_data['bcc'])
        
        # Corpo da mensagem
        body = input_data['body']
        if input_data.get('html', False):
            message.attach(MIMEText(body, 'html'))
        else:
            message.attach(MIMEText(body, 'plain'))
        
        # Anexos
        if input_data.get('attachments'):
            for attachment in input_data['attachments']:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(base64.b64decode(attachment['content']))
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment["filename"]}'
                )
                message.attach(part)
        
        return message
    
    def _parse_email_message(self, msg_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse dados da mensagem do Gmail"""
        headers = {h['name']: h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
        
        return {
            'id': msg_data.get('id'),
            'thread_id': msg_data.get('threadId'),
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'to': headers.get('To', '').split(', ') if headers.get('To') else [],
            'date': headers.get('Date', ''),
            'snippet': msg_data.get('snippet', ''),
            'body': self._extract_body(msg_data.get('payload', {}))
        }
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extrai corpo da mensagem"""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
        
        return ''
    
    def _get_supported_providers(self) -> List[str]:
        """Provedores suportados"""
        return ['google']
    
    def _get_category(self) -> str:
        """Categoria do agente"""
        return 'communication'