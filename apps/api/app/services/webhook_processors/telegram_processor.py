"""
Telegram Bot API webhook processor
Handles Telegram webhook events and message processing
"""

from typing import Dict, List, Optional, Any

from app.domain.integration import Connection
from .base_processor import BaseWebhookProcessor


class TelegramWebhookProcessor(BaseWebhookProcessor):
    """Processor for Telegram Bot API webhooks"""
    
    async def validate_payload(self, connection: Connection, payload: Dict[str, Any]) -> bool:
        """Validate Telegram webhook payload structure"""
        
        # Telegram webhook must have 'update_id'
        if 'update_id' not in payload:
            return False
        
        # Must have at least one update type
        update_types = [
            'message', 'edited_message', 'channel_post', 'edited_channel_post',
            'inline_query', 'chosen_inline_result', 'callback_query',
            'shipping_query', 'pre_checkout_query', 'poll', 'poll_answer'
        ]
        
        return any(update_type in payload for update_type in update_types)
    
    async def extract_events(self, connection: Connection, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from Telegram webhook payload"""
        
        events = []
        update_id = payload.get('update_id')
        
        # Message events
        if 'message' in payload:
            events.append({
                'type': 'message',
                'update_id': update_id,
                'message': payload['message']
            })
        
        # Edited message events
        if 'edited_message' in payload:
            events.append({
                'type': 'edited_message',
                'update_id': update_id,
                'message': payload['edited_message']
            })
        
        # Callback query events (inline keyboard buttons)
        if 'callback_query' in payload:
            events.append({
                'type': 'callback_query',
                'update_id': update_id,
                'callback_query': payload['callback_query']
            })
        
        # Inline query events
        if 'inline_query' in payload:
            events.append({
                'type': 'inline_query',
                'update_id': update_id,
                'inline_query': payload['inline_query']
            })
        
        # Channel post events
        if 'channel_post' in payload:
            events.append({
                'type': 'channel_post',
                'update_id': update_id,
                'channel_post': payload['channel_post']
            })
        
        return events
    
    async def process_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual Telegram event"""
        
        event_type = event.get('type')
        
        if event_type == 'message':
            return await self._process_message_event(connection, event)
        elif event_type == 'edited_message':
            return await self._process_edited_message_event(connection, event)
        elif event_type == 'callback_query':
            return await self._process_callback_query_event(connection, event)
        elif event_type == 'inline_query':
            return await self._process_inline_query_event(connection, event)
        elif event_type == 'channel_post':
            return await self._process_channel_post_event(connection, event)
        else:
            return {
                'event_type': event_type,
                'processed': False,
                'error': f'Unknown event type: {event_type}'
            }
    
    async def _process_message_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message event"""
        
        message = event.get('message', {})
        
        # Extract message details
        message_id = message.get('message_id')
        chat = message.get('chat', {})
        user = message.get('from', {})
        date = message.get('date')
        
        # Extract message content
        content = await self._extract_message_content(message)
        
        # Detect intent and commands
        intent = await self._detect_intent(message)
        commands = await self._extract_commands(message)
        
        processed_message = {
            'message_id': message_id,
            'chat': {
                'id': chat.get('id'),
                'type': chat.get('type'),
                'title': chat.get('title'),
                'username': chat.get('username')
            },
            'user': {
                'id': user.get('id'),
                'username': user.get('username'),
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name')
            },
            'date': date,
            'content': content,
            'intent': intent,
            'commands': commands,
            'processed': True,
            'actions': []
        }
        
        # Add actions based on content
        if commands:
            for command in commands:
                if command == '/start':
                    processed_message['actions'].append('send_welcome_message')
                elif command == '/help':
                    processed_message['actions'].append('send_help_message')
                elif command.startswith('/'):
                    processed_message['actions'].append(f'handle_command_{command[1:]}')
        
        if intent == 'support':
            processed_message['actions'].append('trigger_support_agent')
        elif intent == 'sales':
            processed_message['actions'].append('trigger_sales_agent')
        
        return processed_message
    
    async def _process_edited_message_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process edited message event"""
        
        message = event.get('message', {})
        
        return {
            'event_type': 'edited_message',
            'message_id': message.get('message_id'),
            'chat_id': message.get('chat', {}).get('id'),
            'user_id': message.get('from', {}).get('id'),
            'edit_date': message.get('edit_date'),
            'content': await self._extract_message_content(message),
            'processed': True
        }
    
    async def _process_callback_query_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process callback query event (inline keyboard button press)"""
        
        callback_query = event.get('callback_query', {})
        
        return {
            'event_type': 'callback_query',
            'id': callback_query.get('id'),
            'user': callback_query.get('from'),
            'message': callback_query.get('message'),
            'data': callback_query.get('data'),
            'processed': True,
            'actions': [f'handle_callback_{callback_query.get("data", "unknown")}']
        }
    
    async def _process_inline_query_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process inline query event"""
        
        inline_query = event.get('inline_query', {})
        
        return {
            'event_type': 'inline_query',
            'id': inline_query.get('id'),
            'user': inline_query.get('from'),
            'query': inline_query.get('query'),
            'offset': inline_query.get('offset'),
            'processed': True,
            'actions': ['handle_inline_query']
        }
    
    async def _process_channel_post_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process channel post event"""
        
        channel_post = event.get('channel_post', {})
        
        return {
            'event_type': 'channel_post',
            'message_id': channel_post.get('message_id'),
            'chat': channel_post.get('chat'),
            'date': channel_post.get('date'),
            'content': await self._extract_message_content(channel_post),
            'processed': True
        }
    
    async def _extract_message_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content based on message type"""
        
        content = {}
        
        # Text message
        if 'text' in message:
            content['type'] = 'text'
            content['text'] = message['text']
            if 'entities' in message:
                content['entities'] = message['entities']
        
        # Photo message
        elif 'photo' in message:
            content['type'] = 'photo'
            content['photo'] = message['photo']
            content['caption'] = message.get('caption', '')
        
        # Document message
        elif 'document' in message:
            content['type'] = 'document'
            content['document'] = message['document']
            content['caption'] = message.get('caption', '')
        
        # Audio message
        elif 'audio' in message:
            content['type'] = 'audio'
            content['audio'] = message['audio']
            content['caption'] = message.get('caption', '')
        
        # Video message
        elif 'video' in message:
            content['type'] = 'video'
            content['video'] = message['video']
            content['caption'] = message.get('caption', '')
        
        # Voice message
        elif 'voice' in message:
            content['type'] = 'voice'
            content['voice'] = message['voice']
        
        # Video note (circular video)
        elif 'video_note' in message:
            content['type'] = 'video_note'
            content['video_note'] = message['video_note']
        
        # Location message
        elif 'location' in message:
            content['type'] = 'location'
            content['location'] = message['location']
        
        # Contact message
        elif 'contact' in message:
            content['type'] = 'contact'
            content['contact'] = message['contact']
        
        # Sticker message
        elif 'sticker' in message:
            content['type'] = 'sticker'
            content['sticker'] = message['sticker']
        
        # Poll message
        elif 'poll' in message:
            content['type'] = 'poll'
            content['poll'] = message['poll']
        
        return content
    
    async def _detect_intent(self, message: Dict[str, Any]) -> str:
        """Detect user intent from message"""
        
        text = message.get('text', '').lower()
        
        # Support intents
        if any(word in text for word in ['help', 'ajuda', 'suporte', 'problema', 'erro']):
            return 'support'
        
        # Sales intents
        if any(word in text for word in ['comprar', 'produto', 'preço', 'valor', 'pedido']):
            return 'sales'
        
        # Information intents
        if any(word in text for word in ['info', 'informação', 'sobre', 'como']):
            return 'information'
        
        # Greeting intents
        if any(word in text for word in ['oi', 'olá', 'bom dia', 'boa tarde', 'boa noite', '/start']):
            return 'greeting'
        
        return 'general'
    
    async def _extract_commands(self, message: Dict[str, Any]) -> List[str]:
        """Extract bot commands from message"""
        
        commands = []
        
        # Check for entities of type 'bot_command'
        entities = message.get('entities', [])
        text = message.get('text', '')
        
        for entity in entities:
            if entity.get('type') == 'bot_command':
                offset = entity.get('offset', 0)
                length = entity.get('length', 0)
                command = text[offset:offset + length]
                commands.append(command)
        
        return commands
    
    async def get_supported_event_types(self) -> List[str]:
        """Get supported Telegram event types"""
        return [
            'message',
            'edited_message',
            'callback_query',
            'inline_query',
            'channel_post'
        ]
    
    async def validate_connection_config(self, connection: Connection) -> bool:
        """Validate Telegram connection configuration"""
        
        # Must have bot token
        if 'bot_token' not in connection.credentials:
            return False
        
        # Validate bot token format (should contain ':')
        bot_token = connection.credentials.get('bot_token', '')
        if ':' not in bot_token:
            return False
        
        return True