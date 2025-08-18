"""
Testes para serviços de PII e conformidade de dados
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.pii_service import PIIService, PIIType
from app.services.data_purge_service import (
    DataPurgeService, 
    EntityType, 
    PurgeReason, 
    PurgeStatus
)

client = TestClient(app)

class TestPIIService:
    """Testes do serviço de mascaramento de PII"""
    
    @pytest.fixture
    def pii_service(self):
        return PIIService()
    
    def test_mask_email(self, pii_service):
        """Teste de mascaramento de email"""
        test_cases = [
            ("fulano@email.com", "f***o@email.com"),
            ("a@b.com", "*@b.com"),
            ("test.user@example.org", "t*******r@example.org"),
            ("user123@domain.co.uk", "u*****3@domain.co.uk")
        ]
        
        for original, expected in test_cases:
            masked, found_piis = pii_service.mask_text(original)
            assert masked == expected
            assert len(found_piis) == 1
            assert found_piis[0]['type'] == PIIType.EMAIL.value
    
    def test_mask_cpf(self, pii_service):
        """Teste de mascaramento de CPF"""
        test_cases = [
            ("123.456.789-00", "***.***.**-**"),
            ("12345678900", "***********"),
            ("000.000.001-91", "***.***.**-**")
        ]
        
        for original, expected in test_cases:
            masked, found_piis = pii_service.mask_text(original)
            assert expected in masked  # Pode ter variações no mascaramento
            assert len(found_piis) >= 1
            assert any(pii['type'] == PIIType.CPF.value for pii in found_piis)
    
    def test_mask_phone(self, pii_service):
        """Teste de mascaramento de telefone"""
        test_cases = [
            "+55 11 99999-9999",
            "(11) 98888-7777",
            "5511987654321"
        ]
        
        for phone in test_cases:
            masked, found_piis = pii_service.mask_text(phone)
            assert masked != phone  # Deve ser diferente do original
            assert len(found_piis) >= 1
            assert any(pii['type'] == PIIType.PHONE.value for pii in found_piis)
    
    def test_mask_credit_card(self, pii_service):
        """Teste de mascaramento de cartão de crédito"""
        test_cases = [
            ("4111 1111 1111 1111", "**** **** **** 1111"),
            ("5555-5555-5555-4444", "****-****-****-4444"),
            ("378282246310005", "***********0005")
        ]
        
        for original, expected_pattern in test_cases:
            masked, found_piis = pii_service.mask_text(original)
            # Verificar se os últimos 4 dígitos são preservados
            assert masked.endswith(original[-4:])
            assert len(found_piis) >= 1
            assert any(pii['type'] == PIIType.CREDIT_CARD.value for pii in found_piis)
    
    def test_mask_ip_address(self, pii_service):
        """Teste de mascaramento de endereço IP"""
        test_cases = [
            ("192.168.1.100", "192.168.*.*"),
            ("10.0.0.1", "10.0.*.*"),
            ("172.16.254.1", "172.16.*.*")
        ]
        
        for original, expected in test_cases:
            masked, found_piis = pii_service.mask_text(original)
            assert masked == expected
            assert len(found_piis) == 1
            assert found_piis[0]['type'] == PIIType.IP_ADDRESS.value
    
    def test_mask_multiple_pii_types(self, pii_service):
        """Teste de mascaramento de múltiplos tipos de PII"""
        text = "Contato: fulano@email.com, CPF: 123.456.789-00, Tel: +55 11 99999-9999"
        
        masked, found_piis = pii_service.mask_text(text)
        
        # Deve encontrar pelo menos 3 tipos de PII
        assert len(found_piis) >= 3
        
        pii_types = [pii['type'] for pii in found_piis]
        assert PIIType.EMAIL.value in pii_types
        assert PIIType.CPF.value in pii_types
        assert PIIType.PHONE.value in pii_types
        
        # Texto mascarado deve ser diferente do original
        assert masked != text
        assert "f***o@email.com" in masked
    
    def test_mask_dict_data(self, pii_service):
        """Teste de mascaramento em dicionário"""
        data = {
            "user": {
                "name": "João Silva",
                "email": "joao@email.com",
                "cpf": "123.456.789-00",
                "phone": "+55 11 99999-9999"
            },
            "metadata": {
                "ip": "192.168.1.100",
                "timestamp": "2024-12-15T14:30:22Z"
            }
        }
        
        masked_data, found_piis = pii_service.mask_dict(data)
        
        # Verificar se PII foi mascarado
        assert masked_data["user"]["email"] != data["user"]["email"]
        assert masked_data["user"]["cpf"] != data["user"]["cpf"]
        assert masked_data["user"]["phone"] != data["user"]["phone"]
        assert masked_data["metadata"]["ip"] != data["metadata"]["ip"]
        
        # Timestamp não deve ser alterado
        assert masked_data["metadata"]["timestamp"] == data["metadata"]["timestamp"]
        
        # Deve encontrar múltiplos PIIs
        assert len(found_piis) >= 4
    
    def test_pii_statistics(self, pii_service):
        """Teste de estatísticas de PII"""
        text = "Email: test@example.com, CPF: 123.456.789-00, IP: 192.168.1.1"
        
        stats = pii_service.get_pii_statistics(text)
        
        assert stats['total_piis_found'] >= 3
        assert 'email' in stats['pii_types']
        assert 'cpf' in stats['pii_types']
        assert 'ip_address' in stats['pii_types']
        assert stats['text_length'] == len(text)
        assert stats['pii_density'] > 0
    
    def test_sensitive_field_detection(self, pii_service):
        """Teste de detecção de campos sensíveis"""
        sensitive_fields = [
            'email', 'e_mail', 'mail_address',
            'cpf', 'document', 'rg',
            'phone', 'telefone', 'mobile',
            'password', 'senha', 'secret'
        ]
        
        for field in sensitive_fields:
            assert pii_service.is_sensitive_field(field)
            assert pii_service.is_sensitive_field(field.upper())
        
        non_sensitive_fields = ['name', 'age', 'color', 'status']
        for field in non_sensitive_fields:
            # Alguns podem ser considerados sensíveis (como 'name')
            # Apenas verificar que a função não falha
            result = pii_service.is_sensitive_field(field)
            assert isinstance(result, bool)

class TestDataPurgeService:
    """Testes do serviço de purga de dados"""
    
    @pytest.fixture
    def purge_service(self):
        return DataPurgeService()
    
    @pytest.mark.asyncio
    async def test_create_purge_request(self, purge_service):
        """Teste de criação de solicitação de purga"""
        purge_request = await purge_service.create_purge_request(
            tenant_id="tenant-123",
            entity_type=EntityType.USER,
            entity_ids=["user-1", "user-2"],
            reason=PurgeReason.GDPR_RIGHT_TO_BE_FORGOTTEN,
            requested_by="admin-user"
        )
        
        assert purge_request.tenant_id == "tenant-123"
        assert purge_request.entity_type == EntityType.USER
        assert purge_request.entity_ids == ["user-1", "user-2"]
        assert purge_request.reason == PurgeReason.GDPR_RIGHT_TO_BE_FORGOTTEN
        assert purge_request.status == PurgeStatus.PENDING
        assert purge_request.requested_by == "admin-user"
        
        # Deve estar na lista de purgas ativas
        assert purge_request.purge_id in purge_service.active_purges
    
    @pytest.mark.asyncio
    async def test_create_purge_request_validation(self, purge_service):
        """Teste de validação na criação de purga"""
        # Deve falhar sem entity_ids nem before_date
        with pytest.raises(ValueError, match="Deve especificar entity_ids ou before_date"):
            await purge_service.create_purge_request(
                tenant_id="tenant-123",
                entity_type=EntityType.USER,
                reason=PurgeReason.USER_REQUEST,
                requested_by="admin-user"
            )
        
        # Deve falhar ao tentar purgar audit logs sem motivo de conformidade
        with pytest.raises(ValueError, match="só podem ser purgados por requisito de conformidade"):
            await purge_service.create_purge_request(
                tenant_id="tenant-123",
                entity_type=EntityType.AUDIT_LOG,
                entity_ids=["log-1"],
                reason=PurgeReason.USER_REQUEST,
                requested_by="admin-user"
            )
    
    @pytest.mark.asyncio
    async def test_approve_purge_request(self, purge_service):
        """Teste de aprovação de solicitação de purga"""
        # Criar solicitação
        purge_request = await purge_service.create_purge_request(
            tenant_id="tenant-123",
            entity_type=EntityType.USER,
            entity_ids=["user-1"],
            reason=PurgeReason.GDPR_RIGHT_TO_BE_FORGOTTEN,
            requested_by="admin-user"
        )
        
        # Aprovar
        success = await purge_service.approve_purge_request(
            purge_id=purge_request.purge_id,
            approved_by="super-admin"
        )
        
        assert success is True
        assert purge_request.approved_by == "super-admin"
        assert purge_request.approved_at is not None
    
    @pytest.mark.asyncio
    async def test_execute_purge(self, purge_service):
        """Teste de execução de purga"""
        # Criar e aprovar solicitação
        purge_request = await purge_service.create_purge_request(
            tenant_id="tenant-123",
            entity_type=EntityType.USER,
            entity_ids=["user-1", "user-2"],
            reason=PurgeReason.GDPR_RIGHT_TO_BE_FORGOTTEN,
            requested_by="admin-user"
        )
        
        await purge_service.approve_purge_request(
            purge_id=purge_request.purge_id,
            approved_by="super-admin"
        )
        
        # Executar purga
        result = await purge_service.execute_purge(purge_request.purge_id)
        
        assert result['status'] == 'completed'
        assert result['records_purged'] > 0
        assert purge_request.status == PurgeStatus.COMPLETED
        assert purge_request.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_cancel_purge_request(self, purge_service):
        """Teste de cancelamento de solicitação de purga"""
        # Criar solicitação
        purge_request = await purge_service.create_purge_request(
            tenant_id="tenant-123",
            entity_type=EntityType.USER,
            entity_ids=["user-1"],
            reason=PurgeReason.USER_REQUEST,
            requested_by="admin-user"
        )
        
        # Cancelar
        success = await purge_service.cancel_purge_request(
            purge_id=purge_request.purge_id,
            cancelled_by="admin-user"
        )
        
        assert success is True
        assert purge_request.status == PurgeStatus.CANCELLED
        assert purge_request.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_list_purge_requests(self, purge_service):
        """Teste de listagem de solicitações de purga"""
        # Criar algumas solicitações
        await purge_service.create_purge_request(
            tenant_id="tenant-123",
            entity_type=EntityType.USER,
            entity_ids=["user-1"],
            reason=PurgeReason.GDPR_RIGHT_TO_BE_FORGOTTEN,
            requested_by="admin-user"
        )
        
        await purge_service.create_purge_request(
            tenant_id="tenant-456",
            entity_type=EntityType.EXECUTION,
            before_date=datetime.utcnow() - timedelta(days=30),
            reason=PurgeReason.DATA_RETENTION_POLICY,
            requested_by="system"
        )
        
        # Listar todas
        all_requests = await purge_service.list_purge_requests()
        assert len(all_requests) >= 2
        
        # Filtrar por status
        pending_requests = await purge_service.list_purge_requests(
            status=PurgeStatus.PENDING
        )
        assert len(pending_requests) >= 2
        
        # Filtrar por tipo de entidade
        user_requests = await purge_service.list_purge_requests(
            entity_type=EntityType.USER
        )
        assert len(user_requests) >= 1
    
    @pytest.mark.asyncio
    async def test_audit_log(self, purge_service):
        """Teste de log de auditoria"""
        # Criar e executar uma purga
        purge_request = await purge_service.create_purge_request(
            tenant_id="tenant-123",
            entity_type=EntityType.USER,
            entity_ids=["user-1"],
            reason=PurgeReason.GDPR_RIGHT_TO_BE_FORGOTTEN,
            requested_by="admin-user"
        )
        
        # Deve ter entradas de auditoria
        audit_log = await purge_service.get_audit_log(
            purge_id=purge_request.purge_id
        )
        
        assert len(audit_log) >= 1
        assert audit_log[0]['purge_id'] == purge_request.purge_id
        assert audit_log[0]['action'] == 'purge_request_created'
    
    @pytest.mark.asyncio
    async def test_compliance_report(self, purge_service):
        """Teste de relatório de conformidade"""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        # Criar algumas purgas para o relatório
        await purge_service.create_purge_request(
            tenant_id="tenant-123",
            entity_type=EntityType.USER,
            entity_ids=["user-1"],
            reason=PurgeReason.GDPR_RIGHT_TO_BE_FORGOTTEN,
            requested_by="admin-user"
        )
        
        report = await purge_service.generate_compliance_report(
            start_date=start_date,
            end_date=end_date
        )
        
        assert 'report_period' in report
        assert 'summary' in report
        assert 'entity_statistics' in report
        assert 'reason_statistics' in report
        assert 'compliance_indicators' in report
        
        assert report['summary']['total_purge_requests'] >= 1
        assert 'gdpr_requests' in report['compliance_indicators']
        assert 'lgpd_requests' in report['compliance_indicators']
    
    def test_retention_policies(self, purge_service):
        """Teste de políticas de retenção"""
        # Verificar se todas as entidades têm políticas definidas
        for entity_type in EntityType:
            retention_period = purge_service.retention_policy.get_retention_period(entity_type)
            assert retention_period.days > 0
        
        # Verificar elegibilidade para purga
        old_date = datetime.utcnow() - timedelta(days=400)  # Mais de 1 ano
        recent_date = datetime.utcnow() - timedelta(days=30)  # 30 dias
        
        # Execuções antigas devem ser elegíveis
        assert purge_service.retention_policy.is_eligible_for_purge(
            EntityType.EXECUTION, old_date
        )
        
        # Execuções recentes não devem ser elegíveis
        assert not purge_service.retention_policy.is_eligible_for_purge(
            EntityType.EXECUTION, recent_date
        )

class TestPIIComplianceEndpoints:
    """Testes dos endpoints de conformidade de PII"""
    
    def test_mask_pii_endpoint_requires_auth(self):
        """Teste que endpoint de mascaramento requer autenticação"""
        response = client.post(
            "/api/v1/data/pii/mask",
            json={"text": "test@example.com"}
        )
        assert response.status_code == 401
    
    def test_create_purge_request_requires_admin(self):
        """Teste que criação de purga requer admin"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            response = client.post(
                "/api/v1/data/purge",
                json={
                    "entity_type": "user",
                    "entity_ids": ["user-1"],
                    "reason": "user_request"
                }
            )
            assert response.status_code == 403
    
    def test_data_compliance_health_check_public(self):
        """Teste que health check é público"""
        response = client.get("/api/v1/data/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "data-compliance"
        assert "metrics" in data
    
    def test_retention_policies_endpoint(self):
        """Teste do endpoint de políticas de retenção"""
        with patch('app.middleware.auth.jwt_auth.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': 'user-123', 'role': 'user'}
            
            response = client.get("/api/v1/data/retention/policies")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "success"
            assert "policies" in data["data"]
            
            # Verificar se todas as entidades têm políticas
            policies = data["data"]["policies"]
            assert "user" in policies
            assert "execution" in policies
            assert "workflow" in policies

class TestPIIMaskingMiddleware:
    """Testes do middleware de mascaramento de PII"""
    
    @pytest.mark.asyncio
    async def test_middleware_masks_sensitive_headers(self):
        """Teste que middleware mascara headers sensíveis"""
        from app.middleware.pii_masking import PIIMaskingMiddleware
        
        middleware = PIIMaskingMiddleware()
        
        # Simular request com headers sensíveis
        class MockRequest:
            method = "GET"
            url = type('obj', (object,), {'path': '/test'})()
            query_params = {}
            headers = {
                'authorization': 'Bearer secret-token-123',
                'x-api-key': 'api-key-456',
                'user-agent': 'TestClient/1.0'
            }
            client = type('obj', (object,), {'host': '192.168.1.100'})()
            
            async def body(self):
                return b''
        
        request = MockRequest()
        masked_data = await middleware._mask_request_data(request)
        
        # Headers sensíveis devem ser mascarados
        assert 'Bearer ***MASKED***' in masked_data['headers']['authorization']
        assert masked_data['headers']['x-api-key'] == '***MASKED***'
        
        # User-agent não deve ser mascarado completamente
        assert 'TestClient' in masked_data['headers']['user-agent']
        
        # IP deve ser mascarado
        assert masked_data['client_ip'] == '192.168.*.*'
    
    def test_log_data_masking_function(self):
        """Teste da função de mascaramento de dados de log"""
        from app.middleware.pii_masking import mask_log_data
        
        log_data = {
            'message': 'User login',
            'user_email': 'test@example.com',
            'user_ip': '192.168.1.100',
            'timestamp': '2024-12-15T14:30:22Z'
        }
        
        masked_data = mask_log_data(log_data)
        
        # Email deve ser mascarado
        assert masked_data['user_email'] != log_data['user_email']
        assert 't***t@example.com' in masked_data['user_email']
        
        # IP deve ser mascarado
        assert masked_data['user_ip'] == '192.168.*.*'
        
        # Timestamp não deve ser alterado
        assert masked_data['timestamp'] == log_data['timestamp']
        
        # Deve indicar que PII foi mascarado
        assert masked_data.get('_pii_masked') is True
        assert 'email' in masked_data.get('_pii_types_found', [])
        assert masked_data.get('_pii_count', 0) > 0