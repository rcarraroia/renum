# Convenções de Código

## Padrões de Desenvolvimento

### Estrutura de Arquivos
- **Serviços**: Terminam com `_service.py` (ex: `agent_registry_service.py`)
- **Repositórios**: Terminam com `_repository.py` (ex: `agent_repository.py`)
- **Schemas**: Agrupados por domínio em `app/schemas/` (ex: `agent.py`, `integration.py`)
- **Testes**: Prefixo `test_` (ex: `test_agent_registry.py`)

### Nomenclatura de Classes e Métodos

#### Serviços
```python
class AgentRegistryService:
    async def create_agent(self, agent_data: CreateAgentSchema) -> Agent:
        """Criar novo agente com versionamento."""
        pass
    
    async def get_available_agents(self, filters: Optional[Dict]) -> List[Agent]:
        """Obter agentes disponíveis com filtros opcionais."""
        pass
```

#### Repositórios
```python
class AgentRepository:
    async def save(self, agent: Agent) -> Agent:
        """Salvar agente no banco de dados."""
        pass
    
    async def find_by_id(self, agent_id: UUID) -> Optional[Agent]:
        """Buscar agente por ID."""
        pass
```

### Schemas Pydantic

#### Convenções de Naming
- **Create**: `CreateXxxSchema` (ex: `CreateAgentSchema`)
- **Update**: `UpdateXxxSchema` (ex: `UpdateAgentSchema`)
- **Response**: `XxxResponse` (ex: `AgentResponse`)
- **Request**: `XxxRequest` (ex: `AgentExecutionRequest`)

#### Exemplo de Schema
```python
class CreateAgentSchema(BaseModel):
    """Schema para criação de agente."""
    
    agent_id: str = Field(..., description="ID único do agente")
    version: str = Field(..., description="Versão semântica")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    capabilities: List[AgentCapabilitySchema]
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "sa-email-basic",
                "version": "1.0.0",
                "name": "Basic Email Agent",
                "description": "Send emails via SMTP or API"
            }
        }
```

### Tratamento de Erros

#### HTTPException para APIs
```python
from fastapi import HTTPException

# Erro de validação
raise HTTPException(
    status_code=400, 
    detail="Dados de entrada inválidos"
)

# Recurso não encontrado
raise HTTPException(
    status_code=404, 
    detail=f"Agente {agent_id} não encontrado"
)

# Erro de autorização
raise HTTPException(
    status_code=403, 
    detail="Acesso negado"
)
```

#### Logging Estruturado
```python
import structlog

logger = structlog.get_logger(__name__)

async def create_agent(self, agent_data: CreateAgentSchema) -> Agent:
    logger.info(
        "Criando novo agente",
        agent_id=agent_data.agent_id,
        version=agent_data.version
    )
    
    try:
        # Lógica de criação
        pass
    except Exception as e:
        logger.error(
            "Erro ao criar agente",
            agent_id=agent_data.agent_id,
            error=str(e)
        )
        raise
```

### Validações de Domínio

#### Entidades de Domínio
```python
class Agent:
    def _validate(self):
        """Validar regras de negócio da entidade."""
        if not self.capabilities:
            raise ValueError("Agente deve ter pelo menos uma capacidade")
        
        if not self._is_valid_semantic_version(self.version):
            raise ValueError(f"Versão inválida: {self.version}")
    
    def approve(self, approved_by: UUID):
        """Aprovar agente para uso em produção."""
        if self.status != 'draft':
            raise ValueError("Apenas agentes em draft podem ser aprovados")
        
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()
```

### Testes

#### Estrutura de Testes
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestAgentRegistryService:
    @pytest.fixture
    def service(self):
        """Fixture do serviço com mocks."""
        db_mock = AsyncMock()
        return AgentRegistryService(db_connection=db_mock)
    
    @pytest.mark.asyncio
    async def test_create_agent_success(self, service):
        """Teste de criação de agente com sucesso."""
        # Arrange
        agent_data = CreateAgentSchema(
            agent_id="test-agent",
            version="1.0.0",
            name="Test Agent",
            description="Agent for testing"
        )
        
        # Act
        result = await service.create_agent(agent_data, user_id=uuid4())
        
        # Assert
        assert result.agent_id == "test-agent"
        assert result.status == "draft"
    
    @pytest.mark.asyncio
    async def test_create_agent_duplicate_fails(self, service):
        """Teste de falha ao criar agente duplicado."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="já existe"):
            await service.create_agent(duplicate_data, user_id=uuid4())
```

### Documentação de API

#### Docstrings para Endpoints
```python
@router.post("/agents", response_model=AgentResponse)
async def create_agent(
    agent_data: CreateAgentSchema,
    current_user: User = Depends(get_current_user)
):
    """
    Criar novo agente no registro.
    
    - **agent_id**: ID único do agente (formato: sa-nome-versao)
    - **version**: Versão semântica (ex: 1.0.0)
    - **name**: Nome descritivo do agente
    - **description**: Descrição das funcionalidades
    - **capabilities**: Lista de capacidades do agente
    
    Retorna o agente criado com status 'draft'.
    """
    pass
```

### Configurações

#### Variáveis de Ambiente
```python
class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    # API Configuration
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # Database
    SUPABASE_URL: str = Field(..., description="URL do projeto Supabase")
    SUPABASE_ANON_KEY: str = Field(..., description="Chave anônima do Supabase")
    
    # External Services
    SUNA_API_URL: str = Field(
        default="http://157.180.39.41:8000/api",
        description="URL da API do Suna Backend"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

### Integrações Externas

#### Cliente HTTP
```python
import httpx

class SunaClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0
        )
    
    async def execute_agent(self, agent_id: str, inputs: Dict) -> Dict:
        """Executar agente no Suna Backend."""
        try:
            response = await self._client.post(
                "/agents/execute",
                json={"agent_id": agent_id, "inputs": inputs}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Erro na comunicação com Suna", error=str(e))
            raise
```

## Padrões de Commit

### Mensagens de Commit
- **feat**: Nova funcionalidade
- **fix**: Correção de bug
- **docs**: Documentação
- **style**: Formatação de código
- **refactor**: Refatoração
- **test**: Testes
- **chore**: Tarefas de manutenção

Exemplo: `feat: adicionar endpoint de criação de agentes`

### Pull Requests
- Título descritivo em português
- Descrição detalhada das mudanças
- Testes incluídos para novas funcionalidades
- Documentação atualizada quando necessário