"""
API Endpoints para Sistema de Sandbox
Endpoints para execução isolada e segura de agentes
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime, timedelta

from app.middleware.auth import get_current_user
from app.services.sandbox_service import sandbox_service
from app.services.analytics_service import analytics_service
from app.schemas.sandbox import (
    SandboxExecutionRequest,
    SandboxExecutionResponse,
    CreateSandboxResponse,
    SandboxListResponse,
    SandboxLogsResponse,
    SandboxHealthCheck,
    SandboxMetrics,
    SandboxTestTemplate,
    CreateSandboxTestTemplateRequest,
    SandboxTestTemplateList
)
from app.schemas.user import User
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

@router.post("/create", response_model=CreateSandboxResponse)
async def create_sandbox(
    request: SandboxExecutionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Criar novo sandbox para teste de agente
    
    Cria um ambiente isolado e seguro para execução de agentes
    com recursos limitados e integrações mockadas.
    """
    try:
        logger.info(
            "Creating sandbox",
            user_id=current_user.user_id,
            agent_id=request.agent_id,
            capability=request.capability
        )
        
        # Verificar se o serviço está inicializado
        if not sandbox_service.docker_client:
            await sandbox_service.initialize()
        
        # Criar sandbox
        sandbox_id = await sandbox_service.create_sandbox(
            execution_request=request,
            user_id=current_user.user_id
        )
        
        # Registrar métricas
        await analytics_service.track_sandbox_creation(
            user_id=current_user.user_id,
            sandbox_id=sandbox_id,
            agent_id=request.agent_id,
            capability=request.capability
        )
        
        return CreateSandboxResponse(
            sandbox_id=sandbox_id,
            status="created",
            created_at=datetime.utcnow(),
            estimated_ready_in_seconds=30
        )
        
    except ValueError as e:
        logger.warning("Sandbox creation failed", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Sandbox creation error", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to create sandbox")

@router.post("/{sandbox_id}/execute", response_model=SandboxExecutionResponse)
async def execute_sandbox(
    sandbox_id: str,
    timeout_seconds: Optional[int] = Query(None, ge=10, le=1800),
    current_user: User = Depends(get_current_user)
):
    """
    Executar sandbox e obter resultado
    
    Inicia a execução do agente no ambiente sandbox isolado
    e retorna o resultado completo da execução.
    """
    try:
        logger.info(
            "Executing sandbox",
            sandbox_id=sandbox_id,
            user_id=current_user.user_id,
            timeout_seconds=timeout_seconds
        )
        
        # Verificar se sandbox existe e pertence ao usuário
        active_sandboxes = await sandbox_service.list_active_sandboxes(current_user.user_id)
        sandbox_exists = any(s['sandbox_id'] == sandbox_id for s in active_sandboxes)
        
        if not sandbox_exists:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        # Executar sandbox
        execution_result = await sandbox_service.execute_sandbox(
            sandbox_id=sandbox_id,
            timeout_seconds=timeout_seconds
        )
        
        # Registrar métricas
        await analytics_service.track_sandbox_execution(
            user_id=current_user.user_id,
            sandbox_id=sandbox_id,
            execution_result=execution_result
        )
        
        return SandboxExecutionResponse(
            sandbox_id=sandbox_id,
            execution_result=execution_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Sandbox execution error",
            sandbox_id=sandbox_id,
            error=str(e),
            user_id=current_user.user_id
        )
        raise HTTPException(status_code=500, detail="Failed to execute sandbox")

@router.post("/execute-immediate", response_model=SandboxExecutionResponse)
async def execute_sandbox_immediate(
    request: SandboxExecutionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Criar e executar sandbox imediatamente
    
    Conveniência para criar um sandbox e executá-lo em uma única operação.
    O sandbox é automaticamente limpo após a execução.
    """
    try:
        logger.info(
            "Creating and executing sandbox immediately",
            user_id=current_user.user_id,
            agent_id=request.agent_id,
            capability=request.capability
        )
        
        # Verificar se o serviço está inicializado
        if not sandbox_service.docker_client:
            await sandbox_service.initialize()
        
        # Criar sandbox
        sandbox_id = await sandbox_service.create_sandbox(
            execution_request=request,
            user_id=current_user.user_id
        )
        
        # Executar imediatamente
        execution_result = await sandbox_service.execute_sandbox(
            sandbox_id=sandbox_id,
            timeout_seconds=request.timeout_seconds
        )
        
        # Registrar métricas
        await analytics_service.track_sandbox_execution(
            user_id=current_user.user_id,
            sandbox_id=sandbox_id,
            execution_result=execution_result
        )
        
        return SandboxExecutionResponse(
            sandbox_id=sandbox_id,
            execution_result=execution_result
        )
        
    except ValueError as e:
        logger.warning("Immediate sandbox execution failed", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Immediate sandbox execution error", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to execute sandbox")

@router.get("/list", response_model=SandboxListResponse)
async def list_sandboxes(
    current_user: User = Depends(get_current_user)
):
    """
    Listar sandboxes ativos do usuário
    
    Retorna todos os sandboxes ativos pertencentes ao usuário atual.
    """
    try:
        sandboxes = await sandbox_service.list_active_sandboxes(current_user.user_id)
        
        # Converter para formato de resposta
        sandbox_infos = []
        for sandbox in sandboxes:
            sandbox_infos.append({
                'sandbox_id': sandbox['sandbox_id'],
                'user_id': sandbox['user_id'],
                'agent_id': sandbox['agent_id'],
                'capability': sandbox.get('capability', 'unknown'),
                'status': sandbox['status'],
                'created_at': sandbox['created_at'],
                'started_at': None,  # TODO: implementar tracking de início
                'completed_at': None,  # TODO: implementar tracking de conclusão
                'resource_quota': {
                    'cpu_cores': 0.5,
                    'memory_mb': 512,
                    'disk_mb': 1024,
                    'network_enabled': False,
                    'max_execution_time_seconds': 300
                },
                'container_id': sandbox['container_id']
            })
        
        active_count = len([s for s in sandbox_infos if s['status'] in ['created', 'running']])
        
        return SandboxListResponse(
            sandboxes=sandbox_infos,
            total_count=len(sandbox_infos),
            active_count=active_count
        )
        
    except Exception as e:
        logger.error("Failed to list sandboxes", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to list sandboxes")

@router.get("/{sandbox_id}/logs", response_model=SandboxLogsResponse)
async def get_sandbox_logs(
    sandbox_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Obter logs do sandbox
    
    Retorna os logs completos da execução do sandbox.
    """
    try:
        # Verificar se sandbox existe e pertence ao usuário
        active_sandboxes = await sandbox_service.list_active_sandboxes(current_user.user_id)
        sandbox_exists = any(s['sandbox_id'] == sandbox_id for s in active_sandboxes)
        
        if not sandbox_exists:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        # Obter logs
        logs = await sandbox_service.get_sandbox_logs(sandbox_id)
        log_lines = logs.split('\n') if logs else []
        
        return SandboxLogsResponse(
            sandbox_id=sandbox_id,
            logs=logs,
            log_lines=log_lines,
            retrieved_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get sandbox logs",
            sandbox_id=sandbox_id,
            error=str(e),
            user_id=current_user.user_id
        )
        raise HTTPException(status_code=500, detail="Failed to get sandbox logs")

@router.get("/{sandbox_id}/logs/stream")
async def stream_sandbox_logs(
    sandbox_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Stream logs do sandbox em tempo real
    
    Retorna um stream de logs em tempo real do sandbox.
    """
    try:
        # Verificar se sandbox existe e pertence ao usuário
        active_sandboxes = await sandbox_service.list_active_sandboxes(current_user.user_id)
        sandbox_exists = any(s['sandbox_id'] == sandbox_id for s in active_sandboxes)
        
        if not sandbox_exists:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        async def log_generator():
            """Gerador de logs em tempo real"""
            last_logs = ""
            
            while True:
                try:
                    current_logs = await sandbox_service.get_sandbox_logs(sandbox_id)
                    
                    # Enviar apenas logs novos
                    if current_logs != last_logs:
                        new_logs = current_logs[len(last_logs):]
                        if new_logs:
                            yield f"data: {json.dumps({'logs': new_logs, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                        last_logs = current_logs
                    
                    # Verificar se sandbox ainda está ativo
                    active_sandboxes = await sandbox_service.list_active_sandboxes(current_user.user_id)
                    sandbox_still_active = any(s['sandbox_id'] == sandbox_id for s in active_sandboxes)
                    
                    if not sandbox_still_active:
                        yield f"data: {json.dumps({'status': 'completed', 'message': 'Sandbox execution completed'})}\n\n"
                        break
                    
                    await asyncio.sleep(1)  # Poll a cada segundo
                    
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    break
        
        return StreamingResponse(
            log_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to stream sandbox logs",
            sandbox_id=sandbox_id,
            error=str(e),
            user_id=current_user.user_id
        )
        raise HTTPException(status_code=500, detail="Failed to stream sandbox logs")

@router.delete("/{sandbox_id}")
async def cleanup_sandbox(
    sandbox_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Limpar sandbox manualmente
    
    Remove o sandbox e todos os recursos associados.
    """
    try:
        # Verificar se sandbox existe e pertence ao usuário
        active_sandboxes = await sandbox_service.list_active_sandboxes(current_user.user_id)
        sandbox_exists = any(s['sandbox_id'] == sandbox_id for s in active_sandboxes)
        
        if not sandbox_exists:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        # Limpar sandbox
        await sandbox_service._cleanup_sandbox(sandbox_id)
        
        logger.info(
            "Sandbox cleaned up manually",
            sandbox_id=sandbox_id,
            user_id=current_user.user_id
        )
        
        return {"message": "Sandbox cleaned up successfully", "sandbox_id": sandbox_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to cleanup sandbox",
            sandbox_id=sandbox_id,
            error=str(e),
            user_id=current_user.user_id
        )
        raise HTTPException(status_code=500, detail="Failed to cleanup sandbox")

@router.get("/health", response_model=SandboxHealthCheck)
async def sandbox_health_check():
    """
    Verificar saúde do sistema de sandbox
    
    Retorna informações sobre o status e saúde do sistema de sandbox.
    """
    try:
        # Verificar se Docker está disponível
        docker_available = False
        try:
            if not sandbox_service.docker_client:
                await sandbox_service.initialize()
            docker_available = sandbox_service.docker_client.ping()
        except:
            pass
        
        # Verificar rede
        network_configured = False
        try:
            sandbox_service.docker_client.networks.get(sandbox_service.sandbox_network)
            network_configured = True
        except:
            pass
        
        # Verificar imagens base
        base_images_ready = False
        try:
            sandbox_service.docker_client.images.get(sandbox_service.base_image)
            base_images_ready = True
        except:
            pass
        
        # Contar sandboxes ativos
        active_sandboxes = await sandbox_service.list_active_sandboxes()
        active_count = len(active_sandboxes)
        
        # Determinar status geral
        status = "healthy" if (docker_available and network_configured and base_images_ready) else "unhealthy"
        
        # Identificar problemas
        issues = []
        if not docker_available:
            issues.append("Docker not available")
        if not network_configured:
            issues.append("Sandbox network not configured")
        if not base_images_ready:
            issues.append("Base images not ready")
        
        return SandboxHealthCheck(
            status=status,
            docker_available=docker_available,
            network_configured=network_configured,
            base_images_ready=base_images_ready,
            active_sandboxes_count=active_count,
            max_sandboxes_limit=sandbox_service.max_concurrent_sandboxes,
            system_resources={
                "available_memory_gb": 8,  # TODO: obter recursos reais do sistema
                "available_cpu_cores": 4,
                "available_disk_gb": 100
            },
            issues=issues,
            checked_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Sandbox health check failed", error=str(e))
        return SandboxHealthCheck(
            status="unhealthy",
            docker_available=False,
            network_configured=False,
            base_images_ready=False,
            active_sandboxes_count=0,
            max_sandboxes_limit=0,
            issues=[f"Health check failed: {str(e)}"],
            checked_at=datetime.utcnow()
        )

@router.get("/metrics", response_model=SandboxMetrics)
async def get_sandbox_metrics(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user)
):
    """
    Obter métricas do sistema de sandbox
    
    Retorna métricas agregadas de uso do sistema de sandbox.
    """
    try:
        # Calcular período
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Obter métricas do analytics service
        metrics = await analytics_service.get_sandbox_metrics(
            user_id=current_user.user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return SandboxMetrics(
            total_executions=metrics.get('total_executions', 0),
            successful_executions=metrics.get('successful_executions', 0),
            failed_executions=metrics.get('failed_executions', 0),
            timeout_executions=metrics.get('timeout_executions', 0),
            average_execution_time_ms=metrics.get('average_execution_time_ms', 0),
            average_memory_usage_mb=metrics.get('average_memory_usage_mb', 0),
            average_cpu_usage_percent=metrics.get('average_cpu_usage_percent', 0),
            most_tested_agents=metrics.get('most_tested_agents', []),
            resource_efficiency=metrics.get('resource_efficiency', {}),
            period_start=start_date,
            period_end=end_date
        )
        
    except Exception as e:
        logger.error("Failed to get sandbox metrics", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to get sandbox metrics")

# Background task para limpeza automática
@router.post("/cleanup/expired")
async def cleanup_expired_sandboxes(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Limpar sandboxes expirados (apenas admin)
    
    Inicia limpeza em background de sandboxes expirados.
    """
    # Verificar se usuário é admin
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    background_tasks.add_task(sandbox_service.cleanup_expired_sandboxes)
    
    return {"message": "Cleanup task started", "initiated_by": current_user.user_id}

# Templates de teste (funcionalidade adicional)
@router.get("/templates", response_model=SandboxTestTemplateList)
async def list_test_templates(
    agent_id: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Listar templates de teste disponíveis
    
    Retorna templates pré-configurados para testes de agentes.
    """
    # TODO: Implementar sistema de templates
    # Por enquanto, retornar templates hardcoded
    
    templates = [
        SandboxTestTemplate(
            template_id="whatsapp-send-message",
            name="WhatsApp Send Message",
            description="Template para testar envio de mensagem via WhatsApp",
            agent_id="sa-whatsapp",
            capability="send_message",
            default_input={
                "phone_number": "+5511999999999",
                "message": "Hello from sandbox test!"
            },
            mock_configurations={
                "whatsapp": {
                    "service_name": "whatsapp",
                    "endpoints": [
                        {
                            "endpoint": "/messages",
                            "method": "POST",
                            "response": {
                                "messages": [{"id": "wamid_test_123"}]
                            },
                            "delay_ms": 100
                        }
                    ]
                }
            },
            tags=["whatsapp", "messaging"],
            created_by="system",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]
    
    # Filtrar por agent_id e capability se fornecidos
    if agent_id:
        templates = [t for t in templates if t.agent_id == agent_id]
    if capability:
        templates = [t for t in templates if t.capability == capability]
    
    return SandboxTestTemplateList(
        templates=templates,
        total_count=len(templates)
    )