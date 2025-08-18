"""
Integration Tests for Webhook Flows
End-to-end testing of webhook processing and integration flows
"""
import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
import hmac
import hashlib

from app.main import app

client = TestClient(app)

class TestWebhookIntegrationFlows:
    """Integration tests for complete webhook flows"""
    
    @pytest.fixture
    def mock_user_token(self):
        """Mock user authentication token"""
        return "webhook-integration-test-token"
    
    @pytest.fixture
    def auth_headers(self, mock_user_token):
        """Headers with authentication token"""
        return {"Authorization": f"Bearer {mock_user_token}"}
    
    @pytest.fixture
    def sample_integration(self):
        """Sample integration configuration"""
        return {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "name": "Test WhatsApp Integration",
            "provider": "whatsapp_business",
            "webhook_url": "https://api.renum.com/api/v1/webhooks/whatsapp",
            "webhook_token": "test-webhook-token-123",
            "status": "active",
            "settings": {
                "phone_number": "+1234567890",
                "business_account_id": "test-business-123"
            }
        }
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_complete_whatsapp_webhook_flow(self, mock_get_user, auth_headers, sample_integration):
        """Test complete WhatsApp webhook processing flow"""
        mock_get_user.return_value = {'user_id': sample_integration['user_id'], 'role': 'user'}
        
        # Step 1: Create integration
        with patch('app.api.v1.integrations.integration_service') as mock_integration_service:
            mock_integration_service.create_integration.return_value = sample_integration
            
            integration_data = {
                "name": sample_integration["name"],
                "provider": sample_integration["provider"],
                "settings": sample_integration["settings"]
            }
            
            response = client.post(
                "/api/v1/integrations",
                json=integration_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            created_integration = response.json()
            integration_id = created_integration["id"]
        
        # Step 2: Simulate incoming WhatsApp webhook
        whatsapp_webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "test-business-123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "+1234567890",
                                    "phone_number_id": "test-phone-123"
                                },
                                "messages": [
                                    {
                                        "from": "+0987654321",
                                        "id": "wamid.test123",
                                        "timestamp": "1234567890",
                                        "text": {
                                            "body": "Hello, this is a test message!"
                                        },
                                        "type": "text"
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        
        # Step 3: Process webhook with proper signature
        webhook_secret = "test-webhook-secret"
        payload_string = json.dumps(whatsapp_webhook_payload, sort_keys=True)
        signature = hmac.new(
            webhook_secret.encode(),
            payload_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        webhook_headers = {
            "X-Hub-Signature-256": f"sha256={signature}",
            "Content-Type": "application/json"
        }
        
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.process_webhook.return_value = {
                "success": True,
                "message_id": "processed-msg-123",
                "processing_time_ms": 150,
                "actions_triggered": 1
            }
            
            response = client.post(
                f"/api/v1/webhooks/whatsapp/{integration_id}",
                json=whatsapp_webhook_payload,
                headers=webhook_headers
            )
            
            assert response.status_code == 200
            webhook_result = response.json()
            assert webhook_result["success"] is True
            assert "message_id" in webhook_result
        
        # Step 4: Verify webhook processing triggered agent execution
        with patch('app.api.v1.agents.get_agent_by_id') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.execute_capability.return_value = MagicMock(
                success=True,
                data={
                    "message_sent": True,
                    "recipient": "+0987654321",
                    "message": "Auto-reply: Thank you for your message!"
                },
                execution_time_ms=200
            )
            mock_get_agent.return_value = mock_agent
            
            # Simulate auto-reply agent execution
            agent_execution_data = {
                "agent_id": "sa-whatsapp",
                "capability": "send_message",
                "input_data": {
                    "recipient": "+0987654321",
                    "message": "Auto-reply: Thank you for your message!",
                    "message_type": "text"
                }
            }
            
            response = client.post(
                "/api/v1/agents/execute",
                json=agent_execution_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            execution_result = response.json()
            assert execution_result["success"] is True
            assert execution_result["data"]["message_sent"] is True
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_telegram_webhook_integration_flow(self, mock_get_user, auth_headers):
        """Test Telegram webhook integration flow"""
        user_id = str(uuid4())
        mock_get_user.return_value = {'user_id': user_id, 'role': 'user'}
        
        # Telegram webhook payload
        telegram_payload = {
            "update_id": 123456789,
            "message": {
                "message_id": 1234,
                "from": {
                    "id": 987654321,
                    "is_bot": False,
                    "first_name": "Test",
                    "last_name": "User",
                    "username": "testuser"
                },
                "chat": {
                    "id": 987654321,
                    "first_name": "Test",
                    "last_name": "User",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1234567890,
                "text": "/start"
            }
        }
        
        integration_id = str(uuid4())
        
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.process_webhook.return_value = {
                "success": True,
                "update_id": 123456789,
                "processing_time_ms": 100,
                "command_processed": "/start"
            }
            
            response = client.post(
                f"/api/v1/webhooks/telegram/{integration_id}",
                json=telegram_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["update_id"] == 123456789
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_zapier_webhook_integration_flow(self, mock_get_user, auth_headers):
        """Test Zapier webhook integration flow"""
        user_id = str(uuid4())
        mock_get_user.return_value = {'user_id': user_id, 'role': 'user'}
        
        # Zapier webhook payload (generic format)
        zapier_payload = {
            "trigger_event": "new_contact",
            "data": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "company": "Test Company",
                "source": "website_form"
            },
            "zap_id": "zapier-123456",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        integration_id = str(uuid4())
        
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.process_webhook.return_value = {
                "success": True,
                "contact_created": True,
                "processing_time_ms": 80,
                "actions_triggered": 2
            }
            
            response = client.post(
                f"/api/v1/webhooks/zapier/{integration_id}",
                json=zapier_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["contact_created"] is True
    
    def test_webhook_signature_validation_flow(self):
        """Test webhook signature validation in integration flow"""
        integration_id = str(uuid4())
        webhook_secret = "super-secret-webhook-key"
        
        payload = {
            "test": "data",
            "timestamp": int(time.time())
        }
        
        # Test with valid signature
        payload_string = json.dumps(payload, sort_keys=True)
        valid_signature = hmac.new(
            webhook_secret.encode(),
            payload_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.validate_webhook_signature.return_value = True
            mock_webhook_service.process_webhook.return_value = {
                "success": True,
                "signature_valid": True
            }
            
            response = client.post(
                f"/api/v1/webhooks/generic/{integration_id}",
                json=payload,
                headers={
                    "X-Signature": f"sha256={valid_signature}",
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
        
        # Test with invalid signature
        invalid_signature = "invalid-signature-hash"
        
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.validate_webhook_signature.return_value = False
            
            response = client.post(
                f"/api/v1/webhooks/generic/{integration_id}",
                json=payload,
                headers={
                    "X-Signature": f"sha256={invalid_signature}",
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 401  # Unauthorized due to invalid signature
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_multi_step_orchestration_webhook_flow(self, mock_get_user, auth_headers):
        """Test webhook triggering multi-step orchestration"""
        user_id = str(uuid4())
        mock_get_user.return_value = {'user_id': user_id, 'role': 'user'}
        
        # Webhook payload that should trigger orchestration
        webhook_payload = {
            "event_type": "order_created",
            "order": {
                "id": "order-123",
                "customer_email": "customer@example.com",
                "total": 99.99,
                "items": [
                    {"name": "Product A", "quantity": 2, "price": 49.99}
                ]
            }
        }
        
        integration_id = str(uuid4())
        
        # Step 1: Process webhook
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.process_webhook.return_value = {
                "success": True,
                "orchestration_triggered": True,
                "workflow_id": "order-processing-workflow"
            }
            
            response = client.post(
                f"/api/v1/webhooks/ecommerce/{integration_id}",
                json=webhook_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            webhook_result = response.json()
            assert webhook_result["orchestration_triggered"] is True
        
        # Step 2: Execute orchestrated workflow
        workflow_data = {
            "workflow_name": "Order Processing Workflow",
            "strategy": "sequential",
            "agents": [
                {
                    "agent_id": "sa-gmail",
                    "capability": "send_email",
                    "input_data": {
                        "to": "customer@example.com",
                        "subject": "Order Confirmation",
                        "body": "Your order #order-123 has been confirmed."
                    }
                },
                {
                    "agent_id": "sa-supabase",
                    "capability": "create_record",
                    "input_data": {
                        "table": "orders",
                        "data": webhook_payload["order"]
                    }
                },
                {
                    "agent_id": "sa-whatsapp",
                    "capability": "send_notification",
                    "input_data": {
                        "recipient": "+1234567890",
                        "message": "New order received: #order-123"
                    }
                }
            ]
        }
        
        with patch('app.api.v1.orchestrator.orchestrator_service') as mock_orchestrator:
            mock_orchestrator.execute_workflow.return_value = {
                "execution_id": str(uuid4()),
                "status": "completed",
                "results": [
                    {"agent_id": "sa-gmail", "success": True, "execution_time_ms": 1200},
                    {"agent_id": "sa-supabase", "success": True, "execution_time_ms": 300},
                    {"agent_id": "sa-whatsapp", "success": True, "execution_time_ms": 800}
                ],
                "total_execution_time_ms": 2300,
                "success_rate": 100.0
            }
            
            response = client.post(
                "/api/v1/orchestrator/execute",
                json=workflow_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            orchestration_result = response.json()
            assert orchestration_result["status"] == "completed"
            assert orchestration_result["success_rate"] == 100.0
            assert len(orchestration_result["results"]) == 3

class TestWebhookErrorHandling:
    """Test error handling in webhook integration flows"""
    
    def test_webhook_processing_with_malformed_payload(self):
        """Test webhook processing with malformed JSON payload"""
        integration_id = str(uuid4())
        
        # Send malformed JSON
        response = client.post(
            f"/api/v1/webhooks/generic/{integration_id}",
            data="invalid-json-payload",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400  # Bad Request
    
    def test_webhook_processing_with_missing_integration(self):
        """Test webhook processing with non-existent integration"""
        non_existent_id = str(uuid4())
        
        payload = {"test": "data"}
        
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.process_webhook.side_effect = ValueError("Integration not found")
            
            response = client.post(
                f"/api/v1/webhooks/generic/{non_existent_id}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 404  # Not Found
    
    def test_webhook_processing_timeout_handling(self):
        """Test webhook processing with timeout scenarios"""
        integration_id = str(uuid4())
        payload = {"test": "data"}
        
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.process_webhook.side_effect = asyncio.TimeoutError("Processing timeout")
            
            response = client.post(
                f"/api/v1/webhooks/generic/{integration_id}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 408  # Request Timeout
    
    @patch('app.middleware.auth.jwt_auth.get_current_user')
    def test_webhook_retry_mechanism(self, mock_get_user, auth_headers):
        """Test webhook retry mechanism for failed processing"""
        user_id = str(uuid4())
        mock_get_user.return_value = {'user_id': user_id, 'role': 'user'}
        
        integration_id = str(uuid4())
        payload = {"retry_test": "data"}
        
        # Simulate initial failure followed by success
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            # First call fails
            mock_webhook_service.process_webhook.side_effect = [
                Exception("Temporary processing error"),
                {
                    "success": True,
                    "retry_attempt": 2,
                    "processing_time_ms": 250
                }
            ]
            
            # First attempt should fail
            response = client.post(
                f"/api/v1/webhooks/generic/{integration_id}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 500  # Internal Server Error
            
            # Second attempt should succeed (simulating retry)
            response = client.post(
                f"/api/v1/webhooks/generic/{integration_id}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True

class TestWebhookPerformanceIntegration:
    """Performance tests for webhook integration flows"""
    
    def test_high_volume_webhook_processing(self):
        """Test webhook processing under high volume"""
        integration_id = str(uuid4())
        num_webhooks = 100
        
        response_times = []
        successful_requests = 0
        
        with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
            mock_webhook_service.process_webhook.return_value = {
                "success": True,
                "processing_time_ms": 50
            }
            
            for i in range(num_webhooks):
                payload = {
                    "webhook_id": i,
                    "data": f"test-data-{i}",
                    "timestamp": int(time.time())
                }
                
                start_time = time.time()
                response = client.post(
                    f"/api/v1/webhooks/generic/{integration_id}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                end_time = time.time()
                
                response_times.append((end_time - start_time) * 1000)
                
                if response.status_code == 200:
                    successful_requests += 1
        
        success_rate = (successful_requests / num_webhooks) * 100
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        print(f"High volume webhook processing:")
        print(f"  Total webhooks: {num_webhooks}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Max response time: {max_response_time:.2f}ms")
        
        # Performance assertions
        assert success_rate >= 95, f"Success rate too low: {success_rate:.1f}%"
        assert avg_response_time < 200, f"Average response time too high: {avg_response_time:.2f}ms"
        assert max_response_time < 1000, f"Max response time too high: {max_response_time:.2f}ms"
    
    def test_concurrent_webhook_processing(self):
        """Test concurrent webhook processing"""
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        integration_id = str(uuid4())
        num_threads = 10
        webhooks_per_thread = 20
        
        def process_webhooks():
            response_times = []
            errors = 0
            
            with patch('app.api.v1.webhooks.webhook_service') as mock_webhook_service:
                mock_webhook_service.process_webhook.return_value = {
                    "success": True,
                    "thread_id": threading.current_thread().ident
                }
                
                for i in range(webhooks_per_thread):
                    payload = {
                        "thread_webhook_id": i,
                        "thread_id": threading.current_thread().ident
                    }
                    
                    try:
                        start_time = time.time()
                        response = client.post(
                            f"/api/v1/webhooks/generic/{integration_id}",
                            json=payload,
                            headers={"Content-Type": "application/json"}
                        )
                        end_time = time.time()
                        
                        response_times.append((end_time - start_time) * 1000)
                        
                        if response.status_code != 200:
                            errors += 1
                            
                    except Exception:
                        errors += 1
                        response_times.append(5000)  # Timeout value
            
            return response_times, errors
        
        # Execute concurrent webhook processing
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(process_webhooks) for _ in range(num_threads)]
            
            all_response_times = []
            total_errors = 0
            
            for future in futures:
                response_times, errors = future.result()
                all_response_times.extend(response_times)
                total_errors += errors
        
        end_time = time.time()
        
        total_webhooks = num_threads * webhooks_per_thread
        total_time = end_time - start_time
        webhooks_per_second = total_webhooks / total_time
        error_rate = (total_errors / total_webhooks) * 100
        
        avg_response_time = sum(all_response_times) / len(all_response_times)
        
        print(f"Concurrent webhook processing:")
        print(f"  Total webhooks: {total_webhooks}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Webhooks per second: {webhooks_per_second:.2f}")
        print(f"  Error rate: {error_rate:.2f}%")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        
        # Performance assertions
        assert error_rate < 5, f"Error rate too high: {error_rate:.2f}%"
        assert webhooks_per_second > 50, f"Throughput too low: {webhooks_per_second:.2f} webhooks/s"
        assert avg_response_time < 500, f"Average response time too high: {avg_response_time:.2f}ms"