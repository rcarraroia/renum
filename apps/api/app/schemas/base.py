"""
Schemas base para a aplicação.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, Generic, TypeVar, List

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Schema base com configurações padrão."""
    
    class Config:
        from_attributes = True
        use_enum_values = True


class TimestampedSchema(BaseSchema):
    """Schema com timestamps de criação e atualização."""
    
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data da última atualização")


class PaginationParams(BaseModel):
    """Parâmetros de paginação."""
    
    page: int = Field(1, ge=1, description="Número da página")
    limit: int = Field(10, ge=1, le=100, description="Itens por página")


class PaginationMeta(BaseModel):
    """Metadados de paginação."""
    
    page: int
    limit: int
    total: int
    pages: int


class PaginatedResponse(BaseSchema, Generic[T]):
    """Resposta paginada genérica."""
    
    items: List[T]
    pagination: PaginationMeta


class HealthResponse(BaseSchema):
    """Resposta de health check."""
    
    status: str = Field(..., description="Status da aplicação")
    version: str = Field(..., description="Versão da aplicação")
    timestamp: str = Field(..., description="Timestamp da verificação")
    service: Optional[str] = Field(None, description="Nome do serviço")