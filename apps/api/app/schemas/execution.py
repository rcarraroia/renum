"""
Schemas para entidades de Execution.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any
from enum import Enum

from .base import BaseSchema, TimestampedSchema


class ExecutionStatus(str, Enum):
    """Status de uma execução."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecutionStatus(str, Enum):
    """Status de execução de um agente."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionConfig(BaseSchema):
    """Configuração de execução."""
    
    timeout_minutes: Optional[int] = Field(30, ge=1, le=120, description="Timeout em minutos")
    parallel_limit: Optional[int] = Field(3, ge=1, le=10, description="Limite de execuções paralelas")
    retry_failed: bool = Field(True, description="Tentar novamente em caso de falha")
    max_retries: int = Field(3, ge=0, le=5, description="Número máximo de tentativas")


class ExecutionCreate(BaseSchema):
    """Schema para iniciar execução de equipe."""
    
    input_data: Dict[str, Any] = Field(..., description="Dados de entrada para a execução")
    execution_config: Optional[ExecutionConfig] = Field(None, description="Configuração da execução")


class AgentResult(BaseSchema):
    """Resultado de execução de um agente."""
    
    agent_id: UUID = Field(..., description="ID do agente")
    status: AgentExecutionStatus = Field(..., description="Status da execução do agente")
    output: Optional[str] = Field(None, description="Saída do agente")
    error_message: Optional[str] = Field(None, description="Mensagem de erro se houver")
    execution_time_ms: int = Field(0, ge=0, description="Tempo de execução em milissegundos")
    started_at: Optional[datetime] = Field(None, description="Início da execução")
    completed_at: Optional[datetime] = Field(None, description="Fim da execução")
    retry_count: int = Field(0, ge=0, description="Número de tentativas")


class ExecutionProgress(BaseSchema):
    """Progresso de uma execução."""
    
    completed_agents: int = Field(0, ge=0, description="Agentes completados")
    total_agents: int = Field(..., ge=1, description="Total de agentes")
    current_step: str = Field(..., description="Etapa atual")
    percentage: float = Field(0.0, ge=0.0, le=100.0, description="Porcentagem de conclusão")


class ExecutionLog(BaseSchema):
    """Log de execução."""
    
    timestamp: datetime = Field(..., description="Timestamp do log")
    level: str = Field(..., description="Nível do log (info, warning, error)")
    message: str = Field(..., description="Mensagem do log")
    agent_id: Optional[UUID] = Field(None, description="ID do agente relacionado")
    data: Optional[Dict[str, Any]] = Field(None, description="Dados adicionais")


class ExecutionResponse(TimestampedSchema):
    """Schema de resposta para execução."""
    
    id: UUID = Field(..., description="ID da execução")
    team_id: UUID = Field(..., description="ID da equipe")
    user_id: UUID = Field(..., description="ID do usuário")
    status: ExecutionStatus = Field(..., description="Status da execução")
    input_data: Dict[str, Any] = Field(..., description="Dados de entrada")
    execution_config: ExecutionConfig = Field(..., description="Configuração da execução")
    progress: ExecutionProgress = Field(..., description="Progresso da execução")
    results: List[AgentResult] = Field(default_factory=list, description="Resultados dos agentes")
    logs: List[ExecutionLog] = Field(default_factory=list, description="Logs da execução")
    started_at: Optional[datetime] = Field(None, description="Início da execução")
    completed_at: Optional[datetime] = Field(None, description="Fim da execução")
    error_message: Optional[str] = Field(None, description="Mensagem de erro geral")
    estimated_completion: Optional[datetime] = Field(None, description="Estimativa de conclusão")


class ExecutionListItem(BaseSchema):
    """Item da lista de execuções."""
    
    id: UUID
    team_id: UUID
    team_name: str
    status: ExecutionStatus
    progress: ExecutionProgress
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class ExecutionStartResponse(BaseSchema):
    """Resposta ao iniciar uma execução."""
    
    execution_id: UUID = Field(..., description="ID da execução criada")
    team_id: UUID = Field(..., description="ID da equipe")
    status: ExecutionStatus = Field(..., description="Status inicial")
    started_at: datetime = Field(..., description="Timestamp de início")
    estimated_completion: Optional[datetime] = Field(None, description="Estimativa de conclusão")
    progress: ExecutionProgress = Field(..., description="Progresso inicial")


class ExecutionCancelResponse(BaseSchema):
    """Resposta ao cancelar uma execução."""
    
    execution_id: UUID = Field(..., description="ID da execução")
    status: ExecutionStatus = Field(..., description="Status após cancelamento")
    cancelled_at: datetime = Field(..., description="Timestamp do cancelamento")