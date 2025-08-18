"""
Agent Registry
Registro central de todos os agentes especializados
"""
from typing import Dict, List, Optional, Type
from app.agents.base_agent import BaseAgent
from app.agents.sa_gmail import GmailAgent
from app.agents.sa_supabase import SupabaseAgent
from app.agents.sa_whatsapp import WhatsAppAgent
from app.agents.sa_telegram import TelegramAgent
from app.agents.sa_http_generic import HTTPGenericAgent

class AgentRegistry:
    """Registro central de agentes especializados"""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {
            'sa-gmail': GmailAgent,
            'sa-supabase': SupabaseAgent,
            'sa-whatsapp': WhatsAppAgent,
            'sa-telegram': TelegramAgent,
            'sa-http-generic': HTTPGenericAgent
        }
        
        # Inicializar agentes
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Inicializar todos os agentes registrados"""
        for agent_id, agent_class in self._agent_classes.items():
            try:
                agent = agent_class()
                self._agents[agent_id] = agent
            except Exception as e:
                print(f"Erro ao inicializar agente {agent_id}: {str(e)}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Obter agente por ID"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[BaseAgent]:
        """Listar todos os agentes"""
        return list(self._agents.values())
    
    def get_agents_by_category(self, category: str) -> List[BaseAgent]:
        """Obter agentes por categoria"""
        return [
            agent for agent in self._agents.values()
            if agent._get_category() == category
        ]
    
    def get_agents_by_provider(self, provider: str) -> List[BaseAgent]:
        """Obter agentes que suportam um provedor específico"""
        return [
            agent for agent in self._agents.values()
            if provider in agent._get_supported_providers()
        ]
    
    def get_agent_manifest(self, agent_id: str) -> Optional[Dict]:
        """Obter manifesto de um agente"""
        agent = self.get_agent(agent_id)
        if agent:
            return agent.get_manifest()
        return None
    
    def get_all_manifests(self) -> Dict[str, Dict]:
        """Obter manifestos de todos os agentes"""
        manifests = {}
        for agent_id, agent in self._agents.items():
            manifests[agent_id] = agent.get_manifest()
        return manifests
    
    def search_agents_by_capability(self, capability_name: str) -> List[BaseAgent]:
        """Buscar agentes que têm uma capacidade específica"""
        return [
            agent for agent in self._agents.values()
            if agent.has_capability(capability_name)
        ]
    
    def get_registry_stats(self) -> Dict:
        """Obter estatísticas do registro"""
        categories = {}
        providers = set()
        total_capabilities = 0
        
        for agent in self._agents.values():
            # Contar por categoria
            category = agent._get_category()
            categories[category] = categories.get(category, 0) + 1
            
            # Coletar provedores
            providers.update(agent._get_supported_providers())
            
            # Contar capacidades
            total_capabilities += len(agent.capabilities)
        
        return {
            'total_agents': len(self._agents),
            'categories': categories,
            'supported_providers': list(providers),
            'total_capabilities': total_capabilities,
            'agents': list(self._agents.keys())
        }
    
    async def health_check_all(self) -> Dict[str, Dict]:
        """Verificar saúde de todos os agentes"""
        health_results = {}
        
        for agent_id, agent in self._agents.items():
            try:
                health_results[agent_id] = await agent.health_check()
            except Exception as e:
                health_results[agent_id] = {
                    'status': 'error',
                    'agent_id': agent_id,
                    'error': str(e)
                }
        
        return health_results
    
    async def close_all(self):
        """Fechar todos os agentes"""
        for agent in self._agents.values():
            try:
                await agent.close()
            except Exception as e:
                print(f"Erro ao fechar agente {agent.agent_id}: {str(e)}")
    
    def register_agent(self, agent: BaseAgent):
        """Registrar um novo agente dinamicamente"""
        self._agents[agent.agent_id] = agent
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Desregistrar um agente"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

# Instância global do registro
agent_registry = AgentRegistry()

def get_agent_registry() -> AgentRegistry:
    """Obter instância do registro de agentes"""
    return agent_registry