"""
Testes para endpoints de execuções.
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import json

from app.main import app

client = TestClient(app)


class TestExecutionsEndpoints:
    """Testes para endpoints de gerenciamento de execuções."""
    
    @pytest.fixture
    def auth_headers(self):
        """Headers de autenticação para testes."""
        return {"Authorization": "Bearer test-token"}
    
    @pytest.fixture
    def sample_execution_data(self):
        """Dados de exemplo para execução."""
        return {
            "input_data": {
                "prompt": "Create a marketing campaign for product X",
                "context": {
                    "product": "Product X",
                    "target_audience": "Young professionals"
                }
            },
            "execution_config": {
                "timeout_minutes": 30,
                "parallel_limit": 3,
                "retry_failed": True,
                "max_retries": 2
            }
        }
    
    def test_start_execution_team_not_found(self, auth_headers, sample_execution_data):
        """Testa início de execução com equipe inexistente."""
        team_id = str(uuid4())
        response = client.post(
            f"/api/v1/teams/{team_id}/execute",
            json=sample_execution_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_start_execution_invalid_data(self, auth_headers):
        """Testa início de execução com dados inválidos."""
        team_id = str(uuid4())
        invalid_data = {
            "input_data": {},  # Dados vazios
            "execution_config": {
                "timeout_minutes": -1,  # Valor inválido
                "parallel_limit": 0,    # Valor inválido
                "max_retries": -1       # Valor inválido
            }
        }
        
        response = client.post(
            f"/api/v1/teams/{team_id}/execute",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_start_execution_without_config(self, auth_headers):
        """Testa início de execução sem configuração (deve usar padrões)."""
        team_id = str(uuid4())
        minimal_data = {
            "input_data": {
                "prompt": "Test prompt"
            }
        }
        
        response = client.post(
            f"/api/v1/teams/{team_id}/execute",
            json=minimal_data,
            headers=auth_headers
        )
        
        # Deve falhar por equipe não encontrada, mas validação deve passar
        assert response.status_code == 404
    
    def test_list_executions_empty(self, auth_headers):
        """Testa listagem de execuções quando não há nenhuma."""
        response = client.get("/api/v1/executions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "executions" in data
        assert "pagination" in data
        assert isinstance(data["executions"], list)
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10
    
    def test_list_executions_with_filters(self, auth_headers):
        """Testa listagem de execuções com filtros."""
        team_id = str(uuid4())
        response = client.get(
            f"/api/v1/executions?team_id={team_id}&status=running&page=1&limit=5",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "executions" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 5
    
    def test_get_execution_not_found(self, auth_headers):
        """Testa busca de execução inexistente."""
        execution_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{execution_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_cancel_execution_not_found(self, auth_headers):
        """Testa cancelamento de execução inexistente."""
        execution_id = str(uuid4())
        response = client.post(f"/api/v1/executions/{execution_id}/cancel", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_start_execution_without_auth(self, sample_execution_data):
        """Testa início de execução sem autenticação."""
        team_id = str(uuid4())
        response = client.post(f"/api/v1/teams/{team_id}/execute", json=sample_execution_data)
        
        assert response.status_code == 403
    
    def test_list_executions_without_auth(self):
        """Testa listagem de execuções sem autenticação."""
        response = client.get("/api/v1/executions")
        
        assert response.status_code == 403


class TestExecutionsValidation:
    """Testes específicos para validação de dados de execução."""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_execution_config_timeout_validation(self, auth_headers):
        """Testa validação do timeout de execução."""
        team_id = str(uuid4())
        
        # Timeout muito alto
        data = {
            "input_data": {"prompt": "test"},
            "execution_config": {
                "timeout_minutes": 200  # Máximo é 120
            }
        }
        
        response = client.post(f"/api/v1/teams/{team_id}/execute", json=data, headers=auth_headers)
        assert response.status_code == 422
        
        # Timeout muito baixo
        data["execution_config"]["timeout_minutes"] = 0
        response = client.post(f"/api/v1/teams/{team_id}/execute", json=data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_execution_config_parallel_limit_validation(self, auth_headers):
        """Testa validação do limite paralelo."""
        team_id = str(uuid4())
        
        # Limite muito alto
        data = {
            "input_data": {"prompt": "test"},
            "execution_config": {
                "parallel_limit": 15  # Máximo é 10
            }
        }
        
        response = client.post(f"/api/v1/teams/{team_id}/execute", json=data, headers=auth_headers)
        assert response.status_code == 422
        
        # Limite muito baixo
        data["execution_config"]["parallel_limit"] = 0
        response = client.post(f"/api/v1/teams/{team_id}/execute", json=data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_execution_config_max_retries_validation(self, auth_headers):
        """Testa validação do número máximo de tentativas."""
        team_id = str(uuid4())
        
        # Muitas tentativas
        data = {
            "input_data": {"prompt": "test"},
            "execution_config": {
                "max_retries": 10  # Máximo é 5
            }
        }
        
        response = client.post(f"/api/v1/teams/{team_id}/execute", json=data, headers=auth_headers)
        assert response.status_code == 422
        
        # Tentativas negativas
        data["execution_config"]["max_retries"] = -1
        response = client.post(f"/api/v1/teams/{team_id}/execute", json=data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_input_data_required(self, auth_headers):
        """Testa que input_data é obrigatório."""
        team_id = str(uuid4())
        
        # Sem input_data
        data = {
            "execution_config": {
                "timeout_minutes": 30
            }
        }
        
        response = client.post(f"/api/v1/teams/{team_id}/execute", json=data, headers=auth_headers)
        assert response.status_code == 422


class TestExecutionsStatusFlow:
    """Testes para fluxo de status de execuções."""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_execution_status_enum_validation(self, auth_headers):
        """Testa validação dos valores de status."""
        # Testa filtro com status válido
        response = client.get("/api/v1/executions?status=running", headers=auth_headers)
        assert response.status_code == 200
        
        response = client.get("/api/v1/executions?status=completed", headers=auth_headers)
        assert response.status_code == 200
        
        response = client.get("/api/v1/executions?status=failed", headers=auth_headers)
        assert response.status_code == 200
        
        response = client.get("/api/v1/executions?status=cancelled", headers=auth_headers)
        assert response.status_code == 200
        
        # Testa filtro com status inválido
        response = client.get("/api/v1/executions?status=invalid_status", headers=auth_headers)
        assert response.status_code == 422


class TestExecutionsIntegration:
    """Testes de integração para execuções."""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_execution_workflow_sequential(self, auth_headers):
        """Testa que execução sequencial é suportada."""
        # Este teste seria mais completo com mock do Suna Backend
        pass
    
    def test_execution_workflow_parallel(self, auth_headers):
        """Testa que execução paralela é suportada."""
        # Este teste seria mais completo com mock do Suna Backend
        pass
    
    def test_execution_error_handling(self, auth_headers):
        """Testa tratamento de erros durante execução."""
        # Este teste seria mais completo com mock do Suna Backend
        pass