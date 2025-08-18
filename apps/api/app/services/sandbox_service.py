"""
Serviço de Sandbox para Execução Isolada de Agentes
Fornece ambiente seguro e isolado para testes de agentes
"""
import asyncio
import uuid
import time
import json
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import docker
from docker.errors import DockerException, ContainerError, ImageNotFound
import structlog

from app.core.config import settings
from app.schemas.sandbox import (
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxConfig,
    ResourceQuota
)

logger = structlog.get_logger(__name__)

class SandboxService:
    """Serviço para execução isolada de agentes em sandbox"""
    
    def __init__(self):
        self.docker_client = None
        self.active_sandboxes: Dict[str, Dict] = {}
        self.sandbox_network = "renum-sandbox"
        self.base_image = "python:3.11-slim"
        self.max_concurrent_sandboxes = settings.SANDBOX_MAX_CONCURRENT or 10
        
    async def initialize(self):
        """Inicializar serviço de sandbox"""
        try:
            self.docker_client = docker.from_env()
            await self._setup_sandbox_network()
            await self._setup_base_images()
            logger.info("Sandbox service initialized successfully")
        except DockerException as e:
            logger.error("Failed to initialize sandbox service", error=str(e))
            raise
    
    async def _setup_sandbox_network(self):
        """Configurar rede isolada para sandboxes"""
        try:
            # Verificar se rede já existe
            try:
                network = self.docker_client.networks.get(self.sandbox_network)
                logger.info("Sandbox network already exists", network_id=network.id)
            except docker.errors.NotFound:
                # Criar rede isolada
                network = self.docker_client.networks.create(
                    self.sandbox_network,
                    driver="bridge",
                    options={
                        "com.docker.network.bridge.enable_icc": "false",
                        "com.docker.network.bridge.enable_ip_masquerade": "true"
                    },
                    internal=True  # Rede interna sem acesso à internet
                )
                logger.info("Created sandbox network", network_id=network.id)
                
        except DockerException as e:
            logger.error("Failed to setup sandbox network", error=str(e))
            raise
    
    async def _setup_base_images(self):
        """Preparar imagens base para sandbox"""
        try:
            # Pull da imagem base se não existir
            try:
                self.docker_client.images.get(self.base_image)
                logger.info("Base image already available", image=self.base_image)
            except ImageNotFound:
                logger.info("Pulling base image", image=self.base_image)
                self.docker_client.images.pull(self.base_image)
                logger.info("Base image pulled successfully", image=self.base_image)
                
        except DockerException as e:
            logger.error("Failed to setup base images", error=str(e))
            raise
    
    async def create_sandbox(
        self,
        execution_request: SandboxExecutionRequest,
        user_id: str
    ) -> str:
        """Criar novo sandbox para execução"""
        
        # Verificar limite de sandboxes concorrentes
        if len(self.active_sandboxes) >= self.max_concurrent_sandboxes:
            raise ValueError("Maximum concurrent sandboxes limit reached")
        
        sandbox_id = str(uuid.uuid4())
        
        try:
            # Configurar recursos
            resource_quota = execution_request.resource_quota or ResourceQuota()
            
            # Criar diretório temporário para o sandbox
            temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id}_")
            
            # Preparar ambiente do sandbox
            sandbox_config = await self._prepare_sandbox_environment(
                sandbox_id,
                execution_request,
                temp_dir
            )
            
            # Criar container
            container = await self._create_sandbox_container(
                sandbox_id,
                sandbox_config,
                resource_quota,
                temp_dir
            )
            
            # Registrar sandbox ativo
            self.active_sandboxes[sandbox_id] = {
                'container': container,
                'config': sandbox_config,
                'temp_dir': temp_dir,
                'user_id': user_id,
                'created_at': datetime.utcnow(),
                'status': 'created'
            }
            
            logger.info(
                "Sandbox created successfully",
                sandbox_id=sandbox_id,
                user_id=user_id,
                container_id=container.id[:12]
            )
            
            return sandbox_id
            
        except Exception as e:
            logger.error(
                "Failed to create sandbox",
                sandbox_id=sandbox_id,
                error=str(e)
            )
            # Cleanup em caso de erro
            await self._cleanup_sandbox(sandbox_id)
            raise
    
    async def _prepare_sandbox_environment(
        self,
        sandbox_id: str,
        execution_request: SandboxExecutionRequest,
        temp_dir: str
    ) -> SandboxConfig:
        """Preparar ambiente do sandbox"""
        
        # Criar estrutura de diretórios
        sandbox_path = Path(temp_dir)
        (sandbox_path / "app").mkdir(exist_ok=True)
        (sandbox_path / "logs").mkdir(exist_ok=True)
        (sandbox_path / "data").mkdir(exist_ok=True)
        
        # Criar script de execução do agente
        agent_script = self._generate_agent_script(execution_request)
        with open(sandbox_path / "app" / "agent_runner.py", "w") as f:
            f.write(agent_script)
        
        # Criar arquivo de configuração
        config = SandboxConfig(
            sandbox_id=sandbox_id,
            agent_id=execution_request.agent_id,
            capability=execution_request.capability,
            input_data=execution_request.input_data,
            mock_integrations=execution_request.mock_integrations or {},
            timeout_seconds=execution_request.timeout_seconds or 300,
            allowed_domains=execution_request.allowed_domains or [],
            environment_variables=execution_request.environment_variables or {}
        )
        
        with open(sandbox_path / "app" / "config.json", "w") as f:
            json.dump(config.dict(), f, indent=2, default=str)
        
        # Criar requirements.txt com dependências mínimas
        requirements = [
            "requests==2.31.0",
            "httpx==0.25.0",
            "pydantic==2.5.0",
            "structlog==23.2.0"
        ]
        
        with open(sandbox_path / "app" / "requirements.txt", "w") as f:
            f.write("\n".join(requirements))
        
        return config
    
    def _generate_agent_script(self, execution_request: SandboxExecutionRequest) -> str:
        """Gerar script de execução do agente no sandbox"""
        return f'''#!/usr/bin/env python3
"""
Script de execução de agente em sandbox isolado
Gerado automaticamente - NÃO EDITAR
"""
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
import structlog

# Configurar logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class MockIntegrationService:
    """Serviço mock para integrações externas"""
    
    def __init__(self, mock_configs):
        self.mock_configs = mock_configs
        logger.info("Mock integration service initialized", configs=list(mock_configs.keys()))
    
    def get_mock_response(self, service_name: str, endpoint: str, method: str = "GET"):
        """Obter resposta mock para serviço"""
        if service_name not in self.mock_configs:
            return {{"error": f"Mock not configured for service: {{service_name}}"}}
        
        service_config = self.mock_configs[service_name]
        
        # Buscar resposta específica para endpoint
        for mock in service_config.get("endpoints", []):
            if mock.get("endpoint") == endpoint and mock.get("method", "GET") == method:
                response = mock.get("response", {{}})
                delay = mock.get("delay_ms", 0)
                
                if delay > 0:
                    time.sleep(delay / 1000)
                
                logger.info(
                    "Mock response returned",
                    service=service_name,
                    endpoint=endpoint,
                    method=method,
                    delay_ms=delay
                )
                
                return response
        
        # Resposta padrão se não encontrar mock específico
        return service_config.get("default_response", {{"status": "ok", "mock": True}})

class SandboxAgentRunner:
    """Executor de agente em ambiente sandbox"""
    
    def __init__(self):
        self.config = None
        self.mock_service = None
        self.start_time = time.time()
        
    def load_config(self):
        """Carregar configuração do sandbox"""
        try:
            with open("/app/config.json", "r") as f:
                config_data = json.load(f)
                self.config = config_data
                
            # Inicializar serviço mock
            mock_integrations = self.config.get("mock_integrations", {{}})
            self.mock_service = MockIntegrationService(mock_integrations)
            
            logger.info("Configuration loaded", agent_id=self.config.get("agent_id"))
            
        except Exception as e:
            logger.error("Failed to load configuration", error=str(e))
            raise
    
    def execute_agent(self):
        """Executar agente com input fornecido"""
        try:
            agent_id = self.config["agent_id"]
            capability = self.config["capability"]
            input_data = self.config["input_data"]
            
            logger.info(
                "Starting agent execution",
                agent_id=agent_id,
                capability=capability
            )
            
            # Simular execução do agente
            # Em implementação real, aqui seria carregado e executado o agente real
            result = self._simulate_agent_execution(agent_id, capability, input_data)
            
            execution_time = (time.time() - self.start_time) * 1000
            
            final_result = {{
                "success": True,
                "result": result,
                "execution_time_ms": execution_time,
                "agent_id": agent_id,
                "capability": capability,
                "timestamp": datetime.utcnow().isoformat(),
                "sandbox_id": self.config["sandbox_id"]
            }}
            
            logger.info(
                "Agent execution completed",
                success=True,
                execution_time_ms=execution_time
            )
            
            return final_result
            
        except Exception as e:
            execution_time = (time.time() - self.start_time) * 1000
            error_result = {{
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time_ms": execution_time,
                "agent_id": self.config.get("agent_id"),
                "capability": self.config.get("capability"),
                "timestamp": datetime.utcnow().isoformat(),
                "sandbox_id": self.config.get("sandbox_id"),
                "traceback": traceback.format_exc()
            }}
            
            logger.error(
                "Agent execution failed",
                error=str(e),
                execution_time_ms=execution_time
            )
            
            return error_result
    
    def _simulate_agent_execution(self, agent_id: str, capability: str, input_data: dict):
        """Simular execução do agente (placeholder)"""
        
        # Simular diferentes tipos de agentes
        if "whatsapp" in agent_id.lower():
            return self._simulate_whatsapp_agent(capability, input_data)
        elif "telegram" in agent_id.lower():
            return self._simulate_telegram_agent(capability, input_data)
        elif "gmail" in agent_id.lower():
            return self._simulate_gmail_agent(capability, input_data)
        elif "http" in agent_id.lower():
            return self._simulate_http_agent(capability, input_data)
        else:
            return self._simulate_generic_agent(capability, input_data)
    
    def _simulate_whatsapp_agent(self, capability: str, input_data: dict):
        """Simular agente WhatsApp"""
        if capability == "send_message":
            phone = input_data.get("phone_number", "unknown")
            message = input_data.get("message", "")
            
            # Usar mock service
            response = self.mock_service.get_mock_response(
                "whatsapp", 
                "/messages", 
                "POST"
            )
            
            return {{
                "message_id": f"wamid_mock_{{int(time.time())}}",
                "status": "sent",
                "phone_number": phone,
                "message_length": len(message),
                "mock_response": response
            }}
        
        return {{"error": f"Capability {{capability}} not supported"}}
    
    def _simulate_telegram_agent(self, capability: str, input_data: dict):
        """Simular agente Telegram"""
        if capability == "send_message":
            chat_id = input_data.get("chat_id", "unknown")
            message = input_data.get("message", "")
            
            response = self.mock_service.get_mock_response(
                "telegram",
                "/sendMessage",
                "POST"
            )
            
            return {{
                "message_id": int(time.time()),
                "chat_id": chat_id,
                "message_length": len(message),
                "mock_response": response
            }}
        
        return {{"error": f"Capability {{capability}} not supported"}}
    
    def _simulate_gmail_agent(self, capability: str, input_data: dict):
        """Simular agente Gmail"""
        if capability == "send_email":
            to_email = input_data.get("to", "unknown")
            subject = input_data.get("subject", "")
            body = input_data.get("body", "")
            
            response = self.mock_service.get_mock_response(
                "gmail",
                "/send",
                "POST"
            )
            
            return {{
                "message_id": f"gmail_mock_{{int(time.time())}}",
                "to": to_email,
                "subject": subject,
                "body_length": len(body),
                "mock_response": response
            }}
        
        return {{"error": f"Capability {{capability}} not supported"}}
    
    def _simulate_http_agent(self, capability: str, input_data: dict):
        """Simular agente HTTP genérico"""
        if capability == "api_call":
            url = input_data.get("url", "")
            method = input_data.get("method", "GET")
            
            # Extrair domínio para mock
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            response = self.mock_service.get_mock_response(
                "http_generic",
                parsed_url.path,
                method
            )
            
            return {{
                "url": url,
                "method": method,
                "domain": domain,
                "status_code": 200,
                "mock_response": response
            }}
        
        return {{"error": f"Capability {{capability}} not supported"}}
    
    def _simulate_generic_agent(self, capability: str, input_data: dict):
        """Simular agente genérico"""
        return {{
            "capability": capability,
            "input_data_keys": list(input_data.keys()),
            "simulated": True,
            "timestamp": datetime.utcnow().isoformat()
        }}

def main():
    """Função principal"""
    runner = SandboxAgentRunner()
    
    try:
        # Carregar configuração
        runner.load_config()
        
        # Executar agente
        result = runner.execute_agent()
        
        # Salvar resultado
        with open("/app/result.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        
        # Output para stdout
        print(json.dumps(result, default=str))
        
        # Exit code baseado no sucesso
        sys.exit(0 if result.get("success", False) else 1)
        
    except Exception as e:
        error_result = {{
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "traceback": traceback.format_exc()
        }}
        
        # Salvar erro
        with open("/app/result.json", "w") as f:
            json.dump(error_result, f, indent=2, default=str)
        
        print(json.dumps(error_result, default=str))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    async def _create_sandbox_container(
        self,
        sandbox_id: str,
        config: SandboxConfig,
        resource_quota: ResourceQuota,
        temp_dir: str
    ) -> Any:
        """Criar container do sandbox"""
        
        container_name = f"sandbox_{sandbox_id}"
        
        # Configurar limites de recursos
        mem_limit = f"{resource_quota.memory_mb}m"
        cpu_quota = int(resource_quota.cpu_cores * 100000)  # CPU quota em microsegundos
        
        # Configurar volumes
        volumes = {
            temp_dir: {'bind': '/app', 'mode': 'rw'}
        }
        
        # Configurar variáveis de ambiente
        environment = {
            'PYTHONPATH': '/app',
            'SANDBOX_ID': sandbox_id,
            'SANDBOX_MODE': 'true',
            **config.environment_variables
        }
        
        # Configurar rede (isolada)
        network_config = {
            self.sandbox_network: {}
        }
        
        try:
            # Criar container
            container = self.docker_client.containers.create(
                image=self.base_image,
                command=[
                    "sh", "-c",
                    "cd /app && pip install -r app/requirements.txt && python app/agent_runner.py"
                ],
                name=container_name,
                volumes=volumes,
                environment=environment,
                networks_config=network_config,
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                cpu_period=100000,
                network_disabled=False,  # Permitir rede interna
                read_only=False,
                security_opt=['no-new-privileges:true'],
                cap_drop=['ALL'],
                cap_add=['CHOWN', 'SETUID', 'SETGID'],  # Mínimas necessárias
                user='1000:1000',  # Usuário não-root
                working_dir='/app',
                labels={
                    'renum.sandbox.id': sandbox_id,
                    'renum.sandbox.user_id': config.sandbox_id,  # Usar sandbox_id como user_id temporário
                    'renum.sandbox.agent_id': config.agent_id,
                    'renum.sandbox.created_at': datetime.utcnow().isoformat()
                },
                detach=True,
                remove=False,  # Manter para coleta de logs
                tty=False,
                stdin_open=False
            )
            
            logger.info(
                "Sandbox container created",
                sandbox_id=sandbox_id,
                container_id=container.id[:12],
                container_name=container_name
            )
            
            return container
            
        except DockerException as e:
            logger.error(
                "Failed to create sandbox container",
                sandbox_id=sandbox_id,
                error=str(e)
            )
            raise
    
    async def execute_sandbox(
        self,
        sandbox_id: str,
        timeout_seconds: Optional[int] = None
    ) -> SandboxExecutionResult:
        """Executar sandbox e retornar resultado"""
        
        if sandbox_id not in self.active_sandboxes:
            raise ValueError(f"Sandbox {sandbox_id} not found")
        
        sandbox_info = self.active_sandboxes[sandbox_id]
        container = sandbox_info['container']
        config = sandbox_info['config']
        
        timeout = timeout_seconds or config.timeout_seconds
        
        try:
            # Atualizar status
            sandbox_info['status'] = 'running'
            
            logger.info(
                "Starting sandbox execution",
                sandbox_id=sandbox_id,
                timeout_seconds=timeout
            )
            
            # Iniciar container
            container.start()
            
            # Aguardar execução com timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result['StatusCode']
                
                # Coletar logs
                logs = container.logs(stdout=True, stderr=True).decode('utf-8')
                
                # Ler resultado do arquivo
                result_data = None
                try:
                    # Copiar arquivo de resultado do container
                    result_archive, _ = container.get_archive('/app/result.json')
                    
                    # Extrair e ler arquivo
                    import tarfile
                    import io
                    
                    tar_stream = io.BytesIO(b''.join(result_archive))
                    with tarfile.open(fileobj=tar_stream, mode='r') as tar:
                        result_file = tar.extractfile('result.json')
                        if result_file:
                            result_data = json.loads(result_file.read().decode('utf-8'))
                
                except Exception as e:
                    logger.warning(
                        "Failed to read result file from container",
                        sandbox_id=sandbox_id,
                        error=str(e)
                    )
                
                # Criar resultado
                execution_result = SandboxExecutionResult(
                    sandbox_id=sandbox_id,
                    success=exit_code == 0,
                    exit_code=exit_code,
                    result_data=result_data,
                    logs=logs,
                    execution_time_ms=int((time.time() - time.mktime(sandbox_info['created_at'].timetuple())) * 1000),
                    resource_usage=await self._get_resource_usage(container),
                    completed_at=datetime.utcnow()
                )
                
                # Atualizar status
                sandbox_info['status'] = 'completed'
                
                logger.info(
                    "Sandbox execution completed",
                    sandbox_id=sandbox_id,
                    success=execution_result.success,
                    exit_code=exit_code,
                    execution_time_ms=execution_result.execution_time_ms
                )
                
                return execution_result
                
            except asyncio.TimeoutError:
                # Timeout - matar container
                container.kill()
                
                logs = container.logs(stdout=True, stderr=True).decode('utf-8')
                
                execution_result = SandboxExecutionResult(
                    sandbox_id=sandbox_id,
                    success=False,
                    exit_code=-1,
                    result_data={"error": "Execution timeout", "timeout_seconds": timeout},
                    logs=logs,
                    execution_time_ms=timeout * 1000,
                    resource_usage=await self._get_resource_usage(container),
                    completed_at=datetime.utcnow()
                )
                
                sandbox_info['status'] = 'timeout'
                
                logger.warning(
                    "Sandbox execution timeout",
                    sandbox_id=sandbox_id,
                    timeout_seconds=timeout
                )
                
                return execution_result
                
        except Exception as e:
            # Erro durante execução
            sandbox_info['status'] = 'error'
            
            logs = ""
            try:
                logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            except:
                pass
            
            execution_result = SandboxExecutionResult(
                sandbox_id=sandbox_id,
                success=False,
                exit_code=-2,
                result_data={"error": str(e), "error_type": type(e).__name__},
                logs=logs,
                execution_time_ms=int((time.time() - time.mktime(sandbox_info['created_at'].timetuple())) * 1000),
                resource_usage={},
                completed_at=datetime.utcnow()
            )
            
            logger.error(
                "Sandbox execution error",
                sandbox_id=sandbox_id,
                error=str(e)
            )
            
            return execution_result
        
        finally:
            # Cleanup automático após execução
            await self._cleanup_sandbox(sandbox_id)
    
    async def _get_resource_usage(self, container) -> Dict[str, Any]:
        """Obter uso de recursos do container"""
        try:
            stats = container.stats(stream=False)
            
            # Calcular uso de CPU
            cpu_usage = 0
            if 'cpu_stats' in stats and 'precpu_stats' in stats:
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                
                if system_delta > 0:
                    cpu_usage = (cpu_delta / system_delta) * 100
            
            # Uso de memória
            memory_usage = 0
            memory_limit = 0
            if 'memory_stats' in stats:
                memory_usage = stats['memory_stats'].get('usage', 0)
                memory_limit = stats['memory_stats'].get('limit', 0)
            
            return {
                'cpu_usage_percent': round(cpu_usage, 2),
                'memory_usage_bytes': memory_usage,
                'memory_limit_bytes': memory_limit,
                'memory_usage_percent': round((memory_usage / memory_limit) * 100, 2) if memory_limit > 0 else 0
            }
            
        except Exception as e:
            logger.warning("Failed to get resource usage", error=str(e))
            return {}
    
    async def _cleanup_sandbox(self, sandbox_id: str):
        """Limpar recursos do sandbox"""
        if sandbox_id not in self.active_sandboxes:
            return
        
        sandbox_info = self.active_sandboxes[sandbox_id]
        
        try:
            # Parar e remover container
            container = sandbox_info['container']
            try:
                container.stop(timeout=10)
                container.remove()
                logger.info("Container removed", sandbox_id=sandbox_id)
            except Exception as e:
                logger.warning("Failed to remove container", sandbox_id=sandbox_id, error=str(e))
            
            # Remover diretório temporário
            temp_dir = sandbox_info['temp_dir']
            try:
                shutil.rmtree(temp_dir)
                logger.info("Temp directory removed", sandbox_id=sandbox_id)
            except Exception as e:
                logger.warning("Failed to remove temp directory", sandbox_id=sandbox_id, error=str(e))
            
        except Exception as e:
            logger.error("Error during sandbox cleanup", sandbox_id=sandbox_id, error=str(e))
        
        finally:
            # Remover do registro de sandboxes ativos
            del self.active_sandboxes[sandbox_id]
            logger.info("Sandbox cleaned up", sandbox_id=sandbox_id)
    
    async def list_active_sandboxes(self, user_id: Optional[str] = None) -> List[Dict]:
        """Listar sandboxes ativos"""
        sandboxes = []
        
        for sandbox_id, info in self.active_sandboxes.items():
            if user_id and info['user_id'] != user_id:
                continue
                
            sandboxes.append({
                'sandbox_id': sandbox_id,
                'user_id': info['user_id'],
                'agent_id': info['config'].agent_id,
                'status': info['status'],
                'created_at': info['created_at'],
                'container_id': info['container'].id[:12]
            })
        
        return sandboxes
    
    async def cleanup_expired_sandboxes(self):
        """Limpar sandboxes expirados"""
        current_time = datetime.utcnow()
        expired_sandboxes = []
        
        for sandbox_id, info in self.active_sandboxes.items():
            # Sandboxes com mais de 1 hora são considerados expirados
            if current_time - info['created_at'] > timedelta(hours=1):
                expired_sandboxes.append(sandbox_id)
        
        for sandbox_id in expired_sandboxes:
            logger.info("Cleaning up expired sandbox", sandbox_id=sandbox_id)
            await self._cleanup_sandbox(sandbox_id)
    
    async def get_sandbox_logs(self, sandbox_id: str) -> str:
        """Obter logs do sandbox"""
        if sandbox_id not in self.active_sandboxes:
            raise ValueError(f"Sandbox {sandbox_id} not found")
        
        container = self.active_sandboxes[sandbox_id]['container']
        
        try:
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            return logs
        except Exception as e:
            logger.error("Failed to get sandbox logs", sandbox_id=sandbox_id, error=str(e))
            return f"Error retrieving logs: {str(e)}"

# Instância global do serviço
sandbox_service = SandboxService()