"""
Testes para sistema de analytics e monitoramento
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timedelta

from app.main import app
from app.services.analytics_service import AnalyticsService, MetricsCollector
from app.services.performance_monitor import PerformanceMonitor, AlertSeverity
from app.services.billing_service import BillingService, BillingTier
from app.services.alerting_service import AlertingService, AlertType

client = TestClient(app)

class TestMetricsCollector:
    """Testes para MetricsCollector"""
    
    @pytest.fixture
    def metrics_collector(self):
        """Fixture do MetricsCollector"""
        return MetricsCollector()
    
    @pytest.mark.asyncio
    async def test_record_metric_memory_fallback(self, metrics_collector):
        """Teste para gravação de métrica em memória"""
        # Force memory fallback
        metrics_collector.redis_client = None
        
        await metrics_collector.record_metric(
            'test_metric',
            42.5,
            {'tag1': 'value1'},
            datetime.utcnow()
        )
        
        # Check if metric was stored in memory
        assert 'test_metric:tag1=value1' in metrics_collector.memory_metrics
        assert len(metrics_collector.memory_metrics['test_metric:tag1=value1']) == 1
    
    @pytest.mark.asyncio
    async def test_increment_counter_memory_fallback(self, metrics_collector):
        """Teste para incremento de contador em memória"""
        # Force memory fallback
        metrics_collector.redis_client = None
        
        await metrics_collector.increment_counter(
            'test_counter',
            5,
            {'tag1': 'value1'}
        )
        
        # Check if counter was incremented in memory
        assert metrics_collector.memory_counters['test_counter:tag1=value1'] == 5
        
        # Increment again
        await metrics_collector.increment_counter(
            'test_counter',
            3,
            {'tag1': 'value1'}
        )
        
        assert metrics_collector.memory_counters['test_counter:tag1=value1'] == 8
    
    @pytest.mark.asyncio
    async def test_get_metric_stats_memory(self, metrics_collector):
        """Teste para obter estatísticas de métrica da memória"""
        # Force memory fallback
        metrics_collector.redis_client = None
        
        # Record some metrics
        now = datetime.utcnow()
        for i in range(5):
            await metrics_collector.record_metric(
                'test_metric',
                float(i * 10),
                timestamp=now - timedelta(minutes=i)
            )
        
        # Get stats
        stats = await metrics_collector.get_metric_stats(
            'test_metric',
            now - timedelta(minutes=10),
            now + timedelta(minutes=1)
        )
        
        assert stats['count'] == 5
        assert stats['sum'] == 100.0  # 0 + 10 + 20 + 30 + 40
        assert stats['avg'] == 20.0
        assert stats['min'] == 0.0
        assert stats['max'] == 40.0
    
    @pytest.mark.asyncio
    async def test_get_counter_value_memory(self, metrics_collector):
        """Teste para obter valor de contador da memória"""
        # Force memory fallback
        metrics_collector.redis_client = None
        
        # Increment counter
        await metrics_collector.increment_counter('test_counter', 15)
        
        # Get value
        value = await metrics_collector.get_counter_value('test_counter')
        assert value == 15

class TestAnalyticsService:
    """Testes para AnalyticsService"""
    
    @pytest.fixture
    def analytics_service(self):
        """Fixture do AnalyticsService"""
        return AnalyticsService()
    
    @pytest.mark.asyncio
    async def test_record_integration_metric(self, analytics_service):
        """Teste para gravação de métrica de integração"""
        integration_id = uuid4()
        
        with patch.object(analytics_service.metrics_collector, 'record_metric') as mock_record:
            await analytics_service.record_integration_metric(
                integration_id,
                'webhook_processing',
                1250.5,
                {'provider': 'whatsapp'}
            )
            
            mock_record.assert_called_once()
            args, kwargs = mock_record.call_args
            assert args[0] == 'integration_metric'
            assert args[1] == 1250.5
            assert kwargs['tags']['integration_id'] == str(integration_id)
            assert kwargs['tags']['metric_type'] == 'webhook_processing'
            assert kwargs['tags']['provider'] == 'whatsapp'
    
    @pytest.mark.asyncio
    async def test_record_webhook_processing(self, analytics_service):
        """Teste para gravação de processamento de webhook"""
        integration_id = uuid4()
        
        with patch.object(analytics_service.metrics_collector, 'record_metric') as mock_record, \
             patch.object(analytics_service.metrics_collector, 'increment_counter') as mock_increment:
            
            await analytics_service.record_webhook_processing(
                integration_id,
                'whatsapp',
                1250.0,
                True,
                1024
            )
            
            # Check that metrics were recorded
            assert mock_record.call_count == 2  # processing_time and payload_size
            assert mock_increment.call_count == 2  # total and success counters
    
    @pytest.mark.asyncio
    async def test_record_agent_execution(self, analytics_service):
        """Teste para gravação de execução de agente"""
        execution_id = uuid4()
        
        with patch.object(analytics_service.metrics_collector, 'record_metric') as mock_record, \
             patch.object(analytics_service.metrics_collector, 'increment_counter') as mock_increment:
            
            await analytics_service.record_agent_execution(
                'sa-whatsapp',
                execution_id,
                2500.0,
                True,
                cost_cents=5.0
            )
            
            # Check that metrics were recorded
            assert mock_record.call_count == 2  # execution_time and cost
            assert mock_increment.call_count == 2  # total and success counters
    
    @pytest.mark.asyncio
    async def test_get_integration_analytics(self, analytics_service):
        """Teste para obter analytics de integração"""
        integration_id = uuid4()
        start_time = datetime.utcnow() - timedelta(hours=24)
        end_time = datetime.utcnow()
        
        with patch.object(analytics_service.metrics_collector, 'get_metric_stats') as mock_stats, \
             patch.object(analytics_service.metrics_collector, 'get_counter_value') as mock_counter:
            
            mock_stats.return_value = {
                'count': 10,
                'sum': 12500,
                'avg': 1250,
                'min': 800,
                'max': 2000,
                'median': 1200
            }
            mock_counter.side_effect = [45, 5]  # success_count, error_count
            
            analytics = await analytics_service.get_integration_analytics(
                integration_id, start_time, end_time
            )
            
            assert analytics['integration_id'] == str(integration_id)
            assert analytics['success_count'] == 45
            assert analytics['error_count'] == 5
            assert analytics['total_count'] == 50
            assert analytics['success_rate_percent'] == 90.0

class TestPerformanceMonitor:
    """Testes para PerformanceMonitor"""
    
    @pytest.fixture
    def performance_monitor(self):
        """Fixture do PerformanceMonitor"""
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_record_agent_execution_performance(self, performance_monitor):
        """Teste para gravação de performance de execução de agente"""
        execution_id = uuid4()
        start_time = datetime.utcnow() - timedelta(seconds=5)
        end_time = datetime.utcnow()
        
        with patch('app.services.performance_monitor.analytics_service') as mock_analytics:
            await performance_monitor.record_agent_execution_performance(
                'sa-whatsapp',
                execution_id,
                start_time,
                end_time,
                True,
                memory_usage_mb=256.5,
                cost_cents=3.0
            )
            
            # Check that analytics service was called
            mock_analytics.record_agent_execution.assert_called_once()
            mock_analytics.metrics_collector.record_metric.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_threshold_warning(self, performance_monitor):
        """Teste para verificação de threshold de warning"""
        # Test CPU threshold
        await performance_monitor._check_threshold('cpu_usage_percent', 85.0)
        
        # Should create an alert
        assert len(performance_monitor.active_alerts) == 1
        alert = list(performance_monitor.active_alerts.values())[0]
        assert alert.severity == AlertSeverity.MEDIUM
        assert 'cpu_usage_percent' in alert.details['metric_name']
    
    @pytest.mark.asyncio
    async def test_check_threshold_critical(self, performance_monitor):
        """Teste para verificação de threshold crítico"""
        # Test memory threshold
        await performance_monitor._check_threshold('memory_usage_percent', 97.0)
        
        # Should create a critical alert
        assert len(performance_monitor.active_alerts) == 1
        alert = list(performance_monitor.active_alerts.values())[0]
        assert alert.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_get_performance_summary(self, performance_monitor):
        """Teste para obter resumo de performance"""
        with patch('app.services.performance_monitor.analytics_service') as mock_analytics:
            mock_analytics.get_system_analytics.return_value = {
                'api_requests': {'total': 1000, 'errors': 50},
                'agent_executions': {'total': 500, 'successful': 475}
            }
            mock_analytics.metrics_collector.get_metric_stats.return_value = {
                'count': 10, 'avg': 75.5, 'max': 95.0
            }
            
            summary = await performance_monitor.get_performance_summary(24)
            
            assert 'period' in summary
            assert 'system_analytics' in summary
            assert 'active_alerts' in summary
            assert 'system_resources' in summary

class TestBillingService:
    """Testes para BillingService"""
    
    @pytest.fixture
    def billing_service(self):
        """Fixture do BillingService"""
        return BillingService()
    
    @pytest.mark.asyncio
    async def test_record_agent_execution_cost(self, billing_service):
        """Teste para gravação de custo de execução de agente"""
        user_id = uuid4()
        execution_id = uuid4()
        
        with patch.object(billing_service, '_store_cost_item') as mock_store:
            cost = await billing_service.record_agent_execution_cost(
                user_id,
                'sa-whatsapp',
                execution_id,
                True,
                2500.0  # 2.5 seconds
            )
            
            # Should be base cost (1 cent for sa-whatsapp)
            assert cost == 1
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_agent_execution_cost_long_execution(self, billing_service):
        """Teste para custo de execução longa"""
        user_id = uuid4()
        execution_id = uuid4()
        
        with patch.object(billing_service, '_store_cost_item') as mock_store:
            cost = await billing_service.record_agent_execution_cost(
                user_id,
                'sa-whatsapp',
                execution_id,
                True,
                15000.0  # 15 seconds (long execution)
            )
            
            # Should be base cost * time multiplier (1 * 1.5 = 1.5, rounded to 1)
            assert cost == 1  # int(1 * 1.5) = 1
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_agent_execution_cost_failed(self, billing_service):
        """Teste para custo de execução falhada"""
        user_id = uuid4()
        execution_id = uuid4()
        
        with patch.object(billing_service, '_store_cost_item') as mock_store:
            cost = await billing_service.record_agent_execution_cost(
                user_id,
                'sa-whatsapp',
                execution_id,
                False,  # Failed execution
                2500.0
            )
            
            # Should be base cost * success multiplier (1 * 0.5 = 0.5, rounded to 0)
            assert cost == 0  # int(1 * 0.5) = 0
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_billing_summary(self, billing_service):
        """Teste para obter resumo de billing do usuário"""
        user_id = uuid4()
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch('app.services.billing_service.analytics_service') as mock_analytics:
            mock_analytics.metrics_collector.get_metric_stats.return_value = {
                'count': 10, 'sum': 150, 'avg': 15
            }
            mock_analytics.metrics_collector.get_counter_value.side_effect = [50, 500, 25]
            
            summary = await billing_service.get_user_billing_summary(
                user_id, start_date, end_date, BillingTier.FREE
            )
            
            assert summary['user_id'] == str(user_id)
            assert summary['tier'] == 'free'
            assert 'usage' in summary
            assert 'costs' in summary
            assert 'cost_breakdown' in summary
    
    @pytest.mark.asyncio
    async def test_estimate_monthly_cost(self, billing_service):
        """Teste para estimativa de custo mensal"""
        user_id = uuid4()
        
        estimate = await billing_service.estimate_monthly_cost(
            user_id,
            BillingTier.STARTER,
            2000,  # executions
            15000  # api requests
        )
        
        assert estimate['user_id'] == str(user_id)
        assert estimate['tier'] == 'starter'
        assert 'projected_usage' in estimate
        assert 'estimated_costs' in estimate
        assert 'cost_savings_by_tier' in estimate

class TestAlertingService:
    """Testes para AlertingService"""
    
    @pytest.fixture
    def alerting_service(self):
        """Fixture do AlertingService"""
        return AlertingService()
    
    @pytest.mark.asyncio
    async def test_create_custom_alert(self, alerting_service):
        """Teste para criação de alerta customizado"""
        alert_id = await alerting_service.create_custom_alert(
            "Test Alert",
            "This is a test alert",
            AlertSeverity.MEDIUM,
            {'test_key': 'test_value'}
        )
        
        assert alert_id in alerting_service.active_alerts
        alert = alerting_service.active_alerts[alert_id]
        assert alert.title == "Test Alert"
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.details['test_key'] == 'test_value'
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, alerting_service):
        """Teste para reconhecimento de alerta"""
        # Create alert first
        alert_id = await alerting_service.create_custom_alert(
            "Test Alert",
            "Test message",
            AlertSeverity.LOW
        )
        
        user_id = uuid4()
        success = await alerting_service.acknowledge_alert(
            alert_id, user_id, "Acknowledged by test"
        )
        
        assert success is True
        alert = alerting_service.active_alerts[alert_id]
        assert alert.acknowledged_by == user_id
        assert alert.details['acknowledgment_note'] == "Acknowledged by test"
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, alerting_service):
        """Teste para resolução de alerta"""
        # Create alert first
        alert_id = await alerting_service.create_custom_alert(
            "Test Alert",
            "Test message",
            AlertSeverity.LOW
        )
        
        user_id = uuid4()
        success = await alerting_service.resolve_alert(
            alert_id, user_id, "Resolved by test"
        )
        
        assert success is True
        assert alert_id not in alerting_service.active_alerts
        assert len(alerting_service.alert_history) == 1
        
        resolved_alert = alerting_service.alert_history[0]
        assert resolved_alert.resolved_by == user_id
        assert resolved_alert.details['resolution_note'] == "Resolved by test"
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, alerting_service):
        """Teste para obter alertas ativos"""
        # Create some alerts
        await alerting_service.create_custom_alert(
            "High Severity Alert", "Test", AlertSeverity.HIGH
        )
        await alerting_service.create_custom_alert(
            "Low Severity Alert", "Test", AlertSeverity.LOW
        )
        
        # Get all alerts
        all_alerts = await alerting_service.get_active_alerts()
        assert len(all_alerts) == 2
        
        # Get only high severity alerts
        high_alerts = await alerting_service.get_active_alerts(severity=AlertSeverity.HIGH)
        assert len(high_alerts) == 1
        assert high_alerts[0]['severity'] == 'high'
    
    @pytest.mark.asyncio
    async def test_get_alert_statistics(self, alerting_service):
        """Teste para obter estatísticas de alertas"""
        # Create some alerts
        await alerting_service.create_custom_alert("Alert 1", "Test", AlertSeverity.HIGH)
        await alerting_service.create_custom_alert("Alert 2", "Test", AlertSeverity.LOW)
        
        stats = await alerting_service.get_alert_statistics(24)
        
        assert stats['total_alerts'] == 2
        assert stats['active_alerts'] == 2
        assert stats['resolved_alerts'] == 0
        assert 'alerts_by_severity' in stats
        assert stats['alerts_by_severity']['high'] == 1
        assert stats['alerts_by_severity']['low'] == 1

class TestAnalyticsAPI:
    """Testes para Analytics API endpoints"""
    
    @pytest.fixture
    def mock_admin_token(self):
        """Mock token de admin válido"""
        return "valid-admin-token"
    
    @pytest.fixture
    def admin_headers(self, mock_admin_token):
        """Headers com token de admin"""
        return {"Authorization": f"Bearer {mock_admin_token}"}
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_get_integration_analytics(self, mock_get_user, admin_headers):
        """Teste para endpoint de analytics de integração"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        integration_id = str(uuid4())
        
        with patch('app.api.v1.analytics.analytics_service') as mock_service:
            mock_service.get_integration_analytics.return_value = {
                'integration_id': integration_id,
                'period': {'start': '2024-01-01T00:00:00', 'end': '2024-01-02T00:00:00'},
                'webhook_processing': {'count': 10, 'avg': 1250},
                'success_count': 45,
                'error_count': 5,
                'total_count': 50,
                'success_rate_percent': 90.0
            }
            
            response = client.get(
                f"/api/v1/analytics/integrations/{integration_id}",
                headers=admin_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['integration_id'] == integration_id
            assert data['success_rate_percent'] == 90.0
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_get_agent_analytics(self, mock_get_user, admin_headers):
        """Teste para endpoint de analytics de agente"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        with patch('app.api.v1.analytics.analytics_service') as mock_service:
            mock_service.get_agent_analytics.return_value = {
                'agent_id': 'sa-whatsapp',
                'period': {'start': '2024-01-01T00:00:00', 'end': '2024-01-02T00:00:00'},
                'execution_stats': {'count': 20, 'avg': 1500},
                'cost_stats': {'count': 20, 'sum': 40},
                'success_count': 18,
                'error_count': 2,
                'total_count': 20,
                'success_rate_percent': 90.0
            }
            
            response = client.get(
                "/api/v1/analytics/agents/sa-whatsapp",
                headers=admin_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['agent_id'] == 'sa-whatsapp'
            assert data['success_rate_percent'] == 90.0
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_create_custom_alert(self, mock_get_user, admin_headers):
        """Teste para criação de alerta customizado via API"""
        mock_get_user.return_value = {'user_id': 'admin-123', 'role': 'admin'}
        
        alert_data = {
            "title": "Test Alert",
            "message": "This is a test alert",
            "severity": "high",
            "details": {"test": "value"}
        }
        
        with patch('app.api.v1.analytics.alerting_service') as mock_service:
            mock_service.create_custom_alert.return_value = "alert-123"
            
            response = client.post(
                "/api/v1/analytics/alerts/custom",
                json=alert_data,
                headers=admin_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['alert_id'] == 'alert-123'
            assert "created successfully" in data['message']
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_acknowledge_alert(self, mock_get_user, admin_headers):
        """Teste para reconhecimento de alerta via API"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        action_data = {"note": "Acknowledged by user"}
        
        with patch('app.api.v1.analytics.alerting_service') as mock_service:
            mock_service.acknowledge_alert.return_value = True
            
            response = client.post(
                "/api/v1/analytics/alerts/alert-123/acknowledge",
                json=action_data,
                headers=admin_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "acknowledged successfully" in data['message']
    
    def test_analytics_endpoints_require_auth(self):
        """Teste que endpoints de analytics requerem autenticação"""
        response = client.get("/api/v1/analytics/system")
        assert response.status_code == 403  # Unauthorized