"""
Agents API endpoints
Handles specialized agent operations and execution
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.agents.agent_registry import get_agent_registry, AgentRegistry
from app.schemas.agent import (
    AgentManifestSchema,
    AgentExecutionSchema,
    AgentExecutionResultSchema,
    AgentHealthSchema,
    AgentStatsSchema
)

router = APIRouter(prefix="/agents", tags=["Specialized Agents"])

@router.get("/", response_model=List[AgentManifestSchema])
async def list_agents(
    category: Optional[str] = Query(None, description="Filter by category"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """List all available specialized agents"""
    try:
        if category:
            agents = registry.get_agents_by_category(category)
        elif provider:
            agents = registry.get_agents_by_provider(provider)
        else:
            agents = registry.list_agents()
        
        manifests = []
        for agent in agents:
            manifest = agent.get_manifest()
            manifests.append(AgentManifestSchema(
                agent_id=manifest['agent_id'],
                name=manifest['name'],
                description=manifest['description'],
                version=manifest['version'],
                capabilities=manifest['capabilities'],
                supported_providers=manifest['supported_providers'],
                metadata=manifest['metadata']
            ))
        
        return manifests
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar agentes: {str(e)}"
        )

@router.get("/{agent_id}", response_model=AgentManifestSchema)
async def get_agent_manifest(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Get agent manifest by ID"""
    try:
        manifest = registry.get_agent_manifest(agent_id)
        
        if not manifest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agente '{agent_id}' não encontrado"
            )
        
        return AgentManifestSchema(
            agent_id=manifest['agent_id'],
            name=manifest['name'],
            description=manifest['description'],
            version=manifest['version'],
            capabilities=manifest['capabilities'],
            supported_providers=manifest['supported_providers'],
            metadata=manifest['metadata']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter manifesto: {str(e)}"
        )

@router.post("/{agent_id}/execute", response_model=AgentExecutionResultSchema)
async def execute_agent_capability(
    agent_id: str,
    execution_data: AgentExecutionSchema,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Execute agent capability"""
    try:
        agent = registry.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agente '{agent_id}' não encontrado"
            )
        
        # Verificar se agente tem a capacidade
        if not agent.has_capability(execution_data.capability_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agente '{agent_id}' não tem capacidade '{execution_data.capability_name}'"
            )
        
        # For now, use a mock user ID
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        # Executar capacidade
        result = await agent.execute_capability(
            capability_name=execution_data.capability_name,
            input_data=execution_data.input_data,
            user_id=mock_user_id,
            credential_id=execution_data.credential_id
        )
        
        return AgentExecutionResultSchema(
            success=result.success,
            data=result.data,
            error_message=result.error_message,
            execution_time_ms=result.execution_time_ms,
            metadata=result.metadata,
            timestamp=result.timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar agente: {str(e)}"
        )

@router.get("/{agent_id}/capabilities")
async def get_agent_capabilities(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Get agent capabilities"""
    try:
        agent = registry.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agente '{agent_id}' não encontrado"
            )
        
        capabilities = []
        for cap in agent.capabilities:
            capabilities.append({
                'name': cap.name,
                'description': cap.description,
                'input_schema': cap.input_schema,
                'output_schema': cap.output_schema,
                'required_credentials': cap.required_credentials
            })
        
        return {
            'agent_id': agent_id,
            'capabilities': capabilities
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter capacidades: {str(e)}"
        )

@router.get("/{agent_id}/health", response_model=AgentHealthSchema)
async def check_agent_health(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Check agent health"""
    try:
        agent = registry.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agente '{agent_id}' não encontrado"
            )
        
        health = await agent.health_check()
        
        return AgentHealthSchema(
            status=health['status'],
            agent_id=health['agent_id'],
            version=health['version'],
            response_time_ms=health.get('response_time_ms'),
            capabilities_count=health.get('capabilities_count'),
            error=health.get('error'),
            timestamp=health['timestamp']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao verificar saúde: {str(e)}"
        )

@router.get("/health/all")
async def check_all_agents_health(
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Check health of all agents"""
    try:
        health_results = await registry.health_check_all()
        
        return {
            'total_agents': len(health_results),
            'healthy_agents': len([h for h in health_results.values() if h.get('status') == 'healthy']),
            'unhealthy_agents': len([h for h in health_results.values() if h.get('status') != 'healthy']),
            'results': health_results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao verificar saúde dos agentes: {str(e)}"
        )

@router.get("/search/capability")
async def search_agents_by_capability(
    capability: str = Query(..., description="Capability name to search for"),
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Search agents by capability"""
    try:
        agents = registry.search_agents_by_capability(capability)
        
        results = []
        for agent in agents:
            capability_obj = agent.get_capability(capability)
            results.append({
                'agent_id': agent.agent_id,
                'name': agent.name,
                'description': agent.description,
                'capability': {
                    'name': capability_obj.name,
                    'description': capability_obj.description,
                    'input_schema': capability_obj.input_schema,
                    'output_schema': capability_obj.output_schema,
                    'required_credentials': capability_obj.required_credentials
                }
            })
        
        return {
            'capability': capability,
            'found_agents': len(results),
            'agents': results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar agentes: {str(e)}"
        )

@router.get("/stats/overview", response_model=AgentStatsSchema)
async def get_agents_stats(
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Get agents registry statistics"""
    try:
        stats = registry.get_registry_stats()
        
        return AgentStatsSchema(
            total_agents=stats['total_agents'],
            categories=stats['categories'],
            supported_providers=stats['supported_providers'],
            total_capabilities=stats['total_capabilities'],
            agents=stats['agents']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas: {str(e)}"
        )

@router.get("/categories/list")
async def list_agent_categories(
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """List all agent categories"""
    try:
        agents = registry.list_agents()
        categories = set()
        
        for agent in agents:
            categories.add(agent._get_category())
        
        return {
            'categories': sorted(list(categories))
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar categorias: {str(e)}"
        )

@router.get("/providers/list")
async def list_supported_providers(
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """List all supported providers"""
    try:
        agents = registry.list_agents()
        providers = set()
        
        for agent in agents:
            providers.update(agent._get_supported_providers())
        
        return {
            'providers': sorted(list(providers))
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar provedores: {str(e)}"
        )