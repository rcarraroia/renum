"""
Endpoints de autenticação.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from datetime import timedelta

from app.schemas.auth import LoginRequest, LoginResponse, RefreshTokenResponse, UserInfo
from app.core.security import authenticate_user, create_access_token, get_current_user, security
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """
    Autentica um usuário com email e senha.
    
    Args:
        login_data: Dados de login (email e senha)
        
    Returns:
        Token de acesso e informações do usuário
        
    Raises:
        HTTPException: Se as credenciais forem inválidas
    """
    # Autentica com Supabase
    auth_result = await authenticate_user(login_data.email, login_data.password)
    
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria token JWT
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": auth_result["user"]["id"], "email": auth_result["user"]["email"]},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,  # em segundos
        user=UserInfo(
            id=auth_result["user"]["id"],
            email=auth_result["user"]["email"],
            name=auth_result["user"]["name"]
        )
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Renova um token de acesso.
    
    Args:
        credentials: Token atual no header Authorization
        
    Returns:
        Novo token de acesso
        
    Raises:
        HTTPException: Se o token for inválido
    """
    # Verifica o token atual
    current_user = await get_current_user(credentials)
    
    # Cria novo token
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user["id"], "email": current_user["email"]},
        expires_delta=access_token_expires
    )
    
    return RefreshTokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60  # em segundos
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Obtém informações do usuário atual.
    
    Args:
        current_user: Usuário atual (injetado via dependency)
        
    Returns:
        Informações do usuário autenticado
    """
    return UserInfo(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user.get("user_metadata", {}).get("name", "")
    )