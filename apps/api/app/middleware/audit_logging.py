"""
Audit Logging Middleware
Comprehensive audit logging for compliance and security monitoring
"""
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
import json
import time
import logging
import hashlib
from datetime import datetime, timezone
from uuid import uuid4
import asyncio

logger = logging.getLogger(__name__)

class AuditLogger:
    """Audit logging service for compliance and security"""
    
    def __init__(self):
        # Configure audit logger
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # Create audit log handler if not exists
        if not self.audit_logger.handlers:
            handler = logging.FileHandler('audit.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
        
        # Sensitive endpoints that require detailed logging
        self.sensitive_endpoints = [
            '/api/v1/admin/',
            '/api/v1/credentials/',
            '/api/v1/orchestrator/execute',
            '/api/v1/agents/execute'
        ]
        
        # Fields to mask in logs
        self.sensitive_fields = [
            'password', 'token', 'secret', 'key', 'credential',
            'authorization', 'api_key', 'access_token', 'refresh_token'
        ]
    
    def mask_sensitive_data(self, data: Any, path: str = "") -> Any:
        """Recursively mask sensitive data in logs"""
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                key_lower = key.lower()
                current_path = f"{path}.{key}" if path else key
                
                # Check if key contains sensitive information
                if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                    masked[key] = "***MASKED***"
                else:
                    masked[key] = self.mask_sensitive_data(value, current_path)
            return masked
        
        elif isinstance(data, list):
            return [self.mask_sensitive_data(item, f"{path}[{i}]") for i, item in enumerate(data)]
        
        elif isinstance(data, str):
            # Mask potential tokens or secrets in strings
            if len(data) > 20 and any(char.isalnum() for char in data):
                # Looks like a token, mask it
                return f"{data[:4]}***{data[-4:]}" if len(data) > 8 else "***MASKED***"
            return data
        
        else:
            return data
    
    def get_client_info(self, request: Request) -> Dict[str, Any]:
        """Extract client information from request"""
        # Get client IP
        client_ip = request.client.host
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
        
        # Get user agent
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # Get user ID if available
        user_id = getattr(request.state, 'user_id', None)
        user_email = getattr(request.state, 'user_email', None)
        
        return {
            'client_ip': client_ip,
            'user_agent': user_agent,
            'user_id': user_id,
            'user_email': user_email,
            'real_ip': request.headers.get('X-Real-IP'),
            'forwarded_for': forwarded_for
        }
    
    def should_log_endpoint(self, path: str) -> bool:
        """Determine if endpoint should be logged"""
        # Always log sensitive endpoints
        if any(path.startswith(endpoint) for endpoint in self.sensitive_endpoints):
            return True
        
        # Log all POST, PUT, DELETE operations
        return True
    
    def create_request_hash(self, request_data: Dict[str, Any]) -> str:
        """Create hash of request for integrity verification"""
        # Create deterministic string from request data
        request_str = json.dumps(request_data, sort_keys=True, default=str)
        return hashlib.sha256(request_str.encode()).hexdigest()
    
    async def log_request(
        self,
        request: Request,
        request_body: Optional[bytes] = None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """Log incoming request"""
        if not self.should_log_endpoint(request.url.path):
            return {}
        
        request_id = request_id or str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Parse request body if available
        body_data = None
        if request_body:
            try:
                body_data = json.loads(request_body.decode('utf-8'))
                body_data = self.mask_sensitive_data(body_data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                body_data = f"<binary data: {len(request_body)} bytes>"
        
        # Create audit log entry
        audit_entry = {
            'event_type': 'request',
            'request_id': request_id,
            'timestamp': timestamp,
            'method': request.method,
            'path': str(request.url.path),
            'query_params': dict(request.query_params),
            'headers': self.mask_sensitive_data(dict(request.headers)),
            'body': body_data,
            'client_info': self.get_client_info(request),
            'content_length': request.headers.get('content-length'),
            'content_type': request.headers.get('content-type')
        }
        
        # Add request hash for integrity
        audit_entry['request_hash'] = self.create_request_hash(audit_entry)
        
        # Log to audit logger
        self.audit_logger.info(json.dumps(audit_entry, default=str))
        
        return audit_entry
    
    async def log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        processing_time: float,
        request_entry: Dict[str, Any] = None
    ) -> None:
        """Log response"""
        if not self.should_log_endpoint(request.url.path):
            return
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Create response audit entry
        audit_entry = {
            'event_type': 'response',
            'request_id': request_id,
            'timestamp': timestamp,
            'status_code': response.status_code,
            'processing_time_ms': round(processing_time * 1000, 2),
            'response_headers': self.mask_sensitive_data(dict(response.headers)),
            'content_length': response.headers.get('content-length'),
            'content_type': response.headers.get('content-type')
        }
        
        # Add error details for failed requests
        if response.status_code >= 400:
            audit_entry['error'] = True
            audit_entry['severity'] = 'high' if response.status_code >= 500 else 'medium'
        
        # Log to audit logger
        self.audit_logger.info(json.dumps(audit_entry, default=str))
    
    async def log_security_event(
        self,
        request: Request,
        event_type: str,
        details: Dict[str, Any],
        severity: str = 'medium'
    ) -> None:
        """Log security-related events"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        audit_entry = {
            'event_type': 'security_event',
            'security_event_type': event_type,
            'timestamp': timestamp,
            'severity': severity,
            'details': details,
            'client_info': self.get_client_info(request),
            'path': str(request.url.path),
            'method': request.method
        }
        
        # Log to audit logger with appropriate level
        if severity == 'high':
            self.audit_logger.error(json.dumps(audit_entry, default=str))
        elif severity == 'medium':
            self.audit_logger.warning(json.dumps(audit_entry, default=str))
        else:
            self.audit_logger.info(json.dumps(audit_entry, default=str))

class AuditLoggingMiddleware:
    """Audit logging middleware"""
    
    def __init__(self):
        self.audit_logger = AuditLogger()
        # Skip logging for these endpoints to reduce noise
        self.skip_endpoints = [
            '/health',
            '/api/v1/health',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/favicon.ico'
        ]
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Audit logging middleware"""
        # Skip logging for certain endpoints
        if request.url.path in self.skip_endpoints:
            return await call_next(request)
        
        request_id = str(uuid4())
        start_time = time.time()
        
        # Read request body for logging
        request_body = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                request_body = await request.body()
                
                # Recreate request with body for downstream processing
                async def receive():
                    return {
                        'type': 'http.request',
                        'body': request_body,
                        'more_body': False
                    }
                request._receive = receive
                
            except Exception as e:
                logger.error(f"Failed to read request body for audit: {e}")
        
        # Log request
        try:
            request_entry = await self.audit_logger.log_request(
                request, request_body, request_id
            )
        except Exception as e:
            logger.error(f"Failed to log request: {e}")
            request_entry = {}
        
        # Store request info in state for other middlewares
        request.state.request_id = request_id
        request.state.audit_start_time = start_time
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log response
            try:
                await self.audit_logger.log_response(
                    request, response, request_id, processing_time, request_entry
                )
            except Exception as e:
                logger.error(f"Failed to log response: {e}")
            
            return response
            
        except Exception as e:
            # Log exception
            processing_time = time.time() - start_time
            
            try:
                await self.audit_logger.log_security_event(
                    request,
                    'request_exception',
                    {
                        'exception': str(e),
                        'exception_type': type(e).__name__,
                        'processing_time_ms': round(processing_time * 1000, 2)
                    },
                    severity='high'
                )
            except Exception as log_error:
                logger.error(f"Failed to log exception: {log_error}")
            
            # Re-raise the exception
            raise

# Global middleware instance
audit_logging = AuditLoggingMiddleware()

# Utility function for manual security event logging
async def log_security_event(
    request: Request,
    event_type: str,
    details: Dict[str, Any],
    severity: str = 'medium'
) -> None:
    """Utility function to log security events from anywhere in the application"""
    audit_logger = AuditLogger()
    await audit_logger.log_security_event(request, event_type, details, severity)