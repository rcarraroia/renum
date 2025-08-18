"""
Metrics Collection Middleware
Real-time metrics collection for all API requests and responses
"""
from typing import Callable
from fastapi import Request, Response
import time
import logging
from uuid import UUID

from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class MetricsMiddleware:
    """Middleware for collecting real-time metrics"""
    
    def __init__(self):
        # Endpoints to skip metrics collection (to avoid noise)
        self.skip_endpoints = [
            '/health',
            '/api/v1/health',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/favicon.ico',
            '/metrics'  # Avoid recursive metrics
        ]
        
        # Sensitive endpoints that need special handling
        self.sensitive_endpoints = [
            '/api/v1/admin/',
            '/api/v1/credentials/'
        ]
    
    def should_collect_metrics(self, path: str) -> bool:
        """Determine if metrics should be collected for this endpoint"""
        return path not in self.skip_endpoints
    
    def get_endpoint_category(self, path: str) -> str:
        """Categorize endpoint for better metrics organization"""
        if path.startswith('/api/v1/webhooks/'):
            return 'webhooks'
        elif path.startswith('/api/v1/agents/'):
            return 'agents'
        elif path.startswith('/api/v1/orchestrator/'):
            return 'orchestrator'
        elif path.startswith('/api/v1/integrations/'):
            return 'integrations'
        elif path.startswith('/api/v1/credentials/'):
            return 'credentials'
        elif path.startswith('/api/v1/admin/'):
            return 'admin'
        else:
            return 'other'
    
    def sanitize_endpoint_path(self, path: str) -> str:
        """Sanitize endpoint path for metrics (remove IDs, etc.)"""
        import re
        
        # Replace UUIDs with placeholder
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace other IDs (numeric)
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Replace agent IDs (sa-*)
        path = re.sub(r'/sa-[a-zA-Z0-9-]+', '/sa-{agent}', path)
        
        return path
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Metrics collection middleware"""
        # Skip metrics collection for certain endpoints
        if not self.should_collect_metrics(request.url.path):
            return await call_next(request)
        
        start_time = time.time()
        
        # Get user ID if available
        user_id = None
        if hasattr(request.state, 'user_id'):
            try:
                user_id = UUID(request.state.user_id)
            except (ValueError, TypeError):
                user_id = None
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Sanitize endpoint path
            sanitized_path = self.sanitize_endpoint_path(request.url.path)
            
            # Record API request metrics
            try:
                await analytics_service.record_api_request(
                    endpoint=sanitized_path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    user_id=user_id
                )
            except Exception as e:
                logger.error(f"Failed to record API metrics: {e}")
            
            return response
            
        except Exception as e:
            # Record error metrics
            response_time_ms = (time.time() - start_time) * 1000
            sanitized_path = self.sanitize_endpoint_path(request.url.path)
            
            try:
                await analytics_service.record_api_request(
                    endpoint=sanitized_path,
                    method=request.method,
                    status_code=500,  # Internal server error
                    response_time_ms=response_time_ms,
                    user_id=user_id
                )
            except Exception as metrics_error:
                logger.error(f"Failed to record error metrics: {metrics_error}")
            
            # Re-raise the original exception
            raise

# Global middleware instance
metrics_middleware = MetricsMiddleware()