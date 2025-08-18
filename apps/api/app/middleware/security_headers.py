"""
Security Headers Middleware
Adds security headers to all responses for protection against common attacks
"""
from typing import Callable
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware:
    """Security headers middleware for enhanced protection"""
    
    def __init__(self):
        # Default security headers
        self.security_headers = {
            # Prevent clickjacking attacks
            'X-Frame-Options': 'DENY',
            
            # Prevent MIME type sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # Enable XSS protection
            'X-XSS-Protection': '1; mode=block',
            
            # Referrer policy
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Content Security Policy
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            
            # Strict Transport Security (HTTPS only)
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
            
            # Permissions Policy (formerly Feature Policy)
            'Permissions-Policy': (
                'geolocation=(), '
                'microphone=(), '
                'camera=(), '
                'payment=(), '
                'usb=(), '
                'magnetometer=(), '
                'gyroscope=(), '
                'speaker=()'
            ),
            
            # Cross-Origin policies
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-origin',
            
            # Server information hiding
            'Server': 'Renum-API',
            
            # Cache control for sensitive endpoints
            'Cache-Control': 'no-store, no-cache, must-revalidate, private',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        # Relaxed headers for API documentation endpoints
        self.docs_headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://cdn.jsdelivr.net; "
                "connect-src 'self' https:; "
                "frame-ancestors 'self'"
            )
        }
        
        # Public endpoints that need relaxed CORS
        self.public_endpoints = [
            '/health',
            '/api/v1/health',
            '/api/v1/webhooks/'
        ]
    
    def get_headers_for_endpoint(self, path: str) -> dict:
        """Get appropriate headers based on endpoint"""
        # Documentation endpoints need relaxed CSP
        if path in ['/docs', '/redoc', '/openapi.json']:
            headers = self.security_headers.copy()
            headers.update(self.docs_headers)
            return headers
        
        # Public endpoints
        if any(path.startswith(endpoint) for endpoint in self.public_endpoints):
            headers = self.security_headers.copy()
            # Remove some restrictive headers for webhooks
            if path.startswith('/api/v1/webhooks/'):
                headers.pop('Cross-Origin-Resource-Policy', None)
            return headers
        
        # Default security headers
        return self.security_headers
    
    def add_security_headers(self, response: Response, headers: dict) -> None:
        """Add security headers to response"""
        for header, value in headers.items():
            # Don't override existing headers
            if header not in response.headers:
                response.headers[header] = value
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Security headers middleware"""
        try:
            # Process request
            response = await call_next(request)
            
            # Get appropriate headers for this endpoint
            headers = self.get_headers_for_endpoint(request.url.path)
            
            # Add security headers
            self.add_security_headers(response, headers)
            
            # Add custom headers based on response type
            if hasattr(response, 'media_type'):
                if response.media_type == 'application/json':
                    # Additional headers for JSON responses
                    response.headers['X-Content-Type-Options'] = 'nosniff'
                elif response.media_type == 'text/html':
                    # Additional headers for HTML responses
                    response.headers['X-Frame-Options'] = 'DENY'
            
            # Remove server information from error responses
            if hasattr(response, 'status_code') and response.status_code >= 400:
                response.headers.pop('Server', None)
            
            return response
            
        except Exception as e:
            logger.error(f"Security headers middleware error: {e}")
            # Continue with request even if security headers fail
            return await call_next(request)

class CORSSecurityMiddleware:
    """Enhanced CORS middleware with security considerations"""
    
    def __init__(self):
        # Allowed origins (should be configured from environment)
        self.allowed_origins = [
            'http://localhost:3000',
            'http://localhost:5173',
            'https://renum.app',
            'https://app.renum.com'
        ]
        
        # Allowed methods
        self.allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
        
        # Allowed headers
        self.allowed_headers = [
            'Accept',
            'Accept-Language',
            'Content-Language',
            'Content-Type',
            'Authorization',
            'X-Requested-With',
            'X-API-Key'
        ]
        
        # Exposed headers
        self.exposed_headers = [
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset',
            'X-Total-Count'
        ]
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        if not origin:
            return False
        
        # Check exact matches
        if origin in self.allowed_origins:
            return True
        
        # Check wildcard patterns (be very careful with this)
        for allowed in self.allowed_origins:
            if allowed.endswith('*'):
                if origin.startswith(allowed[:-1]):
                    return True
        
        return False
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """CORS security middleware"""
        origin = request.headers.get('origin')
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            if not self.is_origin_allowed(origin):
                return Response(status_code=403)
            
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
            response.headers['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
            response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and self.is_origin_allowed(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Expose-Headers'] = ', '.join(self.exposed_headers)
        
        return response

# Global middleware instances
security_headers = SecurityHeadersMiddleware()
cors_security = CORSSecurityMiddleware()