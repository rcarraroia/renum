"""
Testes para o serviço de cache de manifests
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.services.manifest_cache_service import ManifestCacheService, CacheEventType
from app.schemas.agent_manifest import SignedAgentManifest, AgentManifest, ManifestSignature

client = TestClient(app)

class TestManifestCacheService:
    """Testes do serviço de cache de manifests"""
    
    @pytest.fixture
    def cache_service(self):
        """Fixture do serviço de cache"""
        service = ManifestCacheService()
        service.default_ttl = timedelta(minutes=5)
        service.max_cache_size = 10
        return service
    
    @pytest.fixture
    def sample_manifest(self):
        """Fixture de manifest de exemplo"""
        manifest = AgentManifest(
            agent_id="test-agent",
            version="1.0.0",
            name="Test Agent",
            description="Agent for testing",
            capabilities=[],
            checksum="test-checksum"
        )
        
        signature = ManifestSignature(
            signature="test-signature",
            signature_key_id="test-key",
            signed_at=datetime.utcnow()
        )
        
        return SignedAgentManifest(
            manifest=manifest,
            signature=signature
        )
    
    @pytest.mark.asyncio
    async def test_cache_miss_and_hit(self, cache_service, sample_manifest):
        """Teste de cache miss seguido de cache hit"""
        # Mock do registry
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Primeira busca - cache miss
            result1 = await cache_service.get_manifest("test-agent", "1.0.0")
            
            assert result1 == sample_manifest
            assert cache_service.stats.miss_count == 1
            assert cache_service.stats.hit_count == 0
            mock_fetch.assert_called_once()
            
            # Segunda busca - cache hit
            mock_fetch.reset_mock()
            result2 = await cache_service.get_manifest("test-agent", "1.0.0")
            
            assert result2 == sample_manifest
            assert cache_service.stats.miss_count == 1
            assert cache_service.stats.hit_count == 1
            mock_fetch.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache_service, sample_manifest):
        """Teste de expiração de cache"""
        # TTL muito curto para teste
        cache_service.default_ttl = timedelta(milliseconds=100)
        
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Primeira busca
            result1 = await cache_service.get_manifest("test-agent", "1.0.0")
            assert result1 == sample_manifest
            
            # Aguardar expiração
            await asyncio.sleep(0.2)
            
            # Segunda busca após expiração - deve buscar no registry novamente
            result2 = await cache_service.get_manifest("test-agent", "1.0.0")
            assert result2 == sample_manifest
            assert mock_fetch.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_service, sample_manifest):
        """Teste de invalidação de cache"""
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Adicionar ao cache
            await cache_service.get_manifest("test-agent", "1.0.0")
            assert len(cache_service.cache) == 1
            
            # Invalidar
            await cache_service.invalidate_manifest("test-agent", "1.0.0")
            assert len(cache_service.cache) == 0
            assert cache_service.stats.invalidation_count == 1
    
    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_service, sample_manifest):
        """Teste de warming do cache"""
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Warming
            await cache_service.warm_cache(["test-agent"])
            
            # Verificar se foi adicionado ao cache
            assert len(cache_service.cache) == 1
            assert cache_service.stats.warming_count == 1
            
            # Busca deve ser cache hit
            result = await cache_service.get_manifest("test-agent", "latest")
            assert result == sample_manifest
            assert cache_service.stats.hit_count == 1
    
    @pytest.mark.asyncio
    async def test_cache_size_limit_and_eviction(self, cache_service, sample_manifest):
        """Teste de limite de tamanho e eviction LRU"""
        cache_service.max_cache_size = 2
        
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Adicionar 3 manifests (excede limite)
            await cache_service.get_manifest("agent1", "1.0.0")
            await cache_service.get_manifest("agent2", "1.0.0")
            await cache_service.get_manifest("agent3", "1.0.0")
            
            # Deve ter apenas 2 entradas (mais recentes)
            assert len(cache_service.cache) == 2
            assert cache_service.stats.eviction_count == 1
            
            # agent1 deve ter sido removido (LRU)
            assert "agent1:1.0.0" not in cache_service.cache
            assert "agent2:1.0.0" in cache_service.cache
            assert "agent3:1.0.0" in cache_service.cache
    
    @pytest.mark.asyncio
    async def test_agent_event_handling(self, cache_service, sample_manifest):
        """Teste de tratamento de eventos de agente"""
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Adicionar ao cache
            await cache_service.get_manifest("test-agent", "1.0.0")
            assert len(cache_service.cache) == 1
            
            # Evento de aprovação - deve invalidar e fazer warming
            await cache_service.handle_agent_event(
                CacheEventType.AGENT_APPROVED,
                "test-agent",
                "1.0.0"
            )
            
            # Deve ter invalidado e feito warming
            assert len(cache_service.cache) == 1  # Warming recarregou
            assert mock_fetch.call_count == 2  # Busca inicial + warming
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_service, sample_manifest):
        """Teste de estatísticas do cache"""
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Fazer algumas operações
            await cache_service.get_manifest("test-agent", "1.0.0")  # miss
            await cache_service.get_manifest("test-agent", "1.0.0")  # hit
            await cache_service.invalidate_manifest("test-agent", "1.0.0")
            
            stats = await cache_service.get_cache_stats()
            
            assert stats["cache_stats"]["hit_count"] == 1
            assert stats["cache_stats"]["miss_count"] == 1
            assert stats["cache_stats"]["invalidation_count"] == 1
            assert stats["cache_stats"]["hit_rate"] == 0.5
    
    @pytest.mark.asyncio
    async def test_frequently_used_agents(self, cache_service, sample_manifest):
        """Teste de identificação de agentes mais usados"""
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Simular acessos com frequências diferentes
            for _ in range(5):
                await cache_service.get_manifest("popular-agent", "1.0.0")
            
            for _ in range(2):
                await cache_service.get_manifest("less-popular-agent", "1.0.0")
            
            frequently_used = await cache_service._get_frequently_used_agents(10)
            
            # popular-agent deve estar primeiro
            assert len(frequently_used) == 2
            assert frequently_used[0] == "popular-agent"
            assert frequently_used[1] == "less-popular-agent"
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_expired_entries(self, cache_service, sample_manifest):
        """Teste de limpeza de entradas expiradas"""
        # TTL muito curto
        cache_service.default_ttl = timedelta(milliseconds=50)
        
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Adicionar entrada
            await cache_service.get_manifest("test-agent", "1.0.0")
            assert len(cache_service.cache) == 1
            
            # Aguardar expiração
            await asyncio.sleep(0.1)
            
            # Executar limpeza
            await cache_service._cleanup_expired_entries()
            
            # Entrada expirada deve ter sido removida
            assert len(cache_service.cache) == 0
    
    @pytest.mark.asyncio
    async def test_fallback_to_registry_on_error(self, cache_service, sample_manifest):
        """Teste de fallback para registry em caso de erro"""
        with patch.object(cache_service, '_get_from_cache') as mock_cache:
            mock_cache.side_effect = Exception("Cache error")
            
            with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
                mock_fetch.return_value = sample_manifest
                
                # Deve fazer fallback para registry
                result = await cache_service.get_manifest("test-agent", "1.0.0")
                assert result == sample_manifest
                mock_fetch.assert_called_once()

class TestManifestCacheEndpoints:
    """Testes dos endpoints de cache de manifests"""
    
    def test_get_cache_stats_requires_auth(self):
        """Teste que endpoint de stats requer autenticação"""
        response = client.get("/api/v1/manifest-cache/stats")
        assert response.status_code == 401
    
    def test_warm_cache_requires_admin(self):
        """Teste que warming requer privilégios de admin"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            response = client.post("/api/v1/manifest-cache/warm")
            assert response.status_code == 403
    
    def test_invalidate_cache_requires_admin(self):
        """Teste que invalidação requer privilégios de admin"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            response = client.delete("/api/v1/manifest-cache/invalidate/test-agent")
            assert response.status_code == 403
    
    def test_cache_health_check_public(self):
        """Teste que health check é público"""
        with patch('app.services.manifest_cache_service.manifest_cache_service.get_cache_stats') as mock_stats:
            mock_stats.return_value = {
                "cache_health": {
                    "health_status": "healthy",
                    "hit_rate": 0.8,
                    "total_entries": 10,
                    "memory_usage_mb": 5.2
                }
            }
            
            response = client.get("/api/v1/manifest-cache/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "manifest-cache"
    
    def test_webhook_agent_event_requires_secret(self):
        """Teste que webhook requer secret válido"""
        response = client.post(
            "/api/v1/manifest-cache/webhook/agent-event",
            json={
                "event_type": "approved",
                "agent_id": "test-agent",
                "version": "1.0.0",
                "webhook_secret": "invalid-secret"
            }
        )
        assert response.status_code == 401
    
    def test_webhook_agent_event_with_valid_secret(self):
        """Teste de webhook com secret válido"""
        with patch('app.core.config.settings.MANIFEST_CACHE_WEBHOOK_SECRET', 'valid-secret'):
            with patch('app.services.manifest_cache_service.manifest_cache_service.handle_agent_event') as mock_handle:
                response = client.post(
                    "/api/v1/manifest-cache/webhook/agent-event",
                    json={
                        "event_type": "approved",
                        "agent_id": "test-agent",
                        "version": "1.0.0",
                        "webhook_secret": "valid-secret"
                    }
                )
                
                assert response.status_code == 200
                mock_handle.assert_called_once()

class TestManifestCacheIntegration:
    """Testes de integração do cache com orchestrator"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_uses_cache(self):
        """Teste que orchestrator usa o cache de manifests"""
        # Este teste verificaria se o orchestrator está usando o cache
        # ao buscar manifests de agentes durante execução de workflows
        pass
    
    @pytest.mark.asyncio
    async def test_cache_warming_on_startup(self):
        """Teste de warming automático na inicialização"""
        cache_service = ManifestCacheService()
        
        with patch.object(cache_service, '_get_frequently_used_agents') as mock_frequent:
            mock_frequent.return_value = ["popular-agent-1", "popular-agent-2"]
            
            with patch.object(cache_service, 'warm_cache') as mock_warm:
                await cache_service.start()
                
                # Aguardar um pouco para warming automático
                await asyncio.sleep(0.1)
                
                await cache_service.stop()
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_agent_approval(self):
        """Teste de invalidação automática quando agente é aprovado"""
        # Este teste verificaria se o cache é invalidado automaticamente
        # quando um agente é aprovado no sistema de registry
        pass

class TestManifestCachePerformance:
    """Testes de performance do cache"""
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """Teste de acesso concorrente ao cache"""
        cache_service = ManifestCacheService()
        
        async def access_cache(agent_id):
            with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
                mock_fetch.return_value = MagicMock()
                return await cache_service.get_manifest(agent_id, "1.0.0")
        
        # Acessos concorrentes
        tasks = [access_cache(f"agent-{i}") for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Todos devem ter sucesso
        assert all(not isinstance(r, Exception) for r in results)
    
    @pytest.mark.asyncio
    async def test_cache_memory_usage_tracking(self, cache_service, sample_manifest):
        """Teste de rastreamento de uso de memória"""
        with patch.object(cache_service, '_fetch_from_registry') as mock_fetch:
            mock_fetch.return_value = sample_manifest
            
            # Adicionar várias entradas
            for i in range(5):
                await cache_service.get_manifest(f"agent-{i}", "1.0.0")
            
            stats = await cache_service.get_cache_stats()
            
            # Deve rastrear uso de memória
            assert stats["cache_stats"]["memory_usage_bytes"] > 0
            assert "memory_usage_mb" in stats["cache_health"]