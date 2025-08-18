"""
User Credentials Service
Handles secure credential management, OAuth flows, and validation
"""
import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
import httpx

from app.domain.credentials import (
    UserCredential, OAuthFlow, CredentialValidationResult,
    ProviderType, CredentialType, CredentialStatus,
    get_credential_metadata, CREDENTIAL_METADATA
)
from app.repositories.credentials_repository import CredentialsRepository
from app.services.encryption_service import EncryptionService, CredentialEncryption

class UserCredentialsService:
    """Service for managing user credentials securely"""
    
    def __init__(
        self,
        credentials_repository: Optional[CredentialsRepository] = None,
        encryption_service: Optional[EncryptionService] = None
    ):
        self.credentials_repo = credentials_repository or CredentialsRepository()
        self.encryption_service = encryption_service or EncryptionService()
        self.credential_encryption = CredentialEncryption(self.encryption_service)
        
        # HTTP client for validation requests
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def create_oauth_credential(
        self,
        user_id: UUID,
        provider: ProviderType,
        name: str,
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> UserCredential:
        """Create OAuth credential"""
        try:
            # Validate provider supports OAuth
            metadata = get_credential_metadata(provider)
            if metadata.credential_type != CredentialType.OAUTH2:
                raise ValueError(f"Provider {provider.value} não suporta OAuth2")
            
            # Check for duplicate name
            existing = await self.credentials_repo.find_credential_by_name(user_id, name)
            if existing:
                raise ValueError(f"Credencial com nome '{name}' já existe")
            
            # Encrypt credential data
            encrypted_data, key_id = self.credential_encryption.encrypt_oauth_credentials(
                client_id=client_id,
                client_secret=client_secret,
                additional_data=additional_data
            )
            
            # Create credential entity
            credential = UserCredential(
                user_id=user_id,
                provider=provider,
                credential_type=CredentialType.OAUTH2,
                name=name,
                encrypted_data=encrypted_data,
                encryption_key_id=key_id,
                scopes=scopes or [],
                status=CredentialStatus.PENDING_VALIDATION
            )
            
            # Save to database
            saved_credential = await self.credentials_repo.save_credential(credential)
            
            # Schedule validation
            asyncio.create_task(self._validate_credential_async(saved_credential))
            
            return saved_credential
            
        except Exception as e:
            raise ValueError(f"Falha ao criar credencial OAuth: {str(e)}")
    
    async def create_api_key_credential(
        self,
        user_id: UUID,
        provider: ProviderType,
        name: str,
        api_key: str,
        additional_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> UserCredential:
        """Create API key credential"""
        try:
            # Check for duplicate name
            existing = await self.credentials_repo.find_credential_by_name(user_id, name)
            if existing:
                raise ValueError(f"Credencial com nome '{name}' já existe")
            
            # Encrypt credential data
            encrypted_data, key_id = self.credential_encryption.encrypt_api_key_credentials(
                api_key=api_key,
                additional_data=additional_data
            )
            
            # Create credential entity
            credential = UserCredential(
                user_id=user_id,
                provider=provider,
                credential_type=CredentialType.API_KEY,
                name=name,
                encrypted_data=encrypted_data,
                encryption_key_id=key_id,
                expires_at=expires_at,
                status=CredentialStatus.PENDING_VALIDATION
            )
            
            # Save to database
            saved_credential = await self.credentials_repo.save_credential(credential)
            
            # Schedule validation
            asyncio.create_task(self._validate_credential_async(saved_credential))
            
            return saved_credential
            
        except Exception as e:
            raise ValueError(f"Falha ao criar credencial API key: {str(e)}")
    
    async def create_basic_auth_credential(
        self,
        user_id: UUID,
        provider: ProviderType,
        name: str,
        username: str,
        password: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> UserCredential:
        """Create basic auth credential"""
        try:
            # Check for duplicate name
            existing = await self.credentials_repo.find_credential_by_name(user_id, name)
            if existing:
                raise ValueError(f"Credencial com nome '{name}' já existe")
            
            # Encrypt credential data
            encrypted_data, key_id = self.credential_encryption.encrypt_basic_auth_credentials(
                username=username,
                password=password,
                additional_data=additional_data
            )
            
            # Create credential entity
            credential = UserCredential(
                user_id=user_id,
                provider=provider,
                credential_type=CredentialType.BASIC_AUTH,
                name=name,
                encrypted_data=encrypted_data,
                encryption_key_id=key_id,
                status=CredentialStatus.PENDING_VALIDATION
            )
            
            # Save to database
            saved_credential = await self.credentials_repo.save_credential(credential)
            
            # Schedule validation
            asyncio.create_task(self._validate_credential_async(saved_credential))
            
            return saved_credential
            
        except Exception as e:
            raise ValueError(f"Falha ao criar credencial básica: {str(e)}")
    
    async def get_user_credentials(
        self,
        user_id: UUID,
        provider: Optional[ProviderType] = None,
        status: Optional[CredentialStatus] = None,
        include_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user credentials (safe for display)"""
        credentials = await self.credentials_repo.find_credentials_by_user(
            user_id=user_id,
            provider=provider,
            status=status
        )
        
        result = []
        for credential in credentials:
            if include_sensitive:
                # Only for internal use - include masked sensitive data
                masked_data = self.credential_encryption.get_masked_credentials(
                    credential.encrypted_data,
                    credential.encryption_key_id
                )
                credential_dict = credential.get_display_info()
                credential_dict['masked_data'] = masked_data
                result.append(credential_dict)
            else:
                # Safe display info only
                result.append(credential.get_display_info())
        
        return result
    
    async def get_credential_by_id(
        self,
        credential_id: UUID,
        user_id: UUID,
        decrypt: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get credential by ID"""
        credential = await self.credentials_repo.find_credential_by_id(credential_id, user_id)
        if not credential:
            return None
        
        if decrypt:
            # Return decrypted data (for internal use only)
            decrypted_data = self.credential_encryption.decrypt_credentials(
                credential.encrypted_data,
                credential.encryption_key_id
            )
            credential_dict = credential.to_dict(include_sensitive=True)
            credential_dict['decrypted_data'] = decrypted_data
            return credential_dict
        else:
            # Return safe display info
            return credential.get_display_info()
    
    async def update_credential(
        self,
        credential_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        new_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> UserCredential:
        """Update credential"""
        credential = await self.credentials_repo.find_credential_by_id(credential_id, user_id)
        if not credential:
            raise ValueError("Credencial não encontrada")
        
        # Update name if provided
        if name and name != credential.name:
            # Check for duplicate name
            existing = await self.credentials_repo.find_credential_by_name(user_id, name)
            if existing and existing.id != credential_id:
                raise ValueError(f"Credencial com nome '{name}' já existe")
            credential.name = name
        
        # Update encrypted data if provided
        if new_data:
            # Decrypt current data
            current_data = self.credential_encryption.decrypt_credentials(
                credential.encrypted_data,
                credential.encryption_key_id
            )
            
            # Merge with new data
            current_data.update(new_data)
            
            # Re-encrypt with new key
            new_key_id = self.encryption_service.generate_encryption_key_id()
            new_encrypted_data = self.encryption_service.encrypt_credential_data(current_data, new_key_id)
            
            credential.encrypted_data = new_encrypted_data
            credential.encryption_key_id = new_key_id
            credential.status = CredentialStatus.PENDING_VALIDATION
        
        # Update expiration
        if expires_at is not None:
            credential.expires_at = expires_at
        
        # Save changes
        updated_credential = await self.credentials_repo.save_credential(credential)
        
        # Re-validate if data changed
        if new_data:
            asyncio.create_task(self._validate_credential_async(updated_credential))
        
        return updated_credential
    
    async def delete_credential(self, credential_id: UUID, user_id: UUID) -> bool:
        """Delete (revoke) credential"""
        credential = await self.credentials_repo.find_credential_by_id(credential_id, user_id)
        if not credential:
            return False
        
        # Mark as revoked
        credential.revoke("user_deleted")
        await self.credentials_repo.save_credential(credential)
        
        return True
    
    async def validate_credential(self, credential_id: UUID, user_id: UUID) -> CredentialValidationResult:
        """Manually validate credential"""
        credential = await self.credentials_repo.find_credential_by_id(credential_id, user_id)
        if not credential:
            raise ValueError("Credencial não encontrada")
        
        return await self._validate_credential_async(credential)
    
    async def _validate_credential_async(self, credential: UserCredential) -> CredentialValidationResult:
        """Validate credential asynchronously"""
        try:
            metadata = get_credential_metadata(credential.provider)
            
            if not metadata.validation_endpoint:
                # No validation endpoint - assume valid
                result = CredentialValidationResult(is_valid=True)
            else:
                # Decrypt credential data
                decrypted_data = self.credential_encryption.decrypt_credentials(
                    credential.encrypted_data,
                    credential.encryption_key_id
                )
                
                # Perform validation based on credential type
                if credential.credential_type == CredentialType.OAUTH2:
                    result = await self._validate_oauth_credential(metadata, decrypted_data)
                elif credential.credential_type == CredentialType.API_KEY:
                    result = await self._validate_api_key_credential(metadata, decrypted_data)
                else:
                    result = await self._validate_generic_credential(metadata, decrypted_data)
            
            # Update credential with validation result
            credential.mark_as_validated(result.is_valid, result.error_message)
            
            # Update expiration if provided
            if result.expires_at:
                credential.expires_at = result.expires_at
            
            # Update scopes if provided
            if result.scopes:
                credential.scopes = result.scopes
            
            # Save updated credential
            await self.credentials_repo.save_credential(credential)
            
            return result
            
        except Exception as e:
            error_message = f"Erro na validação: {str(e)}"
            result = CredentialValidationResult(is_valid=False, error_message=error_message)
            
            credential.mark_as_validated(False, error_message)
            await self.credentials_repo.save_credential(credential)
            
            return result
    
    async def _validate_oauth_credential(
        self,
        metadata,
        decrypted_data: Dict[str, Any]
    ) -> CredentialValidationResult:
        """Validate OAuth credential"""
        try:
            # For OAuth, we need an access token to validate
            access_token = decrypted_data.get('access_token')
            if not access_token:
                return CredentialValidationResult(
                    is_valid=False,
                    error_message="Access token não encontrado - execute fluxo OAuth primeiro"
                )
            
            # Make validation request
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Replace placeholders in validation endpoint
            validation_url = metadata.validation_endpoint
            for key, value in decrypted_data.items():
                validation_url = validation_url.replace(f'{{{key}}}', str(value))
            
            response = await self.http_client.get(validation_url, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract expiration if available
                expires_at = None
                if 'expires_in' in response_data:
                    expires_at = datetime.utcnow() + timedelta(seconds=response_data['expires_in'])
                elif 'exp' in response_data:
                    expires_at = datetime.fromtimestamp(response_data['exp'])
                
                # Extract scopes if available
                scopes = response_data.get('scope', '').split() if 'scope' in response_data else None
                
                return CredentialValidationResult(
                    is_valid=True,
                    expires_at=expires_at,
                    scopes=scopes,
                    metadata=response_data
                )
            else:
                return CredentialValidationResult(
                    is_valid=False,
                    error_message=f"Validação falhou: HTTP {response.status_code}"
                )
                
        except Exception as e:
            return CredentialValidationResult(
                is_valid=False,
                error_message=f"Erro na validação OAuth: {str(e)}"
            )
    
    async def _validate_api_key_credential(
        self,
        metadata,
        decrypted_data: Dict[str, Any]
    ) -> CredentialValidationResult:
        """Validate API key credential"""
        try:
            api_key = decrypted_data.get('api_key')
            if not api_key:
                return CredentialValidationResult(
                    is_valid=False,
                    error_message="API key não encontrada"
                )
            
            # Replace placeholders in validation endpoint
            validation_url = metadata.validation_endpoint
            for key, value in decrypted_data.items():
                validation_url = validation_url.replace(f'{{{key}}}', str(value))
            
            # Make validation request with API key
            headers = {'Authorization': f'Bearer {api_key}'}
            
            # Some APIs use different auth headers
            if 'whatsapp' in validation_url.lower():
                headers = {'Authorization': f'Bearer {api_key}'}
            elif 'telegram' in validation_url.lower():
                # Telegram uses bot token in URL
                validation_url = validation_url.replace('{bot_token}', api_key)
                headers = {}
            
            response = await self.http_client.get(validation_url, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                return CredentialValidationResult(
                    is_valid=True,
                    metadata=response_data
                )
            else:
                return CredentialValidationResult(
                    is_valid=False,
                    error_message=f"Validação falhou: HTTP {response.status_code}"
                )
                
        except Exception as e:
            return CredentialValidationResult(
                is_valid=False,
                error_message=f"Erro na validação API key: {str(e)}"
            )
    
    async def _validate_generic_credential(
        self,
        metadata,
        decrypted_data: Dict[str, Any]
    ) -> CredentialValidationResult:
        """Validate generic credential"""
        # For generic credentials, just check if required fields are present
        for field in metadata.required_fields:
            if field not in decrypted_data or not decrypted_data[field]:
                return CredentialValidationResult(
                    is_valid=False,
                    error_message=f"Campo obrigatório '{field}' não encontrado"
                )
        
        return CredentialValidationResult(is_valid=True)
    
    async def start_oauth_flow(
        self,
        user_id: UUID,
        provider: ProviderType,
        scopes: List[str],
        redirect_uri: str
    ) -> Tuple[str, str]:
        """Start OAuth flow and return authorization URL and state"""
        try:
            metadata = get_credential_metadata(provider)
            if metadata.credential_type != CredentialType.OAUTH2:
                raise ValueError(f"Provider {provider.value} não suporta OAuth2")
            
            # Generate state and code verifier for PKCE
            state = secrets.token_urlsafe(32)
            code_verifier = secrets.token_urlsafe(32)
            
            # Create OAuth flow record
            oauth_flow = OAuthFlow(
                user_id=user_id,
                provider=provider,
                state=state,
                scopes=scopes,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier
            )
            
            # Save OAuth flow
            await self.credentials_repo.save_oauth_flow(oauth_flow)
            
            # Generate authorization URL
            auth_url = self._build_oauth_authorization_url(provider, state, scopes, redirect_uri, oauth_flow)
            
            return auth_url, state
            
        except Exception as e:
            raise ValueError(f"Falha ao iniciar fluxo OAuth: {str(e)}")
    
    def _build_oauth_authorization_url(
        self,
        provider: ProviderType,
        state: str,
        scopes: List[str],
        redirect_uri: str,
        oauth_flow: OAuthFlow
    ) -> str:
        """Build OAuth authorization URL"""
        # This would be configured per provider
        base_urls = {
            ProviderType.GOOGLE: "https://accounts.google.com/o/oauth2/v2/auth",
            ProviderType.META: "https://www.facebook.com/v18.0/dialog/oauth",
            ProviderType.MICROSOFT: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        }
        
        base_url = base_urls.get(provider)
        if not base_url:
            raise ValueError(f"OAuth não configurado para provider {provider.value}")
        
        # Build query parameters
        params = {
            'response_type': 'code',
            'state': state,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(scopes)
        }
        
        # Add PKCE if supported
        if oauth_flow.code_verifier:
            params['code_challenge'] = oauth_flow.generate_code_challenge()
            params['code_challenge_method'] = 'S256'
        
        # Build URL
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    async def complete_oauth_flow(
        self,
        state: str,
        authorization_code: str,
        credential_name: str
    ) -> UserCredential:
        """Complete OAuth flow with authorization code"""
        try:
            # Find OAuth flow
            oauth_flow = await self.credentials_repo.find_oauth_flow_by_state(state)
            if not oauth_flow:
                raise ValueError("Fluxo OAuth não encontrado ou expirado")
            
            if oauth_flow.is_expired():
                raise ValueError("Fluxo OAuth expirado")
            
            # Exchange authorization code for tokens
            tokens = await self._exchange_oauth_code(oauth_flow, authorization_code)
            
            # Create credential with tokens
            credential = await self.create_oauth_credential(
                user_id=oauth_flow.user_id,
                provider=oauth_flow.provider,
                name=credential_name,
                client_id="",  # Would be provided during flow setup
                client_secret="",  # Would be provided during flow setup
                scopes=oauth_flow.scopes,
                additional_data={
                    'access_token': tokens['access_token'],
                    'refresh_token': tokens.get('refresh_token'),
                    'token_type': tokens.get('token_type', 'Bearer'),
                    'expires_in': tokens.get('expires_in')
                }
            )
            
            # Clean up OAuth flow
            await self.credentials_repo.delete_oauth_flow(oauth_flow.id)
            
            return credential
            
        except Exception as e:
            raise ValueError(f"Falha ao completar fluxo OAuth: {str(e)}")
    
    async def _exchange_oauth_code(self, oauth_flow: OAuthFlow, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        # This would be implemented per provider
        # For now, return mock tokens
        return {
            'access_token': secrets.token_urlsafe(32),
            'refresh_token': secrets.token_urlsafe(32),
            'token_type': 'Bearer',
            'expires_in': 3600
        }
    
    async def refresh_oauth_token(self, credential_id: UUID, user_id: UUID) -> UserCredential:
        """Refresh OAuth access token"""
        credential = await self.credentials_repo.find_credential_by_id(credential_id, user_id)
        if not credential:
            raise ValueError("Credencial não encontrada")
        
        if credential.credential_type != CredentialType.OAUTH2:
            raise ValueError("Credencial não é OAuth2")
        
        # Decrypt current data
        decrypted_data = self.credential_encryption.decrypt_credentials(
            credential.encrypted_data,
            credential.encryption_key_id
        )
        
        refresh_token = decrypted_data.get('refresh_token')
        if not refresh_token:
            raise ValueError("Refresh token não encontrado")
        
        # Refresh token (mock implementation)
        new_tokens = {
            'access_token': secrets.token_urlsafe(32),
            'refresh_token': refresh_token,  # May be rotated
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        # Update credential with new tokens
        decrypted_data.update(new_tokens)
        
        # Re-encrypt
        new_key_id = self.encryption_service.generate_encryption_key_id()
        new_encrypted_data = self.encryption_service.encrypt_credential_data(decrypted_data, new_key_id)
        
        credential.encrypted_data = new_encrypted_data
        credential.encryption_key_id = new_key_id
        credential.expires_at = datetime.utcnow() + timedelta(seconds=new_tokens['expires_in'])
        credential.status = CredentialStatus.ACTIVE
        
        return await self.credentials_repo.save_credential(credential)
    
    async def get_credential_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get credential statistics for user"""
        return await self.credentials_repo.get_credential_stats(user_id)
    
    async def check_expiring_credentials(self, user_id: UUID, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Check for credentials expiring soon"""
        expiring_credentials = await self.credentials_repo.find_expiring_credentials(days_ahead)
        
        # Filter by user and return display info
        user_expiring = [
            cred.get_display_info() 
            for cred in expiring_credentials 
            if cred.user_id == user_id
        ]
        
        return user_expiring
    
    async def validate_all_user_credentials(self, user_id: UUID) -> Dict[str, Any]:
        """Validate all user credentials"""
        credentials = await self.credentials_repo.find_credentials_by_user(user_id)
        
        results = {
            'total': len(credentials),
            'validated': 0,
            'failed': 0,
            'results': []
        }
        
        for credential in credentials:
            try:
                result = await self._validate_credential_async(credential)
                if result.is_valid:
                    results['validated'] += 1
                else:
                    results['failed'] += 1
                
                results['results'].append({
                    'credential_id': str(credential.id),
                    'name': credential.name,
                    'provider': credential.provider.value,
                    'is_valid': result.is_valid,
                    'error_message': result.error_message
                })
                
            except Exception as e:
                results['failed'] += 1
                results['results'].append({
                    'credential_id': str(credential.id),
                    'name': credential.name,
                    'provider': credential.provider.value,
                    'is_valid': False,
                    'error_message': str(e)
                })
        
        return results
    
    async def cleanup_expired_oauth_flows(self) -> int:
        """Clean up expired OAuth flows"""
        return await self.credentials_repo.cleanup_expired_oauth_flows()
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

def get_user_credentials_service() -> UserCredentialsService:
    """Get user credentials service instance"""
    return UserCredentialsService()