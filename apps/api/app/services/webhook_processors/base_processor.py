"""
Base webhook processor
Abstract base class for platform-specific webhook processors
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from app.domain.integration import Connection


class WebhookProcessingResult:
    """Result of webhook processing"""
    
    def __init__(
        self,
        success: bool,
        processed_events: List[Dict[str, Any]],
        execution_time_ms: int,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.processed_events = processed_events
        self.execution_time_ms = execution_time_ms
        self.error_message = error_message
        self.metadata = metadata or {}
        self.processed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'processed_events': self.processed_events,
            'execution_time_ms': self.execution_time_ms,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'processed_at': self.processed_at.isoformat()
        }


class BaseWebhookProcessor(ABC):
    """Abstract base class for webhook processors"""
    
    def __init__(self):
        self.platform_name = self.__class__.__name__.replace('WebhookProcessor', '').lower()
    
    @abstractmethod
    async def validate_payload(self, connection: Connection, payload: Dict[str, Any]) -> bool:
        """Validate webhook payload structure"""
        pass
    
    @abstractmethod
    async def extract_events(self, connection: Connection, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from webhook payload"""
        pass
    
    @abstractmethod
    async def process_event(self, connection: Connection, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual event"""
        pass
    
    async def process_webhook(
        self, 
        connection: Connection, 
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> WebhookProcessingResult:
        """Process complete webhook"""
        
        start_time = datetime.utcnow()
        
        try:
            # Validate payload
            if not await self.validate_payload(connection, payload):
                return WebhookProcessingResult(
                    success=False,
                    processed_events=[],
                    execution_time_ms=self._calculate_execution_time(start_time),
                    error_message="Invalid payload structure"
                )
            
            # Extract events
            events = await self.extract_events(connection, payload)
            
            # Process each event
            processed_events = []
            for event in events:
                try:
                    processed_event = await self.process_event(connection, event)
                    processed_events.append(processed_event)
                except Exception as e:
                    # Log individual event error but continue processing
                    processed_events.append({
                        'event': event,
                        'error': str(e),
                        'processed': False
                    })
            
            return WebhookProcessingResult(
                success=True,
                processed_events=processed_events,
                execution_time_ms=self._calculate_execution_time(start_time),
                metadata=metadata
            )
            
        except Exception as e:
            return WebhookProcessingResult(
                success=False,
                processed_events=[],
                execution_time_ms=self._calculate_execution_time(start_time),
                error_message=str(e),
                metadata=metadata
            )
    
    def _calculate_execution_time(self, start_time: datetime) -> int:
        """Calculate execution time in milliseconds"""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    def _sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize payload for logging (remove sensitive data)"""
        
        sensitive_keys = ['token', 'password', 'secret', 'key', 'auth', 'credential']
        
        def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            sanitized = {}
            for key, value in d.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    sanitized[key] = '***REDACTED***'
                elif isinstance(value, dict):
                    sanitized[key] = sanitize_dict(value)
                elif isinstance(value, list):
                    sanitized[key] = [sanitize_dict(item) if isinstance(item, dict) else item for item in value]
                else:
                    sanitized[key] = value
            return sanitized
        
        return sanitize_dict(payload)
    
    async def get_supported_event_types(self) -> List[str]:
        """Get list of supported event types for this processor"""
        return []
    
    async def validate_connection_config(self, connection: Connection) -> bool:
        """Validate that connection has required configuration for this processor"""
        return True