"""
Testes para endpoints de distribuição de chaves públicas
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.services.signature_service import signature_service

client = TestClient(app)

class TestPublicKeysEndpoints:
    """Testes dos endpoints de chaves públicas"""
    
    def test_list_public_keys_success(self):
        """Teste de listagem de chaves públicas com sucesso"""
        with patch.object(signature_service, 'list_public_keys') as mock_list:
            mock_list.return_value = [
                {
                    'key_id': 'renum-signing-key-2024-001',
                    'key_type': 'rsa',
                    'algorithm': 'RS256',
                    'created_at': datetime(2024, 1, 15, 10, 30, 0),
                    'expires_at': datetime(2025, 1, 15, 10, 30, 0),
                    'is_active': True,
                    'usage': ['verify'],
                    'fingerprint': 'sha256:1234567890abcdef...'
                }
            ]
            
            response = client.get('/api/v1/keys/')
            
            assert response.status_code == 200
            data = response.json()
            
            assert 'keys' in data
            assert 'total_count' in data
            assert 'active_count' in data
            assert len(data['keys']) == 1
            assert data['total_count'] == 1
            assert data['active_count'] == 1
            
            key = data['keys'][0]
            assert key['key_id'] == 'renum-signing-key-2024-001'
            assert key['key_type'] == 'rsa'
            assert key['algorithm'] == 'RS256'
            assert key['is_active'] is True
    
    def test_list_public_keys_with_filters(self):
        """Teste de listagem com filtros"""
        with patch.object(signature_service, 'list_public_keys') as mock_list:
            mock_list.return_value = []
            
            # Teste com filtro de tipo
            response = client.get('/api/v1/keys/?key_type=rsa&active_only=true')
            assert response.status_code == 200
            
            # Verificar se filtros foram passados
            mock_list.assert_called_with(key_type='rsa', active_only=True)
    
    def test_get_public_key_success(self):
        """Teste de obtenção de chave específica com sucesso"""
        with patch.object(signature_service, 'get_public_key') as mock_get:
            mock_get.return_value = {
                'key_id': 'renum-signing-key-2024-001',
                'key_type': 'rsa',
                'algorithm': 'RS256',
                'public_key': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG...\n-----END PUBLIC KEY-----',
                'created_at': datetime(2024, 1, 15, 10, 30, 0),
                'expires_at': datetime(2025, 1, 15, 10, 30, 0),
                'is_active': True,
                'usage': ['verify'],
                'fingerprint': 'sha256:1234567890abcdef...'
            }
            
            response = client.get('/api/v1/keys/renum-signing-key-2024-001')
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['key_id'] == 'renum-signing-key-2024-001'
            assert data['key_type'] == 'rsa'
            assert data['format'] == 'pem'
            assert '-----BEGIN PUBLIC KEY-----' in data['public_key']
    
    def test_get_public_key_not_found(self):
        """Teste de chave não encontrada"""
        with patch.object(signature_service, 'get_public_key') as mock_get:
            mock_get.return_value = None
            
            response = client.get('/api/v1/keys/nonexistent-key')
            
            assert response.status_code == 404
            assert 'not found' in response.json()['detail']
    
    def test_get_public_key_different_formats(self):
        """Teste de obtenção em diferentes formatos"""
        with patch.object(signature_service, 'get_public_key') as mock_get:
            # Formato JWK
            mock_get.return_value = {
                'key_id': 'test-key',
                'key_type': 'rsa',
                'algorithm': 'RS256',
                'public_key': {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": "test-key",
                    "n": "example_modulus",
                    "e": "AQAB"
                },
                'created_at': datetime.utcnow(),
                'is_active': True,
                'usage': ['verify'],
                'fingerprint': 'sha256:test'
            }
            
            response = client.get('/api/v1/keys/test-key?format=jwk')
            
            assert response.status_code == 200
            data = response.json()
            assert data['format'] == 'jwk'
            assert isinstance(data['public_key'], dict)
            assert data['public_key']['kty'] == 'RSA'
    
    def test_get_public_key_invalid_format(self):
        """Teste de formato inválido"""
        response = client.get('/api/v1/keys/test-key?format=invalid')
        
        assert response.status_code == 400
        assert 'Invalid format' in response.json()['detail']
    
    def test_get_jwks_success(self):
        """Teste do endpoint JWKS"""
        with patch.object(signature_service, 'get_jwks') as mock_jwks:
            mock_jwks.return_value = {
                "keys": [
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "key_ops": ["verify"],
                        "alg": "RS256",
                        "kid": "renum-signing-key-2024-001",
                        "n": "example_modulus",
                        "e": "AQAB"
                    }
                ]
            }
            
            response = client.get('/api/v1/keys/.well-known/jwks.json')
            
            assert response.status_code == 200
            data = response.json()
            
            assert 'keys' in data
            assert len(data['keys']) == 1
            assert data['keys'][0]['kty'] == 'RSA'
            assert data['keys'][0]['kid'] == 'renum-signing-key-2024-001'
    
    def test_verify_key_status_success(self):
        """Teste de verificação de status da chave"""
        with patch.object(signature_service, 'get_public_key') as mock_get:
            mock_get.return_value = {
                'key_id': 'test-key',
                'is_active': True,
                'expires_at': datetime.utcnow() + timedelta(days=30)
            }
            
            response = client.get('/api/v1/keys/test-key/verify')
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['key_id'] == 'test-key'
            assert data['is_active'] is True
            assert data['is_expired'] is False
            assert data['is_valid'] is True
            assert data['can_verify'] is True
    
    def test_verify_key_status_expired(self):
        """Teste de chave expirada"""
        with patch.object(signature_service, 'get_public_key') as mock_get:
            mock_get.return_value = {
                'key_id': 'expired-key',
                'is_active': True,
                'expires_at': datetime.utcnow() - timedelta(days=1)
            }
            
            response = client.get('/api/v1/keys/expired-key/verify')
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['is_expired'] is True
            assert data['is_valid'] is False
            assert data['can_verify'] is True  # Ainda pode verificar manifests antigos
    
    def test_verify_key_status_not_found(self):
        """Teste de verificação de chave não encontrada"""
        with patch.object(signature_service, 'get_public_key') as mock_get:
            mock_get.return_value = None
            
            response = client.get('/api/v1/keys/nonexistent/verify')
            
            assert response.status_code == 404
    
    def test_get_key_fingerprint_success(self):
        """Teste de obtenção de fingerprint"""
        with patch.object(signature_service, 'get_key_fingerprint') as mock_fingerprint:
            mock_fingerprint.return_value = '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
            
            response = client.get('/api/v1/keys/test-key/fingerprint')
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['key_id'] == 'test-key'
            assert data['algorithm'] == 'sha256'
            assert data['fingerprint'] == '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
            assert data['format'] == 'hex'
    
    def test_get_key_fingerprint_different_algorithms(self):
        """Teste de fingerprint com diferentes algoritmos"""
        with patch.object(signature_service, 'get_key_fingerprint') as mock_fingerprint:
            mock_fingerprint.return_value = 'abcdef1234567890'
            
            response = client.get('/api/v1/keys/test-key/fingerprint?algorithm=sha1')
            
            assert response.status_code == 200
            data = response.json()
            assert data['algorithm'] == 'sha1'
            
            # Verificar se foi chamado com algoritmo correto
            mock_fingerprint.assert_called_with('test-key', 'sha1')
    
    def test_get_key_fingerprint_invalid_algorithm(self):
        """Teste de algoritmo de fingerprint inválido"""
        response = client.get('/api/v1/keys/test-key/fingerprint?algorithm=invalid')
        
        assert response.status_code == 400
        assert 'Invalid algorithm' in response.json()['detail']
    
    def test_get_supported_algorithms_success(self):
        """Teste de obtenção de algoritmos suportados"""
        with patch.object(signature_service, 'get_supported_algorithms') as mock_algorithms:
            mock_algorithms.return_value = {
                'signature': ['RS256', 'RS384', 'RS512', 'ES256'],
                'hash': ['sha256', 'sha384', 'sha512'],
                'key_types': ['rsa', 'ecdsa']
            }
            
            response = client.get('/api/v1/keys/algorithms/supported')
            
            assert response.status_code == 200
            data = response.json()
            
            assert 'signature_algorithms' in data
            assert 'hash_algorithms' in data
            assert 'key_types' in data
            assert 'formats' in data
            
            assert 'RS256' in data['signature_algorithms']
            assert 'sha256' in data['hash_algorithms']
            assert 'rsa' in data['key_types']
            assert 'pem' in data['formats']
    
    def test_keys_health_check_healthy(self):
        """Teste de health check saudável"""
        with patch.object(signature_service, 'list_public_keys') as mock_list:
            mock_list.return_value = [
                {'key_id': 'key1', 'is_active': True},
                {'key_id': 'key2', 'is_active': True}
            ]
            
            response = client.get('/api/v1/keys/health')
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['status'] == 'healthy'
            assert data['active_keys_count'] == 2
            assert data['service'] == 'public-key-distribution'
    
    def test_keys_health_check_degraded(self):
        """Teste de health check degradado (sem chaves ativas)"""
        with patch.object(signature_service, 'list_public_keys') as mock_list:
            mock_list.return_value = []
            
            response = client.get('/api/v1/keys/health')
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['status'] == 'degraded'
            assert data['active_keys_count'] == 0
    
    def test_keys_health_check_unhealthy(self):
        """Teste de health check não saudável (erro no serviço)"""
        with patch.object(signature_service, 'list_public_keys') as mock_list:
            mock_list.side_effect = Exception("Service error")
            
            response = client.get('/api/v1/keys/health')
            
            assert response.status_code == 503
            data = response.json()
            
            assert data['status'] == 'unhealthy'
            assert 'error' in data

class TestPublicKeysAuthentication:
    """Testes de autenticação nos endpoints de chaves públicas"""
    
    def test_endpoints_are_public(self):
        """Teste que endpoints de chaves públicas são acessíveis sem autenticação"""
        # Todos os endpoints de chaves públicas devem ser acessíveis sem token
        
        with patch.object(signature_service, 'list_public_keys') as mock_list:
            mock_list.return_value = []
            
            # Sem header de autorização
            response = client.get('/api/v1/keys/')
            assert response.status_code == 200
        
        with patch.object(signature_service, 'get_jwks') as mock_jwks:
            mock_jwks.return_value = {"keys": []}
            
            response = client.get('/api/v1/keys/.well-known/jwks.json')
            assert response.status_code == 200
    
    def test_optional_authentication_logging(self):
        """Teste que autenticação opcional funciona para logging"""
        with patch.object(signature_service, 'list_public_keys') as mock_list:
            mock_list.return_value = []
            
            # Com token válido (deve logar user_id)
            with patch('app.middleware.auth.jwt_auth.get_current_user_optional') as mock_auth:
                mock_auth.return_value = {'user_id': 'user-123', 'role': 'user'}
                
                response = client.get(
                    '/api/v1/keys/',
                    headers={"Authorization": "Bearer valid-token"}
                )
                assert response.status_code == 200
            
            # Sem token (deve funcionar normalmente)
            response = client.get('/api/v1/keys/')
            assert response.status_code == 200

class TestPublicKeysErrorHandling:
    """Testes de tratamento de erros"""
    
    def test_service_error_handling(self):
        """Teste de tratamento de erros do serviço"""
        with patch.object(signature_service, 'list_public_keys') as mock_list:
            mock_list.side_effect = Exception("Database connection failed")
            
            response = client.get('/api/v1/keys/')
            
            assert response.status_code == 500
            assert 'Failed to retrieve public keys' in response.json()['detail']
    
    def test_invalid_key_id_format(self):
        """Teste de formato inválido de key_id"""
        with patch.object(signature_service, 'get_public_key') as mock_get:
            mock_get.return_value = None
            
            # Key ID com caracteres especiais
            response = client.get('/api/v1/keys/invalid@key#id')
            assert response.status_code == 404
    
    def test_concurrent_requests_handling(self):
        """Teste de tratamento de requisições concorrentes"""
        import threading
        import time
        
        results = []
        
        def make_request():
            with patch.object(signature_service, 'list_public_keys') as mock_list:
                mock_list.return_value = [{'key_id': 'test', 'is_active': True}]
                
                response = client.get('/api/v1/keys/')
                results.append(response.status_code)
        
        # Fazer múltiplas requisições concorrentes
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Todas as requisições devem ter sucesso
        assert all(status == 200 for status in results)
        assert len(results) == 5