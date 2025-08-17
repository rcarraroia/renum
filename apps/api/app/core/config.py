"""
Configurações da aplicação Renum API.

Este módulo centraliza todas as configurações da aplicação,
usando Pydantic Settings para validação e carregamento de variáveis de ambiente.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    # Configurações básicas
    APP_NAME: str = Field(default="Renum API", description="Nome da aplicação")
    APP_VERSION: str = Field(default="1.0.0", description="Versão da aplicação")
    ENVIRONMENT: str = Field(default="development", description="Ambiente de execução")
    DEBUG: bool = Field(default=False, description="Modo debug")
    LOG_LEVEL: str = Field(default="INFO", description="Nível de log")
    
    # Configurações do servidor
    HOST: str = Field(default="0.0.0.0", description="Host do servidor")
    PORT: int = Field(default=8000, description="Porta do servidor")
    WORKERS: int = Field(default=1, description="Número de workers")
    
    # URLs
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="URL do frontend")
    API_BASE_URL: str = Field(default="http://localhost:8000", description="URL base da API")
    
    # Supabase
    SUPABASE_URL: str = Field(..., description="URL do Supabase")
    SUPABASE_ANON_KEY: str = Field(..., description="Chave anônima do Supabase")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Chave de service role do Supabase")
    
    # Suna Backend
    SUNA_BASE_URL: str = Field(default="http://157.180.39.41:8000", description="URL base do Suna Backend")
    SUNA_API_KEY: Optional[str] = Field(default=None, description="Chave de API do Suna")
    SUNA_TIMEOUT: int = Field(default=30, description="Timeout para requisições ao Suna")
    
    # Segurança
    JWT_SECRET_KEY: str = Field(..., description="Chave secreta para JWT")
    JWT_ALGORITHM: str = Field(default="HS256", description="Algoritmo JWT")
    JWT_EXPIRATION_HOURS: int = Field(default=24, description="Expiração do JWT em horas")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Origens permitidas para CORS"
    )
    ALLOWED_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Métodos permitidos para CORS"
    )
    ALLOWED_HEADERS: List[str] = Field(
        default=["*"],
        description="Headers permitidos para CORS"
    )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Número de requests por janela")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Janela de rate limit em segundos")
    
    # Redis (opcional)
    REDIS_URL: Optional[str] = Field(default=None, description="URL do Redis")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Senha do Redis")
    
    # Monitoramento
    SENTRY_DSN: Optional[str] = Field(default=None, description="DSN do Sentry")
    ENABLE_METRICS: bool = Field(default=False, description="Habilitar métricas")
    METRICS_PORT: int = Field(default=9090, description="Porta para métricas")
    
    # Health Checks
    HEALTH_CHECK_TIMEOUT: int = Field(default=5, description="Timeout para health checks")
    HEALTH_CHECK_INTERVAL: int = Field(default=30, description="Intervalo entre health checks")
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Valida o ambiente."""
        allowed = ["development", "staging", "production", "test"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Valida o nível de log."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse allowed origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def is_production(self) -> bool:
        """Verifica se está em produção."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Verifica se está em desenvolvimento."""
        return self.ENVIRONMENT == "development"
    
    @property
    def suna_api_url(self) -> str:
        """URL da API do Suna."""
        return f"{self.SUNA_BASE_URL.rstrip('/')}/api"
    
    @property
    def suna_ws_url(self) -> str:
        """URL do WebSocket do Suna."""
        ws_url = self.SUNA_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_url.rstrip('/')}/ws"
    
    class Config:
        """Configuração do Pydantic."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Instância global das configurações
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Obtém as configurações da aplicação (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Configurações para diferentes ambientes
def get_development_settings() -> Settings:
    """Configurações para desenvolvimento."""
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    return get_settings()


def get_production_settings() -> Settings:
    """Configurações para produção."""
    os.environ.setdefault("ENVIRONMENT", "production")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("ENABLE_METRICS", "true")
    return get_settings()


def get_test_settings() -> Settings:
    """Configurações para testes."""
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    return get_settings()