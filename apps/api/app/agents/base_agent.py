"""
Base Agent Class
Classe base para todos os agentes especializados do sistema
"""
import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
import httpx
import structlog

from app.domain.credentials import UserCredential, ProviderType
from app.services.user_credentials_service import UserCredentialsService

logger = structlog.get_logger(__name__)

class AgentCapability:
    """Representa uma capacidade do agente"""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        required_credentials: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.required_credentials = required_credentials or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'input_schema': self.input_schema,
            'output_schema': self.output_schema,
            'required_credentials': self.required_credentials
        }

class AgentExecutionResult:
    """Resultado da execução de um agente"""
    
    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data or {}
        self.error_message = error_message
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

class BaseAgent(ABC):
    """Classe base para todos os agentes especializados"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        version: str = "1.0.0",
        credentials_service: Optional[UserCredentialsService] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.version = version
        self.credentials_service = credentials_service or UserCredentialsService()
        
        # HTTP client para requisições externas
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={'User-Agent': f'Renum-Agent/{self.agent_id}/{self.version}'}
        )
        
        # Cache de credenciais
        self._credentials_cache = {}
        
        # Inicializar capacidades
        self.capabilities = self._define_capabilities()
    
    @abstractmethod
    def _define_capabilities(self) -> List[AgentCapability]:
        """Define as capacidades do agente"""
        pass
    
    @abstractmethod
    async def execute_capability(
        self,
        capability_name: str,
        input_data: Dict[str, Any],
        user_id: UUID,
        credential_id: Optional[UUID] = None
    ) -> AgentExecutionResult:
        """Executa uma capacidade específica do agente"""
        pass
    
    def has_capability(self, capability_name: str) -> bool:
        """Verifica se o agente tem uma capacidade específica"""
        return any(cap.name == capability_name for cap in self.capabilities)
    
    def get_capability(self, capability_name: str) -> Optional[AgentCapability]:
        """Obtém uma capacidade específica"""
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap
        return None
    
    async def get_user_credential(
        self,
        user_id: UUID,
        provider: ProviderType,
        credential_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """Obtém credencial do usuário para o provedor"""
        try:
            cache_key = f"{user_id}:{provider.value}:{credential_id}"
            
            # Verificar cache
            if cache_key in self._credentials_cache:
                return self._credentials_cache[cache_key]
            
            if credential_id:
                # Buscar credencial específica
                credential_data = await self.credentials_service.get_credential_by_id(
                    credential_id, user_id, decrypt=True
                )
            else:
                # Buscar primeira credencial ativa do provedor
                credentials = await self.credentials_service.get_user_credentials(
                    user_id=user_id,
                    provider=provider,
                    status=None
                )
                
                # Filtrar apenas credenciais ativas
                active_credentials = [c for c in credentials if c.get('status') == 'active']
                if not active_credentials:
                    return None
                
                # Pegar a primeira credencial ativa e descriptografar
                credential_data = await self.credentials_service.get_credential_by_id(
                    UUID(active_credentials[0]['id']), user_id, decrypt=True
                )
            
            if credential_data and credential_data.get('decrypted_data'):
                # Cache por 5 minutos
                self._credentials_cache[cache_key] = credential_data['decrypted_data']
                
                # Limpar cache após 5 minutos
                asyncio.create_task(self._clear_cache_after_delay(cache_key, 300))
                
                return credential_data['decrypted_data']
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter credencial: {str(e)}", agent_id=self.agent_id)
            return None
    
    async def _clear_cache_after_delay(self, cache_key: str, delay_seconds: int):
        """Limpa cache após delay"""
        await asyncio.sleep(delay_seconds)
        if cache_key in self._credentials_cache:
            del self._credentials_cache[cache_key]
    
    async def validate_input(
        self,
        capability_name: str,
        input_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Valida dados de entrada para uma capacidade"""
        capability = self.get_capability(capability_name)
        if not capability:
            return False, f"Capacidade '{capability_name}' não encontrada"
        
        # Validação básica de campos obrigatórios
        required_fields = capability.input_schema.get('required', [])
        for field in required_fields:
            if field not in input_data:
                return False, f"Campo obrigatório '{field}' não fornecido"
        
        return True, None
    
    async def log_execution(
        self,
        capability_name: str,
        input_data: Dict[str, Any],
        result: AgentExecutionResult,
        user_id: UUID
    ):
        """Log da execução do agente"""
        logger.info(
            "Execução de agente",
            agent_id=self.agent_id,
            capability=capability_name,
            success=result.success,
            execution_time_ms=result.execution_time_ms,
            user_id=str(user_id),
            error=result.error_message if not result.success else None
        )
    
    def get_manifest(self) -> Dict[str, Any]:
        """Retorna manifesto do agente"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'capabilities': [cap.to_dict() for cap in self.capabilities],
            'supported_providers': self._get_supported_providers(),
            'metadata': {
                'created_at': datetime.utcnow().isoformat(),
                'agent_type': 'specialized',
                'category': self._get_category()
            }
        }
    
    @abstractmethod
    def _get_supported_providers(self) -> List[str]:
        """Retorna lista de provedores suportados"""
        pass
    
    @abstractmethod
    def _get_category(self) -> str:
        """Retorna categoria do agente"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do agente"""
        try:
            # Teste básico de conectividade
            start_time = datetime.utcnow()
            
            # Verificar se HTTP client está funcionando
            response = await self.http_client.get('https://httpbin.org/status/200')
            
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                'status': 'healthy',
                'agent_id': self.agent_id,
                'version': self.version,
                'response_time_ms': response_time,
                'capabilities_count': len(self.capabilities),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'agent_id': self.agent_id,
                'version': self.version,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Fecha recursos do agente"""
        await self.http_client.aclose()
        self._credentials_cache.clear()
    
    def __str__(self) -> str:
        return f"{self.name} ({self.agent_id}) v{self.version}"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.agent_id}>"