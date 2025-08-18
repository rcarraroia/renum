"""
Repository for integration/connection data access
Camada de infraestrutura para acesso aos dados de conexões BYOC no Supabase
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.integration import Connection, IntegrationAnalytics


class IntegrationRepository:
    """Repository para acesso aos dados de conexões no Supabase"""
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
    
    async def save_connection(self, connection: Connection) -> Connection:
        """Salvar conexão no banco de dados"""
        
        # Converter domain object para formato do banco
        connection_data = {
            'id': str(connection.id),
            'tenant_id': str(connection.tenant_id),
            'service_name': connection.service_name,
            'connection_type': connection.connection_type,
            'credentials': connection.credentials,  # Será criptografado pelo Supabase
            'scopes': connection.scopes,
            'status': connection.status,
            'expires_at': connection.expires_at.isoformat() if connection.expires_at else None,
            'last_validated': connection.last_validated.isoformat() if connection.last_validated else None,
            'updated_at': connection.updated_at.isoformat()
        }
        
        # Se é nova conexão, incluir created_at
        if not await self.connection_exists(connection.id):
            connection_data['created_at'] = connection.created_at.isoformat()
        
        # Upsert no Supabase
        if self.supabase:
            result = self.supabase.table('tenant_connections').upsert(connection_data).execute()
            if result.data:
                return await self._map_connection_to_domain(result.data[0])
        
        return connection
    
    async def find_connection_by_id(self, connection_id: UUID) -> Optional[Connection]:
        """Buscar conexão por ID"""
        
        if not self.supabase:
            return None
        
        result = (
            self.supabase.table('tenant_connections')
            .select('*')
            .eq('id', str(connection_id))
            .execute()
        )
        
        if result.data:
            return await self._map_connection_to_domain(result.data[0])
        
        return None
    
    async def find_connections_by_tenant(
        self, 
        tenant_id: UUID,
        connection_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Connection]:
        """Buscar conexões por tenant"""
        
        if not self.supabase:
            return []
        
        query = (
            self.supabase.table('tenant_connections')
            .select('*')
            .eq('tenant_id', str(tenant_id))
        )
        
        # Aplicar filtros
        if connection_type:
            query = query.eq('connection_type', connection_type)
        
        if status:
            query = query.eq('status', status)
        
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        connections = []
        for row in result.data:
            connections.append(await self._map_connection_to_domain(row))
        
        return connections
    
    async def find_connections_by_service(
        self, 
        tenant_id: UUID,
        service_name: str
    ) -> List[Connection]:
        """Buscar conexões por nome do serviço"""
        
        if not self.supabase:
            return []
        
        result = (
            self.supabase.table('tenant_connections')
            .select('*')
            .eq('tenant_id', str(tenant_id))
            .eq('service_name', service_name)
            .order('created_at', desc=True)
            .execute()
        )
        
        connections = []
        for row in result.data:
            connections.append(await self._map_connection_to_domain(row))
        
        return connections
    
    async def find_expired_connections(self) -> List[Connection]:
        """Buscar conexões expiradas"""
        
        if not self.supabase:
            return []
        
        now = datetime.utcnow().isoformat()
        
        result = (
            self.supabase.table('tenant_connections')
            .select('*')
            .lt('expires_at', now)
            .neq('status', 'expired')
            .execute()
        )
        
        connections = []
        for row in result.data:
            connections.append(await self._map_connection_to_domain(row))
        
        return connections
    
    async def find_connections_needing_validation(
        self, 
        hours_threshold: int = 24
    ) -> List[Connection]:
        """Buscar conexões que precisam de validação"""
        
        if not self.supabase:
            return []
        
        threshold = datetime.utcnow().replace(hour=datetime.utcnow().hour - hours_threshold)
        threshold_iso = threshold.isoformat()
        
        result = (
            self.supabase.table('tenant_connections')
            .select('*')
            .eq('status', 'active')
            .or_(f'last_validated.is.null,last_validated.lt.{threshold_iso}')
            .execute()
        )
        
        connections = []
        for row in result.data:
            connections.append(await self._map_connection_to_domain(row))
        
        return connections
    
    async def delete_connection(self, connection_id: UUID) -> bool:
        """Deletar conexão"""
        
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('tenant_connections')
            .delete()
            .eq('id', str(connection_id))
            .execute()
        )
        
        return len(result.data) > 0
    
    async def connection_exists(self, connection_id: UUID) -> bool:
        """Verificar se conexão existe"""
        
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('tenant_connections')
            .select('id')
            .eq('id', str(connection_id))
            .limit(1)
            .execute()
        )
        
        return len(result.data) > 0
    
    async def count_connections_by_tenant(
        self, 
        tenant_id: UUID,
        status: Optional[str] = None
    ) -> int:
        """Contar conexões por tenant"""
        
        if not self.supabase:
            return 0
        
        query = (
            self.supabase.table('tenant_connections')
            .select('id', count='exact')
            .eq('tenant_id', str(tenant_id))
        )
        
        if status:
            query = query.eq('status', status)
        
        result = query.execute()
        
        return result.count or 0
    
    async def get_connection_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """Obter estatísticas de conexões do tenant"""
        
        # Esta seria uma query mais complexa no Supabase
        # Por enquanto, implementação mock
        return {
            'total_connections': await self.count_connections_by_tenant(tenant_id),
            'active_connections': await self.count_connections_by_tenant(tenant_id, 'active'),
            'expired_connections': await self.count_connections_by_tenant(tenant_id, 'expired'),
            'error_connections': await self.count_connections_by_tenant(tenant_id, 'error'),
            'by_type': {
                'oauth': 5,
                'api_key': 3,
                'database': 2,
                'webhook': 4
            }
        }
    
    async def _map_connection_to_domain(self, row: Dict[str, Any]) -> Connection:
        """Mapear linha do banco para domain object"""
        
        # Converter datas
        created_at = None
        if row.get('created_at'):
            created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        
        updated_at = None
        if row.get('updated_at'):
            updated_at = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
        
        expires_at = None
        if row.get('expires_at'):
            expires_at = datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00'))
        
        last_validated = None
        if row.get('last_validated'):
            last_validated = datetime.fromisoformat(row['last_validated'].replace('Z', '+00:00'))
        
        return Connection(
            id=UUID(row['id']),
            tenant_id=UUID(row['tenant_id']),
            service_name=row['service_name'],
            connection_type=row['connection_type'],
            credentials=row['credentials'],
            scopes=row.get('scopes', []),
            status=row.get('status', 'active'),
            expires_at=expires_at,
            last_validated=last_validated,
            created_at=created_at,
            updated_at=updated_at
        )
    
    # Analytics methods
    
    async def save_analytics(self, analytics: IntegrationAnalytics) -> IntegrationAnalytics:
        """Salvar analytics de integração"""
        
        # Esta seria implementada com uma tabela específica de analytics
        # Por enquanto, retorna o objeto
        return analytics
    
    async def get_analytics(
        self, 
        connection_id: UUID,
        days: int = 30
    ) -> List[IntegrationAnalytics]:
        """Obter analytics de uma conexão"""
        
        # Implementação mock
        return []
    
    async def update_analytics(
        self,
        connection_id: UUID,
        success: bool,
        response_time_ms: int,
        cost: float = 0.0
    ):
        """Atualizar analytics com nova requisição"""
        
        # Esta seria uma implementação mais complexa
        # Por enquanto, apenas log
        print(f"Analytics updated for {connection_id}: success={success}, time={response_time_ms}ms")