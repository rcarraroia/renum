"""
WhatsApp Business API webhook processor
Handles WhatsApp webhook events and message processing
"""

import re
from typing import Dict, List, Optional, Any

from app.domain.integration import Connection
from .base_processor import BaseWebhookProcessor


class WhatsAppWebhookProcessor(BaseWebhookProcessor):
    """Processor for WhatsApp Business API webhooks"""
    
    async def validate_payload(self, connection: Connection, payload: Dict[str, Any]) -> bool:
        """Validate WhatsApp webhook payload structure"""
        
        # WhatsApp webhook must have 'object' and 'entry' fields
        if 'object' not in payload or 'entry' not in payload:
            return False
        
        # Object should be 'whatsapp_business_account'
        if payload['object'] != 'whatsapp_business_account':
            return False
        
        # Entry should be a list
        if not isinstance(payload['entry'], list):
            return False
        
        return True
    
    async def extract_events(self, connection: Connection, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from WhatsApp webhook payload"""
        
        events = []
        
        for entry in payload.get('entry', []):
            entry_id = entry.get('id')
            
            # Process changes in the entry
            for change in entry.get('changes', []):
                field = change.get('field')
                value = change.get('value', {})
                
                if field == 'messages':
                    # Extract message events
                    for message in value.get('messages', []):
                        events.append({
                            'type': 'message',
                            'entry_id': entry_id,
                            'message': message,
                            'metadata': value.get('metadata', {}),
                            'contacts': value.get('contacts', [])
                        })
                
                elif field == 'message_status':
                    # Extract status update events
                    for status in value.get('statuses', []):
                        events.append({
                            'type': 'message_status',
                            'entry_id': entry_id,
                            'status': status,
                            'metadata': value.get('metadata', {})
                        })
                
                elif field == 'account_alerts':
                    # Extract account alert events
                    events.append({
                        'type': 'account_alert',
                        'entry_id': entry_id,
                        'alert': value,
                        'metadata': value.get('metadata', {})
                    })
        
        return events
    
    async def process_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual WhatsApp event"""
        
        event_type = event.get('type')
        
        if event_type == 'message':
            return await self._process_message_event(connection, event)
        elif event_type == 'message_status':
            return await self._process_status_event(connection, event)
        elif event_type == 'account_alert':
            return await self._process_alert_event(connection, event)
        else:
            return {
                'event_type': event_type,
                'processed': False,
                'error': f'Unknown event type: {event_type}'
            }
    
    async def _process_message_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message event"""
        
        message = event.get('message', {})
        contacts = event.get('contacts', [])
        
        # Extract message details
        message_id = message.get('id')
        from_number = message.get('from')
        timestamp = message.get('timestamp')
        message_type = message.get('type')
        
        # Extract contact info
        contact_info = {}
        for contact in contacts:
            if contact.get('wa_id') == from_number:
                contact_info = {
                    'name': contact.get('profile', {}).get('name'),
                    'wa_id': contact.get('wa_id')
                }
                break
        
        # Extract message content based on type
        content = await self._extract_message_content(message, message_type)
        
        # Process the message (this would trigger agent workflows)
        processed_message = {
            'message_id': message_id,
            'from': from_number,
            'contact': contact_info,
            'timestamp': timestamp,
            'type': message_type,
            'content': content,
            'processed': True,
            'actions': []
        }
        
        # Add potential actions based on message content
        if message_type == 'text':
            text_content = content.get('text', '').lower()
            if any(keyword in text_content for keyword in ['help', 'ajuda', 'suporte']):
                processed_message['actions'].append('trigger_support_agent')
            elif any(keyword in text_content for keyword in ['pedido', 'comprar', 'produto']):
                processed_message['actions'].append('trigger_sales_agent')
        
        return processed_message
    
    async def _process_status_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process message status update event"""
        
        status = event.get('status', {})
        
        return {
            'event_type': 'message_status',
            'message_id': status.get('id'),
            'recipient_id': status.get('recipient_id'),
            'status': status.get('status'),
            'timestamp': status.get('timestamp'),
            'processed': True
        }
    
    async def _process_alert_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process account alert event"""
        
        alert = event.get('alert', {})
        
        return {
            'event_type': 'account_alert',
            'alert_type': alert.get('type'),
            'message': alert.get('message'),
            'processed': True,
            'requires_attention': True
        }
    
    async def _extract_message_content(self, message: Dict[str, Any], message_type: str) -> Dict[str, Any]:
        """Extract content based on message type"""
        
        content = {}
        
        if message_type == 'text':
            content = {
                'text': message.get('text', {}).get('body', '')
            }
        
        elif message_type == 'image':
            image = message.get('image', {})
            content = {
                'media_id': image.get('id'),
                'mime_type': image.get('mime_type'),
                'sha256': image.get('sha256'),
                'caption': image.get('caption', '')
            }
        
        elif message_type == 'document':
            document = message.get('document', {})
            content = {
                'media_id': document.get('id'),
                'filename': document.get('filename'),
                'mime_type': document.get('mime_type'),
                'sha256': document.get('sha256'),
                'caption': document.get('caption', '')
            }
        
        elif message_type == 'audio':
            audio = message.get('audio', {})
            content = {
                'media_id': audio.get('id'),
                'mime_type': audio.get('mime_type'),
                'sha256': audio.get('sha256')
            }
        
        elif message_type == 'video':
            video = message.get('video', {})
            content = {
                'media_id': video.get('id'),
                'mime_type': video.get('mime_type'),
                'sha256': video.get('sha256'),
                'caption': video.get('caption', '')
            }
        
        elif message_type == 'location':
            location = message.get('location', {})
            content = {
                'latitude': location.get('latitude'),
                'longitude': location.get('longitude'),
                'name': location.get('name', ''),
                'address': location.get('address', '')
            }
        
        elif message_type == 'contacts':
            contacts = message.get('contacts', [])
            content = {
                'contacts': contacts
            }
        
        elif message_type == 'interactive':
            interactive = message.get('interactive', {})
            content = {
                'type': interactive.get('type'),
                'button_reply': interactive.get('button_reply'),
                'list_reply': interactive.get('list_reply')
            }
        
        return content
    
    async def get_supported_event_types(self) -> List[str]:
        """Get supported WhatsApp event types"""
        return [
            'message',
            'message_status',
            'account_alert'
        ]
    
    async def validate_connection_config(self, connection: Connection) -> bool:
        """Validate WhatsApp connection configuration"""
        
        required_fields = ['access_token', 'business_phone_number', 'webhook_verify_token']
        
        for field in required_fields:
            if field not in connection.credentials:
                return False
        
        # Validate phone number format
        phone = connection.credentials.get('business_phone_number', '')
        if not re.match(r'^\+\d{10,15}$', phone):
            return False
        
        return True
    
    def extract_phone_number(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        
        # Brazilian phone number patterns
        patterns = [
            r'\+55\s*\(?(\d{2})\)?\s*9?\s*(\d{4,5})-?(\d{4})',  # +55 (11) 99999-9999
            r'\(?(\d{2})\)?\s*9?\s*(\d{4,5})-?(\d{4})',         # (11) 99999-9999
            r'(\d{2})\s*9?\s*(\d{4,5})-?(\d{4})'                # 11 99999-9999
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    return f"+55{groups[0]}{groups[1]}{groups[2]}"
        
        return None
    
    def extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        
        return match.group(0) if match else None
    
    def detect_intent(self, text: str) -> str:
        """Detect user intent from message text"""
        
        text_lower = text.lower()
        
        # Support intents
        if any(word in text_lower for word in ['help', 'ajuda', 'suporte', 'problema', 'erro']):
            return 'support'
        
        # Sales intents
        if any(word in text_lower for word in ['comprar', 'produto', 'preço', 'valor', 'pedido']):
            return 'sales'
        
        # Information intents
        if any(word in text_lower for word in ['info', 'informação', 'sobre', 'como']):
            return 'information'
        
        # Greeting intents
        if any(word in text_lower for word in ['oi', 'olá', 'bom dia', 'boa tarde', 'boa noite']):
            return 'greeting'
        
        return 'general'