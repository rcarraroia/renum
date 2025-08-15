"""
Schemas para autenticação.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    """Schema para requisição de login."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Schema para resposta de login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserInfo"


class UserInfo(BaseModel):
    """Informações básicas do usuário."""
    id: str
    email: str
    name: Optional[str] = None


class RefreshTokenResponse(BaseModel):
    """Schema para resposta de refresh token."""
    access_token: str
    expires_in: int


class ErrorResponse(BaseModel):
    """Schema para respostas de erro."""
    detail: str
    error_code: Optional[str] = None