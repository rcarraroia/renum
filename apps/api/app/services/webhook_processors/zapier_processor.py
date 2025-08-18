"""
Zapier webhook processor
Handles Zapier webhook events and automation triggers
"""

from typing import Dict, List, Optional, Any

from app.domain.integration import Connection
from .base_processor import BaseWebhookProcessor


class ZapierWebhookProcessor(BaseWebhookProcessor):
    """Processor for Zapier webhooks"""
    
    async def validate_payload(self, connection: Connection, payload: Dict[str, Any]) -> bool:
        """Validate Zapier webhook payload structure"""
        
        # Zapier webhooks are flexible, but should have some data
        if not payload:
            return False
        
        # Check for common Zapier fields
        zapier_fields = ['zap_id', 'trigger_id', 'data', 'meta']
        has_zapier_field = any(field in payload for field in zapier_fields)
        
        # If no specific Zapier fields, accept any non-empty payload
        return has_zapier_field or len(payload) > 0
    
    async def extract_events(self, connection: Connection, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from Zapier webhook payload"""
        
        # Zapier typically sends one event per webhook
        events = [{
            'type': 'zapier_trigger',
            'zap_id': payload.get('zap_id'),
            'trigger_id': payload.get('trigger_id'),
            'data': payload.get('data', payload),  # Use 'data' field or entire payload
            'meta': payload.get('meta', {}),
            'raw_payload': payload
        }]
        
        return events
    
    async def process_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual Zapier event"""
        
        data = event.get('data', {})
        meta = event.get('meta', {})
        
        # Extract common fields from Zapier data
        processed_event = {
            'event_type': 'zapier_trigger',
            'zap_id': event.get('zap_id'),
            'trigger_id': event.get('trigger_id'),
            'trigger_type': await self._detect_trigger_type(data),
            'data': await self._normalize_data(data),
            'meta': meta,
            'processed': True,
            'actions': []
        }
        
        # Add actions based on trigger type
        trigger_type = processed_event['trigger_type']
        
        if trigger_type == 'form_submission':
            processed_event['actions'].append('process_form_submission')
        elif trigger_type == 'email_received':
            processed_event['actions'].append('process_email')
        elif trigger_type == 'calendar_event':
            processed_event['actions'].append('process_calendar_event')
        elif trigger_type == 'payment_received':
            processed_event['actions'].append('process_payment')
        elif trigger_type == 'file_upload':
            processed_event['actions'].append('process_file_upload')
        else:
            processed_event['actions'].append('process_generic_trigger')
        
        return processed_event
    
    async def _detect_trigger_type(self, data: Dict[str, Any]) -> str:
        """Detect the type of Zapier trigger based on data"""
        
        # Check for common field patterns to identify trigger type
        
        # Form submission indicators
        if any(field in data for field in ['form_id', 'form_name', 'submission_id', 'form_data']):
            return 'form_submission'
        
        # Email indicators
        if any(field in data for field in ['email', 'subject', 'from', 'to', 'body']):
            return 'email_received'
        
        # Calendar event indicators
        if any(field in data for field in ['event_id', 'start_time', 'end_time', 'calendar_id']):
            return 'calendar_event'
        
        # Payment indicators
        if any(field in data for field in ['amount', 'currency', 'payment_id', 'transaction_id']):
            return 'payment_received'
        
        # File upload indicators
        if any(field in data for field in ['file_url', 'file_name', 'file_size', 'upload_id']):
            return 'file_upload'
        
        # CRM indicators
        if any(field in data for field in ['contact_id', 'lead_id', 'deal_id', 'customer_id']):
            return 'crm_update'
        
        # E-commerce indicators
        if any(field in data for field in ['order_id', 'product_id', 'customer_email', 'order_total']):
            return 'ecommerce_order'
        
        # Social media indicators
        if any(field in data for field in ['post_id', 'tweet_id', 'social_platform', 'engagement']):
            return 'social_media'
        
        return 'generic'
    
    async def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Zapier data to standard format"""
        
        normalized = {}
        
        # Common field mappings
        field_mappings = {
            # Contact/User fields
            'email': ['email', 'email_address', 'user_email', 'contact_email'],
            'name': ['name', 'full_name', 'contact_name', 'user_name'],
            'first_name': ['first_name', 'fname', 'given_name'],
            'last_name': ['last_name', 'lname', 'surname', 'family_name'],
            'phone': ['phone', 'phone_number', 'mobile', 'contact_phone'],
            
            # Content fields
            'title': ['title', 'subject', 'name', 'heading'],
            'description': ['description', 'body', 'content', 'message', 'text'],
            'url': ['url', 'link', 'website', 'page_url'],
            
            # Identifiers
            'id': ['id', 'record_id', 'item_id', 'entry_id'],
            'external_id': ['external_id', 'reference_id', 'source_id'],
            
            # Timestamps
            'created_at': ['created_at', 'date_created', 'timestamp', 'created'],
            'updated_at': ['updated_at', 'date_modified', 'last_updated', 'modified'],
            
            # Amounts
            'amount': ['amount', 'total', 'price', 'value', 'cost'],
            'currency': ['currency', 'currency_code']
        }
        
        # Apply field mappings
        for standard_field, possible_fields in field_mappings.items():
            for field in possible_fields:
                if field in data:
                    normalized[standard_field] = data[field]
                    break
        
        # Include all original fields with 'raw_' prefix
        for key, value in data.items():
            if key not in normalized:
                normalized[f'raw_{key}'] = value
        
        return normalized
    
    async def get_supported_event_types(self) -> List[str]:
        """Get supported Zapier event types"""
        return [
            'zapier_trigger',
            'form_submission',
            'email_received',
            'calendar_event',
            'payment_received',
            'file_upload',
            'crm_update',
            'ecommerce_order',
            'social_media',
            'generic'
        ]
    
    async def validate_connection_config(self, connection: Connection) -> bool:
        """Validate Zapier connection configuration"""
        
        # Zapier webhooks are flexible, minimal validation needed
        # Could check for webhook_url if required
        return True
    
    def extract_contact_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contact information from Zapier data"""
        
        contact_info = {}
        
        # Email
        email_fields = ['email', 'email_address', 'user_email', 'contact_email']
        for field in email_fields:
            if field in data:
                contact_info['email'] = data[field]
                break
        
        # Name
        if 'name' in data or 'full_name' in data:
            contact_info['name'] = data.get('name') or data.get('full_name')
        elif 'first_name' in data or 'last_name' in data:
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            contact_info['name'] = f"{first_name} {last_name}".strip()
        
        # Phone
        phone_fields = ['phone', 'phone_number', 'mobile', 'contact_phone']
        for field in phone_fields:
            if field in data:
                contact_info['phone'] = data[field]
                break
        
        # Company
        company_fields = ['company', 'organization', 'company_name']
        for field in company_fields:
            if field in data:
                contact_info['company'] = data[field]
                break
        
        return contact_info
    
    def extract_form_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract form submission data"""
        
        form_data = {
            'form_id': data.get('form_id'),
            'form_name': data.get('form_name'),
            'submission_id': data.get('submission_id'),
            'submitted_at': data.get('submitted_at') or data.get('created_at'),
            'fields': {}
        }
        
        # Extract form fields (Zapier often prefixes with 'field_')
        for key, value in data.items():
            if key.startswith('field_') or key.startswith('form_'):
                field_name = key.replace('field_', '').replace('form_', '')
                form_data['fields'][field_name] = value
        
        return form_data
    
    def extract_ecommerce_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract e-commerce order data"""
        
        order_data = {
            'order_id': data.get('order_id'),
            'customer_email': data.get('customer_email') or data.get('email'),
            'customer_name': data.get('customer_name') or data.get('name'),
            'total_amount': data.get('total_amount') or data.get('amount'),
            'currency': data.get('currency', 'USD'),
            'status': data.get('status') or data.get('order_status'),
            'items': data.get('items', []),
            'shipping_address': data.get('shipping_address'),
            'billing_address': data.get('billing_address')
        }
        
        return order_data