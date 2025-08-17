"""
Testes para endpoints de teams.
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import json

from app.main import app

client = TestClient(app)


class TestTeamsEndpoints:
    """Testes para endpoints de gerenciamento de equipes."""
    
    @pytest.fixture
    def auth_headers(self):
        """Headers de autenticação para testes."""
        # TODO: Implementar autenticação real nos testes
        return {"Authorization": "Bearer test-token"}
    
    @pytest.fixture
    def sample_team_data(self):
        """Dados de exemplo para criação de equipe."""
        return {
            "name": "Test Marketing Team",
            "description": "Team for testing marketing automation",
            "workflow_type": "sequential",
            "agents": [
                {
                    "agent_id": str(uuid4()),
                    "role": "leader",
                    "order": 1,
                    "config": {
                        "input_source": "initial_prompt",
                        "conditions": [],
                        "timeout_minutes": 30
                    }
                },
                {
                    "agent_id": str(uuid4()),
                    "role": "member",
                    "order": 2,
                    "config": {
                        "input_source": "previous_output",
                        "conditions": [],
                        "timeout_minutes": 20
                    }
                }
            ]
        }
    
    def test_create_team_success(self, auth_headers, sample_team_data):
        """Testa criação bem-sucedida de equipe."""
        response = client.post(
            "/api/v1/teams",
            json=sample_team_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["name"] == sample_team_data["name"]
        assert data["description"] == sample_team_data["description"]
        assert data["workflow_type"] == sample_team_data["workflow_type"]
        assert len(data["agents"]) == len(sample_team_data["agents"])
        assert data["status"] == "active"
        assert data["agents_count"] == 2
    
    def test_create_team_invalid_data(self, auth_headers):
        """Testa criação de equipe com dados inválidos."""
        invalid_data = {
            "name": "",  # Nome vazio
            "workflow_type": "invalid_type",
            "agents": []  # Lista vazia de agentes
        }
        
        response = client.post(
            "/api/v1/teams",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_team_duplicate_agent_order(self, auth_headers):
        """Testa criação de equipe com ordens duplicadas de agentes."""
        invalid_data = {
            "name": "Test Team",
            "workflow_type": "sequential",
            "agents": [
                {
                    "agent_id": str(uuid4()),
                    "role": "leader",
                    "order": 1,
                    "config": {"input_source": "initial_prompt", "conditions": []}
                },
                {
                    "agent_id": str(uuid4()),
                    "role": "member",
                    "order": 1,  # Ordem duplicada
                    "config": {"input_source": "previous_output", "conditions": []}
                }
            ]
        }
        
        response = client.post(
            "/api/v1/teams",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_list_teams_empty(self, auth_headers):
        """Testa listagem de equipes quando não há nenhuma."""
        response = client.get("/api/v1/teams", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "teams" in data
        assert "pagination" in data
        assert isinstance(data["teams"], list)
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10
    
    def test_list_teams_with_pagination(self, auth_headers):
        """Testa listagem de equipes com paginação."""
        response = client.get(
            "/api/v1/teams?page=2&limit=5",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["limit"] == 5
    
    def test_list_teams_with_search(self, auth_headers):
        """Testa listagem de equipes com busca."""
        response = client.get(
            "/api/v1/teams?search=marketing",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "teams" in data
        assert "pagination" in data
    
    def test_get_team_not_found(self, auth_headers):
        """Testa busca de equipe inexistente."""
        team_id = str(uuid4())
        response = client.get(f"/api/v1/teams/{team_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_team_not_found(self, auth_headers):
        """Testa atualização de equipe inexistente."""
        team_id = str(uuid4())
        update_data = {"name": "Updated Team Name"}
        
        response = client.put(
            f"/api/v1/teams/{team_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_delete_team_not_found(self, auth_headers):
        """Testa remoção de equipe inexistente."""
        team_id = str(uuid4())
        response = client.delete(f"/api/v1/teams/{team_id}", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_create_team_without_auth(self, sample_team_data):
        """Testa criação de equipe sem autenticação."""
        response = client.post("/api/v1/teams", json=sample_team_data)
        
        assert response.status_code == 403  # Forbidden
    
    def test_list_teams_without_auth(self):
        """Testa listagem de equipes sem autenticação."""
        response = client.get("/api/v1/teams")
        
        assert response.status_code == 403


class TestTeamsValidation:
    """Testes específicos para validação de dados de equipes."""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_team_name_validation(self, auth_headers):
        """Testa validação do nome da equipe."""
        # Nome muito longo
        long_name = "x" * 101
        data = {
            "name": long_name,
            "workflow_type": "sequential",
            "agents": [{
                "agent_id": str(uuid4()),
                "role": "leader",
                "order": 1,
                "config": {"input_source": "initial_prompt", "conditions": []}
            }]
        }
        
        response = client.post("/api/v1/teams", json=data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_team_description_validation(self, auth_headers):
        """Testa validação da descrição da equipe."""
        # Descrição muito longa
        long_description = "x" * 501
        data = {
            "name": "Test Team",
            "description": long_description,
            "workflow_type": "sequential",
            "agents": [{
                "agent_id": str(uuid4()),
                "role": "leader",
                "order": 1,
                "config": {"input_source": "initial_prompt", "conditions": []}
            }]
        }
        
        response = client.post("/api/v1/teams", json=data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_team_agents_limit(self, auth_headers):
        """Testa limite de agentes por equipe."""
        # Mais de 10 agentes
        agents = []
        for i in range(11):
            agents.append({
                "agent_id": str(uuid4()),
                "role": "member",
                "order": i + 1,
                "config": {"input_source": "initial_prompt", "conditions": []}
            })
        
        data = {
            "name": "Test Team",
            "workflow_type": "sequential",
            "agents": agents
        }
        
        response = client.post("/api/v1/teams", json=data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_workflow_type_validation(self, auth_headers):
        """Testa validação do tipo de workflow."""
        data = {
            "name": "Test Team",
            "workflow_type": "invalid_workflow",
            "agents": [{
                "agent_id": str(uuid4()),
                "role": "leader",
                "order": 1,
                "config": {"input_source": "initial_prompt", "conditions": []}
            }]
        }
        
        response = client.post("/api/v1/teams", json=data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_agent_role_validation(self, auth_headers):
        """Testa validação do papel do agente."""
        data = {
            "name": "Test Team",
            "workflow_type": "sequential",
            "agents": [{
                "agent_id": str(uuid4()),
                "role": "invalid_role",
                "order": 1,
                "config": {"input_source": "initial_prompt", "conditions": []}
            }]
        }
        
        response = client.post("/api/v1/teams", json=data, headers=auth_headers)
        assert response.status_code == 422