"""
Schemas para Manifesto de Agentes com Verificação Digital
Define estrutura formal e validação de manifestos de agentes
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
import hashlib
import json

class AgentStatus(str, Enum):
    """Status do agente"""
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"

class AgentCapabilitySchema(BaseModel):
    """Schema de capacidade do agente"""
    name: str = Field(..., description="Nome da capacidade")
    description: str = Field(..., description="Descrição da capacidade")
    input_schema: Dict[str, Any] = Field(..., description="Schema de entrada JSON")
    output_schema: Dict[str, Any] = Field(..., description="Schema de saída JSON")
    required_credentials: List[str] = Field(default=[], description="Credenciais necessárias")
    cost_per_execution: float = Field(default=0.0, description="Custo por execução")

class AgentSecurityInfo(BaseModel):
    """Informações de segurança do agente"""
    permissions: List[str] = Field(default=[], description="Permissões necessárias")
    network_access: bool = Field(default=True, description="Requer acesso à rede")
    file_system_access: bool = Field(default=False, description="Requer acesso ao sistema de arquivos")
    sensitive_data_access: bool = Field(default=False, description="Acessa dados sensíveis")
    external_apis: List[str] = Field(default=[], description="APIs externas utilizadas")

class AgentMetadata(BaseModel):
    """Metadados do agente"""
    author: str = Field(..., description="Autor do agente")
    organization: Optional[str] = Field(None, description="Organização")
    license: str = Field(default="proprietary", description="Licença")
    tags: List[str] = Field(default=[], description="Tags para categorização")
    documentation_url: Optional[str] = Field(None, description="URL da documentação")
    support_url: Optional[str] = Field(None, description="URL de suporte")
    changelog_url: Optional[str] = Field(None, description="URL do changelog")

class AgentManifestSignature(BaseModel):
    """Assinatura digital do manifesto"""
    algorithm: str = Field(..., description="Algoritmo de assinatura (RS256)")
    signature: str = Field(..., description="Assinatura digital base64")
    signature_key_id: str = Field(..., description="ID da chave pública para verificação")
    signed_at: datetime = Field(..., description="Timestamp da assinatura")
    signed_by: str = Field(..., description="Identificador do signatário")

class AgentManifestCore(BaseModel):
    """Núcleo do manifesto do agente (dados assinados)"""
    # Identificação
    agent_id: str = Field(..., regex=r"^sa-[a-z0-9-]+$", description="ID único do agente")
    name: str = Field(..., min_length=1, max_length=100, description="Nome do agente")
    description: str = Field(..., min_length=1, max_length=500, description="Descrição do agente")
    version: str = Field(..., regex=r"^\d+\.\d+\.\d+(-\w+)?$", description="Versão semântica")
    
    # Capacidades
    capabilities: List[AgentCapabilitySchema] = Field(..., min_items=1, description="Capacidades do agente")
    
    # Segurança
    security: AgentSecurityInfo = Field(..., description="Informações de segurança")
    
    # Metadados
    metadata: AgentMetadata = Field(..., description="Metadados do agente")
    
    # Timestamps
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data de atualização")
    
    # Checksum do código
    code_checksum: str = Field(..., description="SHA256 do código do agente")
    
    @validator('capabilities')
    def validate_capabilities(cls, v):
        """Validar capacidades únicas"""
        names = [cap.name for cap in v]
        if len(names) != len(set(names)):
            raise ValueError("Nomes de capacidades devem ser únicos")
        return v
    
    def calculate_content_hash(self) -> str:
        """Calcular hash do conteúdo para verificação de integridade"""
        # Serializar de forma determinística
        content = self.dict(exclude={'updated_at'}, sort_keys=True)
        content_json = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content_json.encode()).hexdigest()

class AgentManifest(BaseModel):
    """Manifesto completo do agente com assinatura"""
    # Versão do schema
    schema_version: str = Field(default="1.0.0", description="Versão do schema do manifesto")
    
    # Conteúdo principal
    manifest: AgentManifestCore = Field(..., description="Conteúdo do manifesto")
    
    # Assinatura digital
    signature: AgentManifestSignature = Field(..., description="Assinatura digital")
    
    # Status e aprovação
    status: AgentStatus = Field(default=AgentStatus.DRAFT, description="Status do agente")
    approved_by: Optional[str] = Field(None, description="Aprovado por (superadmin)")
    approved_at: Optional[datetime] = Field(None, description="Data de aprovação")
    
    # Verificação de integridade
    content_hash: str = Field(..., description="Hash do conteúdo para verificação")
    
    @validator('content_hash')
    def validate_content_hash(cls, v, values):
        """Validar hash do conteúdo"""
        if 'manifest' in values:
            expected_hash = values['manifest'].calculate_content_hash()
            if v != expected_hash:
                raise ValueError("Hash do conteúdo não confere")
        return v
    
    @validator('approved_at')
    def validate_approval(cls, v, values):
        """Validar aprovação"""
        if 'status' in values and values['status'] == AgentStatus.APPROVED:
            if not v or not values.get('approved_by'):
                raise ValueError("Agente aprovado deve ter approved_by e approved_at")
        return v

class CreateAgentManifestRequest(BaseModel):
    """Request para criar manifesto de agente"""
    manifest: AgentManifestCore = Field(..., description="Conteúdo do manifesto")
    
class SignAgentManifestRequest(BaseModel):
    """Request para assinar manifesto de agente"""
    agent_id: str = Field(..., description="ID do agente")
    version: str = Field(..., description="Versão do agente")
    private_key_id: str = Field(..., description="ID da chave privada para assinatura")

class VerifyAgentManifestRequest(BaseModel):
    """Request para verificar manifesto de agente"""
    manifest: AgentManifest = Field(..., description="Manifesto para verificação")

class AgentManifestResponse(BaseModel):
    """Response com manifesto de agente"""
    manifest: AgentManifest = Field(..., description="Manifesto do agente")
    verification_status: str = Field(..., description="Status da verificação")
    verification_details: Dict[str, Any] = Field(default={}, description="Detalhes da verificação")

class PublicKeyInfo(BaseModel):
    """Informações da chave pública"""
    key_id: str = Field(..., description="ID da chave")
    algorithm: str = Field(..., description="Algoritmo (RS256)")
    public_key: str = Field(..., description="Chave pública PEM")
    created_at: datetime = Field(..., description="Data de criação")
    expires_at: Optional[datetime] = Field(None, description="Data de expiração")
    is_active: bool = Field(default=True, description="Chave ativa")
    description: Optional[str] = Field(None, description="Descrição da chave")

class PublicKeysResponse(BaseModel):
    """Response com chaves públicas"""
    keys: List[PublicKeyInfo] = Field(..., description="Lista de chaves públicas")
    
class AgentManifestListResponse(BaseModel):
    """Response com lista de manifestos"""
    manifests: List[AgentManifest] = Field(..., description="Lista de manifestos")
    total: int = Field(..., description="Total de manifestos")
    page: int = Field(..., description="Página atual")
    per_page: int = Field(..., description="Itens por página")

# JSON Schema para validação externa
AGENT_MANIFEST_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://api.renum.com/schemas/agent-manifest/v1.0.0",
    "title": "Renum Agent Manifest",
    "description": "Schema for Renum agent manifests with digital signature verification",
    "type": "object",
    "required": ["schema_version", "manifest", "signature", "content_hash"],
    "properties": {
        "schema_version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
            "description": "Version of the manifest schema"
        },
        "manifest": {
            "type": "object",
            "required": ["agent_id", "name", "description", "version", "capabilities", "security", "metadata", "created_at", "updated_at", "code_checksum"],
            "properties": {
                "agent_id": {
                    "type": "string",
                    "pattern": "^sa-[a-z0-9-]+$",
                    "description": "Unique agent identifier"
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Agent name"
                },
                "description": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 500,
                    "description": "Agent description"
                },
                "version": {
                    "type": "string",
                    "pattern": "^\\d+\\.\\d+\\.\\d+(-\\w+)?$",
                    "description": "Semantic version"
                },
                "capabilities": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["name", "description", "input_schema", "output_schema"],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "input_schema": {"type": "object"},
                            "output_schema": {"type": "object"},
                            "required_credentials": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "cost_per_execution": {"type": "number", "minimum": 0}
                        }
                    }
                },
                "security": {
                    "type": "object",
                    "properties": {
                        "permissions": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "network_access": {"type": "boolean"},
                        "file_system_access": {"type": "boolean"},
                        "sensitive_data_access": {"type": "boolean"},
                        "external_apis": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "metadata": {
                    "type": "object",
                    "required": ["author"],
                    "properties": {
                        "author": {"type": "string"},
                        "organization": {"type": "string"},
                        "license": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "documentation_url": {"type": "string", "format": "uri"},
                        "support_url": {"type": "string", "format": "uri"},
                        "changelog_url": {"type": "string", "format": "uri"}
                    }
                },
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"},
                "code_checksum": {
                    "type": "string",
                    "pattern": "^[a-f0-9]{64}$",
                    "description": "SHA256 checksum of agent code"
                }
            }
        },
        "signature": {
            "type": "object",
            "required": ["algorithm", "signature", "signature_key_id", "signed_at", "signed_by"],
            "properties": {
                "algorithm": {
                    "type": "string",
                    "enum": ["RS256"],
                    "description": "Signature algorithm"
                },
                "signature": {
                    "type": "string",
                    "description": "Base64 encoded signature"
                },
                "signature_key_id": {
                    "type": "string",
                    "description": "Public key ID for verification"
                },
                "signed_at": {"type": "string", "format": "date-time"},
                "signed_by": {"type": "string", "description": "Signer identifier"}
            }
        },
        "status": {
            "type": "string",
            "enum": ["draft", "approved", "deprecated", "revoked"],
            "description": "Agent status"
        },
        "approved_by": {"type": "string"},
        "approved_at": {"type": "string", "format": "date-time"},
        "content_hash": {
            "type": "string",
            "pattern": "^[a-f0-9]{64}$",
            "description": "SHA256 hash of manifest content"
        }
    }
}