"""
Domain models para orquestração de agentes
Entidades de negócio para workflows e execuções multi-agente
"""

import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4


class ExecutionStrategy(Enum):
    """Estratégias de execução de workflow"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"


class WorkflowStatus(Enum):
    """Status do workflow"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ExecutionStatus(Enum):
    """Status de execução"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Status de passo de execução"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep:
    """Passo individual de um workflow"""
    
    def __init__(
        self,
        step_id: str,
        agent_id: str,
        agent_version: str = "latest",
        action: str = "",
        input_data: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        timeout_seconds: int = 300,
        retry_count: int = 0,
        condition: Optional[str] = None
    ):
        self.step_id = step_id
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.action = action
        self.input_data = input_data or {}
        self.depends_on = depends_on or []
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.condition = condition
        
        # Execution state
        self.status = StepStatus.PENDING
        self.output_data: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None
        self.execution_time_ms: Optional[int] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
    
    def can_execute(self, completed_steps: List[str]) -> bool:
        """Verificar se o passo pode ser executado baseado nas dependências"""
        if not self.depends_on:
            return True
        
        return all(dep in completed_steps for dep in self.depends_on)
    
    def start_execution(self):
        """Marcar passo como iniciado"""
        self.status = StepStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete_execution(self, output_data: Dict[str, Any], execution_time_ms: int):
        """Marcar passo como completado"""
        self.status = StepStatus.COMPLETED
        self.output_data = output_data
        self.execution_time_ms = execution_time_ms
        self.completed_at = datetime.utcnow()
    
    def fail_execution(self, error_message: str, execution_time_ms: int):
        """Marcar passo como falhado"""
        self.status = StepStatus.FAILED
        self.error_message = error_message
        self.execution_time_ms = execution_time_ms
        self.completed_at = datetime.utcnow()
    
    def skip_execution(self, reason: str):
        """Marcar passo como pulado"""
        self.status = StepStatus.SKIPPED
        self.error_message = reason
        self.completed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'step_id': self.step_id,
            'agent_id': self.agent_id,
            'agent_version': self.agent_version,
            'action': self.action,
            'input_data': self.input_data,
            'depends_on': self.depends_on,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'condition': self.condition,
            'status': self.status.value,
            'output_data': self.output_data,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class WorkflowConfig:
    """Configuração de execução do workflow"""
    
    def __init__(
        self,
        execution_strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
        max_parallel_steps: int = 5,
        failure_strategy: str = "stop",
        retry_policy: Optional[Dict[str, Any]] = None,
        timeout_minutes: int = 30
    ):
        self.execution_strategy = execution_strategy
        self.max_parallel_steps = max_parallel_steps
        self.failure_strategy = failure_strategy
        self.retry_policy = retry_policy or {}
        self.timeout_minutes = timeout_minutes
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'execution_strategy': self.execution_strategy.value,
            'max_parallel_steps': self.max_parallel_steps,
            'failure_strategy': self.failure_strategy,
            'retry_policy': self.retry_policy,
            'timeout_minutes': self.timeout_minutes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowConfig':
        """Criar a partir de dicionário"""
        return cls(
            execution_strategy=ExecutionStrategy(data.get('execution_strategy', 'sequential')),
            max_parallel_steps=data.get('max_parallel_steps', 5),
            failure_strategy=data.get('failure_strategy', 'stop'),
            retry_policy=data.get('retry_policy', {}),
            timeout_minutes=data.get('timeout_minutes', 30)
        )


class Workflow:
    """Entidade de domínio para workflow"""
    
    def __init__(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        steps: Optional[List[WorkflowStep]] = None,
        config: Optional[WorkflowConfig] = None,
        status: WorkflowStatus = WorkflowStatus.DRAFT,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.user_id = user_id
        self.name = name
        self.description = description
        self.steps = steps or []
        self.config = config or WorkflowConfig()
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Validar na criação
        self._validate()
    
    def _validate(self):
        """Validar regras de negócio do workflow"""
        if not self.name:
            raise ValueError("Workflow deve ter um nome")
        
        if not self.steps:
            raise ValueError("Workflow deve ter pelo menos um passo")
        
        # Validar IDs únicos dos passos
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("IDs dos passos devem ser únicos")
        
        # Validar dependências
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(f"Dependência '{dep}' não encontrada nos passos")
    
    def add_step(self, step: WorkflowStep):
        """Adicionar passo ao workflow"""
        # Verificar ID único
        if any(s.step_id == step.step_id for s in self.steps):
            raise ValueError(f"Passo com ID '{step.step_id}' já existe")
        
        self.steps.append(step)
        self.updated_at = datetime.utcnow()
    
    def remove_step(self, step_id: str):
        """Remover passo do workflow"""
        # Verificar se outros passos dependem deste
        for step in self.steps:
            if step_id in step.depends_on:
                raise ValueError(f"Passo '{step_id}' é dependência de '{step.step_id}'")
        
        self.steps = [s for s in self.steps if s.step_id != step_id]
        self.updated_at = datetime.utcnow()
    
    def get_agents_used(self) -> List[str]:
        """Obter lista de agentes utilizados"""
        return list(set(step.agent_id for step in self.steps))
    
    def activate(self):
        """Ativar workflow"""
        if self.status == WorkflowStatus.ARCHIVED:
            raise ValueError("Workflow arquivado não pode ser ativado")
        
        self.status = WorkflowStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Desativar workflow"""
        self.status = WorkflowStatus.INACTIVE
        self.updated_at = datetime.utcnow()
    
    def archive(self):
        """Arquivar workflow"""
        self.status = WorkflowStatus.ARCHIVED
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'name': self.name,
            'description': self.description,
            'workflow_data': {
                'steps': [step.to_dict() for step in self.steps],
                'config': self.config.to_dict()
            },
            'agents_used': self.get_agents_used(),
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class WorkflowExecution:
    """Entidade para execução de workflow"""
    
    def __init__(
        self,
        workflow_id: UUID,
        user_id: UUID,
        input_data: Optional[Dict[str, Any]] = None,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        id: Optional[UUID] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.workflow_id = workflow_id
        self.user_id = user_id
        self.input_data = input_data or {}
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Execution state
        self.results: List[Dict[str, Any]] = []
        self.execution_logs: List[Dict[str, Any]] = []
        self.error_message: Optional[str] = None
        self.total_cost: float = 0.0
    
    def start_execution(self):
        """Iniciar execução"""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def complete_execution(self, results: List[Dict[str, Any]], total_cost: float = 0.0):
        """Completar execução"""
        self.status = ExecutionStatus.COMPLETED
        self.results = results
        self.total_cost = total_cost
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def fail_execution(self, error_message: str):
        """Falhar execução"""
        self.status = ExecutionStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def cancel_execution(self):
        """Cancelar execução"""
        self.status = ExecutionStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_log(self, level: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Adicionar log de execução"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'metadata': metadata or {}
        }
        self.execution_logs.append(log_entry)
    
    def add_step_result(self, step_result: Dict[str, Any]):
        """Adicionar resultado de passo"""
        self.results.append(step_result)
        self.updated_at = datetime.utcnow()
    
    def get_execution_time_seconds(self) -> Optional[int]:
        """Obter tempo total de execução em segundos"""
        if not self.started_at or not self.completed_at:
            return None
        
        return int((self.completed_at - self.started_at).total_seconds())
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'id': str(self.id),
            'workflow_id': str(self.workflow_id),
            'user_id': str(self.user_id),
            'status': self.status.value,
            'input_data': self.input_data,
            'results': self.results,
            'execution_logs': self.execution_logs,
            'error_message': self.error_message,
            'total_cost': self.total_cost,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'execution_time_seconds': self.get_execution_time_seconds()
        }


class ConversationSession:
    """Sessão de conversa com o orquestrador"""
    
    def __init__(
        self,
        user_id: UUID,
        session_id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.session_id = session_id or f"sess_{uuid4().hex[:12]}"
        self.user_id = user_id
        self.created_at = created_at or datetime.utcnow()
        
        # Conversation state
        self.messages: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.current_workflow: Optional[Workflow] = None
        self.pending_confirmations: List[Dict[str, Any]] = []
        self.last_activity: datetime = datetime.utcnow()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Adicionar mensagem à conversa"""
        message = {
            'role': role,  # user, assistant, system
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        self.messages.append(message)
        self.last_activity = datetime.utcnow()
    
    def update_context(self, key: str, value: Any):
        """Atualizar contexto da conversa"""
        self.context[key] = value
        self.last_activity = datetime.utcnow()
    
    def add_pending_confirmation(self, confirmation_type: str, data: Dict[str, Any]):
        """Adicionar confirmação pendente"""
        confirmation = {
            'type': confirmation_type,
            'data': data,
            'created_at': datetime.utcnow().isoformat()
        }
        self.pending_confirmations.append(confirmation)
    
    def clear_pending_confirmations(self):
        """Limpar confirmações pendentes"""
        self.pending_confirmations = []
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Verificar se sessão expirou"""
        timeout_delta = datetime.utcnow() - self.last_activity
        return timeout_delta.total_seconds() > (timeout_minutes * 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'session_id': self.session_id,
            'user_id': str(self.user_id),
            'messages': self.messages,
            'context': self.context,
            'current_workflow': self.current_workflow.to_dict() if self.current_workflow else None,
            'pending_confirmations': self.pending_confirmations,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat()
        }