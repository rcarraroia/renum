"""
Domain models para agentes
Entidades de negócio com lógica de domínio
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel


class AgentCapability:
    """Capacidade de um agente"""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'name': self.name,
            'description': self.description,
            'input_schema': self.input_schema,
            'output_schema': self.output_schema
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCapability':
        """Criar a partir de dicionário"""
        return cls(
            name=data['name'],
            description=data['description'],
            input_schema=data['input_schema'],
            output_schema=data.get('output_schema', {})
        )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validar dados de entrada contra o schema"""
        # Implementação básica - em produção usaria jsonschema
        if self.input_schema.get('type') == 'object':
            required_props = self.input_schema.get('required', [])
            for prop in required_props:
                if prop not in input_data:
                    return False
        return True


class AgentPolicy:
    """Políticas de execução de um agente"""
    
    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_concurrent_executions: int = 5,
        timeout_seconds: int = 30,
        allowed_domains: Optional[List[str]] = None,
        require_confirmation: bool = False,
        cost_per_execution: float = 0.0
    ):
        self.max_requests_per_minute = max_requests_per_minute
        self.max_concurrent_executions = max_concurrent_executions
        self.timeout_seconds = timeout_seconds
        self.allowed_domains = allowed_domains or []
        self.require_confirmation = require_confirmation
        self.cost_per_execution = cost_per_execution
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'max_requests_per_minute': self.max_requests_per_minute,
            'max_concurrent_executions': self.max_concurrent_executions,
            'timeout_seconds': self.timeout_seconds,
            'allowed_domains': self.allowed_domains,
            'require_confirmation': self.require_confirmation,
            'cost_per_execution': self.cost_per_execution
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentPolicy':
        """Criar a partir de dicionário"""
        return cls(
            max_requests_per_minute=data.get('max_requests_per_minute', 60),
            max_concurrent_executions=data.get('max_concurrent_executions', 5),
            timeout_seconds=data.get('timeout_seconds', 30),
            allowed_domains=data.get('allowed_domains', []),
            require_confirmation=data.get('require_confirmation', False),
            cost_per_execution=data.get('cost_per_execution', 0.0)
        )
    
    def can_execute(self, current_executions: int) -> bool:
        """Verificar se pode executar baseado nas políticas"""
        return current_executions < self.max_concurrent_executions
    
    def is_domain_allowed(self, domain: str) -> bool:
        """Verificar se domínio é permitido"""
        if not self.allowed_domains:
            return True
        return domain in self.allowed_domains


class AgentDependency:
    """Dependência de um agente"""
    
    def __init__(self, agent_id: str, version: str, optional: bool = False):
        self.agent_id = agent_id
        self.version = version
        self.optional = optional
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'agent_id': self.agent_id,
            'version': self.version,
            'optional': self.optional
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentDependency':
        """Criar a partir de dicionário"""
        return cls(
            agent_id=data['agent_id'],
            version=data['version'],
            optional=data.get('optional', False)
        )


class Agent:
    """Entidade de domínio para agente"""
    
    def __init__(
        self,
        agent_id: str,
        version: str,
        name: str,
        description: Optional[str] = None,
        capabilities: Optional[List[AgentCapability]] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        policy: Optional[AgentPolicy] = None,
        dependencies: Optional[List[AgentDependency]] = None,
        status: str = "active",
        id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        manifest_checksum: Optional[str] = None,
        manifest_signature: Optional[str] = None,
        signature_key_id: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.agent_id = agent_id
        self.version = version
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.input_schema = input_schema or {}
        self.policy = policy or AgentPolicy()
        self.dependencies = dependencies or []
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.manifest_checksum = manifest_checksum
        self.manifest_signature = manifest_signature
        self.signature_key_id = signature_key_id
        
        # Validar na criação
        self._validate()
    
    def _validate(self):
        """Validar regras de negócio da entidade"""
        if not self.agent_id.startswith('sa-'):
            raise ValueError("agent_id deve começar com 'sa-'")
        
        if not self._is_valid_semantic_version(self.version):
            raise ValueError(f"Versão inválida: {self.version}")
        
        if not self.capabilities:
            raise ValueError("Agente deve ter pelo menos uma capacidade")
        
        if self.status not in ['active', 'inactive', 'deprecated']:
            raise ValueError(f"Status inválido: {self.status}")
    
    def _is_valid_semantic_version(self, version: str) -> bool:
        """Verificar se versão segue padrão semântico"""
        import re
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
    
    def add_capability(self, capability: AgentCapability):
        """Adicionar nova capacidade"""
        # Verificar se já existe
        for existing in self.capabilities:
            if existing.name == capability.name:
                raise ValueError(f"Capacidade '{capability.name}' já existe")
        
        self.capabilities.append(capability)
        self.updated_at = datetime.utcnow()
    
    def remove_capability(self, capability_name: str):
        """Remover capacidade"""
        self.capabilities = [
            cap for cap in self.capabilities 
            if cap.name != capability_name
        ]
        
        if not self.capabilities:
            raise ValueError("Agente deve ter pelo menos uma capacidade")
        
        self.updated_at = datetime.utcnow()
    
    def update_policy(self, policy: AgentPolicy):
        """Atualizar políticas"""
        self.policy = policy
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """Ativar agente"""
        if self.status == 'deprecated':
            raise ValueError("Agente depreciado não pode ser ativado")
        
        self.status = 'active'
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Desativar agente"""
        self.status = 'inactive'
        self.updated_at = datetime.utcnow()
    
    def deprecate(self, deprecated_by: UUID):
        """Depreciar agente"""
        self.status = 'deprecated'
        self.updated_at = datetime.utcnow()
        # Em implementação completa, registraria quem depreciou
    
    def approve(self, approved_by: UUID):
        """Aprovar agente para produção"""
        if self.status != 'active':
            raise ValueError("Apenas agentes ativos podem ser aprovados")
        
        # Gerar checksum se não existir
        if not self.manifest_checksum:
            self.manifest_checksum = self.calculate_checksum()
        
        self.updated_at = datetime.utcnow()
        # Em implementação completa, mudaria status para 'approved'
    
    def calculate_checksum(self) -> str:
        """Calcular checksum do manifesto"""
        manifest_data = self.generate_manifest()
        manifest_json = json.dumps(manifest_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(manifest_json.encode()).hexdigest()
    
    def sign_manifest(self, signature: str, key_id: str):
        """Assinar manifesto digitalmente"""
        self.manifest_signature = signature
        self.signature_key_id = key_id
        self.updated_at = datetime.utcnow()
    
    def generate_manifest(self) -> Dict[str, Any]:
        """Gerar manifesto para execução"""
        return {
            'agent_id': self.agent_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'capabilities': [cap.to_dict() for cap in self.capabilities],
            'input_schema': self.input_schema,
            'policy': self.policy.to_dict(),
            'dependencies': [dep.to_dict() for dep in self.dependencies],
            'checksum': self.manifest_checksum,
            'signature': self.manifest_signature,
            'signature_key_id': self.signature_key_id
        }
    
    def has_capability(self, capability_name: str) -> bool:
        """Verificar se agente tem capacidade específica"""
        return any(cap.name == capability_name for cap in self.capabilities)
    
    def get_capability(self, capability_name: str) -> Optional[AgentCapability]:
        """Obter capacidade específica"""
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap
        return None
    
    def can_execute_with_input(self, input_data: Dict[str, Any]) -> bool:
        """Verificar se pode executar com dados de entrada"""
        # Validar contra schema geral
        if self.input_schema:
            # Implementação básica - em produção usaria jsonschema
            pass
        
        # Verificar se tem capacidades necessárias
        return len(self.capabilities) > 0
    
    def estimate_execution_cost(self, input_data: Dict[str, Any]) -> float:
        """Estimar custo de execução"""
        base_cost = self.policy.cost_per_execution
        
        # Ajustar baseado na complexidade dos dados
        complexity_factor = 1.0
        if isinstance(input_data, dict):
            complexity_factor = min(2.0, 1.0 + len(input_data) * 0.1)
        
        return base_cost * complexity_factor
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'id': str(self.id),
            'agent_id': self.agent_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'capabilities': [cap.to_dict() for cap in self.capabilities],
            'input_schema': self.input_schema,
            'policy': self.policy.to_dict(),
            'dependencies': [dep.to_dict() for dep in self.dependencies],
            'status': self.status,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'manifest_checksum': self.manifest_checksum,
            'manifest_signature': self.manifest_signature,
            'signature_key_id': self.signature_key_id
        }


class AgentTemplate:
    """Template para criação rápida de agentes"""
    
    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        category: str,
        default_capabilities: List[Dict[str, Any]],
        default_policy: Dict[str, Any],
        required_connections: List[str]
    ):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.category = category
        self.default_capabilities = default_capabilities
        self.default_policy = default_policy
        self.required_connections = required_connections
    
    def create_agent(
        self,
        agent_id: str,
        version: str = "1.0.0",
        customizations: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """Criar agente a partir do template"""
        customizations = customizations or {}
        
        # Criar capacidades
        capabilities = []
        for cap_data in self.default_capabilities:
            capabilities.append(AgentCapability.from_dict(cap_data))
        
        # Criar política
        policy = AgentPolicy.from_dict(self.default_policy)
        
        # Aplicar customizações
        name = customizations.get('name', self.name)
        description = customizations.get('description', self.description)
        
        return Agent(
            agent_id=agent_id,
            version=version,
            name=name,
            description=description,
            capabilities=capabilities,
            policy=policy
        )