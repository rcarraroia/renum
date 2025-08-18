"""
Schemas Pydantic para orquestração e workflows
Baseado na estrutura real das tabelas workflows e workflow_runs no Supabase
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class WorkflowStepSchema(BaseModel):
    """Schema para um passo do workflow"""
    
    step_id: str = Field(..., description="ID único do passo")
    agent_id: str = Field(..., description="ID do agente a executar")
    agent_version: str = Field(default="latest", description="Versão do agente")
    action: str = Field(..., description="Ação a ser executada")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Dados de entrada")
    depends_on: List[str] = Field(default_factory=list, description="IDs dos passos dependentes")
    timeout_seconds: int = Field(default=300, description="Timeout do passo")
    retry_count: int = Field(default=0, description="Número de tentativas")
    condition: Optional[str] = Field(None, description="Condição para execução")
    
    class Config:
        json_schema_extra = {
            "example": {
                "step_id": "send_email_1",
                "agent_id": "sa-email-basic",
                "agent_version": "1.0.0",
                "action": "send_email",
                "input_data": {
                    "to": "user@example.com",
                    "subject": "Test Email",
                    "body": "Hello World"
                },
                "depends_on": [],
                "timeout_seconds": 60
            }
        }


class WorkflowConfigSchema(BaseModel):
    """Schema para configuração do workflow"""
    
    execution_strategy: str = Field(default="sequential", description="Estratégia de execução")
    max_parallel_steps: int = Field(default=5, description="Máximo de passos paralelos")
    failure_strategy: str = Field(default="stop", description="Estratégia em caso de falha")
    retry_policy: Dict[str, Any] = Field(default_factory=dict, description="Política de retry")
    timeout_minutes: int = Field(default=30, description="Timeout total do workflow")
    
    @validator('execution_strategy')
    def validate_execution_strategy(cls, v):
        """Validar estratégia de execução"""
        allowed = ['sequential', 'parallel', 'pipeline', 'conditional']
        if v not in allowed:
            raise ValueError(f'Estratégia deve ser uma de: {", ".join(allowed)}')
        return v
    
    @validator('failure_strategy')
    def validate_failure_strategy(cls, v):
        """Validar estratégia de falha"""
        allowed = ['stop', 'continue', 'retry', 'rollback']
        if v not in allowed:
            raise ValueError(f'Estratégia de falha deve ser uma de: {", ".join(allowed)}')
        return v


class CreateWorkflowSchema(BaseModel):
    """Schema para criação de workflow"""
    
    name: str = Field(..., min_length=1, max_length=200, description="Nome do workflow")
    description: Optional[str] = Field(None, description="Descrição do workflow")
    steps: List[WorkflowStepSchema] = Field(..., min_items=1, description="Passos do workflow")
    config: WorkflowConfigSchema = Field(default_factory=WorkflowConfigSchema, description="Configuração")
    agents_used: List[str] = Field(default_factory=list, description="Lista de agentes utilizados")
    
    @validator('agents_used', pre=True, always=True)
    def extract_agents_from_steps(cls, v, values):
        """Extrair agentes dos passos automaticamente"""
        if 'steps' in values:
            agents = list(set(step.agent_id for step in values['steps']))
            return agents
        return v or []
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Email Notification Workflow",
                "description": "Enviar email de notificação para usuários",
                "steps": [
                    {
                        "step_id": "send_email",
                        "agent_id": "sa-email-basic",
                        "action": "send_email",
                        "input_data": {
                            "to": "user@example.com",
                            "subject": "Notification",
                            "body": "Your task is complete"
                        }
                    }
                ]
            }
        }


class UpdateWorkflowSchema(BaseModel):
    """Schema para atualização de workflow"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    steps: Optional[List[WorkflowStepSchema]] = None
    config: Optional[WorkflowConfigSchema] = None
    status: Optional[str] = Field(None, regex="^(draft|active|inactive|archived)$")


class WorkflowSchema(BaseModel):
    """Schema completo de workflow (response)"""
    
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    workflow_data: Dict[str, Any]  # Contém steps e config
    agents_used: List[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ExecuteWorkflowSchema(BaseModel):
    """Schema para execução de workflow"""
    
    workflow_id: UUID = Field(..., description="ID do workflow a executar")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Dados de entrada globais")
    override_config: Optional[WorkflowConfigSchema] = Field(None, description="Configuração override")
    dry_run: bool = Field(default=False, description="Execução de teste")
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "input_data": {
                    "user_email": "user@example.com",
                    "notification_type": "welcome"
                },
                "dry_run": False
            }
        }


class WorkflowRunStepResult(BaseModel):
    """Schema para resultado de um passo da execução"""
    
    step_id: str
    agent_id: str
    status: str  # pending, running, completed, failed, skipped
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowRunSchema(BaseModel):
    """Schema completo de execução de workflow"""
    
    id: UUID
    workflow_id: UUID
    user_id: UUID
    status: str  # pending, running, completed, failed, cancelled
    input_data: Dict[str, Any]
    results: List[WorkflowRunStepResult]
    execution_logs: List[Dict[str, Any]]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessageSchema(BaseModel):
    """Schema para mensagem de chat com orquestrador"""
    
    message: str = Field(..., min_length=1, description="Mensagem do usuário")
    session_id: Optional[str] = Field(None, description="ID da sessão de conversa")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Preciso enviar um email para todos os clientes sobre a nova promoção",
                "session_id": "sess_123456",
                "context": {
                    "user_role": "marketing_manager",
                    "available_connections": ["gmail", "mailchimp"]
                }
            }
        }


class OrchestratorResponseSchema(BaseModel):
    """Schema para resposta do orquestrador"""
    
    message: str = Field(..., description="Resposta do orquestrador")
    session_id: str = Field(..., description="ID da sessão")
    requires_input: bool = Field(..., description="Se requer mais entrada do usuário")
    suggested_workflow: Optional[CreateWorkflowSchema] = Field(None, description="Workflow sugerido")
    missing_connections: Optional[List[str]] = Field(None, description="Conexões faltantes")
    confidence_score: float = Field(default=0.0, description="Confiança na resposta (0-1)")
    next_questions: Optional[List[str]] = Field(None, description="Próximas perguntas sugeridas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Entendi que você quer enviar emails para clientes. Preciso de mais informações:",
                "session_id": "sess_123456",
                "requires_input": True,
                "missing_connections": ["gmail"],
                "confidence_score": 0.85,
                "next_questions": [
                    "Qual é o assunto do email?",
                    "Você tem uma lista específica de clientes?"
                ]
            }
        }


class ExecutionPlanSchema(BaseModel):
    """Schema para plano de execução gerado pelo orquestrador"""
    
    plan_id: str = Field(..., description="ID único do plano")
    description: str = Field(..., description="Descrição do plano")
    workflow: CreateWorkflowSchema = Field(..., description="Workflow a ser executado")
    estimated_cost: float = Field(default=0.0, description="Custo estimado")
    estimated_duration_minutes: int = Field(default=5, description="Duração estimada")
    required_connections: List[str] = Field(default_factory=list, description="Conexões necessárias")
    risks: List[str] = Field(default_factory=list, description="Riscos identificados")
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "plan_email_campaign_001",
                "description": "Enviar email promocional para lista de clientes",
                "estimated_cost": 0.50,
                "estimated_duration_minutes": 10,
                "required_connections": ["gmail", "customer_database"],
                "risks": ["Rate limiting do Gmail", "Lista de emails pode estar desatualizada"]
            }
        }


class ExecutionMetricsSchema(BaseModel):
    """Schema para métricas de execução"""
    
    run_id: UUID
    total_steps: int
    completed_steps: int
    failed_steps: int
    skipped_steps: int
    total_execution_time_ms: int
    total_cost: float
    success_rate: float
    
    class Config:
        from_attributes = True