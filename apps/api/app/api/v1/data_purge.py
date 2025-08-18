"""
Endpoints para Purga de Dados e Conformidade LGPD/GDPR
API para gerenciamento de purga de dados com auditoria completa
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
import structlog

from app.services.data_purge_service import (
    data_purge_service, 
    EntityType, 
    PurgeReason, 
    PurgeStatus
)
from app.services.pii_service import pii_service
from app.middleware.auth import get_current_user, require_admin
from app.schemas.base import BaseResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/data", tags=["Data Purge & Compliance"])

@router.post("/purge")
async def create_purge_request(
    tenant_id: Optional[str] = Body(None, description="ID do tenant (opcional para purga global)"),
    entity_type: EntityType = Body(..., description="Tipo de entidade para purgar"),
    entity_ids: Optional[List[str]] = Body(None, description="IDs específicos para purgar"),
    before_date: Optional[datetime] = Body(None, description="Purgar registros antes desta data"),
    reason: PurgeReason = Body(PurgeReason.USER_REQUEST, description="Motivo da purga"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="Metadados adicionais"),
    current_user = Depends(require_admin)
):
    """
    Criar solicitação de purga de dados.
    
    Esta API permite criar solicitações de purga de dados para conformidade
    com LGPD/GDPR. Todas as purgas são auditadas e requerem aprovação.
    
    **Parâmetros:**
    - **tenant_id**: ID do tenant (opcional para purga global)
    - **entity_type**: Tipo de entidade (user, execution, workflow, etc.)
    - **entity_ids**: Lista de IDs específicos OU
    - **before_date**: Data limite para purga (registros anteriores)
    - **reason**: Motivo da purga (GDPR, LGPD, política de retenção, etc.)
    - **metadata**: Informações adicionais para auditoria
    
    **Requer privilégios de administrador.**
    """
    try:
        logger.info(
            "Creating purge request",
            entity_type=entity_type.value,
            tenant_id=tenant_id,
            reason=reason.value,
            user_id=current_user.get('user_id')
        )
        
        # Validações específicas
        if entity_type == EntityType.AUDIT_LOG and reason != PurgeReason.COMPLIANCE_REQUIREMENT:
            raise HTTPException(
                status_code=400,
                detail="Audit logs can only be purged for compliance requirements"
            )
        
        if not entity_ids and not before_date:
            raise HTTPException(
                status_code=400,
                detail="Must specify either entity_ids or before_date"
            )
        
        # Criar solicitação
        purge_request = await data_purge_service.create_purge_request(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_ids=entity_ids,
            before_date=before_date,
            reason=reason,
            requested_by=current_user.get('user_id', 'unknown'),
            metadata=metadata
        )
        
        return {
            "status": "success",
            "message": "Purge request created successfully",
            "purge_id": purge_request.purge_id,
            "entity_type": entity_type.value,
            "status": purge_request.status.value,
            "requires_approval": data_purge_service.require_approval,
            "created_at": purge_request.requested_at.isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create purge request", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to create purge request"
        )

@router.post("/purge/{purge_id}/approve")
async def approve_purge_request(
    purge_id: str,
    current_user = Depends(require_admin)
):
    """
    Aprovar solicitação de purga de dados.
    
    Aprova uma solicitação de purga pendente. Após aprovação,
    a purga pode ser executada.
    
    **Requer privilégios de administrador.**
    """
    try:
        logger.info(
            "Approving purge request",
            purge_id=purge_id,
            user_id=current_user.get('user_id')
        )
        
        success = await data_purge_service.approve_purge_request(
            purge_id=purge_id,
            approved_by=current_user.get('user_id', 'unknown')
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Purge request {purge_id} approved successfully",
                "purge_id": purge_id,
                "approved_by": current_user.get('user_id'),
                "approved_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to approve purge request"
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to approve purge request", purge_id=purge_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to approve purge request"
        )

@router.post("/purge/{purge_id}/execute")
async def execute_purge(
    purge_id: str,
    current_user = Depends(require_admin)
):
    """
    Executar purga de dados aprovada.
    
    Executa uma solicitação de purga que foi aprovada.
    A execução é feita em background e pode ser monitorada
    via endpoint de status.
    
    **Requer privilégios de administrador.**
    """
    try:
        logger.info(
            "Executing purge request",
            purge_id=purge_id,
            user_id=current_user.get('user_id')
        )
        
        result = await data_purge_service.execute_purge(purge_id)
        
        return {
            "status": "success",
            "message": f"Purge {purge_id} executed successfully",
            "execution_result": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to execute purge", purge_id=purge_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to execute purge"
        )

@router.get("/purge/{purge_id}/status")
async def get_purge_status(
    purge_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obter status de uma solicitação de purga.
    
    Retorna informações detalhadas sobre o status e progresso
    de uma solicitação de purga.
    
    **Requer autenticação.**
    """
    try:
        status = await data_purge_service.get_purge_status(purge_id)
        
        return {
            "status": "success",
            "data": status
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get purge status", purge_id=purge_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get purge status"
        )

@router.get("/purge/requests")
async def list_purge_requests(
    status: Optional[PurgeStatus] = Query(None, description="Filtrar por status"),
    entity_type: Optional[EntityType] = Query(None, description="Filtrar por tipo de entidade"),
    requested_by: Optional[str] = Query(None, description="Filtrar por solicitante"),
    limit: int = Query(100, description="Limite de resultados"),
    current_user = Depends(get_current_user)
):
    """
    Listar solicitações de purga.
    
    Lista todas as solicitações de purga com filtros opcionais.
    Usuários normais veem apenas suas próprias solicitações,
    administradores veem todas.
    
    **Requer autenticação.**
    """
    try:
        # Usuários normais só veem suas próprias solicitações
        if current_user.get('role') != 'admin':
            requested_by = current_user.get('user_id')
        
        requests = await data_purge_service.list_purge_requests(
            status=status,
            entity_type=entity_type,
            requested_by=requested_by,
            limit=limit
        )
        
        return {
            "status": "success",
            "data": {
                "requests": requests,
                "total_count": len(requests),
                "filters_applied": {
                    "status": status.value if status else None,
                    "entity_type": entity_type.value if entity_type else None,
                    "requested_by": requested_by
                }
            }
        }
        
    except Exception as e:
        logger.error("Failed to list purge requests", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to list purge requests"
        )

@router.delete("/purge/{purge_id}")
async def cancel_purge_request(
    purge_id: str,
    current_user = Depends(require_admin)
):
    """
    Cancelar solicitação de purga.
    
    Cancela uma solicitação de purga pendente ou em execução.
    Purgas já concluídas não podem ser canceladas.
    
    **Requer privilégios de administrador.**
    """
    try:
        logger.info(
            "Cancelling purge request",
            purge_id=purge_id,
            user_id=current_user.get('user_id')
        )
        
        success = await data_purge_service.cancel_purge_request(
            purge_id=purge_id,
            cancelled_by=current_user.get('user_id', 'unknown')
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Purge request {purge_id} cancelled successfully",
                "purge_id": purge_id,
                "cancelled_by": current_user.get('user_id'),
                "cancelled_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to cancel purge request"
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to cancel purge request", purge_id=purge_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel purge request"
        )

@router.get("/purge/audit")
async def get_purge_audit_log(
    purge_id: Optional[str] = Query(None, description="Filtrar por ID de purga"),
    start_date: Optional[datetime] = Query(None, description="Data inicial"),
    end_date: Optional[datetime] = Query(None, description="Data final"),
    limit: int = Query(1000, description="Limite de resultados"),
    current_user = Depends(require_admin)
):
    """
    Obter log de auditoria de purgas.
    
    Retorna o log de auditoria imutável de todas as operações
    de purga. Essencial para conformidade e rastreabilidade.
    
    **Requer privilégios de administrador.**
    """
    try:
        audit_log = await data_purge_service.get_audit_log(
            purge_id=purge_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "status": "success",
            "data": {
                "audit_entries": audit_log,
                "total_entries": len(audit_log),
                "filters_applied": {
                    "purge_id": purge_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
        }
        
    except Exception as e:
        logger.error("Failed to get audit log", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get audit log"
        )

@router.get("/compliance/report")
async def generate_compliance_report(
    start_date: datetime = Query(..., description="Data inicial do relatório"),
    end_date: datetime = Query(..., description="Data final do relatório"),
    current_user = Depends(require_admin)
):
    """
    Gerar relatório de conformidade LGPD/GDPR.
    
    Gera relatório detalhado de todas as atividades de purga
    no período especificado, incluindo estatísticas e indicadores
    de conformidade.
    
    **Requer privilégios de administrador.**
    """
    try:
        logger.info(
            "Generating compliance report",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            user_id=current_user.get('user_id')
        )
        
        report = await data_purge_service.generate_compliance_report(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "status": "success",
            "data": report
        }
        
    except Exception as e:
        logger.error("Failed to generate compliance report", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate compliance report"
        )

@router.post("/pii/mask")
async def mask_pii_data(
    text: str = Body(..., description="Texto para mascarar PII"),
    preserve_format: bool = Body(True, description="Preservar formato original"),
    current_user = Depends(get_current_user)
):
    """
    Mascarar dados PII em texto.
    
    Identifica e mascara automaticamente dados pessoais sensíveis
    em texto, preservando o formato quando possível.
    
    **Tipos de PII detectados:**
    - Emails
    - CPF/CNPJ
    - Telefones
    - Cartões de crédito
    - Endereços IP
    - Documentos de identidade
    
    **Requer autenticação.**
    """
    try:
        masked_text, found_piis = pii_service.mask_text(text, preserve_format)
        
        return {
            "status": "success",
            "data": {
                "original_length": len(text),
                "masked_text": masked_text,
                "pii_found": found_piis,
                "pii_count": len(found_piis),
                "pii_types": list(set(pii['type'] for pii in found_piis))
            }
        }
        
    except Exception as e:
        logger.error("Failed to mask PII data", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to mask PII data"
        )

@router.post("/pii/analyze")
async def analyze_pii_data(
    text: str = Body(..., description="Texto para analisar"),
    current_user = Depends(get_current_user)
):
    """
    Analisar dados PII em texto.
    
    Analisa texto para identificar tipos e quantidade de dados
    pessoais sensíveis sem mascarar o conteúdo.
    
    **Requer autenticação.**
    """
    try:
        stats = pii_service.get_pii_statistics(text)
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error("Failed to analyze PII data", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze PII data"
        )

@router.get("/retention/policies")
async def get_retention_policies(
    current_user = Depends(get_current_user)
):
    """
    Obter políticas de retenção de dados.
    
    Lista as políticas de retenção configuradas para cada
    tipo de entidade no sistema.
    
    **Requer autenticação.**
    """
    try:
        policies = {}
        
        for entity_type in EntityType:
            retention_period = data_purge_service.retention_policy.get_retention_period(entity_type)
            policies[entity_type.value] = {
                "retention_days": retention_period.days,
                "retention_period_human": f"{retention_period.days} dias",
                "description": f"Dados de {entity_type.value} são mantidos por {retention_period.days} dias"
            }
        
        return {
            "status": "success",
            "data": {
                "policies": policies,
                "last_updated": datetime.utcnow().isoformat(),
                "compliance_frameworks": ["LGPD", "GDPR"]
            }
        }
        
    except Exception as e:
        logger.error("Failed to get retention policies", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get retention policies"
        )

@router.get("/health")
async def data_compliance_health_check():
    """
    Health check do sistema de conformidade de dados.
    
    Verifica se os serviços de purga de dados e mascaramento
    de PII estão funcionando corretamente.
    
    **Endpoint público para monitoramento.**
    """
    try:
        # Verificar serviços
        active_purges = len([p for p in data_purge_service.active_purges.values() 
                           if p.status.value == 'in_progress'])
        
        total_audit_entries = len(data_purge_service.audit_log)
        
        # Testar mascaramento PII
        test_text = "Teste com email test@example.com"
        masked_text, found_piis = pii_service.mask_text(test_text)
        pii_service_working = len(found_piis) > 0
        
        status = "healthy"
        if active_purges > data_purge_service.max_concurrent_purges:
            status = "degraded"
        
        return JSONResponse(
            status_code=200 if status == "healthy" else 503,
            content={
                "status": status,
                "service": "data-compliance",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    "active_purges": active_purges,
                    "max_concurrent_purges": data_purge_service.max_concurrent_purges,
                    "total_audit_entries": total_audit_entries,
                    "pii_service_working": pii_service_working,
                    "supported_pii_types": len(pii_service.patterns)
                }
            }
        )
        
    except Exception as e:
        logger.error("Data compliance health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "data-compliance",
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Service unavailable"
            }
        )