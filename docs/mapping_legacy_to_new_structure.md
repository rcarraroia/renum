# Mapeamento da Estrutura Legada para Nova Arquitetura

## Resumo Executivo

Este documento mapeia os módulos e funcionalidades encontrados no `renum-backend` legado para a nova estrutura proposta, identificando prioridades de migração e estratégias de refatoração.

## Estrutura Legada Analisada

### Módulos Principais Encontrados

#### 1. **API Routes** (`app/api/routes/`)
- **teams.py** - Gerenciamento de equipes de agentes
  - **Função**: CRUD de equipes, configuração de workflows
  - **Endpoints**: POST/GET/PUT/DELETE `/teams`
  - **Dependências**: TeamRepository, ApiKeyManager, SunaApiClient
  - **Prioridade**: **ALTA** - Core do sistema
  - **Status**: Reutilizável com refatoração

- **team_executions.py** - Execução de equipes
  - **Função**: Iniciar, monitorar e parar execuções de equipes
  - **Endpoints**: POST `/teams/{id}/execute`, WebSocket para monitoramento
  - **Dependências**: TeamOrchestrator, WebSocketManager
  - **Prioridade**: **ALTA** - Funcionalidade principal
  - **Status**: Reutilizável com refatoração

- **team_members.py** - Gerenciamento de membros de equipe
  - **Função**: CRUD de membros, papéis e permissões
  - **Endpoints**: POST/GET/PUT/DELETE `/teams/{id}/members`
  - **Dependências**: TeamRepository
  - **Prioridade**: **ALTA** - Essencial para colaboração
  - **Status**: Reutilizável com refatoração

- **auth.py** - Autenticação e autorização
  - **Função**: Login, registro, validação de tokens
  - **Endpoints**: POST `/auth/login`, `/auth/register`
  - **Dependências**: Supabase, JWT
  - **Prioridade**: **ALTA** - Segurança crítica
  - **Status**: Reutilizável com adaptação

- **notifications.py** - Sistema de notificações
  - **Função**: Envio e gerenciamento de notificações
  - **Endpoints**: GET/POST `/notifications`
  - **Dependências**: NotificationService, WebSocketManager
  - **Prioridade**: **MÉDIA** - UX importante
  - **Status**: Reutilizável

- **webhooks.py** - Integração via webhooks
  - **Função**: Receber e processar webhooks externos
  - **Endpoints**: POST `/webhooks/{integration_id}`
  - **Dependências**: WebhookService, IntegrationService
  - **Prioridade**: **MÉDIA** - Integrações externas
  - **Status**: Reutilizável

- **websocket.py** - Comunicação em tempo real
  - **Função**: WebSocket para atualizações em tempo real
  - **Endpoints**: WebSocket `/ws`
  - **Dependências**: WebSocketManager
  - **Prioridade**: **ALTA** - UX crítica
  - **Status**: Reutilizável

- **proxy_routes.py** - Proxy para Suna Backend
  - **Função**: Proxy transparente para API do Suna
  - **Endpoints**: Múltiplos endpoints proxy
  - **Dependências**: SunaProxyService
  - **Prioridade**: **ALTA** - Integração crítica
  - **Status**: Reutilizável com isolamento

#### 2. **Services** (`app/services/`)
- **team_orchestrator.py** - Orquestração de equipes
  - **Função**: Coordena execução de workflows de agentes
  - **Dependências**: SunaApiClient, ExecutionEngine
  - **Prioridade**: **ALTA** - Core business logic
  - **Status**: Reutilizável com refatoração

- **suna_api_client.py** - Cliente para API Suna
  - **Função**: Comunicação com backend Suna
  - **Dependências**: httpx, configurações de API
  - **Prioridade**: **ALTA** - Integração crítica
  - **Status**: Mover para `infra/suna/`

- **notification_service.py** - Serviço de notificações
  - **Função**: Gerencia envio de notificações
  - **Dependências**: WebSocketManager, templates
  - **Prioridade**: **MÉDIA** - UX
  - **Status**: Reutilizável

- **websocket_manager.py** - Gerenciador WebSocket
  - **Função**: Gerencia conexões WebSocket
  - **Dependências**: FastAPI WebSocket
  - **Prioridade**: **ALTA** - Tempo real
  - **Status**: Reutilizável

- **execution_engine.py** - Motor de execução
  - **Função**: Executa workflows de agentes
  - **Dependências**: SunaApiClient, TeamOrchestrator
  - **Prioridade**: **ALTA** - Core engine
  - **Status**: Reutilizável com refatoração

- **supabase_service.py** - Serviço Supabase
  - **Função**: Operações de banco de dados
  - **Dependências**: supabase-py
  - **Prioridade**: **ALTA** - Persistência
  - **Status**: Mover para `infra/supabase/`

#### 3. **Models** (`app/models/`)
- **team_models.py** - Modelos de equipe
  - **Função**: Schemas Pydantic para equipes
  - **Dependências**: Pydantic, UUID, Enum
  - **Prioridade**: **ALTA** - Estrutura de dados
  - **Status**: Mover para `schemas/`

- **auth.py** - Modelos de autenticação
  - **Função**: Schemas para auth
  - **Dependências**: Pydantic, JWT
  - **Prioridade**: **ALTA** - Segurança
  - **Status**: Mover para `schemas/`

- **agent.py** - Modelos de agente
  - **Função**: Schemas para agentes
  - **Dependências**: Pydantic
  - **Prioridade**: **ALTA** - Core entities
  - **Status**: Mover para `schemas/`

#### 4. **Core** (`app/core/`)
- **config.py** - Configurações
  - **Função**: Configurações da aplicação
  - **Dependências**: pydantic-settings, dotenv
  - **Prioridade**: **ALTA** - Configuração
  - **Status**: Reutilizável

- **auth.py** - Utilitários de auth
  - **Função**: Validação de tokens, dependências
  - **Dependências**: JWT, Supabase
  - **Prioridade**: **ALTA** - Segurança
  - **Status**: Reutilizável

- **logging_config.py** - Configuração de logs
  - **Função**: Setup de logging estruturado
  - **Dependências**: structlog
  - **Prioridade**: **MÉDIA** - Observabilidade
  - **Status**: Reutilizável

## Mapeamento para Nova Estrutura

### Migração Prioritária (ALTA)

| Módulo Legado | Novo Local | Ação |
|---------------|------------|------|
| `api/routes/teams.py` | `api/v1/teams.py` | Refatorar + Clean Architecture |
| `api/routes/team_executions.py` | `api/v1/executions.py` | Refatorar + Clean Architecture |
| `api/routes/auth.py` | `api/v1/auth.py` | Refatorar + Clean Architecture |
| `services/team_orchestrator.py` | `usecases/team_orchestrator.py` | Refatorar para use cases |
| `services/execution_engine.py` | `usecases/execution_engine.py` | Refatorar para use cases |
| `services/suna_api_client.py` | `infra/suna/client.py` | Isolar integração |
| `services/supabase_service.py` | `infra/supabase/client.py` | Isolar persistência |
| `models/team_models.py` | `schemas/team.py` | Reorganizar schemas |
| `models/auth.py` | `schemas/auth.py` | Reorganizar schemas |
| `core/config.py` | `common/config.py` | Manter configurações |

### Migração Secundária (MÉDIA)

| Módulo Legado | Novo Local | Ação |
|---------------|------------|------|
| `api/routes/notifications.py` | `api/v1/notifications.py` | Refatorar |
| `api/routes/webhooks.py` | `api/v1/webhooks.py` | Refatorar |
| `services/notification_service.py` | `usecases/notification_service.py` | Refatorar |
| `services/websocket_manager.py` | `infra/websocket/manager.py` | Isolar infraestrutura |

### Migração Baixa Prioridade (BAIXA)

| Módulo Legado | Novo Local | Ação |
|---------------|------------|------|
| `services/billing_manager.py` | `usecases/billing.py` | Avaliar necessidade |
| `services/metrics_collector.py` | `infra/monitoring/` | Mover para observabilidade |
| `api/routes/rag.py` | `api/v1/rag.py` | Avaliar se necessário |

## Dependências Críticas Identificadas

### Bibliotecas Principais
- **FastAPI** 0.115.12 - Framework web
- **Supabase** 2.17.0 - Banco de dados e auth
- **httpx** 0.28.0 - Cliente HTTP para Suna
- **websockets** 13.1 - Comunicação tempo real
- **pydantic** - Validação de dados
- **structlog** 25.4.0 - Logging estruturado

### Integrações Externas
- **Suna Backend** - `http://157.180.39.41:8000/api`
- **Suna WebSocket** - `ws://157.180.39.41:8000/ws`
- **Supabase** - Banco de dados PostgreSQL
- **Redis** - Cache e sessões (opcional)

## Gaps e Questões Técnicas

### 1. **Configuração de Ambiente**
- Variáveis de ambiente para Suna API
- Configuração Supabase (URL, keys)
- Configuração Redis (se mantido)

### 2. **Autenticação**
- Migração de tokens JWT existentes
- Integração com Supabase Auth
- Políticas RLS (Row Level Security)

### 3. **WebSocket**
- Estratégia de reconexão
- Gerenciamento de salas/canais
- Escalabilidade horizontal

### 4. **Monitoramento**
- Métricas de performance
- Health checks
- Logging centralizado

## Estratégia de Migração Recomendada

### Fase 1: Core API (Sprint 1-2)
1. Migrar `teams.py`, `team_executions.py`, `auth.py`
2. Implementar `infra/suna/client.py`
3. Configurar `infra/supabase/client.py`
4. Schemas básicos em `schemas/`

### Fase 2: Execução e WebSocket (Sprint 3)
1. Migrar `team_orchestrator.py` para use cases
2. Implementar WebSocket manager
3. Sistema de notificações básico

### Fase 3: Integrações (Sprint 4)
1. Webhooks e integrações externas
2. Sistema de monitoramento
3. Otimizações de performance

## Riscos Identificados

### Alto Risco
- **Dependência do Suna Backend**: Sistema crítico externo
- **Migração de dados**: Compatibilidade com dados existentes
- **WebSocket**: Complexidade de gerenciamento de estado

### Médio Risco
- **Autenticação**: Migração de usuários existentes
- **Performance**: Latência com múltiplas integrações

### Baixo Risco
- **Logging**: Configuração de observabilidade
- **Testes**: Cobertura de testes automatizados

## Conclusões

O sistema legado possui uma arquitetura bem estruturada com separação clara de responsabilidades. A migração deve focar em:

1. **Isolar integrações externas** (Suna, Supabase) em `infra/`
2. **Refatorar lógica de negócio** para `usecases/` e `domain/`
3. **Manter compatibilidade** com APIs existentes
4. **Priorizar funcionalidades core** (teams, executions, auth)

A nova estrutura permitirá melhor testabilidade, manutenibilidade e escalabilidade do sistema.