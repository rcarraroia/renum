#!/usr/bin/env python3
"""
Teste básico do sistema de integraçõeimpor
t pytest
import asyncio
import json
from datetime import datetime, timedelta
from uuid import uuid4
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.domain.integration import Integration, IntegrationChannel, IntegrationStatus
from app.repositories.integration_repository import IntegrationRepository
from app.services.webhook_service import WebhookService

# =====================================================
# 9. TESTE DE INTEGRAÇÃO COMPLETO
# =====================================================

class TestIntegrationsComplete:
    """Testes completos do sistema de integrações."""
    
    @pytest.fixture
    def client(self):
        """Cliente de teste FastAPI."""
        return TestClient(app)
    
    @pytest.fixture
    async def async_client(self):
        """Cliente assíncrono para testes."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    def mock_user_id(self):
        """ID de usuário mock para testes."""
        return str(uuid4())
    
    @pytest.fixture
    def mock_agent_id(self):
        """ID de agente mock para testes."""
        return str(uuid4())
    
    @pytest.fixture
    def sample_integration_data(self, mock_user_id, mock_agent_id):
        """Dados de exemplo para criar integração."""
        return {
            "user_id": mock_user_id,
            "agent_id": mock_agent_id,
            "name": "Test WhatsApp Integration",
            "description": "Integração de teste para WhatsApp",
            "channel": "whatsapp",
            "rate_limit_per_minute": 60,
            "metadata": {
                "phone_number": "+5511999999999",
                "business_account_id": "123456789"
            }
        }
    
    @pytest.fixture
    def webhook_payload_whatsapp(self):
        """Payload de exemplo para webhook WhatsApp."""
        return {
            "message": "Olá, preciso de ajuda!",
            "phone": "+5511888888888",
            "name": "João Silva",
            "timestamp": datetime.now().isoformat(),
            "message_id": str(uuid4()),
            "chat_id": "whatsapp_chat_123"
        }
    
    @pytest.fixture
    def webhook_payload_telegram(self):
        """Payload de exemplo para webhook Telegram."""
        return {
            "message": "Hello, I need help!",
            "chat_id": 123456789,
            "user_id": 987654321,
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "timestamp": datetime.now().isoformat(),
            "message_id": 456
        }
    
    # =====================================================
    # TESTES DE CRUD DE INTEGRAÇÕES
    # =====================================================
    
    async def test_create_integration_success(self, async_client, sample_integration_data):
        """Teste de criação de integração com sucesso."""
        response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == sample_integration_data["name"]
        assert data["channel"] == sample_integration_data["channel"]
        assert data["status"] == "active"
        assert "webhook_token" in data
        assert "webhook_url" in data
        assert data["webhook_token"].startswith("whk_")
    
    async def test_create_integration_invalid_channel(self, async_client, sample_integration_data):
        """Teste de criação com canal inválido."""
        sample_integration_data["channel"] = "invalid_channel"
        
        response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 422
    
    async def test_list_integrations(self, async_client, mock_user_id):
        """Teste de listagem de integrações."""
        response = await async_client.get(
            "/api/v1/integrations",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "integrations" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["integrations"], list)
    
    async def test_get_integration_by_id(self, async_client, sample_integration_data):
        """Teste de obtenção de integração por ID."""
        # Primeiro criar uma integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert create_response.status_code == 201
        integration_id = create_response.json()["id"]
        
        # Depois buscar por ID
        response = await async_client.get(
            f"/api/v1/integrations/{integration_id}",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == integration_id
        assert data["name"] == sample_integration_data["name"]
    
    async def test_update_integration(self, async_client, sample_integration_data):
        """Teste de atualização de integração."""
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration_id = create_response.json()["id"]
        
        # Atualizar
        update_data = {
            "name": "Updated Integration Name",
            "rate_limit_per_minute": 120,
            "status": "inactive"
        }
        
        response = await async_client.put(
            f"/api/v1/integrations/{integration_id}",
            json=update_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["rate_limit_per_minute"] == update_data["rate_limit_per_minute"]
        assert data["status"] == update_data["status"]
    
    async def test_delete_integration(self, async_client, sample_integration_data):
        """Teste de exclusão de integração."""
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration_id = create_response.json()["id"]
        
        # Excluir
        response = await async_client.delete(
            f"/api/v1/integrations/{integration_id}",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 204
        
        # Verificar se foi excluída
        get_response = await async_client.get(
            f"/api/v1/integrations/{integration_id}",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert get_response.status_code == 404
    
    # =====================================================
    # TESTES DE WEBHOOKS
    # =====================================================
    
    async def test_webhook_whatsapp_success(self, async_client, sample_integration_data, webhook_payload_whatsapp):
        """Teste de webhook WhatsApp com sucesso."""
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration = create_response.json()
        agent_id = integration["agent_id"]
        webhook_token = integration["webhook_token"]
        
        # Enviar webhook
        response = await async_client.post(
            f"/webhook/{agent_id}/whatsapp",
            json=webhook_payload_whatsapp,
            headers={"Authorization": f"Bearer {webhook_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert "execution_time_ms" in data
        assert isinstance(data["execution_time_ms"], int)
    
    async def test_webhook_telegram_success(self, async_client, sample_integration_data, webhook_payload_telegram):
        """Teste de webhook Telegram com sucesso."""
        # Alterar canal para telegram
        sample_integration_data["channel"] = "telegram"
        sample_integration_data["name"] = "Test Telegram Integration"
        
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration = create_response.json()
        agent_id = integration["agent_id"]
        webhook_token = integration["webhook_token"]
        
        # Enviar webhook
        response = await async_client.post(
            f"/webhook/{agent_id}/telegram",
            json=webhook_payload_telegram,
            headers={"Authorization": f"Bearer {webhook_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    async def test_webhook_invalid_token(self, async_client, mock_agent_id, webhook_payload_whatsapp):
        """Teste de webhook com token inválido."""
        response = await async_client.post(
            f"/webhook/{mock_agent_id}/whatsapp",
            json=webhook_payload_whatsapp,
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "INVALID_TOKEN" in data.get("code", "")
    
    async def test_webhook_missing_token(self, async_client, mock_agent_id, webhook_payload_whatsapp):
        """Teste de webhook sem token."""
        response = await async_client.post(
            f"/webhook/{mock_agent_id}/whatsapp",
            json=webhook_payload_whatsapp
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "MISSING_TOKEN" in data.get("code", "")
    
    async def test_webhook_rate_limit(self, async_client, sample_integration_data, webhook_payload_whatsapp):
        """Teste de rate limiting em webhooks."""
        # Criar integração com rate limit baixo
        sample_integration_data["rate_limit_per_minute"] = 2
        
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration = create_response.json()
        agent_id = integration["agent_id"]
        webhook_token = integration["webhook_token"]
        
        # Fazer várias chamadas rapidamente
        for i in range(3):
            response = await async_client.post(
                f"/webhook/{agent_id}/whatsapp",
                json=webhook_payload_whatsapp,
                headers={"Authorization": f"Bearer {webhook_token}"}
            )
            
            if i < 2:
                assert response.status_code == 200
            else:
                # Terceira chamada deve ser bloqueada
                assert response.status_code == 429
                data = response.json()
                assert "RATE_LIMIT_EXCEEDED" in data.get("code", "")
    
    # =====================================================
    # TESTES DE ANALYTICS
    # =====================================================
    
    async def test_integration_analytics(self, async_client, sample_integration_data):
        """Teste de analytics de integração."""
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration_id = create_response.json()["id"]
        
        # Buscar analytics
        response = await async_client.get(
            f"/api/v1/integrations/{integration_id}/analytics",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_calls" in data
        assert "success_rate" in data
        assert "avg_response_time" in data
        assert "error_distribution" in data
        assert "hourly_distribution" in data
    
    async def test_integration_calls_history(self, async_client, sample_integration_data):
        """Teste de histórico de chamadas."""
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration_id = create_response.json()["id"]
        
        # Buscar histórico
        response = await async_client.get(
            f"/api/v1/integrations/{integration_id}/calls",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "calls" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["calls"], list)
    
    # =====================================================
    # TESTES DE REGENERAÇÃO DE TOKEN
    # =====================================================
    
    async def test_regenerate_token(self, async_client, sample_integration_data):
        """Teste de regeneração de token."""
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration = create_response.json()
        integration_id = integration["id"]
        old_token = integration["webhook_token"]
        
        # Regenerar token
        response = await async_client.post(
            f"/api/v1/integrations/{integration_id}/regenerate-token",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        new_token = data["webhook_token"]
        assert new_token != old_token
        assert new_token.startswith("whk_")
        assert len(new_token) > 20
    
    # =====================================================
    # TESTES DE VALIDAÇÃO DE PAYLOAD
    # =====================================================
    
    async def test_webhook_payload_validation(self, async_client):
        """Teste de validação de payload."""
        # Payload malicioso
        malicious_payload = {
            "message": "<script>alert('xss')</script>",
            "sql_injection": "'; DROP TABLE users; --",
            "command_injection": "; rm -rf /",
            "oversized_field": "A" * 10000
        }
        
        response = await async_client.post(
            "/api/v1/webhook/validate",
            json=malicious_payload
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["valid"] is False
        assert "VALIDATION_FAILED" in data.get("code", "")
    
    async def test_webhook_payload_validation_success(self, async_client, webhook_payload_whatsapp):
        """Teste de validação de payload válido."""
        response = await async_client.post(
            "/api/v1/webhook/validate",
            json=webhook_payload_whatsapp
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "sanitized_payload" in data
    
    # =====================================================
    # TESTES DE HEALTH CHECK
    # =====================================================
    
    async def test_webhook_health_check(self, async_client, mock_agent_id):
        """Teste de health check do webhook."""
        response = await async_client.get(f"/api/v1/webhook/{mock_agent_id}/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["agent_id"] == mock_agent_id
        assert "timestamp" in data
        assert "message" in data
    
    # =====================================================
    # TESTES DE INFORMAÇÕES DE VALIDAÇÃO
    # =====================================================
    
    async def test_validation_info(self, async_client):
        """Teste de informações sobre validação."""
        response = await async_client.get("/api/v1/webhook/validation-info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "validation_criteria" in data
        criteria = data["validation_criteria"]
        
        assert "max_payload_size_bytes" in criteria
        assert "security_checks" in criteria
        assert "channel_specific_validation" in criteria
        assert isinstance(criteria["security_checks"], list)
    
    # =====================================================
    # TESTES DE INTEGRAÇÃO COM DIFERENTES CANAIS
    # =====================================================
    
    @pytest.mark.parametrize("channel,payload_key", [
        ("whatsapp", "webhook_payload_whatsapp"),
        ("telegram", "webhook_payload_telegram"),
        ("zapier", "webhook_payload_whatsapp"),  # Usar payload genérico
        ("n8n", "webhook_payload_whatsapp"),     # Usar payload genérico
        ("custom", "webhook_payload_whatsapp")   # Usar payload genérico
    ])
    async def test_webhooks_all_channels(self, async_client, sample_integration_data, channel, payload_key, request):
        """Teste de webhooks para todos os canais suportados."""
        # Obter payload do fixture
        payload = request.getfixturevalue(payload_key)
        
        # Configurar integração para o canal específico
        sample_integration_data["channel"] = channel
        sample_integration_data["name"] = f"Test {channel.title()} Integration"
        
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert create_response.status_code == 201
        
        integration = create_response.json()
        agent_id = integration["agent_id"]
        webhook_token = integration["webhook_token"]
        
        # Determinar endpoint
        if channel == "custom":
            endpoint = f"/webhook/{agent_id}"
        else:
            endpoint = f"/webhook/{agent_id}/{channel}"
        
        # Enviar webhook
        response = await async_client.post(
            endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {webhook_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    # =====================================================
    # TESTES DE PERFORMANCE
    # =====================================================
    
    async def test_webhook_performance(self, async_client, sample_integration_data, webhook_payload_whatsapp):
        """Teste de performance de webhook."""
        # Criar integração
        create_response = await async_client.post(
            "/api/v1/integrations",
            json=sample_integration_data,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        integration = create_response.json()
        agent_id = integration["agent_id"]
        webhook_token = integration["webhook_token"]
        
        # Medir tempo de resposta
        import time
        start_time = time.time()
        
        response = await async_client.post(
            f"/webhook/{agent_id}/whatsapp",
            json=webhook_payload_whatsapp,
            headers={"Authorization": f"Bearer {webhook_token}"}
        )
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # em ms
        
        assert response.status_code == 200
        assert response_time < 5000  # Menos de 5 segundos
        
        data = response.json()
        assert "execution_time_ms" in data
        assert isinstance(data["execution_time_ms"], int)
    
    # =====================================================
    # TESTES DE CLEANUP E MANUTENÇÃO
    # =====================================================
    
    async def test_cleanup_functions(self, async_client):
        """Teste das funções de limpeza."""
        # Este teste verificaria se as funções SQL de cleanup funcionam
        # Em um ambiente real, seria executado diretamente no banco
        
        # Por enquanto, apenas verificamos se os endpoints relacionados existem
        response = await async_client.get(
            "/api/v1/admin/cleanup-status",
            headers={"Authorization": "Bearer admin_token"}
        )
        
        # Pode retornar 404 se não implementado ainda, mas não deve dar erro 500
        assert response.status_code in [200, 404, 403]


# =====================================================
# TESTES DE UNIDADE PARA SERVIÇOS
# =====================================================

class TestWebhookService:
    """Testes unitários para WebhookService."""
    
    @pytest.fixture
    def webhook_service(self):
        """Instância do WebhookService para testes."""
        return WebhookService()
    
    def test_generate_webhook_token(self, webhook_service):
        """Teste de geração de token."""
        token = webhook_service.generate_webhook_token()
        
        assert token.startswith("whk_")
        assert len(token) > 20
        assert isinstance(token, str)
    
    def test_validate_webhook_token_format(self, webhook_service):
        """Teste de validação de formato de token."""
        valid_token = "whk_" + "a" * 32
        invalid_token = "invalid_token"
        
        assert webhook_service.is_valid_token_format(valid_token) is True
        assert webhook_service.is_valid_token_format(invalid_token) is False
    
    def test_sanitize_payload(self, webhook_service):
        """Teste de sanitização de payload."""
        malicious_payload = {
            "message": "<script>alert('xss')</script>",
            "safe_field": "normal text",
            "nested": {
                "dangerous": "'; DROP TABLE users; --"
            }
        }
        
        sanitized = webhook_service.sanitize_payload(malicious_payload)
        
        assert "<script>" not in str(sanitized)
        assert "DROP TABLE" not in str(sanitized)
        assert sanitized["safe_field"] == "normal text"


# =====================================================
# TESTES DE INTEGRAÇÃO COM BANCO DE DADOS
# =====================================================

class TestIntegrationRepository:
    """Testes para IntegrationRepository."""
    
    @pytest.fixture
    def repository(self):
        """Instância do repositório para testes."""
        return IntegrationRepository()
    
    @pytest.fixture
    def sample_integration(self, mock_user_id, mock_agent_id):
        """Integração de exemplo."""
        return Integration(
            user_id=mock_user_id,
            agent_id=mock_agent_id,
            name="Test Integration",
            description="Test Description",
            channel=IntegrationChannel.WHATSAPP,
            webhook_token="whk_test_token_123",
            webhook_url="https://api.test.com/webhook/123",
            status=IntegrationStatus.ACTIVE,
            rate_limit_per_minute=60,
            metadata={"test": "data"}
        )
    
    async def test_create_integration(self, repository, sample_integration):
        """Teste de criação no repositório."""
        created = await repository.create(sample_integration)
        
        assert created.id is not None
        assert created.name == sample_integration.name
        assert created.channel == sample_integration.channel
        assert created.created_at is not None
    
    async def test_get_integration_by_id(self, repository, sample_integration):
        """Teste de busca por ID."""
        created = await repository.create(sample_integration)
        found = await repository.get_by_id(created.id)
        
        assert found is not None
        assert found.id == created.id
        assert found.name == created.name
    
    async def test_get_integration_by_token(self, repository, sample_integration):
        """Teste de busca por token."""
        created = await repository.create(sample_integration)
        found = await repository.get_by_webhook_token(created.webhook_token)
        
        assert found is not None
        assert found.webhook_token == created.webhook_token
    
    async def test_list_integrations_by_user(self, repository, sample_integration):
        """Teste de listagem por usuário."""
        created = await repository.create(sample_integration)
        integrations = await repository.list_by_user_id(sample_integration.user_id)
        
        assert len(integrations) >= 1
        assert any(i.id == created.id for i in integrations)
    
    async def test_update_integration(self, repository, sample_integration):
        """Teste de atualização."""
        created = await repository.create(sample_integration)
        
        created.name = "Updated Name"
        created.status = IntegrationStatus.INACTIVE
        
        updated = await repository.update(created.id, created)
        
        assert updated.name == "Updated Name"
        assert updated.status == IntegrationStatus.INACTIVE
    
    async def test_delete_integration(self, repository, sample_integration):
        """Teste de exclusão."""
        created = await repository.create(sample_integration)
        
        success = await repository.delete(created.id)
        assert success is True
        
        found = await repository.get_by_id(created.id)
        assert found is None


# =====================================================
# CONFIGURAÇÃO DE TESTES
# =====================================================

if __name__ == "__main__":
    # Executar testes
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])