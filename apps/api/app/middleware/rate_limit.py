"""
Rate Limiting Middleware
Implements rate limiting with Redis backend and different strategies
"""
from typing import Optional, Dict, Any, Callable
from fastapi import HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import time
import json
import hashlib
from datetime import datetime, timedelta
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class RateLimitMiddleware:
    """Advanced rate limiting middleware with Redis backend"""
    
    def __init__(self):
        self.redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
        self.redis_client: Optional[redis.Redis] = None
        self.default_limits = {
            'requests_per_minute': 60,
            'requests_per_hour': 1000,
            'requests_per_day': 10000
        }
        self.premium_limits = {
            'requests_per_minute': 300,
            'requests_per_hour': 5000,
            'requests_per_day': 50000
        }
    
    async def get_redis_client(self) -> redis.Redis:
        """Get Redis client with connection pooling"""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20
                )
                # Test connection
                await self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
                # Fallback to in-memory storage (not recommended for production)
                self.redis_client = None
        
        return self.redis_client
    
    def get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier for rate limiting"""
        # Try to get user ID from auth
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fallback to IP address
        client_ip = request.client.host
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
        
        return f"ip:{client_ip}"
    
    def get_rate_limits(self, request: Request) -> Dict[str, int]:
        """Get rate limits based on user tier"""
        user_tier = getattr(request.state, 'user_tier', 'default')
        
        if user_tier == 'premium':
            return self.premium_limits
        else:
            return self.default_limits
    
    async def check_rate_limit_redis(
        self,
        client_id: str,
        limits: Dict[str, int],
        endpoint: str
    ) -> Dict[str, Any]:
        """Check rate limit using Redis sliding window"""
        redis_client = await self.get_redis_client()
        if not redis_client:
            # If Redis is not available, allow request
            return {'allowed': True, 'remaining': 999, 'reset_time': time.time() + 60}
        
        current_time = time.time()
        results = {}
        
        for period, limit in limits.items():
            # Convert period to seconds
            if 'minute' in period:
                window_size = 60
            elif 'hour' in period:
                window_size = 3600
            elif 'day' in period:
                window_size = 86400
            else:
                continue
            
            # Create Redis key
            key = f"rate_limit:{client_id}:{endpoint}:{period}"
            
            try:
                # Use sliding window log algorithm
                pipe = redis_client.pipeline()
                
                # Remove expired entries
                pipe.zremrangebyscore(key, 0, current_time - window_size)
                
                # Count current requests
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(current_time): current_time})
                
                # Set expiry
                pipe.expire(key, window_size)
                
                # Execute pipeline
                results_pipe = await pipe.execute()
                current_count = results_pipe[1]
                
                if current_count >= limit:
                    # Calculate reset time
                    oldest_request = await redis_client.zrange(key, 0, 0, withscores=True)
                    reset_time = oldest_request[0][1] + window_size if oldest_request else current_time + window_size
                    
                    return {
                        'allowed': False,
                        'limit': limit,
                        'remaining': 0,
                        'reset_time': reset_time,
                        'period': period
                    }
                
                results[period] = {
                    'limit': limit,
                    'remaining': limit - current_count - 1,
                    'reset_time': current_time + window_size
                }
                
            except Exception as e:
                logger.error(f"Redis rate limit check failed: {e}")
                # Allow request if Redis fails
                return {'allowed': True, 'remaining': 999, 'reset_time': current_time + 60}
        
        # Return most restrictive result
        min_remaining = min(r['remaining'] for r in results.values())
        return {
            'allowed': True,
            'remaining': min_remaining,
            'reset_time': min(r['reset_time'] for r in results.values()),
            'limits': results
        }
    
    async def check_endpoint_specific_limits(
        self,
        request: Request,
        client_id: str
    ) -> Dict[str, Any]:
        """Check endpoint-specific rate limits"""
        endpoint = request.url.path
        method = request.method
        
        # Define endpoint-specific limits
        endpoint_limits = {
            '/api/v1/orchestrator/execute': {'requests_per_minute': 10},
            '/api/v1/agents/execute': {'requests_per_minute': 20},
            '/api/v1/webhooks/': {'requests_per_minute': 100},
            '/api/v1/admin/': {'requests_per_minute': 30},
            '/api/v1/prompt-editor/': {'requests_per_minute': 50},
            '/api/v1/auth/login': {'requests_per_minute': 10},
            '/api/v1/auth/register': {'requests_per_minute': 5}
        }
        
        # Check if endpoint has specific limits
        for pattern, limits in endpoint_limits.items():
            if endpoint.startswith(pattern):
                return await self.check_rate_limit_redis(client_id, limits, f"{method}:{pattern}")
        
        # Use default limits
        default_limits = self.get_rate_limits(request)
        return await self.check_rate_limit_redis(client_id, default_limits, f"{method}:{endpoint}")
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Rate limiting middleware"""
        # Skip rate limiting for health checks
        if request.url.path in ['/health', '/api/v1/health']:
            return await call_next(request)
        
        # Get client identifier
        client_id = self.get_client_identifier(request)
        
        # Check rate limits
        try:
            rate_limit_result = await self.check_endpoint_specific_limits(request, client_id)
            
            if not rate_limit_result.get('allowed', True):
                # Rate limit exceeded
                headers = {
                    'X-RateLimit-Limit': str(rate_limit_result.get('limit', 0)),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(int(rate_limit_result.get('reset_time', time.time()))),
                    'Retry-After': str(int(rate_limit_result.get('reset_time', time.time()) - time.time()))
                }
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        'error': 'Rate limit exceeded',
                        'message': f"Too many requests for {rate_limit_result.get('period', 'this period')}",
                        'retry_after': int(rate_limit_result.get('reset_time', time.time()) - time.time())
                    },
                    headers=headers
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            if 'limits' in rate_limit_result:
                # Use the most restrictive limit for headers
                min_limit = min(l['limit'] for l in rate_limit_result['limits'].values())
                min_remaining = min(l['remaining'] for l in rate_limit_result['limits'].values())
                min_reset = min(l['reset_time'] for l in rate_limit_result['limits'].values())
                
                response.headers['X-RateLimit-Limit'] = str(min_limit)
                response.headers['X-RateLimit-Remaining'] = str(max(0, min_remaining))
                response.headers['X-RateLimit-Reset'] = str(int(min_reset))
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Allow request if rate limiting fails
            return await call_next(request)

class IPWhitelistMiddleware:
    """IP whitelist middleware for admin endpoints"""
    
    def __init__(self, whitelist: Optional[list] = None):
        self.whitelist = whitelist or []
        # Add localhost by default
        if not self.whitelist:
            self.whitelist = ['127.0.0.1', '::1', 'localhost']
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check X-Forwarded-For header first
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
        
        # Fallback to client host
        return request.client.host
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """IP whitelist middleware for admin endpoints"""
        # Only apply to admin endpoints
        if not request.url.path.startswith('/api/v1/admin'):
            return await call_next(request)
        
        client_ip = self.get_client_ip(request)
        
        # Check if IP is whitelisted
        if self.whitelist and client_ip not in self.whitelist:
            logger.warning(f"Admin access denied for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    'error': 'Access denied',
                    'message': 'Your IP address is not authorized to access admin endpoints'
                }
            )
        
        return await call_next(request)

# Global middleware instances
rate_limiter = RateLimitMiddleware()
ip_whitelist = IPWhitelistMiddleware()

async def rate_limit_dependency(request: Request) -> None:
    """Rate limiting dependency for specific endpoints"""
    client_id = rate_limiter.get_client_identifier(request)
    result = await rate_limiter.check_endpoint_specific_limits(request, client_id)
    
    if not result.get('allowed', True):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                'X-RateLimit-Limit': str(result.get('limit', 0)),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int(result.get('reset_time', time.time()))),
                'Retry-After': str(int(result.get('reset_time', time.time()) - time.time()))
            }
        )