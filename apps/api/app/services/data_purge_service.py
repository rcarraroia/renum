"""
Serviço de Purga de Dados para Conformidade LGPD/GDPR
Implementa purga segura de dados com auditoria completa
"""
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from uuid import uuid4, UUID
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

class EntityType(str, Enum):
    """Tipos de entidade para purga"""
    USER = "user"
    EXECUTION = "execution"
    WORKFLOW = "workflow"
    AGENT_LOG = "agent_log"
    WEBHOOK_LOG = "webhook_log"
    ANALYTICS_DATA = "analytics_data"
    AUDIT_LOG = "audit_log"
    CREDENTIAL = "credential"
    INTEGRATION = "integration"
    TEAM = "team"

class PurgeStatus(str, Enum):
    """Status da operação de purga"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PurgeReason(str, Enum):
    """Motivos para purga de dados"""
    USER_REQUEST = "user_request"
    GDPR_RIGHT_TO_BE_FORGOTTEN = "gdpr_right_to_be_forgotten"
    LGPD_DATA_DELETION = "lgpd_data_deletion"
    DATA_RETENTION_POLICY = "data_retention_policy"
    COMPLIANCE_REQUIREMENT = "compliance_requirement"
    SECURITY_INCIDENT = "security_incident"
    ADMINISTRATIVE = "administrative"

@dataclass
class PurgeRequest:
    """Solicitação de purga de dados"""
    purge_id: str
    tenant_id: Optional[str]
    entity_type: EntityType
    entity_ids: List[str]
    before_date: Optional[datetime]
    reason: PurgeReason
    requested_by: str
    requested_at: datetime
    status: PurgeStatus
    metadata: Dict[str, Any]
    
    # Campos de auditoria
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Resultados
    records_identified: int = 0
    records_purged: int = 0
    records_failed: int = 0
    tables_affected: List[str] = None
    
    def __post_init__(self):
        if self.tables_affected is None:
            self.tables_affected = []

@dataclass
class PurgeAuditEntry:
    """Entrada de auditoria imutável para purga"""
    audit_id: str
    purge_id: str
    timestamp: datetime
    action: str
    entity_type: EntityType
    entity_id: str
    table_name: str
    record_count: int
    checksum: str
    performed_by: str
    metadata: Dict[str, Any]

class DataRetentionPolicy:
    """Política de retenção de dados"""
    
    def __init__(self):
        self.policies = {
            EntityType.USER: timedelta(days=2555),  # 7 anos (LGPD)
            EntityType.EXECUTION: timedelta(days=365),  # 1 ano
            EntityType.WORKFLOW: timedelta(days=1095),  # 3 anos
            EntityType.AGENT_LOG: timedelta(days=90),   # 3 meses
            EntityType.WEBHOOK_LOG: timedelta(days=180), # 6 meses
            EntityType.ANALYTICS_DATA: timedelta(days=730), # 2 anos
            EntityType.AUDIT_LOG: timedelta(days=2555),  # 7 anos (nunca purgar)
            EntityType.CREDENTIAL: timedelta(days=365),  # 1 ano após inatividade
            EntityType.INTEGRATION: timedelta(days=1095), # 3 anos
            EntityType.TEAM: timedelta(days=1095)  # 3 anos
        }
    
    def get_retention_period(self, entity_type: EntityType) -> timedelta:
        """Obter período de retenção para tipo de entidade"""
        return self.policies.get(entity_type, timedelta(days=365))
    
    def is_eligible_for_purge(self, entity_type: EntityType, created_at: datetime) -> bool:
        """Verificar se entidade é elegível para purga"""
        retention_period = self.get_retention_period(entity_type)
        cutoff_date = datetime.utcnow() - retention_period
        return created_at < cutoff_date

class DataPurgeService:
    """Serviço de purga de dados com conformidade LGPD/GDPR"""
    
    def __init__(self):
        self.retention_policy = DataRetentionPolicy()
        self.active_purges: Dict[str, PurgeRequest] = {}
        self.audit_log: List[PurgeAuditEntry] = []
        
        # Configurações
        self.max_concurrent_purges = settings.MAX_CONCURRENT_PURGES or 3
        self.purge_batch_size = settings.PURGE_BATCH_SIZE or 1000
        self.require_approval = settings.PURGE_REQUIRE_APPROVAL or True
    
    async def create_purge_request(
        self,
        tenant_id: Optional[str],
        entity_type: EntityType,
        entity_ids: Optional[List[str]] = None,
        before_date: Optional[datetime] = None,
        reason: PurgeReason = PurgeReason.USER_REQUEST,
        requested_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> PurgeRequest:
        """
        Criar solicitação de purga de dados
        
        Args:
            tenant_id: ID do tenant (opcional para purga global)
            entity_type: Tipo de entidade para purgar
            entity_ids: IDs específicos ou None para purga por data
            before_date: Purgar registros antes desta data
            reason: Motivo da purga
            requested_by: Usuário que solicitou
            metadata: Metadados adicionais
            
        Returns:
            Solicitação de purga criada
        """
        try:
            purge_id = str(uuid4())
            
            # Validações
            if not entity_ids and not before_date:
                raise ValueError("Deve especificar entity_ids ou before_date")
            
            if entity_type == EntityType.AUDIT_LOG and reason != PurgeReason.COMPLIANCE_REQUIREMENT:
                raise ValueError("Logs de auditoria só podem ser purgados por requisito de conformidade")
            
            purge_request = PurgeRequest(
                purge_id=purge_id,
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_ids=entity_ids or [],
                before_date=before_date,
                reason=reason,
                requested_by=requested_by,
                requested_at=datetime.utcnow(),
                status=PurgeStatus.PENDING,
                metadata=metadata or {}
            )
            
            # Adicionar à lista de purgas ativas
            self.active_purges[purge_id] = purge_request
            
            logger.info(
                "Purge request created",
                purge_id=purge_id,
                entity_type=entity_type.value,
                tenant_id=tenant_id,
                reason=reason.value,
                requested_by=requested_by
            )
            
            # Registrar na auditoria
            await self._audit_action(
                purge_id=purge_id,
                action="purge_request_created",
                entity_type=entity_type,
                entity_id="",
                table_name="",
                record_count=0,
                performed_by=requested_by,
                metadata={"reason": reason.value}
            )
            
            return purge_request
            
        except Exception as e:
            logger.error("Failed to create purge request", error=str(e))
            raise
    
    async def approve_purge_request(self, purge_id: str, approved_by: str) -> bool:
        """
        Aprovar solicitação de purga
        
        Args:
            purge_id: ID da solicitação de purga
            approved_by: Usuário que aprovou
            
        Returns:
            True se aprovado com sucesso
        """
        try:
            if purge_id not in self.active_purges:
                raise ValueError(f"Purge request {purge_id} not found")
            
            purge_request = self.active_purges[purge_id]
            
            if purge_request.status != PurgeStatus.PENDING:
                raise ValueError(f"Purge request {purge_id} is not pending approval")
            
            purge_request.approved_by = approved_by
            purge_request.approved_at = datetime.utcnow()
            
            logger.info(
                "Purge request approved",
                purge_id=purge_id,
                approved_by=approved_by
            )
            
            # Registrar aprovação na auditoria
            await self._audit_action(
                purge_id=purge_id,
                action="purge_request_approved",
                entity_type=purge_request.entity_type,
                entity_id="",
                table_name="",
                record_count=0,
                performed_by=approved_by,
                metadata={"approved_at": purge_request.approved_at.isoformat()}
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to approve purge request", purge_id=purge_id, error=str(e))
            raise
    
    async def execute_purge(self, purge_id: str) -> Dict[str, Any]:
        """
        Executar purga de dados
        
        Args:
            purge_id: ID da solicitação de purga
            
        Returns:
            Resultado da execução
        """
        try:
            if purge_id not in self.active_purges:
                raise ValueError(f"Purge request {purge_id} not found")
            
            purge_request = self.active_purges[purge_id]
            
            # Verificar se requer aprovação
            if self.require_approval and not purge_request.approved_by:
                raise ValueError(f"Purge request {purge_id} requires approval")
            
            # Verificar se já está em execução
            if purge_request.status == PurgeStatus.IN_PROGRESS:
                raise ValueError(f"Purge request {purge_id} is already in progress")
            
            # Verificar limite de purgas concorrentes
            active_count = sum(1 for p in self.active_purges.values() 
                             if p.status == PurgeStatus.IN_PROGRESS)
            
            if active_count >= self.max_concurrent_purges:
                raise ValueError("Maximum concurrent purges reached")
            
            # Iniciar execução
            purge_request.status = PurgeStatus.IN_PROGRESS
            purge_request.started_at = datetime.utcnow()
            
            logger.info(
                "Starting purge execution",
                purge_id=purge_id,
                entity_type=purge_request.entity_type.value
            )
            
            # Executar purga baseada no tipo de entidade
            result = await self._execute_purge_by_type(purge_request)
            
            # Atualizar status
            purge_request.status = PurgeStatus.COMPLETED
            purge_request.completed_at = datetime.utcnow()
            purge_request.records_identified = result.get('records_identified', 0)
            purge_request.records_purged = result.get('records_purged', 0)
            purge_request.records_failed = result.get('records_failed', 0)
            purge_request.tables_affected = result.get('tables_affected', [])
            
            logger.info(
                "Purge execution completed",
                purge_id=purge_id,
                records_purged=purge_request.records_purged,
                records_failed=purge_request.records_failed
            )
            
            # Registrar conclusão na auditoria
            await self._audit_action(
                purge_id=purge_id,
                action="purge_execution_completed",
                entity_type=purge_request.entity_type,
                entity_id="",
                table_name="",
                record_count=purge_request.records_purged,
                performed_by=purge_request.requested_by,
                metadata={
                    "records_identified": purge_request.records_identified,
                    "records_purged": purge_request.records_purged,
                    "records_failed": purge_request.records_failed,
                    "tables_affected": purge_request.tables_affected
                }
            )
            
            return {
                "purge_id": purge_id,
                "status": "completed",
                "records_identified": purge_request.records_identified,
                "records_purged": purge_request.records_purged,
                "records_failed": purge_request.records_failed,
                "tables_affected": purge_request.tables_affected,
                "execution_time_seconds": (
                    purge_request.completed_at - purge_request.started_at
                ).total_seconds()
            }
            
        except Exception as e:
            # Marcar como falhou
            if purge_id in self.active_purges:
                purge_request = self.active_purges[purge_id]
                purge_request.status = PurgeStatus.FAILED
                purge_request.error_message = str(e)
                purge_request.completed_at = datetime.utcnow()
            
            logger.error("Purge execution failed", purge_id=purge_id, error=str(e))
            
            # Registrar falha na auditoria
            await self._audit_action(
                purge_id=purge_id,
                action="purge_execution_failed",
                entity_type=purge_request.entity_type if purge_id in self.active_purges else EntityType.USER,
                entity_id="",
                table_name="",
                record_count=0,
                performed_by=purge_request.requested_by if purge_id in self.active_purges else "system",
                metadata={"error": str(e)}
            )
            
            raise
    
    async def get_purge_status(self, purge_id: str) -> Dict[str, Any]:
        """Obter status de uma purga"""
        if purge_id not in self.active_purges:
            raise ValueError(f"Purge request {purge_id} not found")
        
        purge_request = self.active_purges[purge_id]
        
        return {
            "purge_id": purge_id,
            "status": purge_request.status.value,
            "entity_type": purge_request.entity_type.value,
            "reason": purge_request.reason.value,
            "requested_by": purge_request.requested_by,
            "requested_at": purge_request.requested_at.isoformat(),
            "approved_by": purge_request.approved_by,
            "approved_at": purge_request.approved_at.isoformat() if purge_request.approved_at else None,
            "started_at": purge_request.started_at.isoformat() if purge_request.started_at else None,
            "completed_at": purge_request.completed_at.isoformat() if purge_request.completed_at else None,
            "records_identified": purge_request.records_identified,
            "records_purged": purge_request.records_purged,
            "records_failed": purge_request.records_failed,
            "tables_affected": purge_request.tables_affected,
            "error_message": purge_request.error_message
        }
    
    async def list_purge_requests(
        self,
        status: Optional[PurgeStatus] = None,
        entity_type: Optional[EntityType] = None,
        requested_by: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Listar solicitações de purga"""
        requests = list(self.active_purges.values())
        
        # Filtros
        if status:
            requests = [r for r in requests if r.status == status]
        
        if entity_type:
            requests = [r for r in requests if r.entity_type == entity_type]
        
        if requested_by:
            requests = [r for r in requests if r.requested_by == requested_by]
        
        # Ordenar por data de solicitação (mais recente primeiro)
        requests.sort(key=lambda x: x.requested_at, reverse=True)
        
        # Limitar resultados
        requests = requests[:limit]
        
        return [await self.get_purge_status(r.purge_id) for r in requests]
    
    async def cancel_purge_request(self, purge_id: str, cancelled_by: str) -> bool:
        """Cancelar solicitação de purga"""
        if purge_id not in self.active_purges:
            raise ValueError(f"Purge request {purge_id} not found")
        
        purge_request = self.active_purges[purge_id]
        
        if purge_request.status not in [PurgeStatus.PENDING, PurgeStatus.IN_PROGRESS]:
            raise ValueError(f"Cannot cancel purge request {purge_id} with status {purge_request.status}")
        
        purge_request.status = PurgeStatus.CANCELLED
        purge_request.completed_at = datetime.utcnow()
        
        logger.info(
            "Purge request cancelled",
            purge_id=purge_id,
            cancelled_by=cancelled_by
        )
        
        # Registrar cancelamento na auditoria
        await self._audit_action(
            purge_id=purge_id,
            action="purge_request_cancelled",
            entity_type=purge_request.entity_type,
            entity_id="",
            table_name="",
            record_count=0,
            performed_by=cancelled_by,
            metadata={"cancelled_at": purge_request.completed_at.isoformat()}
        )
        
        return True
    
    async def get_audit_log(
        self,
        purge_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Obter log de auditoria de purgas"""
        audit_entries = self.audit_log.copy()
        
        # Filtros
        if purge_id:
            audit_entries = [e for e in audit_entries if e.purge_id == purge_id]
        
        if start_date:
            audit_entries = [e for e in audit_entries if e.timestamp >= start_date]
        
        if end_date:
            audit_entries = [e for e in audit_entries if e.timestamp <= end_date]
        
        # Ordenar por timestamp (mais recente primeiro)
        audit_entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Limitar resultados
        audit_entries = audit_entries[:limit]
        
        return [asdict(entry) for entry in audit_entries]
    
    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Gerar relatório de conformidade LGPD/GDPR"""
        try:
            # Filtrar purgas no período
            period_purges = [
                p for p in self.active_purges.values()
                if start_date <= p.requested_at <= end_date
            ]
            
            # Estatísticas por tipo de entidade
            entity_stats = {}
            for purge in period_purges:
                entity_type = purge.entity_type.value
                if entity_type not in entity_stats:
                    entity_stats[entity_type] = {
                        'total_requests': 0,
                        'completed_requests': 0,
                        'records_purged': 0,
                        'failed_requests': 0
                    }
                
                entity_stats[entity_type]['total_requests'] += 1
                
                if purge.status == PurgeStatus.COMPLETED:
                    entity_stats[entity_type]['completed_requests'] += 1
                    entity_stats[entity_type]['records_purged'] += purge.records_purged
                elif purge.status == PurgeStatus.FAILED:
                    entity_stats[entity_type]['failed_requests'] += 1
            
            # Estatísticas por motivo
            reason_stats = {}
            for purge in period_purges:
                reason = purge.reason.value
                reason_stats[reason] = reason_stats.get(reason, 0) + 1
            
            # Tempo médio de processamento
            completed_purges = [p for p in period_purges if p.status == PurgeStatus.COMPLETED]
            avg_processing_time = 0
            
            if completed_purges:
                total_time = sum(
                    (p.completed_at - p.started_at).total_seconds()
                    for p in completed_purges
                    if p.started_at and p.completed_at
                )
                avg_processing_time = total_time / len(completed_purges)
            
            report = {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "summary": {
                    "total_purge_requests": len(period_purges),
                    "completed_purges": len([p for p in period_purges if p.status == PurgeStatus.COMPLETED]),
                    "failed_purges": len([p for p in period_purges if p.status == PurgeStatus.FAILED]),
                    "pending_purges": len([p for p in period_purges if p.status == PurgeStatus.PENDING]),
                    "total_records_purged": sum(p.records_purged for p in period_purges),
                    "avg_processing_time_seconds": avg_processing_time
                },
                "entity_statistics": entity_stats,
                "reason_statistics": reason_stats,
                "compliance_indicators": {
                    "gdpr_requests": len([p for p in period_purges if p.reason == PurgeReason.GDPR_RIGHT_TO_BE_FORGOTTEN]),
                    "lgpd_requests": len([p for p in period_purges if p.reason == PurgeReason.LGPD_DATA_DELETION]),
                    "retention_policy_purges": len([p for p in period_purges if p.reason == PurgeReason.DATA_RETENTION_POLICY]),
                    "success_rate": (len(completed_purges) / len(period_purges) * 100) if period_purges else 0
                },
                "audit_trail_entries": len([e for e in self.audit_log if start_date <= e.timestamp <= end_date]),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error("Failed to generate compliance report", error=str(e))
            raise
    
    # Métodos privados
    
    async def _execute_purge_by_type(self, purge_request: PurgeRequest) -> Dict[str, Any]:
        """Executar purga baseada no tipo de entidade"""
        entity_type = purge_request.entity_type
        
        # Mapear tipos de entidade para tabelas
        table_mapping = {
            EntityType.USER: ['users', 'user_profiles', 'user_preferences'],
            EntityType.EXECUTION: ['executions', 'execution_logs', 'execution_results'],
            EntityType.WORKFLOW: ['workflows', 'workflow_steps', 'workflow_history'],
            EntityType.AGENT_LOG: ['agent_logs', 'agent_execution_logs'],
            EntityType.WEBHOOK_LOG: ['webhook_logs', 'webhook_events'],
            EntityType.ANALYTICS_DATA: ['analytics_events', 'metrics_data'],
            EntityType.AUDIT_LOG: ['audit_logs'],
            EntityType.CREDENTIAL: ['credentials', 'encrypted_credentials'],
            EntityType.INTEGRATION: ['integrations', 'integration_configs'],
            EntityType.TEAM: ['teams', 'team_members', 'team_permissions']
        }
        
        tables = table_mapping.get(entity_type, [])
        
        # Simular purga (em implementação real, executaria queries SQL)
        records_identified = 0
        records_purged = 0
        records_failed = 0
        
        for table in tables:
            try:
                # Simular identificação de registros
                if purge_request.entity_ids:
                    # Purga por IDs específicos
                    table_records = len(purge_request.entity_ids)
                else:
                    # Purga por data
                    table_records = 100  # Simulado
                
                records_identified += table_records
                
                # Simular purga em lotes
                batch_size = self.purge_batch_size
                for i in range(0, table_records, batch_size):
                    batch_end = min(i + batch_size, table_records)
                    batch_count = batch_end - i
                    
                    # Simular purga do lote
                    await asyncio.sleep(0.01)  # Simular tempo de processamento
                    
                    records_purged += batch_count
                    
                    # Registrar na auditoria
                    await self._audit_action(
                        purge_id=purge_request.purge_id,
                        action="records_purged",
                        entity_type=entity_type,
                        entity_id="",
                        table_name=table,
                        record_count=batch_count,
                        performed_by=purge_request.requested_by,
                        metadata={"batch_start": i, "batch_end": batch_end}
                    )
                
            except Exception as e:
                logger.error(f"Failed to purge from table {table}", error=str(e))
                records_failed += 1
        
        return {
            "records_identified": records_identified,
            "records_purged": records_purged,
            "records_failed": records_failed,
            "tables_affected": tables
        }
    
    async def _audit_action(
        self,
        purge_id: str,
        action: str,
        entity_type: EntityType,
        entity_id: str,
        table_name: str,
        record_count: int,
        performed_by: str,
        metadata: Dict[str, Any]
    ):
        """Registrar ação na auditoria imutável"""
        import hashlib
        
        audit_entry = PurgeAuditEntry(
            audit_id=str(uuid4()),
            purge_id=purge_id,
            timestamp=datetime.utcnow(),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            table_name=table_name,
            record_count=record_count,
            checksum="",  # Será calculado
            performed_by=performed_by,
            metadata=metadata
        )
        
        # Calcular checksum para integridade
        data_to_hash = f"{audit_entry.audit_id}{audit_entry.purge_id}{audit_entry.timestamp}{action}{entity_type.value}{entity_id}{table_name}{record_count}{performed_by}"
        audit_entry.checksum = hashlib.sha256(data_to_hash.encode()).hexdigest()
        
        # Adicionar ao log de auditoria
        self.audit_log.append(audit_entry)
        
        logger.debug(
            "Audit entry created",
            audit_id=audit_entry.audit_id,
            purge_id=purge_id,
            action=action
        )

# Instância global do serviço
data_purge_service = DataPurgeService()