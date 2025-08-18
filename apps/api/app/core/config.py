"""
Configurações centrais da aplicação.
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    # API Configuration
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    
    # Supabase Configuration
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    
    # Suna Backend Configuration
    SUNA_API_URL: str = "http://157.180.39.41:8000/api"
    SUNA_WS_URL: str = "ws://157.180.39.41:8000/ws"
    SUNA_API_KEY: str = ""
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str = ""
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    DEFAULT_RATE_LIMIT_PER_MINUTE: int = 60
    DEFAULT_RATE_LIMIT_PER_HOUR: int = 1000
    PREMIUM_RATE_LIMIT_PER_MINUTE: int = 300
    PREMIUM_RATE_LIMIT_PER_HOUR: int = 5000
    
    # Security Configuration
    SECURITY_HEADERS_ENABLED: bool = True
    AUDIT_LOGGING_ENABLED: bool = True
    REQUEST_VALIDATION_ENABLED: bool = True
    
    # Admin IP Whitelist (comma-separated)
    ADMIN_IP_WHITELIST: str = "127.0.0.1,::1,localhost"
    
    # Encryption Configuration
    ENCRYPTION_KEY: str = ""  # Should be 32 bytes base64 encoded
    
    # File Upload Limits
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".json", ".csv", ".txt", ".pdf"]
    
    # Sandbox Configuration
    SANDBOX_ENABLED: bool = True
    SANDBOX_MAX_CONCURRENT: int = 10
    SANDBOX_DEFAULT_TIMEOUT: int = 300
    SANDBOX_AUTO_CLEANUP: bool = True
    SANDBOX_DOCKER_HOST: str = "unix://var/run/docker.sock"
    SANDBOX_BASE_IMAGE: str = "python:3.11-slim"
    SANDBOX_NETWORK_NAME: str = "renum-sandbox"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instância global das configurações
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings    

    # Manifest Cache Configuration
    MANIFEST_CACHE_TTL_MINUTES: int = 5
    MANIFEST_CACHE_MAX_SIZE: int = 1000
    MANIFEST_CACHE_WARMING_THRESHOLD: int = 10
    MANIFEST_CACHE_CLEANUP_INTERVAL: int = 1
    MANIFEST_CACHE_WEBHOOK_SECRET: str = ""    

    # Data Purge and PII Configuration
    MAX_CONCURRENT_PURGES: int = 3
    PURGE_BATCH_SIZE: int = 1000
    PURGE_REQUIRE_APPROVAL: bool = True
    PII_HASH_SALT: str = "renum-pii-salt-change-in-production"