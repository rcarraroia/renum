"""
Make (Integromat) webhook processor
Handles Make scenario webhook events
"""

from typing import Dict, List, Optional, Any

from app.domain.integration import Connection
from .base_processor import BaseWebhookProcessor


class MakeWebhookProcessor(BaseWebhookProcessor):
    """Processor for Make (Integromat) scenario webhooks"""
    
    async def validate_payload(self, connection: Connection, payload: Dict[str, Any]) -> bool:
        """Validate Make webhook payload structure"""
        
        # Make webhooks are flexible, but should have some data
        if not payload:
            return False
        
        # Check for common Make fields
        make_fields = ['scenario_id', 'execution_id', 'bundle_id', 'data']
        has_make_field = any(field in payload for field in make_fields)
        
        # If no specific Make fields, accept any non-empty payload
        return has_make_field or len(payload) > 0
    
    async def extract_events(self, connection: Connection, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from Make webhook payload"""
        
        # Make can send single or multiple bundles
        if 'bundles' in payload and isinstance(payload['bundles'], list):
            # Multiple bundles
            events = []
            for bundle in payload['bundles']:
                events.append({
                    'type': 'make_scenario',
                    'scenario_id': payload.get('scenario_id'),
                    'execution_id': payload.get('execution_id'),
                    'bundle_id': bundle.get('bundle_id'),
                    'data': bundle.get('data', bundle),
                    'raw_payload': bundle
                })
            return events
        else:
            # Single event
            return [{
                'type': 'make_scenario',
                'scenario_id': payload.get('scenario_id'),
                'execution_id': payload.get('execution_id'),
                'bundle_id': payload.get('bundle_id'),
                'data': payload.get('data', payload),
                'raw_payload': payload
            }]
    
    async def process_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual Make event"""
        
        data = event.get('data', {})
        
        # Extract scenario information
        processed_event = {
            'event_type': 'make_scenario',
            'scenario_id': event.get('scenario_id'),
            'execution_id': event.get('execution_id'),
            'bundle_id': event.get('bundle_id'),
            'scenario_type': await self._detect_scenario_type(data),
            'data': await self._normalize_data(data),
            'processed': True,
            'actions': []
        }
        
        # Add actions based on scenario type
        scenario_type = processed_event['scenario_type']
        
        if scenario_type == 'data_sync':
            processed_event['actions'].append('sync_data')
        elif scenario_type == 'notification':
            processed_event['actions'].append('send_notification')
        elif scenario_type == 'file_processing':
            processed_event['actions'].append('process_file')
        elif scenario_type == 'api_integration':
            processed_event['actions'].append('handle_api_data')
        elif scenario_type == 'email_automation':
            processed_event['actions'].append('process_email')
        else:
            processed_event['actions'].append('process_generic_scenario')
        
        return processed_event
    
    async def _detect_scenario_type(self, data: Dict[str, Any]) -> str:
        """Detect the type of Make scenario based on data"""
        
        # Check for common patterns to identify scenario type
        
        # Data sync indicators
        if any(field in data for field in ['source_record', 'target_record', 'sync_status', 'mapping']):
            return 'data_sync'
        
        # Notification indicators
        if any(field in data for field in ['message', 'alert', 'notification_type', 'recipient']):
            return 'notification'
        
        # File processing indicators
        if any(field in data for field in ['file_url', 'file_name', 'file_content', 'document']):
            return 'file_processing'
        
        # API integration indicators
        if any(field in data for field in ['api_response', 'endpoint', 'http_method', 'api_data']):
            return 'api_integration'
        
        # Email automation indicators
        if any(field in data for field in ['email', 'subject', 'sender', 'recipient', 'email_body']):
            return 'email_automation'
        
        # CRM indicators
        if any(field in data for field in ['contact', 'lead', 'deal', 'account', 'opportunity']):
            return 'crm_automation'
        
        # E-commerce indicators
        if any(field in data for field in ['order', 'product', 'customer', 'payment', 'inventory']):
            return 'ecommerce_automation'
        
        # Social media indicators
        if any(field in data for field in ['post', 'tweet', 'social_platform', 'engagement']):
            return 'social_media'
        
        return 'generic'
    
    async def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Make data to standard format"""
        
        normalized = {}
        
        # Common field mappings for Make
        field_mappings = {
            # Identifiers
            'id': ['id', 'record_id', 'item_id', 'object_id'],
            'external_id': ['external_id', 'source_id', 'reference_id', 'remote_id'],
            
            # Content
            'title': ['title', 'name', 'subject', 'headline', 'summary'],
            'description': ['description', 'body', 'content', 'text', 'message', 'details'],
            'url': ['url', 'link', 'href', 'web_url', 'page_url'],
            
            # Timestamps
            'created_at': ['created_at', 'createdAt', 'date_created', 'created', 'timestamp'],
            'updated_at': ['updated_at', 'updatedAt', 'date_modified', 'modified', 'last_updated'],
            
            # Status and Type
            'status': ['status', 'state', 'stage', 'phase', 'condition'],
            'type': ['type', 'category', 'kind', 'classification', 'object_type'],
            
            # User/Contact Information
            'user_id': ['user_id', 'userId', 'owner_id', 'assignee_id', 'created_by'],
            'email': ['email', 'email_address', 'user_email', 'contact_email'],
            'name': ['name', 'full_name', 'display_name', 'user_name', 'contact_name'],
            'first_name': ['first_name', 'firstName', 'given_name'],
            'last_name': ['last_name', 'lastName', 'surname', 'family_name'],
            'phone': ['phone', 'phone_number', 'mobile', 'contact_phone'],
            
            # Business Data
            'company': ['company', 'organization', 'company_name', 'org_name'],
            'amount': ['amount', 'value', 'total', 'sum', 'price'],
            'currency': ['currency', 'currency_code'],
            'quantity': ['quantity', 'count', 'number', 'qty'],
            
            # Location
            'address': ['address', 'location', 'street_address'],
            'city': ['city', 'locality'],
            'country': ['country', 'country_code'],
            'postal_code': ['postal_code', 'zip_code', 'zip']
        }
        
        # Apply field mappings
        for standard_field, possible_fields in field_mappings.items():
            for field in possible_fields:
                if field in data:
                    normalized[standard_field] = data[field]
                    break
        
        # Handle Make-specific nested structures
        if 'attributes' in data and isinstance(data['attributes'], dict):
            # Make often uses 'attributes' for main data
            for key, value in data['attributes'].items():
                if key not in normalized:
                    normalized[key] = value
        
        if 'properties' in data and isinstance(data['properties'], dict):
            # Some Make modules use 'properties'
            for key, value in data['properties'].items():
                if key not in normalized:
                    normalized[key] = value
        
        # Include all original fields with 'raw_' prefix
        for key, value in data.items():
            if key not in normalized and key not in ['attributes', 'properties']:
                normalized[f'raw_{key}'] = value
        
        return normalized
    
    async def get_supported_event_types(self) -> List[str]:
        """Get supported Make event types"""
        return [
            'make_scenario',
            'data_sync',
            'notification',
            'file_processing',
            'api_integration',
            'email_automation',
            'crm_automation',
            'ecommerce_automation',
            'social_media',
            'generic'
        ]
    
    async def validate_connection_config(self, connection: Connection) -> bool:
        """Validate Make connection configuration"""
        
        # Make webhooks are flexible, minimal validation needed
        # Could check for webhook_url if required
        return True
    
    def extract_scenario_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract scenario metadata from Make data"""
        
        metadata = {
            'scenario_id': data.get('scenario_id'),
            'execution_id': data.get('execution_id'),
            'bundle_id': data.get('bundle_id'),
            'module_name': data.get('module_name'),
            'operation': data.get('operation'),
            'started_at': data.get('started_at'),
            'finished_at': data.get('finished_at'),
            'status': data.get('status'),
            'error': data.get('error'),
            'cycles_used': data.get('cycles_used')
        }
        
        return {k: v for k, v in metadata.items() if v is not None}
    
    def extract_crm_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract CRM-specific data from Make payload"""
        
        crm_data = {
            'object_type': data.get('object_type'),  # contact, lead, deal, etc.
            'record_id': data.get('id') or data.get('record_id'),
            'name': data.get('name') or data.get('full_name'),
            'email': data.get('email'),
            'phone': data.get('phone'),
            'company': data.get('company'),
            'status': data.get('status'),
            'stage': data.get('stage'),
            'owner': data.get('owner') or data.get('assigned_to'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at')
        }
        
        # Extract custom fields
        custom_fields = {}
        for key, value in data.items():
            if key.startswith('custom_') or key.startswith('cf_'):
                custom_fields[key] = value
        
        if custom_fields:
            crm_data['custom_fields'] = custom_fields
        
        return {k: v for k, v in crm_data.items() if v is not None}
    
    def extract_ecommerce_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract e-commerce data from Make payload"""
        
        ecommerce_data = {
            'order_id': data.get('order_id') or data.get('id'),
            'customer_id': data.get('customer_id'),
            'customer_email': data.get('customer_email') or data.get('email'),
            'customer_name': data.get('customer_name') or data.get('name'),
            'total_amount': data.get('total_amount') or data.get('amount'),
            'currency': data.get('currency', 'USD'),
            'status': data.get('status') or data.get('order_status'),
            'payment_status': data.get('payment_status'),
            'fulfillment_status': data.get('fulfillment_status'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at')
        }
        
        # Extract line items if present
        if 'line_items' in data or 'items' in data:
            ecommerce_data['items'] = data.get('line_items') or data.get('items')
        
        # Extract addresses
        if 'shipping_address' in data:
            ecommerce_data['shipping_address'] = data['shipping_address']
        if 'billing_address' in data:
            ecommerce_data['billing_address'] = data['billing_address']
        
        return {k: v for k, v in ecommerce_data.items() if v is not None}