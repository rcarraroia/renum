# 🎨 RENUM FRONTEND - ESPECIFICAÇÃO COMPLETA PARA LOVABLE (PARTE 2)

**Data:** 09/01/2025  
**Versão:** 1.0  
**Continuação da Parte 1**

---

## 📋 ÍNDICE (PARTE 2)

7. [Sistema de Estado](#sistema-de-estado)
8. [WebSocket e Tempo Real](#websocket-e-tempo-real)
9. [Sistema de Notificações](#sistema-de-notificações)
10. [Funcionalidades Avançadas](#funcionalidades-avançadas)
11. [Configurações e Estilos](#configurações-e-estilos)
12. [Guia de Implementação](#guia-de-implementação)

---

## 🏪 SISTEMA DE ESTADO

### **1. Zustand Stores**

#### **Auth Store (`lib/store.ts`)**
```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  clearAuth: () => void;
}
```

#### **Agent Store**
```typescript
interface AgentState {
  agents: Agent[];
  isLoading: boolean;
  error: string | null;
  setAgents: (agents: Agent[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}
```

### **2. Context Providers**

#### **WebSocketContext (`contexts/WebSocketContext.tsx`)**
```typescript
interface WebSocketContextType {
  isConnected: boolean;
  subscribe: (channel: string, callback: (data: any) => void) => () => void;
  unsubscribe: (channel: string) => void;
  publish: (channel: string, data: any) => void;
  sendCommand: (command: string, data?: any) => void;
}
```

#### **AuthContext (`contexts/AuthContext.tsx`)**
- Gerenciamento de autenticação
- Integração com Supabase
- Persistência de sessão
- Refresh automático

### **3. React Query Configuration**

#### **Query Client (`services/query-client.ts`)**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 60 * 5, // 5 minutos
      cacheTime: 1000 * 60 * 30, // 30 minutos
    },
  },
});
```

**Funcionalidades:**
- Cache inteligente
- Invalidação automática
- Retry logic
- Background refetch
- Optimistic updates

---

## 🔌 WEBSOCKET E TEMPO REAL

### **1. Sistema WebSocket Robusto**

#### **Funcionalidades Implementadas:**
- ✅ **Reconexão automática** com backoff exponencial
- ✅ **Heartbeat** para manter conexão viva
- ✅ **Buffer de mensagens** quando desconectado
- ✅ **Circuit breaker** para evitar loops
- ✅ **Múltiplos canais** de subscrição
- ✅ **Tratamento de erros** robusto

#### **Configuração WebSocket (`constants/websocket.ts`)**
```typescript
export const WEBSOCKET_CONFIG = {
  DEFAULT_URL: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:9000/ws',
  RECONNECT_ATTEMPTS: 5,
  RECONNECT_INTERVAL: 1000,
  HEARTBEAT_INTERVAL: 30000,
  MAX_RECONNECT_DELAY: 30000,
  BACKOFF_MULTIPLIER: 2
};
```

### **2. Componentes WebSocket**

#### **Indicadores de Conexão**
- **ConnectionLostBanner**: Banner de conexão perdida
- **ConnectionLostOverlay**: Overlay de reconexão
- **ReconnectionProgress**: Progresso de reconexão
- **WebSocketStatus**: Status da conexão

#### **Monitoramento em Tempo Real**
- **ExecutionMonitor**: Monitor de execução específica
- **RealTimeExecutionProgress**: Progresso em tempo real
- **WebSocketNotifications**: Notificações via WebSocket

### **3. Tipos WebSocket (`types/websocket.ts`)**
```typescript
export interface WebSocketMessage {
  type: WebSocketMessageType;
  data: any;
  timestamp: string;
}

export interface WebSocketExecutionUpdate {
  execution_id: string;
  status: ExecutionStatus;
  progress: number;
  current_step?: string;
  result?: any;
  error?: string;
}

export interface WebSocketNotification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  action?: {
    type: 'url' | 'callback';
    payload: string;
  };
}
```

---

## 🔔 SISTEMA DE NOTIFICAÇÕES

### **1. Arquitetura de Notificações**

#### **Componentes Principais:**
- **NotificationsCenter**: Centro principal de notificações
- **NotificationDropdown**: Dropdown de notificações
- **NotificationToast**: Toasts temporários
- **NotificationBadge**: Badge de contagem
- **NotificationSettings**: Configurações de notificação

### **2. Tipos de Notificações**

#### **Notificações WebSocket:**
- Execuções iniciadas/concluídas
- Erros de execução
- Atualizações de status
- Mensagens do sistema

#### **Notificações Toast:**
- Ações do usuário (salvar, deletar)
- Erros de API
- Confirmações
- Avisos temporários

### **3. Gerenciamento de Estado**

#### **Hook de Notificações (`hooks/useWebSocketNotifications.ts`)**
```typescript
export function useWebSocketNotifications() {
  return {
    notifications: WebSocketNotification[];
    unreadCount: number;
    markAsRead: (id: string) => void;
    markAllAsRead: () => void;
    removeNotification: (id: string) => void;
    clearAllNotifications: () => void;
    addNotification: (notification: Omit<WebSocketNotification, 'id' | 'created_at'>) => void;
  };
}
```

### **4. Persistência e Sincronização**

- **LocalStorage**: Persistência de notificações
- **Sincronização**: Entre abas do navegador
- **Limpeza automática**: Notificações antigas
- **Configurações**: Preferências do usuário

---

## ⚡ FUNCIONALIDADES AVANÇADAS

### **1. Lazy Loading e Performance**

#### **Componentes Lazy (`components/lazy/LazyComponents.tsx`)**
```typescript
// Lazy loading de componentes pesados
export const LazyExecutionDashboard = lazy(() => import('../executions/ExecutionDashboard'));
export const LazyWorkflowVisualizer = lazy(() => import('../teams/WorkflowVisualizer'));
export const LazyNotificationsCenter = lazy(() => import('../notifications/NotificationsCenter'));
```

#### **Otimizações Implementadas:**
- **Code splitting** automático
- **Image optimization** com Next.js
- **Bundle analysis** configurado
- **Memoização** de componentes pesados
- **Virtual scrolling** para listas grandes

### **2. Sistema de Busca e Filtros**

#### **SearchFilter (`components/common/SearchFilter.tsx`)**
```typescript
interface SearchFilterProps {
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  debounceMs?: number;
  className?: string;
}
```

#### **Filtros Avançados:**
- Busca com debounce
- Filtros múltiplos
- Persistência de filtros
- URL state management

### **3. Sistema de Validação**

#### **Validação de Formulários (`utils/validation-utils.ts`)**
```typescript
export function validateTeamCreate(data: TeamCreate): ValidationErrors {
  const errors: ValidationErrors = {};
  
  if (!data.name?.trim()) {
    errors.name = 'Nome é obrigatório';
  }
  
  if (!data.agent_ids?.length) {
    errors.agents = 'Pelo menos um agente deve ser selecionado';
  }
  
  // ... mais validações
  
  return errors;
}
```

### **4. Tratamento de Erros**

#### **Error Boundaries**
- Captura de erros React
- Fallback components
- Logging automático
- Recovery mechanisms

#### **API Error Handling**
```typescript
export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: any
  ) {
    super(message);
  }
  
  static fromResponse(response: Response, data: any): ApiError {
    return new ApiError(response.status, data.message, data.details);
  }
}
```

### **5. Internacionalização (Preparado)**

#### **Estrutura i18n:**
- Chaves de tradução definidas
- Componentes preparados
- Formatação de datas/números
- Pluralização

---

## 🎨 CONFIGURAÇÕES E ESTILOS

### **1. TailwindCSS Configuration**

#### **tailwind.config.js**
```javascript
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        // ... mais cores
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
```

### **2. Design System**

#### **Cores Principais:**
- **Primary**: Azul (#3b82f6)
- **Success**: Verde (#10b981)
- **Warning**: Amarelo (#f59e0b)
- **Error**: Vermelho (#ef4444)
- **Gray Scale**: Tons de cinza

#### **Tipografia:**
- **Headings**: Inter, system fonts
- **Body**: Inter, system fonts
- **Code**: Fira Code, monospace

#### **Espaçamentos:**
- **Grid**: 8px base unit
- **Containers**: max-width responsivo
- **Padding/Margin**: Escala consistente

### **3. Responsividade**

#### **Breakpoints:**
```css
/* Mobile First */
sm: '640px'   /* Tablet */
md: '768px'   /* Desktop pequeno */
lg: '1024px'  /* Desktop médio */
xl: '1280px'  /* Desktop grande */
2xl: '1536px' /* Desktop extra grande */
```

#### **Componentes Responsivos:**
- Grid layouts adaptativos
- Navigation colapsível
- Modals responsivos
- Tables com scroll horizontal

### **4. Temas e Customização**

#### **Dark Mode (Preparado):**
- Variáveis CSS definidas
- Componentes preparados
- Toggle de tema
- Persistência de preferência

---

## 📚 GUIA DE IMPLEMENTAÇÃO

### **1. Estrutura de Arquivos para Lovable**

```
src/
├── components/
│   ├── ui/              # Componentes base (Button, Input, etc.)
│   ├── layout/          # Layout components (Header, Sidebar, etc.)
│   ├── teams/           # Componentes específicos de equipes
│   ├── executions/      # Componentes de execução
│   ├── notifications/   # Sistema de notificações
│   └── websocket/       # Componentes WebSocket
├── hooks/               # Hooks customizados
├── services/            # Serviços de API
├── types/               # Tipos TypeScript
├── utils/               # Utilitários
└── pages/               # Páginas Next.js
```

### **2. Prioridades de Implementação**

#### **Fase 1: Base (Essencial)**
1. ✅ Componentes UI básicos (Button, Input, Select)
2. ✅ Layout principal (Header, Sidebar)
3. ✅ Sistema de autenticação
4. ✅ Páginas principais (Dashboard, Login)

#### **Fase 2: Core Features**
1. ✅ Sistema de equipes (CRUD completo)
2. ✅ Integração com API Renum
3. ✅ Formulários de criação
4. ✅ Listagens com filtros

#### **Fase 3: Tempo Real**
1. ✅ WebSocket integration
2. ✅ Monitoramento de execuções
3. ✅ Notificações em tempo real
4. ✅ Dashboard de execuções

#### **Fase 4: Avançado**
1. ✅ Sistema de notificações completo
2. ✅ Componentes lazy loading
3. ✅ Otimizações de performance
4. ✅ Error boundaries

### **3. Componentes Críticos para Replicar**

#### **3.1 Dashboard Principal**
```typescript
// Componente principal com estatísticas e listas
export default function Dashboard() {
  const { user } = useAuthStore();
  const { agents, isLoading, error } = useAgentStore();
  
  return (
    <Layout title="Dashboard">
      {/* Estatísticas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard title="Agentes Ativos" value={activeCount} icon={Users} />
        <StatCard title="Execuções Hoje" value={executionsToday} icon={BarChart3} />
        <StatCard title="Bases de Conhecimento" value={kbCount} icon={Database} />
      </div>
      
      {/* Lista de agentes */}
      <AgentsList agents={agents} loading={isLoading} error={error} />
    </Layout>
  );
}
```

#### **3.2 Criação de Equipes**
```typescript
export default function CreateTeamPage() {
  const [formData, setFormData] = useState<TeamFormData>(initialState);
  const { mutate: createTeam, isPending } = useCreateTeam();
  
  return (
    <div className="container mx-auto px-4 py-8">
      <PageHeader title="Criar Nova Equipe" />
      
      <form onSubmit={handleSubmit}>
        <TeamBasicInfo data={formData} onChange={setFormData} />
        <AgentSelector selected={formData.agents} onChange={handleAgentsChange} />
        <WorkflowConfigurator workflow={formData.workflow} onChange={handleWorkflowChange} />
        
        <div className="flex justify-end space-x-3">
          <Button type="button" variant="secondary">Cancelar</Button>
          <Button type="submit" loading={isPending}>Criar Equipe</Button>
        </div>
      </form>
    </div>
  );
}
```

#### **3.3 Monitoramento WebSocket**
```typescript
export function ExecutionMonitor({ executionId }: { executionId: string }) {
  const { isConnected, subscribe } = useWebSocket(`/ws/executions/${executionId}/monitor`);
  const [status, setStatus] = useState<ExecutionStatus>();
  
  useEffect(() => {
    const unsubscribe = subscribe('execution_update', (data) => {
      setStatus(data);
    });
    
    return unsubscribe;
  }, [subscribe]);
  
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium">Execução em Tempo Real</h3>
        <ConnectionIndicator connected={isConnected} />
      </div>
      
      <ProgressBar progress={status?.progress || 0} />
      <AgentStatusGrid agents={status?.agents || []} />
      <ExecutionLogs executionId={executionId} />
    </div>
  );
}
```

### **4. Configurações Essenciais**

#### **4.1 Environment Variables**
```env
NEXT_PUBLIC_API_URL=http://localhost:9000
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:9000/ws
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

#### **4.2 Package.json Dependencies**
```json
{
  "dependencies": {
    "next": "15.0.0",
    "react": "18.0.0",
    "react-dom": "18.0.0",
    "typescript": "5.0.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.0.0",
    "tailwindcss": "^3.0.0",
    "@supabase/supabase-js": "^2.0.0",
    "react-hook-form": "^7.0.0",
    "lucide-react": "^0.300.0"
  }
}
```

### **5. Padrões de Código**

#### **5.1 Estrutura de Componente**
```typescript
interface ComponentProps {
  // Props tipadas
}

export const Component: React.FC<ComponentProps> = ({ 
  prop1, 
  prop2 
}) => {
  // Hooks no topo
  const [state, setState] = useState();
  const { data, isLoading } = useQuery();
  
  // Handlers
  const handleAction = useCallback(() => {
    // Lógica
  }, [dependencies]);
  
  // Early returns
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  // Render principal
  return (
    <div className="component-container">
      {/* JSX */}
    </div>
  );
};
```

#### **5.2 Hooks Customizados**
```typescript
export function useCustomHook(param: string) {
  const [state, setState] = useState();
  
  useEffect(() => {
    // Side effects
  }, [param]);
  
  const actions = useMemo(() => ({
    action1: () => {},
    action2: () => {},
  }), []);
  
  return {
    state,
    ...actions,
  };
}
```

---

## 🎯 CONCLUSÃO

### **O que está 100% implementado:**

1. ✅ **Dashboard completo** com estatísticas e listas
2. ✅ **Sistema de equipes** (CRUD completo)
3. ✅ **Monitoramento em tempo real** via WebSocket
4. ✅ **Sistema de notificações** avançado
5. ✅ **Componentes reutilizáveis** bem estruturados
6. ✅ **Hooks customizados** para todas as funcionalidades
7. ✅ **Integração com APIs** do Renum Backend
8. ✅ **Autenticação** com Supabase
9. ✅ **Interface responsiva** com TailwindCSS
10. ✅ **Tratamento de erros** robusto

### **Para o Lovable implementar:**

1. **Replicar a estrutura** de componentes e hooks
2. **Manter a tipagem TypeScript** completa
3. **Implementar o sistema WebSocket** para tempo real
4. **Seguir os padrões** de código estabelecidos
5. **Usar as configurações** de TailwindCSS
6. **Integrar com as APIs** do Renum Backend existente

### **Resultado esperado:**

Uma aplicação **moderna, funcional e completa** que replica todas as funcionalidades do frontend Renum atual, com melhorias de UX/UI proporcionadas pela expertise do Lovable.

---

**Documento criado em:** 09/01/2025  
**Versão:** 1.0 - Parte 2  
**Status:** Completo e pronto para implementação no Lovable