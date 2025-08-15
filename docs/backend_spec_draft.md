# Especificação do Renum API v1 - Draft

## Visão Geral

Esta especificação define os endpoints mínimos necessários para a v1 do Renum API, baseada na análise do sistema legado e nos requisitos de negócio identificados.

## Arquitetura Proposta

### Estrutura de Diretórios
```
apps/api/
├── app/
│   ├── core/           # Configurações e utilitários centrais
│   ├── common/         # Código compartilhado
│   ├── domain/         # Entidades de negócio
│   ├── usecases/       # Casos de uso (business logic)
│   ├── infra/          # Infraestrutura e integrações
│   │   ├── db/         # Configuração de banco
│   │   ├── suna/       # Cliente Suna Backend
│   │   ├── supabase/   # Cliente Supabase
│   │   └── websocket/  # Gerenciador WebSocket
│   ├── api/            # Camada de apresentação
│   │   └── v1/         # Endpoints v1
│   ├── schemas/        # Schemas Pydantic
│   └── main.py         # Aplicação principal
├── alembic/            # Migrações de banco
├── pyproject.toml      # Configuração do projeto
└── Dockerfile          # Container
```

## Endpoints Mínimos v1

### 1. **Health & Status**

#### `GET /health`
**Descrição**: Verificação básica de saúde da aplicação
**Response**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2025-08-15T11:18:00Z"
}
```

#### `GET /health/services`
**Descrição**: Verificação detalhada de todos os serviços
**Response**:
```json
{
  "status": "ok",
  "services": {
    "database": {"status": "healthy", "latency_ms": 12},
    "suna_backend": {"status": "healthy", "latency_ms": 45},
    "websocket": {"status": "healthy", "connections": 23}
  }
}
```

### 2. **Autenticação**

#### `POST /api/v1/auth/login`
**Descrição**: Autenticação de usuário
**Request**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

#### `POST /api/v1/auth/refresh`
**Descrição**: Renovação de token
**Headers**: `Authorization: Bearer <refresh_token>`
**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_in": 3600
}
```

### 3. **Teams Management**

#### `GET /api/v1/teams`
**Descrição**: Listar equipes do usuário
**Query Params**: 
- `page` (int, default=1)
- `limit` (int, default=10)
- `search` (string, optional)

**Response**:
```json
{
  "teams": [
    {
      "id": "uuid",
      "name": "Marketing Team",
      "description": "Team for marketing automation",
      "workflow_type": "sequential",
      "created_at": "2025-08-15T10:00:00Z",
      "updated_at": "2025-08-15T10:00:00Z",
      "agents_count": 3,
      "status": "active"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 25,
    "pages": 3
  }
}
```

#### `POST /api/v1/teams`
**Descrição**: Criar nova equipe
**Request**:
```json
{
  "name": "Marketing Team",
  "description": "Team for marketing automation",
  "workflow_type": "sequential",
  "agents": [
    {
      "agent_id": "suna_agent_uuid",
      "role": "leader",
      "order": 1,
      "config": {
        "input_source": "initial_prompt",
        "conditions": []
      }
    }
  ]
}
```
**Response**:
```json
{
  "id": "uuid",
  "name": "Marketing Team",
  "description": "Team for marketing automation",
  "workflow_type": "sequential",
  "created_at": "2025-08-15T10:00:00Z",
  "agents": [...],
  "status": "active"
}
```

#### `GET /api/v1/teams/{team_id}`
**Descrição**: Obter detalhes de uma equipe
**Response**:
```json
{
  "id": "uuid",
  "name": "Marketing Team",
  "description": "Team for marketing automation",
  "workflow_type": "sequential",
  "agents": [
    {
      "id": "uuid",
      "agent_id": "suna_agent_uuid",
      "role": "leader",
      "order": 1,
      "config": {...},
      "agent_details": {
        "name": "Content Creator",
        "description": "Creates marketing content"
      }
    }
  ],
  "created_at": "2025-08-15T10:00:00Z",
  "updated_at": "2025-08-15T10:00:00Z",
  "status": "active"
}
```

#### `PUT /api/v1/teams/{team_id}`
**Descrição**: Atualizar equipe
**Request**: Similar ao POST, campos opcionais
**Response**: Equipe atualizada

#### `DELETE /api/v1/teams/{team_id}`
**Descrição**: Excluir equipe
**Response**: `204 No Content`

### 4. **Team Executions**

#### `POST /api/v1/teams/{team_id}/execute`
**Descrição**: Iniciar execução de equipe
**Request**:
```json
{
  "input_data": {
    "prompt": "Create a marketing campaign for product X",
    "context": {
      "product": "Product X",
      "target_audience": "Young professionals"
    }
  },
  "execution_config": {
    "timeout_minutes": 30,
    "parallel_limit": 3,
    "retry_failed": true
  }
}
```
**Response**:
```json
{
  "execution_id": "uuid",
  "team_id": "uuid",
  "status": "running",
  "started_at": "2025-08-15T11:00:00Z",
  "estimated_completion": "2025-08-15T11:30:00Z",
  "progress": {
    "completed_agents": 0,
    "total_agents": 3,
    "current_step": "Initializing agents"
  }
}
```

#### `GET /api/v1/executions/{execution_id}`
**Descrição**: Obter status de execução
**Response**:
```json
{
  "execution_id": "uuid",
  "team_id": "uuid",
  "status": "running",
  "started_at": "2025-08-15T11:00:00Z",
  "completed_at": null,
  "progress": {
    "completed_agents": 1,
    "total_agents": 3,
    "current_step": "Agent 2 processing"
  },
  "results": [
    {
      "agent_id": "uuid",
      "status": "completed",
      "output": "Generated marketing copy...",
      "execution_time_ms": 15000,
      "completed_at": "2025-08-15T11:15:00Z"
    }
  ],
  "logs": [
    {
      "timestamp": "2025-08-15T11:00:00Z",
      "level": "info",
      "message": "Execution started",
      "agent_id": null
    }
  ]
}
```

#### `POST /api/v1/executions/{execution_id}/cancel`
**Descrição**: Cancelar execução
**Response**:
```json
{
  "execution_id": "uuid",
  "status": "cancelled",
  "cancelled_at": "2025-08-15T11:20:00Z"
}
```

#### `GET /api/v1/executions`
**Descrição**: Listar execuções do usuário
**Query Params**:
- `team_id` (uuid, optional)
- `status` (string, optional)
- `page`, `limit`

**Response**:
```json
{
  "executions": [...],
  "pagination": {...}
}
```

### 5. **Agents (Proxy para Suna)**

#### `GET /api/v1/agents`
**Descrição**: Listar agentes disponíveis (proxy para Suna)
**Response**:
```json
{
  "agents": [
    {
      "id": "uuid",
      "name": "Content Creator",
      "description": "Creates marketing content",
      "category": "marketing",
      "capabilities": ["text_generation", "image_analysis"],
      "available": true
    }
  ]
}
```

#### `GET /api/v1/agents/{agent_id}`
**Descrição**: Detalhes do agente (proxy para Suna)

### 6. **Notifications**

#### `GET /api/v1/notifications`
**Descrição**: Listar notificações do usuário
**Response**:
```json
{
  "notifications": [
    {
      "id": "uuid",
      "type": "execution_completed",
      "title": "Team execution completed",
      "message": "Your Marketing Team execution has completed successfully",
      "read": false,
      "created_at": "2025-08-15T11:30:00Z",
      "data": {
        "execution_id": "uuid",
        "team_id": "uuid"
      }
    }
  ]
}
```

#### `PUT /api/v1/notifications/{notification_id}/read`
**Descrição**: Marcar notificação como lida

### 7. **WebSocket**

#### `WS /api/v1/ws`
**Descrição**: Conexão WebSocket para atualizações em tempo real
**Eventos**:
- `execution_status_update`
- `agent_completed`
- `new_notification`
- `team_updated`

**Exemplo de mensagem**:
```json
{
  "type": "execution_status_update",
  "data": {
    "execution_id": "uuid",
    "status": "running",
    "progress": {
      "completed_agents": 2,
      "total_agents": 3
    }
  }
}
```

## Integração com Suna Backend

### Configuração
```python
# infra/suna/client.py
SUNA_API_URL = "http://157.180.39.41:8000/api"
SUNA_WS_URL = "ws://157.180.39.41:8000/ws"
```

### Endpoints Proxy Necessários
- `GET /agents` → `{SUNA_API_URL}/agents`
- `POST /agents/{id}/execute` → `{SUNA_API_URL}/agents/{id}/execute`
- `GET /executions/{id}` → `{SUNA_API_URL}/executions/{id}`

## Modelos de Dados Principais

### Team
```python
class Team(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    workflow_type: WorkflowType
    user_id: UUID
    agents: List[TeamAgent]
    created_at: datetime
    updated_at: datetime
    status: TeamStatus
```

### TeamExecution
```python
class TeamExecution(BaseModel):
    id: UUID
    team_id: UUID
    user_id: UUID
    status: ExecutionStatus
    input_data: Dict[str, Any]
    results: List[AgentResult]
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
```

### AgentResult
```python
class AgentResult(BaseModel):
    agent_id: UUID
    status: ExecutionStatus
    output: Optional[str]
    error_message: Optional[str]
    execution_time_ms: int
    started_at: datetime
    completed_at: Optional[datetime]
```

## Configurações de Ambiente

### Variáveis Obrigatórias
```env
# Suna Integration
SUNA_API_URL=http://157.180.39.41:8000/api
SUNA_WS_URL=ws://157.180.39.41:8000/ws
SUNA_API_KEY=<suna_api_key>

# Supabase
SUPABASE_URL=<supabase_url>
SUPABASE_ANON_KEY=<supabase_anon_key>
SUPABASE_SERVICE_KEY=<supabase_service_key>

# JWT
JWT_SECRET_KEY=<jwt_secret>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Application
API_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000"]
DEBUG=false
```

## Gaps e Questões Técnicas

### 1. **Autenticação Suna**
- **Questão**: Como autenticar com Suna Backend?
- **Solução Proposta**: API Key ou JWT forwarding

### 2. **Rate Limiting**
- **Questão**: Limites de execução simultânea
- **Solução Proposta**: Redis para controle de rate limiting

### 3. **Persistência de Execuções**
- **Questão**: Onde armazenar logs detalhados?
- **Solução Proposta**: Supabase + storage para arquivos grandes

### 4. **WebSocket Scaling**
- **Questão**: Como escalar WebSocket horizontalmente?
- **Solução Proposta**: Redis pub/sub para múltiplas instâncias

### 5. **Error Handling**
- **Questão**: Como tratar falhas do Suna Backend?
- **Solução Proposta**: Circuit breaker + retry policies

### 6. **Monitoring**
- **Questão**: Como monitorar performance e erros?
- **Solução Proposta**: Structured logging + health checks

## Dependências Técnicas

### Core Dependencies
```toml
[project.dependencies]
fastapi = ">=0.115.0"
uvicorn = ">=0.27.0"
pydantic = ">=2.0.0"
supabase = ">=2.17.0"
httpx = ">=0.28.0"
websockets = ">=13.1"
structlog = ">=25.4.0"
redis = ">=5.0.0"
pyjwt = ">=2.10.0"
python-dotenv = ">=1.0.0"
```

### Development Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "black>=24.0.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0"
]
```

## Próximos Passos

1. **Implementar skeleton básico** com health checks
2. **Configurar integração Suna** com client isolado
3. **Implementar autenticação** com Supabase
4. **Desenvolver endpoints core** (teams, executions)
5. **Adicionar WebSocket** para tempo real
6. **Implementar testes** automatizados
7. **Configurar CI/CD** e deployment

## Critérios de Aceitação v1

- [ ] Autenticação funcional com Supabase
- [ ] CRUD completo de Teams
- [ ] Execução de teams com status em tempo real
- [ ] Integração estável com Suna Backend
- [ ] WebSocket para atualizações live
- [ ] Sistema de notificações básico
- [ ] Health checks e monitoramento
- [ ] Documentação API (OpenAPI/Swagger)
- [ ] Testes automatizados (>80% cobertura)
- [ ] Deploy automatizado