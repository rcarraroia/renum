"""
Schemas para Prompt Editor (Agent Builder)
Modelos Pydantic para criação, edição e gerenciamento de prompts
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator


class PromptTypeEnum(str, Enum):
    """Tipos de prompt suportados"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TEMPLATE = "template"


class PromptCategoryEnum(str, Enum):
    """Categorias de prompt"""
    GENERAL = "general"
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    SUPPORT = "support"
    MARKETING = "marketing"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    CUSTOM = "custom"


class PromptStatusEnum(str, Enum):
    """Status do prompt"""
    DRAFT = "draft"
    ACTIVE = "active"
    TESTING = "testing"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PromptVariableSchema(BaseModel):
    """Schema para variável de prompt"""
    
    name: str = Field(..., min_length=1, max_length=50, description="Nome da variável")
    type: str = Field(..., description="Tipo da variável")
    description: str = Field(..., min_length=1, max_length=200, description="Descrição da variável")
    required: bool = Field(default=True, description="Se a variável é obrigatória")
    default_value: Optional[Any] = Field(None, description="Valor padrão")
    validation_pattern: Optional[str] = Field(None, description="Padrão regex para validação")
    min_length: Optional[int] = Field(None, ge=0, description="Comprimento mínimo")
    max_length: Optional[int] = Field(None, ge=1, description="Comprimento máximo")
    options: Optional[List[str]] = Field(None, description="Opções válidas para select/enum")
    
    @validator('type')
    def validate_type(cls, v):
        """Validar tipo de variável"""
        allowed_types = ['string', 'number', 'boolean', 'array', 'object']
        if v not in allowed_types:
            raise ValueError(f'Tipo deve ser um de: {", ".join(allowed_types)}')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validar nome da variável"""
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError('Nome deve ser um identificador válido (letras, números e underscore)')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "company_name",
                "type": "string",
                "description": "Nome da empresa",
                "required": True,
                "default_value": None,
                "min_length": 1,
                "max_length": 100
            }
        }


class CreatePromptVariableSchema(BaseModel):
    """Schema para criação de variável de prompt"""
    
    name: str = Field(..., min_length=1, max_length=50)
    type: str = Field(...)
    description: str = Field(..., min_length=1, max_length=200)
    required: bool = Field(default=True)
    default_value: Optional[Any] = None
    validation_pattern: Optional[str] = None
    min_length: Optional[int] = Field(None, ge=0)
    max_length: Optional[int] = Field(None, ge=1)
    options: Optional[List[str]] = None


class PromptTemplateSchema(BaseModel):
    """Schema para template de prompt"""
    
    template_id: str = Field(..., description="ID único do template")
    name: str = Field(..., min_length=1, max_length=100, description="Nome do template")
    description: str = Field(..., min_length=1, max_length=500, description="Descrição do template")
    category: PromptCategoryEnum = Field(..., description="Categoria do template")
    type: PromptTypeEnum = Field(..., description="Tipo do prompt")
    content: str = Field(..., min_length=10, description="Conteúdo do template")
    variables: List[PromptVariableSchema] = Field(default_factory=list, description="Variáveis do template")
    tags: List[str] = Field(default_factory=list, description="Tags para categorização")
    version: str = Field(..., description="Versão semântica")
    status: PromptStatusEnum = Field(..., description="Status do template")
    created_by: str = Field(..., description="Criado por")
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data de atualização")
    usage_count: int = Field(default=0, ge=0, description="Número de usos")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Avaliação média")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "template_id": "cs-general-001",
                "name": "Atendimento ao Cliente Geral",
                "description": "Template para atendimento ao cliente com tom profissional",
                "category": "customer_service",
                "type": "system",
                "content": "Você é um assistente de atendimento ao cliente da empresa {{company_name}}...",
                "variables": [
                    {
                        "name": "company_name",
                        "type": "string",
                        "description": "Nome da empresa",
                        "required": True
                    }
                ],
                "tags": ["atendimento", "cliente", "suporte"],
                "version": "1.0.0",
                "status": "active"
            }
        }


class CreatePromptTemplateSchema(BaseModel):
    """Schema para criação de template de prompt"""
    
    name: str = Field(..., min_length=1, max_length=100, description="Nome do template")
    description: str = Field(..., min_length=1, max_length=500, description="Descrição do template")
    category: PromptCategoryEnum = Field(..., description="Categoria do template")
    type: PromptTypeEnum = Field(..., description="Tipo do prompt")
    content: str = Field(..., min_length=10, description="Conteúdo do template")
    variables: List[CreatePromptVariableSchema] = Field(default_factory=list, description="Variáveis do template")
    tags: List[str] = Field(default_factory=list, description="Tags para categorização")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadados adicionais")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Novo Template de Vendas",
                "description": "Template personalizado para pitch de vendas",
                "category": "sales",
                "type": "system",
                "content": "Você é um consultor de vendas especializado em {{product_category}}...",
                "variables": [
                    {
                        "name": "product_category",
                        "type": "string",
                        "description": "Categoria do produto",
                        "required": True
                    }
                ],
                "tags": ["vendas", "pitch", "personalizado"]
            }
        }


class UpdatePromptTemplateSchema(BaseModel):
    """Schema para atualização de template de prompt"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[PromptCategoryEnum] = None
    content: Optional[str] = Field(None, min_length=10)
    variables: Optional[List[CreatePromptVariableSchema]] = None
    tags: Optional[List[str]] = None
    status: Optional[PromptStatusEnum] = None
    metadata: Optional[Dict[str, Any]] = None


class PromptRenderRequestSchema(BaseModel):
    """Schema para solicitação de renderização de prompt"""
    
    template_id: str = Field(..., description="ID do template")
    variables: Dict[str, Any] = Field(..., description="Variáveis para renderização")
    version: Optional[str] = Field(None, description="Versão específica do template")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "cs-general-001",
                "variables": {
                    "company_name": "Renum Tech",
                    "tone": "profissional",
                    "approach": "empático"
                }
            }
        }


class PromptRenderResponseSchema(BaseModel):
    """Schema para resposta de renderização de prompt"""
    
    rendered_content: str = Field(..., description="Conteúdo renderizado")
    metadata: Dict[str, Any] = Field(..., description="Metadados da renderização")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rendered_content": "Você é um assistente de atendimento ao cliente da empresa Renum Tech...",
                "metadata": {
                    "template_id": "cs-general-001",
                    "version": "1.0.0",
                    "character_count": 245,
                    "word_count": 42,
                    "rendered_at": "2024-01-15T10:30:00Z"
                }
            }
        }


class PromptTestRequestSchema(BaseModel):
    """Schema para solicitação de teste de prompt"""
    
    template_id: str = Field(..., description="ID do template")
    variables: Dict[str, Any] = Field(..., description="Variáveis para o teste")
    test_input: str = Field(..., min_length=1, description="Entrada de teste")
    version: Optional[str] = Field(None, description="Versão específica do template")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "cs-general-001",
                "variables": {
                    "company_name": "Renum Tech",
                    "tone": "profissional"
                },
                "test_input": "Olá, preciso de ajuda com meu pedido"
            }
        }


class PromptTestResultSchema(BaseModel):
    """Schema para resultado de teste de prompt"""
    
    test_id: str = Field(..., description="ID único do teste")
    template_id: str = Field(..., description="ID do template testado")
    version_id: str = Field(..., description="Versão testada")
    input_data: Dict[str, Any] = Field(..., description="Dados de entrada do teste")
    rendered_prompt: str = Field(..., description="Prompt renderizado")
    test_response: str = Field(..., description="Resposta do teste")
    execution_time_ms: float = Field(..., ge=0, description="Tempo de execução em ms")
    success: bool = Field(..., description="Se o teste foi bem-sucedido")
    error_message: Optional[str] = Field(None, description="Mensagem de erro se houver")
    metrics: Dict[str, Any] = Field(..., description="Métricas do teste")
    tested_by: str = Field(..., description="Quem executou o teste")
    tested_at: datetime = Field(..., description="Data/hora do teste")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "test_id": "test-123",
                "template_id": "cs-general-001",
                "version_id": "1.0.0",
                "success": True,
                "execution_time_ms": 1250.5,
                "test_response": "Olá! Sou o assistente da Renum Tech...",
                "metrics": {
                    "response_length": 156,
                    "tokens_used": 45,
                    "cost_estimate": 0.002
                }
            }
        }


class PromptVersionSchema(BaseModel):
    """Schema para versão de prompt"""
    
    version_id: str = Field(..., description="ID único da versão")
    template_id: str = Field(..., description="ID do template")
    version_number: str = Field(..., description="Número da versão")
    content: str = Field(..., description="Conteúdo desta versão")
    variables: List[PromptVariableSchema] = Field(..., description="Variáveis desta versão")
    changelog: str = Field(..., description="Log de mudanças")
    created_by: str = Field(..., description="Criado por")
    created_at: datetime = Field(..., description="Data de criação")
    is_active: bool = Field(..., description="Se é a versão ativa")
    
    class Config:
        from_attributes = True


class PromptAnalyticsSchema(BaseModel):
    """Schema para analytics de prompt"""
    
    template_id: str = Field(..., description="ID do template")
    template_name: str = Field(..., description="Nome do template")
    total_usage: int = Field(..., ge=0, description="Total de usos")
    total_tests: int = Field(..., ge=0, description="Total de testes")
    successful_tests: int = Field(..., ge=0, description="Testes bem-sucedidos")
    success_rate: float = Field(..., ge=0, le=100, description="Taxa de sucesso (%)")
    avg_execution_time_ms: float = Field(..., ge=0, description="Tempo médio de execução")
    total_versions: int = Field(..., ge=0, description="Total de versões")
    current_version: str = Field(..., description="Versão atual")
    rating: float = Field(..., ge=0, le=5, description="Avaliação média")
    usage_by_day: Dict[str, int] = Field(..., description="Uso por dia")
    last_used: Optional[str] = Field(None, description="Último uso")
    created_at: str = Field(..., description="Data de criação")
    updated_at: str = Field(..., description="Data de atualização")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "cs-general-001",
                "template_name": "Atendimento ao Cliente Geral",
                "total_usage": 156,
                "total_tests": 23,
                "successful_tests": 21,
                "success_rate": 91.3,
                "avg_execution_time_ms": 1245.6,
                "total_versions": 3,
                "current_version": "1.2.0",
                "rating": 4.2,
                "usage_by_day": {
                    "2024-01-15": 12,
                    "2024-01-14": 8,
                    "2024-01-13": 15
                }
            }
        }


class PromptValidationSchema(BaseModel):
    """Schema para resultado de validação de prompt"""
    
    valid: bool = Field(..., description="Se o prompt é válido")
    errors: List[str] = Field(..., description="Lista de erros")
    warnings: List[str] = Field(..., description="Lista de avisos")
    content_variables: List[str] = Field(..., description="Variáveis encontradas no conteúdo")
    defined_variables: List[str] = Field(..., description="Variáveis definidas")
    required_variables: List[str] = Field(..., description="Variáveis obrigatórias")
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "errors": [],
                "warnings": ["Variável 'optional_field' definida mas não usada"],
                "content_variables": ["company_name", "tone"],
                "defined_variables": ["company_name", "tone", "optional_field"],
                "required_variables": ["company_name", "tone"]
            }
        }


class PromptCloneRequestSchema(BaseModel):
    """Schema para solicitação de clonagem de prompt"""
    
    template_id: str = Field(..., description="ID do template a ser clonado")
    new_name: str = Field(..., min_length=1, max_length=100, description="Nome do novo template")
    modifications: Optional[Dict[str, Any]] = Field(None, description="Modificações a aplicar")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "cs-general-001",
                "new_name": "Atendimento Personalizado",
                "modifications": {
                    "description": "Versão personalizada do template geral",
                    "tags": ["personalizado", "atendimento"]
                }
            }
        }


class PromptExportSchema(BaseModel):
    """Schema para exportação de prompt"""
    
    template_data: Dict[str, Any] = Field(..., description="Dados completos do template")
    export_format: str = Field(default="json", description="Formato de exportação")
    exported_at: datetime = Field(..., description="Data/hora da exportação")
    exported_by: str = Field(..., description="Quem exportou")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_data": {
                    "template_id": "cs-general-001",
                    "name": "Atendimento ao Cliente Geral",
                    "content": "...",
                    "versions": []
                },
                "export_format": "json",
                "exported_at": "2024-01-15T10:30:00Z",
                "exported_by": "admin@renum.com"
            }
        }


class PromptImportRequestSchema(BaseModel):
    """Schema para solicitação de importação de prompt"""
    
    template_data: Dict[str, Any] = Field(..., description="Dados do template a importar")
    overwrite: bool = Field(default=False, description="Se deve sobrescrever template existente")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_data": {
                    "name": "Template Importado",
                    "description": "Template importado de arquivo",
                    "category": "general",
                    "type": "system",
                    "content": "Conteúdo do template...",
                    "variables": []
                },
                "overwrite": False
            }
        }


class PromptLibrarySchema(BaseModel):
    """Schema para biblioteca de templates"""
    
    templates: List[PromptTemplateSchema] = Field(..., description="Lista de templates")
    total_count: int = Field(..., ge=0, description="Total de templates")
    categories: List[str] = Field(..., description="Categorias disponíveis")
    tags: List[str] = Field(..., description="Tags disponíveis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "templates": [],
                "total_count": 25,
                "categories": ["customer_service", "sales", "support"],
                "tags": ["atendimento", "vendas", "suporte", "geral"]
            }
        }