"""
Testes para Sistema de Sandbox
Testes abrangentes do ambiente isolado de execução de agentes
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import tempfile
import shutil

from app.services.sandbox_service import sandbox_service, SandboxService
from app.schemas.sandbox import (
    SandboxExecutionRequest,
    ResourceQuota,
    MockIntegrationConfig,
    MockIntegrationEndpoint
)

class TestSandboxService:
    """Testes do serviço de sandbox"""
    
    @pytest.fixture
    def sandbox_service_instance(self):
        """Fixture do serviço de sandbox"""
        service = SandboxService()
        # Mock Docker client para testes
        service.docker_client = MagicMock()
        return service
    
    @pytest.fixture
    def sample_execution_request(self):
        """Requisição de execução de exemplo"""
        return SandboxExecutionRequest(
            agent_id="sa-whatsapp",
            capability="send_message",
            input_data={
                "phone_number": "+5511999999999",
                "message": "Test message from sandbox"
            },
            resource_quota=ResourceQuota(
                cpu_cores=0.25,
                memory_mb=256,
                disk_mb=512,
                max_execution_time_seconds=60
            ),
            mock_integrations={
                "whatsapp": MockIntegrationConfig(
                    service_name="whatsapp",
                    endpoints=[
                        MockIntegrationEndpoint(
                            endpoint="/messages",
                            method="POST",
                            response={"messages": [{"id": "wamid_test_123"}]},
                            delay_ms=100
                        )
                    ]
                )
            },
            timeout_seconds=60
        )
    
    @pytest.mark.asyncio
    async def test_sandbox_initialization(self, sandbox_service_instance):
        """Teste de inicialização do serviço de sandbox"""
        service = sandbox_service_instance
        
        # Mock Docker operations
        service.docker_client.networks.get.side_effect = Exception("Network not found")
        service.docker_client.networks.create.return_value = MagicMock(id="network-123")
        service.docker_client.images.get.return_value = MagicMock()
        
        await service.initialize()
        
        # Verificar se rede foi criada
        service.docker_client.networks.create.assert_called_once()
        
        # Verificar se imagem base foi verificada
        service.docker_client.images.get.assert_called_with(service.base_image)
    
    @pytest.mark.asyncio
    async def test_create_sandbox_success(self, sandbox_service_instance, sample_execution_request):
        """Teste de criação bem-sucedida de sandbox"""
        service = sandbox_service_instance
        
        # Mock container creation
        mock_container = MagicMock()
        mock_container.id = "container-123"
        service.docker_client.containers.create.return_value = mock_container
        
        # Mock temp directory
        with patch('tempfile.mkdtemp') as mock_mkdtemp:
            mock_mkdtemp.return_value = "/tmp/sandbox_test"
            
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', create=True):
                    sandbox_id = await service.create_sandbox(
                        execution_request=sample_execution_request,
                        user_id="user-123"
                    )
        
        assert sandbox_id is not None
        assert sandbox_id in service.active_sandboxes
        
        # Verificar se container foi criado
        service.docker_client.containers.create.assert_called_once()
        
        # Verificar informações do sandbox
        sandbox_info = service.active_sandboxes[sandbox_id]
        assert sandbox_info['user_id'] == "user-123"
        assert sandbox_info['status'] == 'created'
    
    @pytest.mark.asyncio
    async def test_create_sandbox_limit_exceeded(self, sandbox_service_instance, sample_execution_request):
        """Teste de limite de sandboxes concorrentes"""
        service = sandbox_service_instance
        service.max_concurrent_sandboxes = 1
        
        # Adicionar sandbox ativo para simular limite
        service.active_sandboxes['existing-sandbox'] = {
            'container': MagicMock(),
            'user_id': 'user-456',
            'status': 'running'
        }
        
        with pytest.raises(ValueError, match="Maximum concurrent sandboxes limit reached"):
            await service.create_sandbox(
                execution_request=sample_execution_request,
                user_id="user-123"
            )
    
    @pytest.mark.asyncio
    async def test_execute_sandbox_success(self, sandbox_service_instance):
        """Teste de execução bem-sucedida de sandbox"""
        service = sandbox_service_instance
        sandbox_id = "test-sandbox-123"
        
        # Mock container
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 0}
        mock_container.logs.return_value = b'{"success": true, "result": {"message_id": "test-123"}}'
        mock_container.get_archive.return_value = (iter([b'mock_tar_data']), {})
        
        # Mock sandbox info
        service.active_sandboxes[sandbox_id] = {
            'container': mock_container,
            'config': MagicMock(timeout_seconds=60),
            'user_id': 'user-123',
            'created_at': datetime.utcnow(),
            'status': 'created'
        }
        
        # Mock tar extraction
        with patch('tarfile.open'):
            with patch('json.loads') as mock_json_loads:
                mock_json_loads.return_value = {
                    "success": True,
                    "result": {"message_id": "test-123"},
                    "execution_time_ms": 1500
                }
                
                result = await service.execute_sandbox(sandbox_id)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.sandbox_id == sandbox_id
        assert result.result_data is not None
        
        # Verificar se container foi iniciado
        mock_container.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_sandbox_timeout(self, sandbox_service_instance):
        """Teste de timeout na execução de sandbox"""
        service = sandbox_service_instance
        sandbox_id = "test-sandbox-timeout"
        
        # Mock container que não responde
        mock_container = MagicMock()
        mock_container.wait.side_effect = asyncio.TimeoutError()
        mock_container.logs.return_value = b'Execution timed out'
        
        # Mock sandbox info
        service.active_sandboxes[sandbox_id] = {
            'container': mock_container,
            'config': MagicMock(timeout_seconds=1),  # Timeout muito baixo
            'user_id': 'user-123',
            'created_at': datetime.utcnow(),
            'status': 'created'
        }
        
        with patch.object(service, '_get_resource_usage', return_value={}):
            result = await service.execute_sandbox(sandbox_id, timeout_seconds=1)
        
        assert result.success is False
        assert result.exit_code == -1
        assert "timeout" in result.result_data.get("error", "").lower()
        
        # Verificar se container foi morto
        mock_container.kill.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_sandbox(self, sandbox_service_instance):
        """Teste de limpeza de sandbox"""
        service = sandbox_service_instance
        sandbox_id = "test-sandbox-cleanup"
        
        # Mock container e temp directory
        mock_container = MagicMock()
        temp_dir = "/tmp/test_sandbox"
        
        service.active_sandboxes[sandbox_id] = {
            'container': mock_container,
            'temp_dir': temp_dir,
            'user_id': 'user-123',
            'status': 'completed'
        }
        
        with patch('shutil.rmtree') as mock_rmtree:
            await service._cleanup_sandbox(sandbox_id)
        
        # Verificar se container foi parado e removido
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
        
        # Verificar se diretório temporário foi removido
        mock_rmtree.assert_called_once_with(temp_dir)
        
        # Verificar se sandbox foi removido da lista ativa
        assert sandbox_id not in service.active_sandboxes
    
    @pytest.mark.asyncio
    async def test_list_active_sandboxes(self, sandbox_service_instance):
        """Teste de listagem de sandboxes ativos"""
        service = sandbox_service_instance
        
        # Adicionar sandboxes de teste
        service.active_sandboxes.update({
            'sandbox-1': {
                'user_id': 'user-123',
                'config': MagicMock(agent_id='sa-whatsapp'),
                'status': 'running',
                'created_at': datetime.utcnow(),
                'container': MagicMock(id='container-1')
            },
            'sandbox-2': {
                'user_id': 'user-456',
                'config': MagicMock(agent_id='sa-telegram'),
                'status': 'created',
                'created_at': datetime.utcnow(),
                'container': MagicMock(id='container-2')
            }
        })
        
        # Listar todos os sandboxes
        all_sandboxes = await service.list_active_sandboxes()
        assert len(all_sandboxes) == 2
        
        # Listar sandboxes de usuário específico
        user_sandboxes = await service.list_active_sandboxes('user-123')
        assert len(user_sandboxes) == 1
        assert user_sandboxes[0]['user_id'] == 'user-123'
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sandboxes(self, sandbox_service_instance):
        """Teste de limpeza de sandboxes expirados"""
        service = sandbox_service_instance
        
        # Adicionar sandbox expirado (mais de 1 hora)
        expired_time = datetime.utcnow() - timedelta(hours=2)
        service.active_sandboxes['expired-sandbox'] = {
            'user_id': 'user-123',
            'created_at': expired_time,
            'container': MagicMock(),
            'temp_dir': '/tmp/expired',
            'status': 'running'
        }
        
        # Adicionar sandbox recente
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        service.active_sandboxes['recent-sandbox'] = {
            'user_id': 'user-456',
            'created_at': recent_time,
            'container': MagicMock(),
            'temp_dir': '/tmp/recent',
            'status': 'running'
        }
        
        with patch('shutil.rmtree'):
            await service.cleanup_expired_sandboxes()
        
        # Verificar se apenas o sandbox expirado foi removido
        assert 'expired-sandbox' not in service.active_sandboxes
        assert 'recent-sandbox' in service.active_sandboxes
    
    def test_generate_agent_script(self, sandbox_service_instance, sample_execution_request):
        """Teste de geração de script do agente"""
        service = sandbox_service_instance
        
        script = service._generate_agent_script(sample_execution_request)
        
        assert isinstance(script, str)
        assert len(script) > 0
        assert "SandboxAgentRunner" in script
        assert "MockIntegrationService" in script
        assert "def main():" in script
        
        # Verificar se contém elementos específicos do agente
        assert "whatsapp" in script.lower()
        assert "send_message" in script.lower()

class TestSandboxIntegration:
    """Testes de integração do sistema de sandbox"""
    
    @pytest.mark.asyncio
    async def test_mock_integration_whatsapp(self):
        """Teste de integração mock do WhatsApp"""
        from app.core.sandbox_config import MOCK_INTEGRATION_CONFIGS
        
        whatsapp_config = MOCK_INTEGRATION_CONFIGS["whatsapp"]
        
        assert whatsapp_config["base_url"] == "https://graph.facebook.com/v18.0"
        assert "default_response" in whatsapp_config
        assert len(whatsapp_config["endpoints"]) > 0
        
        # Verificar endpoint de mensagens
        message_endpoint = next(
            (ep for ep in whatsapp_config["endpoints"] if ep["endpoint"] == "/messages"),
            None
        )
        assert message_endpoint is not None
        assert message_endpoint["method"] == "POST"
        assert message_endpoint["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_mock_integration_telegram(self):
        """Teste de integração mock do Telegram"""
        from app.core.sandbox_config import MOCK_INTEGRATION_CONFIGS
        
        telegram_config = MOCK_INTEGRATION_CONFIGS["telegram"]
        
        assert telegram_config["base_url"] == "https://api.telegram.org/bot"
        assert "default_response" in telegram_config
        assert telegram_config["default_response"]["ok"] is True
        
        # Verificar endpoint sendMessage
        send_message_endpoint = next(
            (ep for ep in telegram_config["endpoints"] if ep["endpoint"] == "/sendMessage"),
            None
        )
        assert send_message_endpoint is not None
        assert send_message_endpoint["method"] == "POST"
    
    @pytest.mark.asyncio
    async def test_mock_integration_gmail(self):
        """Teste de integração mock do Gmail"""
        from app.core.sandbox_config import MOCK_INTEGRATION_CONFIGS
        
        gmail_config = MOCK_INTEGRATION_CONFIGS["gmail"]
        
        assert gmail_config["base_url"] == "https://gmail.googleapis.com/gmail/v1"
        assert "default_response" in gmail_config
        
        # Verificar endpoint de envio
        send_endpoint = next(
            (ep for ep in gmail_config["endpoints"] if "send" in ep["endpoint"]),
            None
        )
        assert send_endpoint is not None
        assert send_endpoint["method"] == "POST"

class TestSandboxSecurity:
    """Testes de segurança do sandbox"""
    
    @pytest.mark.asyncio
    async def test_resource_limits_enforcement(self, sandbox_service_instance, sample_execution_request):
        """Teste de aplicação de limites de recursos"""
        service = sandbox_service_instance
        
        # Configurar limites específicos
        sample_execution_request.resource_quota = ResourceQuota(
            cpu_cores=0.1,
            memory_mb=128,
            disk_mb=256,
            max_execution_time_seconds=30
        )
        
        mock_container = MagicMock()
        service.docker_client.containers.create.return_value = mock_container
        
        with patch('tempfile.mkdtemp', return_value="/tmp/test"):
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', create=True):
                    sandbox_id = await service.create_sandbox(
                        execution_request=sample_execution_request,
                        user_id="user-123"
                    )
        
        # Verificar se container foi criado com limites corretos
        create_call = service.docker_client.containers.create.call_args
        assert create_call is not None
        
        # Verificar argumentos de criação do container
        kwargs = create_call.kwargs
        assert 'mem_limit' in kwargs
        assert kwargs['mem_limit'] == '128m'
        assert 'cpu_quota' in kwargs
        assert kwargs['cpu_quota'] == 10000  # 0.1 * 100000
    
    @pytest.mark.asyncio
    async def test_network_isolation(self, sandbox_service_instance):
        """Teste de isolamento de rede"""
        service = sandbox_service_instance
        
        # Verificar se rede isolada é configurada
        await service._setup_sandbox_network()
        
        # Verificar se rede foi criada com configurações de isolamento
        if service.docker_client.networks.create.called:
            create_call = service.docker_client.networks.create.call_args
            network_name = create_call.args[0]
            options = create_call.kwargs.get('options', {})
            
            assert network_name == service.sandbox_network
            assert create_call.kwargs.get('internal') is True  # Rede interna
    
    @pytest.mark.asyncio
    async def test_user_isolation(self, sandbox_service_instance, sample_execution_request):
        """Teste de isolamento entre usuários"""
        service = sandbox_service_instance
        
        # Criar sandboxes para usuários diferentes
        mock_container1 = MagicMock(id="container-1")
        mock_container2 = MagicMock(id="container-2")
        
        service.docker_client.containers.create.side_effect = [mock_container1, mock_container2]
        
        with patch('tempfile.mkdtemp', side_effect=["/tmp/user1", "/tmp/user2"]):
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', create=True):
                    sandbox1 = await service.create_sandbox(sample_execution_request, "user-1")
                    sandbox2 = await service.create_sandbox(sample_execution_request, "user-2")
        
        # Verificar isolamento
        user1_sandboxes = await service.list_active_sandboxes("user-1")
        user2_sandboxes = await service.list_active_sandboxes("user-2")
        
        assert len(user1_sandboxes) == 1
        assert len(user2_sandboxes) == 1
        assert user1_sandboxes[0]['sandbox_id'] != user2_sandboxes[0]['sandbox_id']
        assert user1_sandboxes[0]['user_id'] == "user-1"
        assert user2_sandboxes[0]['user_id'] == "user-2"

class TestSandboxTemplates:
    """Testes de templates de sandbox"""
    
    def test_predefined_templates(self):
        """Teste de templates pré-definidos"""
        from app.core.sandbox_config import SANDBOX_TEST_TEMPLATES
        
        assert len(SANDBOX_TEST_TEMPLATES) > 0
        
        # Verificar template do WhatsApp
        whatsapp_template = next(
            (t for t in SANDBOX_TEST_TEMPLATES if t["agent_id"] == "sa-whatsapp"),
            None
        )
        assert whatsapp_template is not None
        assert whatsapp_template["capability"] == "send_message"
        assert "phone_number" in whatsapp_template["default_input"]
        assert "message" in whatsapp_template["default_input"]
        
        # Verificar template do Telegram
        telegram_template = next(
            (t for t in SANDBOX_TEST_TEMPLATES if t["agent_id"] == "sa-telegram"),
            None
        )
        assert telegram_template is not None
        assert telegram_template["capability"] == "send_message"
        assert "chat_id" in telegram_template["default_input"]
    
    def test_template_validation(self):
        """Teste de validação de templates"""
        from app.core.sandbox_config import SANDBOX_TEST_TEMPLATES
        
        for template in SANDBOX_TEST_TEMPLATES:
            # Verificar campos obrigatórios
            assert "template_id" in template
            assert "name" in template
            assert "agent_id" in template
            assert "capability" in template
            assert "default_input" in template
            assert "resource_quota" in template
            
            # Verificar tipos
            assert isinstance(template["template_id"], str)
            assert isinstance(template["name"], str)
            assert isinstance(template["default_input"], dict)
            assert isinstance(template["resource_quota"], dict)
            
            # Verificar resource quota
            quota = template["resource_quota"]
            assert "cpu_cores" in quota
            assert "memory_mb" in quota
            assert quota["cpu_cores"] > 0
            assert quota["memory_mb"] > 0

class TestSandboxPerformance:
    """Testes de performance do sandbox"""
    
    @pytest.mark.asyncio
    async def test_concurrent_sandbox_creation(self, sandbox_service_instance):
        """Teste de criação concorrente de sandboxes"""
        service = sandbox_service_instance
        service.max_concurrent_sandboxes = 5
        
        # Mock containers
        mock_containers = [MagicMock(id=f"container-{i}") for i in range(3)]
        service.docker_client.containers.create.side_effect = mock_containers
        
        # Criar requisições
        requests = [
            SandboxExecutionRequest(
                agent_id=f"sa-test-{i}",
                capability="test",
                input_data={"test": f"data-{i}"}
            )
            for i in range(3)
        ]
        
        with patch('tempfile.mkdtemp', side_effect=[f"/tmp/test-{i}" for i in range(3)]):
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', create=True):
                    # Criar sandboxes concorrentemente
                    tasks = [
                        service.create_sandbox(req, f"user-{i}")
                        for i, req in enumerate(requests)
                    ]
                    
                    sandbox_ids = await asyncio.gather(*tasks)
        
        # Verificar se todos foram criados
        assert len(sandbox_ids) == 3
        assert len(set(sandbox_ids)) == 3  # IDs únicos
        assert len(service.active_sandboxes) == 3
    
    @pytest.mark.asyncio
    async def test_sandbox_resource_monitoring(self, sandbox_service_instance):
        """Teste de monitoramento de recursos"""
        service = sandbox_service_instance
        
        # Mock container com stats
        mock_container = MagicMock()
        mock_container.stats.return_value = {
            'cpu_stats': {
                'cpu_usage': {'total_usage': 1000000},
                'system_cpu_usage': 10000000
            },
            'precpu_stats': {
                'cpu_usage': {'total_usage': 500000},
                'system_cpu_usage': 5000000
            },
            'memory_stats': {
                'usage': 134217728,  # 128MB
                'limit': 268435456   # 256MB
            }
        }
        
        resource_usage = await service._get_resource_usage(mock_container)
        
        assert 'cpu_usage_percent' in resource_usage
        assert 'memory_usage_bytes' in resource_usage
        assert 'memory_usage_percent' in resource_usage
        
        assert resource_usage['memory_usage_bytes'] == 134217728
        assert resource_usage['memory_usage_percent'] == 50.0  # 128MB / 256MB