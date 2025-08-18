"""
Testes para Admin Panel API
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timedelta

from app.main import app
from app.services.admin_service import AdminService

client = TestClient(app)

class TestAdminAPI:
    """Testes para endpoints de administração"""
    
    @pytest.fixture
    def mock_admin_token(self):
        """Mock token de admin válido"""
        return "valid-admin-token"
    
    @pytest.fixture
    def admin_headers(self, mock_admin_token):
        """Headers com token de admin"""
        return {"Authorization": f"Bearer {mock_admin_token}"}
    
    @pytest.fixture
    def mock_admin_service(self):
        """Mock do AdminService"""
        service = AsyncMock(spec=AdminService)
        
        # Mock system stats
        service.get_system_stats.return_value = {
            'total_users': 150,
            'active_users': 89,
            'total_agents': 5,
            'total_workflows': 45,
            'total_executions': 1250,
            'successful_executions': 1180,
            'failed_executions': 70,
            'total_integrations': 12,
            'active_integrations': 10,
            'total_credentials': 78,
            'system_uptime_seconds': 86400,
            'memory_usage_mb': 512,
            'cpu_usage_percent': 25.5,
            'disk_usage_percent': 45.2,
            'database_connections': 15,
            'cache_hit_rate': 85.5,
            'api_requests_per_minute': 245,
            'error_rate_percent': 2.1
        }
        
        # Mock users list
        service.list_users.return_value = [
            {
                'id': 'user-1',
                'email': 'user1@example.com',
                'name': 'User 1',
                'status': 'active',
                'role': 'user',
                'created_at': datetime.utcnow().isoformat(),
                'last_login': datetime.utcnow().isoformat(),
                'total_workflows': 5,
                'total_executions': 25,
                'total_credentials': 3
            }
        ]
        
        # Mock agent stats
        service.get_agent_stats.return_value = {
            'total_agents': 5,
            'active_agents': 5,
            'agents_by_category': {'communication': 1, 'messaging': 2},
            'agents_by_provider': {'google': 1, 'whatsapp': 1},
            'most_used_agents': [{'agent_id': 'sa-whatsapp', 'executions': 450}],
            'agent_success_rates': {'sa-whatsapp': 95.2},
            'avg_execution_time_by_agent': {'sa-whatsapp': 1250},
            'total_agent_executions': 1250
        }
        
        # Mock workflow stats
        service.get_workflow_stats.return_value = {
            'total_workflows': 45,
            'active_workflows': 38,
            'total_executions': 1250,
            'successful_executions': 1180,
            'failed_executions': 70,
            'avg_execution_time_ms': 2500,
            'workflows_by_status': {'active': 38, 'draft': 5},
            'most_executed_workflows': [{'workflow_id': 'wf-1', 'name': 'Test', 'executions': 320}],
            'execution_trends': [{'date': '2024-01-01', 'executions': 45, 'success_rate': 94.2}]
        }
        
        # Mock system health
        service.get_system_health.return_value = {
            'overall_status': 'healthy',
            'database_status': 'healthy',
            'cache_status': 'healthy',
            'agents_status': 'healthy',
            'integrations_status': 'healthy',
            'external_apis_status': 'healthy',
            'disk_space_status': 'healthy',
            'memory_status': 'healthy',
            'last_backup': datetime.utcnow().isoformat(),
            'uptime_seconds': 86400,
            'version': '1.0.0',
            'environment': 'test'
        }
        
        # Mock audit logs
        service.get_audit_logs.return_value = [
            {
                'id': 'log-1',
                'user_id': 'user-1',
                'action': 'login',
                'resource_type': 'user',
                'resource_id': 'user-1',
                'details': {'ip': '192.168.1.1'},
                'ip_address': '192.168.1.1',
                'user_agent': 'Mozilla/5.0',
                'timestamp': datetime.utcnow().isoformat()
            }
        ]
        
        # Mock system config
        service.get_system_config.return_value = {
            'max_workflow_execution_time': 3600,
            'max_concurrent_executions': 10,
            'default_agent_timeout': 300,
            'max_retry_attempts': 3,
            'credential_encryption_enabled': True,
            'audit_logging_enabled': True,
            'rate_limiting_enabled': True,
            'backup_enabled': True,
            'backup_frequency_hours': 24,
            'log_retention_days': 90,
            'maintenance_mode': False,
            'debug_mode': False
        }
        
        # Mock backups
        service.list_backups.return_value = [
            {
                'id': 'backup-1',
                'filename': 'backup-20240101-1.sql',
                'size_bytes': 125500000,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'completed',
                'backup_type': 'full'
            }
        ]
        
        # Mock other methods
        service.update_user_status.return_value = True
        service.update_system_config.return_value = True
        service.create_backup.return_value = {
            'backup_id': 'backup-123',
            'backup_size': '125.5 MB',
            'created_at': datetime.utcnow().isoformat()
        }
        service.set_maintenance_mode.return_value = True
        service.cleanup_system.return_value = {'items_removed': 100, 'space_freed_mb': 50.0}
        service.export_metrics.return_value = {'test': 'data'}
        
        return service
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_get_system_stats(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para obter estatísticas do sistema"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/stats/system", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_users'] == 150
        assert data['active_users'] == 89
        assert data['total_agents'] == 5
        assert data['system_uptime_seconds'] == 86400
        mock_admin_service.get_system_stats.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_list_users(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para listar usuários"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/users?limit=50&offset=0", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['email'] == 'user1@example.com'
        mock_admin_service.list_users.assert_called_once_with(
            limit=50, offset=0, search=None, status_filter=None
        )
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_update_user_status(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para atualizar status do usuário"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        user_id = str(uuid4())
        response = client.put(
            f"/api/v1/admin/users/{user_id}/status?new_status=suspended",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Status do usuário atualizado" in data['message']
        mock_admin_service.update_user_status.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_get_agent_stats(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para obter estatísticas de agentes"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/agents/stats", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_agents'] == 5
        assert data['active_agents'] == 5
        assert 'agents_by_category' in data
        assert 'most_used_agents' in data
        mock_admin_service.get_agent_stats.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_get_workflow_stats(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para obter estatísticas de workflows"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/workflows/stats", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_workflows'] == 45
        assert data['active_workflows'] == 38
        assert data['total_executions'] == 1250
        assert 'execution_trends' in data
        mock_admin_service.get_workflow_stats.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_get_system_health(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para verificar saúde do sistema"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/health", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['overall_status'] == 'healthy'
        assert data['database_status'] == 'healthy'
        assert data['version'] == '1.0.0'
        mock_admin_service.get_system_health.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_get_audit_logs(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para obter logs de auditoria"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/audit-logs?limit=50", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['action'] == 'login'
        assert data[0]['user_id'] == 'user-1'
        mock_admin_service.get_audit_logs.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_get_system_config(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para obter configuração do sistema"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/config", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['max_workflow_execution_time'] == 3600
        assert data['credential_encryption_enabled'] is True
        assert data['maintenance_mode'] is False
        mock_admin_service.get_system_config.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_create_backup(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para criar backup do sistema"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.post("/api/v1/admin/backup", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "Backup criado com sucesso" in data['message']
        assert 'backup_id' in data
        assert 'backup_size' in data
        mock_admin_service.create_backup.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_list_backups(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para listar backups"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/backups", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['filename'] == 'backup-20240101-1.sql'
        assert data[0]['status'] == 'completed'
        mock_admin_service.list_backups.assert_called_once()
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_toggle_maintenance_mode(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para alternar modo de manutenção"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.post("/api/v1/admin/maintenance?enabled=true", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "Modo de manutenção ativado" in data['message']
        mock_admin_service.set_maintenance_mode.assert_called_once_with(True)
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_cleanup_system(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para limpeza do sistema"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.post(
            "/api/v1/admin/cleanup?cleanup_type=logs&days_old=30",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Limpeza de logs concluída" in data['message']
        assert 'items_removed' in data
        assert 'space_freed_mb' in data
        mock_admin_service.cleanup_system.assert_called_once_with('logs', 30)
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    @patch('app.api.v1.admin.get_admin_service')
    def test_export_metrics_json(self, mock_get_service, mock_verify_token, admin_headers, mock_admin_service):
        """Teste para exportar métricas em JSON"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get_service.return_value = mock_admin_service
        
        response = client.get("/api/v1/admin/metrics/export?format=json", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'test' in data
        mock_admin_service.export_metrics.assert_called_once()
    
    def test_admin_endpoints_require_auth(self):
        """Teste que endpoints admin requerem autenticação"""
        response = client.get("/api/v1/admin/stats/system")
        assert response.status_code == 403  # Unauthorized
    
    @patch('app.middleware.admin_auth.verify_admin_token')
    def test_admin_endpoints_require_admin_role(self, mock_verify_token):
        """Teste que endpoints admin requerem role de admin"""
        # Mock token de usuário comum (não admin)
        mock_verify_token.side_effect = Exception("Acesso negado")
        
        headers = {"Authorization": "Bearer user-token"}
        response = client.get("/api/v1/admin/stats/system", headers=headers)
        
        assert response.status_code == 500  # Error from auth middleware

class TestAdminService:
    """Testes para AdminService"""
    
    @pytest.fixture
    def admin_service(self):
        """Fixture do AdminService"""
        return AdminService()
    
    @pytest.mark.asyncio
    async def test_get_system_stats(self, admin_service):
        """Teste para obter estatísticas do sistema"""
        stats = await admin_service.get_system_stats()
        
        assert isinstance(stats, dict)
        assert 'total_users' in stats
        assert 'active_users' in stats
        assert 'total_agents' in stats
        assert 'system_uptime_seconds' in stats
        assert stats['total_users'] > 0
    
    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, admin_service):
        """Teste para listar usuários com paginação"""
        users = await admin_service.list_users(limit=10, offset=0)
        
        assert isinstance(users, list)
        assert len(users) <= 10
        if users:
            assert 'id' in users[0]
            assert 'email' in users[0]
            assert 'status' in users[0]
    
    @pytest.mark.asyncio
    async def test_list_users_with_search(self, admin_service):
        """Teste para listar usuários com busca"""
        users = await admin_service.list_users(search="user1")
        
        assert isinstance(users, list)
        # Verifica se a busca funciona (mock implementation)
        if users:
            assert any("user1" in user['email'].lower() for user in users)
    
    @pytest.mark.asyncio
    async def test_update_user_status_valid(self, admin_service):
        """Teste para atualizar status válido do usuário"""
        user_id = uuid4()
        result = await admin_service.update_user_status(user_id, 'suspended')
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_user_status_invalid(self, admin_service):
        """Teste para atualizar status inválido do usuário"""
        user_id = uuid4()
        
        with pytest.raises(ValueError, match="Status inválido"):
            await admin_service.update_user_status(user_id, 'invalid_status')
    
    @pytest.mark.asyncio
    async def test_get_agent_stats(self, admin_service):
        """Teste para obter estatísticas de agentes"""
        stats = await admin_service.get_agent_stats()
        
        assert isinstance(stats, dict)
        assert 'total_agents' in stats
        assert 'active_agents' in stats
        assert 'agents_by_category' in stats
        assert 'most_used_agents' in stats
        assert isinstance(stats['most_used_agents'], list)
    
    @pytest.mark.asyncio
    async def test_get_system_health(self, admin_service):
        """Teste para verificar saúde do sistema"""
        health = await admin_service.get_system_health()
        
        assert isinstance(health, dict)
        assert 'overall_status' in health
        assert 'database_status' in health
        assert 'uptime_seconds' in health
        assert health['overall_status'] in ['healthy', 'warning', 'error']
    
    @pytest.mark.asyncio
    async def test_export_metrics_json(self, admin_service):
        """Teste para exportar métricas em JSON"""
        metrics = await admin_service.export_metrics(format="json")
        
        assert isinstance(metrics, dict)
        assert 'system_stats' in metrics
        assert 'agent_stats' in metrics
        assert 'export_timestamp' in metrics
    
    @pytest.mark.asyncio
    async def test_export_metrics_csv(self, admin_service):
        """Teste para exportar métricas em CSV"""
        csv_data = await admin_service.export_metrics(format="csv")
        
        assert isinstance(csv_data, str)
        assert 'Metric,Value,Category' in csv_data  # CSV header
        assert 'system' in csv_data  # Category
        assert 'agents' in csv_data  # Category
    
    @pytest.mark.asyncio
    async def test_cleanup_system(self, admin_service):
        """Teste para limpeza do sistema"""
        result = await admin_service.cleanup_system('logs', 30)
        
        assert isinstance(result, dict)
        assert 'items_removed' in result
        assert 'space_freed_mb' in result
        assert result['items_removed'] >= 0
        assert result['space_freed_mb'] >= 0
    
    @pytest.mark.asyncio
    async def test_cleanup_system_invalid_type(self, admin_service):
        """Teste para limpeza com tipo inválido"""
        result = await admin_service.cleanup_system('invalid_type', 30)
        
        assert result['items_removed'] == 0
        assert result['space_freed_mb'] == 0