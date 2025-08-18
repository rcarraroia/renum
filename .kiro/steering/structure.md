# Estrutura do Projeto

## Layout do Diretório Raiz

```
renum/
├── apps/api/                 # Backend FastAPI
├── src/                     # Frontend React (futuro)
├── docs/                    # Documentação
├── .kiro/                   # Configuração Kiro
│   ├── specs/              # Especificações de funcionalidades
│   └── steering/           # Orientações para assistente IA
├── .github/workflows/      # Pipelines CI/CD
├── deploy-production.sh    # Script de deploy de produção
├── docker-compose.production.yml  # Configuração Docker produção
└── README.md               # Documentação principal
```

## Estrutura do Backend (apps/api/)

Seguindo princípios de Clean Architecture:

```
apps/api/
├── app/                     # Código fonte da aplicação
│   ├── api/v1/             # Endpoints da API (Camada de Interface)
│   │   ├── health.py       # Health checks
│   │   ├── teams.py        # Gerenciamento de equipes
│   │   ├── executions.py   # Execução de agentes
│   │   ├── agent_registry.py # Registro de agentes
│   │   ├── integrations.py # Integrações externas
│   │   ├── webhooks.py     # Webhooks
│   │   └── websocket.py    # Conexões WebSocket
│   ├── domain/             # Entidades de negócio (Camada de Domínio)
│   │   ├── agent.py        # Entidade Agent
│   │   └── integration.py  # Entidade Integration
│   ├── schemas/            # Modelos Pydantic (Camada de Interface)
│   │   ├── agent.py        # Schemas de agentes
│   │   ├── integration.py  # Schemas de integrações
│   │   ├── orchestrator.py # Schemas de orquestração
│   │   ├── credentials.py  # Schemas de credenciais
│   │   └── admin.py        # Schemas administrativos
│   ├── services/           # Lógica de negócio (Camada de Casos de Uso)
│   │   ├── agent_registry_service.py    # Serviço de registro de agentes
│   │   ├── integration_service.py       # Serviço de integrações
│   │   └── webhook_service.py           # Serviço de webhooks
│   ├── repositories/       # Acesso a dados (Camada de Infraestrutura)
│   │   ├── agent_repository.py          # Repositório de agentes
│   │   └── integration_repository.py    # Repositório de integrações
│   ├── infra/              # Integrações externas (Camada de Infraestrutura)
│   │   └── suna/           # Cliente Suna Backend
│   ├── core/               # Configuração e utilitários
│   │   └── config.py       # Configurações centralizadas
│   └── main.py             # Ponto de entrada da aplicação FastAPI
├── migrations/             # Migrações do schema do banco
│   ├── 001_multi_agent_system_schema.sql
│   ├── 002_rls_policies.sql
│   ├── 003_triggers_and_functions.sql
│   ├── 004_initial_data.sql
│   └── run_migrations.py   # Script de execução de migrações
├── tests/                  # Suíte de testes
│   └── test_agent_registry.py
├── scripts/                # Scripts utilitários
├── pyproject.toml          # Configuração do pacote Python
├── .env.production.example # Exemplo de variáveis de ambiente
└── start_server.py         # Script de inicialização do servidor
```

## Camadas da Arquitetura

### Camada de Domínio (`app/domain/`)
- Entidades de negócio puras e regras
- Sem dependências externas
- Contém lógica de negócio central
- Exemplos: `Agent`, `Integration`, `AgentCapability`

### Camada de Casos de Uso (`app/services/`)
- Lógica de negócio da aplicação
- Orquestra entidades de domínio
- Define operações específicas da aplicação
- Exemplos: `AgentRegistryService`, `IntegrationService`

### Camada de Infraestrutura (`app/repositories/`, `app/infra/`)
- Preocupações externas (banco de dados, APIs, sistema de arquivos)
- Implementa interfaces definidas pelas camadas internas
- Contém adaptadores para serviços externos
- Exemplos: `AgentRepository`, `SunaClient`

### Camada de Interface (`app/api/`, `app/schemas/`)
- Controladores e apresentadores
- Manipulação de requisições/respostas HTTP
- Validação de entrada e serialização
- Exemplos: routers FastAPI, schemas Pydantic

## Convenções Principais

### Nomenclatura
- **Arquivos**: snake_case (ex: `agent_registry.py`)
- **Classes**: PascalCase (ex: `AgentRegistryService`)
- **Funções/Métodos**: snake_case (ex: `create_agent`)
- **Constantes**: UPPER_SNAKE_CASE (ex: `MAX_AGENTS_PER_TEAM`)

### Dependências
- Camadas internas nunca dependem de camadas externas
- Injeção de dependência para desacoplamento
- Interfaces para abstrair implementações

### Testes
- Cada camada tem arquivos de teste correspondentes
- Testes unitários para lógica de domínio
- Testes de integração para APIs e banco de dados
- Mocks para dependências externas

### Configuração
- Centralizada em `app/core/config.py`
- Usa pydantic-settings para validação
- Variáveis de ambiente para configuração

### Migrações
- Arquivos SQL sequenciais no diretório `migrations/`
- Nomenclatura: `XXX_description.sql`
- Script `run_migrations.py` para execução

## Padrões de Desenvolvimento

### Async/Await
- Todas as operações I/O devem ser assíncronas
- Usar `async def` para funções que fazem I/O
- Usar `await` para chamadas assíncronas

### Error Handling
- Usar `HTTPException` para erros de API
- Logging estruturado para debugging
- Validação de entrada com Pydantic

### Documentação
- Docstrings em português para métodos públicos
- Comentários inline para lógica complexa
- README.md atualizado com mudanças