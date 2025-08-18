"""
Endpoints para distribuição de chaves públicas
Fornece chaves públicas para verificação de assinaturas de manifests
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.services.signature_service import signature_service
from app.schemas.keys import (
    PublicKeyResponse,
    KeyListResponse,
    KeyMetadata,
    JWKSResponse
)
from app.middleware.auth import get_current_user_optional

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/keys", tags=["Public Keys"])

@router.get("/", response_model=KeyListResponse)
async def list_public_keys(
    key_type: Optional[str] = Query(None, description="Filter by key type (rsa, ecdsa)"),
    active_only: bool = Query(True, description="Return only active keys"),
    current_user = Depends(get_current_user_optional)
):
    """
    Listar todas as chaves públicas disponíveis para verificação de assinaturas.
    
    Este endpoint é público e não requer autenticação, permitindo que qualquer
    cliente verifique a autenticidade dos manifests de agentes.
    
    - **key_type**: Filtrar por tipo de chave (rsa, ecdsa)
    - **active_only**: Retornar apenas chaves ativas (padrão: true)
    
    Retorna lista de metadados das chaves públicas disponíveis.
    """
    try:
        logger.info(
            "Listing public keys",
            key_type=key_type,
            active_only=active_only,
            user_id=getattr(current_user, 'user_id', None)
        )
        
        keys = await signature_service.list_public_keys(
            key_type=key_type,
            active_only=active_only
        )
        
        key_metadata = []
        for key_info in keys:
            metadata = KeyMetadata(
                key_id=key_info['key_id'],
                key_type=key_info['key_type'],
                algorithm=key_info['algorithm'],
                created_at=key_info['created_at'],
                expires_at=key_info.get('expires_at'),
                is_active=key_info['is_active'],
                usage=key_info.get('usage', ['verify']),
                fingerprint=key_info['fingerprint']
            )
            key_metadata.append(metadata)
        
        return KeyListResponse(
            keys=key_metadata,
            total_count=len(key_metadata),
            active_count=len([k for k in key_metadata if k.is_active])
        )
        
    except Exception as e:
        logger.error("Failed to list public keys", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve public keys"
        )

@router.get("/{key_id}", response_model=PublicKeyResponse)
async def get_public_key(
    key_id: str,
    format: str = Query("pem", description="Key format (pem, jwk, der)"),
    current_user = Depends(get_current_user_optional)
):
    """
    Obter uma chave pública específica por ID.
    
    Este endpoint é público e permite obter a chave pública em diferentes
    formatos para verificação de assinaturas de manifests.
    
    - **key_id**: ID único da chave pública
    - **format**: Formato da chave (pem, jwk, der)
    
    Retorna a chave pública no formato solicitado.
    """
    try:
        logger.info(
            "Getting public key",
            key_id=key_id,
            format=format,
            user_id=getattr(current_user, 'user_id', None)
        )
        
        # Validar formato
        if format not in ['pem', 'jwk', 'der']:
            raise HTTPException(
                status_code=400,
                detail="Invalid format. Supported formats: pem, jwk, der"
            )
        
        key_info = await signature_service.get_public_key(key_id, format=format)
        
        if not key_info:
            raise HTTPException(
                status_code=404,
                detail=f"Public key {key_id} not found"
            )
        
        # Verificar se a chave está ativa
        if not key_info.get('is_active', False):
            logger.warning("Requested inactive public key", key_id=key_id)
            # Ainda permitir acesso a chaves inativas para verificação de manifests antigos
        
        return PublicKeyResponse(
            key_id=key_info['key_id'],
            key_type=key_info['key_type'],
            algorithm=key_info['algorithm'],
            public_key=key_info['public_key'],
            format=format,
            created_at=key_info['created_at'],
            expires_at=key_info.get('expires_at'),
            is_active=key_info['is_active'],
            usage=key_info.get('usage', ['verify']),
            fingerprint=key_info['fingerprint']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get public key", key_id=key_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve public key"
        )

@router.get("/.well-known/jwks.json", response_model=JWKSResponse)
async def get_jwks():
    """
    Endpoint JWKS (JSON Web Key Set) padrão para distribuição de chaves públicas.
    
    Este endpoint segue o padrão RFC 7517 para distribuição de chaves públicas
    em formato JWK, facilitando a integração com bibliotecas JWT padrão.
    
    Retorna todas as chaves públicas ativas em formato JWKS.
    """
    try:
        logger.info("Getting JWKS")
        
        jwks = await signature_service.get_jwks()
        
        return JWKSResponse(keys=jwks['keys'])
        
    except Exception as e:
        logger.error("Failed to get JWKS", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve JWKS"
        )

@router.get("/{key_id}/verify", response_model=Dict[str, bool])
async def verify_key_status(
    key_id: str,
    current_user = Depends(get_current_user_optional)
):
    """
    Verificar o status de uma chave pública.
    
    Este endpoint permite verificar se uma chave específica está ativa
    e pode ser usada para verificação de assinaturas.
    
    - **key_id**: ID único da chave pública
    
    Retorna o status da chave (ativa/inativa, expirada, etc.).
    """
    try:
        logger.info(
            "Verifying key status",
            key_id=key_id,
            user_id=getattr(current_user, 'user_id', None)
        )
        
        key_info = await signature_service.get_public_key(key_id)
        
        if not key_info:
            raise HTTPException(
                status_code=404,
                detail=f"Public key {key_id} not found"
            )
        
        # Verificar status da chave
        is_active = key_info.get('is_active', False)
        is_expired = False
        
        if key_info.get('expires_at'):
            from datetime import datetime
            expires_at = key_info['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            is_expired = datetime.utcnow() > expires_at.replace(tzinfo=None)
        
        return {
            "key_id": key_id,
            "is_active": is_active,
            "is_expired": is_expired,
            "is_valid": is_active and not is_expired,
            "can_verify": is_active  # Permitir verificação mesmo se expirada
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to verify key status", key_id=key_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to verify key status"
        )

@router.get("/{key_id}/fingerprint")
async def get_key_fingerprint(
    key_id: str,
    algorithm: str = Query("sha256", description="Hash algorithm (sha256, sha1, md5)"),
    current_user = Depends(get_current_user_optional)
):
    """
    Obter fingerprint de uma chave pública.
    
    O fingerprint é um hash da chave pública que pode ser usado para
    verificação rápida da integridade da chave.
    
    - **key_id**: ID único da chave pública
    - **algorithm**: Algoritmo de hash (sha256, sha1, md5)
    
    Retorna o fingerprint da chave no algoritmo especificado.
    """
    try:
        logger.info(
            "Getting key fingerprint",
            key_id=key_id,
            algorithm=algorithm,
            user_id=getattr(current_user, 'user_id', None)
        )
        
        # Validar algoritmo
        if algorithm not in ['sha256', 'sha1', 'md5']:
            raise HTTPException(
                status_code=400,
                detail="Invalid algorithm. Supported: sha256, sha1, md5"
            )
        
        fingerprint = await signature_service.get_key_fingerprint(key_id, algorithm)
        
        if not fingerprint:
            raise HTTPException(
                status_code=404,
                detail=f"Public key {key_id} not found"
            )
        
        return {
            "key_id": key_id,
            "algorithm": algorithm,
            "fingerprint": fingerprint,
            "format": "hex"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get key fingerprint", key_id=key_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get key fingerprint"
        )

@router.get("/algorithms/supported")
async def get_supported_algorithms():
    """
    Listar algoritmos de assinatura suportados.
    
    Retorna lista de algoritmos de assinatura e hash suportados
    pelo sistema para verificação de manifests.
    """
    try:
        algorithms = await signature_service.get_supported_algorithms()
        
        return {
            "signature_algorithms": algorithms.get('signature', []),
            "hash_algorithms": algorithms.get('hash', []),
            "key_types": algorithms.get('key_types', []),
            "formats": ["pem", "jwk", "der"]
        }
        
    except Exception as e:
        logger.error("Failed to get supported algorithms", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get supported algorithms"
        )

# Endpoint de health check específico para o serviço de chaves
@router.get("/health")
async def keys_health_check():
    """
    Health check do serviço de distribuição de chaves.
    
    Verifica se o serviço de chaves está funcionando corretamente
    e se as chaves públicas estão acessíveis.
    """
    try:
        # Verificar se conseguimos listar chaves
        keys = await signature_service.list_public_keys(active_only=True)
        
        # Verificar se há pelo menos uma chave ativa
        active_keys_count = len(keys)
        
        status = "healthy" if active_keys_count > 0 else "degraded"
        
        return {
            "status": status,
            "active_keys_count": active_keys_count,
            "service": "public-key-distribution",
            "timestamp": "2024-12-15T14:30:22Z"
        }
        
    except Exception as e:
        logger.error("Keys health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "Service unavailable",
                "service": "public-key-distribution",
                "timestamp": "2024-12-15T14:30:22Z"
            }
        )