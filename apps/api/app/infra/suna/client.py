"""
Cliente para integração com Suna Backend.

Este módulo isola toda a comunicação com o Suna Backend,
fornecendo uma interface limpa para o resto da aplicação.
"""

import httpx
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import asyncio
from contextlib import asynccontextmanager

# Configurações do Suna Backend
SUNA_API_URL = "http://157.180.39.41:8000/api"
SUNA_WS_URL = "ws://157.180.39.41:8000/ws"

class SunaClient:
    """Cliente para comunicação com Suna Backend."""
    
    def __init__(self, api_url: str = SUNA_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    @asynccontextmanager
    async def get_client(self):
        """Context manager para cliente HTTP."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=30.0
            )
        
        try:
            yield self._client
        finally:
            pass  # Mantém cliente aberto para reutilização
    
    async def close(self):
        """Fecha o cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do Suna Backend."""
        try:
            async with self.get_client() as client:
                response = await client.get("/health")
                response.raise_for_status()
                return {
                    "status": "healthy",
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                    "data": response.json()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """Lista agentes disponíveis no Suna."""
        async with self.get_client() as client:
            response = await client.get("/agents")
            response.raise_for_status()
            return response.json()
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Obtém detalhes de um agente específico."""
        async with self.get_client() as client:
            response = await client.get(f"/agents/{agent_id}")
            response.raise_for_status()
            return response.json()
    
    async def execute_agent(self, agent_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa um agente com os dados fornecidos."""
        async with self.get_client() as client:
            response = await client.post(
                f"/agents/{agent_id}/execute",
                json=input_data
            )
            response.raise_for_status()
            return response.json()
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Obtém status de uma execução."""
        async with self.get_client() as client:
            response = await client.get(f"/executions/{execution_id}")
            response.raise_for_status()
            return response.json()
    
    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """Cancela uma execução."""
        async with self.get_client() as client:
            response = await client.post(f"/executions/{execution_id}/cancel")
            response.raise_for_status()
            return response.json()


# Instância global do cliente
suna_client = SunaClient()


async def get_suna_client() -> SunaClient:
    """Dependency injection para FastAPI."""
    return suna_client