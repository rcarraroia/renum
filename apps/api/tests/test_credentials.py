"""
Tests for User Credentials Service and BYOC system
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timedelta

from app.services.user_credentials_service import UserCredentialsService
from app.services.encryption_service import EncryptionService, CredentialEncryption
from app.domain.credentials import (
    UserCredential, OAuthFlow, CredentialValidationResult,
    ProviderType, CredentialType, CredentialStatus
)

class TestEncryptionService:
    
    @pytest.fixture
    def encryption_service(self):
        """Encryption service with test master key"""
        return EncryptionService(master_key="test_master_key_for_testing_only")
    
    @pytest.fixture
    def credential_encryption(self, encryption_service):
        """Credential encryption helper"""
        return CredentialEncryption(encryption_service)
    
    def test_generate_encryption_key_id(self, encryption_service):
        """Test encryption key ID generation"""
        key_id = encryption_service.generate_encryption_key_id()
        
        assert isinstance(key_id, str)
        assert len(key_id) > 0
        
        # Should generate different IDs
        key_id2 = encryption_service.generate_encryption_key_id()
        assert key_id != key_id2
    
    def test_encrypt_decrypt_credential_data(self, encryption_service):
        """Test credential data encryption and decryption"""
        # Arrange
        test_data = {
            'api_key': 'test_api_key_123',
            'secret': 'test_secret_456',
            'additional_field': 'test_value'
        }
        key_id = encryption_service.generate_encryption_key_id()
        
        # Act - Encrypt
        encrypted_data = encryption_service.encrypt_credential_data(test_data, key_id)
        
        # Assert - Encrypted data should be different
        assert encrypted_data != str(test_data)
        assert isinstance(encrypted_data, str)
        
        # Act - Decrypt
        decrypted_data = encryption_service.decrypt_credential_data(encrypted_data, key_id)
        
        # Assert - Decrypted data should match original
        assert decrypted_data == test_data
    
    def test_encrypt_decrypt_with_wrong_key_fails(self, encryption_service):
        """Test that decryption fails with wrong key"""
        # Arrange
        test_data = {'api_key': 'test_key'}
        key_id = encryption_service.generate_encryption_key_id()
        wrong_key_id = encryption_service.generate_encryption_key_id()
        
        # Act
        encrypted_data = encryption_service.encrypt_credential_data(test_data, key_id)
        
        # Assert - Should fail with wrong key
        with pytest.raises(ValueError, match="Falha ao descriptografar"):
            encryption_service.decrypt_credential_data(encrypted_data, wrong_key_id)
    
    def test_verify_data_integrity(self, encryption_service):
        """Test data integrity verification"""
        # Arrange
        test_data = {'api_key': 'test_key'}
        key_id = encryption_service.generate_encryption_key_id()
        encrypted_data = encryption_service.encrypt_credential_data(test_data, key_id)
        
        # Act & Assert - Valid data
        assert encryption_service.verify_data_integrity(encrypted_data, key_id) == True
        
        # Act & Assert - Invalid data
        assert encryption_service.verify_data_integrity("invalid_data", key_id) == False
    
    def test_rotate_encryption_key(self, encryption_service):
        """Test encryption key rotation"""
        # Arrange
        test_data = {'api_key': 'test_key'}
        old_key_id = encryption_service.generate_encryption_key_id()
        new_key_id = encryption_service.generate_encryption_key_id()
        
        old_encrypted_data = encryption_service.encrypt_credential_data(test_data, old_key_id)
        
        # Act
        new_encrypted_data = encryption_service.rotate_encryption_key(
            old_encrypted_data, old_key_id, new_key_id
        )
        
        # Assert - Should be able to decrypt with new key
        decrypted_data = encryption_service.decrypt_credential_data(new_encrypted_data, new_key_id)
        assert decrypted_data == test_data
        
        # Assert - Old encrypted data should be different from new
        assert old_encrypted_data != new_encrypted_data
    
    def test_encrypt_oauth_credentials(self, credential_encryption):
        """Test OAuth credentials encryption"""
        # Act
        encrypted_data, key_id = credential_encryption.encrypt_oauth_credentials(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access_token",
            refresh_token="test_refresh_token"
        )
        
        # Assert
        assert isinstance(encrypted_data, str)
        assert isinstance(key_id, str)
        
        # Decrypt and verify
        decrypted = credential_encryption.decrypt_credentials(encrypted_data, key_id)
        assert decrypted['client_id'] == "test_client_id"
        assert decrypted['client_secret'] == "test_client_secret"
        assert decrypted['access_token'] == "test_access_token"
        assert decrypted['refresh_token'] == "test_refresh_token"
    
    def test_encrypt_api_key_credentials(self, credential_encryption):
        """Test API key credentials encryption"""
        # Act
        encrypted_data, key_id = credential_encryption.encrypt_api_key_credentials(
            api_key="test_api_key",
            additional_data={"endpoint": "https://api.example.com"}
        )
        
        # Assert
        assert isinstance(encrypted_data, str)
        assert isinstance(key_id, str)
        
        # Decrypt and verify
        decrypted = credential_encryption.decrypt_credentials(encrypted_data, key_id)
        assert decrypted['api_key'] == "test_api_key"
        assert decrypted['endpoint'] == "https://api.example.com"
    
    def test_get_masked_credentials(self, credential_encryption):
        """Test credential masking for display"""
        # Arrange
        encrypted_data, key_id = credential_encryption.encrypt_oauth_credentials(
            client_id="test_client_id",
            client_secret="very_long_secret_key_123456789",
            access_token="access_token_123456789"
        )
        
        # Act
        masked_data = credential_encryption.get_masked_credentials(encrypted_data, key_id)
        
        # Assert
        assert masked_data['client_id'] == "test_client_id"  # Not masked
        assert masked_data['client_secret'].startswith("very")
        assert masked_data['client_secret'].endswith("6789")
        assert "*" in masked_data['client_secret']
        assert masked_data['access_token'].startswith("acce")
        assert "*" in masked_data['access_token']

class TestUserCredentialsService:
    
    @pytest.fixture
    def mock_credentials_repo(self):
        """Mock credentials repository"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_encryption_service(self):
        """Mock encryption service"""
        mock_service = MagicMock()
        mock_service.generate_encryption_key_id.return_value = "test_key_id"
        mock_service.encrypt_credential_data.return_value = "encrypted_data"
        return mock_service
    
    @pytest.fixture
    def credentials_service(self, mock_credentials_repo, mock_encryption_service):
        """Credentials service with mocked dependencies"""
        service = UserCredentialsService(
            credentials_repository=mock_credentials_repo,
            encryption_service=mock_encryption_service
        )
        # Mock the credential encryption helper
        service.credential_encryption = MagicMock()
        service.credential_encryption.encrypt_oauth_credentials.return_value = ("encrypted_data", "key_id")
        service.credential_encryption.encrypt_api_key_credentials.return_value = ("encrypted_data", "key_id")
        service.credential_encryption.encrypt_basic_auth_credentials.return_value = ("encrypted_data", "key_id")
        return service
    
    @pytest.mark.asyncio
    async def test_create_oauth_credential_success(
        self, 
        credentials_service, 
        mock_credentials_repo
    ):
        """Test successful OAuth credential creation"""
        # Arrange
        user_id = uuid4()
        provider = ProviderType.GOOGLE
        name = "Test Google Account"
        client_id = "test_client_id"
        client_secret = "test_client_secret"
        scopes = ["email", "profile"]
        
        # Mock repository responses
        mock_credentials_repo.find_credential_by_name.return_value = None  # No duplicate
        mock_credentials_repo.save_credential.return_value = MagicMock()
        
        # Act
        result = await credentials_service.create_oauth_credential(
            user_id=user_id,
            provider=provider,
            name=name,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes
        )
        
        # Assert
        assert result is not None
        mock_credentials_repo.find_credential_by_name.assert_called_once_with(user_id, name)
        mock_credentials_repo.save_credential.assert_called_once()
        credentials_service.credential_encryption.encrypt_oauth_credentials.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_oauth_credential_duplicate_name_fails(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test OAuth credential creation fails with duplicate name"""
        # Arrange
        user_id = uuid4()
        name = "Duplicate Name"
        
        # Mock existing credential
        existing_credential = MagicMock()
        mock_credentials_repo.find_credential_by_name.return_value = existing_credential
        
        # Act & Assert
        with pytest.raises(ValueError, match="já existe"):
            await credentials_service.create_oauth_credential(
                user_id=user_id,
                provider=ProviderType.GOOGLE,
                name=name,
                client_id="test_id",
                client_secret="test_secret"
            )
    
    @pytest.mark.asyncio
    async def test_create_api_key_credential_success(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test successful API key credential creation"""
        # Arrange
        user_id = uuid4()
        provider = ProviderType.WHATSAPP_BUSINESS
        name = "Test WhatsApp"
        api_key = "test_api_key"
        additional_data = {"phone_number_id": "123456"}
        
        # Mock repository responses
        mock_credentials_repo.find_credential_by_name.return_value = None
        mock_credentials_repo.save_credential.return_value = MagicMock()
        
        # Act
        result = await credentials_service.create_api_key_credential(
            user_id=user_id,
            provider=provider,
            name=name,
            api_key=api_key,
            additional_data=additional_data
        )
        
        # Assert
        assert result is not None
        mock_credentials_repo.save_credential.assert_called_once()
        credentials_service.credential_encryption.encrypt_api_key_credentials.assert_called_once_with(
            api_key=api_key,
            additional_data=additional_data
        )
    
    @pytest.mark.asyncio
    async def test_get_user_credentials(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test getting user credentials"""
        # Arrange
        user_id = uuid4()
        
        # Mock credentials
        mock_credential = MagicMock()
        mock_credential.get_display_info.return_value = {
            'id': str(uuid4()),
            'name': 'Test Credential',
            'provider': 'google',
            'status': 'active'
        }
        mock_credentials_repo.find_credentials_by_user.return_value = [mock_credential]
        
        # Act
        result = await credentials_service.get_user_credentials(user_id)
        
        # Assert
        assert len(result) == 1
        assert result[0]['name'] == 'Test Credential'
        mock_credentials_repo.find_credentials_by_user.assert_called_once_with(
            user_id=user_id,
            provider=None,
            status=None
        )
    
    @pytest.mark.asyncio
    async def test_delete_credential_success(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test successful credential deletion"""
        # Arrange
        credential_id = uuid4()
        user_id = uuid4()
        
        # Mock credential
        mock_credential = MagicMock()
        mock_credential.revoke = MagicMock()
        mock_credentials_repo.find_credential_by_id.return_value = mock_credential
        mock_credentials_repo.save_credential.return_value = mock_credential
        
        # Act
        result = await credentials_service.delete_credential(credential_id, user_id)
        
        # Assert
        assert result == True
        mock_credential.revoke.assert_called_once_with("user_deleted")
        mock_credentials_repo.save_credential.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_credential_not_found(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test credential deletion when credential not found"""
        # Arrange
        credential_id = uuid4()
        user_id = uuid4()
        mock_credentials_repo.find_credential_by_id.return_value = None
        
        # Act
        result = await credentials_service.delete_credential(credential_id, user_id)
        
        # Assert
        assert result == False
    
    @pytest.mark.asyncio
    async def test_start_oauth_flow(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test starting OAuth flow"""
        # Arrange
        user_id = uuid4()
        provider = ProviderType.GOOGLE
        scopes = ["email", "profile"]
        redirect_uri = "https://example.com/callback"
        
        # Mock OAuth flow save
        mock_credentials_repo.save_oauth_flow.return_value = MagicMock()
        
        # Act
        auth_url, state = await credentials_service.start_oauth_flow(
            user_id=user_id,
            provider=provider,
            scopes=scopes,
            redirect_uri=redirect_uri
        )
        
        # Assert
        assert isinstance(auth_url, str)
        assert isinstance(state, str)
        assert len(state) > 0
        mock_credentials_repo.save_oauth_flow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_credential_success(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test successful credential validation"""
        # Arrange
        credential_id = uuid4()
        user_id = uuid4()
        
        # Mock credential
        mock_credential = MagicMock()
        mock_credential.provider = ProviderType.GOOGLE
        mock_credential.credential_type = CredentialType.OAUTH2
        mock_credential.mark_as_validated = MagicMock()
        mock_credentials_repo.find_credential_by_id.return_value = mock_credential
        mock_credentials_repo.save_credential.return_value = mock_credential
        
        # Mock credential encryption
        credentials_service.credential_encryption.decrypt_credentials.return_value = {
            'access_token': 'test_token'
        }
        
        # Mock HTTP response
        with patch.object(credentials_service, '_validate_oauth_credential') as mock_validate:
            mock_validate.return_value = CredentialValidationResult(is_valid=True)
            
            # Act
            result = await credentials_service.validate_credential(credential_id, user_id)
            
            # Assert
            assert result.is_valid == True
            mock_credential.mark_as_validated.assert_called_once_with(True, None)
    
    @pytest.mark.asyncio
    async def test_get_credential_stats(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test getting credential statistics"""
        # Arrange
        user_id = uuid4()
        mock_stats = {
            'total_credentials': 5,
            'active_credentials': 4,
            'expired_credentials': 1,
            'invalid_credentials': 0,
            'by_provider': {'google': 2, 'whatsapp_business': 3}
        }
        mock_credentials_repo.get_credential_stats.return_value = mock_stats
        
        # Act
        result = await credentials_service.get_credential_stats(user_id)
        
        # Assert
        assert result == mock_stats
        mock_credentials_repo.get_credential_stats.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_check_expiring_credentials(
        self,
        credentials_service,
        mock_credentials_repo
    ):
        """Test checking for expiring credentials"""
        # Arrange
        user_id = uuid4()
        days_ahead = 7
        
        # Mock expiring credential
        mock_credential = MagicMock()
        mock_credential.user_id = user_id
        mock_credential.get_display_info.return_value = {
            'id': str(uuid4()),
            'name': 'Expiring Credential',
            'expires_at': (datetime.utcnow() + timedelta(days=3)).isoformat()
        }
        mock_credentials_repo.find_expiring_credentials.return_value = [mock_credential]
        
        # Act
        result = await credentials_service.check_expiring_credentials(user_id, days_ahead)
        
        # Assert
        assert len(result) == 1
        assert result[0]['name'] == 'Expiring Credential'
        mock_credentials_repo.find_expiring_credentials.assert_called_once_with(days_ahead)

class TestCredentialDomain:
    
    def test_user_credential_creation_success(self):
        """Test successful user credential creation"""
        # Arrange
        user_id = uuid4()
        provider = ProviderType.GOOGLE
        credential_type = CredentialType.OAUTH2
        name = "Test Credential"
        encrypted_data = "encrypted_test_data"
        encryption_key_id = "test_key_id"
        
        # Act
        credential = UserCredential(
            user_id=user_id,
            provider=provider,
            credential_type=credential_type,
            name=name,
            encrypted_data=encrypted_data,
            encryption_key_id=encryption_key_id
        )
        
        # Assert
        assert credential.user_id == user_id
        assert credential.provider == provider
        assert credential.credential_type == credential_type
        assert credential.name == name
        assert credential.status == CredentialStatus.PENDING_VALIDATION
        assert credential.fingerprint is not None
        assert len(credential.fingerprint) == 16
    
    def test_user_credential_validation_empty_name(self):
        """Test user credential validation with empty name"""
        # Arrange
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Nome da credencial é obrigatório"):
            UserCredential(
                user_id=user_id,
                provider=ProviderType.GOOGLE,
                credential_type=CredentialType.OAUTH2,
                name="   ",  # Empty after strip
                encrypted_data="test_data",
                encryption_key_id="test_key"
            )
    
    def test_user_credential_validation_missing_encrypted_data(self):
        """Test user credential validation with missing encrypted data"""
        # Arrange
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Dados criptografados são obrigatórios"):
            UserCredential(
                user_id=user_id,
                provider=ProviderType.GOOGLE,
                credential_type=CredentialType.OAUTH2,
                name="Test Credential",
                encrypted_data="",  # Empty
                encryption_key_id="test_key"
            )
    
    def test_user_credential_is_expired(self):
        """Test credential expiration check"""
        # Arrange
        user_id = uuid4()
        past_date = datetime.utcnow() - timedelta(days=1)
        future_date = datetime.utcnow() + timedelta(days=1)
        
        # Test expired credential
        expired_credential = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Expired Credential",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            expires_at=past_date
        )
        
        # Test non-expired credential
        valid_credential = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Valid Credential",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            expires_at=future_date
        )
        
        # Test credential without expiration
        no_expiry_credential = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="No Expiry Credential",
            encrypted_data="test_data",
            encryption_key_id="test_key"
        )
        
        # Assert
        assert expired_credential.is_expired() == True
        assert valid_credential.is_expired() == False
        assert no_expiry_credential.is_expired() == False
    
    def test_user_credential_expires_soon(self):
        """Test credential expiration warning"""
        # Arrange
        user_id = uuid4()
        soon_date = datetime.utcnow() + timedelta(days=3)  # Expires in 3 days
        far_date = datetime.utcnow() + timedelta(days=30)  # Expires in 30 days
        
        # Test credential expiring soon
        soon_credential = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Soon Credential",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            expires_at=soon_date
        )
        
        # Test credential not expiring soon
        far_credential = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Far Credential",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            expires_at=far_date
        )
        
        # Assert
        assert soon_credential.expires_soon(warning_days=7) == True
        assert far_credential.expires_soon(warning_days=7) == False
    
    def test_user_credential_needs_validation(self):
        """Test credential validation requirement check"""
        # Arrange
        user_id = uuid4()
        old_validation = datetime.utcnow() - timedelta(hours=25)  # 25 hours ago
        recent_validation = datetime.utcnow() - timedelta(hours=1)  # 1 hour ago
        
        # Test credential needing validation (never validated)
        never_validated = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Never Validated",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            status=CredentialStatus.PENDING_VALIDATION
        )
        
        # Test credential needing validation (old validation)
        old_validated = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Old Validated",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            status=CredentialStatus.ACTIVE,
            last_validated_at=old_validation
        )
        
        # Test credential not needing validation (recent validation)
        recent_validated = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Recent Validated",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            status=CredentialStatus.ACTIVE,
            last_validated_at=recent_validation
        )
        
        # Assert
        assert never_validated.needs_validation(max_age_hours=24) == True
        assert old_validated.needs_validation(max_age_hours=24) == True
        assert recent_validated.needs_validation(max_age_hours=24) == False
    
    def test_user_credential_mark_as_validated(self):
        """Test marking credential as validated"""
        # Arrange
        user_id = uuid4()
        credential = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Test Credential",
            encrypted_data="test_data",
            encryption_key_id="test_key"
        )
        
        # Act - Mark as successfully validated
        credential.mark_as_validated(True)
        
        # Assert
        assert credential.status == CredentialStatus.ACTIVE
        assert credential.last_validated_at is not None
        assert credential.validation_error is None
        
        # Act - Mark as failed validation
        error_message = "Invalid token"
        credential.mark_as_validated(False, error_message)
        
        # Assert
        assert credential.status == CredentialStatus.INVALID
        assert credential.validation_error == error_message
    
    def test_user_credential_revoke(self):
        """Test credential revocation"""
        # Arrange
        user_id = uuid4()
        credential = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Test Credential",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            status=CredentialStatus.ACTIVE
        )
        
        # Act
        reason = "User requested revocation"
        credential.revoke(reason)
        
        # Assert
        assert credential.status == CredentialStatus.REVOKED
        assert credential.metadata['revocation_reason'] == reason
        assert 'revoked_at' in credential.metadata
    
    def test_user_credential_get_display_info(self):
        """Test getting safe display information"""
        # Arrange
        user_id = uuid4()
        credential = UserCredential(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            credential_type=CredentialType.OAUTH2,
            name="Test Credential",
            encrypted_data="test_data",
            encryption_key_id="test_key",
            scopes=["email", "profile"]
        )
        
        # Act
        display_info = credential.get_display_info()
        
        # Assert
        assert 'id' in display_info
        assert display_info['name'] == "Test Credential"
        assert display_info['provider'] == "google"
        assert display_info['credential_type'] == "oauth2"
        assert display_info['scopes'] == ["email", "profile"]
        assert 'fingerprint' in display_info
        
        # Ensure sensitive data is not included
        assert 'encrypted_data' not in display_info
        assert 'encryption_key_id' not in display_info

class TestOAuthFlow:
    
    def test_oauth_flow_creation(self):
        """Test OAuth flow creation"""
        # Arrange
        user_id = uuid4()
        provider = ProviderType.GOOGLE
        state = "test_state"
        scopes = ["email", "profile"]
        redirect_uri = "https://example.com/callback"
        
        # Act
        oauth_flow = OAuthFlow(
            user_id=user_id,
            provider=provider,
            state=state,
            scopes=scopes,
            redirect_uri=redirect_uri
        )
        
        # Assert
        assert oauth_flow.user_id == user_id
        assert oauth_flow.provider == provider
        assert oauth_flow.state == state
        assert oauth_flow.scopes == scopes
        assert oauth_flow.redirect_uri == redirect_uri
        assert oauth_flow.expires_at > datetime.utcnow()
    
    def test_oauth_flow_is_expired(self):
        """Test OAuth flow expiration check"""
        # Arrange
        user_id = uuid4()
        past_date = datetime.utcnow() - timedelta(minutes=1)
        future_date = datetime.utcnow() + timedelta(minutes=10)
        
        # Test expired flow
        expired_flow = OAuthFlow(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            state="test_state",
            scopes=["email"],
            redirect_uri="https://example.com/callback",
            expires_at=past_date
        )
        
        # Test valid flow
        valid_flow = OAuthFlow(
            user_id=user_id,
            provider=ProviderType.GOOGLE,
            state="test_state",
            scopes=["email"],
            redirect_uri="https://example.com/callback",
            expires_at=future_date
        )
        
        # Assert
        assert expired_flow.is_expired() == True
        assert valid_flow.is_expired() == False
    
    def test_oauth_flow_generate_code_challenge(self):
        """Test PKCE code challenge generation"""
        # Arrange
        oauth_flow = OAuthFlow(
            user_id=uuid4(),
            provider=ProviderType.GOOGLE,
            state="test_state",
            scopes=["email"],
            redirect_uri="https://example.com/callback"
        )
        
        # Act
        code_challenge = oauth_flow.generate_code_challenge()
        
        # Assert
        assert isinstance(code_challenge, str)
        assert len(code_challenge) > 0
        assert oauth_flow.code_verifier is not None
        
        # Should generate same challenge for same verifier
        code_challenge2 = oauth_flow.generate_code_challenge()
        assert code_challenge == code_challenge2