"""
Serviço de Editor de Prompts (Agent Builder)
Gerencia criação, edição e versionamento de prompts de agentes
"""
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import structlog

from app.core.config import settings
from app.services.sandbox_service import sandbox_service

logger = structlog.get_logger(__name__)

class PromptStatus(str, Enum):
    """Status do prompt"""
    DRAFT = "draft"
    TESTING = "testing"
    APPROVED = "approved"
    DEPRECATED = "deprecated"

class PromptCategory(str, Enum):
    """Categorias de prompt"""
    MESSAGING = "messaging"
    EMAIL = "email"
    DATA_PROCESSING = "data_processing"
    API_INTEGRATION = "api_integration"
    WORKFLOW = "workflow"
    CUSTOM = "custom"

@dataclass
class PromptTemplate:
    """Template de prompt reutilizável"""
    template_id: str
    name: str
    description: str
    category: PromptCategory
    template_content: str
    variables: List[str]
    example_usage: str
    created_by: str
    created_at: datetime
    usage_count: int = 0

@dataclass
class PromptVersion:
    """Versão de um prompt"""
    version_id: str
    prompt_id: str
    version_number: str
    content: str
    variables: List[str]
    status: PromptStatus
    created_by: str
    created_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    test_results: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None

@dataclass
class PromptGroup:
    """Grupo de prompts para A/B testing"""
    group_id: str
    name: str
    description: str
    prompts: List[str]  # IDs dos prompts
    traffic_split: Dict[str, float]  # Distribuição de tráfego
    active: bool
    created_by: str
    created_at: datetime
    test_results: Optional[Dict[str, Any]] = None

class PromptEditorService:
    """Serviço para edição e gerenciamento de prompts"""
    
    def __init__(self):
        self.prompts: Dict[str, Dict[str, PromptVersion]] = {}  # prompt_id -> {version -> PromptVersion}
        self.templates: Dict[str, PromptTemplate] = {}
        self.prompt_groups: Dict[str, PromptGroup] = {}
        
        # Inicializar templates padrão
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Inicializar templates padrão"""
        default_templates = [
            PromptTemplate(
                template_id="messaging-basic",
                name="Basic Messaging Template",
                description="Template básico para envio de mensagens",
                category=PromptCategory.MESSAGING,
                template_content="""Você é um assistente de mensagens. Sua tarefa é enviar a seguinte mensagem:

Destinatário: {{recipient}}
Mensagem: {{message}}

Instruções:
- Seja claro e direto
- Mantenha tom profissional
- Confirme o envio

Variáveis disponíveis:
- {{recipient}}: Destinatário da mensagem
- {{message}}: Conteúdo da mensagem
- {{sender_name}}: Nome do remetente
- {{timestamp}}: Timestamp atual""",
                variables=["recipient", "message", "sender_name", "timestamp"],
                example_usage="Envio de notificações automáticas",
                created_by="system",
                created_at=datetime.utcnow()
            ),
            
            PromptTemplate(
                template_id="email-formal",
                name="Formal Email Template",
                description="Template para emails formais",
                category=PromptCategory.EMAIL,
                template_content="""Você é um assistente de email profissional. Compose um email formal com:

Para: {{to}}
Assunto: {{subject}}
Conteúdo: {{body}}

Diretrizes:
- Use linguagem formal e respeitosa
- Inclua saudação apropriada
- Termine com assinatura profissional
- Verifique ortografia e gramática

Variáveis disponíveis:
- {{to}}: Destinatário do email
- {{subject}}: Assunto do email
- {{body}}: Corpo da mensagem
- {{from_name}}: Nome do remetente
- {{company}}: Nome da empresa""",
                variables=["to", "subject", "body", "from_name", "company"],
                example_usage="Comunicação corporativa e atendimento ao cliente",
                created_by="system",
                created_at=datetime.utcnow()
            ),
            
            PromptTemplate(
                template_id="api-integration",
                name="API Integration Template",
                description="Template para integrações de API",
                category=PromptCategory.API_INTEGRATION,
                template_content="""Você é um especialista em integrações de API. Execute a seguinte operação:

Endpoint: {{endpoint}}
Método: {{method}}
Dados: {{data}}

Instruções:
- Valide os dados de entrada
- Execute a chamada da API
- Trate erros apropriadamente
- Retorne resposta estruturada

Variáveis disponíveis:
- {{endpoint}}: URL do endpoint
- {{method}}: Método HTTP (GET, POST, etc.)
- {{data}}: Dados para enviar
- {{headers}}: Headers da requisição
- {{auth_token}}: Token de autenticação""",
                variables=["endpoint", "method", "data", "headers", "auth_token"],
                example_usage="Integrações com APIs externas",
                created_by="system",
                created_at=datetime.utcnow()
            )
        ]
        
        for template in default_templates:
            self.templates[template.template_id] = template
    
    async def create_prompt(
        self,
        name: str,
        description: str,
        content: str,
        variables: List[str],
        category: PromptCategory = PromptCategory.CUSTOM,
        created_by: str = "user"
    ) -> PromptVersion:
        """Criar novo prompt"""
        try:
            prompt_id = str(uuid.uuid4())
            version_id = str(uuid.uuid4())
            
            prompt_version = PromptVersion(
                version_id=version_id,
                prompt_id=prompt_id,
                version_number="1.0.0",
                content=content,
                variables=variables,
                status=PromptStatus.DRAFT,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            # Inicializar histórico de versões
            if prompt_id not in self.prompts:
                self.prompts[prompt_id] = {}
            
            self.prompts[prompt_id]["1.0.0"] = prompt_version
            
            logger.info(
                "Prompt created",
                prompt_id=prompt_id,
                version="1.0.0",
                created_by=created_by
            )
            
            return prompt_version
            
        except Exception as e:
            logger.error("Failed to create prompt", error=str(e))
            raise
    
    async def update_prompt(
        self,
        prompt_id: str,
        content: str,
        variables: List[str],
        updated_by: str
    ) -> PromptVersion:
        """Atualizar prompt (criar nova versão)"""
        try:
            if prompt_id not in self.prompts:
                raise ValueError(f"Prompt {prompt_id} not found")
            
            # Obter última versão
            versions = self.prompts[prompt_id]
            latest_version = max(versions.keys(), key=lambda v: tuple(map(int, v.split('.'))))
            
            # Incrementar versão
            major, minor, patch = map(int, latest_version.split('.'))
            new_version = f"{major}.{minor}.{patch + 1}"
            
            version_id = str(uuid.uuid4())
            
            prompt_version = PromptVersion(
                version_id=version_id,
                prompt_id=prompt_id,
                version_number=new_version,
                content=content,
                variables=variables,
                status=PromptStatus.DRAFT,
                created_by=updated_by,
                created_at=datetime.utcnow()
            )
            
            self.prompts[prompt_id][new_version] = prompt_version
            
            logger.info(
                "Prompt updated",
                prompt_id=prompt_id,
                version=new_version,
                updated_by=updated_by
            )
            
            return prompt_version
            
        except Exception as e:
            logger.error("Failed to update prompt", prompt_id=prompt_id, error=str(e))
            raise
    
    async def test_prompt_in_sandbox(
        self,
        prompt_id: str,
        version: str,
        test_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Testar prompt no ambiente sandbox"""
        try:
            if prompt_id not in self.prompts or version not in self.prompts[prompt_id]:
                raise ValueError(f"Prompt {prompt_id} version {version} not found")
            
            prompt_version = self.prompts[prompt_id][version]
            
            # Preparar dados para teste no sandbox
            sandbox_config = {
                "agent_type": "prompt_test",
                "prompt_content": prompt_version.content,
                "test_data": test_data,
                "timeout_seconds": 60
            }
            
            # Executar no sandbox
            result = await sandbox_service.execute_in_sandbox(
                config=sandbox_config,
                user_id="prompt-tester"
            )
            
            # Processar resultado
            test_result = {
                "prompt_id": prompt_id,
                "version": version,
                "test_status": "success" if result.get("success") else "failed",
                "execution_time_ms": result.get("execution_time_ms", 0),
                "output": result.get("output", ""),
                "error": result.get("error"),
                "tested_at": datetime.utcnow().isoformat(),
                "test_data_used": test_data
            }
            
            # Salvar resultado no prompt
            prompt_version.test_results = test_result
            
            logger.info(
                "Prompt tested in sandbox",
                prompt_id=prompt_id,
                version=version,
                test_status=test_result["test_status"]
            )
            
            return test_result
            
        except Exception as e:
            logger.error("Failed to test prompt in sandbox", prompt_id=prompt_id, error=str(e))
            raise
    
    async def get_prompt_versions(self, prompt_id: str) -> List[PromptVersion]:
        """Obter todas as versões de um prompt"""
        if prompt_id not in self.prompts:
            return []
        
        versions = list(self.prompts[prompt_id].values())
        versions.sort(key=lambda v: v.created_at, reverse=True)
        
        return versions
    
    async def compare_prompt_versions(
        self,
        prompt_id: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """Comparar duas versões de prompt (visual diff)"""
        try:
            if prompt_id not in self.prompts:
                raise ValueError(f"Prompt {prompt_id} not found")
            
            if version1 not in self.prompts[prompt_id] or version2 not in self.prompts[prompt_id]:
                raise ValueError("One or both versions not found")
            
            v1 = self.prompts[prompt_id][version1]
            v2 = self.prompts[prompt_id][version2]
            
            # Calcular diferenças
            diff_result = {
                "prompt_id": prompt_id,
                "version1": {
                    "version": version1,
                    "content": v1.content,
                    "variables": v1.variables,
                    "created_at": v1.created_at.isoformat(),
                    "created_by": v1.created_by
                },
                "version2": {
                    "version": version2,
                    "content": v2.content,
                    "variables": v2.variables,
                    "created_at": v2.created_at.isoformat(),
                    "created_by": v2.created_by
                },
                "differences": {
                    "content_changed": v1.content != v2.content,
                    "variables_changed": set(v1.variables) != set(v2.variables),
                    "added_variables": list(set(v2.variables) - set(v1.variables)),
                    "removed_variables": list(set(v1.variables) - set(v2.variables)),
                    "content_length_diff": len(v2.content) - len(v1.content)
                }
            }
            
            return diff_result
            
        except Exception as e:
            logger.error("Failed to compare prompt versions", prompt_id=prompt_id, error=str(e))
            raise
    
    async def create_prompt_group(
        self,
        name: str,
        description: str,
        prompt_ids: List[str],
        traffic_split: Dict[str, float],
        created_by: str
    ) -> PromptGroup:
        """Criar grupo de prompts para A/B testing"""
        try:
            # Validar traffic split
            if abs(sum(traffic_split.values()) - 1.0) > 0.01:
                raise ValueError("Traffic split must sum to 1.0")
            
            group_id = str(uuid.uuid4())
            
            prompt_group = PromptGroup(
                group_id=group_id,
                name=name,
                description=description,
                prompts=prompt_ids,
                traffic_split=traffic_split,
                active=False,  # Inicia inativo
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            self.prompt_groups[group_id] = prompt_group
            
            logger.info(
                "Prompt group created",
                group_id=group_id,
                prompts_count=len(prompt_ids),
                created_by=created_by
            )
            
            return prompt_group
            
        except Exception as e:
            logger.error("Failed to create prompt group", error=str(e))
            raise
    
    async def get_templates(self, category: Optional[PromptCategory] = None) -> List[PromptTemplate]:
        """Obter templates de prompt"""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        # Ordenar por uso e data de criação
        templates.sort(key=lambda t: (t.usage_count, t.created_at), reverse=True)
        
        return templates
    
    async def use_template(self, template_id: str, customizations: Dict[str, Any]) -> str:
        """Usar template para criar prompt personalizado"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        template.usage_count += 1
        
        # Aplicar personalizações
        content = template.template_content
        
        for key, value in customizations.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
        
        return content
    
    async def validate_prompt_syntax(self, content: str) -> Dict[str, Any]:
        """Validar sintaxe do prompt"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "variables_found": [],
            "statistics": {}
        }
        
        try:
            # Encontrar variáveis no formato {{variable}}
            import re
            variables = re.findall(r'\{\{(\w+)\}\}', content)
            validation_result["variables_found"] = list(set(variables))
            
            # Validações básicas
            if len(content.strip()) < 10:
                validation_result["warnings"].append("Prompt muito curto (< 10 caracteres)")
            
            if len(content) > 10000:
                validation_result["warnings"].append("Prompt muito longo (> 10000 caracteres)")
            
            # Verificar variáveis não fechadas
            open_braces = content.count('{{')
            close_braces = content.count('}}')
            
            if open_braces != close_braces:
                validation_result["errors"].append("Variáveis mal formadas - chaves não balanceadas")
                validation_result["valid"] = False
            
            # Estatísticas
            validation_result["statistics"] = {
                "character_count": len(content),
                "word_count": len(content.split()),
                "line_count": len(content.split('\n')),
                "variable_count": len(validation_result["variables_found"])
            }
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Erro na validação: {str(e)}")
        
        return validation_result
    
    async def generate_prompt_preview(
        self,
        content: str,
        sample_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gerar preview do prompt com dados de exemplo"""
        try:
            # Substituir variáveis com dados de exemplo
            preview_content = content
            
            for key, value in sample_data.items():
                placeholder = f"{{{{{key}}}}}"
                preview_content = preview_content.replace(placeholder, str(value))
            
            # Verificar variáveis não substituídas
            import re
            unresolved_vars = re.findall(r'\{\{(\w+)\}\}', preview_content)
            
            return {
                "preview_content": preview_content,
                "unresolved_variables": unresolved_vars,
                "sample_data_used": sample_data,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to generate prompt preview", error=str(e))
            raise
    
    async def get_prompt_analytics(self, prompt_id: str) -> Dict[str, Any]:
        """Obter analytics de uso do prompt"""
        if prompt_id not in self.prompts:
            raise ValueError(f"Prompt {prompt_id} not found")
        
        versions = self.prompts[prompt_id]
        
        # Calcular estatísticas
        total_versions = len(versions)
        approved_versions = len([v for v in versions.values() if v.status == PromptStatus.APPROVED])
        
        # Simular métricas de performance
        analytics = {
            "prompt_id": prompt_id,
            "total_versions": total_versions,
            "approved_versions": approved_versions,
            "latest_version": max(versions.keys(), key=lambda v: tuple(map(int, v.split('.')))),
            "creation_timeline": [
                {
                    "version": v.version_number,
                    "created_at": v.created_at.isoformat(),
                    "status": v.status.value
                }
                for v in sorted(versions.values(), key=lambda x: x.created_at)
            ],
            "performance_metrics": {
                "avg_execution_time_ms": 1500,  # Simulado
                "success_rate": 0.95,
                "usage_count": 150,
                "last_used": datetime.utcnow().isoformat()
            }
        }
        
        return analytics

# Instância global do serviço
prompt_editor_service = PromptEditorService()   
 
    async def list_templates(
        self,
        category: Optional[PromptCategory] = None,
        status: Optional[PromptStatus] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PromptTemplate]:
        """Listar templates com filtros"""
        try:
            templates = list(self.templates.values())
            
            # Incluir templates da biblioteca
            templates.extend(list(self.template_library.values()))
            
            # Aplicar filtros
            if category:
                templates = [t for t in templates if t.category == category]
            
            if status:
                templates = [t for t in templates if t.status == status]
            
            if tags:
                templates = [t for t in templates if any(tag in t.tags for tag in tags)]
            
            if search:
                search_lower = search.lower()
                templates = [
                    t for t in templates 
                    if search_lower in t.name.lower() 
                    or search_lower in t.description.lower()
                    or any(search_lower in tag.lower() for tag in t.tags)
                ]
            
            # Ordenar por data de atualização (mais recente primeiro)
            templates.sort(key=lambda x: x.updated_at, reverse=True)
            
            # Aplicar paginação
            return templates[offset:offset + limit]
            
        except Exception as e:
            logger.error("Failed to list templates", error=str(e))
            raise
    
    async def delete_template(self, template_id: str, deleted_by: str) -> bool:
        """Deletar template"""
        try:
            if template_id not in self.templates:
                raise ValueError(f"Template {template_id} not found")
            
            template = self.templates[template_id]
            
            # Não permitir deletar templates em uso
            if template.usage_count > 0:
                raise ValueError("Cannot delete template with usage history. Consider deprecating instead.")
            
            # Remover template e versões
            del self.templates[template_id]
            if template_id in self.versions:
                del self.versions[template_id]
            if template_id in self.test_results:
                del self.test_results[template_id]
            
            logger.info(
                "Prompt template deleted",
                template_id=template_id,
                deleted_by=deleted_by
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to delete template", template_id=template_id, error=str(e))
            raise
    
    async def get_template_versions(self, template_id: str) -> List[PromptVersion]:
        """Obter versões de um template"""
        try:
            if template_id not in self.templates:
                raise ValueError(f"Template {template_id} not found")
            
            return self.versions.get(template_id, [])
            
        except Exception as e:
            logger.error("Failed to get template versions", template_id=template_id, error=str(e))
            raise
    
    async def get_template_test_results(
        self,
        template_id: str,
        limit: int = 20
    ) -> List[PromptTestResult]:
        """Obter resultados de teste de um template"""
        try:
            if template_id not in self.templates:
                raise ValueError(f"Template {template_id} not found")
            
            results = self.test_results.get(template_id, [])
            
            # Ordenar por data de teste (mais recente primeiro)
            results.sort(key=lambda x: x.tested_at, reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error("Failed to get test results", template_id=template_id, error=str(e))
            raise
    
    async def clone_template(
        self,
        template_id: str,
        new_name: str,
        created_by: str,
        modifications: Optional[Dict[str, Any]] = None
    ) -> PromptTemplate:
        """Clonar template existente"""
        try:
            # Buscar template original
            original = None
            if template_id in self.templates:
                original = self.templates[template_id]
            elif template_id in self.template_library:
                original = self.template_library[template_id]
            else:
                raise ValueError(f"Template {template_id} not found")
            
            # Criar novo template baseado no original
            new_template_id = str(uuid4())
            
            cloned_template = PromptTemplate(
                template_id=new_template_id,
                name=new_name,
                description=f"Clonado de: {original.name}",
                category=original.category,
                type=original.type,
                content=original.content,
                variables=original.variables.copy(),
                tags=original.tags.copy(),
                version="1.0.0",
                status=PromptStatus.DRAFT,
                created_by=created_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={
                    "cloned_from": template_id,
                    "original_name": original.name
                }
            )
            
            # Aplicar modificações se fornecidas
            if modifications:
                if 'description' in modifications:
                    cloned_template.description = modifications['description']
                if 'content' in modifications:
                    cloned_template.content = modifications['content']
                if 'variables' in modifications:
                    cloned_template.variables = [
                        PromptVariable(**var) if isinstance(var, dict) else var 
                        for var in modifications['variables']
                    ]
                if 'tags' in modifications:
                    cloned_template.tags = modifications['tags']
            
            self.templates[new_template_id] = cloned_template
            self.versions[new_template_id] = []
            
            logger.info(
                "Template cloned",
                original_id=template_id,
                new_id=new_template_id,
                created_by=created_by
            )
            
            return cloned_template
            
        except Exception as e:
            logger.error("Failed to clone template", template_id=template_id, error=str(e))
            raise
    
    async def export_template(self, template_id: str) -> Dict[str, Any]:
        """Exportar template para JSON"""
        try:
            template = await self.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Converter para dict serializável
            template_dict = asdict(template)
            
            # Converter datetime para string
            template_dict['created_at'] = template.created_at.isoformat()
            template_dict['updated_at'] = template.updated_at.isoformat()
            
            # Incluir versões
            versions = await self.get_template_versions(template_id)
            template_dict['versions'] = [
                {
                    **asdict(version),
                    'created_at': version.created_at.isoformat()
                }
                for version in versions
            ]
            
            return template_dict
            
        except Exception as e:
            logger.error("Failed to export template", template_id=template_id, error=str(e))
            raise
    
    async def import_template(
        self,
        template_data: Dict[str, Any],
        imported_by: str,
        overwrite: bool = False
    ) -> PromptTemplate:
        """Importar template de JSON"""
        try:
            # Validar dados obrigatórios
            required_fields = ['name', 'description', 'category', 'type', 'content', 'variables']
            for field in required_fields:
                if field not in template_data:
                    raise ValueError(f"Campo obrigatório '{field}' não encontrado")
            
            # Verificar se template já existe
            template_id = template_data.get('template_id', str(uuid4()))
            if template_id in self.templates and not overwrite:
                raise ValueError(f"Template {template_id} já existe. Use overwrite=True para sobrescrever.")
            
            # Converter variáveis
            variables = [
                PromptVariable(**var) if isinstance(var, dict) else var
                for var in template_data['variables']
            ]
            
            # Criar template
            template = PromptTemplate(
                template_id=template_id,
                name=template_data['name'],
                description=template_data['description'],
                category=PromptCategory(template_data['category']),
                type=PromptType(template_data['type']),
                content=template_data['content'],
                variables=variables,
                tags=template_data.get('tags', []),
                version=template_data.get('version', '1.0.0'),
                status=PromptStatus(template_data.get('status', 'draft')),
                created_by=imported_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=template_data.get('metadata', {})
            )
            
            self.templates[template_id] = template
            if template_id not in self.versions:
                self.versions[template_id] = []
            
            logger.info(
                "Template imported",
                template_id=template_id,
                imported_by=imported_by,
                overwrite=overwrite
            )
            
            return template
            
        except Exception as e:
            logger.error("Failed to import template", error=str(e))
            raise
    
    async def get_template_analytics(self, template_id: str) -> Dict[str, Any]:
        """Obter analytics de um template"""
        try:
            template = await self.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            test_results = await self.get_template_test_results(template_id)
            versions = await self.get_template_versions(template_id)
            
            # Calcular métricas
            total_tests = len(test_results)
            successful_tests = len([r for r in test_results if r.success])
            success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
            
            avg_execution_time = 0
            if test_results:
                avg_execution_time = sum(r.execution_time_ms for r in test_results) / len(test_results)
            
            # Análise de uso por período
            usage_by_day = {}
            for result in test_results:
                day = result.tested_at.date().isoformat()
                usage_by_day[day] = usage_by_day.get(day, 0) + 1
            
            return {
                'template_id': template_id,
                'template_name': template.name,
                'total_usage': template.usage_count,
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': success_rate,
                'avg_execution_time_ms': avg_execution_time,
                'total_versions': len(versions),
                'current_version': template.version,
                'rating': template.rating,
                'usage_by_day': usage_by_day,
                'last_used': test_results[0].tested_at.isoformat() if test_results else None,
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get template analytics", template_id=template_id, error=str(e))
            raise
    
    def _validate_prompt_content(
        self,
        content: str,
        variables: List[PromptVariable]
    ) -> Dict[str, Any]:
        """Validar conteúdo do prompt"""
        errors = []
        warnings = []
        
        # Extrair variáveis do conteúdo
        import re
        content_variables = set(re.findall(r'\{\{(\w+)\}\}', content))
        
        # Verificar variáveis definidas mas não usadas
        defined_variables = set(var.name for var in variables)
        unused_variables = defined_variables - content_variables
        if unused_variables:
            warnings.append(f"Variáveis definidas mas não usadas: {', '.join(unused_variables)}")
        
        # Verificar variáveis usadas mas não definidas
        undefined_variables = content_variables - defined_variables
        if undefined_variables:
            errors.append(f"Variáveis usadas mas não definidas: {', '.join(undefined_variables)}")
        
        # Verificar tamanho do conteúdo
        if len(content) < 10:
            errors.append("Conteúdo muito curto (mínimo 10 caracteres)")
        
        if len(content) > 10000:
            warnings.append("Conteúdo muito longo (máximo recomendado: 10000 caracteres)")
        
        # Verificar variáveis obrigatórias sem valor padrão
        required_without_default = [
            var.name for var in variables 
            if var.required and var.default_value is None
        ]
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'content_variables': list(content_variables),
            'defined_variables': list(defined_variables),
            'required_variables': required_without_default
        }
    
    def _validate_variables(
        self,
        template_variables: List[PromptVariable],
        provided_variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validar variáveis fornecidas"""
        errors = []
        warnings = []
        
        # Verificar variáveis obrigatórias
        for var in template_variables:
            if var.required and var.name not in provided_variables:
                if var.default_value is None:
                    errors.append(f"Variável obrigatória '{var.name}' não fornecida")
        
        # Validar tipos e valores
        for var in template_variables:
            if var.name in provided_variables:
                value = provided_variables[var.name]
                
                # Validar tipo
                if var.type == 'string' and not isinstance(value, str):
                    errors.append(f"Variável '{var.name}' deve ser string")
                elif var.type == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"Variável '{var.name}' deve ser número")
                elif var.type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Variável '{var.name}' deve ser boolean")
                
                # Validar comprimento para strings
                if var.type == 'string' and isinstance(value, str):
                    if var.min_length and len(value) < var.min_length:
                        errors.append(f"Variável '{var.name}' muito curta (mínimo {var.min_length})")
                    if var.max_length and len(value) > var.max_length:
                        errors.append(f"Variável '{var.name}' muito longa (máximo {var.max_length})")
                
                # Validar padrão regex
                if var.validation_pattern and isinstance(value, str):
                    import re
                    if not re.match(var.validation_pattern, value):
                        errors.append(f"Variável '{var.name}' não atende ao padrão exigido")
                
                # Validar opções
                if var.options and value not in var.options:
                    errors.append(f"Variável '{var.name}' deve ser uma das opções: {', '.join(var.options)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _render_template_content(self, content: str, variables: Dict[str, Any]) -> str:
        """Renderizar conteúdo do template com variáveis"""
        try:
            # Substituir variáveis no formato {{variable}}
            import re
            
            def replace_variable(match):
                var_name = match.group(1)
                if var_name in variables:
                    return str(variables[var_name])
                else:
                    return match.group(0)  # Manter original se não encontrada
            
            rendered = re.sub(r'\{\{(\w+)\}\}', replace_variable, content)
            
            return rendered
            
        except Exception as e:
            logger.error("Failed to render template content", error=str(e))
            raise
    
    async def _create_version(
        self,
        template_id: str,
        changelog: str,
        created_by: str
    ) -> PromptVersion:
        """Criar nova versão do template"""
        try:
            template = self.templates[template_id]
            
            # Gerar ID da versão
            version_id = str(uuid4())
            
            # Criar versão
            version = PromptVersion(
                version_id=version_id,
                template_id=template_id,
                version_number=template.version,
                content=template.content,
                variables=template.variables.copy(),
                changelog=changelog,
                created_by=created_by,
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            # Desativar versões anteriores
            for existing_version in self.versions.get(template_id, []):
                existing_version.is_active = False
            
            # Adicionar nova versão
            if template_id not in self.versions:
                self.versions[template_id] = []
            
            self.versions[template_id].append(version)
            
            return version
            
        except Exception as e:
            logger.error("Failed to create version", template_id=template_id, error=str(e))
            raise
    
    def _get_template_version(self, template_id: str, version: str) -> Optional[PromptVersion]:
        """Obter versão específica do template"""
        versions = self.versions.get(template_id, [])
        for v in versions:
            if v.version_number == version:
                return v
        return None

# Instância global do serviço
prompt_editor_service = PromptEditorService() 
       ] = None,
        status: Optional[PromptStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PromptTemplate]:
        """Listar templates com filtros"""
        try:
            filtered_templates = []
            
            for template in self.templates.values():
                # Aplicar filtros
                if category and template.category != category:
                    continue
                if status and template.status != status:
                    continue
                if tags:
                    if not any(tag in template.tags for tag in tags):
                        continue
                
                filtered_templates.append(template)
            
            # Ordenar por data de atualização (mais recente primeiro)
            filtered_templates.sort(key=lambda x: x.updated_at, reverse=True)
            
            # Aplicar paginação
            return filtered_templates[offset:offset + limit]
            
        except Exception as e:
            logger.error("Failed to list templates", error=str(e))
            raise
    
    async def delete_template(self, template_id: str, deleted_by: str) -> bool:
        """Deletar template"""
        try:
            if template_id not in self.templates:
                return False
            
            template = self.templates[template_id]
            
            # Verificar se pode ser deletado
            if template.status == PromptStatus.ACTIVE:
                raise ValueError("Cannot delete active template. Deprecate it first.")
            
            # Remover template e versões
            del self.templates[template_id]
            if template_id in self.versions:
                del self.versions[template_id]
            if template_id in self.test_results:
                del self.test_results[template_id]
            
            logger.info(
                "Prompt template deleted",
                template_id=template_id,
                deleted_by=deleted_by
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to delete template", template_id=template_id, error=str(e))
            raise
    
    async def get_template_versions(self, template_id: str) -> List[PromptVersion]:
        """Obter versões de um template"""
        return self.versions.get(template_id, [])
    
    async def get_template_test_results(
        self,
        template_id: str,
        limit: int = 50
    ) -> List[PromptTestResult]:
        """Obter resultados de teste de um template"""
        results = self.test_results.get(template_id, [])
        return sorted(results, key=lambda x: x.tested_at, reverse=True)[:limit]
    
    async def export_template(self, template_id: str) -> Dict[str, Any]:
        """Exportar template para JSON"""
        try:
            if template_id not in self.templates:
                raise ValueError(f"Template {template_id} not found")
            
            template = self.templates[template_id]
            versions = self.versions.get(template_id, [])
            
            export_data = {
                "template": asdict(template),
                "versions": [asdict(version) for version in versions],
                "exported_at": datetime.utcnow().isoformat(),
                "export_version": "1.0"
            }
            
            # Converter datetime objects para strings
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
            
            return convert_datetime(export_data)
            
        except Exception as e:
            logger.error("Failed to export template", template_id=template_id, error=str(e))
            raise
    
    async def import_template(
        self,
        import_data: Dict[str, Any],
        imported_by: str
    ) -> PromptTemplate:
        """Importar template de JSON"""
        try:
            template_data = import_data["template"]
            
            # Gerar novo ID para evitar conflitos
            new_template_id = str(uuid4())
            
            # Converter strings de volta para datetime
            def convert_strings_to_datetime(obj):
                if isinstance(obj, dict):
                    result = {}
                    for k, v in obj.items():
                        if k.endswith('_at') and isinstance(v, str):
                            try:
                                result[k] = datetime.fromisoformat(v.replace('Z', '+00:00'))
                            except:
                                result[k] = datetime.utcnow()
                        else:
                            result[k] = convert_strings_to_datetime(v)
                    return result
                elif isinstance(obj, list):
                    return [convert_strings_to_datetime(item) for item in obj]
                return obj
            
            template_data = convert_strings_to_datetime(template_data)
            
            # Criar template importado
            template = PromptTemplate(
                template_id=new_template_id,
                name=f"{template_data['name']} (Imported)",
                description=template_data['description'],
                category=PromptCategory(template_data['category']),
                type=PromptType(template_data['type']),
                content=template_data['content'],
                variables=[PromptVariable(**var) for var in template_data['variables']],
                tags=template_data['tags'] + ['imported'],
                version="1.0.0",
                status=PromptStatus.DRAFT,
                created_by=imported_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=template_data.get('metadata', {})
            )
            
            self.templates[new_template_id] = template
            self.versions[new_template_id] = []
            
            logger.info(
                "Template imported",
                template_id=new_template_id,
                original_name=template_data['name'],
                imported_by=imported_by
            )
            
            return template
            
        except Exception as e:
            logger.error("Failed to import template", error=str(e))
            raise
    
    def _validate_prompt_content(
        self,
        content: str,
        variables: List[PromptVariable]
    ) -> Dict[str, Any]:
        """Validar conteúdo do prompt"""
        errors = []
        warnings = []
        
        # Extrair variáveis do conteúdo
        import re
        content_variables = set(re.findall(r'\{\{(\w+)\}\}', content))
        
        # Verificar variáveis definidas
        defined_variables = {var.name for var in variables}
        
        # Variáveis não definidas
        undefined_vars = content_variables - defined_variables
        if undefined_vars:
            errors.append(f"Undefined variables in content: {', '.join(undefined_vars)}")
        
        # Variáveis definidas mas não usadas
        unused_vars = defined_variables - content_variables
        if unused_vars:
            warnings.append(f"Defined but unused variables: {', '.join(unused_vars)}")
        
        # Verificar tamanho do conteúdo
        if len(content) > 10000:
            warnings.append("Content is very long (>10k chars), consider splitting")
        
        # Verificar variáveis obrigatórias sem valor padrão
        required_without_default = [
            var.name for var in variables 
            if var.required and var.default_value is None
        ]
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'content_variables': list(content_variables),
            'defined_variables': list(defined_variables),
            'required_variables': required_without_default
        }
    
    def _validate_variables(
        self,
        template_variables: List[PromptVariable],
        provided_variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validar variáveis fornecidas"""
        errors = []
        warnings = []
        
        for var in template_variables:
            if var.required and var.name not in provided_variables:
                if var.default_value is None:
                    errors.append(f"Required variable '{var.name}' is missing")
                else:
                    warnings.append(f"Using default value for '{var.name}': {var.default_value}")
            
            if var.name in provided_variables:
                value = provided_variables[var.name]
                
                # Validar tipo
                if var.type == "string" and not isinstance(value, str):
                    errors.append(f"Variable '{var.name}' must be a string")
                elif var.type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Variable '{var.name}' must be a number")
                elif var.type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Variable '{var.name}' must be a boolean")
                
                # Validar comprimento para strings
                if var.type == "string" and isinstance(value, str):
                    if var.min_length and len(value) < var.min_length:
                        errors.append(f"Variable '{var.name}' is too short (min: {var.min_length})")
                    if var.max_length and len(value) > var.max_length:
                        errors.append(f"Variable '{var.name}' is too long (max: {var.max_length})")
                
                # Validar padrão regex
                if var.validation_pattern and isinstance(value, str):
                    if not re.match(var.validation_pattern, value):
                        errors.append(f"Variable '{var.name}' doesn't match required pattern")
                
                # Validar opções
                if var.options and value not in var.options:
                    errors.append(f"Variable '{var.name}' must be one of: {', '.join(var.options)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _render_template_content(
        self,
        content: str,
        variables: Dict[str, Any]
    ) -> str:
        """Renderizar conteúdo do template com variáveis"""
        try:
            # Usar template engine simples
            rendered = content
            
            for var_name, var_value in variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                rendered = rendered.replace(placeholder, str(var_value))
            
            return rendered
            
        except Exception as e:
            logger.error("Failed to render template content", error=str(e))
            raise
    
    async def _create_version(
        self,
        template_id: str,
        changelog: str,
        created_by: str
    ) -> PromptVersion:
        """Criar nova versão do template"""
        try:
            template = self.templates[template_id]
            
            version = PromptVersion(
                version_id=str(uuid4()),
                template_id=template_id,
                version_number=template.version,
                content=template.content,
                variables=template.variables.copy(),
                changelog=changelog,
                created_by=created_by,
                created_at=datetime.utcnow(),
                is_active=False
            )
            
            if template_id not in self.versions:
                self.versions[template_id] = []
            
            self.versions[template_id].append(version)
            
            return version
            
        except Exception as e:
            logger.error("Failed to create version", template_id=template_id, error=str(e))
            raise
    
    def _get_template_version(
        self,
        template_id: str,
        version_number: str
    ) -> Optional[PromptVersion]:
        """Obter versão específica do template"""
        versions = self.versions.get(template_id, [])
        for version in versions:
            if version.version_number == version_number:
                return version
        return None

# Instância global do serviço
prompt_editor_service = PromptEditorService()