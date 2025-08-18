"""
Encryption Service for secure credential storage
Serviço de criptografia para armazenamento seguro de credenciais
"""
import base64
import json
import secrets
from typing import Dict, Any, Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

class EncryptionService:
    """Service for encrypting and decrypting sensitive credential data"""
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize encryption service with master key"""
        self.master_key = master_key or os.getenv('CREDENTIAL_MASTER_KEY')
        if not self.master_key:
            raise ValueError("Master key for credential encryption is required")
        
        # Cache for derived keys (in production, use Redis or similar)
        self._key_cache = {}
    
    def generate_encryption_key_id(self) -> str:
        """Generate unique encryption key ID"""
        return secrets.token_urlsafe(16)
    
    def _derive_key(self, key_id: str, salt: bytes) -> bytes:
        """Derive encryption key from master key and salt"""
        cache_key = f"{key_id}:{base64.b64encode(salt).decode()}"
        
        if cache_key in self._key_cache:
            return self._key_cache[cache_key]
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        # Combine master key with key_id for uniqueness
        password = f"{self.master_key}:{key_id}".encode()
        derived_key = kdf.derive(password)
        
        # Cache the derived key
        self._key_cache[cache_key] = derived_key
        
        return derived_key
    
    def encrypt_credential_data(self, data: Dict[str, Any], key_id: str) -> str:
        """Encrypt credential data"""
        try:
            # Convert data to JSON string
            json_data = json.dumps(data, sort_keys=True)
            
            # Generate random salt
            salt = secrets.token_bytes(16)
            
            # Derive encryption key
            derived_key = self._derive_key(key_id, salt)
            
            # Create Fernet cipher
            fernet_key = base64.urlsafe_b64encode(derived_key)
            fernet = Fernet(fernet_key)
            
            # Encrypt data
            encrypted_data = fernet.encrypt(json_data.encode())
            
            # Combine salt and encrypted data
            combined_data = salt + encrypted_data
            
            # Return base64 encoded result
            return base64.b64encode(combined_data).decode()
            
        except Exception as e:
            raise ValueError(f"Falha ao criptografar dados: {str(e)}")
    
    def decrypt_credential_data(self, encrypted_data: str, key_id: str) -> Dict[str, Any]:
        """Decrypt credential data"""
        try:
            # Decode base64
            combined_data = base64.b64decode(encrypted_data.encode())
            
            # Extract salt and encrypted data
            salt = combined_data[:16]
            encrypted_payload = combined_data[16:]
            
            # Derive encryption key
            derived_key = self._derive_key(key_id, salt)
            
            # Create Fernet cipher
            fernet_key = base64.urlsafe_b64encode(derived_key)
            fernet = Fernet(fernet_key)
            
            # Decrypt data
            decrypted_data = fernet.decrypt(encrypted_payload)
            
            # Parse JSON
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            raise ValueError(f"Falha ao descriptografar dados: {str(e)}")
    
    def rotate_encryption_key(self, old_encrypted_data: str, old_key_id: str, new_key_id: str) -> str:
        """Rotate encryption key for existing data"""
        try:
            # Decrypt with old key
            decrypted_data = self.decrypt_credential_data(old_encrypted_data, old_key_id)
            
            # Encrypt with new key
            return self.encrypt_credential_data(decrypted_data, new_key_id)
            
        except Exception as e:
            raise ValueError(f"Falha ao rotacionar chave: {str(e)}")
    
    def verify_data_integrity(self, encrypted_data: str, key_id: str) -> bool:
        """Verify that encrypted data can be decrypted (integrity check)"""
        try:
            self.decrypt_credential_data(encrypted_data, key_id)
            return True
        except:
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for comparison (one-way)"""
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()
    
    def mask_sensitive_value(self, value: str, visible_chars: int = 4) -> str:
        """Mask sensitive value for display"""
        if len(value) <= visible_chars * 2:
            return '*' * len(value)
        
        return value[:visible_chars] + '*' * (len(value) - visible_chars * 2) + value[-visible_chars:]

class CredentialEncryption:
    """Helper class for credential-specific encryption operations"""
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption_service = encryption_service
    
    def encrypt_oauth_credentials(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Encrypt OAuth credentials"""
        key_id = self.encryption_service.generate_encryption_key_id()
        
        credential_data = {
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        if access_token:
            credential_data['access_token'] = access_token
        
        if refresh_token:
            credential_data['refresh_token'] = refresh_token
        
        if additional_data:
            credential_data.update(additional_data)
        
        encrypted_data = self.encryption_service.encrypt_credential_data(credential_data, key_id)
        
        return encrypted_data, key_id
    
    def encrypt_api_key_credentials(
        self,
        api_key: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Encrypt API key credentials"""
        key_id = self.encryption_service.generate_encryption_key_id()
        
        credential_data = {
            'api_key': api_key
        }
        
        if additional_data:
            credential_data.update(additional_data)
        
        encrypted_data = self.encryption_service.encrypt_credential_data(credential_data, key_id)
        
        return encrypted_data, key_id
    
    def encrypt_basic_auth_credentials(
        self,
        username: str,
        password: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Encrypt basic auth credentials"""
        key_id = self.encryption_service.generate_encryption_key_id()
        
        credential_data = {
            'username': username,
            'password': password
        }
        
        if additional_data:
            credential_data.update(additional_data)
        
        encrypted_data = self.encryption_service.encrypt_credential_data(credential_data, key_id)
        
        return encrypted_data, key_id
    
    def decrypt_credentials(self, encrypted_data: str, key_id: str) -> Dict[str, Any]:
        """Decrypt any type of credentials"""
        return self.encryption_service.decrypt_credential_data(encrypted_data, key_id)
    
    def get_masked_credentials(self, encrypted_data: str, key_id: str) -> Dict[str, Any]:
        """Get credentials with sensitive values masked"""
        try:
            decrypted_data = self.decrypt_credentials(encrypted_data, key_id)
            masked_data = {}
            
            for key, value in decrypted_data.items():
                if isinstance(value, str) and key in ['client_secret', 'api_key', 'password', 'access_token', 'refresh_token']:
                    masked_data[key] = self.encryption_service.mask_sensitive_value(value)
                else:
                    masked_data[key] = value
            
            return masked_data
            
        except Exception as e:
            return {'error': f'Falha ao descriptografar: {str(e)}'}

def get_encryption_service() -> EncryptionService:
    """Get encryption service instance"""
    return EncryptionService()

def get_credential_encryption() -> CredentialEncryption:
    """Get credential encryption helper"""
    return CredentialEncryption(get_encryption_service())