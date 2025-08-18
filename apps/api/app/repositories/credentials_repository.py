"""
Repository for user credentials data access
Camada de infraestrutura para acesso seguro aos dados de credenciais no Supabase
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.credentials import UserCredential, OAuthFlow, ProviderType, CredentialStatus

class CredentialsRepository:
    """Repository para acesso aos dados de credenciais no Supabase"""
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
    
    async def save_credential(self, credential: UserCredential) -> UserCredential:
        """Salvar credencial no banco de dados"""
        credential_data = {
            'id': str(credential.id),
            'user_id': str(credential.user_id),
            'provider': credential.provider.value,
            'credential_type': credential.credential_type.value,
            'name': credential.name,
            'encrypted_data': credential.encrypted_data,
            'encryption_key_id': credential.encryption_key_id,
            'metadata': credential.metadata,
            'expires_at': credential.expires_at.isoformat() if credential.expires_at else None,
            'scopes': credential.scopes,
            'status': credential.status.value,
            'last_validated_at': credential.last_validated_at.isoformat() if credential.last_validated_at else None,
            'validation_error': credential.validation_error,
            'fingerprint': credential.fingerprint,
            'updated_at': credential.updated_at.isoformat()
        }
        
        # Se é nova credencial, incluir created_at
        if not await self.credential_exists(credential.id):
            credential_data['created_at'] = credential.created_at.isoformat()
        
        # Upsert no Supabase
        if self.supabase:
            result = self.supabase.table('user_credentials').upsert(credential_data).execute()
            if result.data:
                return await self._map_credential_to_domain(result.data[0])
        
        return credential
    
    async def find_credential_by_id(self, credential_id: UUID, user_id: UUID) -> Optional[UserCredential]:
        """Buscar credencial por ID (com verificação de usuário)"""
        if not self.supabase:
            return None
        
        result = (
            self.supabase.table('user_credentials')
            .select('*')
            .eq('id', str(credential_id))
            .eq('user_id', str(user_id))
            .execute()
        )
        
        if result.data:
            return await self._map_credential_to_domain(result.data[0])
        return None
    
    async def find_credentials_by_user(
        self,
        user_id: UUID,
        provider: Optional[ProviderType] = None,
        status: Optional[CredentialStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserCredential]:
        """Buscar credenciais por usuário"""
        if not self.supabase:
            return []
        
        query = (
            self.supabase.table('user_credentials')
            .select('*')
            .eq('user_id', str(user_id))
        )
        
        if provider:
            query = query.eq('provider', provider.value)
        
        if status:
            query = query.eq('status', status.value)
        
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        credentials = []
        for row in result.data:
            credentials.append(await self._map_credential_to_domain(row))
        return credentials
    
    async def find_credential_by_name(self, user_id: UUID, name: str) -> Optional[UserCredential]:
        """Buscar credencial por nome (único por usuário)"""
        if not self.supabase:
            return None
        
        result = (
            self.supabase.table('user_credentials')
            .select('*')
            .eq('user_id', str(user_id))
            .eq('name', name)
            .limit(1)
            .execute()
        )
        
        if result.data:
            return await self._map_credential_to_domain(result.data[0])
        return None
    
    async def find_expiring_credentials(self, days_ahead: int = 7) -> List[UserCredential]:
        """Buscar credenciais que expiram em X dias"""
        if not self.supabase:
            return []
        
        # Calcular data limite
        from datetime import datetime, timedelta
        limit_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat()
        
        result = (
            self.supabase.table('user_credentials')
            .select('*')
            .not_.is_('expires_at', 'null')
            .lte('expires_at', limit_date)
            .eq('status', 'active')
            .execute()
        )
        
        credentials = []
        for row in result.data:
            credentials.append(await self._map_credential_to_domain(row))
        return credentials
    
    async def find_credentials_needing_validation(self, max_age_hours: int = 24) -> List[UserCredential]:
        """Buscar credenciais que precisam de validação"""
        if not self.supabase:
            return []
        
        from datetime import datetime, timedelta
        cutoff_date = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()
        
        # Credenciais que nunca foram validadas ou validadas há muito tempo
        result = (
            self.supabase.table('user_credentials')
            .select('*')
            .or_(
                f'last_validated_at.is.null,last_validated_at.lt.{cutoff_date},status.eq.pending_validation'
            )
            .in_('status', ['active', 'pending_validation'])
            .execute()
        )
        
        credentials = []
        for row in result.data:
            credentials.append(await self._map_credential_to_domain(row))
        return credentials
    
    async def delete_credential(self, credential_id: UUID, user_id: UUID) -> bool:
        """Deletar credencial (soft delete - marca como revogada)"""
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('user_credentials')
            .update({
                'status': 'revoked',
                'updated_at': datetime.utcnow().isoformat(),
                'metadata': {'revoked_at': datetime.utcnow().isoformat(), 'revocation_reason': 'user_deleted'}
            })
            .eq('id', str(credential_id))
            .eq('user_id', str(user_id))
            .execute()
        )
        
        return len(result.data) > 0
    
    async def credential_exists(self, credential_id: UUID) -> bool:
        """Verificar se credencial existe"""
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('user_credentials')
            .select('id')
            .eq('id', str(credential_id))
            .limit(1)
            .execute()
        )
        return len(result.data) > 0
    
    async def save_oauth_flow(self, oauth_flow: OAuthFlow) -> OAuthFlow:
        """Salvar fluxo OAuth"""
        flow_data = {
            'id': str(oauth_flow.id),
            'user_id': str(oauth_flow.user_id),
            'provider': oauth_flow.provider.value,
            'state': oauth_flow.state,
            'scopes': oauth_flow.scopes,
            'redirect_uri': oauth_flow.redirect_uri,
            'code_verifier': oauth_flow.code_verifier,
            'expires_at': oauth_flow.expires_at.isoformat(),
            'created_at': oauth_flow.created_at.isoformat()
        }
        
        if self.supabase:
            result = self.supabase.table('oauth_flows').upsert(flow_data).execute()
            if result.data:
                return await self._map_oauth_flow_to_domain(result.data[0])
        
        return oauth_flow
    
    async def find_oauth_flow_by_state(self, state: str) -> Optional[OAuthFlow]:
        """Buscar fluxo OAuth por state"""
        if not self.supabase:
            return None
        
        result = (
            self.supabase.table('oauth_flows')
            .select('*')
            .eq('state', state)
            .limit(1)
            .execute()
        )
        
        if result.data:
            return await self._map_oauth_flow_to_domain(result.data[0])
        return None
    
    async def delete_oauth_flow(self, flow_id: UUID) -> bool:
        """Deletar fluxo OAuth"""
        if not self.supabase:
            return False
        
        result = (
            self.supabase.table('oauth_flows')
            .delete()
            .eq('id', str(flow_id))
            .execute()
        )
        
        return len(result.data) > 0
    
    async def cleanup_expired_oauth_flows(self) -> int:
        """Limpar fluxos OAuth expirados"""
        if not self.supabase:
            return 0
        
        current_time = datetime.utcnow().isoformat()
        result = (
            self.supabase.table('oauth_flows')
            .delete()
            .lt('expires_at', current_time)
            .execute()
        )
        
        return len(result.data)
    
    async def get_credential_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Obter estatísticas de credenciais do usuário"""
        if not self.supabase:
            return {
                'total_credentials': 0,
                'active_credentials': 0,
                'expired_credentials': 0,
                'invalid_credentials': 0,
                'by_provider': {}
            }
        
        # Query para estatísticas básicas
        result = (
            self.supabase.table('user_credentials')
            .select('status, provider')
            .eq('user_id', str(user_id))
            .execute()
        )
        
        stats = {
            'total_credentials': len(result.data),
            'active_credentials': 0,
            'expired_credentials': 0,
            'invalid_credentials': 0,
            'by_provider': {}
        }
        
        for row in result.data:
            status = row['status']
            provider = row['provider']
            
            if status == 'active':
                stats['active_credentials'] += 1
            elif status == 'expired':
                stats['expired_credentials'] += 1
            elif status == 'invalid':
                stats['invalid_credentials'] += 1
            
            if provider not in stats['by_provider']:
                stats['by_provider'][provider] = 0
            stats['by_provider'][provider] += 1
        
        return stats
    
    async def _map_credential_to_domain(self, row: Dict[str, Any]) -> UserCredential:
        """Mapear linha do banco para domain object de credencial"""
        from app.domain.credentials import UserCredential, ProviderType, CredentialType, CredentialStatus
        
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
        
        last_validated_at = None
        if row.get('last_validated_at'):
            last_validated_at = datetime.fromisoformat(row['last_validated_at'].replace('Z', '+00:00'))
        
        return UserCredential(
            id=UUID(row['id']),
            user_id=UUID(row['user_id']),
            provider=ProviderType(row['provider']),
            credential_type=CredentialType(row['credential_type']),
            name=row['name'],
            encrypted_data=row['encrypted_data'],
            encryption_key_id=row['encryption_key_id'],
            metadata=row.get('metadata', {}),
            expires_at=expires_at,
            scopes=row.get('scopes', []),
            status=CredentialStatus(row.get('status', 'pending_validation')),
            created_at=created_at,
            updated_at=updated_at,
            last_validated_at=last_validated_at,
            validation_error=row.get('validation_error')
        )
    
    async def _map_oauth_flow_to_domain(self, row: Dict[str, Any]) -> OAuthFlow:
        """Mapear linha do banco para domain object de OAuth flow"""
        from app.domain.credentials import OAuthFlow, ProviderType
        
        expires_at = datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00'))
        created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        
        return OAuthFlow(
            id=UUID(row['id']),
            user_id=UUID(row['user_id']),
            provider=ProviderType(row['provider']),
            state=row['state'],
            scopes=row['scopes'],
            redirect_uri=row['redirect_uri'],
            code_verifier=row.get('code_verifier'),
            expires_at=expires_at,
            created_at=created_at
        )