"""
Schemas para Sistema de Sandbox
Modelos Pydantic para execução isolada de agentes
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

class SandboxStatus(str, Enum):
    """Status do sandbox"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    CLEANUP = "cleanup"

class ResourceQuota(BaseModel):
    """Configuração de cotas de recursos para sandbox"""
    
    cpu_cores: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="Número de cores de CPU (0.1 a 2.0)"
    )
    
    memory_mb: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Memória em MB (128 a 2048)"
    )
    
    disk_mb: int = Field(
        default=1024,
        ge=256,
        le=4096,
        description="Espaço em disco em MB (256 a 4096)"
    )
    
    network_enabled: bool = Field(
        default=False,
        description="Permitir acesso à rede externa"
    )
    
    max_execution_time_seconds: int = Field(
        default=300,
        ge=10,
        le=1800,
        description="Tempo máximo de execução em segundos (10 a 1800)"
    )

class MockIntegrationEndpoint(BaseModel):
    """Configuração de endpoint mock"""
    
    endpoint: str = Field(..., description="Caminho do endpoint (ex: /api/send)")
    method: str = Field(default="GET", description="Método HTTP")
    response: Dict[str, Any] = Field(default_factory=dict, description="Resposta mock")
    status_code: int = Field(default=200, description="Código de status HTTP")
    delay_ms: int = Field(default=0, ge=0, le=5000, description="Delay em milissegundos")
    
    @validator('method')
    def validate_method(cls, v):
        allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if v.upper() not in allowed_methods:
            raise ValueError(f'Method must be one of {allowed_methods}')
        return v.upper()

class MockIntegrationConfig(BaseModel):
    """Configuração de integração mock"""
    
    service_name: str = Field(..., description="Nome do serviço (ex: whatsapp, telegram)")
    base_url: Optional[str] = Field(None, description="URL base do serviço")
    default_response: Dict[str, Any] = Field(
        default_factory=lambda: {"status": "ok", "mock": True},
        description="Resposta padrão quando endpoint específico não encontrado"
    )
    endpoints: List[MockIntegrationEndpoint] = Field(
        default_factory=list,
        description="Lista de endpoints mockados"
    )
    
    # Configurações específicas por tipo de serviço
    whatsapp_config: Optional[Dict[str, Any]] = Field(None, description="Configurações específicas do WhatsApp")
    telegram_config: Optional[Dict[str, Any]] = Field(None, description="Configurações específicas do Telegram")
    gmail_config: Optional[Dict[str, Any]] = Field(None, description="Configurações específicas do Gmail")

class SandboxExecutionRequest(BaseModel):
    """Requisição de execução em sandbox"""
    
    agent_id: str = Field(..., description="ID do agente a ser testado")
    capability: str = Field(..., description="Capacidade do agente a ser executada")
    
    input_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dados de entrada para o agente"
    )
    
    resource_quota: Optional[ResourceQuota] = Field(
        None,
        description="Cotas de recursos para execução"
    )
    
    mock_integrations: Optional[Dict[str, MockIntegrationConfig]] = Field(
        None,
        description="Configurações de integrações mock"
    )
    
    timeout_seconds: Optional[int] = Field(
        300,
        ge=10,
        le=1800,
        description="Timeout de execução em segundos"
    )
    
    allowed_domains: Optional[List[str]] = Field(
        None,
        description="Domínios permitidos para acesso de rede"
    )
    
    environment_variables: Optional[Dict[str, str]] = Field(
        None,
        description="Variáveis de ambiente adicionais"
    )
    
    test_mode: bool = Field(
        default=True,
        description="Executar em modo de teste (com mocks)"
    )
    
    collect_metrics: bool = Field(
        default=True,
        description="Coletar métricas de execução"
    )

class SandboxConfig(BaseModel):
    """Configuração interna do sandbox"""
    
    sandbox_id: str = Field(..., description="ID único do sandbox")
    agent_id: str = Field(..., description="ID do agente")
    capability: str = Field(..., description="Capacidade sendo testada")
    
    input_data: Dict[str, Any] = Field(default_factory=dict)
    mock_integrations: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300)
    allowed_domains: List[str] = Field(default_factory=list)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SandboxExecutionResult(BaseModel):
    """Resultado da execução em sandbox"""
    
    sandbox_id: str = Field(..., description="ID do sandbox")
    success: bool = Field(..., description="Se a execução foi bem-sucedida")
    exit_code: int = Field(..., description="Código de saída do processo")
    
    result_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Dados de resultado da execução do agente"
    )
    
    logs: str = Field(default="", description="Logs da execução")
    
    execution_time_ms: int = Field(..., description="Tempo de execução em milissegundos")
    
    resource_usage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Uso de recursos durante execução"
    )
    
    completed_at: datetime = Field(..., description="Timestamp de conclusão")
    
    # Métricas adicionais
    memory_peak_mb: Optional[float] = Field(None, description="Pico de uso de memória")
    cpu_usage_percent: Optional[float] = Field(None, description="Uso médio de CPU")
    network_requests: Optional[int] = Field(None, description="Número de requisições de rede")
    
    # Informações de erro (se houver)
    error_message: Optional[str] = Field(None, description="Mensagem de erro")
    error_type: Optional[str] = Field(None, description="Tipo do erro")
    traceback: Optional[str] = Field(None, description="Stack trace do erro")

class SandboxInfo(BaseModel):
    """Informações sobre um sandbox ativo"""
    
    sandbox_id: str = Field(..., description="ID do sandbox")
    user_id: str = Field(..., description="ID do usuário proprietário")
    agent_id: str = Field(..., description="ID do agente sendo testado")
    capability: str = Field(..., description="Capacidade sendo testada")
    
    status: SandboxStatus = Field(..., description="Status atual do sandbox")
    
    created_at: datetime = Field(..., description="Timestamp de criação")
    started_at: Optional[datetime] = Field(None, description="Timestamp de início da execução")
    completed_at: Optional[datetime] = Field(None, description="Timestamp de conclusão")
    
    resource_quota: ResourceQuota = Field(..., description="Cotas de recursos")
    
    container_id: Optional[str] = Field(None, description="ID do container Docker")
    
    # Métricas em tempo real
    current_memory_mb: Optional[float] = Field(None, description="Uso atual de memória")
    current_cpu_percent: Optional[float] = Field(None, description="Uso atual de CPU")

class SandboxListResponse(BaseModel):
    """Resposta da listagem de sandboxes"""
    
    sandboxes: List[SandboxInfo] = Field(..., description="Lista de sandboxes")
    total_count: int = Field(..., description="Total de sandboxes")
    active_count: int = Field(..., description="Sandboxes ativos")
    
class CreateSandboxResponse(BaseModel):
    """Resposta da criação de sandbox"""
    
    sandbox_id: str = Field(..., description="ID do sandbox criado")
    status: SandboxStatus = Field(..., description="Status inicial")
    created_at: datetime = Field(..., description="Timestamp de criação")
    estimated_ready_in_seconds: int = Field(default=30, description="Tempo estimado para ficar pronto")

class SandboxExecutionResponse(BaseModel):
    """Resposta da execução de sandbox"""
    
    sandbox_id: str = Field(..., description="ID do sandbox")
    execution_result: SandboxExecutionResult = Field(..., description="Resultado da execução")

class SandboxLogsResponse(BaseModel):
    """Resposta dos logs do sandbox"""
    
    sandbox_id: str = Field(..., description="ID do sandbox")
    logs: str = Field(..., description="Logs completos")
    log_lines: List[str] = Field(..., description="Logs divididos por linha")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp da coleta")

# Schemas para templates de teste
class SandboxTestTemplate(BaseModel):
    """Template de teste para sandbox"""
    
    template_id: str = Field(..., description="ID do template")
    name: str = Field(..., description="Nome do template")
    description: str = Field(..., description="Descrição do template")
    
    agent_id: str = Field(..., description="ID do agente alvo")
    capability: str = Field(..., description="Capacidade a ser testada")
    
    default_input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dados de entrada padrão"
    )
    
    mock_configurations: Dict[str, MockIntegrationConfig] = Field(
        default_factory=dict,
        description="Configurações de mock pré-definidas"
    )
    
    expected_output: Optional[Dict[str, Any]] = Field(
        None,
        description="Saída esperada para validação"
    )
    
    resource_quota: ResourceQuota = Field(
        default_factory=ResourceQuota,
        description="Cotas de recursos recomendadas"
    )
    
    tags: List[str] = Field(default_factory=list, description="Tags para categorização")
    
    created_by: str = Field(..., description="Usuário que criou o template")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SandboxTestTemplateList(BaseModel):
    """Lista de templates de teste"""
    
    templates: List[SandboxTestTemplate] = Field(..., description="Lista de templates")
    total_count: int = Field(..., description="Total de templates")
    
class CreateSandboxTestTemplateRequest(BaseModel):
    """Requisição para criar template de teste"""
    
    name: str = Field(..., min_length=1, max_length=100, description="Nome do template")
    description: str = Field(..., min_length=1, max_length=500, description="Descrição")
    
    agent_id: str = Field(..., description="ID do agente")
    capability: str = Field(..., description="Capacidade")
    
    default_input: Dict[str, Any] = Field(default_factory=dict)
    mock_configurations: Dict[str, MockIntegrationConfig] = Field(default_factory=dict)
    expected_output: Optional[Dict[str, Any]] = Field(None)
    resource_quota: Optional[ResourceQuota] = Field(None)
    tags: List[str] = Field(default_factory=list)

# Schemas para métricas de sandbox
class SandboxMetrics(BaseModel):
    """Métricas agregadas do sistema de sandbox"""
    
    total_executions: int = Field(..., description="Total de execuções")
    successful_executions: int = Field(..., description="Execuções bem-sucedidas")
    failed_executions: int = Field(..., description="Execuções falhadas")
    timeout_executions: int = Field(..., description="Execuções com timeout")
    
    average_execution_time_ms: float = Field(..., description="Tempo médio de execução")
    average_memory_usage_mb: float = Field(..., description="Uso médio de memória")
    average_cpu_usage_percent: float = Field(..., description="Uso médio de CPU")
    
    most_tested_agents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Agentes mais testados"
    )
    
    resource_efficiency: Dict[str, float] = Field(
        default_factory=dict,
        description="Eficiência de uso de recursos"
    )
    
    period_start: datetime = Field(..., description="Início do período das métricas")
    period_end: datetime = Field(..., description="Fim do período das métricas")

class SandboxHealthCheck(BaseModel):
    """Health check do sistema de sandbox"""
    
    status: str = Field(..., description="Status geral (healthy/unhealthy)")
    docker_available: bool = Field(..., description="Docker disponível")
    network_configured: bool = Field(..., description="Rede configurada")
    base_images_ready: bool = Field(..., description="Imagens base prontas")
    
    active_sandboxes_count: int = Field(..., description="Sandboxes ativos")
    max_sandboxes_limit: int = Field(..., description="Limite máximo de sandboxes")
    
    system_resources: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recursos do sistema"
    )
    
    last_cleanup: Optional[datetime] = Field(None, description="Última limpeza")
    
    issues: List[str] = Field(default_factory=list, description="Problemas identificados")
    
    checked_at: datetime = Field(default_factory=datetime.utcnow)