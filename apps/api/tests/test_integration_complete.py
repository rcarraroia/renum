"""
Testes de Integração Completos
Testes end-to-end de todos os componentes do sistema
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timedelta
import json

from app.main import app
from app.services.orchestrator_service import OrchestratorService
from app.services.analytics_service import analytics_service
from app.services.fallback_service import fallback_service
from app.services.billing_service import billing_service
from app.agents.sa_whatsapp import WhatsAppAgent
from app.agents.sa_telegram import TelegramAgent
from app.agents.sa_gmail import GmailAgent

client = TestClient(app)

class TestEndToEndWorkflows:
    """Testes end-to-end de workflows completos"""
    
    @pytest.fixture
    def mock_auth_headers(self):
        """Headers de autenticação mock"""
        return {"Authorization": "Bearer test-token"}
    
    @pytest.fixture
    def sample_workflow_definition(self):
        """Definição de workflow de exemplo"""
        return {
            "name": "Multi-Channel Notification",
            "description": "Send notification via WhatsApp, Telegram, and Email",
            "execution_strategy": "parallel",
            "steps": [
                {
                    "id": "whatsapp_step",
                    "agent_id": "sa-whatsapp",
                    "capability": "send_message",
                    "input": {
                        "phone_number": "+5511999999999",
                        "message": "Hello from WhatsApp!"
                    }
                },
                {
                    "id": "telegram_step", 
                    "agent_id": "sa-telegram",
                    "capability": "send_message",
                    "input": {
                        "chat_id": "123456789",
                        "message": "Hello from Telegram!"
                    }
                },
                {
                    "id": "email_step",
                    "agent_id": "sa-gmail",
                    "capability": "send_email",
                    "input": {
                        "to": "user@example.com",
                        "subject": "Test Email",
                        "body": "Hello from Gmail!"
                    }
                }
            ]
        }
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    @patch('app.services.orchestrator_service.OrchestratorService.execute_workflow')
    def test_complete_workflow_execution(self, mock_execute_workflow, mock_get_user, 
                                       mock_auth_headers, sample_workflow_definition):
        """Teste de execução completa de workflow"""
        # Setup mocks
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        mock_execute_workflow.return_value = {
            'execution_id': str(uuid4()),
            'status': 'completed',
            'results': {
                'whatsapp_step': {'success': True, 'message_id': 'wa-123'},
                'telegram_step': {'success': True, 'message_id': 'tg-456'},
                'email_step': {'success': True, 'message_id': 'em-789'}
            },
            'execution_time_ms': 2500,
            'total_cost': 0.15
        }
        
        # Execute workflow
        response = client.post(
            '/api/v1/orchestrator/execute',
            json={
                'workflow_definition': sample_workflow_definition,
                'input_data': {}
            },
            headers=mock_auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        result = response.json()
        
        assert result['status'] == 'completed'
        assert 'execution_id' in result
        assert 'results' in result
        assert len(result['results']) == 3
        
        # Verify all steps completed successfully
        for step_id in ['whatsapp_step', 'telegram_step', 'email_step']:
            assert step_id in result['results']
            assert result['results'][step_id]['success'] is True
        
        # Verify orchestrator was called with correct parameters
        mock_execute_workflow.assert_called_once()
        call_args = mock_execute_workflow.call_args[1]
        assert call_args['workflow_definition'] == sample_workflow_definition
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    @patch('app.services.analytics_service.analytics_service.track_execution')
    def test_workflow_with_analytics_tracking(self, mock_track_execution, mock_get_user, mock_auth_headers):
        """Teste de workflow com rastreamento de analytics"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        workflow_definition = {
            "name": "Simple WhatsApp Message",
            "steps": [{
                "id": "step1",
                "agent_id": "sa-whatsapp",
                "capability": "send_message",
                "input": {"phone_number": "+5511999999999", "message": "Test"}
            }]
        }
        
        with patch('app.services.orchestrator_service.OrchestratorService.execute_workflow') as mock_execute:
            mock_execute.return_value = {
                'execution_id': 'exec-123',
                'status': 'completed',
                'results': {'step1': {'success': True}},
                'execution_time_ms': 1500
            }
            
            response = client.post(
                '/api/v1/orchestrator/execute',
                json={'workflow_definition': workflow_definition, 'input_data': {}},
                headers=mock_auth_headers
            )
            
            assert response.status_code == 200
            
            # Verify analytics tracking was called
            mock_track_execution.assert_called()
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_workflow_with_fallback_handling(self, mock_get_user, mock_auth_headers):
        """Teste de workflow com tratamento de fallback"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        # Workflow with unsupported agent
        workflow_definition = {
            "name": "Unsupported Integration Test",
            "steps": [{
                "id": "step1",
                "agent_id": "sa-unsupported-service",
                "capability": "send_notification",
                "input": {"message": "Test notification"}
            }]
        }
        
        with patch('app.services.fallback_service.fallback_service.handle_unsupported_integration') as mock_fallback:
            mock_fallback.return_value = {
                'fallback_used': True,
                'alternative_agent': 'sa-http-generic',
                'suggestion': 'Use HTTP Generic agent with custom API endpoint'
            }
            
            response = client.post(
                '/api/v1/orchestrator/execute',
                json={'workflow_definition': workflow_definition, 'input_data': {}},
                headers=mock_auth_headers
            )
            
            # Should handle gracefully with fallback
            assert response.status_code in [200, 202]  # Success or accepted for async processing
            
            # Verify fallback service was called
            mock_fallback.assert_called()
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_workflow_with_billing_tracking(self, mock_get_user, mock_auth_headers):
        """Teste de workflow com rastreamento de billing"""
        mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
        
        workflow_definition = {
            "name": "Billing Test Workflow",
            "steps": [{
                "id": "step1",
                "agent_id": "sa-whatsapp",
                "capability": "send_message",
                "input": {"phone_number": "+5511999999999", "message": "Test"}
            }]
        }
        
        with patch('app.services.billing_service.billing_service.track_usage') as mock_billing:
            with patch('app.services.orchestrator_service.OrchestratorService.execute_workflow') as mock_execute:
                mock_execute.return_value = {
                    'execution_id': 'exec-123',
                    'status': 'completed',
                    'results': {'step1': {'success': True}},
                    'total_cost': 0.05
                }
                
                response = client.post(
                    '/api/v1/orchestrator/execute',
                    json={'workflow_definition': workflow_definition, 'input_data': {}},
                    headers=mock_auth_headers
                )
                
                assert response.status_code == 200
                
                # Verify billing tracking was called
                mock_billing.assert_called()

class TestWebhookIntegrationFlows:
    """Testes de fluxos de integração via webhook"""
    
    def test_webhook_to_workflow_execution(self):
        """Teste de execução de workflow via webhook"""
        webhook_payload = {
            "event": "user_registered",
            "data": {
                "user_id": "user-456",
                "email": "newuser@example.com",
                "phone": "+5511888888888"
            }
        }
        
        with patch('app.services.orchestrator_service.OrchestratorService.execute_workflow') as mock_execute:
            mock_execute.return_value = {
                'execution_id': 'exec-webhook-123',
                'status': 'completed',
                'results': {'welcome_message': {'success': True}}
            }
            
            response = client.post(
                '/api/v1/webhooks/user-events',
                json=webhook_payload,
                headers={"X-Webhook-Secret": "test-secret"}
            )
            
            assert response.status_code == 200
            result = response.json()
            
            assert 'execution_id' in result
            assert result['status'] == 'processed'
    
    def test_webhook_authentication_and_validation(self):
        """Teste de autenticação e validação de webhook"""
        # Test without secret
        response = client.post(
            '/api/v1/webhooks/user-events',
            json={"event": "test"}
        )
        assert response.status_code == 401
        
        # Test with invalid secret
        response = client.post(
            '/api/v1/webhooks/user-events',
            json={"event": "test"},
            headers={"X-Webhook-Secret": "invalid-secret"}
        )
        assert response.status_code == 401
        
        # Test with invalid payload
        response = client.post(
            '/api/v1/webhooks/user-events',
            json={"invalid": "payload"},
            headers={"X-Webhook-Secret": "test-secret"}
        )
        assert response.status_code == 400
    
    def test_webhook_async_processing(self):
        """Teste de processamento assíncrono de webhook"""
        webhook_payload = {
            "event": "bulk_notification",
            "data": {
                "recipients": [f"user-{i}@example.com" for i in range(100)],
                "message": "Bulk notification test"
            }
        }
        
        with patch('app.services.orchestrator_service.OrchestratorService.execute_workflow_async') as mock_execute_async:
            mock_execute_async.return_value = {
                'execution_id': 'exec-async-123',
                'status': 'queued'
            }
            
            response = client.post(
                '/api/v1/webhooks/bulk-events',
                json=webhook_payload,
                headers={"X-Webhook-Secret": "test-secret"}
            )
            
            assert response.status_code == 202  # Accepted for async processing
            result = response.json()
            
            assert result['status'] == 'queued'
            assert 'execution_id' in result

class TestAgentIntegrationFlows:
    """Testes de fluxos de integração entre agentes"""
    
    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self):
        """Teste de coordenação entre múltiplos agentes"""
        orchestrator = OrchestratorService()
        
        # Workflow que requer coordenação entre agentes
        workflow_definition = {
            "name": "Customer Support Flow",
            "execution_strategy": "sequential",
            "steps": [
                {
                    "id": "get_customer_info",
                    "agent_id": "sa-http-generic",
                    "capability": "api_call",
                    "input": {
                        "url": "https://api.example.com/customers/123",
                        "method": "GET"
                    }
                },
                {
                    "id": "send_whatsapp",
                    "agent_id": "sa-whatsapp",
                    "capability": "send_message",
                    "input": {
                        "phone_number": "{{get_customer_info.phone}}",
                        "message": "Hello {{get_customer_info.name}}, we received your request!"
                    }
                },
                {
                    "id": "send_email_followup",
                    "agent_id": "sa-gmail",
                    "capability": "send_email",
                    "input": {
                        "to": "{{get_customer_info.email}}",
                        "subject": "Support Request Confirmation",
                        "body": "Dear {{get_customer_info.name}}, your request has been received."
                    }
                }
            ]
        }
        
        # Mock agent responses
        with patch.object(orchestrator, '_execute_agent_step') as mock_execute_step:
            mock_execute_step.side_effect = [
                # First step: get customer info
                {
                    'success': True,
                    'data': {
                        'name': 'John Doe',
                        'email': 'john@example.com',
                        'phone': '+5511999999999'
                    }
                },
                # Second step: WhatsApp message
                {
                    'success': True,
                    'data': {'message_id': 'wa-123'}
                },
                # Third step: Email followup
                {
                    'success': True,
                    'data': {'message_id': 'em-456'}
                }
            ]
            
            result = await orchestrator.execute_workflow(
                workflow_definition=workflow_definition,
                input_data={},
                user_id=uuid4()
            )
            
            assert result['status'] == 'completed'
            assert len(result['results']) == 3
            
            # Verify all steps executed in sequence
            assert mock_execute_step.call_count == 3
            
            # Verify variable interpolation worked
            whatsapp_call = mock_execute_step.call_args_list[1]
            assert 'John Doe' in str(whatsapp_call)
            assert '+5511999999999' in str(whatsapp_call)
    
    @pytest.mark.asyncio
    async def test_agent_error_handling_and_retry(self):
        """Teste de tratamento de erro e retry entre agentes"""
        orchestrator = OrchestratorService()
        
        workflow_definition = {
            "name": "Retry Test Workflow",
            "steps": [{
                "id": "flaky_step",
                "agent_id": "sa-whatsapp",
                "capability": "send_message",
                "input": {"phone_number": "+5511999999999", "message": "Test"},
                "retry_config": {
                    "max_retries": 3,
                    "retry_delay_ms": 100
                }
            }]
        }
        
        with patch.object(orchestrator, '_execute_agent_step') as mock_execute_step:
            # First two calls fail, third succeeds
            mock_execute_step.side_effect = [
                Exception("Network error"),
                Exception("Rate limit exceeded"),
                {'success': True, 'data': {'message_id': 'wa-123'}}
            ]
            
            result = await orchestrator.execute_workflow(
                workflow_definition=workflow_definition,
                input_data={},
                user_id=uuid4()
            )
            
            assert result['status'] == 'completed'
            assert mock_execute_step.call_count == 3  # 2 failures + 1 success
    
    @pytest.mark.asyncio
    async def test_parallel_agent_execution(self):
        """Teste de execução paralela de agentes"""
        orchestrator = OrchestratorService()
        
        workflow_definition = {
            "name": "Parallel Notification",
            "execution_strategy": "parallel",
            "steps": [
                {
                    "id": "whatsapp",
                    "agent_id": "sa-whatsapp",
                    "capability": "send_message",
                    "input": {"phone_number": "+5511999999999", "message": "Test"}
                },
                {
                    "id": "telegram",
                    "agent_id": "sa-telegram", 
                    "capability": "send_message",
                    "input": {"chat_id": "123456789", "message": "Test"}
                },
                {
                    "id": "email",
                    "agent_id": "sa-gmail",
                    "capability": "send_email",
                    "input": {"to": "test@example.com", "subject": "Test", "body": "Test"}
                }
            ]
        }
        
        with patch.object(orchestrator, '_execute_agent_step') as mock_execute_step:
            # All agents succeed
            mock_execute_step.return_value = {'success': True, 'data': {'message_id': 'test-123'}}
            
            start_time = asyncio.get_event_loop().time()
            
            result = await orchestrator.execute_workflow(
                workflow_definition=workflow_definition,
                input_data={},
                user_id=uuid4()
            )
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            assert result['status'] == 'completed'
            assert len(result['results']) == 3
            
            # Parallel execution should be faster than sequential
            # (This is a rough check since we're mocking)
            assert execution_time < 1.0  # Should complete quickly with mocks
            
            # All agents should have been called
            assert mock_execute_step.call_count == 3

class TestSystemIntegrationHealth:
    """Testes de saúde da integração do sistema"""
    
    def test_health_check_endpoint(self):
        """Teste do endpoint de health check"""
        response = client.get('/health')
        
        assert response.status_code == 200
        health_data = response.json()
        
        assert 'status' in health_data
        assert 'timestamp' in health_data
        assert 'version' in health_data
        assert 'services' in health_data
        
        # Check individual service health
        services = health_data['services']
        expected_services = ['database', 'analytics', 'orchestrator', 'agents']
        
        for service in expected_services:
            assert service in services
            assert 'status' in services[service]
    
    def test_metrics_endpoint(self):
        """Teste do endpoint de métricas"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'admin-123', 'role': 'admin'}
            
            response = client.get(
                '/api/v1/metrics',
                headers={"Authorization": "Bearer admin-token"}
            )
            
            assert response.status_code == 200
            metrics_data = response.json()
            
            assert 'system_metrics' in metrics_data
            assert 'agent_metrics' in metrics_data
            assert 'workflow_metrics' in metrics_data
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_system_status_dashboard(self, mock_get_user):
        """Teste do dashboard de status do sistema"""
        mock_get_user.return_value = {'user_id': 'admin-123', 'role': 'admin'}
        
        response = client.get(
            '/api/v1/analytics/dashboard',
            headers={"Authorization": "Bearer admin-token"}
        )
        
        assert response.status_code == 200
        dashboard_data = response.json()
        
        # Verify dashboard contains key metrics
        expected_sections = [
            'execution_stats',
            'agent_performance',
            'error_rates',
            'system_health'
        ]
        
        for section in expected_sections:
            assert section in dashboard_data

class TestDataConsistencyAndIntegrity:
    """Testes de consistência e integridade de dados"""
    
    @pytest.mark.asyncio
    async def test_execution_data_consistency(self):
        """Teste de consistência de dados de execução"""
        # Simulate workflow execution and verify data consistency
        execution_id = str(uuid4())
        user_id = uuid4()
        
        # Mock database operations
        with patch('app.services.analytics_service.analytics_service.track_execution') as mock_track:
            with patch('app.services.billing_service.billing_service.track_usage') as mock_billing:
                
                # Execute workflow
                orchestrator = OrchestratorService()
                
                workflow_definition = {
                    "name": "Consistency Test",
                    "steps": [{
                        "id": "step1",
                        "agent_id": "sa-whatsapp",
                        "capability": "send_message",
                        "input": {"phone_number": "+5511999999999", "message": "Test"}
                    }]
                }
                
                with patch.object(orchestrator, '_execute_agent_step') as mock_execute:
                    mock_execute.return_value = {'success': True, 'data': {'message_id': 'wa-123'}}
                    
                    result = await orchestrator.execute_workflow(
                        workflow_definition=workflow_definition,
                        input_data={},
                        user_id=user_id
                    )
                    
                    # Verify all tracking services were called with consistent data
                    mock_track.assert_called()
                    mock_billing.assert_called()
                    
                    # Verify execution result consistency
                    assert result['status'] == 'completed'
                    assert 'execution_id' in result
                    assert 'results' in result
    
    def test_concurrent_execution_isolation(self):
        """Teste de isolamento de execuções concorrentes"""
        # Test that concurrent executions don't interfere with each other
        
        def execute_workflow_sync(workflow_id):
            """Execute workflow synchronously for testing"""
            with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
                mock_get_user.return_value = {'user_id': f'user-{workflow_id}', 'role': 'user'}
                
                workflow_definition = {
                    "name": f"Concurrent Test {workflow_id}",
                    "steps": [{
                        "id": "step1",
                        "agent_id": "sa-whatsapp",
                        "capability": "send_message",
                        "input": {
                            "phone_number": f"+551199999999{workflow_id}",
                            "message": f"Test message {workflow_id}"
                        }
                    }]
                }
                
                with patch('app.services.orchestrator_service.OrchestratorService.execute_workflow') as mock_execute:
                    mock_execute.return_value = {
                        'execution_id': f'exec-{workflow_id}',
                        'status': 'completed',
                        'results': {'step1': {'success': True, 'message_id': f'msg-{workflow_id}'}}
                    }
                    
                    response = client.post(
                        '/api/v1/orchestrator/execute',
                        json={'workflow_definition': workflow_definition, 'input_data': {}},
                        headers={"Authorization": f"Bearer token-{workflow_id}"}
                    )
                    
                    return response.json()
        
        # Execute multiple workflows concurrently
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_workflow_sync, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # Verify all executions completed successfully and independently
        assert len(results) == 5
        
        execution_ids = [result['execution_id'] for result in results]
        assert len(set(execution_ids)) == 5  # All execution IDs should be unique
        
        for i, result in enumerate(results):
            assert result['status'] == 'completed'
            assert result['execution_id'] == f'exec-{i}'

class TestErrorRecoveryAndResilience:
    """Testes de recuperação de erro e resiliência"""
    
    @pytest.mark.asyncio
    async def test_system_recovery_after_service_failure(self):
        """Teste de recuperação do sistema após falha de serviço"""
        orchestrator = OrchestratorService()
        
        workflow_definition = {
            "name": "Recovery Test",
            "steps": [{
                "id": "step1",
                "agent_id": "sa-whatsapp",
                "capability": "send_message",
                "input": {"phone_number": "+5511999999999", "message": "Test"}
            }]
        }
        
        # Simulate service failure followed by recovery
        with patch.object(orchestrator, '_execute_agent_step') as mock_execute:
            # First call fails with service unavailable
            # Second call succeeds after "recovery"
            mock_execute.side_effect = [
                Exception("Service temporarily unavailable"),
                {'success': True, 'data': {'message_id': 'wa-123'}}
            ]
            
            # Execute with retry logic
            result = await orchestrator.execute_workflow(
                workflow_definition=workflow_definition,
                input_data={},
                user_id=uuid4()
            )
            
            # Should eventually succeed after retry
            assert result['status'] == 'completed'
            assert mock_execute.call_count == 2
    
    def test_graceful_degradation_on_partial_failure(self):
        """Teste de degradação graciosa em falha parcial"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            # Workflow with multiple steps where some might fail
            workflow_definition = {
                "name": "Partial Failure Test",
                "execution_strategy": "parallel",
                "failure_strategy": "continue_on_error",
                "steps": [
                    {
                        "id": "whatsapp",
                        "agent_id": "sa-whatsapp",
                        "capability": "send_message",
                        "input": {"phone_number": "+5511999999999", "message": "Test"}
                    },
                    {
                        "id": "telegram",
                        "agent_id": "sa-telegram",
                        "capability": "send_message", 
                        "input": {"chat_id": "123456789", "message": "Test"}
                    }
                ]
            }
            
            with patch('app.services.orchestrator_service.OrchestratorService.execute_workflow') as mock_execute:
                # Simulate partial failure (WhatsApp succeeds, Telegram fails)
                mock_execute.return_value = {
                    'execution_id': 'exec-partial-123',
                    'status': 'partial_success',
                    'results': {
                        'whatsapp': {'success': True, 'message_id': 'wa-123'},
                        'telegram': {'success': False, 'error': 'Rate limit exceeded'}
                    },
                    'failed_steps': ['telegram'],
                    'successful_steps': ['whatsapp']
                }
                
                response = client.post(
                    '/api/v1/orchestrator/execute',
                    json={'workflow_definition': workflow_definition, 'input_data': {}},
                    headers={"Authorization": "Bearer test-token"}
                )
                
                assert response.status_code == 200
                result = response.json()
                
                # Should indicate partial success
                assert result['status'] == 'partial_success'
                assert 'failed_steps' in result
                assert 'successful_steps' in result
                assert len(result['successful_steps']) > 0  # At least one step succeeded