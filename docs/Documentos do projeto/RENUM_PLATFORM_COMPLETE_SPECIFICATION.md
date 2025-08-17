# 🚀 RENUM PLATFORM - ESPECIFICAÇÃO COMPLETA PARA LOVABLE

**Data:** 09/01/2025  
**Versão:** 1.0  
**Objetivo:** Documentação completa do sistema Renum para desenvolvimento no Lovable

---

## 📋 ÍNDICE

1. [Visão Geral do Projeto](#visão-geral-do-projeto)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Backend Renum - Funcionalidades](#backend-renum---funcionalidades)
4. [Frontend Renum - Especificações](#frontend-renum---especificações)
5. [Integração com Suna Backend](#integração-com-suna-backend)
6. [Modelos de Dados](#modelos-de-dados)
7. [APIs e Endpoints](#apis-e-endpoints)
8. [Componentes de Interface](#componentes-de-interface)
9. [Fluxos de Usuário](#fluxos-de-usuário)
10. [Configurações e Environment](#configurações-e-environment)
11. [Considerações Técnicas](#considerações-técnicas)

---

## 🎯 VISÃO GERAL DO PROJETO

### **O que é o Renum?**

O **Renum** é uma plataforma avançada de orquestração de equipes de agentes de IA que permite criar, gerenciar e executar equipes coordenadas de agentes especializados para resolver tarefas complexas através de múltiplas estratégias de execução.

### **Diferencial Principal**

Enquanto o **Suna** é um assistente de IA individual, o **Renum** permite criar **equipes de agentes** que trabalham em conjunto usando diferentes estratégias:

- **Sequencial**: Agentes executam um após o outro
- **Paralelo**: Agentes executam simultaneamente
- **Pipeline**: Saída de um agente alimenta o próximo
- **Condicional**: Execução baseada em condições específicas

### **Público-Alvo**

- **Usuários Finais**: Profissionais que precisam resolver tarefas complexas
- **Empresas**: Equipes que precisam de automação avançada
- **Desenvolvedores**: Criadores de workflows de IA personalizados

---

## 🏗️ ARQUITETURA DO SISTEMA

### **Componentes Principais**

```
┌─────────────────────────────────────────────────────────────┐
│                    RENUM PLATFORM                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 15)                                     │
│  ├── Dashboard de Usuário                                  │
│  ├── Criação de Equipes                                    │
│  ├── Monitoramento de Execuções                            │
│  ├── Gerenciamento de Agentes                              │
│  └── Painel Administrativo (Futuro)                        │
├─────────────────────────────────────────────────────────────┤
│  Renum Backend (FastAPI)                                   │
│  ├── API de Equipes                                        │
│  ├── Sistema de Execução                                   │
│  ├── WebSocket para Tempo Real                             │
│  ├── Gerenciamento de API Keys                             │
│  └── Integração com Suna                                   │
├─────────────────────────────────────────────────────────────┤
│  Suna Backend (FastAPI) - EXTERNO                          │
│  ├── Execução de Agentes Individuais                       │
│  ├── Integração com LLMs                                   │
│  ├── Ferramentas e Automação                               │
│  └── Sistema de Threads                                    │
├─────────────────────────────────────────────────────────────┤
│  Banco de Dados (Supabase)                                 │
│  ├── Tabelas de Equipes                                    │
│  ├── Execuções e Logs                                      │
│  ├── Usuários e Autenticação                               │
│  └── Configurações                                         │
└─────────────────────────────────────────────────────────────┘
```

### **Fluxo de Dados**

```
[Frontend] → [Renum Backend] → [Suna Backend] → [LLMs/Tools]
     ↓              ↓                ↓
[WebSocket] ← [Supabase] ← [Execução de Agentes]
```

---

## 🔧 BACKEND RENUM - FUNCIONALIDADES

### **1. Sistema de Equipes**

#### **Criação de Equipes**
- **Endpoint**: `POST /api/v1/teams`
- **Funcionalidade**: Criar equipes com múltiplos agentes
- **Configurações**:
  - Nome e descrição da equipe
  - Lista de agentes (IDs do Suna)
  - Definição de workflow
  - Configurações específicas da equipe
  - API keys por usuário (criptografadas)

#### **Gerenciamento de Equipes**
- **Listar**: `GET /api/v1/teams`
- **Obter**: `GET /api/v1/teams/{id}`
- **Atualizar**: `PUT /api/v1/teams/{id}`
- **Excluir**: `DELETE /api/v1/teams/{id}`

#### **Membros de Equipe**
- **Adicionar**: `POST /api/v1/teams/{id}/members`
- **Atualizar**: `PUT /api/v1/teams/{id}/members/{agent_id}`
- **Remover**: `DELETE /api/v1/teams/{id}/members/{agent_id}`

### **2. Sistema de Execução**

#### **Execução de Equipes**
- **Endpoint**: `POST /api/v1/teams/{id}/execute`
- **Funcionalidade**: Executar equipe com prompt inicial
- **Estratégias Suportadas**:
  - **Sequential**: Execução em ordem definida
  - **Parallel**: Execução simultânea
  - **Pipeline**: Saída de um alimenta o próximo
  - **Conditional**: Baseado em condições

#### **Monitoramento de Execuções**
- **Listar**: `GET /api/v1/executions`
- **Status**: `GET /api/v1/executions/{id}/status`
- **Resultado**: `GET /api/v1/executions/{id}/result`
- **Logs**: `GET /api/v1/executions/{id}/logs`
- **Parar**: `POST /api/v1/executions/{id}/stop`

#### **WebSocket em Tempo Real**
- **Endpoint**: `WebSocket /ws/executions/{id}/monitor`
- **Funcionalidade**: Monitoramento em tempo real
- **Eventos**:
  - `status_update`: Atualização de status
  - `agent_status_update`: Status de agente específico
  - `progress_update`: Progresso da execução
  - `result_update`: Resultado parcial
  - `error_update`: Erros durante execução

### **3. Integração com Suna**

#### **Cliente Suna API**
- **Funcionalidade**: Comunicação com backend Suna
- **Endpoints Utilizados**:
  - `/api/agents/*`: Gerenciamento de agentes
  - `/api/threads/*`: Sistema de threads
  - `/api/execute/*`: Execução de agentes
  - `/ws/*`: WebSocket do Suna

#### **Orquestrador de Equipes**
- **Classe**: `TeamOrchestrator`
- **Responsabilidades**:
  - Coordenar execução de múltiplos agentes
  - Gerenciar contexto compartilhado
  - Implementar estratégias de execução
  - Coletar e agregar resultados

#### **Motor de Execução**
- **Classe**: `ExecutionEngine`
- **Responsabilidades**:
  - Executar workflows definidos
  - Gerenciar estado de execução
  - Tratar erros e falhas
  - Calcular métricas de custo

### **4. Gerenciamento de API Keys**

#### **Armazenamento Seguro**
- **Criptografia**: API keys criptografadas no banco
- **Por Usuário**: Cada usuário tem suas próprias keys
- **Por Serviço**: Suporte a múltiplos provedores LLM
- **Endpoints**:
  - `POST /api/v1/api-keys`: Criar/atualizar key
  - `GET /api/v1/api-keys`: Listar keys do usuário
  - `DELETE /api/v1/api-keys/{service}`: Remover key

### **5. Sistema de Autenticação**

#### **Integração com Supabase**
- **JWT Tokens**: Autenticação baseada em tokens
- **RLS (Row Level Security)**: Segurança a nível de linha
- **Middleware**: Verificação automática de autenticação
- **Scopes**: Diferentes níveis de acesso

---

## 💻 FRONTEND RENUM - ESPECIFICAÇÕES

### **1. Tecnologias Base**

#### **Framework e Bibliotecas**
- **Next.js 15**: Framework React com App Router
- **React 18**: Biblioteca de interface
- **TypeScript**: Tipagem estática
- **TailwindCSS**: Framework de estilos
- **Radix UI**: Componentes de interface
- **React Query**: Gerenciamento de estado servidor
- **Zustand**: Gerenciamento de estado local
- **React Hook Form**: Gerenciamento de formulários
- **Zod**: Validação de esquemas

### **2. Estrutura de Páginas**

#### **Páginas Principais**
```
/                     # Dashboard principal
/login               # Autenticação
/agents              # Gerenciamento de agentes (integração Suna)
/agents/new          # Criar novo agente
/agents/[id]         # Detalhes do agente
/teams               # Lista de equipes
/teams/new           # Criar nova equipe
/teams/[id]          # Detalhes da equipe
/teams/[id]/edit     # Editar equipe
/teams/[id]/execute  # Executar equipe
/executions          # Lista de execuções
/executions/[id]     # Detalhes da execução
/knowledge-base      # Bases de conhecimento
/settings            # Configurações do usuário
/admin/*             # Painel administrativo (futuro)
```

### **3. Componentes Principais**

#### **Layout e Navegação**
- **Layout**: Componente base com sidebar e header
- **Sidebar**: Navegação principal com menu colapsível
- **Header**: Barra superior com perfil e notificações
- **Breadcrumb**: Navegação hierárquica

#### **Componentes de Equipes**
- **TeamCard**: Card de equipe na listagem
- **TeamForm**: Formulário de criação/edição
- **TeamMemberSelector**: Seletor de agentes para equipe
- **WorkflowConfigurator**: Configurador de workflow
- **TeamExecutionPanel**: Painel de execução

#### **Componentes de Execução**
- **ExecutionCard**: Card de execução na listagem
- **ExecutionStatus**: Indicador de status
- **ExecutionProgress**: Barra de progresso
- **ExecutionLogs**: Visualizador de logs
- **ExecutionResult**: Exibição de resultados
- **RealTimeMonitor**: Monitor em tempo real via WebSocket

#### **Componentes de Agentes**
- **AgentCard**: Card de agente na listagem
- **AgentSelector**: Seletor de agentes
- **AgentPreview**: Prévia de configuração
- **AgentIntegration**: Integração com Suna

#### **Componentes de Interface**
- **Button**: Botão customizado
- **Input**: Campo de entrada
- **Select**: Seletor dropdown
- **Modal**: Modal customizado
- **Toast**: Notificações toast
- **Loading**: Indicadores de carregamento
- **EmptyState**: Estados vazios
- **ErrorBoundary**: Tratamento de erros

### **4. Hooks Customizados**

#### **Hooks de API**
- **useTeams**: Gerenciamento de equipes
- **useExecutions**: Gerenciamento de execuções
- **useAgents**: Integração com agentes Suna
- **useWebSocket**: Conexão WebSocket
- **useAuth**: Autenticação

#### **Hooks de Estado**
- **useTeamStore**: Estado global de equipes
- **useExecutionStore**: Estado global de execuções
- **useAuthStore**: Estado de autenticação
- **useUIStore**: Estado da interface

### **5. Serviços e Utilitários**

#### **Cliente API**
- **RenumApiClient**: Cliente para API Renum
- **SunaApiClient**: Cliente para API Suna (integração)
- **WebSocketClient**: Cliente WebSocket
- **ErrorHandler**: Tratamento de erros

#### **Utilitários**
- **formatters**: Formatação de dados
- **validators**: Validação de formulários
- **constants**: Constantes da aplicação
- **types**: Tipos TypeScript

---

## 🔗 INTEGRAÇÃO COM SUNA BACKEND

### **1. Comunicação com Suna**

#### **Endpoints Suna Utilizados**
```typescript
// Agentes
GET /api/agents                    # Listar agentes
GET /api/agents/{id}               # Obter agente
POST /api/agents                   # Criar agente
PUT /api/agents/{id}               # Atualizar agente

// Execução
POST /api/execute                  # Executar agente
GET /api/threads/{id}              # Obter thread
POST /api/threads/{id}/messages    # Enviar mensagem

// WebSocket
WebSocket /ws/threads/{id}         # Monitor de execução
```

#### **Fluxo de Integração**
1. **Frontend** → **Renum Backend**: Solicita execução de equipe
2. **Renum Backend** → **Suna Backend**: Executa agentes individuais
3. **Suna Backend** → **Renum Backend**: Retorna resultados
4. **Renum Backend** → **Frontend**: Agrega e retorna resultado final

### **2. Contexto Compartilhado**

#### **Gerenciamento de Contexto**
- **Contexto Global**: Compartilhado entre todos os agentes da equipe
- **Contexto Individual**: Específico de cada agente
- **Passagem de Dados**: Resultado de um agente alimenta outro
- **Memória Persistente**: Contexto mantido durante toda execução

#### **Estrutura de Contexto**
```typescript
interface TeamContext {
  team_execution_id: string;
  shared_context: Record<string, any>;
  agent_results: Record<string, any>;
  global_variables: Record<string, any>;
  execution_metadata: {
    started_at: string;
    current_step: number;
    total_steps: number;
  };
}
```

---

## 📊 MODELOS DE DADOS

### **1. Equipes (Teams)**

```typescript
interface Team {
  team_id: string;           // UUID
  user_id: string;           // UUID do usuário
  name: string;              // Nome da equipe
  description?: string;      // Descrição opcional
  agent_ids: string[];       // IDs dos agentes Suna
  workflow_definition: {     // Definição do workflow
    type: 'sequential' | 'parallel' | 'pipeline' | 'conditional';
    agents: AgentWorkflowConfig[];
  };
  user_api_keys: Record<string, string>; // API keys criptografadas
  team_config: {             // Configurações da equipe
    max_tokens?: number;
    temperature?: number;
    timeout?: number;
  };
  is_active: boolean;        // Status ativo/inativo
  created_at: string;        // Data de criação
  updated_at: string;        // Data de atualização
}
```

### **2. Configuração de Agente no Workflow**

```typescript
interface AgentWorkflowConfig {
  agent_id: string;          // ID do agente Suna
  role: 'leader' | 'member' | 'coordinator'; // Papel na equipe
  execution_order: number;   // Ordem de execução
  input: {                   // Configuração de entrada
    source: 'initial_prompt' | 'agent_result' | 'combined';
    agent_id?: string;       // ID do agente fonte (se aplicável)
    sources?: Array<{        // Múltiplas fontes (para combined)
      type: 'agent_result' | 'context' | 'variable';
      agent_id?: string;
      key?: string;
    }>;
  };
  conditions?: {             // Condições para execução (condicional)
    field: string;
    operator: 'equals' | 'contains' | 'greater_than' | 'less_than';
    value: any;
  }[];
  config?: {                 // Configurações específicas do agente
    max_tokens?: number;
    temperature?: number;
    tools?: string[];
  };
}
```

### **3. Execuções (Team Executions)**

```typescript
interface TeamExecution {
  execution_id: string;      // UUID
  team_id: string;           // UUID da equipe
  user_id: string;           // UUID do usuário
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  initial_prompt: string;    // Prompt inicial
  final_result?: {           // Resultado final
    summary: string;
    details: any;
    agent_contributions: Record<string, any>;
  };
  agent_results: Record<string, any>; // Resultados por agente
  cost_metrics: {            // Métricas de custo
    total_cost_usd: number;
    agent_costs: Record<string, number>;
  };
  usage_metrics: {           // Métricas de uso
    total_tokens: number;
    agent_tokens: Record<string, number>;
    execution_time: number;
  };
  error_message?: string;    // Mensagem de erro (se houver)
  started_at?: string;       // Início da execução
  completed_at?: string;     // Fim da execução
  created_at: string;        // Data de criação
}
```

### **4. Logs de Execução**

```typescript
interface ExecutionLog {
  log_id: string;            // UUID
  execution_id: string;      // UUID da execução
  timestamp: string;         // Timestamp do log
  level: 'info' | 'warning' | 'error'; // Nível do log
  agent_id?: string;         // ID do agente (se aplicável)
  message: string;           // Mensagem do log
  details?: Record<string, any>; // Detalhes adicionais
}
```

### **5. API Keys de Usuário**

```typescript
interface UserApiKey {
  key_id: string;            // UUID
  user_id: string;           // UUID do usuário
  service_name: string;      // Nome do serviço (openai, anthropic, etc.)
  encrypted_key: string;     // Chave criptografada
  is_active: boolean;        // Status ativo/inativo
  created_at: string;        // Data de criação
  updated_at: string;        // Data de atualização
}
```

---

## 🔌 APIS E ENDPOINTS

### **1. API de Equipes**

#### **Criar Equipe**
```http
POST /api/v1/teams
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "Equipe de Análise",
  "description": "Equipe para análise de dados",
  "agent_ids": ["agent-1", "agent-2"],
  "workflow_definition": {
    "type": "sequential",
    "agents": [
      {
        "agent_id": "agent-1",
        "role": "leader",
        "execution_order": 1,
        "input": { "source": "initial_prompt" }
      },
      {
        "agent_id": "agent-2",
        "role": "member",
        "execution_order": 2,
        "input": { "source": "agent_result", "agent_id": "agent-1" }
      }
    ]
  }
}
```

#### **Listar Equipes**
```http
GET /api/v1/teams?page=1&limit=10&search=análise
Authorization: Bearer {token}
```

#### **Executar Equipe**
```http
POST /api/v1/teams/{team_id}/execute
Content-Type: application/json
Authorization: Bearer {token}

{
  "initial_prompt": "Analise os dados financeiros da empresa XYZ"
}
```

### **2. API de Execuções**

#### **Obter Status**
```http
GET /api/v1/executions/{execution_id}/status
Authorization: Bearer {token}
```

#### **Obter Resultado**
```http
GET /api/v1/executions/{execution_id}/result
Authorization: Bearer {token}
```

#### **Obter Logs**
```http
GET /api/v1/executions/{execution_id}/logs?limit=100&offset=0
Authorization: Bearer {token}
```

### **3. WebSocket**

#### **Monitoramento em Tempo Real**
```javascript
const ws = new WebSocket('ws://localhost:9000/ws/executions/{execution_id}/monitor?token={jwt_token}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'status_update':
      // Atualizar status da execução
      break;
    case 'agent_status_update':
      // Atualizar status de agente específico
      break;
    case 'progress_update':
      // Atualizar progresso
      break;
    case 'result_update':
      // Resultado parcial
      break;
    case 'error_update':
      // Erro durante execução
      break;
  }
};
```

---

## 🎨 COMPONENTES DE INTERFACE

### **1. Dashboard Principal**

#### **Componentes**
- **DashboardStats**: Estatísticas gerais (equipes ativas, execuções, etc.)
- **RecentExecutions**: Execuções recentes
- **TeamQuickActions**: Ações rápidas para equipes
- **ActivityFeed**: Feed de atividades

#### **Layout**
```jsx
<Layout>
  <DashboardHeader />
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div className="lg:col-span-2">
      <DashboardStats />
      <RecentExecutions />
    </div>
    <div>
      <TeamQuickActions />
      <ActivityFeed />
    </div>
  </div>
</Layout>
```

### **2. Criação de Equipes**

#### **Componentes**
- **TeamBasicInfo**: Informações básicas (nome, descrição)
- **AgentSelector**: Seleção de agentes
- **WorkflowDesigner**: Designer visual de workflow
- **TeamConfiguration**: Configurações avançadas

#### **Fluxo de Criação**
```jsx
<TeamCreationWizard>
  <Step1_BasicInfo />
  <Step2_AgentSelection />
  <Step3_WorkflowDesign />
  <Step4_Configuration />
  <Step5_Review />
</TeamCreationWizard>
```

### **3. Execução de Equipes**

#### **Componentes**
- **ExecutionForm**: Formulário de execução
- **RealTimeMonitor**: Monitor em tempo real
- **AgentStatusGrid**: Grid de status dos agentes
- **ExecutionLogs**: Visualizador de logs
- **ResultsPanel**: Painel de resultados

#### **Interface de Execução**
```jsx
<ExecutionInterface>
  <ExecutionHeader team={team} execution={execution} />
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div>
      <RealTimeMonitor execution={execution} />
      <AgentStatusGrid agents={team.agents} />
    </div>
    <div>
      <ExecutionLogs executionId={execution.id} />
      <ResultsPanel execution={execution} />
    </div>
  </div>
</ExecutionInterface>
```

### **4. Componentes Reutilizáveis**

#### **Cards**
```jsx
// TeamCard
<TeamCard
  team={team}
  onExecute={handleExecute}
  onEdit={handleEdit}
  onDelete={handleDelete}
/>

// ExecutionCard
<ExecutionCard
  execution={execution}
  onView={handleView}
  onStop={handleStop}
/>

// AgentCard
<AgentCard
  agent={agent}
  onSelect={handleSelect}
  selected={isSelected}
/>
```

#### **Formulários**
```jsx
// TeamForm
<TeamForm
  initialData={team}
  onSubmit={handleSubmit}
  onCancel={handleCancel}
/>

// ExecutionForm
<ExecutionForm
  team={team}
  onExecute={handleExecute}
/>
```

#### **Visualizadores**
```jsx
// WorkflowVisualizer
<WorkflowVisualizer
  workflow={team.workflow_definition}
  interactive={true}
  onNodeClick={handleNodeClick}
/>

// ProgressIndicator
<ProgressIndicator
  current={execution.current_step}
  total={execution.total_steps}
  status={execution.status}
/>
```

---

## 👤 FLUXOS DE USUÁRIO

### **1. Fluxo de Criação de Equipe**

```
1. Usuário acessa /teams/new
2. Preenche informações básicas (nome, descrição)
3. Seleciona agentes disponíveis do Suna
4. Configura workflow (sequencial, paralelo, etc.)
5. Define configurações específicas
6. Revisa e confirma criação
7. Equipe é criada e usuário é redirecionado para detalhes
```

### **2. Fluxo de Execução de Equipe**

```
1. Usuário seleciona equipe para executar
2. Insere prompt inicial
3. Confirma execução
4. Sistema inicia execução em background
5. Usuário monitora progresso em tempo real via WebSocket
6. Agentes executam conforme workflow definido
7. Resultados são agregados e exibidos
8. Usuário pode visualizar logs detalhados
```

### **3. Fluxo de Monitoramento**

```
1. Usuário acessa execução em andamento
2. Interface conecta via WebSocket
3. Recebe atualizações em tempo real:
   - Status geral da execução
   - Progresso de cada agente
   - Resultados parciais
   - Logs de execução
4. Pode parar execução se necessário
5. Visualiza resultado final quando completo
```

### **4. Fluxo de Gerenciamento de API Keys**

```
1. Usuário acessa configurações
2. Adiciona API keys para diferentes serviços
3. Keys são criptografadas e armazenadas
4. Usuário pode testar conectividade
5. Keys são utilizadas automaticamente nas execuções
```

---

## ⚙️ CONFIGURAÇÕES E ENVIRONMENT

### **1. Variáveis de Ambiente - Frontend**

```env
# API URLs
NEXT_PUBLIC_RENUM_API_URL=http://localhost:9000
NEXT_PUBLIC_SUNA_API_URL=http://localhost:8000
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:9000/ws

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Configurações
NEXT_PUBLIC_APP_NAME=Renum Platform
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_ENVIRONMENT=development
```

### **2. Variáveis de Ambiente - Backend**

```env
# Servidor
HOST=0.0.0.0
PORT=9000
ENVIRONMENT=development

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# Suna Integration
SUNA_API_URL=http://localhost:8000
SUNA_API_KEY=your-suna-api-key

# Criptografia
ENCRYPTION_KEY=your-32-char-encryption-key

# JWT
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION=24h

# Redis (para cache)
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### **3. Configuração do Banco de Dados**

#### **Tabelas Principais**
```sql
-- Equipes
CREATE TABLE renum_teams (
  team_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  name TEXT NOT NULL,
  description TEXT,
  agent_ids TEXT[] NOT NULL,
  workflow_definition JSONB NOT NULL,
  user_api_keys JSONB DEFAULT '{}',
  team_config JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Execuções
CREATE TABLE renum_team_executions (
  execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES renum_teams(team_id),
  user_id UUID REFERENCES auth.users(id),
  status TEXT NOT NULL DEFAULT 'pending',
  initial_prompt TEXT NOT NULL,
  final_result JSONB,
  agent_results JSONB DEFAULT '{}',
  cost_metrics JSONB DEFAULT '{}',
  usage_metrics JSONB DEFAULT '{}',
  error_message TEXT,
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Logs
CREATE TABLE renum_execution_logs (
  log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id UUID REFERENCES renum_team_executions(execution_id),
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  level TEXT NOT NULL,
  agent_id TEXT,
  message TEXT NOT NULL,
  details JSONB DEFAULT '{}'
);

-- API Keys
CREATE TABLE renum_user_api_keys (
  key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  service_name TEXT NOT NULL,
  encrypted_key TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, service_name)
);
```

---

## 🔧 CONSIDERAÇÕES TÉCNICAS

### **1. Performance**

#### **Frontend**
- **Code Splitting**: Divisão de código por rotas
- **Lazy Loading**: Carregamento sob demanda de componentes
- **React Query**: Cache inteligente de dados
- **Memoização**: Otimização de re-renders
- **Bundle Optimization**: Otimização do bundle final

#### **Backend**
- **Async Processing**: Execuções em background
- **Connection Pooling**: Pool de conexões com banco
- **Caching**: Cache Redis para dados frequentes
- **Rate Limiting**: Limitação de taxa de requisições
- **Database Indexing**: Índices otimizados

### **2. Segurança**

#### **Autenticação e Autorização**
- **JWT Tokens**: Tokens seguros com expiração
- **RLS (Row Level Security)**: Segurança a nível de linha
- **API Key Encryption**: Criptografia de chaves sensíveis
- **CORS Configuration**: Configuração adequada de CORS
- **Input Validation**: Validação rigorosa de entradas

#### **Proteção de Dados**
- **Encryption at Rest**: Dados criptografados no banco
- **Encryption in Transit**: HTTPS/WSS obrigatório
- **Sensitive Data Masking**: Mascaramento de dados sensíveis
- **Audit Logging**: Logs de auditoria completos

### **3. Escalabilidade**

#### **Arquitetura**
- **Microservices Ready**: Preparado para microserviços
- **Horizontal Scaling**: Escalabilidade horizontal
- **Load Balancing**: Balanceamento de carga
- **Database Sharding**: Preparado para sharding
- **CDN Integration**: Integração com CDN

#### **Monitoramento**
- **Health Checks**: Verificações de saúde
- **Metrics Collection**: Coleta de métricas
- **Error Tracking**: Rastreamento de erros
- **Performance Monitoring**: Monitoramento de performance
- **Alerting**: Sistema de alertas

### **4. Desenvolvimento**

#### **Padrões de Código**
- **TypeScript**: Tipagem estática obrigatória
- **ESLint/Prettier**: Linting e formatação
- **Conventional Commits**: Commits padronizados
- **Component Documentation**: Documentação de componentes
- **API Documentation**: Documentação automática de APIs

#### **Testing**
- **Unit Tests**: Testes unitários
- **Integration Tests**: Testes de integração
- **E2E Tests**: Testes end-to-end
- **API Tests**: Testes de API
- **Performance Tests**: Testes de performance

### **5. Deploy e DevOps**

#### **Containerização**
- **Docker**: Containerização completa
- **Docker Compose**: Orquestração local
- **Multi-stage Builds**: Builds otimizados
- **Health Checks**: Verificações de saúde

#### **CI/CD**
- **GitHub Actions**: Integração contínua
- **Automated Testing**: Testes automatizados
- **Automated Deployment**: Deploy automatizado
- **Environment Management**: Gestão de ambientes
- **Rollback Strategy**: Estratégia de rollback

---

## 📝 NOTAS IMPORTANTES PARA O LOVABLE

### **1. Integração com Backend Existente**

O **Renum Backend** já está implementado e funcional. O Lovable deve:
- **Consumir as APIs** existentes do Renum Backend
- **Não modificar** o backend, apenas integrar
- **Usar os tipos TypeScript** fornecidos
- **Seguir os padrões** de API documentados

### **2. Comunicação com Suna**

O frontend **não se comunica diretamente** com o Suna Backend:
- **Fluxo**: Frontend → Renum Backend → Suna Backend
- **Agentes**: Obtidos via API do Renum que consulta o Suna
- **Execuções**: Orquestradas pelo Renum Backend
- **WebSocket**: Conecta apenas com Renum Backend

### **3. Autenticação**

- **Supabase Auth**: Sistema de autenticação principal
- **JWT Tokens**: Tokens para comunicação com APIs
- **RLS**: Segurança implementada no banco
- **Middleware**: Verificação automática no backend

### **4. Estado da Aplicação**

- **React Query**: Para dados do servidor (equipes, execuções)
- **Zustand**: Para estado local da UI
- **Context API**: Para dados globais (auth, tema)
- **Local Storage**: Para preferências do usuário

### **5. Responsividade**

- **Mobile First**: Design responsivo obrigatório
- **Breakpoints**: sm, md, lg, xl, 2xl
- **Touch Friendly**: Interface amigável ao toque
- **Progressive Web App**: Preparado para PWA

---

## 🎯 CONCLUSÃO

Esta especificação fornece uma visão completa do sistema Renum para desenvolvimento no Lovable. O backend já está implementado e funcional, cabendo ao Lovable criar uma interface moderna, intuitiva e responsiva que consuma as APIs existentes.

**Pontos-chave para o desenvolvimento:**

1. **Backend pronto**: Todas as APIs estão implementadas
2. **Integração clara**: Fluxos de dados bem definidos
3. **Componentes modulares**: Interface componentizada
4. **Tempo real**: WebSocket para monitoramento
5. **Segurança**: Autenticação e autorização robustas
6. **Performance**: Otimizações implementadas
7. **Escalabilidade**: Arquitetura preparada para crescimento

O resultado final será uma plataforma completa de orquestração de equipes de agentes de IA, moderna e profissional, pronta para uso em produção.

---

**Documento criado em:** 09/01/2025  
**Versão:** 1.0  
**Status:** Completo e pronto para desenvolvimento