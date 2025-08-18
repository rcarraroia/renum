"""
Domain models for user credentials management
Entidades de negócio para gerenciamento seguro de credenciais de usuário
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from enum import Enum
import hashlib
import secrets

class CredentialType(Enum):
    """Types of credentials supported"""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    JWT_TOKEN = "jwt_token"
    CUSTOM = "custom"

class CredentialStatus(Enum):
    """Status of credentials"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"
    PENDING_VALIDATION = "pending_validation"

class ProviderType(Enum):
    """Supported credential providers"""
    GOOGLE = "google"
    META = "meta"
    MICROSOFT = "microsoft"
    WHATSAPP_BUSINESS = "whatsapp_business"
    TELEGRAM = "telegram"
    ZAPIER = "zapier"
    N8N = "n8n"
    MAKE = "make"
    GMAIL = "gmail"
    SUPABASE = "supabase"
    CUSTOM_API = "custom_api"

class OAuthScope:
    """OAuth scope definition"""
    def __init__(self, scope: str, description: str, required: bool = False):
        self.scope = scope
        self.description = description
        self.required = required
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'scope': self.scope,
            'description': self.description,
            'required': self.required
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OAuthScope':
        return cls(
            scope=data['scope'],
            description=data['description'],
            required=data.get('required', False)
        )

class CredentialMetadata:
    """Metadata for credential configuration"""
    def __init__(
        self,
        provider: ProviderType,
        credential_type: CredentialType,
        required_fields: List[str],
        optional_fields: Optional[List[str]] = None,
        oauth_scopes: Optional[List[OAuthScope]] = None,
        validation_endpoint: Optional[str] = None,
        refresh_endpoint: Optional[str] = None,
        expiry_warning_days: int = 7
    ):
        self.provider = provider
        self.credential_type = credential_type
        self.required_fields = required_fields
        self.optional_fields = optional_fields or []
        self.oauth_scopes = oauth_scopes or []
        self.validation_endpoint = validation_endpoint
        self.refresh_endpoint = refresh_endpoint
        self.expiry_warning_days = expiry_warning_days
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'provider': self.provider.value,
            'credential_type': self.credential_type.value,
            'required_fields': self.required_fields,
            'optional_fields': self.optional_fields,
            'oauth_scopes': [scope.to_dict() for scope in self.oauth_scopes],
            'validation_endpoint': self.validation_endpoint,
            'refresh_endpoint': self.refresh_endpoint,
            'expiry_warning_days': self.expiry_warning_days
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CredentialMetadata':
        oauth_scopes = []
        for scope_data in data.get('oauth_scopes', []):
            oauth_scopes.append(OAuthScope.from_dict(scope_data))
        
        return cls(
            provider=ProviderType(data['provider']),
            credential_type=CredentialType(data['credential_type']),
            required_fields=data['required_fields'],
            optional_fields=data.get('optional_fields', []),
            oauth_scopes=oauth_scopes,
            validation_endpoint=data.get('validation_endpoint'),
            refresh_endpoint=data.get('refresh_endpoint'),
            expiry_warning_days=data.get('expiry_warning_days', 7)
        )

class UserCredential:
    """User credential entity with encryption support"""
    
    def __init__(
        self,
        user_id: UUID,
        provider: ProviderType,
        credential_type: CredentialType,
        name: str,
        encrypted_data: str,
        encryption_key_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        scopes: Optional[List[str]] = None,
        status: CredentialStatus = CredentialStatus.PENDING_VALIDATION,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_validated_at: Optional[datetime] = None,
        validation_error: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.user_id = user_id
        self.provider = provider
        self.credential_type = credential_type
        self.name = name
        self.encrypted_data = encrypted_data
        self.encryption_key_id = encryption_key_id
        self.metadata = metadata or {}
        self.expires_at = expires_at
        self.scopes = scopes or []
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_validated_at = last_validated_at
        self.validation_error = validation_error
        
        # Generate fingerprint for integrity checking
        self.fingerprint = self._generate_fingerprint()
        
        # Validate on creation
        self._validate()
    
    def _validate(self):
        """Validate credential entity"""
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Nome da credencial é obrigatório")
        
        if not self.encrypted_data:
            raise ValueError("Dados criptografados são obrigatórios")
        
        if not self.encryption_key_id:
            raise ValueError("ID da chave de criptografia é obrigatório")
        
        # Validate name uniqueness per user (would be enforced at service level)
        if len(self.name) > 100:
            raise ValueError("Nome da credencial deve ter no máximo 100 caracteres")
    
    def _generate_fingerprint(self) -> str:
        """Generate fingerprint for integrity verification"""
        data = f"{self.user_id}:{self.provider.value}:{self.credential_type.value}:{self.encrypted_data}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def is_expired(self) -> bool:
        """Check if credential is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def expires_soon(self, warning_days: int = 7) -> bool:
        """Check if credential expires soon"""
        if not self.expires_at:
            return False
        warning_date = datetime.utcnow() + timedelta(days=warning_days)
        return self.expires_at <= warning_date
    
    def needs_validation(self, max_age_hours: int = 24) -> bool:
        """Check if credential needs validation"""
        if self.status == CredentialStatus.PENDING_VALIDATION:
            return True
        
        if not self.last_validated_at:
            return True
        
        max_age = timedelta(hours=max_age_hours)
        return datetime.utcnow() - self.last_validated_at > max_age
    
    def mark_as_validated(self, success: bool, error_message: Optional[str] = None):
        """Mark credential as validated"""
        self.last_validated_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if success:
            self.status = CredentialStatus.ACTIVE
            self.validation_error = None
        else:
            self.status = CredentialStatus.INVALID
            self.validation_error = error_message
    
    def mark_as_expired(self):
        """Mark credential as expired"""
        self.status = CredentialStatus.EXPIRED
        self.updated_at = datetime.utcnow()
    
    def revoke(self, reason: Optional[str] = None):
        """Revoke credential"""
        self.status = CredentialStatus.REVOKED
        self.updated_at = datetime.utcnow()
        if reason:
            self.metadata['revocation_reason'] = reason
            self.metadata['revoked_at'] = datetime.utcnow().isoformat()
    
    def update_metadata(self, new_metadata: Dict[str, Any]):
        """Update credential metadata"""
        self.metadata.update(new_metadata)
        self.updated_at = datetime.utcnow()
    
    def get_display_info(self) -> Dict[str, Any]:
        """Get safe display information (no sensitive data)"""
        return {
            'id': str(self.id),
            'name': self.name,
            'provider': self.provider.value,
            'credential_type': self.credential_type.value,
            'status': self.status.value,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'expires_soon': self.expires_soon(),
            'is_expired': self.is_expired(),
            'needs_validation': self.needs_validation(),
            'scopes': self.scopes,
            'created_at': self.created_at.isoformat(),
            'last_validated_at': self.last_validated_at.isoformat() if self.last_validated_at else None,
            'fingerprint': self.fingerprint
        }
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'provider': self.provider.value,
            'credential_type': self.credential_type.value,
            'name': self.name,
            'metadata': self.metadata,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'scopes': self.scopes,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_validated_at': self.last_validated_at.isoformat() if self.last_validated_at else None,
            'validation_error': self.validation_error,
            'fingerprint': self.fingerprint
        }
        
        if include_sensitive:
            data.update({
                'encrypted_data': self.encrypted_data,
                'encryption_key_id': self.encryption_key_id
            })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserCredential':
        """Create from dictionary"""
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        
        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        
        last_validated_at = None
        if data.get('last_validated_at'):
            last_validated_at = datetime.fromisoformat(data['last_validated_at'].replace('Z', '+00:00'))
        
        return cls(
            id=UUID(data['id']),
            user_id=UUID(data['user_id']),
            provider=ProviderType(data['provider']),
            credential_type=CredentialType(data['credential_type']),
            name=data['name'],
            encrypted_data=data['encrypted_data'],
            encryption_key_id=data['encryption_key_id'],
            metadata=data.get('metadata', {}),
            expires_at=expires_at,
            scopes=data.get('scopes', []),
            status=CredentialStatus(data.get('status', 'pending_validation')),
            created_at=created_at,
            updated_at=updated_at,
            last_validated_at=last_validated_at,
            validation_error=data.get('validation_error')
        )

class OAuthFlow:
    """OAuth flow management"""
    
    def __init__(
        self,
        user_id: UUID,
        provider: ProviderType,
        state: str,
        scopes: List[str],
        redirect_uri: str,
        code_verifier: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.user_id = user_id
        self.provider = provider
        self.state = state
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        self.code_verifier = code_verifier
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(minutes=10))
        self.created_at = created_at or datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if OAuth flow is expired"""
        return datetime.utcnow() > self.expires_at
    
    def generate_code_challenge(self) -> str:
        """Generate PKCE code challenge"""
        if not self.code_verifier:
            self.code_verifier = secrets.token_urlsafe(32)
        
        challenge = hashlib.sha256(self.code_verifier.encode()).digest()
        return secrets.token_urlsafe(challenge)[:43]  # Base64 URL-safe without padding
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'provider': self.provider.value,
            'state': self.state,
            'scopes': self.scopes,
            'redirect_uri': self.redirect_uri,
            'code_verifier': self.code_verifier,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OAuthFlow':
        """Create from dictionary"""
        expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        
        return cls(
            id=UUID(data['id']),
            user_id=UUID(data['user_id']),
            provider=ProviderType(data['provider']),
            state=data['state'],
            scopes=data['scopes'],
            redirect_uri=data['redirect_uri'],
            code_verifier=data.get('code_verifier'),
            expires_at=expires_at,
            created_at=created_at
        )

class CredentialValidationResult:
    """Result of credential validation"""
    
    def __init__(
        self,
        is_valid: bool,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        scopes: Optional[List[str]] = None
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.metadata = metadata or {}
        self.expires_at = expires_at
        self.scopes = scopes or []
        self.validated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'scopes': self.scopes,
            'validated_at': self.validated_at.isoformat()
        }

# Predefined credential metadata for common providers
CREDENTIAL_METADATA = {
    ProviderType.GOOGLE: CredentialMetadata(
        provider=ProviderType.GOOGLE,
        credential_type=CredentialType.OAUTH2,
        required_fields=['client_id', 'client_secret'],
        oauth_scopes=[
            OAuthScope('https://www.googleapis.com/auth/userinfo.email', 'Access email address', True),
            OAuthScope('https://www.googleapis.com/auth/userinfo.profile', 'Access profile information', True),
            OAuthScope('https://www.googleapis.com/auth/gmail.send', 'Send emails via Gmail', False),
            OAuthScope('https://www.googleapis.com/auth/gmail.readonly', 'Read Gmail messages', False)
        ],
        validation_endpoint='https://www.googleapis.com/oauth2/v1/tokeninfo',
        refresh_endpoint='https://oauth2.googleapis.com/token'
    ),
    
    ProviderType.META: CredentialMetadata(
        provider=ProviderType.META,
        credential_type=CredentialType.OAUTH2,
        required_fields=['app_id', 'app_secret'],
        oauth_scopes=[
            OAuthScope('whatsapp_business_management', 'Manage WhatsApp Business accounts', True),
            OAuthScope('whatsapp_business_messaging', 'Send WhatsApp messages', True)
        ],
        validation_endpoint='https://graph.facebook.com/me',
        refresh_endpoint='https://graph.facebook.com/oauth/access_token'
    ),
    
    ProviderType.WHATSAPP_BUSINESS: CredentialMetadata(
        provider=ProviderType.WHATSAPP_BUSINESS,
        credential_type=CredentialType.API_KEY,
        required_fields=['access_token', 'phone_number_id'],
        optional_fields=['business_account_id', 'webhook_verify_token'],
        validation_endpoint='https://graph.facebook.com/v18.0/{phone_number_id}'
    ),
    
    ProviderType.TELEGRAM: CredentialMetadata(
        provider=ProviderType.TELEGRAM,
        credential_type=CredentialType.API_KEY,
        required_fields=['bot_token'],
        validation_endpoint='https://api.telegram.org/bot{bot_token}/getMe'
    ),
    
    ProviderType.SUPABASE: CredentialMetadata(
        provider=ProviderType.SUPABASE,
        credential_type=CredentialType.API_KEY,
        required_fields=['url', 'anon_key'],
        optional_fields=['service_role_key'],
        validation_endpoint='{url}/rest/v1/'
    ),
    
    ProviderType.CUSTOM_API: CredentialMetadata(
        provider=ProviderType.CUSTOM_API,
        credential_type=CredentialType.CUSTOM,
        required_fields=['base_url'],
        optional_fields=['api_key', 'username', 'password', 'headers']
    )
}

def get_credential_metadata(provider: ProviderType) -> CredentialMetadata:
    """Get credential metadata for a provider"""
    return CREDENTIAL_METADATA.get(provider, CredentialMetadata(
        provider=provider,
        credential_type=CredentialType.CUSTOM,
        required_fields=['api_key']
    ))