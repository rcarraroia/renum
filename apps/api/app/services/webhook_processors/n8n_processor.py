"""
n8n webhook processor
Handles n8n workflow webhook events
"""

from typing import Dict, List, Optional, Any

from app.domain.integration import Connection
from .base_processor import BaseWebhookProcessor


class N8nWebhookProcessor(BaseWebhookProcessor):
    """Processor for n8n workflow webhooks"""
    
    async def validate_payload(self, connection: Connection, payload: Dict[str, Any]) -> bool:
        """Validate n8n webhook payload structure"""
        
        # n8n webhooks are flexible, but should have some data
        if not payload:
            return False
        
        # Check for common n8n fields
        n8n_fields = ['workflow_id', 'execution_id', 'node_name', 'data']
        has_n8n_field = any(field in payload for field in n8n_fields)
        
        # If no specific n8n fields, accept any non-empty payload
        return has_n8n_field or len(payload) > 0
    
    async def extract_events(self, connection: Connection, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from n8n webhook payload"""
        
        # n8n can send single or multiple items
        if isinstance(payload, list):
            # Multiple items
            events = []
            for item in payload:
                events.append({
                    'type': 'n8n_workflow',
                    'workflow_id': item.get('workflow_id'),
                    'execution_id': item.get('execution_id'),
                    'node_name': item.get('node_name'),
                    'data': item,
                    'raw_payload': item
                })
            return events
        else:
            # Single item
            return [{
                'type': 'n8n_workflow',
                'workflow_id': payload.get('workflow_id'),
                'execution_id': payload.get('execution_id'),
                'node_name': payload.get('node_name'),
                'data': payload.get('data', payload),
                'raw_payload': payload
            }]
    
    async def process_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual n8n event"""
        
        data = event.get('data', {})
        
        # Extract workflow information
        processed_event = {
            'event_type': 'n8n_workflow',
            'workflow_id': event.get('workflow_id'),
            'execution_id': event.get('execution_id'),
            'node_name': event.get('node_name'),
            'workflow_type': await self._detect_workflow_type(data),
            'data': await self._normalize_data(data),
            'processed': True,
            'actions': []
        }
        
        # Add actions based on workflow type
        workflow_type = processed_event['workflow_type']
        
        if workflow_type == 'data_processing':
            processed_event['actions'].append('process_data')
        elif workflow_type == 'notification':
            processed_event['actions'].append('send_notification')
        elif workflow_type == 'integration':
            processed_event['actions'].append('sync_data')
        elif workflow_type == 'automation':
            processed_event['actions'].append('execute_automation')
        else:
            processed_event['actions'].append('process_generic_workflow')
        
        return processed_event
    
    async def _detect_workflow_type(self, data: Dict[str, Any]) -> str:
        """Detect the type of n8n workflow based on data"""
        
        # Check for common patterns to identify workflow type
        
        # Data processing indicators
        if any(field in data for field in ['records', 'items', 'dataset', 'processed_data']):
            return 'data_processing'
        
        # Notification indicators
        if any(field in data for field in ['message', 'alert', 'notification', 'email_body']):
            return 'notification'
        
        # Integration indicators
        if any(field in data for field in ['source_system', 'target_system', 'sync_status']):
            return 'integration'
        
        # Automation indicators
        if any(field in data for field in ['trigger_event', 'action_type', 'automation_rule']):
            return 'automation'
        
        # API call indicators
        if any(field in data for field in ['api_response', 'http_status', 'endpoint']):
            return 'api_call'
        
        # File processing indicators
        if any(field in data for field in ['file_path', 'file_content', 'file_metadata']):
            return 'file_processing'
        
        return 'generic'
    
    async def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize n8n data to standard format"""
        
        normalized = {}
        
        # Common field mappings for n8n
        field_mappings = {
            # Identifiers
            'id': ['id', 'item_id', 'record_id', 'uuid'],
            'external_id': ['external_id', 'source_id', 'reference_id'],
            
            # Content
            'title': ['title', 'name', 'subject', 'headline'],
            'description': ['description', 'body', 'content', 'text', 'message'],
            'url': ['url', 'link', 'href', 'web_url'],
            
            # Timestamps
            'created_at': ['created_at', 'createdAt', 'date_created', 'timestamp'],
            'updated_at': ['updated_at', 'updatedAt', 'date_modified', 'last_updated'],
            
            # Status
            'status': ['status', 'state', 'stage', 'phase'],
            'type': ['type', 'category', 'kind', 'classification'],
            
            # User/Contact
            'user_id': ['user_id', 'userId', 'owner_id', 'assignee_id'],
            'email': ['email', 'email_address', 'user_email'],
            'name': ['name', 'full_name', 'display_name', 'user_name'],
            
            # Amounts/Numbers
            'amount': ['amount', 'value', 'total', 'sum'],
            'count': ['count', 'quantity', 'number', 'total_count']
        }
        
        # Apply field mappings
        for standard_field, possible_fields in field_mappings.items():
            for field in possible_fields:
                if field in data:
                    normalized[standard_field] = data[field]
                    break
        
        # Handle nested objects (common in n8n)
        if 'json' in data:
            # n8n often wraps data in 'json' field
            json_data = data['json']
            if isinstance(json_data, dict):
                for key, value in json_data.items():
                    if key not in normalized:
                        normalized[key] = value
        
        # Include all original fields with 'raw_' prefix
        for key, value in data.items():
            if key not in normalized and key != 'json':
                normalized[f'raw_{key}'] = value
        
        return normalized
    
    async def get_supported_event_types(self) -> List[str]:
        """Get supported n8n event types"""
        return [
            'n8n_workflow',
            'data_processing',
            'notification',
            'integration',
            'automation',
            'api_call',
            'file_processing',
            'generic'
        ]
    
    async def validate_connection_config(self, connection: Connection) -> bool:
        """Validate n8n connection configuration"""
        
        # n8n webhooks are flexible, minimal validation needed
        # Could check for webhook_url if required
        return True
    
    def extract_workflow_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract workflow metadata from n8n data"""
        
        metadata = {
            'workflow_id': data.get('workflow_id'),
            'execution_id': data.get('execution_id'),
            'node_name': data.get('node_name'),
            'execution_mode': data.get('mode'),
            'started_at': data.get('startedAt'),
            'finished_at': data.get('finishedAt'),
            'status': data.get('status'),
            'error': data.get('error')
        }
        
        return {k: v for k, v in metadata.items() if v is not None}
    
    def extract_processed_items(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract processed items from n8n workflow data"""
        
        items = []
        
        # n8n often sends data as array of items
        if isinstance(data, list):
            items = data
        elif 'items' in data:
            items = data['items']
        elif 'data' in data and isinstance(data['data'], list):
            items = data['data']
        else:
            # Single item
            items = [data]
        
        processed_items = []
        for item in items:
            if isinstance(item, dict):
                # Extract json field if present (common in n8n)
                if 'json' in item:
                    processed_items.append(item['json'])
                else:
                    processed_items.append(item)
        
        return processed_items
    
    def detect_data_operation(self, data: Dict[str, Any]) -> str:
        """Detect what type of data operation was performed"""
        
        # Check for operation indicators
        if 'created' in data or 'inserted' in data:
            return 'create'
        elif 'updated' in data or 'modified' in data:
            return 'update'
        elif 'deleted' in data or 'removed' in data:
            return 'delete'
        elif 'fetched' in data or 'retrieved' in data:
            return 'read'
        elif 'processed' in data or 'transformed' in data:
            return 'transform'
        elif 'sent' in data or 'delivered' in data:
            return 'send'
        
        return 'unknown'