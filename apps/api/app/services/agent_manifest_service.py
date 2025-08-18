"""
Serviço de Gerenciamento de Manifestos de Agentes
Gerencia criação, assinatura, verificação e aprovação de manifestos
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
import structlog

from app.core.config import settings
from app.schemas.agent_manifest import (
    AgentManifest,
    AgentManifestCore,
    AgentManifestSignature,
    AgentStatus,
    CreateAgentManifestRequest,
    SignAgentManifestRequest,
    VerifyAgentManifestRequest,
    AgentManifestResponse
)
from app.services.signature_service import signature_service

logger = structlog.get_logger(__name__)

class AgentManifestService:
    """Serviço para gerenciamento de manifestos de agentes"""
    
    def __init__(self):
        # Cache de manifestos em memória (em produção, usar banco de dados)
        self._manifests_cache: Dict[str, AgentManifest] = {}
        
        # Configurações
        self.require_signature = settings.AGENT_MANIFEST_REQUIRE_SIGNATURE or True
        self.auto_approve_signed = settings.AGENT_MANIFEST_AUTO_APPROVE_SIGNED or False
    
    async def create_manifest(
        self, 
        request: CreateAgentManifestRequest, 
        created_by: str
    ) -> AgentManifest:
        """
        Criar novo manifesto de agente
        
        Args:
            request: Dados do manifesto
            created_by: Usuário que está criando
            
        Returns:
            Manifesto criado (não assinado)
        """
        logger.info("Creating agent manifest", 
                   agent_id=request.manifest.agent_id,
                   version=request.manifest.version,
                   created_by=created_by)
        
        try:
            # Verificar se já existe manifesto para esta versão
            existing_key = f"{request.manifest.agent_id}:{request.manifest.version}"
            if existing_key in self._manifests_cache:
                raise ValueError(f"Manifest already exists for {request.manifest.agent_id} v{request.manifest.version}")
            
            # Calcular hash do conteúdo
            content_hash = request.manifest.calculate_content_hash()
            
            # Criar assinatura temporária (será substituída na assinatura real)
            temp_signature = AgentManifestSignature(
                algorithm="RS256",
                signature="UNSIGNED",
                signature_key_id="temp",
                signed_at=datetime.utcnow(),
                signed_by=created_by
            )
            
            # Criar manifesto
            manifest = AgentManifest(
                schema_version="1.0.0",
                manifest=request.manifest,
                signature=temp_signature,
                status=AgentStatus.DRAFT,
                content_hash=content_hash
            )
            
            # Salvar manifesto
            await self._store_manifest(manifest)
            
            logger.info("Agent manifest created successfully", 
                       agent_id=request.manifest.agent_id,
                       version=request.manifest.version)
            
            return manifest
            
        except Exception as e:
            logger.error("Failed to create manifest", 
                        agent_id=request.manifest.agent_id,
                        error=str(e))
            raise
    
    async def sign_manifest(
        self, 
        request: SignAgentManifestRequest, 
        private_key_pem: str,
        signed_by: str
    ) -> AgentManifest:
        """
        Assinar manifesto de agente
        
        Args:
            request: Request de assinatura
            private_key_pem: Chave privada para assinatura
            signed_by: Identificador do signatário
            
        Returns:
            Manifesto assinado
        """
        logger.info("Signing agent manifest", 
                   agent_id=request.agent_id,
                   version=request.version,
                   key_id=request.private_key_id)
        
        try:
            # Buscar manifesto
            manifest = await self.get_manifest(request.agent_id, request.version)
            if not manifest:
                raise ValueError(f"Manifest not found: {request.agent_id} v{request.version}")
            
            if manifest.signature.signature != "UNSIGNED":
                raise ValueError("Manifest is already signed")
            
            # Assinar manifesto
            signature = await signature_service.sign_manifest(
                manifest.manifest,
                private_key_pem,
                request.private_key_id,
                signed_by
            )
            
            # Atualizar manifesto com assinatura
            manifest.signature = signature
            
            # Auto-aprovar se configurado
            if self.auto_approve_signed:
                manifest.status = AgentStatus.APPROVED
                manifest.approved_by = signed_by
                manifest.approved_at = datetime.utcnow()
                
                logger.info("Manifest auto-approved after signing", 
                           agent_id=request.agent_id,
                           version=request.version)
            
            # Salvar manifesto atualizado
            await self._store_manifest(manifest)
            
            logger.info("Agent manifest signed successfully", 
                       agent_id=request.agent_id,
                       version=request.version,
                       key_id=request.private_key_id)
            
            return manifest
            
        except Exception as e:
            logger.error("Failed to sign manifest", 
                        agent_id=request.agent_id,
                        version=request.version,
                        error=str(e))
            raise
    
    async def verify_manifest(self, manifest: AgentManifest) -> Dict[str, Any]:
        """
        Verificar manifesto de agente
        
        Args:
            manifest: Manifesto para verificar
            
        Returns:
            Resultado da verificação
        """
        logger.info("Verifying agent manifest", 
                   agent_id=manifest.manifest.agent_id,
                   version=manifest.manifest.version)
        
        try:
            # Verificar assinatura digital
            verification_result = await signature_service.verify_manifest_signature(manifest)
            
            # Verificações adicionais
            additional_checks = await self._perform_additional_checks(manifest)
            verification_result["additional_checks"] = additional_checks
            
            # Determinar status geral
            all_valid = (
                verification_result["valid"] and 
                all(additional_checks.values())
            )
            
            verification_result["overall_valid"] = all_valid
            
            logger.info("Manifest verification completed", 
                       agent_id=manifest.manifest.agent_id,
                       version=manifest.manifest.version,
                       valid=all_valid)
            
            return verification_result
            
        except Exception as e:
            logger.error("Failed to verify manifest", 
                        agent_id=manifest.manifest.agent_id,
                        error=str(e))
            raise
    
    async def approve_manifest(
        self, 
        agent_id: str, 
        version: str, 
        approved_by: str,
        approval_notes: Optional[str] = None
    ) -> AgentManifest:
        """
        Aprovar manifesto de agente
        
        Args:
            agent_id: ID do agente
            version: Versão do agente
            approved_by: Quem está aprovando (superadmin)
            approval_notes: Notas da aprovação
            
        Returns:
            Manifesto aprovado
        """
        logger.info("Approving agent manifest", 
                   agent_id=agent_id,
                   version=version,
                   approved_by=approved_by)
        
        try:
            # Buscar manifesto
            manifest = await self.get_manifest(agent_id, version)
            if not manifest:
                raise ValueError(f"Manifest not found: {agent_id} v{version}")
            
            if manifest.status == AgentStatus.APPROVED:
                raise ValueError("Manifest is already approved")
            
            # Verificar se está assinado (se obrigatório)
            if self.require_signature and manifest.signature.signature == "UNSIGNED":
                raise ValueError("Manifest must be signed before approval")
            
            # Verificar assinatura se presente
            if manifest.signature.signature != "UNSIGNED":
                verification_result = await self.verify_manifest(manifest)
                if not verification_result["overall_valid"]:
                    raise ValueError("Manifest signature verification failed")
            
            # Aprovar manifesto
            manifest.status = AgentStatus.APPROVED
            manifest.approved_by = approved_by
            manifest.approved_at = datetime.utcnow()
            
            # Salvar manifesto aprovado
            await self._store_manifest(manifest)
            
            logger.info("Agent manifest approved successfully", 
                       agent_id=agent_id,
                       version=version,
                       approved_by=approved_by)
            
            return manifest
            
        except Exception as e:
            logger.error("Failed to approve manifest", 
                        agent_id=agent_id,
                        version=version,
                        error=str(e))
            raise
    
    async def deprecate_manifest(
        self, 
        agent_id: str, 
        version: str, 
        deprecated_by: str,
        reason: Optional[str] = None
    ) -> AgentManifest:
        """
        Deprecar manifesto de agente
        
        Args:
            agent_id: ID do agente
            version: Versão do agente
            deprecated_by: Quem está depreciando
            reason: Motivo da depreciação
            
        Returns:
            Manifesto depreciado
        """
        logger.info("Deprecating agent manifest", 
                   agent_id=agent_id,
                   version=version,
                   deprecated_by=deprecated_by,
                   reason=reason)
        
        try:
            # Buscar manifesto
            manifest = await self.get_manifest(agent_id, version)
            if not manifest:
                raise ValueError(f"Manifest not found: {agent_id} v{version}")
            
            if manifest.status == AgentStatus.DEPRECATED:
                raise ValueError("Manifest is already deprecated")
            
            # Deprecar manifesto
            manifest.status = AgentStatus.DEPRECATED
            
            # Salvar manifesto depreciado
            await self._store_manifest(manifest)
            
            logger.info("Agent manifest deprecated successfully", 
                       agent_id=agent_id,
                       version=version,
                       deprecated_by=deprecated_by)
            
            return manifest
            
        except Exception as e:
            logger.error("Failed to deprecate manifest", 
                        agent_id=agent_id,
                        version=version,
                        error=str(e))
            raise
    
    async def get_manifest(self, agent_id: str, version: str) -> Optional[AgentManifest]:
        """
        Obter manifesto específico
        
        Args:
            agent_id: ID do agente
            version: Versão do agente
            
        Returns:
            Manifesto se encontrado
        """
        key = f"{agent_id}:{version}"
        return self._manifests_cache.get(key)
    
    async def list_manifests(
        self, 
        agent_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Listar manifestos com filtros
        
        Args:
            agent_id: Filtrar por ID do agente
            status: Filtrar por status
            page: Página
            per_page: Itens por página
            
        Returns:
            Lista paginada de manifestos
        """
        logger.info("Listing manifests", 
                   agent_id=agent_id,
                   status=status,
                   page=page,
                   per_page=per_page)
        
        try:
            # Filtrar manifestos
            manifests = list(self._manifests_cache.values())
            
            if agent_id:
                manifests = [m for m in manifests if m.manifest.agent_id == agent_id]
            
            if status:
                manifests = [m for m in manifests if m.status == status]
            
            # Ordenar por data de criação (mais recente primeiro)
            manifests.sort(key=lambda m: m.manifest.created_at, reverse=True)
            
            # Paginação
            total = len(manifests)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_manifests = manifests[start_idx:end_idx]
            
            return {
                "manifests": page_manifests,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            logger.error("Failed to list manifests", error=str(e))
            raise
    
    async def get_latest_approved_manifest(self, agent_id: str) -> Optional[AgentManifest]:
        """
        Obter última versão aprovada de um agente
        
        Args:
            agent_id: ID do agente
            
        Returns:
            Manifesto da última versão aprovada
        """
        try:
            # Buscar manifestos aprovados do agente
            manifests = [
                m for m in self._manifests_cache.values()
                if m.manifest.agent_id == agent_id and m.status == AgentStatus.APPROVED
            ]
            
            if not manifests:
                return None
            
            # Ordenar por versão (assumindo versionamento semântico)
            manifests.sort(
                key=lambda m: tuple(map(int, m.manifest.version.split('.'))),
                reverse=True
            )
            
            return manifests[0]
            
        except Exception as e:
            logger.error("Failed to get latest approved manifest", 
                        agent_id=agent_id,
                        error=str(e))
            return None
    
    async def _store_manifest(self, manifest: AgentManifest):
        """Armazenar manifesto (implementar persistência)"""
        key = f"{manifest.manifest.agent_id}:{manifest.manifest.version}"
        self._manifests_cache[key] = manifest
        
        logger.info("Manifest stored", 
                   agent_id=manifest.manifest.agent_id,
                   version=manifest.manifest.version)
    
    async def _perform_additional_checks(self, manifest: AgentManifest) -> Dict[str, bool]:
        """Realizar verificações adicionais do manifesto"""
        checks = {}
        
        try:
            # Verificar se agent_id segue padrão
            checks["agent_id_format"] = manifest.manifest.agent_id.startswith("sa-")
            
            # Verificar se versão é semântica
            version_parts = manifest.manifest.version.split('.')
            checks["semantic_version"] = (
                len(version_parts) >= 3 and 
                all(part.isdigit() for part in version_parts[:3])
            )
            
            # Verificar se tem pelo menos uma capacidade
            checks["has_capabilities"] = len(manifest.manifest.capabilities) > 0
            
            # Verificar se capacidades têm nomes únicos
            capability_names = [cap.name for cap in manifest.manifest.capabilities]
            checks["unique_capability_names"] = len(capability_names) == len(set(capability_names))
            
            # Verificar se tem autor
            checks["has_author"] = bool(manifest.manifest.metadata.author)
            
            # Verificar se checksum do código está presente
            checks["has_code_checksum"] = bool(manifest.manifest.code_checksum)
            
            # Verificar se checksum tem formato correto (SHA256)
            checks["valid_checksum_format"] = (
                len(manifest.manifest.code_checksum) == 64 and
                all(c in '0123456789abcdef' for c in manifest.manifest.code_checksum.lower())
            )
            
            return checks
            
        except Exception as e:
            logger.error("Failed to perform additional checks", error=str(e))
            return {"error": False}

# Instância global do serviço
agent_manifest_service = AgentManifestService()