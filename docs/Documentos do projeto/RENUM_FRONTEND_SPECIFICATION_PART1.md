# 🎨 RENUM FRONTEND - ESPECIFICAÇÃO COMPLETA PARA LOVABLE (PARTE 1)

**Data:** 09/01/2025  
**Versão:** 1.0  
**Objetivo:** Documentação completa do frontend Renum implementado para replicação no Lovable

---

## 📋 ÍNDICE

1. [Visão Geral do Frontend](#visão-geral-do-frontend)
2. [Arquitetura e Estrutura](#arquitetura-e-estrutura)
3. [Páginas Implementadas](#páginas-implementadas)
4. [Componentes Principais](#componentes-principais)
5. [Hooks Customizados](#hooks-customizados)
6. [Serviços e APIs](#serviços-e-apis)

---

## 🎯 VISÃO GERAL DO FRONTEND

### **O que está implementado:**

O **Renum Frontend** é uma aplicação Next.js 15 completa e funcional que implementa:

- ✅ **Dashboard principal** com estatísticas e visão geral
- ✅ **Sistema de equipes** completo (criar, editar, executar)
- ✅ **Monitoramento em tempo real** via WebSocket
- ✅ **Sistema de notificações** avançado
- ✅ **Gerenciamento de agentes** integrado com Suna
- ✅ **Interface responsiva** com TailwindCSS
- ✅ **Sistema de autenticação** com Supabase
- ✅ **Componentes reutilizáveis** bem estruturados

### **Tecnologias Utilizadas:**

- **Next.js 15** - Framework React com App Router
- **React 18** - Biblioteca de interface
- **TypeScript** - Tipagem estática completa
- **TailwindCSS** - Framework de estilos
- **React Query** - Gerenciamento de estado servidor
- **Zustand** - Gerenciamento de estado local
- **React Hook Form** - Gerenciamento de formulários
- **WebSocket** - Comunicação em tempo real

---

## 🏗️ ARQUITETURA E ESTRUTURA

### **Estrutura de Diretórios Implementada:**

```
renum-frontend/src/
├── components/           # Componentes React
│   ├── admin/           # Componentes administrativos
│   ├── client/          # Componentes do cliente
│   ├── common/          # Componentes comuns
│   ├── executions/      # Componentes de execução
│   ├── layout/          # Componentes de layout
│   ├── notifications/   # Sistema de notificações
│   ├── teams/           # Componentes de equipes
│   ├── ui/              # Componentes de interface
│   └── websocket/       # Componentes WebSocket
├── contexts/            # Contextos React
├── hooks/               # Hooks customizados
├── lib/                 # Bibliotecas e utilitários
├── pages/               # Páginas Next.js
├── services/            # Serviços de API
├── types/               # Definições TypeScript
└── utils/               # Funções utilitárias
```

### **Padrão de Arquitetura:**

- **Componentes funcionais** com hooks
- **Separação de responsabilidades** clara
- **Reutilização** máxima de componentes
- **Tipagem TypeScript** completa
- **Performance otimizada** com lazy loading

---

## 📄 PÁGINAS IMPLEMENTADAS

### **1. Dashboard Principal (`/dashboard`)**

**Funcionalidades:**
- Visão geral com estatísticas
- Lista de agentes do usuário
- Agentes compartilhados
- Filtros por status
- Ações rápidas

**Componentes principais:**
- Estatísticas em cards
- Lista de agentes com filtros
- Seção de agentes compartilhados
- Loading states e error handling

### **2. Página de Login (`/login`)**

**Funcionalidades:**
- Autenticação com Supabase
- Formulário responsivo
- Validação de campos
- Redirecionamento automático

### **3. Página de Registro (`/register`)**

**Funcionalidades:**
- Criação de conta
- Validação de dados
- Integração com Supabase Auth

### **4. Equipes (`/teams`)**

#### **4.1 Lista de Equipes (`/teams`)**
- Grid de equipes
- Filtros e busca
- Paginação
- Ações por equipe (executar, editar, deletar)

#### **4.2 Criar Equipe (`/teams/new`)**
- Formulário multi-etapas
- Seleção de agentes
- Configuração de workflow
- Validação completa

#### **4.3 Detalhes da Equipe (`/teams/[id]`)**
- Informações da equipe
- Histórico de execuções
- Configurações avançadas

#### **4.4 Executar Equipe (`/teams/[id]/execute`)**
- Interface de execução
- Monitoramento em tempo real
- Logs detalhados
- Controles de execução

### **5. Execuções (`/executions`)**

#### **5.1 Lista de Execuções (`/executions`)**
- Histórico completo
- Filtros por status
- Métricas de performance

#### **5.2 Detalhes da Execução (`/executions/[id]`)**
- Status detalhado
- Logs em tempo real
- Resultados e erros
- Métricas de custo

### **6. Agentes (`/agents`)**

#### **6.1 Criar Agente (`/agents/new`)**
- Integração com Suna Backend
- Configuração completa
- Seleção de ferramentas

#### **6.2 Detalhes do Agente (`/agents/[id]`)**
- Informações do agente
- Histórico de uso
- Compartilhamento

### **7. Configurações (`/settings`)**

**Funcionalidades:**
- Configurações de usuário
- API keys
- Preferências de notificação
- Configurações de WebSocket

---

## 🧩 COMPONENTES PRINCIPAIS

### **1. Componentes de Layout**

#### **Layout Principal (`Layout.tsx`)**
```typescript
interface LayoutProps {
  title?: string;
  children: React.ReactNode;
}
```
- Sidebar responsiva
- Header com notificações
- Breadcrumb navigation
- Footer

#### **Sidebar (`Sidebar.tsx`)**
- Navegação principal
- Menu colapsível
- Indicadores de status
- Links ativos

### **2. Componentes de Equipes**

#### **TeamCard (`components/teams/TeamCard.tsx`)**
```typescript
interface TeamCardProps {
  team: Team;
  onExecute?: (team: Team) => void;
  onEdit?: (team: Team) => void;
  onDelete?: (team: Team) => void;
}
```
- Card responsivo
- Ações contextuais
- Status visual
- Informações resumidas

#### **WorkflowConfigurator (`components/teams/WorkflowConfigurator.tsx`)**
```typescript
interface WorkflowConfiguratorProps {
  selectedAgents: string[];
  value: WorkflowDefinition;
  onChange: (workflow: WorkflowDefinition) => void;
  error?: string;
}
```
- Configuração visual de workflows
- Suporte a múltiplos tipos
- Validação em tempo real
- Interface intuitiva

#### **AgentSelector (`components/teams/AgentSelector.tsx`)**
- Seleção múltipla de agentes
- Busca e filtros
- Preview de agentes
- Validação de limites

### **3. Componentes de Execução**

#### **ExecutionDashboard (`components/executions/ExecutionDashboard.tsx`)**
```typescript
interface ExecutionDashboardProps {
  teamId?: string;
  userId?: string;
  className?: string;
}
```
- Dashboard em tempo real
- Múltiplas abas (ativas, concluídas, falhadas)
- Estatísticas rápidas
- Auto-refresh configurável

#### **RealTimeExecutionProgress (`components/executions/RealTimeExecutionProgress.tsx`)**
- Progresso em tempo real
- Status de agentes individuais
- Logs streaming
- Controles de execução

### **4. Componentes WebSocket**

#### **ExecutionMonitor (`components/websocket/ExecutionMonitor.tsx`)**
```typescript
interface ExecutionMonitorProps {
  executionId: string;
  onUpdate?: (update: WebSocketExecutionUpdate) => void;
  showProgress?: boolean;
  showStatus?: boolean;
}
```
- Monitoramento em tempo real
- Atualizações automáticas
- Controles de execução
- Exibição de resultados

#### **ConnectionLostBanner (`components/websocket/ConnectionLostBanner.tsx`)**
- Indicador de conexão perdida
- Tentativas de reconexão
- Status visual claro

### **5. Componentes de Notificações**

#### **NotificationsCenter (`components/notifications/NotificationsCenter.tsx`)**
```typescript
interface NotificationsCenterProps {
  maxNotifications?: number;
  className?: string;
}
```
- Centro de notificações
- Notificações em tempo real
- Ações contextuais
- Gerenciamento de estado

#### **NotificationToast (`components/notifications/NotificationToast.tsx`)**
- Toasts temporários
- Múltiplos tipos (success, error, warning, info)
- Auto-dismiss configurável

### **6. Componentes de Interface**

#### **Button (`components/ui/Button.tsx`)**
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
}
```

#### **Input (`components/ui/Input.tsx`)**
```typescript
interface InputProps {
  id: string;
  label?: string;
  error?: string;
  required?: boolean;
  // ... outras props
}
```

#### **Select (`components/ui/Select.tsx`)**
- Dropdown customizado
- Busca integrada
- Múltipla seleção
- Validação

---

## 🎣 HOOKS CUSTOMIZADOS

### **1. Hooks de API**

#### **useTeams (`hooks/useTeams.ts`)**
```typescript
export function useTeams(options?: ListTeamsOptions) {
  // Gerenciamento completo de equipes
  // Integração com React Query
  // Cache inteligente
}
```

#### **useExecutions (`hooks/useExecutions.ts`)**
```typescript
export function useExecutions(options?: ListExecutionsOptions) {
  // Gerenciamento de execuções
  // Polling automático
  // Estados de loading/error
}
```

### **2. Hooks WebSocket**

#### **useWebSocket (`hooks/useWebSocket.ts`)**
```typescript
export function useWebSocket(url?: string | null, options?: UseWebSocketOptions) {
  return {
    isConnected: boolean;
    lastMessage: WebSocketMessage | null;
    sendMessage: (message: any) => void;
    disconnect: () => void;
    reconnect: () => void;
    status: 'connecting' | 'connected' | 'disconnected' | 'error';
    // ... mais funcionalidades
  };
}
```

**Funcionalidades:**
- Reconexão automática
- Heartbeat
- Buffer de mensagens
- Circuit breaker
- Debug mode

#### **useWebSocketNotifications (`hooks/useWebSocketNotifications.ts`)**
- Notificações em tempo real
- Gerenciamento de estado
- Persistência local
- Ações contextuais

### **3. Hooks de Estado**

#### **useAuth (`hooks/useAuth.ts`)**
```typescript
export function useAuth() {
  return {
    user: User | null;
    isAuthenticated: boolean;
    login: (credentials: LoginCredentials) => Promise<void>;
    logout: () => void;
    register: (data: RegisterData) => Promise<void>;
  };
}
```

#### **useRealTimeExecutions (`hooks/useRealTimeExecutions.ts`)**
- Execuções em tempo real
- Filtros automáticos
- Atualizações via WebSocket
- Cache otimizado

### **4. Hooks Utilitários**

#### **useHydration (`hooks/useHydration.ts`)**
- Gerenciamento de hidratação SSR
- Prevenção de erros de hidratação
- Estado de carregamento

#### **useMediaQuery (`hooks/useMediaQuery.ts`)**
- Responsividade
- Breakpoints dinâmicos
- Performance otimizada

---

## 🔌 SERVIÇOS E APIS

### **1. Cliente API Principal**

#### **RenumApiClient (`services/api-client.ts`)**
```typescript
class RenumApiClient {
  // Equipes
  async createTeam(teamData: TeamCreate): Promise<TeamResponse>
  async listTeams(options?: ListTeamsOptions): Promise<PaginatedTeamResponse>
  async getTeam(teamId: string): Promise<TeamResponse>
  async updateTeam(teamId: string, teamData: TeamUpdate): Promise<TeamResponse>
  async deleteTeam(teamId: string): Promise<void>
  
  // Execuções
  async executeTeam(teamId: string, executionData: TeamExecutionCreate): Promise<TeamExecutionResponse>
  async listExecutions(options?: ListExecutionsOptions): Promise<PaginatedExecutionResponse>
  async getExecutionStatus(executionId: string): Promise<TeamExecutionStatus>
  async getExecutionResult(executionId: string): Promise<TeamExecutionResult>
  async stopExecution(executionId: string): Promise<void>
  async getExecutionLogs(executionId: string, options?: GetExecutionLogsOptions): Promise<ExecutionLogEntry[]>
  
  // WebSocket
  createExecutionMonitor(executionId: string): WebSocket
}
```

### **2. React Query Hooks**

#### **Hooks de Equipes (`services/react-query-hooks.ts`)**
```typescript
// Queries
export function useTeams(options?: ListTeamsOptions, queryOptions?: UseQueryOptions)
export function useTeam(teamId: string, queryOptions?: UseQueryOptions)

// Mutations
export function useCreateTeam(options?: UseMutationOptions)
export function useUpdateTeam(options?: UseMutationOptions)
export function useDeleteTeam(options?: UseMutationOptions)
export function useExecuteTeam(options?: UseMutationOptions)
```

#### **Hooks de Execuções**
```typescript
export function useExecutions(options?: ListExecutionsOptions, queryOptions?: UseQueryOptions)
export function useExecutionStatus(executionId: string, queryOptions?: UseQueryOptions)
export function useExecutionResult(executionId: string, queryOptions?: UseQueryOptions)
export function useStopExecution(options?: UseMutationOptions)
```

### **3. Tipos TypeScript Completos**

#### **Tipos de API (`services/api-types.ts`)**
```typescript
// Interfaces principais
export interface Team { /* ... */ }
export interface TeamExecution { /* ... */ }
export interface WorkflowDefinition { /* ... */ }
export interface Agent { /* ... */ }

// Enums
export enum WorkflowType { /* ... */ }
export enum ExecutionStatus { /* ... */ }
export enum AgentRole { /* ... */ }

// Tipos de requisição/resposta
export interface TeamCreate { /* ... */ }
export interface TeamResponse { /* ... */ }
export interface PaginatedTeamResponse { /* ... */ }
```

---

**Continua na Parte 2...**

---

**Documento criado em:** 09/01/2025  
**Versão:** 1.0 - Parte 1  
**Status:** Completo e pronto para implementação no Lovable