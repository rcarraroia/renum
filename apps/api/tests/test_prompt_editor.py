"""
Testes para Prompt Editor API
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.services.prompt_editor_service import PromptTemplate, PromptVariable, PromptCategory, PromptType, PromptStatus

client = TestClient(app)

class TestPromptEditorAPI:
    """Testes para endpoints do Prompt Editor"""
    
    @pytest.fixture
    def admin_headers(self):
        """Headers com token de admin válido"""
        return {"Authorization": "Bearer valid-admin-token"}
    
    @pytest.fixture
    def sample_template_data(self):
        """Dados de exemplo para template"""
        return {
            "name": "Template de Teste",
            "description": "Template para testes automatizados",
            "category": "general",
            "type": "system",
            "content": "Você é um assistente especializado em {{domain}}. Responda de forma {{tone}}.",
            "variables": [
                {
                    "name": "domain",
                    "type": "string",
                    "description": "Domínio de especialização",
                    "required": True
                },
                {
                    "name": "tone",
                    "type": "string",
                    "description": "Tom de resposta",
                    "required": True,
                    "options": ["profissional", "casual", "técnico"]
                }
            ],
            "tags": ["teste", "geral"],
            "metadata": {"test": True}
        }
    
    @pytest.fixture
    def mock_template(self):
        """Mock de template para testes"""
        return PromptTemplate(
            template_id="test-template-001",
            name="Template de Teste",
            description="Template para testes",
            category=PromptCategory.GENERAL,
            type=PromptType.SYSTEM,
            content="Você é um assistente especializado em {{domain}}.",
            variables=[
                PromptVariable(
                    name="domain",
                    type="string",
                    description="Domínio de especialização",
                    required=True
                )
            ],
            tags=["teste"],
            version="1.0.0",
            status=PromptStatus.DRAFT,
            created_by="test-user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.create_template')
    def test_create_template_success(self, mock_create, mock_verify_token, admin_headers, sample_template_data, mock_template):
        """Teste de criação de template com sucesso"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_create.return_value = mock_template
        
        response = client.post(
            "/api/v1/prompt-editor/templates",
            json=sample_template_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['template_id'] == "test-template-001"
        assert data['name'] == "Template de Teste"
        assert data['status'] == "draft"
        mock_create.assert_called_once()
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.create_template')
    def test_create_template_validation_error(self, mock_create, mock_verify_token, admin_headers):
        """Teste de erro de validação na criação"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_create.side_effect = ValueError("Conteúdo inválido")
        
        invalid_data = {
            "name": "Template Inválido",
            "description": "Template com erro",
            "category": "general",
            "type": "system",
            "content": "{{undefined_var}}",  # Variável não definida
            "variables": [],
            "tags": []
        }
        
        response = client.post(
            "/api/v1/prompt-editor/templates",
            json=invalid_data,
            headers=admin_headers
        )
        
        assert response.status_code == 400
        assert "Conteúdo inválido" in response.json()['detail']
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.list_templates')
    def test_list_templates_success(self, mock_list, mock_verify_token, admin_headers, mock_template):
        """Teste de listagem de templates"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_list.return_value = [mock_template]
        
        response = client.get(
            "/api/v1/prompt-editor/templates?category=general&limit=10",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'templates' in data
        assert len(data['templates']) == 1
        assert data['templates'][0]['template_id'] == "test-template-001"
        assert 'total_count' in data
        assert 'categories' in data
        assert 'tags' in data
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.get_template')
    def test_get_template_success(self, mock_get, mock_verify_token, admin_headers, mock_template):
        """Teste de obtenção de template específico"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get.return_value = mock_template
        
        response = client.get(
            "/api/v1/prompt-editor/templates/test-template-001",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['template_id'] == "test-template-001"
        assert data['name'] == "Template de Teste"
        assert len(data['variables']) == 1
        assert data['variables'][0]['name'] == "domain"
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.get_template')
    def test_get_template_not_found(self, mock_get, mock_verify_token, admin_headers):
        """Teste de template não encontrado"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get.return_value = None
        
        response = client.get(
            "/api/v1/prompt-editor/templates/nonexistent",
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert "não encontrado" in response.json()['detail']
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.update_template')
    def test_update_template_success(self, mock_update, mock_verify_token, admin_headers, mock_template):
        """Teste de atualização de template"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_update.return_value = mock_template
        
        update_data = {
            "name": "Template Atualizado",
            "description": "Descrição atualizada",
            "status": "active"
        }
        
        response = client.put(
            "/api/v1/prompt-editor/templates/test-template-001?changelog=Atualização de teste",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['template_id'] == "test-template-001"
        mock_update.assert_called_once()
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.delete_template')
    def test_delete_template_success(self, mock_delete, mock_verify_token, admin_headers):
        """Teste de deleção de template"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_delete.return_value = True
        
        response = client.delete(
            "/api/v1/prompt-editor/templates/test-template-001",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "deletado com sucesso" in response.json()['message']
        mock_delete.assert_called_once_with(
            template_id="test-template-001",
            deleted_by="admin-1"
        )
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.render_prompt')
    def test_render_prompt_success(self, mock_render, mock_verify_token, admin_headers):
        """Teste de renderização de prompt"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_render.return_value = (
            "Você é um assistente especializado em tecnologia.",
            {
                "template_id": "test-template-001",
                "version": "1.0.0",
                "character_count": 45,
                "word_count": 7
            }
        )
        
        render_data = {
            "template_id": "test-template-001",
            "variables": {
                "domain": "tecnologia"
            }
        }
        
        response = client.post(
            "/api/v1/prompt-editor/templates/test-template-001/render",
            json=render_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "rendered_content" in data
        assert "metadata" in data
        assert data['rendered_content'] == "Você é um assistente especializado em tecnologia."
        assert data['metadata']['character_count'] == 45
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.test_prompt_in_sandbox')
    def test_test_prompt_in_sandbox_success(self, mock_test, mock_verify_token, admin_headers):
        """Teste de execução de prompt no sandbox"""
        from app.services.prompt_editor_service import PromptTestResult
        
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        
        test_result = PromptTestResult(
            test_id="test-123",
            template_id="test-template-001",
            version_id="1.0.0",
            input_data={"variables": {"domain": "tecnologia"}, "test_input": "Olá"},
            rendered_prompt="Você é um assistente especializado em tecnologia.",
            test_response="Olá! Como posso ajudá-lo com tecnologia?",
            execution_time_ms=1250.5,
            success=True,
            error_message=None,
            metrics={"response_length": 42, "tokens_used": 15},
            tested_by="admin-1",
            tested_at=datetime.utcnow()
        )
        
        mock_test.return_value = test_result
        
        test_data = {
            "template_id": "test-template-001",
            "variables": {"domain": "tecnologia"},
            "test_input": "Olá"
        }
        
        response = client.post(
            "/api/v1/prompt-editor/templates/test-template-001/test",
            json=test_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['test_id'] == "test-123"
        assert data['success'] == True
        assert data['execution_time_ms'] == 1250.5
        assert "Olá! Como posso ajudá-lo" in data['test_response']
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.get_template')
    def test_validate_prompt_success(self, mock_get, mock_verify_token, admin_headers, mock_template):
        """Teste de validação de prompt"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_get.return_value = mock_template
        
        response = client.post(
            "/api/v1/prompt-editor/templates/test-template-001/validate",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'valid' in data
        assert 'errors' in data
        assert 'warnings' in data
        assert 'content_variables' in data
        assert 'defined_variables' in data
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.clone_template')
    def test_clone_template_success(self, mock_clone, mock_verify_token, admin_headers, mock_template):
        """Teste de clonagem de template"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        
        # Criar template clonado
        cloned_template = PromptTemplate(
            template_id="cloned-template-001",
            name="Template Clonado",
            description="Clonado de: Template de Teste",
            category=PromptCategory.GENERAL,
            type=PromptType.SYSTEM,
            content="Você é um assistente especializado em {{domain}}.",
            variables=[
                PromptVariable(
                    name="domain",
                    type="string",
                    description="Domínio de especialização",
                    required=True
                )
            ],
            tags=["teste", "clonado"],
            version="1.0.0",
            status=PromptStatus.DRAFT,
            created_by="admin-1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={"cloned_from": "test-template-001"}
        )
        
        mock_clone.return_value = cloned_template
        
        clone_data = {
            "template_id": "test-template-001",
            "new_name": "Template Clonado",
            "modifications": {
                "tags": ["teste", "clonado"]
            }
        }
        
        response = client.post(
            "/api/v1/prompt-editor/templates/test-template-001/clone",
            json=clone_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['template_id'] == "cloned-template-001"
        assert data['name'] == "Template Clonado"
        assert "clonado" in data['tags']
        mock_clone.assert_called_once()
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.export_template')
    def test_export_template_success(self, mock_export, mock_verify_token, admin_headers):
        """Teste de exportação de template"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        
        export_data = {
            "template_id": "test-template-001",
            "name": "Template de Teste",
            "description": "Template para testes",
            "category": "general",
            "type": "system",
            "content": "Conteúdo do template",
            "variables": [],
            "tags": ["teste"],
            "version": "1.0.0",
            "status": "draft",
            "created_by": "test-user",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "versions": []
        }
        
        mock_export.return_value = export_data
        
        response = client.get(
            "/api/v1/prompt-editor/templates/test-template-001/export",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['template_id'] == "test-template-001"
        assert data['name'] == "Template de Teste"
        assert 'versions' in data
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.import_template')
    def test_import_template_success(self, mock_import, mock_verify_token, admin_headers, mock_template):
        """Teste de importação de template"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        mock_import.return_value = mock_template
        
        import_data = {
            "template_data": {
                "name": "Template Importado",
                "description": "Template importado de arquivo",
                "category": "general",
                "type": "system",
                "content": "Conteúdo importado",
                "variables": [],
                "tags": ["importado"]
            },
            "overwrite": False
        }
        
        response = client.post(
            "/api/v1/prompt-editor/templates/import",
            json=import_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['template_id'] == "test-template-001"
        mock_import.assert_called_once()
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    @patch('app.services.prompt_editor_service.prompt_editor_service.get_template_analytics')
    def test_get_template_analytics_success(self, mock_analytics, mock_verify_token, admin_headers):
        """Teste de obtenção de analytics de template"""
        mock_verify_token.return_value = {'user_id': 'admin-1', 'role': 'admin'}
        
        analytics_data = {
            "template_id": "test-template-001",
            "template_name": "Template de Teste",
            "total_usage": 156,
            "total_tests": 23,
            "successful_tests": 21,
            "success_rate": 91.3,
            "avg_execution_time_ms": 1245.6,
            "total_versions": 3,
            "current_version": "1.2.0",
            "rating": 4.2,
            "usage_by_day": {
                "2024-01-15": 12,
                "2024-01-14": 8
            },
            "last_used": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-10T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
        
        mock_analytics.return_value = analytics_data
        
        response = client.get(
            "/api/v1/prompt-editor/templates/test-template-001/analytics",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['template_id'] == "test-template-001"
        assert data['total_usage'] == 156
        assert data['success_rate'] == 91.3
        assert 'usage_by_day' in data
    
    def test_unauthorized_access(self):
        """Teste de acesso não autorizado"""
        response = client.get("/api/v1/prompt-editor/templates")
        
        assert response.status_code == 401
    
    @patch('app.middleware.admin_auth.admin_auth.verify_admin_token')
    def test_insufficient_permissions(self, mock_verify_token):
        """Teste de permissões insuficientes"""
        mock_verify_token.return_value = {
            'user_id': 'user-1', 
            'role': 'user',
            'permissions': ['agents:read']  # Sem permissão de escrita
        }
        
        headers = {"Authorization": "Bearer user-token"}
        
        template_data = {
            "name": "Novo Template",
            "description": "Teste",
            "category": "general",
            "type": "system",
            "content": "Conteúdo",
            "variables": [],
            "tags": []
        }
        
        response = client.post(
            "/api/v1/prompt-editor/templates",
            json=template_data,
            headers=headers
        )
        
        assert response.status_code == 403