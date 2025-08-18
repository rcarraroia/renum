"""
JWT Authentication Middleware
Middleware para autenticação JWT com integração Supabase
"""
import jwt
import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

class JWTAuthMiddleware:
    """Middleware para autenticação JWT"""
    
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_anon_key = settings.SUPABASE_ANON_KEY
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.jwt_expire_minutes = settings.JWT_EXPIRE_MINUTES
        
        # Cache para JWKS (JSON Web Key Set) do Supabase
        self._jwks_cache = {}
        self._jwks_cache_expiry = None
        
        # Cache para usuários validados
        self._user_cache = {}
        self._user_cache_ttl = 300  # 5 minutos
    
    async def get_supabase_jwks(self) -> Dict[str, Any]:
        """Obter JWKS do Supabase com cache"""
        try:
            # Verificar cache
            if (self._jwks_cache and self._jwks_cache_expiry and 
                datetime.utcnow() < self._jwks_cache_expiry):
                return self._jwks_cache
            
            # Buscar JWKS do Supabase
            jwks_url = f"{self.supabase_url}/auth/v1/jwks"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url, timeout=10.0)
                response.raise_for_status()
                
                jwks_data = response.json()
                
                # Atualizar cache
                self._jwks_cache = jwks_data
                self._jwks_cache_expiry = datetime.utcnow() + timedelta(hours=1)
                
                return jwks_data
                
        except Exception as e:
            logger.error("Failed to fetch Supabase JWKS", error=str(e))
            # Retornar cache antigo se disponível
            if self._jwks_cache:
                return self._jwks_cache
            raise
    
    async def verify_supabase_token(self, token: str) -> Dict[str, Any]:
        """Verificar token JWT do Supabase"""
        try:
            # Decodificar header para obter kid (key ID)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid:
                raise ValueError("Token JWT não contém kid")
            
            # Obter JWKS
            jwks = await self.get_supabase_jwks()
            
            # Encontrar chave correspondente
            key = None
            for jwk in jwks.get('keys', []):
                if jwk.get('kid') == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                    break
            
            if not key:
                raise ValueError(f"Chave JWT não encontrada para kid: {kid}")
            
            # Verificar e decodificar token
            payload = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience='authenticated',
                issuer=f"{self.supabase_url}/auth/v1"
            )
            
            # Verificar expiração
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                raise ValueError("Token expirado")
            
            return payload
            
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid Supabase JWT token", error=str(e))
            raise ValueError(f"Token inválido: {str(e)}")
        except Exception as e:
            logger.error("Error verifying Supabase token", error=str(e))
            raise ValueError(f"Erro na verificação do token: {str(e)}")
    
    def verify_local_token(self, token: str) -> Dict[str, Any]:
        """Verificar token JWT local"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            # Verificar expiração
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                raise ValueError("Token expirado")
            
            return payload
            
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid local JWT token", error=str(e))
            raise ValueError(f"Token inválido: {str(e)}")
        except Exception as e:
            logger.error("Error verifying local token", error=str(e))
            raise ValueError(f"Erro na verificação do token: {str(e)}")
    
    async def authenticate_user(self, token: str) -> Dict[str, Any]:
        """Autenticar usuário com token JWT"""
        try:
            # Verificar cache primeiro
            cache_key = f"user_{hash(token)}"
            if cache_key in self._user_cache:
                cached_user, cached_time = self._user_cache[cache_key]
                if datetime.utcnow().timestamp() - cached_time < self._user_cache_ttl:
                    return cached_user
            
            user_data = None
            
            # Tentar verificar como token do Supabase primeiro
            try:
                payload = await self.verify_supabase_token(token)
                user_data = {
                    'user_id': payload.get('sub'),
                    'email': payload.get('email'),
                    'role': payload.get('role', 'user'),
                    'aud': payload.get('aud'),
                    'iss': payload.get('iss'),
                    'provider': 'supabase',
                    'exp': payload.get('exp'),
                    'iat': payload.get('iat')
                }
            except ValueError:
                # Se falhar, tentar como token local
                try:
                    payload = self.verify_local_token(token)
                    user_data = {
                        'user_id': payload.get('user_id'),
                        'email': payload.get('email'),
                        'role': payload.get('role', 'user'),
                        'provider': 'local',
                        'exp': payload.get('exp'),
                        'iat': payload.get('iat')
                    }
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Token inválido: {str(e)}"
                    )
            
            if not user_data or not user_data.get('user_id'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token não contém informações válidas do usuário"
                )
            
            # Atualizar cache
            self._user_cache[cache_key] = (user_data, datetime.utcnow().timestamp())
            
            # Limpar cache antigo
            self._cleanup_user_cache()
            
            return user_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Authentication error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Erro na autenticação"
            )
    
    def _cleanup_user_cache(self):
        """Limpar entradas antigas do cache de usuários"""
        try:
            current_time = datetime.utcnow().timestamp()
            expired_keys = []
            
            for key, (_, cached_time) in self._user_cache.items():
                if current_time - cached_time > self._user_cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._user_cache[key]
                
        except Exception as e:
            logger.warning("Error cleaning user cache", error=str(e))
    
    def generate_local_token(
        self,
        user_id: str,
        email: str,
        role: str = "user",
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Gerar token JWT local"""
        try:
            now = datetime.utcnow()
            exp = now + timedelta(minutes=self.jwt_expire_minutes)
            
            payload = {
                'user_id': user_id,
                'email': email,
                'role': role,
                'iat': int(now.timestamp()),
                'exp': int(exp.timestamp()),
                'iss': 'renum-api',
                'aud': 'renum-users'
            }
            
            if additional_claims:
                payload.update(additional_claims)
            
            token = jwt.encode(
                payload,
                self.jwt_secret,
                algorithm=self.jwt_algorithm
            )
            
            return token
            
        except Exception as e:
            logger.error("Error generating local token", error=str(e))
            raise ValueError(f"Erro ao gerar token: {str(e)}")
    
    async def refresh_token(self, token: str) -> str:
        """Renovar token JWT"""
        try:
            # Verificar token atual (permitindo expiração recente)
            try:
                payload = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=[self.jwt_algorithm],
                    options={"verify_exp": False}  # Não verificar expiração
                )
            except jwt.InvalidTokenError:
                raise ValueError("Token inválido para renovação")
            
            # Verificar se token não está muito antigo (máximo 1 hora após expiração)
            exp = payload.get('exp', 0)
            if datetime.utcnow().timestamp() - exp > 3600:  # 1 hora
                raise ValueError("Token muito antigo para renovação")
            
            # Gerar novo token
            new_token = self.generate_local_token(
                user_id=payload.get('user_id'),
                email=payload.get('email'),
                role=payload.get('role', 'user')
            )
            
            return new_token
            
        except Exception as e:
            logger.error("Error refreshing token", error=str(e))
            raise ValueError(f"Erro ao renovar token: {str(e)}")

# Instância global do middleware
jwt_auth = JWTAuthMiddleware()

# Security scheme para FastAPI
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = security
) -> Dict[str, Any]:
    """Dependency para obter usuário atual autenticado"""
    token = credentials.credentials
    return await jwt_auth.authenticate_user(token)

def require_role(required_role: str):
    """Decorator para exigir role específica"""
    async def role_dependency(
        current_user: Dict[str, Any] = get_current_user
    ) -> Dict[str, Any]:
        user_role = current_user.get('role', 'user')
        
        # Hierarquia de roles: admin > manager > user
        role_hierarchy = {'admin': 3, 'manager': 2, 'user': 1}
        
        required_level = role_hierarchy.get(required_role, 0)
        user_level = role_hierarchy.get(user_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' ou superior necessária"
            )
        
        return current_user
    
    return role_dependency

# Dependências comuns
RequireUser = get_current_user
RequireManager = require_role("manager")
RequireAdmin = require_role("admin")