"""
Repositório para gerenciamento de integrações.
"""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.integration import Integration, IntegrationChannel, IntegrationStatus, WebhookCall
from app.schemas.integration import IntegrationCreate, IntegrationUpdate
from app.core.supabase_client import get_supabase_client


class IntegrationRepository:
    """Repositório para operações de integração."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def _generate_webhook_token(self) -> str:
        """Gera um token único para webhook."""
        return f"whk_{secrets.token_urlsafe(32)}"
    
    async def create_integration(self, user_id: UUID, data: IntegrationCreate) -> Integration:
        """Cria uma nova integração."""
        webhook_token = self._generate_webhook_token()
        
        integration_data = {
            "user_id": str(user_id),
            "agent_id": str(data.agent_id),
            "name": data.name,
            "description": data.description,
            "channel": data.channel.value,
            "status": IntegrationStatus.ACTIVE.value,
            "webhook_token": webhook_token,
            "rate_limit_per_minute": data.rate_limit_per_minute,
            "metadata": data.metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table("integrations").insert(integration_data).execute()
        
        if not result.data:
            raise Exception("Failed to create integration")
        
        integration_dict = result.data[0]
        
        # Gerar webhook_url
        base_url = "https://api.renum.com"  # TODO: Pegar da configuração
        webhook_url = f"{base_url}/webhook/{data.agent_id}/{data.channel.value}"
        
        # Atualizar com webhook_url
        self.supabase.table("integrations").update({
            "webhook_url": webhook_url
        }).eq("id", integration_dict["id"]).execute()
        
        integration_dict["webhook_url"] = webhook_url
        
        return Integration(**integration_dict)
    
    async def get_integration(self, integration_id: UUID, user_id: UUID) -> Optional[Integration]:
        """Busca uma integração por ID."""
        result = self.supabase.table("integrations").select("*").eq(
            "id", str(integration_id)
        ).eq("user_id", str(user_id)).execute()
        
        if not result.data:
            return None
        
        return Integration(**result.data[0])
    
    async def get_integration_by_token(self, token: str) -> Optional[Integration]:
        """Busca uma integração pelo token."""
        result = self.supabase.table("integrations").select("*").eq(
            "webhook_token", token
        ).execute()
        
        if not result.data:
            return None
        
        return Integration(**result.data[0])
    
    async def list_integrations(
        self,
        user_id: UUID,
        agent_id: Optional[UUID] = None,
        channel: Optional[IntegrationChannel] = None,
        status: Optional[IntegrationStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Integration]:
        """Lista integrações com filtros."""
        query = self.supabase.table("integrations").select("*").eq("user_id", str(user_id))
        
        if agent_id:
            query = query.eq("agent_id", str(agent_id))
        
        if channel:
            query = query.eq("channel", channel.value)
        
        if status:
            query = query.eq("status", status.value)
        
        result = query.range(offset, offset + limit - 1).order("created_at", desc=True).execute()
        
        return [Integration(**item) for item in result.data]
    
    async def count_integrations(
        self,
        user_id: UUID,
        agent_id: Optional[UUID] = None,
        channel: Optional[IntegrationChannel] = None,
        status: Optional[IntegrationStatus] = None
    ) -> int:
        """Conta integrações com filtros."""
        query = self.supabase.table("integrations").select("id", count="exact").eq("user_id", str(user_id))
        
        if agent_id:
            query = query.eq("agent_id", str(agent_id))
        
        if channel:
            query = query.eq("channel", channel.value)
        
        if status:
            query = query.eq("status", status.value)
        
        result = query.execute()
        return result.count or 0
    
    async def update_integration(
        self, 
        integration_id: UUID, 
        user_id: UUID, 
        data: IntegrationUpdate
    ) -> Optional[Integration]:
        """Atualiza uma integração."""
        update_data = data.dict(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.supabase.table("integrations").update(update_data).eq(
                "id", str(integration_id)
            ).eq("user_id", str(user_id)).execute()
            
            if not result.data:
                return None
            
            return Integration(**result.data[0])
        
        return await self.get_integration(integration_id, user_id)
    
    async def delete_integration(self, integration_id: UUID, user_id: UUID) -> bool:
        """Deleta uma integração."""
        result = self.supabase.table("integrations").delete().eq(
            "id", str(integration_id)
        ).eq("user_id", str(user_id)).execute()
        
        return len(result.data) > 0
    
    async def regenerate_token(self, integration_id: UUID, user_id: UUID) -> Optional[Integration]:
        """Regenera o token de uma integração."""
        new_token = self._generate_webhook_token()
        
        result = self.supabase.table("integrations").update({
            "webhook_token": new_token,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", str(integration_id)).eq("user_id", str(user_id)).execute()
        
        if not result.data:
            return None
        
        return Integration(**result.data[0])
    
    async def update_last_used(self, integration_id: UUID) -> None:
        """Atualiza o timestamp de último uso."""
        self.supabase.table("integrations").update({
            "last_used_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", str(integration_id)).execute()
    
    # Métodos para WebhookCall
    
    async def create_webhook_call(self, webhook_call: WebhookCall) -> WebhookCall:
        """Registra uma chamada de webhook."""
        call_data = {
            "integration_id": str(webhook_call.integration_id),
            "agent_id": str(webhook_call.agent_id),
            "payload": webhook_call.payload,
            "ip_address": webhook_call.ip_address,
            "user_agent": webhook_call.user_agent,
            "status_code": webhook_call.status_code,
            "response_data": webhook_call.response_data,
            "error_message": webhook_call.error_message,
            "execution_time_ms": webhook_call.execution_time_ms,
            "created_at": webhook_call.created_at.isoformat()
        }
        
        result = self.supabase.table("webhook_calls").insert(call_data).execute()
        
        if not result.data:
            raise Exception("Failed to create webhook call")
        
        return WebhookCall(**result.data[0])
    
    async def get_webhook_calls(
        self,
        integration_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status_code: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[WebhookCall]:
        """Lista chamadas de webhook."""
        query = self.supabase.table("webhook_calls").select("*").eq(
            "integration_id", str(integration_id)
        )
        
        if status_code:
            query = query.eq("status_code", status_code)
        
        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        
        if end_date:
            query = query.lte("created_at", end_date.isoformat())
        
        result = query.range(offset, offset + limit - 1).order("created_at", desc=True).execute()
        
        return [WebhookCall(**item) for item in result.data]
    
    async def get_integration_analytics(
        self,
        integration_id: UUID,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """Obtém analytics de uma integração."""
        start_time = datetime.utcnow() - timedelta(hours=period_hours)
        
        # Buscar chamadas no período
        calls = await self.get_webhook_calls(
            integration_id=integration_id,
            start_date=start_time,
            limit=10000  # Limite alto para analytics
        )
        
        if not calls:
            return {
                "integration_id": str(integration_id),
                "period_hours": period_hours,
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "success_rate": 0.0,
                "avg_response_time_ms": 0.0,
                "calls_by_hour": [],
                "status_code_distribution": {},
                "error_types": {},
                "top_user_agents": [],
                "top_ip_addresses": []
            }
        
        # Calcular métricas
        total_calls = len(calls)
        successful_calls = len([c for c in calls if c.is_successful()])
        failed_calls = total_calls - successful_calls
        success_rate = successful_calls / total_calls if total_calls > 0 else 0.0
        avg_response_time = sum(c.execution_time_ms for c in calls) / total_calls
        
        # Distribuição por código de status
        status_distribution = {}
        for call in calls:
            status_distribution[str(call.status_code)] = status_distribution.get(str(call.status_code), 0) + 1
        
        # Top user agents
        user_agents = {}
        for call in calls:
            ua = call.user_agent[:50]  # Truncar para análise
            user_agents[ua] = user_agents.get(ua, 0) + 1
        
        top_user_agents = [
            {"user_agent": ua, "count": count}
            for ua, count in sorted(user_agents.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # Top IPs
        ip_addresses = {}
        for call in calls:
            ip_addresses[call.ip_address] = ip_addresses.get(call.ip_address, 0) + 1
        
        top_ips = [
            {"ip_address": ip, "count": count}
            for ip, count in sorted(ip_addresses.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        return {
            "integration_id": str(integration_id),
            "period_hours": period_hours,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": success_rate,
            "avg_response_time_ms": avg_response_time,
            "calls_by_hour": [],  # TODO: Implementar agrupamento por hora
            "status_code_distribution": status_distribution,
            "error_types": {},  # TODO: Implementar análise de tipos de erro
            "top_user_agents": top_user_agents,
            "top_ip_addresses": top_ips
        }


# Instância global do repositório
integration_repository = IntegrationRepository()


def get_integration_repository() -> IntegrationRepository:
    """Dependency injection para o repositório."""
    return integration_repository