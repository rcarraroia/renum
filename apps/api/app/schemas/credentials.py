"""
Pydantic schemas for user credentials
Schemas para validação de dados de credenciais de usuário
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

class CreateOAuthCredentialSchema(BaseModel):
    """Schema for creating OAuth credentials"""
    
    provider: str = Field(..., description="Provider name (google, meta, microsoft, etc.)")
    name: str = Field(..., min_length=1, max_length=100, description="Display name for the credential")
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    scopes: Optional[List[str]] = Field(default=[], description="OAuth scopes")
    additional_data: Optional[Dict[str, Any]] = Field(default={}, description="Additional OAuth data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "google",
                "name": "My Google Account",
                "client_id": "your_client_id",
                "client_secret": "your_client_secret",
                "scopes": ["email", "profile", "https://www.googleapis.com/auth/gmail.send"],
                "additional_data": {"account_type": "personal"}
            }
        }

class CreateAPIKeyCredentialSchema(BaseModel):
    """Schema for creating API key credentials"""
    
    provider: str = Field(..., description="Provider name (whatsapp_business, telegram, etc.)")
    name: str = Field(..., min_length=1, max_length=100, description="Display name for the credential")
    api_key: str = Field(..., description="API key or access token")
    additional_data: Optional[Dict[str, Any]] = Field(default={}, description="Additional API data")
    expires_at: Optional[datetime] = Field(None, description="When the API key expires")
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "whatsapp_business",
                "name": "My WhatsApp Business",
                "api_key": "your_access_token",
                "additional_data": {
                    "phone_number_id": "123456789",
                    "business_account_id": "987654321"
                },
                "expires_at": "2024-12-31T23:59:59Z"
            }
        }

class CreateBasicAuthCredentialSchema(BaseModel):
    """Schema for creating basic auth credentials"""
    
    provider: str = Field(..., description="Provider name or custom_api")
    name: str = Field(..., min_length=1, max_length=100, description="Display name for the credential")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    additional_data: Optional[Dict[str, Any]] = Field(default={}, description="Additional auth data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "custom_api",
                "name": "My Custom API",
                "username": "api_user",
                "password": "api_password",
                "additional_data": {
                    "base_url": "https://api.example.com",
                    "version": "v1"
                }
            }
        }

class UpdateCredentialSchema(BaseModel):
    """Schema for updating user credentials"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="New display name")
    new_data: Optional[Dict[str, Any]] = Field(None, description="New credential data to merge")
    expires_at: Optional[datetime] = Field(None, description="New expiration date")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Credential Name",
                "new_data": {"api_key": "new_api_key_value"},
                "expires_at": "2025-12-31T23:59:59Z"
            }
        }

class CredentialResponseSchema(BaseModel):
    """Schema for credential response (safe for display)"""
    
    id: UUID = Field(..., description="Credential ID")
    provider: str = Field(..., description="Provider name")
    credential_type: str = Field(..., description="Type of credential")
    name: str = Field(..., description="Display name")
    status: str = Field(..., description="Credential status")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    expires_soon: bool = Field(..., description="Whether credential expires soon")
    is_expired: bool = Field(..., description="Whether credential is expired")
    needs_validation: bool = Field(..., description="Whether credential needs validation")
    scopes: List[str] = Field(..., description="OAuth scopes or permissions")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_validated_at: Optional[datetime] = Field(None, description="Last validation timestamp")
    fingerprint: str = Field(..., description="Credential fingerprint for integrity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "provider": "google",
                "credential_type": "oauth2",
                "name": "My Google Account",
                "status": "active",
                "expires_at": "2024-12-31T23:59:59Z",
                "expires_soon": False,
                "is_expired": False,
                "needs_validation": False,
                "scopes": ["email", "profile"],
                "created_at": "2024-01-01T00:00:00Z",
                "last_validated_at": "2024-01-01T00:00:00Z",
                "fingerprint": "abc123def456"
            }
        }

class OAuthFlowStartSchema(BaseModel):
    """Schema for starting OAuth flow"""
    
    provider: str = Field(..., description="OAuth provider")
    scopes: List[str] = Field(..., description="Requested OAuth scopes")
    redirect_uri: str = Field(..., description="Redirect URI after authorization")
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "google",
                "scopes": ["email", "profile", "https://www.googleapis.com/auth/gmail.send"],
                "redirect_uri": "https://myapp.com/oauth/callback"
            }
        }

class OAuthFlowCompleteSchema(BaseModel):
    """Schema for completing OAuth flow"""
    
    state: str = Field(..., description="OAuth state parameter")
    code: str = Field(..., description="Authorization code from provider")
    credential_name: str = Field(..., min_length=1, max_length=100, description="Name for the credential")
    
    class Config:
        json_schema_extra = {
            "example": {
                "state": "random_state_string",
                "code": "authorization_code_from_provider",
                "credential_name": "My Google Account"
            }
        }

class CredentialValidationResponseSchema(BaseModel):
    """Schema for credential validation response"""
    
    is_valid: bool = Field(..., description="Whether the credential is valid")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    metadata: Dict[str, Any] = Field(default={}, description="Additional validation metadata")
    expires_at: Optional[datetime] = Field(None, description="Token expiration if available")
    scopes: List[str] = Field(default=[], description="Validated scopes")
    validated_at: datetime = Field(..., description="Validation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": True,
                "error_message": None,
                "metadata": {"user_id": "12345", "email": "user@example.com"},
                "expires_at": "2024-12-31T23:59:59Z",
                "scopes": ["email", "profile"],
                "validated_at": "2024-01-01T12:00:00Z"
            }
        }

class CredentialStatsSchema(BaseModel):
    """Schema for credential statistics"""
    
    total_credentials: int = Field(..., description="Total number of credentials")
    active_credentials: int = Field(..., description="Number of active credentials")
    expired_credentials: int = Field(..., description="Number of expired credentials")
    invalid_credentials: int = Field(..., description="Number of invalid credentials")
    by_provider: Dict[str, int] = Field(..., description="Credentials count by provider")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_credentials": 10,
                "active_credentials": 8,
                "expired_credentials": 1,
                "invalid_credentials": 1,
                "by_provider": {
                    "google": 3,
                    "meta": 2,
                    "whatsapp_business": 2,
                    "telegram": 2,
                    "custom_api": 1
                }
            }
        }