"""
Serviço de Cache de Manifests
Implementa cache local com TTL e invalidação automática para manifests de agentes
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
import hashlib

from app.core.config import settings
from app.schemas.agent_manifest import SignedAgentManifest
from app.services.agent_manifest_service import agent_manifest_service

logger = structlog.get_logger(__name__)

class CacheEventType(str, Enum):
    """Tipos de eventos de cache"""
    AGENT_APPROVED = "agent_approved"
    AGENT_DEPRECATED = "agent_deprecated"
    AGENT_REVOKED = "agent_revoked"
    AGENT_UPDATED = "agent_updated"
    CACHE_WARMING = "cache_warming"
    CACHE_INVALIDATION = "cache_invalidation"

@dataclass
class CacheEntry:
    """Entrada do cache de manifest"""
    agent_id: str
    version: str
    manifest: SignedAgentManifest
    cached_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    cache_key: str = ""
    
    def __post_init__(self):
        if not self.cache_key:
            self.cache_key = f"{self.agent_id}:{self.version}"
        if not self.last_accessed:
            self.last_accessed = self.cached_at

@dataclass
class CacheStats:
    """Estatísticas do cache"""
    total_entries: int
    hit_count: int
    miss_count: int
    eviction_count: int
    warming_count: int
    invalidation_count: int
    memory_usage_bytes: int
    hit_rate: float
    
    @property
    def total_requests(self) -> int:
        return self.hit_count + self.miss_count

class ManifestCacheService:
    """Serviço de cache de manifests com TTL e invalidação"""
    
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}
        self.access_frequency: Dict[str, int] = {}
        self.warming_queue: Set[str] = set()
        self.invalidation_queue: Set[str] = set()
        
        # Configurações
        self.default_ttl = timedelta(minutes=settings.MANIFEST_CACHE_TTL_MINUTES or 5)
        self.max_cache_size = settings.MANIFEST_CACHE_MAX_SIZE or 1000
        self.warming_threshold = settings.MANIFEST_CACHE_WARMING_THRESHOLD or 10
        self.cleanup_interval = timedelta(minutes=settings.MANIFEST_CACHE_CLEANUP_INTERVAL or 1)
        
        # Estatísticas
        self.stats = CacheStats(
            total_entries=0,
            hit_count=0,
            miss_count=0,
            eviction_count=0,
            warming_count=0,
            invalidation_count=0,
            memory_usage_bytes=0,
            hit_rate=0.0
        )
        
        # Controle de tarefas
        self._cleanup_task: Optional[asyncio.Task] = None
        self._warming_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Iniciar serviço de cache"""
        if self._running:
            return
        
        self._running = True
        
        # Iniciar tarefas de background
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._warming_task = asyncio.create_task(self._warming_loop())
        
        logger.info(
            "Manifest cache service started",
            default_ttl_minutes=self.default_ttl.total_seconds() / 60,
            max_cache_size=self.max_cache_size,
            warming_threshold=self.warming_threshold
        )
    
    async def stop(self):
        """Parar serviço de cache"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancelar tarefas
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Manifest cache service stopped")
    
    async def get_manifest(self, agent_id: str, version: str = "latest") -> Optional[SignedAgentManifest]:
        """
        Obter manifest do cache ou registry
        
        Args:
            agent_id: ID do agente
            version: Versão do agente (padrão: latest)
            
        Returns:
            Manifest assinado ou None se não encontrado
        """
        cache_key = f"{agent_id}:{version}"
        
        try:
            # Verificar cache primeiro
            cached_entry = await self._get_from_cache(cache_key)
            if cached_entry:
                self.stats.hit_count += 1
                self._update_access_frequency(cache_key)
                
                logger.debug(
                    "Cache hit for manifest",
                    agent_id=agent_id,
                    version=version,
                    cached_at=cached_entry.cached_at
                )
                
                return cached_entry.manifest
            
            # Cache miss - buscar no registry
            self.stats.miss_count += 1
            
            logger.debug(
                "Cache miss for manifest",
                agent_id=agent_id,
                version=version
            )
            
            # Buscar no registry
            manifest = await self._fetch_from_registry(agent_id, version)
            if manifest:
                # Adicionar ao cache
                await self._add_to_cache(agent_id, version, manifest)
                self._update_access_frequency(cache_key)
                
                return manifest
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get manifest",
                agent_id=agent_id,
                version=version,
                error=str(e)
            )
            return None
    
    async def invalidate_manifest(self, agent_id: str, version: Optional[str] = None, reason: str = "manual"):
        """
        Invalidar manifest(s) do cache
        
        Args:
            agent_id: ID do agente
            version: Versão específica ou None para todas
            reason: Motivo da invalidação
        """
        try:
            invalidated_keys = []
            
            if version:
                # Invalidar versão específica
                cache_key = f"{agent_id}:{version}"
                if cache_key in self.cache:
                    del self.cache[cache_key]
                    invalidated_keys.append(cache_key)
            else:
                # Invalidar todas as versões do agente
                keys_to_remove = [
                    key for key in self.cache.keys()
                    if key.startswith(f"{agent_id}:")
                ]
                
                for key in keys_to_remove:
                    del self.cache[key]
                    invalidated_keys.append(key)
            
            self.stats.invalidation_count += len(invalidated_keys)
            
            logger.info(
                "Manifests invalidated",
                agent_id=agent_id,
                version=version,
                invalidated_count=len(invalidated_keys),
                reason=reason
            )
            
            # Atualizar estatísticas
            await self._update_stats()
            
        except Exception as e:
            logger.error(
                "Failed to invalidate manifest",
                agent_id=agent_id,
                version=version,
                error=str(e)
            )
    
    async def warm_cache(self, agent_ids: Optional[List[str]] = None):
        """
        Pré-carregar cache com manifests frequentemente usados
        
        Args:
            agent_ids: Lista de IDs para pré-carregar ou None para automático
        """
        try:
            if agent_ids is None:
                # Usar agentes mais acessados
                agent_ids = await self._get_frequently_used_agents()
            
            warming_tasks = []
            for agent_id in agent_ids:
                task = asyncio.create_task(
                    self._warm_agent_manifest(agent_id)
                )
                warming_tasks.append(task)
            
            # Executar warming em paralelo
            results = await asyncio.gather(*warming_tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            self.stats.warming_count += success_count
            
            logger.info(
                "Cache warming completed",
                requested_agents=len(agent_ids),
                successful_warmings=success_count
            )
            
        except Exception as e:
            logger.error("Failed to warm cache", error=str(e))
    
    async def handle_agent_event(self, event_type: CacheEventType, agent_id: str, version: str = "latest"):
        """
        Processar evento de agente para invalidação/warming
        
        Args:
            event_type: Tipo do evento
            agent_id: ID do agente
            version: Versão do agente
        """
        try:
            logger.info(
                "Processing agent event",
                event_type=event_type,
                agent_id=agent_id,
                version=version
            )
            
            if event_type in [CacheEventType.AGENT_APPROVED, CacheEventType.AGENT_UPDATED]:
                # Invalidar cache existente e fazer warming
                await self.invalidate_manifest(agent_id, version, reason=f"agent_{event_type.value}")
                await self._warm_agent_manifest(agent_id, version)
                
            elif event_type in [CacheEventType.AGENT_DEPRECATED, CacheEventType.AGENT_REVOKED]:
                # Apenas invalidar
                await self.invalidate_manifest(agent_id, version, reason=f"agent_{event_type.value}")
            
        except Exception as e:
            logger.error(
                "Failed to handle agent event",
                event_type=event_type,
                agent_id=agent_id,
                error=str(e)
            )
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do cache"""
        await self._update_stats()
        
        return {
            "cache_stats": asdict(self.stats),
            "cache_entries": len(self.cache),
            "warming_queue_size": len(self.warming_queue),
            "invalidation_queue_size": len(self.invalidation_queue),
            "top_accessed_agents": await self._get_top_accessed_agents(10),
            "cache_health": await self._get_cache_health()
        }
    
    async def clear_cache(self, reason: str = "manual_clear"):
        """Limpar todo o cache"""
        try:
            cleared_count = len(self.cache)
            self.cache.clear()
            self.access_frequency.clear()
            
            logger.info(
                "Cache cleared",
                cleared_entries=cleared_count,
                reason=reason
            )
            
            await self._update_stats()
            
        except Exception as e:
            logger.error("Failed to clear cache", error=str(e))
    
    # Métodos privados
    
    async def _get_from_cache(self, cache_key: str) -> Optional[CacheEntry]:
        """Obter entrada do cache se válida"""
        if cache_key not in self.cache:
            return None
        
        entry = self.cache[cache_key]
        
        # Verificar expiração
        if datetime.utcnow() > entry.expires_at:
            del self.cache[cache_key]
            return None
        
        # Atualizar estatísticas de acesso
        entry.access_count += 1
        entry.last_accessed = datetime.utcnow()
        
        return entry
    
    async def _add_to_cache(self, agent_id: str, version: str, manifest: SignedAgentManifest):
        """Adicionar manifest ao cache"""
        cache_key = f"{agent_id}:{version}"
        now = datetime.utcnow()
        
        # Verificar limite de tamanho
        if len(self.cache) >= self.max_cache_size:
            await self._evict_lru_entries(1)
        
        # Criar entrada
        entry = CacheEntry(
            agent_id=agent_id,
            version=version,
            manifest=manifest,
            cached_at=now,
            expires_at=now + self.default_ttl,
            cache_key=cache_key
        )
        
        self.cache[cache_key] = entry
        
        logger.debug(
            "Manifest added to cache",
            agent_id=agent_id,
            version=version,
            expires_at=entry.expires_at
        )
    
    async def _fetch_from_registry(self, agent_id: str, version: str) -> Optional[SignedAgentManifest]:
        """Buscar manifest no registry"""
        try:
            # Fallback para registry quando cache não disponível
            manifest = await agent_manifest_service.get_manifest(agent_id, version)
            
            if manifest:
                logger.debug(
                    "Manifest fetched from registry",
                    agent_id=agent_id,
                    version=version
                )
            
            return manifest
            
        except Exception as e:
            logger.error(
                "Failed to fetch manifest from registry",
                agent_id=agent_id,
                version=version,
                error=str(e)
            )
            return None
    
    async def _evict_lru_entries(self, count: int):
        """Remover entradas menos recentemente usadas"""
        if not self.cache:
            return
        
        # Ordenar por último acesso
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed or x[1].cached_at
        )
        
        evicted_count = 0
        for cache_key, entry in sorted_entries[:count]:
            del self.cache[cache_key]
            evicted_count += 1
            
            logger.debug(
                "Cache entry evicted",
                agent_id=entry.agent_id,
                version=entry.version,
                last_accessed=entry.last_accessed
            )
        
        self.stats.eviction_count += evicted_count
    
    def _update_access_frequency(self, cache_key: str):
        """Atualizar frequência de acesso"""
        self.access_frequency[cache_key] = self.access_frequency.get(cache_key, 0) + 1
    
    async def _get_frequently_used_agents(self, limit: int = 20) -> List[str]:
        """Obter agentes mais frequentemente usados"""
        # Ordenar por frequência de acesso
        sorted_agents = sorted(
            self.access_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Extrair agent_ids únicos
        agent_ids = []
        seen_agents = set()
        
        for cache_key, frequency in sorted_agents[:limit * 2]:  # Pegar mais para filtrar
            agent_id = cache_key.split(':')[0]
            if agent_id not in seen_agents:
                agent_ids.append(agent_id)
                seen_agents.add(agent_id)
                
                if len(agent_ids) >= limit:
                    break
        
        return agent_ids
    
    async def _warm_agent_manifest(self, agent_id: str, version: str = "latest"):
        """Pré-carregar manifest de um agente"""
        try:
            cache_key = f"{agent_id}:{version}"
            
            # Verificar se já está no cache
            if cache_key in self.cache:
                return
            
            # Buscar e adicionar ao cache
            manifest = await self._fetch_from_registry(agent_id, version)
            if manifest:
                await self._add_to_cache(agent_id, version, manifest)
                
                logger.debug(
                    "Manifest warmed",
                    agent_id=agent_id,
                    version=version
                )
            
        except Exception as e:
            logger.error(
                "Failed to warm manifest",
                agent_id=agent_id,
                version=version,
                error=str(e)
            )
    
    async def _cleanup_loop(self):
        """Loop de limpeza de entradas expiradas"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval.total_seconds())
                await self._cleanup_expired_entries()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))
    
    async def _warming_loop(self):
        """Loop de warming automático"""
        while self._running:
            try:
                # Warming a cada 10 minutos
                await asyncio.sleep(600)
                
                # Fazer warming dos agentes mais usados
                frequently_used = await self._get_frequently_used_agents(10)
                if frequently_used:
                    await self.warm_cache(frequently_used)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in warming loop", error=str(e))
    
    async def _cleanup_expired_entries(self):
        """Limpar entradas expiradas"""
        now = datetime.utcnow()
        expired_keys = []
        
        for cache_key, entry in self.cache.items():
            if now > entry.expires_at:
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(
                "Expired cache entries cleaned",
                cleaned_count=len(expired_keys)
            )
    
    async def _update_stats(self):
        """Atualizar estatísticas do cache"""
        self.stats.total_entries = len(self.cache)
        
        if self.stats.total_requests > 0:
            self.stats.hit_rate = self.stats.hit_count / self.stats.total_requests
        
        # Calcular uso de memória (aproximado)
        memory_usage = 0
        for entry in self.cache.values():
            # Estimativa baseada no tamanho do JSON
            manifest_json = json.dumps(entry.manifest.dict())
            memory_usage += len(manifest_json.encode('utf-8'))
        
        self.stats.memory_usage_bytes = memory_usage
    
    async def _get_top_accessed_agents(self, limit: int) -> List[Dict[str, Any]]:
        """Obter agentes mais acessados"""
        sorted_agents = sorted(
            self.access_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        result = []
        for cache_key, frequency in sorted_agents[:limit]:
            agent_id, version = cache_key.split(':', 1)
            result.append({
                "agent_id": agent_id,
                "version": version,
                "access_frequency": frequency
            })
        
        return result
    
    async def _get_cache_health(self) -> Dict[str, Any]:
        """Obter indicadores de saúde do cache"""
        total_entries = len(self.cache)
        expired_count = 0
        near_expiry_count = 0
        now = datetime.utcnow()
        
        for entry in self.cache.values():
            if now > entry.expires_at:
                expired_count += 1
            elif (entry.expires_at - now).total_seconds() < 60:  # Expira em menos de 1 minuto
                near_expiry_count += 1
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_count,
            "near_expiry_entries": near_expiry_count,
            "hit_rate": self.stats.hit_rate,
            "memory_usage_mb": self.stats.memory_usage_bytes / (1024 * 1024),
            "health_status": "healthy" if self.stats.hit_rate > 0.7 else "degraded"
        }

# Instância global do serviço
manifest_cache_service = ManifestCacheService()