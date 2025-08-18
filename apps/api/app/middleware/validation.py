"""
Request Validation and Sanitization Middleware
Handles input validation, sanitization, and security checks
"""
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import re
import json
import html
import logging
from urllib.parse import unquote
import bleach

logger = logging.getLogger(__name__)

class RequestValidationMiddleware:
    """Request validation and sanitization middleware"""
    
    def __init__(self):
        # SQL injection patterns
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(INFORMATION_SCHEMA|SYSOBJECTS|SYSCOLUMNS)",
            r"(\bxp_cmdshell\b|\bsp_executesql\b)"
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
            r"onmouseover\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>"
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            r"[;&|`$(){}[\]\\]",
            r"\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig|ping|wget|curl|nc|telnet|ssh|ftp)\b",
            r"(\.\.\/|\.\.\\)",
            r"(/etc/passwd|/etc/shadow|/proc/|/sys/)",
            r"(\$\(|\`|&&|\|\|)"
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r"(\.\.\/|\.\.\\)",
            r"(%2e%2e%2f|%2e%2e%5c)",
            r"(\.\.%2f|\.\.%5c)",
            r"(%252e%252e%252f|%252e%252e%255c)"
        ]
        
        # Allowed HTML tags for content that might need basic formatting
        self.allowed_html_tags = [
            'b', 'i', 'u', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li'
        ]
        
        # Maximum request sizes (in bytes)
        self.max_request_sizes = {
            'default': 1024 * 1024,  # 1MB
            '/api/v1/agents/execute': 5 * 1024 * 1024,  # 5MB for agent execution
            '/api/v1/webhooks/': 2 * 1024 * 1024,  # 2MB for webhooks
            '/api/v1/admin/backup': 10 * 1024 * 1024  # 10MB for backups
        }
    
    def detect_sql_injection(self, text: str) -> bool:
        """Detect potential SQL injection attempts"""
        text_lower = text.lower()
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def detect_xss(self, text: str) -> bool:
        """Detect potential XSS attempts"""
        text_lower = text.lower()
        for pattern in self.xss_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def detect_command_injection(self, text: str) -> bool:
        """Detect potential command injection attempts"""
        for pattern in self.command_injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def detect_path_traversal(self, text: str) -> bool:
        """Detect potential path traversal attempts"""
        # URL decode first
        decoded_text = unquote(text)
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, decoded_text, re.IGNORECASE):
                return True
        return False
    
    def sanitize_string(self, text: str, allow_html: bool = False) -> str:
        """Sanitize string input"""
        if not isinstance(text, str):
            return text
        
        # HTML escape
        if allow_html:
            # Allow only safe HTML tags
            text = bleach.clean(text, tags=self.allowed_html_tags, strip=True)
        else:
            text = html.escape(text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def validate_and_sanitize_dict(self, data: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """Recursively validate and sanitize dictionary data"""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize key
            clean_key = self.sanitize_string(str(key))
            current_path = f"{path}.{clean_key}" if path else clean_key
            
            # Check for malicious patterns in key
            if (self.detect_sql_injection(clean_key) or 
                self.detect_xss(clean_key) or 
                self.detect_command_injection(clean_key) or
                self.detect_path_traversal(clean_key)):
                logger.warning(f"Malicious pattern detected in key: {current_path}")
                continue  # Skip malicious keys
            
            # Process value based on type
            if isinstance(value, str):
                # Check for malicious patterns
                if (self.detect_sql_injection(value) or 
                    self.detect_xss(value) or 
                    self.detect_command_injection(value) or
                    self.detect_path_traversal(value)):
                    logger.warning(f"Malicious pattern detected in value at: {current_path}")
                    # For critical security issues, reject the request
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid input detected in field: {current_path}"
                    )
                
                # Sanitize string value
                allow_html = current_path.endswith(('.description', '.content', '.message'))
                sanitized[clean_key] = self.sanitize_string(value, allow_html=allow_html)
                
            elif isinstance(value, dict):
                sanitized[clean_key] = self.validate_and_sanitize_dict(value, current_path)
                
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    self.validate_and_sanitize_dict(item, f"{current_path}[{i}]") 
                    if isinstance(item, dict) 
                    else self.sanitize_string(str(item)) if isinstance(item, str)
                    else item
                    for i, item in enumerate(value)
                ]
                
            else:
                # Keep other types as-is (numbers, booleans, etc.)
                sanitized[clean_key] = value
        
        return sanitized
    
    def validate_request_size(self, request: Request, body_size: int) -> None:
        """Validate request size limits"""
        endpoint = request.url.path
        
        # Get size limit for endpoint
        size_limit = self.max_request_sizes['default']
        for pattern, limit in self.max_request_sizes.items():
            if pattern != 'default' and endpoint.startswith(pattern):
                size_limit = limit
                break
        
        if body_size > size_limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request body too large. Maximum size: {size_limit} bytes"
            )
    
    def validate_headers(self, request: Request) -> None:
        """Validate request headers"""
        # Check for suspicious headers
        suspicious_headers = [
            'x-forwarded-host', 'x-original-url', 'x-rewrite-url'
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                if (self.detect_xss(value) or 
                    self.detect_command_injection(value) or
                    self.detect_path_traversal(value)):
                    logger.warning(f"Malicious pattern in header {header}: {value}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid header value detected"
                    )
        
        # Validate Content-Type for POST/PUT requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '')
            if content_type and not content_type.startswith(('application/json', 'multipart/form-data', 'application/x-www-form-urlencoded')):
                logger.warning(f"Suspicious content-type: {content_type}")
    
    def validate_query_params(self, request: Request) -> None:
        """Validate query parameters"""
        for key, value in request.query_params.items():
            # Check key
            if (self.detect_sql_injection(key) or 
                self.detect_xss(key) or 
                self.detect_command_injection(key) or
                self.detect_path_traversal(key)):
                logger.warning(f"Malicious pattern in query param key: {key}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid query parameter: {key}"
                )
            
            # Check value
            if (self.detect_sql_injection(value) or 
                self.detect_xss(value) or 
                self.detect_command_injection(value) or
                self.detect_path_traversal(value)):
                logger.warning(f"Malicious pattern in query param value: {key}={value}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid query parameter value: {key}"
                )
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Request validation middleware"""
        try:
            # Skip validation for health checks
            if request.url.path in ['/health', '/api/v1/health', '/docs', '/redoc', '/openapi.json']:
                return await call_next(request)
            
            # Validate headers
            self.validate_headers(request)
            
            # Validate query parameters
            self.validate_query_params(request)
            
            # For requests with body, validate and sanitize
            if request.method in ['POST', 'PUT', 'PATCH']:
                # Read body
                body = await request.body()
                
                # Validate request size
                self.validate_request_size(request, len(body))
                
                if body:
                    try:
                        # Parse JSON body
                        json_data = json.loads(body.decode('utf-8'))
                        
                        # Validate and sanitize
                        sanitized_data = self.validate_and_sanitize_dict(json_data)
                        
                        # Replace request body with sanitized data
                        sanitized_body = json.dumps(sanitized_data).encode('utf-8')
                        
                        # Create new request with sanitized body
                        async def receive():
                            return {
                                'type': 'http.request',
                                'body': sanitized_body,
                                'more_body': False
                            }
                        
                        request._receive = receive
                        
                    except json.JSONDecodeError:
                        # Not JSON, skip sanitization but still validate size
                        pass
                    except UnicodeDecodeError:
                        logger.warning("Invalid UTF-8 encoding in request body")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid character encoding"
                        )
            
            # Process request
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Request validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request validation failed"
            )

# Global middleware instance
request_validator = RequestValidationMiddleware()