"""
BYOC (Bring Your Own Credentials) Pydantic schemas for multi-agent system
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class CredentialScope(BaseModel):
    """Schema for credential scope definition"""
    service: str = Field(..., description="Service name (e.g., 'gmail', 'whatsapp')")
    permissions: List[str] = Field(..., description="List of permissions/scopes")
    description: str = Field(..., description="Human-readable description of what this scope allows")


class CreateCredentialSchema(BaseModel):
    """Schema for creating new user credentials"""
    service_type: str = Field(..., description="Type of service (gmail, whatsapp, supabase, etc.)")
    service_name: str = Field(..., description="User-friendly name for this credential")
    credentials: Dict[str, Any] = Field(..., description="Raw credential data (will be encrypted)")
    scopes: Optional[List[str]] = Field(None, description="OAuth scopes or permissions")
    expires_at: Optional[datetime] = Field(None, description="Credential expiration time")
    
    @validator('service_type')
    def validate_service_type(cls, v):
        allowed_types = [
            'gmail', 'whatsapp', 'telegram', 'supabase', 'zapier', 
            'n8n', 'make', 'oauth_google', 'oauth_meta', 'api_key'
        ]
        if v not in allowed_types:
            raise ValueError(f'Service type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('service_name')
    def validate_service_name(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Service name must be at least 3 characters')
        return v.strip()
    
    @validator('credentials')
    def validate_credentials(cls, v):
        if not v:
            raise ValueError('Credentials cannot be empty')
        # Ensure no sensitive data is logged
        return v


class UpdateCredentialSchema(BaseModel):
    """Schema for updating existing credentials"""
    service_name: Optional[str] = Field(None, description="User-friendly name for this credential")
    credentials: Optional[Dict[str, Any]] = Field(None, description="Updated credential data")
    scopes: Optional[List[str]] = Field(None, description="Updated OAuth scopes")
    expires_at: Optional[datetime] = Field(None, description="Updated expiration time")


class UserCredentialSchema(BaseModel):
    """Schema for user credential (without sensitive data)"""
    id: UUID
    user_id: UUID
    service_type: str
    service_name: str
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    status: str = Field(..., description="Status: active, expired, error, revoked")
    last_validated_at: Optional[datetime] = None
    validation_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Note: encrypted_credentials is intentionally excluded for security
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class CredentialValidationResult(BaseModel):
    """Schema for credential validation result"""
    credential_id: UUID
    is_valid: bool
    validation_message: str
    expires_at: Optional[datetime] = None
    scopes_verified: Optional[List[str]] = None
    last_validated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class OAuthFlowInitiation(BaseModel):
    """Schema for initiating OAuth flow"""
    service_type: str = Field(..., description="OAuth service type")
    service_name: str = Field(..., description="User-friendly name")
    scopes: List[str] = Field(..., description="Requested OAuth scopes")
    redirect_uri: Optional[str] = Field(None, description="OAuth redirect URI")
    
    @validator('service_type')
    def validate_service_type(cls, v):
        oauth_services = ['oauth_google', 'oauth_meta', 'oauth_github', 'oauth_microsoft']
        if v not in oauth_services:
            raise ValueError(f'OAuth service type must be one of: {", ".join(oauth_services)}')
        return v


class OAuthFlowResponse(BaseModel):
    """Schema for OAuth flow response"""
    authorization_url: str = Field(..., description="URL to redirect user for authorization")
    state: str = Field(..., description="OAuth state parameter for security")
    expires_in: int = Field(..., description="Authorization URL expiration in seconds")


class OAuthCallback(BaseModel):
    """Schema for OAuth callback handling"""
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="OAuth state parameter")
    service_type: str = Field(..., description="OAuth service type")
    service_name: str = Field(..., description="User-friendly name")


class CredentialTestRequest(BaseModel):
    """Schema for testing credential connectivity"""
    credential_id: UUID
    test_type: str = Field('basic', description="Type of test: basic, full, specific")
    test_parameters: Optional[Dict[str, Any]] = Field(None, description="Additional test parameters")
    
    @validator('test_type')
    def validate_test_type(cls, v):
        allowed_types = ['basic', 'full', 'specific', 'permissions']
        if v not in allowed_types:
            raise ValueError(f'Test type must be one of: {", ".join(allowed_types)}')
        return v


class CredentialTestResult(BaseModel):
    """Schema for credential test result"""
    credential_id: UUID
    test_type: str
    success: bool
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    test_details: Optional[Dict[str, Any]] = None
    permissions_verified: Optional[List[str]] = None
    tested_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class CredentialUsageLog(BaseModel):
    """Schema for credential usage logging"""
    credential_id: UUID
    agent_id: str
    execution_id: UUID
    action_performed: str
    success: bool
    error_message: Optional[str] = None
    used_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class CredentialSummary(BaseModel):
    """Schema for credential summary/overview"""
    total_credentials: int = 0
    active_credentials: int = 0
    expired_credentials: int = 0
    error_credentials: int = 0
    by_service_type: Dict[str, int] = Field(default_factory=dict)
    expiring_soon: List[UUID] = Field(default_factory=list, description="Credentials expiring in 7 days")
    
    class Config:
        json_encoders = {
            UUID: str
        }


class CredentialRotationRequest(BaseModel):
    """Schema for credential rotation request"""
    credential_id: UUID
    rotation_reason: str = Field(..., description="Reason for rotation")
    new_credentials: Dict[str, Any] = Field(..., description="New credential data")
    revoke_old: bool = Field(True, description="Whether to revoke old credentials")


class CredentialExportRequest(BaseModel):
    """Schema for credential export request (for backup/migration)"""
    credential_ids: Optional[List[UUID]] = Field(None, description="Specific credentials to export")
    service_types: Optional[List[str]] = Field(None, description="Export by service types")
    include_metadata_only: bool = Field(True, description="Export metadata only (no sensitive data)")
    export_format: str = Field('json', description="Export format")
    
    @validator('export_format')
    def validate_export_format(cls, v):
        allowed_formats = ['json', 'csv', 'yaml']
        if v not in allowed_formats:
            raise ValueError(f'Export format must be one of: {", ".join(allowed_formats)}')
        return v


class CredentialImportRequest(BaseModel):
    """Schema for credential import request"""
    credentials_data: List[Dict[str, Any]] = Field(..., description="Credentials to import")
    overwrite_existing: bool = Field(False, description="Whether to overwrite existing credentials")
    validate_before_import: bool = Field(True, description="Validate credentials before importing")


class ServiceCredentialRequirements(BaseModel):
    """Schema for service credential requirements"""
    service_type: str
    display_name: str
    description: str
    required_fields: List[Dict[str, Any]] = Field(..., description="Required credential fields")
    optional_fields: List[Dict[str, Any]] = Field(default_factory=list, description="Optional fields")
    oauth_supported: bool = False
    api_key_supported: bool = False
    setup_instructions: Optional[str] = None
    documentation_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class CredentialHealthCheck(BaseModel):
    """Schema for credential health monitoring"""
    credential_id: UUID
    service_type: str
    service_name: str
    status: str
    last_check: datetime
    next_check: Optional[datetime] = None
    check_interval_minutes: int = 60
    consecutive_failures: int = 0
    health_score: float = Field(..., description="Health score 0-100")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }