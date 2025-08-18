"""
JWT Authentication Middleware
Handles JWT token validation with Supabase integration
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import httpx
from datetime import datetime, timezone
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer()
settings = get_settings()

class JWTAuthMiddleware:
    """JWT Authentication middleware for Supabase integration"""
    
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_anon_key = settings.SUPABASE_ANON_KEY
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self._jwks_cache = {}
        self._jwks_cache_expiry = None
    
    async def get_supabase_jwks(self) -> Dict[str, Any]:
        """Get JWKS from Supabase for token verification"""
        try:
            # Cache JWKS for 1 hour
            if (self._jwks_cache and self._jwks_cache_expiry and 
                datetime.now(timezone.utc) < self._jwks_cache_expiry):
                return self._jwks_cache
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/auth/v1/jwks",
                    headers={"apikey": self.supabase_anon_key}
                )
                response.raise_for_status()
                
                self._jwks_cache = response.json()
                self._jwks_cache_expiry = datetime.now(timezone.utc).replace(hour=datetime.now().hour + 1)
                
                return self._jwks_cache
                
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Supabase: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    async def verify_supabase_token(self, token: str) -> Dict[str, Any]:
        """Verify Supabase JWT token"""
        try:
            # Get JWKS for verification
            jwks = await self.get_supabase_jwks()
            
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID"
                )
            
            # Find matching key in JWKS
            key = None
            for jwk_key in jwks.get('keys', []):
                if jwk_key.get('kid') == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk_key)
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token key ID"
                )
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience='authenticated',
                issuer=f"{self.supabase_url}/auth/v1"
            )
            
            return payload
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def verify_local_token(self, token: str) -> Dict[str, Any]:
        """Verify locally issued JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            return payload
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except InvalidTokenError as e:
            logger.warning(f"Invalid local JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def authenticate_request(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Authenticate request using JWT token"""
        token = credentials.credentials
        
        try:
            # Try Supabase token first
            try:
                payload = await self.verify_supabase_token(token)
                payload['auth_provider'] = 'supabase'
                return payload
            except HTTPException:
                # If Supabase fails, try local token
                payload = await self.verify_local_token(token)
                payload['auth_provider'] = 'local'
                return payload
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Get current authenticated user"""
        payload = await self.authenticate_request(credentials)
        
        # Extract user information from token
        user_info = {
            'user_id': payload.get('sub'),
            'email': payload.get('email'),
            'role': payload.get('role', 'user'),
            'auth_provider': payload.get('auth_provider'),
            'exp': payload.get('exp'),
            'iat': payload.get('iat')
        }
        
        # Validate required fields
        if not user_info['user_id']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        return user_info

# Global middleware instance
jwt_auth = JWTAuthMiddleware()

async def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    return await jwt_auth.get_current_user(credentials)

async def get_current_admin_user(credentials: HTTPAuthorizationCredentials = security) -> Dict[str, Any]:
    """Dependency to get current authenticated admin user"""
    user = await jwt_auth.get_current_user(credentials)
    
    if user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user

async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get user if authenticated, None otherwise"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
        return await jwt_auth.get_current_user(credentials)
    except:
        return None