"""
Schemas para distribuição de chaves públicas
Modelos Pydantic para endpoints de chaves públicas
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class KeyType(str, Enum):
    """Tipos de chave suportados"""
    RSA = "rsa"
    ECDSA = "ecdsa"
    ED25519 = "ed25519"

class KeyFormat(str, Enum):
    """Formatos de chave suportados"""
    PEM = "pem"
    JWK = "jwk"
    DER = "der"

class KeyUsage(str, Enum):
    """Usos permitidos para a chave"""
    SIGN = "sign"
    VERIFY = "verify"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"

class KeyMetadata(BaseModel):
    """Metadados de uma chave pública"""
    key_id: str = Field(..., description="ID único da chave")
    key_type: KeyType = Field(..., description="Tipo da chave (RSA, ECDSA, etc.)")
    algorithm: str = Field(..., description="Algoritmo de assinatura (RS256, ES256, etc.)")
    created_at: datetime = Field(..., description="Data de criação da chave")
    expires_at: Optional[datetime] = Field(None, description="Data de expiração da chave")
    is_active: bool = Field(..., description="Se a chave está ativa")
    usage: List[KeyUsage] = Field(default=["verify"], description="Usos permitidos da chave")
    fingerprint: str = Field(..., description="Fingerprint SHA256 da chave")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "renum-signing-key-2024-001",
                "key_type": "rsa",
                "algorithm": "RS256",
                "created_at": "2024-01-15T10:30:00Z",
                "expires_at": "2025-01-15T10:30:00Z",
                "is_active": True,
                "usage": ["verify"],
                "fingerprint": "sha256:1234567890abcdef..."
            }
        }

class PublicKeyResponse(BaseModel):
    """Resposta com chave pública completa"""
    key_id: str = Field(..., description="ID único da chave")
    key_type: KeyType = Field(..., description="Tipo da chave")
    algorithm: str = Field(..., description="Algoritmo de assinatura")
    public_key: str = Field(..., description="Chave pública no formato solicitado")
    format: KeyFormat = Field(..., description="Formato da chave retornada")
    created_at: datetime = Field(..., description="Data de criação")
    expires_at: Optional[datetime] = Field(None, description="Data de expiração")
    is_active: bool = Field(..., description="Status da chave")
    usage: List[KeyUsage] = Field(default=["verify"], description="Usos permitidos")
    fingerprint: str = Field(..., description="Fingerprint da chave")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "renum-signing-key-2024-001",
                "key_type": "rsa",
                "algorithm": "RS256",
                "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----",
                "format": "pem",
                "created_at": "2024-01-15T10:30:00Z",
                "expires_at": "2025-01-15T10:30:00Z",
                "is_active": True,
                "usage": ["verify"],
                "fingerprint": "sha256:1234567890abcdef..."
            }
        }

class KeyListResponse(BaseModel):
    """Resposta com lista de chaves públicas"""
    keys: List[KeyMetadata] = Field(..., description="Lista de chaves públicas")
    total_count: int = Field(..., description="Total de chaves")
    active_count: int = Field(..., description="Número de chaves ativas")

    class Config:
        json_schema_extra = {
            "example": {
                "keys": [
                    {
                        "key_id": "renum-signing-key-2024-001",
                        "key_type": "rsa",
                        "algorithm": "RS256",
                        "created_at": "2024-01-15T10:30:00Z",
                        "expires_at": "2025-01-15T10:30:00Z",
                        "is_active": True,
                        "usage": ["verify"],
                        "fingerprint": "sha256:1234567890abcdef..."
                    }
                ],
                "total_count": 1,
                "active_count": 1
            }
        }

class JWK(BaseModel):
    """JSON Web Key (RFC 7517)"""
    kty: str = Field(..., description="Key Type")
    use: Optional[str] = Field(None, description="Public Key Use")
    key_ops: Optional[List[str]] = Field(None, description="Key Operations")
    alg: Optional[str] = Field(None, description="Algorithm")
    kid: Optional[str] = Field(None, description="Key ID")
    x5u: Optional[str] = Field(None, description="X.509 URL")
    x5c: Optional[List[str]] = Field(None, description="X.509 Certificate Chain")
    x5t: Optional[str] = Field(None, description="X.509 Certificate SHA-1 Thumbprint")
    x5t_s256: Optional[str] = Field(None, description="X.509 Certificate SHA-256 Thumbprint")
    
    # RSA specific fields
    n: Optional[str] = Field(None, description="RSA Modulus")
    e: Optional[str] = Field(None, description="RSA Exponent")
    
    # ECDSA specific fields
    crv: Optional[str] = Field(None, description="Curve")
    x: Optional[str] = Field(None, description="X Coordinate")
    y: Optional[str] = Field(None, description="Y Coordinate")
    
    # Additional fields
    ext: Optional[bool] = Field(None, description="Extractable")

    class Config:
        json_schema_extra = {
            "example": {
                "kty": "RSA",
                "use": "sig",
                "key_ops": ["verify"],
                "alg": "RS256",
                "kid": "renum-signing-key-2024-001",
                "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
                "e": "AQAB"
            }
        }

class JWKSResponse(BaseModel):
    """JSON Web Key Set (RFC 7517)"""
    keys: List[JWK] = Field(..., description="Array of JWK objects")

    class Config:
        json_schema_extra = {
            "example": {
                "keys": [
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "key_ops": ["verify"],
                        "alg": "RS256",
                        "kid": "renum-signing-key-2024-001",
                        "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
                        "e": "AQAB"
                    }
                ]
            }
        }

class KeyStatusResponse(BaseModel):
    """Resposta do status de uma chave"""
    key_id: str = Field(..., description="ID da chave")
    is_active: bool = Field(..., description="Se a chave está ativa")
    is_expired: bool = Field(..., description="Se a chave está expirada")
    is_valid: bool = Field(..., description="Se a chave é válida para uso")
    can_verify: bool = Field(..., description="Se pode ser usada para verificação")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "renum-signing-key-2024-001",
                "is_active": True,
                "is_expired": False,
                "is_valid": True,
                "can_verify": True
            }
        }

class KeyFingerprintResponse(BaseModel):
    """Resposta com fingerprint de uma chave"""
    key_id: str = Field(..., description="ID da chave")
    algorithm: str = Field(..., description="Algoritmo de hash usado")
    fingerprint: str = Field(..., description="Fingerprint da chave")
    format: str = Field(default="hex", description="Formato do fingerprint")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "renum-signing-key-2024-001",
                "algorithm": "sha256",
                "fingerprint": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "format": "hex"
            }
        }

class SupportedAlgorithmsResponse(BaseModel):
    """Resposta com algoritmos suportados"""
    signature_algorithms: List[str] = Field(..., description="Algoritmos de assinatura suportados")
    hash_algorithms: List[str] = Field(..., description="Algoritmos de hash suportados")
    key_types: List[str] = Field(..., description="Tipos de chave suportados")
    formats: List[str] = Field(..., description="Formatos de chave suportados")

    class Config:
        json_schema_extra = {
            "example": {
                "signature_algorithms": ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
                "hash_algorithms": ["sha256", "sha384", "sha512", "sha1", "md5"],
                "key_types": ["rsa", "ecdsa", "ed25519"],
                "formats": ["pem", "jwk", "der"]
            }
        }

class KeyHealthResponse(BaseModel):
    """Resposta do health check do serviço de chaves"""
    status: str = Field(..., description="Status do serviço (healthy, degraded, unhealthy)")
    active_keys_count: int = Field(..., description="Número de chaves ativas")
    service: str = Field(default="public-key-distribution", description="Nome do serviço")
    timestamp: str = Field(..., description="Timestamp da verificação")
    error: Optional[str] = Field(None, description="Mensagem de erro se houver")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "active_keys_count": 3,
                "service": "public-key-distribution",
                "timestamp": "2024-12-15T14:30:22Z"
            }
        }