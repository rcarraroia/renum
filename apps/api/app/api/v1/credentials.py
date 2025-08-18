"""
User Credentials API endpoints
Handles secure credential management, OAuth flows, and validation
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.schemas.credentials import (
    CreateOAuthCredentialSchema,
    CreateAPIKeyCredentialSchema,
    CreateBasicAuthCredentialSchema,
    UpdateCredentialSchema,
    CredentialResponseSchema,
    OAuthFlowStartSchema,
    OAuthFlowCompleteSchema,
    CredentialValidationResponseSchema,
    CredentialStatsSchema
)
from app.services.user_credentials_service import UserCredentialsService
from app.domain.credentials import ProviderType, CredentialStatus

router = APIRouter(prefix="/credentials", tags=["Credentials"])

def get_credentials_service() -> UserCredentialsService:
    """Get credentials service instance"""
    return UserCredentialsService()

@router.post("/oauth", response_model=CredentialResponseSchema)
async def create_oauth_credential(
    credential_data: CreateOAuthCredentialSchema,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Create OAuth credential"""
    try:
        # For now, use a mock user ID
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        credential = await credentials_service.create_oauth_credential(
            user_id=mock_user_id,
            provider=ProviderType(credential_data.provider),
            name=credential_data.name,
            client_id=credential_data.client_id,
            client_secret=credential_data.client_secret,
            scopes=credential_data.scopes,
            additional_data=credential_data.additional_data
        )
        
        return CredentialResponseSchema(
            id=credential.id,
            name=credential.name,
            provider=credential.provider.value,
            credential_type=credential.credential_type.value,
            status=credential.status.value,
            expires_at=credential.expires_at,
            expires_soon=credential.expires_soon(),
            is_expired=credential.is_expired(),
            needs_validation=credential.needs_validation(),
            scopes=credential.scopes,
            created_at=credential.created_at,
            last_validated_at=credential.last_validated_at,
            fingerprint=credential.fingerprint
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/api-key", response_model=CredentialResponseSchema)
async def create_api_key_credential(
    credential_data: CreateAPIKeyCredentialSchema,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Create API key credential"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        credential = await credentials_service.create_api_key_credential(
            user_id=mock_user_id,
            provider=ProviderType(credential_data.provider),
            name=credential_data.name,
            api_key=credential_data.api_key,
            additional_data=credential_data.additional_data,
            expires_at=credential_data.expires_at
        )
        
        return CredentialResponseSchema(
            id=credential.id,
            name=credential.name,
            provider=credential.provider.value,
            credential_type=credential.credential_type.value,
            status=credential.status.value,
            expires_at=credential.expires_at,
            expires_soon=credential.expires_soon(),
            is_expired=credential.is_expired(),
            needs_validation=credential.needs_validation(),
            scopes=credential.scopes,
            created_at=credential.created_at,
            last_validated_at=credential.last_validated_at,
            fingerprint=credential.fingerprint
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/basic-auth", response_model=CredentialResponseSchema)
async def create_basic_auth_credential(
    credential_data: CreateBasicAuthCredentialSchema,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Create basic auth credential"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        credential = await credentials_service.create_basic_auth_credential(
            user_id=mock_user_id,
            provider=ProviderType(credential_data.provider),
            name=credential_data.name,
            username=credential_data.username,
            password=credential_data.password,
            additional_data=credential_data.additional_data
        )
        
        return CredentialResponseSchema(
            id=credential.id,
            name=credential.name,
            provider=credential.provider.value,
            credential_type=credential.credential_type.value,
            status=credential.status.value,
            expires_at=credential.expires_at,
            expires_soon=credential.expires_soon(),
            is_expired=credential.is_expired(),
            needs_validation=credential.needs_validation(),
            scopes=credential.scopes,
            created_at=credential.created_at,
            last_validated_at=credential.last_validated_at,
            fingerprint=credential.fingerprint
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )

@router.get("/", response_model=List[CredentialResponseSchema])
async def list_credentials(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """List user credentials"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        provider_enum = ProviderType(provider) if provider else None
        status_enum = CredentialStatus(status_filter) if status_filter else None
        
        credentials = await credentials_service.get_user_credentials(
            user_id=mock_user_id,
            provider=provider_enum,
            status=status_enum
        )
        
        return [
            CredentialResponseSchema(
                id=UUID(cred['id']),
                name=cred['name'],
                provider=cred['provider'],
                credential_type=cred['credential_type'],
                status=cred['status'],
                expires_at=cred['expires_at'],
                expires_soon=cred['expires_soon'],
                is_expired=cred['is_expired'],
                needs_validation=cred['needs_validation'],
                scopes=cred['scopes'],
                created_at=cred['created_at'],
                last_validated_at=cred['last_validated_at'],
                fingerprint=cred['fingerprint']
            ) for cred in credentials
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar credenciais: {str(e)}"
        )

@router.get("/{credential_id}", response_model=CredentialResponseSchema)
async def get_credential(
    credential_id: UUID,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Get credential by ID"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        credential = await credentials_service.get_credential_by_id(
            credential_id=credential_id,
            user_id=mock_user_id
        )
        
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credencial não encontrada"
            )
        
        return CredentialResponseSchema(
            id=UUID(credential['id']),
            name=credential['name'],
            provider=credential['provider'],
            credential_type=credential['credential_type'],
            status=credential['status'],
            expires_at=credential['expires_at'],
            expires_soon=credential['expires_soon'],
            is_expired=credential['is_expired'],
            needs_validation=credential['needs_validation'],
            scopes=credential['scopes'],
            created_at=credential['created_at'],
            last_validated_at=credential['last_validated_at'],
            fingerprint=credential['fingerprint']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar credencial: {str(e)}"
        )

@router.put("/{credential_id}", response_model=CredentialResponseSchema)
async def update_credential(
    credential_id: UUID,
    update_data: UpdateCredentialSchema,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Update credential"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        credential = await credentials_service.update_credential(
            credential_id=credential_id,
            user_id=mock_user_id,
            name=update_data.name,
            new_data=update_data.new_data,
            expires_at=update_data.expires_at
        )
        
        return CredentialResponseSchema(
            id=credential.id,
            name=credential.name,
            provider=credential.provider.value,
            credential_type=credential.credential_type.value,
            status=credential.status.value,
            expires_at=credential.expires_at,
            expires_soon=credential.expires_soon(),
            is_expired=credential.is_expired(),
            needs_validation=credential.needs_validation(),
            scopes=credential.scopes,
            created_at=credential.created_at,
            last_validated_at=credential.last_validated_at,
            fingerprint=credential.fingerprint
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar credencial: {str(e)}"
        )

@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: UUID,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Delete credential"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        success = await credentials_service.delete_credential(credential_id, mock_user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credencial não encontrada"
            )
        
        return {"message": "Credencial removida com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover credencial: {str(e)}"
        )

@router.post("/{credential_id}/validate", response_model=CredentialValidationResponseSchema)
async def validate_credential(
    credential_id: UUID,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Validate credential"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        result = await credentials_service.validate_credential(credential_id, mock_user_id)
        
        return CredentialValidationResponseSchema(
            is_valid=result.is_valid,
            error_message=result.error_message,
            metadata=result.metadata,
            expires_at=result.expires_at,
            scopes=result.scopes,
            validated_at=result.validated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao validar credencial: {str(e)}"
        )

@router.post("/oauth/start")
async def start_oauth_flow(
    oauth_data: OAuthFlowStartSchema,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Start OAuth flow"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        auth_url, state = await credentials_service.start_oauth_flow(
            user_id=mock_user_id,
            provider=ProviderType(oauth_data.provider),
            scopes=oauth_data.scopes,
            redirect_uri=oauth_data.redirect_uri
        )
        
        return {
            "authorization_url": auth_url,
            "state": state,
            "message": "Acesse a URL para autorizar a aplicação"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao iniciar fluxo OAuth: {str(e)}"
        )

@router.post("/oauth/complete", response_model=CredentialResponseSchema)
async def complete_oauth_flow(
    oauth_data: OAuthFlowCompleteSchema,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Complete OAuth flow"""
    try:
        credential = await credentials_service.complete_oauth_flow(
            state=oauth_data.state,
            authorization_code=oauth_data.code,
            credential_name=oauth_data.credential_name
        )
        
        return CredentialResponseSchema(
            id=credential.id,
            name=credential.name,
            provider=credential.provider.value,
            credential_type=credential.credential_type.value,
            status=credential.status.value,
            expires_at=credential.expires_at,
            expires_soon=credential.expires_soon(),
            is_expired=credential.is_expired(),
            needs_validation=credential.needs_validation(),
            scopes=credential.scopes,
            created_at=credential.created_at,
            last_validated_at=credential.last_validated_at,
            fingerprint=credential.fingerprint
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao completar fluxo OAuth: {str(e)}"
        )

@router.post("/{credential_id}/refresh", response_model=CredentialResponseSchema)
async def refresh_oauth_token(
    credential_id: UUID,
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Refresh OAuth access token"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        credential = await credentials_service.refresh_oauth_token(credential_id, mock_user_id)
        
        return CredentialResponseSchema(
            id=credential.id,
            name=credential.name,
            provider=credential.provider.value,
            credential_type=credential.credential_type.value,
            status=credential.status.value,
            expires_at=credential.expires_at,
            expires_soon=credential.expires_soon(),
            is_expired=credential.is_expired(),
            needs_validation=credential.needs_validation(),
            scopes=credential.scopes,
            created_at=credential.created_at,
            last_validated_at=credential.last_validated_at,
            fingerprint=credential.fingerprint
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao renovar token: {str(e)}"
        )

@router.get("/stats/overview", response_model=CredentialStatsSchema)
async def get_credential_stats(
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Get credential statistics"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        stats = await credentials_service.get_credential_stats(mock_user_id)
        
        return CredentialStatsSchema(
            total_credentials=stats['total_credentials'],
            active_credentials=stats['active_credentials'],
            expired_credentials=stats['expired_credentials'],
            invalid_credentials=stats['invalid_credentials'],
            by_provider=stats['by_provider']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas: {str(e)}"
        )

@router.get("/expiring/check")
async def check_expiring_credentials(
    days_ahead: int = Query(7, ge=1, le=30, description="Days ahead to check"),
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Check for credentials expiring soon"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        expiring = await credentials_service.check_expiring_credentials(mock_user_id, days_ahead)
        
        return {
            "expiring_count": len(expiring),
            "days_ahead": days_ahead,
            "credentials": expiring
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao verificar credenciais expirando: {str(e)}"
        )

@router.post("/validate-all")
async def validate_all_credentials(
    credentials_service: UserCredentialsService = Depends(get_credentials_service)
):
    """Validate all user credentials"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        results = await credentials_service.validate_all_user_credentials(mock_user_id)
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao validar credenciais: {str(e)}"
        )

@router.get("/providers/metadata")
async def get_providers_metadata():
    """Get metadata for all supported providers"""
    try:
        from app.domain.credentials import CREDENTIAL_METADATA
        
        metadata = {}
        for provider, meta in CREDENTIAL_METADATA.items():
            metadata[provider.value] = meta.to_dict()
        
        return metadata
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter metadados: {str(e)}"
        )