# Módulo de Programação RENUM DevStudio - Requisitos

## Visão Geral

O Módulo de Programação RENUM DevStudio é uma extensão do painel administrativo que integra um fork customizado do VSCode para fornecer capacidades avançadas de desenvolvimento assistido por IA. O módulo permite que administradores criem, editem e gerenciem projetos de código com assistência de agentes IA especializados.

## Objetivos Principais

### 1. Integração Administrativa
- **Acesso Restrito**: Disponível apenas no painel administrativo
- **Autenticação Unificada**: Usar tokens JWT do sistema RENUM
- **Permissões Granulares**: Controle de acesso por funcionalidade
- **Auditoria Completa**: Log de todas as ações e execuções

### 2. Desenvolvimento Assistido por IA
- **Spec Sessions**: Sessões estruturadas de especificação e desenvolvimento
- **Geração de Código**: Criação automática baseada em especificações
- **Refatoração Inteligente**: Melhorias e otimizações de código existente
- **Testes Automáticos**: Geração e execução de testes unitários/integração

### 3. Execução Segura
- **Sandbox Containerizado**: Execução isolada de código e comandos
- **Controle de Recursos**: Limites de CPU, memória e tempo
- **Validação de Patches**: Revisão de alterações antes da aplicação
- **Rollback Automático**: Reversão em caso de falhas

### 4. Integração CI/CD
- **Pipeline Generation**: Criação automática de workflows
- **Deploy Assistido**: Integração com provedores de cloud
- **Monitoramento**: Status de builds, testes e deploys
- **Notificações**: Alertas de sucesso/falha

## Customizações do Fork VSCode

### Configurações Obrigatórias
- **Branding**: Ajustar product.json (nome: "RENUM DevStudio", ícone, cores)
- **Marketplace**: Apontar OpenVSX como galeria padrão
- **Telemetria**: Desabilitar telemetria Microsoft por padrão
- **Extensão Built-in**: Empacotar renum-devstudio-agent como extensão nativa
- **Recomendações**: Desabilitar recomendações automáticas do upstream que não se apliquem

### Arquivos de Configuração
- `product.json`: Nome, ícone, galeria OpenVSX, desabilitar serviços MS
- `extensions/renum-devstudio-agent/`: Extensão principal como built-in
- Remover/modificar referências à telemetria e serviços Microsoft

## Modelo de Dados (DevStudio)

### Schema e Convenções
- **Schema**: `devstudio` dedicado no PostgreSQL
- **Prefixo**: Todas as tabelas com prefixo `ds_`
- **Multi-tenant**: Coluna `tenant_id` obrigatória em todas as tabelas
- **Auditoria**: Coluna `source_module='devstudio'` para rastreamento
- **RLS**: Row-Level Security habilitado por tenant

### Entidades Principais

```sql
-- Projetos de desenvolvimento
devstudio.ds_projects (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(100),
    repo VARCHAR(500),
    provider VARCHAR(20), -- 'github', 'gitlab'
    created_at TIMESTAMP,
    source_module VARCHAR(20) DEFAULT 'devstudio'
);

-- Sessões de especificação
devstudio.ds_spec_sessions (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES ds_projects(id),
    status VARCHAR(20), -- 'draft', 'active', 'completed'
    author_id UUID NOT NULL,
    created_at TIMESTAMP,
    source_module VARCHAR(20) DEFAULT 'devstudio'
);

-- Especificações (requirements, design, tasks)
devstudio.ds_specs (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES ds_spec_sessions(id),
    type VARCHAR(20), -- 'requirements', 'design', 'tasks'
    content TEXT,
    version INTEGER DEFAULT 1,
    updated_at TIMESTAMP,
    source_module VARCHAR(20) DEFAULT 'devstudio'
);

-- Tasks de desenvolvimento
devstudio.ds_tasks (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES ds_spec_sessions(id),
    title VARCHAR(200),
    status VARCHAR(20), -- 'todo', 'in_progress', 'review', 'done'
    assignee VARCHAR(10), -- 'agent', 'human'
    dod TEXT, -- Definition of Done
    links JSONB, -- PRs, commits, etc.
    priority VARCHAR(10), -- 'low', 'medium', 'high'
    source_module VARCHAR(20) DEFAULT 'devstudio'
);

-- Execuções (geração, testes, build, deploy)
devstudio.ds_runs (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES ds_projects(id),
    type VARCHAR(20), -- 'gen', 'test', 'build', 'deploy'
    status VARCHAR(20), -- 'pending', 'running', 'success', 'failed'
    logs_url VARCHAR(500),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    metrics_json JSONB, -- tokens, custo, performance
    source_module VARCHAR(20) DEFAULT 'devstudio'
);

-- Integrações CI/CD
devstudio.ds_ci_integrations (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES ds_projects(id),
    provider VARCHAR(20), -- 'github', 'gitlab'
    pipeline_ref VARCHAR(200),
    branch VARCHAR(100) DEFAULT 'main',
    source_module VARCHAR(20) DEFAULT 'devstudio'
);

-- Configurações de agentes IA
devstudio.ds_agent_settings (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES ds_projects(id),
    model VARCHAR(50), -- 'gpt-4', 'claude-3-sonnet'
    policy JSONB, -- políticas de uso
    token_limits JSONB, -- limites por operação
    source_module VARCHAR(20) DEFAULT 'devstudio'
);

-- Storage chave-valor para estados efêmeros
devstudio.ds_kv (
    scope VARCHAR(50), -- 'session', 'project', 'global'
    key VARCHAR(200),
    value_json JSONB,
    expires_at TIMESTAMP,
    source_module VARCHAR(20) DEFAULT 'devstudio',
    PRIMARY KEY (scope, key)
);
```

## API Interna (v1)

### Endpoints Principais

```http
# Spec Sessions
POST   /api/v1/spec-sessions              # Criar nova spec session
GET    /api/v1/spec-sessions              # Listar spec sessions
GET    /api/v1/spec-sessions/:id          # Obter spec session
PUT    /api/v1/spec-sessions/:id          # Atualizar spec session
POST   /api/v1/spec-sessions/:id/sync     # Sincronizar MD ↔ DB

# Planejamento e Geração
POST   /api/v1/plan                       # Gerar plano de tasks (requirements → design → tasks)
POST   /api/v1/code/apply                 # Aplicar patch assinado
POST   /api/v1/code/preview               # Preview de alterações

# Execução
POST   /api/v1/exec                       # Enfileirar job (test/build/deploy)
GET    /api/v1/exec/:id                   # Status de execução
GET    /api/v1/exec/:id/logs              # Logs em tempo real

# CI/CD
POST   /api/v1/ci/report                  # Callback de status de CI
GET    /api/v1/ci/status/:project_id      # Status atual do pipeline

# IA Orchestration
POST   /api/v1/ai/generate                # Rotear para modelos (sem chaves no cliente)
GET    /api/v1/ai/models                  # Modelos disponíveis
POST   /api/v1/ai/optimize                # Otimizar prompt/contexto
```

### Contratos de Request/Response

```typescript
// Spec Session
interface CreateSpecSessionRequest {
    project_id: string;
    title: string;
    description?: string;
}

interface SpecSessionResponse {
    id: string;
    project_id: string;
    status: 'draft' | 'active' | 'completed';
    specs: {
        requirements?: string;
        design?: string;
        tasks?: string;
    };
    created_at: string;
}

// Code Generation
interface CodeGenerationRequest {
    task_id: string;
    context: string;
    model?: 'gpt-4' | 'claude-3-sonnet';
}

interface CodeGenerationResponse {
    patch: string;
    preview_url: string;
    estimated_changes: number;
    confidence_score: number;
}

// Execution
interface ExecutionRequest {
    project_id: string;
    type: 'test' | 'build' | 'deploy';
    command: string;
    environment?: Record<string, string>;
}

interface ExecutionResponse {
    id: string;
    status: 'pending' | 'running' | 'success' | 'failed';
    logs_url: string;
    started_at?: string;
    metrics?: {
        duration_ms: number;
        exit_code: number;
        resource_usage: object;
    };
}
```

## Requisitos Funcionais

### RF01 - Autenticação e Autorização
- **RF01.1**: Integração com sistema de autenticação RENUM
- **RF01.2**: Verificação de permissões administrativas
- **RF01.3**: Controle de acesso por funcionalidade (spec, code, deploy)
- **RF01.4**: Sessões seguras com timeout automático
- **RF01.5**: Papéis definidos: admin_devstudio, reviewer, executor, viewer
- **RF01.6**: Matriz CRUD por funcionalidade (spec, code, exec, deploy) por papel

### RF02 - Interface DevStudio
- **RF02.1**: Fork customizado do VSCode integrado ao painel admin
- **RF02.2**: Branding RENUM (nome, ícone, cores)
- **RF02.3**: Marketplace OpenVSX como galeria padrão
- **RF02.4**: Extensão "RENUM DevStudio Agent" como built-in
- **RF02.5**: Ajustar product.json (branding/galeria), desabilitar telemetria por padrão
- **RF02.6**: Views mínimas: "Spec Sessions" (árvore), "Dev Tasks" (board), "Runs & Logs" (filtros)
- **RF02.7**: Comandos principais: "DevStudio: Start Spec Session", "DevStudio: Apply Patch", "DevStudio: Open Run Logs"

### RF03 - Spec Sessions
- **RF03.1**: Criação de sessões de especificação estruturadas
- **RF03.2**: Trio de arquivos: requirements.md, design.md, tasks.md
- **RF03.3**: Sincronização automática com banco de dados
- **RF03.4**: Versionamento e histórico de alterações
- **RF03.5**: Colaboração em tempo real (futuro)

### RF04 - Geração de Código
- **RF04.1**: Geração baseada em especificações e tasks
- **RF04.2**: Suporte a múltiplas linguagens e frameworks
- **RF04.3**: Templates de projeto (web, api, mobile)
- **RF04.4**: Aplicação de patches com validação e assinatura digital
- **RF04.5**: Preview de alterações antes da aplicação
- **RF04.6**: Política de aprovação dupla (2-man rule) para branches protegidas
- **RF04.7**: Patches assinados com preview obrigatório

### RF05 - Execução e Testes
- **RF05.1**: Runner containerizado para execução segura
- **RF05.2**: Execução de comandos (npm test, build, lint)
- **RF05.3**: Captura e exibição de logs em tempo real
- **RF05.4**: Geração automática de testes unitários
- **RF05.5**: Relatórios de cobertura de código
- **RF05.6**: Container não-root, rede bloqueada por padrão
- **RF05.7**: Allowlist de rede por tarefa, quotas cgroup e TTL por job

### RF06 - CI/CD Integration
- **RF06.1**: Geração de pipelines GitHub Actions/GitLab CI
- **RF06.2**: Configuração de deploy automático
- **RF06.3**: MVP: GitHub Actions + Vercel/Render; AWS em Fase 2
- **RF06.4**: Monitoramento de status de builds
- **RF06.5**: Notificações de sucesso/falha
- **RF06.6**: Callback endpoint para status de CI (/ci/report)

### RF07 - Gerenciamento de Projetos
- **RF07.1**: CRUD de projetos de desenvolvimento
- **RF07.2**: Organização por categorias/tags
- **RF07.3**: Clonagem e fork de projetos existentes
- **RF07.4**: Backup automático e versionamento
- **RF07.5**: Exportação de projetos

### RF08 - Integração com IA
- **RF08.1**: Suporte a múltiplos modelos (GPT-5, Claude Sonnet 4.0)
- **RF08.2**: Seleção de modelo por projeto/tarefa
- **RF08.3**: Controle de tokens e custos por tenant
- **RF08.4**: Cache de contexto para otimização
- **RF08.5**: Políticas de uso e compliance
- **RF08.6**: Rate limiting por tenant e por usuário
- **RF08.7**: Métricas: tokens in/out, custo estimado, tempo de geração, taxa de sucesso

## Requisitos Não Funcionais

### RNF01 - Performance
- **RNF01.1**: Tempo de carregamento do DevStudio < 3 segundos
- **RNF01.2**: Relatórios p50/p95 por operação (geração, testes, build, deploy)
- **RNF01.3**: Métricas por tamanho do contexto/diff
- **RNF01.4**: Sincronização de specs < 1 segundo
- **RNF01.5**: Geração de código p95 < 45 segundos para projetos médios
- **RNF01.6**: Execução de testes p95 < 8 minutos para suites completas

### RNF02 - Segurança
- **RNF02.1**: Execução em containers isolados
- **RNF02.2**: Validação de entrada para prevenir code injection
- **RNF02.3**: Criptografia de dados sensíveis em trânsito/repouso
- **RNF02.4**: Auditoria completa de ações administrativas
- **RNF02.5**: Rate limiting para APIs de IA
- **RNF02.6**: Row-Level Security habilitado por tenant
- **RNF02.7**: tenant_id obrigatório em todas as tabelas e requests
- **RNF02.8**: Runner executa em container não-root, rede bloqueada por padrão

### RNF03 - Escalabilidade
- **RNF03.1**: Suporte a múltiplas sessões simultâneas
- **RNF03.2**: Auto-scaling de containers de execução
- **RNF03.3**: Cache distribuído para otimização
- **RNF03.4**: Balanceamento de carga para APIs
- **RNF03.5**: Rate limiting por tenant para endpoints de IA
- **RNF03.6**: Métricas de uso armazenadas por run e por tarefa

### RNF04 - Disponibilidade
- **RNF04.1**: Uptime 99.9% para o módulo
- **RNF04.2**: Recuperação automática de falhas
- **RNF04.3**: Backup automático de dados críticos
- **RNF04.4**: Monitoramento proativo de saúde
- **RNF04.5**: Snapshot de specs por release/deploy
- **RNF04.6**: Retenção de artefatos críticos vinculada a logs de auditoria

### RNF05 - Usabilidade
- **RNF05.1**: Interface intuitiva para desenvolvedores
- **RNF05.2**: Documentação integrada e contextual
- **RNF05.3**: Feedback visual de progresso
- **RNF05.4**: Atalhos de teclado customizáveis

## Restrições e Limitações

### Técnicas
- **RT01**: Uso obrigatório do fork VSCode fornecido
- **RT02**: Integração apenas via painel administrativo
- **RT03**: Execução em containers Docker
- **RT04**: Uso do banco PostgreSQL existente
- **RT05**: Compatibilidade com arquitetura RENUM atual

### Negócio
- **RN01**: Acesso restrito a administradores
- **RN02**: Compliance com políticas de segurança
- **RN03**: Controle de custos de IA por projeto
- **RN04**: Auditoria obrigatória de todas as ações

### Regulatórias
- **RR01**: Proteção de dados pessoais (LGPD/GDPR)
- **RR02**: Logs de auditoria por 2 anos
- **RR03**: Criptografia de dados sensíveis
- **RR04**: Controle de acesso baseado em funções

## Critérios de Aceitação

### Funcionalidade Core
- [ ] Autenticação administrativa funcional com papéis definidos
- [ ] DevStudio carrega e funciona no painel admin
- [ ] Spec Sessions podem ser criadas e gerenciadas
- [ ] Geração de código básica funcional
- [ ] Execução segura em containers
- [ ] Integração com pelo menos um modelo de IA
- [ ] UX com 3 views mínimas (Specs / Tasks / Runs & Logs) e comandos listados

### Segurança e Isolamento
- [ ] Todas as execuções são isoladas
- [ ] Logs de auditoria são gerados
- [ ] Validação de entrada implementada
- [ ] Controle de acesso granular funcional
- [ ] **Patches assinados com preview + (opcional) dupla aprovação para branches protegidas**
- [ ] **Runner em container não-root, rede bloqueada por padrão, TTL e quotas por job**
- [ ] **RLS ativo; dados isolados por tenant_id**

### Performance e Métricas
- [ ] Carregamento em menos de 3 segundos
- [ ] **Relatórios p50/p95 por operação implementados**
- [ ] Interface responsiva e fluida
- [ ] **Métricas IA armazenadas (tokens, custo, tempo) por run e por tarefa**

### Integração e Multi-tenant
- [ ] Comunicação com backend RENUM
- [ ] Sincronização com banco de dados
- [ ] Integração com sistema de autenticação
- [ ] **tenant_id obrigatório em todas as operações**
- [ ] **Row-Level Security configurado e testado**

### Fork VSCode
- [ ] **product.json customizado com branding RENUM**
- [ ] **OpenVSX configurado como marketplace padrão**
- [ ] **Telemetria Microsoft desabilitada**
- [ ] **renum-devstudio-agent empacotado como built-in**

### CI/CD MVP
- [ ] **GitHub Actions funcional**
- [ ] **Deploy Vercel/Render implementado**
- [ ] **Callback /ci/report funcionando**

### API Interna
- [ ] **Todos os endpoints v1 funcionais**
- [ ] **Contratos de request/response validados**
- [ ] **Rate limiting por tenant implementado**

## Dependências

### Internas
- Sistema de autenticação RENUM
- Banco de dados PostgreSQL
- API backend RENUM
- Sistema de permissões administrativas

### Externas
- Fork do VSCode (devstudio)
- Docker para containerização
- APIs de IA (OpenAI, Anthropic)
- OpenVSX marketplace
- Provedores de CI/CD

## Riscos Identificados

### Alto Risco
- **R01**: Complexidade de integração VSCode fork
- **R02**: Segurança de execução de código arbitrário
- **R03**: Performance com múltiplas sessões simultâneas

### Médio Risco
- **R04**: Custos de APIs de IA
- **R05**: Compatibilidade com diferentes projetos
- **R06**: Manutenção do fork VSCode

### Baixo Risco
- **R07**: Adoção pelos administradores
- **R08**: Documentação e treinamento
- **R09**: Backup e recuperação

## Próximos Passos

1. **Análise Técnica**: Revisar fork VSCode e planejar customizações
2. **Design da Arquitetura**: Definir componentes e integrações
3. **Prototipagem**: Criar MVP com funcionalidades básicas
4. **Implementação Faseada**: Desenvolver por módulos
5. **Testes e Validação**: Garantir segurança e performance
6. **Deploy e Monitoramento**: Colocar em produção com observabilidade