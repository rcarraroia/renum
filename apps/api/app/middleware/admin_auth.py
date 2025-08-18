"""
Admin Authentication Middleware
Middleware para autenticação e autorização de administradores
"""
import jwt
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

logger = structlog.get_logger(__name__)

security = HTTPBearer()

class AdminAuthMiddleware:
    """Middleware para autenticação de administradores"""
    
    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256"):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        
        # Lista de usuários admin (em produção viria do banco)
        self.admin_users = {
            "admin@renum.com": {
                "id": "admin-001",
                "email": "admin@renum.com",
                "role": "super_admin",
                "permissions": ["*"]  # Todas as permissões
            },
            "manager@renum.com": {
                "id": "manager-001", 
                "email": "manager@renum.com",
                "role": "admin",
                "permissions": [
                    "agents:read", "agents:write", "agents:approve",
                    "integrations:read", "integrations:write",
                    "users:read", "analytics:read"
                ]
            }
        }
    
    def verify_admin_token(self, token: str) -> Dict[str, Any]:
        """Verificar e decodificar token JWT de admin"""
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            
            # Verificar expiração
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expirado"
                )
            
            # Verificar se é usuário admin
            email = payload.get('email')
            if not email or email not in self.admin_users:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado - usuário não é administrador"
                )
            
            user_info = self.admin_users[email]
            payload.update(user_info)
            
            return payload
            
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        except Exception as e:
            logger.error(f"Erro na verificação do token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Erro na autenticação"
            )
    
    def check_permission(self, user: Dict[str, Any], required_permission: str) -> bool:
        """Verificar se usuário tem permissão específica"""
        permissions = user.get('permissions', [])
        
        # Super admin tem todas as permissões
        if "*" in permissions:
            return True
        
        # Verificar permissão específica
        if required_permission in permissions:
            return True
        
        # Verificar permissão por categoria (ex: agents:* permite agents:read)
        category = required_permission.split(':')[0]
        if f"{category}:*" in permissions:
            return True
        
        return False

# Instância global do middleware
admin_auth = AdminAuthMiddleware(
    jwt_secret="admin_jwt_secret_key_change_in_production",
    jwt_algorithm="HS256"
)

async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Dependency para obter usuário admin atual"""
    token = credentials.credentials
    return admin_auth.verify_admin_token(token)

def require_permission(permission: str):
    """Decorator para exigir permissão específica"""
    def permission_dependency(
        current_user: Dict[str, Any] = Depends(get_current_admin_user)
    ) -> Dict[str, Any]:
        if not admin_auth.check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão '{permission}' necessária"
            )
        return current_user
    
    return permission_dependency

# Dependências comuns
RequireAgentRead = Depends(require_permission("agents:read"))
RequireAgentWrite = Depends(require_permission("agents:write"))
RequireAgentApprove = Depends(require_permission("agents:approve"))
RequireIntegrationRead = Depends(require_permission("integrations:read"))
RequireIntegrationWrite = Depends(require_permission("integrations:write"))
RequireUserRead = Depends(require_permission("users:read"))
RequireAnalyticsRead = Depends(require_permission("analytics:read"))
RequireSuperAdmin = Depends(require_permission("*"))