"""
Orchestrator API endpoints
Handles workflow creation, execution, and monitoring
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.orchestrator import (
    CreateWorkflowSchema,
    UpdateWorkflowSchema,
    WorkflowSchema,
    ExecuteWorkflowSchema,
    WorkflowRunSchema,
    ChatMessageSchema,
    OrchestratorResponseSchema,
    ExecutionPlanSchema,
    ExecutionMetricsSchema
)
from app.services.orchestrator_service import OrchestratorService
from app.repositories.orchestrator_repository import OrchestratorRepository

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])

def get_orchestrator_service() -> OrchestratorService:
    """Get orchestrator service instance"""
    # In real implementation, would inject Supabase client
    orchestrator_repo = OrchestratorRepository()
    return OrchestratorService(orchestrator_repo)

@router.post("/workflows", response_model=WorkflowSchema)
async def create_workflow(
    workflow_data: CreateWorkflowSchema,
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """Create new workflow"""
    try:
        # For now, use a mock user ID
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        # Convert schema to dict
        workflow_dict = {
            'name': workflow_data.name,
            'description': workflow_data.description,
            'steps': [
                {
                    'step_id': step.step_id,
                    'agent_id': step.agent_id,
                    'agent_version': step.agent_version,
                    'action': step.action,
                    'input_data': step.input_data,
                    'depends_on': step.depends_on,
                    'timeout_seconds': step.timeout_seconds,
                    'retry_count': step.retry_count,
                    'condition': step.condition
                } for step in workflow_data.steps
            ],
            'config': {
                'execution_strategy': workflow_data.config.execution_strategy,
                'max_parallel_steps': workflow_data.config.max_parallel_steps,
                'failure_strategy': workflow_data.config.failure_strategy,
                'retry_policy': workflow_data.config.retry_policy,
                'timeout_minutes': workflow_data.config.timeout_minutes
            }
        }
        
        workflow = await orchestrator_service.create_workflow(mock_user_id, workflow_dict)
        
        return WorkflowSchema(
            id=workflow.id,
            user_id=workflow.user_id,
            name=workflow.name,
            description=workflow.description,
            workflow_data={
                'steps': [step.to_dict() for step in workflow.steps],
                'config': workflow.config.to_dict()
            },
            agents_used=workflow.agents_used,
            status=workflow.status.value,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )

@router.get("/workflows", response_model=List[WorkflowSchema])
async def list_workflows(
    status_filter: Optional[str] = Query(None, description="Filter by workflow status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """List user workflows"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        workflows = await orchestrator_service.list_user_workflows(
            mock_user_id, status_filter, limit, offset
        )
        
        return [
            WorkflowSchema(
                id=workflow.id,
                user_id=workflow.user_id,
                name=workflow.name,
                description=workflow.description,
                workflow_data={
                    'steps': [step.to_dict() for step in workflow.steps],
                    'config': workflow.config.to_dict()
                },
                agents_used=workflow.agents_used,
                status=workflow.status.value,
                created_at=workflow.created_at,
                updated_at=workflow.updated_at
            ) for workflow in workflows
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar workflows: {str(e)}"
        )

@router.get("/workflows/{workflow_id}", response_model=WorkflowSchema)
async def get_workflow(
    workflow_id: UUID,
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """Get workflow by ID"""
    try:
        workflow = await orchestrator_service.get_workflow_by_id(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} não encontrado"
            )
        
        return WorkflowSchema(
            id=workflow.id,
            user_id=workflow.user_id,
            name=workflow.name,
            description=workflow.description,
            workflow_data={
                'steps': [step.to_dict() for step in workflow.steps],
                'config': workflow.config.to_dict()
            },
            agents_used=workflow.agents_used,
            status=workflow.status.value,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar workflow: {str(e)}"
        )

@router.post("/workflows/{workflow_id}/execute", response_model=WorkflowRunSchema)
async def execute_workflow(
    workflow_id: UUID,
    execution_data: ExecuteWorkflowSchema,
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """Execute workflow"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        workflow_run = await orchestrator_service.execute_workflow(
            workflow_id=workflow_id,
            user_id=mock_user_id,
            input_data=execution_data.input_data,
            dry_run=execution_data.dry_run
        )
        
        return WorkflowRunSchema(
            id=workflow_run.id,
            workflow_id=workflow_run.workflow_id,
            user_id=workflow_run.user_id,
            status=workflow_run.status.value,
            input_data=workflow_run.input_data,
            results=[result.to_dict() for result in workflow_run.results],
            execution_logs=[log.to_dict() for log in workflow_run.execution_logs],
            error_message=workflow_run.error_message,
            started_at=workflow_run.started_at,
            completed_at=workflow_run.completed_at,
            created_at=workflow_run.created_at,
            updated_at=workflow_run.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar workflow: {str(e)}"
        )

@router.get("/runs/{run_id}", response_model=WorkflowRunSchema)
async def get_workflow_run(
    run_id: UUID,
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """Get workflow run by ID"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        workflow_run = await orchestrator_service.get_workflow_run_by_id(run_id, mock_user_id)
        if not workflow_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execução {run_id} não encontrada"
            )
        
        return WorkflowRunSchema(
            id=workflow_run.id,
            workflow_id=workflow_run.workflow_id,
            user_id=workflow_run.user_id,
            status=workflow_run.status.value,
            input_data=workflow_run.input_data,
            results=[result.to_dict() for result in workflow_run.results],
            execution_logs=[log.to_dict() for log in workflow_run.execution_logs],
            error_message=workflow_run.error_message,
            started_at=workflow_run.started_at,
            completed_at=workflow_run.completed_at,
            created_at=workflow_run.created_at,
            updated_at=workflow_run.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar execução: {str(e)}"
        )

@router.post("/runs/{run_id}/cancel", response_model=WorkflowRunSchema)
async def cancel_workflow_run(
    run_id: UUID,
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """Cancel running workflow"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        workflow_run = await orchestrator_service.cancel_workflow_run(run_id, mock_user_id)
        
        return WorkflowRunSchema(
            id=workflow_run.id,
            workflow_id=workflow_run.workflow_id,
            user_id=workflow_run.user_id,
            status=workflow_run.status.value,
            input_data=workflow_run.input_data,
            results=[result.to_dict() for result in workflow_run.results],
            execution_logs=[log.to_dict() for log in workflow_run.execution_logs],
            error_message=workflow_run.error_message,
            started_at=workflow_run.started_at,
            completed_at=workflow_run.completed_at,
            created_at=workflow_run.created_at,
            updated_at=workflow_run.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao cancelar execução: {str(e)}"
        )

@router.get("/runs", response_model=List[WorkflowRunSchema])
async def list_workflow_runs(
    workflow_id: Optional[UUID] = Query(None, description="Filter by workflow ID"),
    status_filter: Optional[str] = Query(None, description="Filter by run status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """List workflow runs"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        workflow_runs = await orchestrator_service.list_workflow_runs(
            user_id=mock_user_id,
            workflow_id=workflow_id,
            status=status_filter,
            limit=limit,
            offset=offset
        )
        
        return [
            WorkflowRunSchema(
                id=run.id,
                workflow_id=run.workflow_id,
                user_id=run.user_id,
                status=run.status.value,
                input_data=run.input_data,
                results=[result.to_dict() for result in run.results],
                execution_logs=[log.to_dict() for log in run.execution_logs],
                error_message=run.error_message,
                started_at=run.started_at,
                completed_at=run.completed_at,
                created_at=run.created_at,
                updated_at=run.updated_at
            ) for run in workflow_runs
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar execuções: {str(e)}"
        )

@router.post("/chat", response_model=OrchestratorResponseSchema)
async def chat_with_orchestrator(
    message: ChatMessageSchema,
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """Chat with orchestrator for conversational workflow creation"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        response = await orchestrator_service.process_chat_message(
            user_id=mock_user_id,
            message=message.message,
            context=message.context
        )
        
        return OrchestratorResponseSchema(
            message=response['message'],
            suggested_actions=response.get('suggested_actions', []),
            execution_plan=response.get('execution_plan'),
            requires_confirmation=response.get('requires_confirmation', False),
            context=response.get('context', {})
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no chat: {str(e)}"
        )

@router.get("/metrics", response_model=ExecutionMetricsSchema)
async def get_execution_metrics(
    workflow_id: Optional[UUID] = Query(None, description="Filter by workflow ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """Get execution metrics and analytics"""
    try:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        metrics = await orchestrator_service.get_execution_metrics(
            user_id=mock_user_id,
            workflow_id=workflow_id,
            days=days
        )
        
        return ExecutionMetricsSchema(
            total_executions=metrics['total_executions'],
            successful_executions=metrics['successful_executions'],
            failed_executions=metrics['failed_executions'],
            success_rate=metrics['success_rate'],
            avg_execution_time_ms=metrics['avg_execution_time_ms'],
            total_agents_used=metrics['total_agents_used'],
            most_used_agents=metrics['most_used_agents'],
            execution_trends=metrics['execution_trends']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter métricas: {str(e)}"
        )

@router.get("/active-runs", response_model=List[dict])
async def get_active_runs(
    orchestrator_service: OrchestratorService = Depends(get_orchestrator_service)
):
    """Get currently active workflow runs"""
    try:
        active_runs = await orchestrator_service.get_active_runs()
        return active_runs
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter execuções ativas: {str(e)}"
        )