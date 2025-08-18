"""
Serviço de Assinatura Digital para Manifestos de Agentes
Implementa assinatura e verificação usando RS256/JWT
"""
import base64
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
import jwt
import structlog

from app.core.config import settings
from app.schemas.agent_manifest import (
    AgentManifest,
    AgentManifestCore,
    AgentManifestSignature,
    PublicKeyInfo
)

logger = structlog.get_logger(__name__)

class SignatureService:
    """Serviço para assinatura digital de manifestos"""
    
    def __init__(self):
        self.algorithm = "RS256"
        self.key_size = 2048
        self.signature_validity_days = 365
        
        # Cache de chaves públicas
        self._public_keys_cache: Dict[str, PublicKeyInfo] = {}
        self._cache_ttl = 300  # 5 minutos
        self._cache_updated_at: Optional[datetime] = None
    
    async def generate_key_pair(self, key_id: str, description: Optional[str] = None) -> Dict[str, str]:
        """
        Gerar par de chaves RSA para assinatura
        
        Args:
            key_id: Identificador único da chave
            description: Descrição da chave
            
        Returns:
            Dict com chave privada e pública em formato PEM
        """
        logger.info("Generating RSA key pair", key_id=key_id)
        
        try:
            # Gerar chave privada
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=self.key_size
            )
            
            # Extrair chave pública
            public_key = private_key.public_key()
            
            # Serializar chaves em formato PEM
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            # Criar informações da chave pública
            public_key_info = PublicKeyInfo(
                key_id=key_id,
                algorithm=self.algorithm,
                public_key=public_pem,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=self.signature_validity_days),
                is_active=True,
                description=description
            )
            
            # Salvar chave pública (em produção, salvar no banco de dados)
            await self._store_public_key(public_key_info)
            
            logger.info("RSA key pair generated successfully", key_id=key_id)
            
            return {
                "key_id": key_id,
                "private_key": private_pem,
                "public_key": public_pem,
                "algorithm": self.algorithm
            }
            
        except Exception as e:
            logger.error("Failed to generate key pair", key_id=key_id, error=str(e))
            raise
    
    async def sign_manifest(
        self, 
        manifest_core: AgentManifestCore, 
        private_key_pem: str, 
        key_id: str,
        signed_by: str
    ) -> AgentManifestSignature:
        """
        Assinar manifesto de agente
        
        Args:
            manifest_core: Conteúdo do manifesto para assinar
            private_key_pem: Chave privada em formato PEM
            key_id: ID da chave pública correspondente
            signed_by: Identificador do signatário
            
        Returns:
            Assinatura digital do manifesto
        """
        logger.info("Signing agent manifest", agent_id=manifest_core.agent_id, key_id=key_id)
        
        try:
            # Serializar manifesto de forma determinística
            manifest_dict = manifest_core.dict(sort_keys=True)
            manifest_json = json.dumps(manifest_dict, sort_keys=True, separators=(',', ':'))
            manifest_bytes = manifest_json.encode('utf-8')
            
            # Carregar chave privada
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None
            )
            
            # Criar payload JWT
            now = datetime.utcnow()
            payload = {
                "iss": "renum-api",  # Issuer
                "sub": manifest_core.agent_id,  # Subject (agent ID)
                "aud": "renum-orchestrator",  # Audience
                "iat": int(now.timestamp()),  # Issued at
                "exp": int((now + timedelta(days=self.signature_validity_days)).timestamp()),  # Expires
                "manifest_hash": hashlib.sha256(manifest_bytes).hexdigest(),
                "key_id": key_id,
                "signed_by": signed_by
            }
            
            # Assinar usando JWT RS256
            token = jwt.encode(payload, private_key, algorithm=self.algorithm, headers={"kid": key_id})
            
            # Criar assinatura
            signature = AgentManifestSignature(
                algorithm=self.algorithm,
                signature=token,
                signature_key_id=key_id,
                signed_at=now,
                signed_by=signed_by
            )
            
            logger.info("Agent manifest signed successfully", 
                       agent_id=manifest_core.agent_id, 
                       key_id=key_id)
            
            return signature
            
        except Exception as e:
            logger.error("Failed to sign manifest", 
                        agent_id=manifest_core.agent_id, 
                        key_id=key_id, 
                        error=str(e))
            raise
    
    async def verify_manifest_signature(self, manifest: AgentManifest) -> Dict[str, Any]:
        """
        Verificar assinatura digital do manifesto
        
        Args:
            manifest: Manifesto completo com assinatura
            
        Returns:
            Resultado da verificação com detalhes
        """
        logger.info("Verifying manifest signature", 
                   agent_id=manifest.manifest.agent_id,
                   key_id=manifest.signature.signature_key_id)
        
        verification_result = {
            "valid": False,
            "details": {},
            "errors": []
        }
        
        try:
            # 1. Verificar hash do conteúdo
            expected_hash = manifest.manifest.calculate_content_hash()
            if manifest.content_hash != expected_hash:
                verification_result["errors"].append("Content hash mismatch")
                return verification_result
            
            verification_result["details"]["content_hash_valid"] = True
            
            # 2. Obter chave pública
            public_key_info = await self._get_public_key(manifest.signature.signature_key_id)
            if not public_key_info:
                verification_result["errors"].append(f"Public key not found: {manifest.signature.signature_key_id}")
                return verification_result
            
            if not public_key_info.is_active:
                verification_result["errors"].append("Public key is not active")
                return verification_result
            
            verification_result["details"]["public_key_found"] = True
            verification_result["details"]["public_key_active"] = True
            
            # 3. Verificar expiração da chave
            if public_key_info.expires_at and datetime.utcnow() > public_key_info.expires_at:
                verification_result["errors"].append("Public key has expired")
                return verification_result
            
            verification_result["details"]["public_key_not_expired"] = True
            
            # 4. Carregar chave pública
            public_key = serialization.load_pem_public_key(
                public_key_info.public_key.encode('utf-8')
            )
            
            # 5. Verificar assinatura JWT
            try:
                decoded_payload = jwt.decode(
                    manifest.signature.signature,
                    public_key,
                    algorithms=[self.algorithm],
                    audience="renum-orchestrator",
                    issuer="renum-api"
                )
                
                verification_result["details"]["jwt_signature_valid"] = True
                verification_result["details"]["decoded_payload"] = decoded_payload
                
            except jwt.ExpiredSignatureError:
                verification_result["errors"].append("Signature has expired")
                return verification_result
            except jwt.InvalidTokenError as e:
                verification_result["errors"].append(f"Invalid JWT token: {str(e)}")
                return verification_result
            
            # 6. Verificar hash do manifesto no payload
            manifest_dict = manifest.manifest.dict(sort_keys=True)
            manifest_json = json.dumps(manifest_dict, sort_keys=True, separators=(',', ':'))
            manifest_hash = hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()
            
            if decoded_payload.get("manifest_hash") != manifest_hash:
                verification_result["errors"].append("Manifest hash in signature doesn't match")
                return verification_result
            
            verification_result["details"]["manifest_hash_valid"] = True
            
            # 7. Verificar subject (agent_id)
            if decoded_payload.get("sub") != manifest.manifest.agent_id:
                verification_result["errors"].append("Agent ID in signature doesn't match")
                return verification_result
            
            verification_result["details"]["agent_id_valid"] = True
            
            # 8. Verificar key_id
            if decoded_payload.get("key_id") != manifest.signature.signature_key_id:
                verification_result["errors"].append("Key ID in signature doesn't match")
                return verification_result
            
            verification_result["details"]["key_id_valid"] = True
            
            # Todas as verificações passaram
            verification_result["valid"] = True
            verification_result["details"]["verified_at"] = datetime.utcnow().isoformat()
            verification_result["details"]["signed_by"] = decoded_payload.get("signed_by")
            
            logger.info("Manifest signature verified successfully", 
                       agent_id=manifest.manifest.agent_id,
                       key_id=manifest.signature.signature_key_id)
            
            return verification_result
            
        except Exception as e:
            logger.error("Failed to verify manifest signature", 
                        agent_id=manifest.manifest.agent_id,
                        error=str(e))
            verification_result["errors"].append(f"Verification error: {str(e)}")
            return verification_result
    
    async def get_public_keys(self, active_only: bool = True) -> List[PublicKeyInfo]:
        """
        Obter lista de chaves públicas
        
        Args:
            active_only: Retornar apenas chaves ativas
            
        Returns:
            Lista de informações de chaves públicas
        """
        logger.info("Getting public keys", active_only=active_only)
        
        try:
            # Verificar cache
            if self._should_refresh_cache():
                await self._refresh_public_keys_cache()
            
            keys = list(self._public_keys_cache.values())
            
            if active_only:
                keys = [key for key in keys if key.is_active]
            
            # Filtrar chaves expiradas
            now = datetime.utcnow()
            keys = [key for key in keys if not key.expires_at or key.expires_at > now]
            
            logger.info("Retrieved public keys", count=len(keys))
            return keys
            
        except Exception as e:
            logger.error("Failed to get public keys", error=str(e))
            raise
    
    async def revoke_key(self, key_id: str, reason: str = "Manual revocation") -> bool:
        """
        Revogar chave pública
        
        Args:
            key_id: ID da chave para revogar
            reason: Motivo da revogação
            
        Returns:
            True se revogada com sucesso
        """
        logger.info("Revoking public key", key_id=key_id, reason=reason)
        
        try:
            public_key_info = await self._get_public_key(key_id)
            if not public_key_info:
                logger.warning("Key not found for revocation", key_id=key_id)
                return False
            
            # Marcar como inativa
            public_key_info.is_active = False
            public_key_info.description = f"{public_key_info.description or ''} [REVOKED: {reason}]"
            
            # Salvar alteração
            await self._store_public_key(public_key_info)
            
            # Limpar cache
            if key_id in self._public_keys_cache:
                del self._public_keys_cache[key_id]
            
            logger.info("Public key revoked successfully", key_id=key_id)
            return True
            
        except Exception as e:
            logger.error("Failed to revoke key", key_id=key_id, error=str(e))
            raise
    
    async def _get_public_key(self, key_id: str) -> Optional[PublicKeyInfo]:
        """Obter chave pública por ID"""
        if self._should_refresh_cache():
            await self._refresh_public_keys_cache()
        
        return self._public_keys_cache.get(key_id)
    
    async def _store_public_key(self, public_key_info: PublicKeyInfo):
        """Armazenar chave pública (implementar persistência)"""
        # Em produção, salvar no banco de dados
        # Por enquanto, usar cache em memória
        self._public_keys_cache[public_key_info.key_id] = public_key_info
        self._cache_updated_at = datetime.utcnow()
        
        logger.info("Public key stored", key_id=public_key_info.key_id)
    
    async def _refresh_public_keys_cache(self):
        """Atualizar cache de chaves públicas"""
        # Em produção, carregar do banco de dados
        # Por enquanto, manter cache atual
        self._cache_updated_at = datetime.utcnow()
        logger.info("Public keys cache refreshed")
    
    def _should_refresh_cache(self) -> bool:
        """Verificar se cache deve ser atualizado"""
        if not self._cache_updated_at:
            return True
        
        return (datetime.utcnow() - self._cache_updated_at).total_seconds() > self._cache_ttl

# Instância global do serviço
signature_service = SignatureService()    
 
   async def list_public_keys(self, key_type: Optional[str] = None, active_only: bool = True) -> List[Dict]:
        """Listar chaves públicas disponíveis para endpoints públicos"""
        try:
            keys = await self.get_public_keys(active_only=active_only)
            
            result = []
            for key_info in keys:
                if key_type and key_info.key_type != key_type:
                    continue
                    
                result.append({
                    'key_id': key_info.key_id,
                    'key_type': key_info.key_type,
                    'algorithm': key_info.algorithm,
                    'created_at': key_info.created_at,
                    'expires_at': key_info.expires_at,
                    'is_active': key_info.is_active,
                    'usage': key_info.usage or ['verify'],
                    'fingerprint': key_info.fingerprint
                })
            
            logger.info("Listed public keys for API", count=len(result), key_type=key_type, active_only=active_only)
            return result
            
        except Exception as e:
            logger.error("Failed to list public keys for API", error=str(e))
            raise
    
    async def get_public_key(self, key_id: str, format: str = 'pem') -> Optional[Dict]:
        """Obter chave pública específica para endpoints públicos"""
        try:
            key_info = await self._get_public_key(key_id)
            if not key_info:
                return None
            
            result = {
                'key_id': key_info.key_id,
                'key_type': key_info.key_type,
                'algorithm': key_info.algorithm,
                'created_at': key_info.created_at,
                'expires_at': key_info.expires_at,
                'is_active': key_info.is_active,
                'usage': key_info.usage or ['verify'],
                'fingerprint': key_info.fingerprint
            }
            
            if format == 'pem':
                result['public_key'] = key_info.public_key
            elif format == 'jwk':
                # Converter para JWK (implementação simplificada)
                if key_info.key_type == 'rsa':
                    result['public_key'] = {
                        "kty": "RSA",
                        "use": "sig",
                        "key_ops": ["verify"],
                        "alg": key_info.algorithm,
                        "kid": key_info.key_id,
                        # Em implementação real, extrairia n e e da chave PEM
                        "n": "exemplo_modulus_base64url",
                        "e": "AQAB"
                    }
                elif key_info.key_type == 'ecdsa':
                    result['public_key'] = {
                        "kty": "EC",
                        "use": "sig",
                        "key_ops": ["verify"],
                        "alg": key_info.algorithm,
                        "kid": key_info.key_id,
                        "crv": "P-256",
                        "x": "exemplo_x_coordinate",
                        "y": "exemplo_y_coordinate"
                    }
            elif format == 'der':
                # Para DER, converteria PEM para DER e codificaria em base64
                result['public_key'] = "exemplo_der_base64"
            
            logger.info("Retrieved public key for API", key_id=key_id, format=format)
            return result
            
        except Exception as e:
            logger.error("Failed to get public key for API", key_id=key_id, error=str(e))
            raise
    
    async def get_jwks(self) -> Dict:
        """Obter JWKS (JSON Web Key Set) para endpoint padrão"""
        try:
            keys = await self.list_public_keys(active_only=True)
            jwks_keys = []
            
            for key_info in keys:
                if key_info['key_type'] == 'rsa':
                    jwk = {
                        "kty": "RSA",
                        "use": "sig",
                        "key_ops": ["verify"],
                        "alg": key_info['algorithm'],
                        "kid": key_info['key_id'],
                        # Em implementação real, extrairia da chave PEM
                        "n": "exemplo_modulus_base64url",
                        "e": "AQAB"
                    }
                    jwks_keys.append(jwk)
                elif key_info['key_type'] == 'ecdsa':
                    jwk = {
                        "kty": "EC",
                        "use": "sig",
                        "key_ops": ["verify"],
                        "alg": key_info['algorithm'],
                        "kid": key_info['key_id'],
                        "crv": "P-256",
                        "x": "exemplo_x_coordinate",
                        "y": "exemplo_y_coordinate"
                    }
                    jwks_keys.append(jwk)
            
            logger.info("Generated JWKS for API", keys_count=len(jwks_keys))
            return {"keys": jwks_keys}
            
        except Exception as e:
            logger.error("Failed to generate JWKS for API", error=str(e))
            raise
    
    async def get_key_fingerprint(self, key_id: str, algorithm: str = 'sha256') -> Optional[str]:
        """Obter fingerprint de uma chave específica"""
        try:
            key_info = await self._get_public_key(key_id)
            if not key_info:
                return None
            
            # Em implementação real, calcularia o hash da chave
            # Por agora, retorna o fingerprint armazenado ou calcula um exemplo
            if hasattr(key_info, 'fingerprint') and key_info.fingerprint:
                return key_info.fingerprint
            
            # Simular cálculo de fingerprint baseado no algoritmo
            import hashlib
            key_bytes = key_info.public_key.encode('utf-8')
            
            if algorithm == 'sha256':
                return hashlib.sha256(key_bytes).hexdigest()
            elif algorithm == 'sha1':
                return hashlib.sha1(key_bytes).hexdigest()
            elif algorithm == 'md5':
                return hashlib.md5(key_bytes).hexdigest()
            
            logger.info("Generated key fingerprint", key_id=key_id, algorithm=algorithm)
            return None
            
        except Exception as e:
            logger.error("Failed to get key fingerprint", key_id=key_id, error=str(e))
            raise
    
    async def get_supported_algorithms(self) -> Dict[str, List[str]]:
        """Obter algoritmos suportados pelo sistema"""
        return {
            'signature': ['RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512'],
            'hash': ['sha256', 'sha384', 'sha512', 'sha1', 'md5'],
            'key_types': ['rsa', 'ecdsa', 'ed25519']
        }