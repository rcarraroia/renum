"""
Supabase Agent (sa-supabase)
Agente especializado para operações com Supabase Database
"""
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

from app.agents.base_agent import BaseAgent, AgentCapability, AgentExecutionResult
from app.domain.credentials import ProviderType

class SupabaseAgent(BaseAgent):
    """Agente para integração com Supabase Database"""
    
    def __init__(self):
        super().__init__(
            agent_id="sa-supabase",
            name="Supabase Agent",
            description="Agente especializado para operações de banco de dados via Supabase API",
            version="1.0.0"
        )
    
    def _define_capabilities(self) -> List[AgentCapability]:
        """Define capacidades do Supabase Agent"""
        return [
            AgentCapability(
                name="select_data",
                description="Consultar dados de uma tabela",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Nome da tabela"},
                        "columns": {"type": "array", "items": {"type": "string"}, "description": "Colunas a selecionar"},
                        "filters": {
                            "type": "object",
                            "description": "Filtros para aplicar",
                            "additionalProperties": True
                        },
                        "order_by": {"type": "string", "description": "Coluna para ordenação"},
                        "order_desc": {"type": "boolean", "default": False, "description": "Ordem decrescente"},
                        "limit": {"type": "integer", "description": "Limite de registros"},
                        "offset": {"type": "integer", "description": "Offset para paginação"}
                    },
                    "required": ["table"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array", "description": "Dados retornados"},
                        "count": {"type": "integer", "description": "Número de registros"}
                    }
                },
                required_credentials=["supabase"]
            ),
            
            AgentCapability(
                name="insert_data",
                description="Inserir dados em uma tabela",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Nome da tabela"},
                        "data": {
                            "oneOf": [
                                {"type": "object", "description": "Objeto único para inserir"},
                                {"type": "array", "items": {"type": "object"}, "description": "Array de objetos"}
                            ]
                        },
                        "upsert": {"type": "boolean", "default": False, "description": "Usar upsert"},
                        "on_conflict": {"type": "string", "description": "Coluna para resolução de conflito"}
                    },
                    "required": ["table", "data"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array", "description": "Dados inseridos"},
                        "count": {"type": "integer", "description": "Número de registros inseridos"}
                    }
                },
                required_credentials=["supabase"]
            ),
            
            AgentCapability(
                name="update_data",
                description="Atualizar dados em uma tabela",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Nome da tabela"},
                        "data": {"type": "object", "description": "Dados para atualizar"},
                        "filters": {
                            "type": "object",
                            "description": "Filtros para identificar registros",
                            "additionalProperties": True
                        }
                    },
                    "required": ["table", "data", "filters"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array", "description": "Dados atualizados"},
                        "count": {"type": "integer", "description": "Número de registros atualizados"}
                    }
                },
                required_credentials=["supabase"]
            ),
            
            AgentCapability(
                name="delete_data",
                description="Deletar dados de uma tabela",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Nome da tabela"},
                        "filters": {
                            "type": "object",
                            "description": "Filtros para identificar registros",
                            "additionalProperties": True
                        }
                    },
                    "required": ["table", "filters"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "Número de registros deletados"}
                    }
                },
                required_credentials=["supabase"]
            ),
            
            AgentCapability(
                name="execute_rpc",
                description="Executar função RPC do Supabase",
                input_schema={
                    "type": "object",
                    "properties": {
                        "function_name": {"type": "string", "description": "Nome da função"},
                        "parameters": {"type": "object", "description": "Parâmetros da função"}
                    },
                    "required": ["function_name"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "data": {"description": "Resultado da função"}
                    }
                },
                required_credentials=["supabase"]
            ),
            
            AgentCapability(
                name="get_table_schema",
                description="Obter schema de uma tabela",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Nome da tabela"}
                    },
                    "required": ["table"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "columns": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "nullable": {"type": "boolean"},
                                    "default": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                required_credentials=["supabase"]
            )
        ]
    
    async def execute_capability(
        self,
        capability_name: str,
        input_data: Dict[str, Any],
        user_id: UUID,
        credential_id: Optional[UUID] = None
    ) -> AgentExecutionResult:
        """Executa capacidade do Supabase Agent"""
        start_time = datetime.utcnow()
        
        try:
            # Validar entrada
            is_valid, error_msg = await self.validate_input(capability_name, input_data)
            if not is_valid:
                return AgentExecutionResult(
                    success=False,
                    error_message=error_msg
                )
            
            # Obter credenciais
            credentials = await self.get_user_credential(
                user_id, ProviderType.SUPABASE, credential_id
            )
            
            if not credentials:
                return AgentExecutionResult(
                    success=False,
                    error_message="Credenciais do Supabase não encontradas"
                )
            
            # Executar capacidade específica
            if capability_name == "select_data":
                result = await self._select_data(input_data, credentials)
            elif capability_name == "insert_data":
                result = await self._insert_data(input_data, credentials)
            elif capability_name == "update_data":
                result = await self._update_data(input_data, credentials)
            elif capability_name == "delete_data":
                result = await self._delete_data(input_data, credentials)
            elif capability_name == "execute_rpc":
                result = await self._execute_rpc(input_data, credentials)
            elif capability_name == "get_table_schema":
                result = await self._get_table_schema(input_data, credentials)
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Capacidade '{capability_name}' não implementada"
                )
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Log da execução
            await self.log_execution(capability_name, input_data, result, user_id)
            
            result.execution_time_ms = execution_time
            return result
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            result = AgentExecutionResult(
                success=False,
                error_message=f"Erro na execução: {str(e)}",
                execution_time_ms=execution_time
            )
            
            await self.log_execution(capability_name, input_data, result, user_id)
            return result
    
    async def _select_data(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Consultar dados de uma tabela"""
        try:
            base_url = credentials.get('url')
            api_key = credentials.get('anon_key')
            
            if not base_url or not api_key:
                return AgentExecutionResult(
                    success=False,
                    error_message="URL ou API key do Supabase não encontrados"
                )
            
            table = input_data['table']
            url = f"{base_url}/rest/v1/{table}"
            
            headers = {
                'apikey': api_key,
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            params = {}
            
            # Colunas a selecionar
            if input_data.get('columns'):
                params['select'] = ','.join(input_data['columns'])
            
            # Filtros
            if input_data.get('filters'):
                for key, value in input_data['filters'].items():
                    if isinstance(value, dict):
                        # Filtros complexos (eq, gt, lt, etc.)
                        for op, val in value.items():
                            params[f"{key}"] = f"{op}.{val}"
                    else:
                        # Filtro simples (igualdade)
                        params[f"{key}"] = f"eq.{value}"
            
            # Ordenação
            if input_data.get('order_by'):
                order = input_data['order_by']
                if input_data.get('order_desc', False):
                    order += '.desc'
                params['order'] = order
            
            # Limite e offset
            if input_data.get('limit'):
                params['limit'] = input_data['limit']
            
            if input_data.get('offset'):
                params['offset'] = input_data['offset']
            
            response = await self.http_client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return AgentExecutionResult(
                    success=True,
                    data={
                        'data': data,
                        'count': len(data)
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Supabase API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao consultar dados: {str(e)}"
            )
    
    async def _insert_data(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Inserir dados em uma tabela"""
        try:
            base_url = credentials.get('url')
            api_key = credentials.get('service_role_key') or credentials.get('anon_key')
            
            if not base_url or not api_key:
                return AgentExecutionResult(
                    success=False,
                    error_message="URL ou API key do Supabase não encontrados"
                )
            
            table = input_data['table']
            url = f"{base_url}/rest/v1/{table}"
            
            headers = {
                'apikey': api_key,
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            # Upsert se especificado
            if input_data.get('upsert', False):
                headers['Prefer'] += ',resolution=merge-duplicates'
                if input_data.get('on_conflict'):
                    headers['Prefer'] += f',on-conflict={input_data["on_conflict"]}'
            
            data = input_data['data']
            
            response = await self.http_client.post(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                result_data = response.json()
                return AgentExecutionResult(
                    success=True,
                    data={
                        'data': result_data,
                        'count': len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Supabase API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao inserir dados: {str(e)}"
            )
    
    async def _update_data(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Atualizar dados em uma tabela"""
        try:
            base_url = credentials.get('url')
            api_key = credentials.get('service_role_key') or credentials.get('anon_key')
            
            table = input_data['table']
            url = f"{base_url}/rest/v1/{table}"
            
            headers = {
                'apikey': api_key,
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            params = {}
            
            # Aplicar filtros
            for key, value in input_data['filters'].items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        params[f"{key}"] = f"{op}.{val}"
                else:
                    params[f"{key}"] = f"eq.{value}"
            
            data = input_data['data']
            
            response = await self.http_client.patch(url, headers=headers, params=params, json=data)
            
            if response.status_code == 200:
                result_data = response.json()
                return AgentExecutionResult(
                    success=True,
                    data={
                        'data': result_data,
                        'count': len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Supabase API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao atualizar dados: {str(e)}"
            )
    
    async def _delete_data(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Deletar dados de uma tabela"""
        try:
            base_url = credentials.get('url')
            api_key = credentials.get('service_role_key') or credentials.get('anon_key')
            
            table = input_data['table']
            url = f"{base_url}/rest/v1/{table}"
            
            headers = {
                'apikey': api_key,
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            params = {}
            
            # Aplicar filtros
            for key, value in input_data['filters'].items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        params[f"{key}"] = f"{op}.{val}"
                else:
                    params[f"{key}"] = f"eq.{value}"
            
            response = await self.http_client.delete(url, headers=headers, params=params)
            
            if response.status_code == 200:
                result_data = response.json()
                return AgentExecutionResult(
                    success=True,
                    data={
                        'count': len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Supabase API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao deletar dados: {str(e)}"
            )
    
    async def _execute_rpc(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Executar função RPC do Supabase"""
        try:
            base_url = credentials.get('url')
            api_key = credentials.get('service_role_key') or credentials.get('anon_key')
            
            function_name = input_data['function_name']
            url = f"{base_url}/rest/v1/rpc/{function_name}"
            
            headers = {
                'apikey': api_key,
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            parameters = input_data.get('parameters', {})
            
            response = await self.http_client.post(url, headers=headers, json=parameters)
            
            if response.status_code == 200:
                result_data = response.json()
                return AgentExecutionResult(
                    success=True,
                    data={'data': result_data}
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    error_message=f"Erro da Supabase API: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao executar RPC: {str(e)}"
            )
    
    async def _get_table_schema(
        self,
        input_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Obter schema de uma tabela"""
        try:
            # Esta seria uma implementação mais complexa que consultaria
            # as tabelas de sistema do PostgreSQL via Supabase
            # Por enquanto, retorna um schema mock
            
            table = input_data['table']
            
            # Mock schema - em produção consultaria information_schema
            mock_schema = {
                'columns': [
                    {'name': 'id', 'type': 'uuid', 'nullable': False, 'default': 'gen_random_uuid()'},
                    {'name': 'created_at', 'type': 'timestamp', 'nullable': False, 'default': 'now()'},
                    {'name': 'updated_at', 'type': 'timestamp', 'nullable': False, 'default': 'now()'}
                ]
            }
            
            return AgentExecutionResult(
                success=True,
                data=mock_schema,
                metadata={'table': table, 'note': 'Schema mock - implementar consulta real'}
            )
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error_message=f"Erro ao obter schema: {str(e)}"
            )
    
    def _get_supported_providers(self) -> List[str]:
        """Provedores suportados"""
        return ['supabase']
    
    def _get_category(self) -> str:
        """Categoria do agente"""
        return 'database'