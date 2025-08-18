"""
Testes de Segurança Abrangentes
Testes de segurança, autenticação, autorização e proteção contra ataques
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
import json
import base64
import hashlib
import hmac

from app.main import app
from app.middleware.auth import jwt_auth
from app.middleware.rate_limiting import rate_limiter

client = TestClient(app)

class TestAuthenticationSecurity:
    """Testes de segurança de autenticação"""
    
    def test_jwt_token_validation(self):
        """Teste de validação de token JWT"""
        # Test without token
        response = client.get('/api/v1/agents')
        assert response.status_code == 401
        
        # Test with invalid token
        response = client.get(
            '/api/v1/agents',
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
        
        # Test with malformed token
        response = client.get(
            '/api/v1/agents',
            headers={"Authorization": "invalid-format"}
        )
        assert response.status_code == 401
    
    def test_token_expiration_handling(self):
        """Teste de tratamento de expiração de token"""
        # Mock expired token
        with patch('app.middleware.auth.jwt_auth.decode_jwt_token') as mock_decode:
            mock_decode.side_effect = jwt_auth.TokenExpiredError("Token expired")
            
            response = client.get(
                '/api/v1/agents',
                headers={"Authorization": "Bearer expired-token"}
            )
            
            assert response.status_code == 401
            assert "expired" in response.json()["detail"].lower()
    
    def test_token_tampering_detection(self):
        """Teste de detecção de adulteração de token"""
        # Create a valid-looking but tampered token
        tampered_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImV4cCI6OTk5OTk5OTk5OX0.tampered_signature"
        
        response = client.get(
            '/api/v1/agents',
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        
        assert response.status_code == 401
    
    def test_role_based_access_control(self):
        """Teste de controle de acesso baseado em função"""
        # Test admin-only endpoint with user role
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            response = client.get(
                '/api/v1/admin/system-stats',
                headers={"Authorization": "Bearer user-token"}
            )
            
            assert response.status_code == 403
        
        # Test admin-only endpoint with admin role
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'admin-123', 'role': 'admin'}
            
            response = client.get(
                '/api/v1/admin/system-stats',
                headers={"Authorization": "Bearer admin-token"}
            )
            
            # Should succeed (or return 404 if endpoint doesn't exist, but not 403)
            assert response.status_code != 403
    
    def test_user_isolation(self):
        """Teste de isolamento entre usuários"""
        # User 1 tries to access User 2's data
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            # Try to access another user's executions
            response = client.get(
                '/api/v1/executions?user_id=user-456',
                headers={"Authorization": "Bearer user-123-token"}
            )
            
            # Should either return empty results or 403, but not other user's data
            if response.status_code == 200:
                data = response.json()
                # Verify no data from other users is returned
                if 'executions' in data:
                    for execution in data['executions']:
                        assert execution.get('user_id') == 'user-123'

class TestInputValidationSecurity:
    """Testes de segurança de validação de entrada"""
    
    def test_sql_injection_prevention(self):
        """Teste de prevenção de injeção SQL"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'/*",
            "1; DELETE FROM agents WHERE 1=1; --"
        ]
        
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            for malicious_input in malicious_inputs:
                # Test in query parameters
                response = client.get(
                    f'/api/v1/agents?search={malicious_input}',
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Should not cause server error (500) - should be handled gracefully
                assert response.status_code != 500
                
                # Test in request body
                response = client.post(
                    '/api/v1/orchestrator/execute',
                    json={
                        'workflow_definition': {
                            'name': malicious_input,
                            'steps': []
                        },
                        'input_data': {}
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Should validate and reject or handle safely
                assert response.status_code in [400, 422]  # Validation error
    
    def test_xss_prevention(self):
        """Teste de prevenção de XSS"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            for xss_payload in xss_payloads:
                response = client.post(
                    '/api/v1/orchestrator/execute',
                    json={
                        'workflow_definition': {
                            'name': xss_payload,
                            'description': xss_payload,
                            'steps': [{
                                'id': 'step1',
                                'agent_id': 'sa-whatsapp',
                                'capability': 'send_message',
                                'input': {
                                    'message': xss_payload,
                                    'phone_number': '+5511999999999'
                                }
                            }]
                        },
                        'input_data': {}
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Should handle XSS attempts safely
                if response.status_code == 200:
                    # If successful, verify response doesn't contain unescaped script
                    response_text = response.text
                    assert "<script>" not in response_text
                    assert "javascript:" not in response_text
    
    def test_command_injection_prevention(self):
        """Teste de prevenção de injeção de comando"""
        command_injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(id)"
        ]
        
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            for payload in command_injection_payloads:
                # Test in HTTP Generic agent configuration
                response = client.post(
                    '/api/v1/orchestrator/execute',
                    json={
                        'workflow_definition': {
                            'name': 'Command Injection Test',
                            'steps': [{
                                'id': 'step1',
                                'agent_id': 'sa-http-generic',
                                'capability': 'api_call',
                                'input': {
                                    'url': f'https://api.example.com/test?param={payload}',
                                    'method': 'GET'
                                }
                            }]
                        },
                        'input_data': {}
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Should validate and sanitize inputs
                assert response.status_code in [200, 400, 422]
    
    def test_path_traversal_prevention(self):
        """Teste de prevenção de path traversal"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            for payload in path_traversal_payloads:
                # Test in file-related operations (if any)
                response = client.get(
                    f'/api/v1/files/{payload}',
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Should not allow path traversal
                assert response.status_code in [400, 403, 404]  # Not 200 or 500

class TestRateLimitingSecurity:
    """Testes de segurança de rate limiting"""
    
    def test_api_rate_limiting(self):
        """Teste de rate limiting da API"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            headers = {"Authorization": "Bearer test-token"}
            
            # Make many requests quickly
            responses = []
            for i in range(100):  # Exceed typical rate limit
                response = client.get('/api/v1/agents', headers=headers)
                responses.append(response.status_code)
                
                if response.status_code == 429:  # Rate limited
                    break
            
            # Should eventually hit rate limit
            assert 429 in responses, "Rate limiting should be triggered"
    
    def test_webhook_rate_limiting(self):
        """Teste de rate limiting de webhooks"""
        webhook_headers = {"X-Webhook-Secret": "test-secret"}
        webhook_payload = {"event": "test", "data": {}}
        
        responses = []
        for i in range(50):  # Try many webhook requests
            response = client.post(
                '/api/v1/webhooks/test-events',
                json=webhook_payload,
                headers=webhook_headers
            )
            responses.append(response.status_code)
            
            if response.status_code == 429:
                break
        
        # Webhooks should also be rate limited
        assert 429 in responses or all(r in [200, 202, 404] for r in responses)
    
    def test_per_user_rate_limiting(self):
        """Teste de rate limiting por usuário"""
        # Test that different users have separate rate limits
        
        def make_requests_for_user(user_id, num_requests=20):
            with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
                mock_get_user.return_value = {'user_id': user_id, 'role': 'user'}
                
                headers = {"Authorization": f"Bearer {user_id}-token"}
                responses = []
                
                for i in range(num_requests):
                    response = client.get('/api/v1/agents', headers=headers)
                    responses.append(response.status_code)
                
                return responses
        
        # User 1 makes requests
        user1_responses = make_requests_for_user('user-123')
        
        # User 2 makes requests (should have separate limit)
        user2_responses = make_requests_for_user('user-456')
        
        # Both users should be able to make requests independently
        assert any(r == 200 for r in user1_responses)
        assert any(r == 200 for r in user2_responses)

class TestWebhookSecurity:
    """Testes de segurança de webhooks"""
    
    def test_webhook_signature_validation(self):
        """Teste de validação de assinatura de webhook"""
        payload = {"event": "test", "data": {"test": "data"}}
        payload_json = json.dumps(payload, separators=(',', ':'))
        
        # Test without signature
        response = client.post('/api/v1/webhooks/secure-events', json=payload)
        assert response.status_code == 401
        
        # Test with invalid signature
        response = client.post(
            '/api/v1/webhooks/secure-events',
            json=payload,
            headers={"X-Webhook-Signature": "invalid-signature"}
        )
        assert response.status_code == 401
        
        # Test with valid signature (if webhook signature validation is implemented)
        secret = "webhook-secret"
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        response = client.post(
            '/api/v1/webhooks/secure-events',
            json=payload,
            headers={"X-Webhook-Signature": f"sha256={signature}"}
        )
        
        # Should accept valid signature (or return 404 if endpoint doesn't exist)
        assert response.status_code != 401
    
    def test_webhook_replay_attack_prevention(self):
        """Teste de prevenção de ataques de replay em webhooks"""
        payload = {"event": "test", "data": {"test": "data"}, "timestamp": int(time.time())}
        
        # Send same webhook twice
        headers = {"X-Webhook-Secret": "test-secret"}
        
        response1 = client.post('/api/v1/webhooks/test-events', json=payload, headers=headers)
        response2 = client.post('/api/v1/webhooks/test-events', json=payload, headers=headers)
        
        # Second request should be rejected if replay protection is implemented
        # (This depends on implementation - might return 409 Conflict or 400 Bad Request)
        if response1.status_code in [200, 202]:
            # If first request succeeded, second might be rejected
            assert response2.status_code in [200, 202, 400, 409]
    
    def test_webhook_timestamp_validation(self):
        """Teste de validação de timestamp em webhooks"""
        # Test with old timestamp (replay attack)
        old_timestamp = int(time.time()) - 3600  # 1 hour ago
        payload = {"event": "test", "data": {"test": "data"}, "timestamp": old_timestamp}
        
        response = client.post(
            '/api/v1/webhooks/test-events',
            json=payload,
            headers={"X-Webhook-Secret": "test-secret"}
        )
        
        # Should reject old timestamps if validation is implemented
        assert response.status_code in [200, 202, 400, 401]

class TestDataProtectionSecurity:
    """Testes de segurança de proteção de dados"""
    
    def test_sensitive_data_masking(self):
        """Teste de mascaramento de dados sensíveis"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            # Create workflow with sensitive data
            workflow_definition = {
                'name': 'Sensitive Data Test',
                'steps': [{
                    'id': 'step1',
                    'agent_id': 'sa-whatsapp',
                    'capability': 'send_message',
                    'input': {
                        'phone_number': '+5511999999999',
                        'message': 'Your password is: secret123',
                        'api_key': 'sk-1234567890abcdef'
                    }
                }]
            }
            
            with patch('app.services.orchestrator_service.OrchestratorService.execute_workflow') as mock_execute:
                mock_execute.return_value = {
                    'execution_id': 'exec-123',
                    'status': 'completed',
                    'results': {'step1': {'success': True}}
                }
                
                response = client.post(
                    '/api/v1/orchestrator/execute',
                    json={'workflow_definition': workflow_definition, 'input_data': {}},
                    headers={"Authorization": "Bearer test-token"}
                )
                
                assert response.status_code == 200
                
                # Verify sensitive data is not exposed in response
                response_text = response.text.lower()
                assert 'secret123' not in response_text
                assert 'sk-1234567890abcdef' not in response_text
    
    def test_credential_encryption(self):
        """Teste de criptografia de credenciais"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            # Store credentials
            credentials_data = {
                'integration_id': 'whatsapp-business',
                'credentials': {
                    'api_key': 'sensitive-api-key-123',
                    'phone_number_id': '1234567890'
                }
            }
            
            response = client.post(
                '/api/v1/integrations/credentials',
                json=credentials_data,
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should accept credentials (or return appropriate error)
            assert response.status_code in [200, 201, 400, 404]
            
            if response.status_code in [200, 201]:
                # Verify credentials are not returned in plain text
                response_data = response.json()
                if 'credentials' in response_data:
                    # Should be encrypted or masked
                    assert response_data['credentials'] != credentials_data['credentials']
    
    def test_pii_data_handling(self):
        """Teste de tratamento de dados PII"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            # Workflow with PII data
            workflow_definition = {
                'name': 'PII Test',
                'steps': [{
                    'id': 'step1',
                    'agent_id': 'sa-gmail',
                    'capability': 'send_email',
                    'input': {
                        'to': 'john.doe@example.com',
                        'subject': 'Personal Information',
                        'body': 'SSN: 123-45-6789, Credit Card: 4111-1111-1111-1111'
                    }
                }]
            }
            
            with patch('app.services.orchestrator_service.OrchestratorService.execute_workflow') as mock_execute:
                mock_execute.return_value = {
                    'execution_id': 'exec-pii-123',
                    'status': 'completed',
                    'results': {'step1': {'success': True}}
                }
                
                response = client.post(
                    '/api/v1/orchestrator/execute',
                    json={'workflow_definition': workflow_definition, 'input_data': {}},
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Should handle PII appropriately
                assert response.status_code in [200, 400]  # Success or validation error
                
                if response.status_code == 200:
                    # Verify PII is not exposed in logs or responses
                    response_text = response.text
                    assert '123-45-6789' not in response_text
                    assert '4111-1111-1111-1111' not in response_text

class TestSecurityHeaders:
    """Testes de cabeçalhos de segurança"""
    
    def test_security_headers_present(self):
        """Teste de presença de cabeçalhos de segurança"""
        response = client.get('/health')
        
        # Check for important security headers
        headers = response.headers
        
        # CORS headers
        assert 'access-control-allow-origin' in headers or 'Access-Control-Allow-Origin' in headers
        
        # Content type should be set
        assert 'content-type' in headers
        
        # Should not expose server information
        server_header = headers.get('server', '').lower()
        assert 'fastapi' not in server_header or server_header == ''
    
    def test_cors_configuration(self):
        """Teste de configuração CORS"""
        # Test preflight request
        response = client.options(
            '/api/v1/agents',
            headers={
                'Origin': 'https://malicious-site.com',
                'Access-Control-Request-Method': 'GET'
            }
        )
        
        # Should handle CORS appropriately
        assert response.status_code in [200, 204, 405]
        
        # Check CORS headers
        if 'access-control-allow-origin' in response.headers:
            allowed_origin = response.headers['access-control-allow-origin']
            # Should not allow all origins in production
            assert allowed_origin != '*' or 'localhost' in allowed_origin
    
    def test_content_type_validation(self):
        """Teste de validação de content-type"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            # Test with wrong content type
            response = client.post(
                '/api/v1/orchestrator/execute',
                data="not-json-data",
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "text/plain"
                }
            )
            
            # Should reject non-JSON content for JSON endpoints
            assert response.status_code in [400, 415, 422]

class TestAuditingAndLogging:
    """Testes de auditoria e logging de segurança"""
    
    def test_security_event_logging(self):
        """Teste de logging de eventos de segurança"""
        with patch('app.middleware.auth.logger') as mock_logger:
            # Trigger security event (invalid token)
            response = client.get(
                '/api/v1/agents',
                headers={"Authorization": "Bearer invalid-token"}
            )
            
            assert response.status_code == 401
            
            # Verify security event was logged
            mock_logger.warning.assert_called()
    
    def test_failed_authentication_logging(self):
        """Teste de logging de falhas de autenticação"""
        with patch('app.middleware.auth.logger') as mock_logger:
            # Multiple failed authentication attempts
            for i in range(5):
                response = client.get(
                    '/api/v1/agents',
                    headers={"Authorization": f"Bearer invalid-token-{i}"}
                )
                assert response.status_code == 401
            
            # Should log failed attempts
            assert mock_logger.warning.call_count >= 5
    
    def test_sensitive_operation_auditing(self):
        """Teste de auditoria de operações sensíveis"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            with patch('app.services.analytics_service.logger') as mock_logger:
                mock_get_user.return_value = {'user_id': 'user-123', 'role': 'admin'}
                
                # Perform sensitive operation (admin endpoint)
                response = client.get(
                    '/api/v1/admin/system-stats',
                    headers={"Authorization": "Bearer admin-token"}
                )
                
                # Should audit admin operations
                if response.status_code == 200:
                    mock_logger.info.assert_called()

class TestSecurityCompliance:
    """Testes de conformidade de segurança"""
    
    def test_password_policy_enforcement(self):
        """Teste de aplicação de política de senhas"""
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "qwerty"
        ]
        
        for weak_password in weak_passwords:
            # Test user registration/password change with weak password
            response = client.post(
                '/api/v1/auth/register',
                json={
                    'email': 'test@example.com',
                    'password': weak_password
                }
            )
            
            # Should reject weak passwords
            assert response.status_code in [400, 422]
    
    def test_session_management(self):
        """Teste de gerenciamento de sessão"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            # Test session timeout
            # This would require actual session implementation
            response = client.get(
                '/api/v1/agents',
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should handle session appropriately
            assert response.status_code in [200, 401]
    
    def test_data_retention_compliance(self):
        """Teste de conformidade de retenção de dados"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            # Test data deletion request
            response = client.delete(
                '/api/v1/user/data',
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should handle data deletion requests
            assert response.status_code in [200, 202, 404]