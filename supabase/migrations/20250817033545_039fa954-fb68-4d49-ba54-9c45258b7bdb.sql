
-- Executando migração 001: Schema do sistema multiagente
-- Criando tabelas para agents registry
CREATE TABLE IF NOT EXISTS public.agents_registry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    name VARCHAR(200) NOT NULL,
    description TEXT,
    capabilities JSONB DEFAULT '[]'::jsonb,
    input_schema JSONB DEFAULT '{}'::jsonb,
    policy JSONB DEFAULT '{}'::jsonb,
    dependencies JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(20) DEFAULT 'active',
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, version)
);

-- Criando tabelas para conexões de tenant (BYOC)
CREATE TABLE IF NOT EXISTS public.tenant_connections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service_name VARCHAR(100) NOT NULL,
    connection_type VARCHAR(50) NOT NULL, -- 'oauth', 'api_key', 'credentials'
    credentials JSONB NOT NULL, -- Criptografado
    scopes JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(20) DEFAULT 'active',
    expires_at TIMESTAMP WITH TIME ZONE,
    last_validated TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, service_name)
);

-- Criando tabelas para workflows
CREATE TABLE IF NOT EXISTS public.workflows (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    workflow_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    agents_used JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Criando tabelas para execuções de workflows
CREATE TABLE IF NOT EXISTS public.workflow_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES public.workflows(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    input_data JSONB DEFAULT '{}'::jsonb,
    results JSONB DEFAULT '[]'::jsonb,
    execution_logs JSONB DEFAULT '[]'::jsonb,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Criando tabelas para logs de execução
CREATE TABLE IF NOT EXISTS public.execution_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES public.workflow_runs(id) ON DELETE CASCADE,
    agent_id VARCHAR(100),
    step_number INTEGER,
    log_level VARCHAR(20) DEFAULT 'info',
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Criando tabelas para requisições de integração
CREATE TABLE IF NOT EXISTS public.integration_requests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service_name VARCHAR(100) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'low',
    status VARCHAR(20) DEFAULT 'pending',
    votes INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Criando tabelas para métricas de billing
CREATE TABLE IF NOT EXISTS public.billing_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    run_id UUID REFERENCES public.workflow_runs(id) ON DELETE SET NULL,
    metric_type VARCHAR(50) NOT NULL, -- 'workflow_execution', 'agent_call', 'api_request'
    agent_id VARCHAR(100),
    quantity INTEGER DEFAULT 1,
    cost_cents INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_agents_registry_agent_id ON public.agents_registry(agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_registry_status ON public.agents_registry(status);
CREATE INDEX IF NOT EXISTS idx_tenant_connections_tenant_id ON public.tenant_connections(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_connections_service ON public.tenant_connections(service_name);
CREATE INDEX IF NOT EXISTS idx_workflows_user_id ON public.workflows(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow_id ON public.workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_id ON public.workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON public.workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_execution_logs_run_id ON public.execution_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_billing_metrics_user_id ON public.billing_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_billing_metrics_created_at ON public.billing_metrics(created_at);

-- Habilitar RLS em todas as tabelas
ALTER TABLE public.agents_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.execution_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_metrics ENABLE ROW LEVEL SECURITY;

-- Políticas RLS para agents_registry (público para leitura, apenas criadores podem modificar)
CREATE POLICY "Anyone can view active agents" ON public.agents_registry
    FOR SELECT USING (status = 'active');

CREATE POLICY "Users can create agents" ON public.agents_registry
    FOR INSERT WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users can update own agents" ON public.agents_registry
    FOR UPDATE USING (auth.uid() = created_by);

-- Políticas RLS para tenant_connections
CREATE POLICY "Users can view own connections" ON public.tenant_connections
    FOR SELECT USING (auth.uid() = tenant_id);

CREATE POLICY "Users can insert own connections" ON public.tenant_connections
    FOR INSERT WITH CHECK (auth.uid() = tenant_id);

CREATE POLICY "Users can update own connections" ON public.tenant_connections
    FOR UPDATE USING (auth.uid() = tenant_id);

CREATE POLICY "Users can delete own connections" ON public.tenant_connections
    FOR DELETE USING (auth.uid() = tenant_id);

-- Políticas RLS para workflows
CREATE POLICY "Users can view own workflows" ON public.workflows
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own workflows" ON public.workflows
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own workflows" ON public.workflows
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own workflows" ON public.workflows
    FOR DELETE USING (auth.uid() = user_id);

-- Políticas RLS para workflow_runs
CREATE POLICY "Users can view own workflow runs" ON public.workflow_runs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own workflow runs" ON public.workflow_runs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own workflow runs" ON public.workflow_runs
    FOR UPDATE USING (auth.uid() = user_id);

-- Políticas RLS para execution_logs (através de workflow_runs)
CREATE POLICY "Users can view own execution logs" ON public.execution_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.workflow_runs 
            WHERE workflow_runs.id = execution_logs.run_id 
            AND workflow_runs.user_id = auth.uid()
        )
    );

CREATE POLICY "System can insert execution logs" ON public.execution_logs
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.workflow_runs 
            WHERE workflow_runs.id = execution_logs.run_id 
            AND workflow_runs.user_id = auth.uid()
        )
    );

-- Políticas RLS para integration_requests
CREATE POLICY "Users can view integration requests" ON public.integration_requests
    FOR SELECT USING (true);

CREATE POLICY "Users can insert integration requests" ON public.integration_requests
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own integration requests" ON public.integration_requests
    FOR UPDATE USING (auth.uid() = user_id);

-- Políticas RLS para billing_metrics
CREATE POLICY "Users can view own billing metrics" ON public.billing_metrics
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "System can insert billing metrics" ON public.billing_metrics
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Triggers para updated_at
CREATE TRIGGER set_updated_at_agents_registry
    BEFORE UPDATE ON public.agents_registry
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_tenant_connections
    BEFORE UPDATE ON public.tenant_connections
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_workflows
    BEFORE UPDATE ON public.workflows
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_workflow_runs
    BEFORE UPDATE ON public.workflow_runs
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_integration_requests
    BEFORE UPDATE ON public.integration_requests
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- Inserir alguns agentes de exemplo
INSERT INTO public.agents_registry (agent_id, name, description, capabilities, input_schema, policy) VALUES
('sa-gmail', 'Gmail Agent', 'Agent for Gmail operations', 
 '["send_email", "read_email", "search_email"]'::jsonb,
 '{"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}}'::jsonb,
 '{"required_scopes": ["https://www.googleapis.com/auth/gmail.send"]}'::jsonb),
('sa-supabase', 'Supabase Agent', 'Agent for Supabase database operations',
 '["query", "insert", "update", "delete"]'::jsonb,
 '{"type": "object", "properties": {"table": {"type": "string"}, "action": {"type": "string"}, "data": {"type": "object"}}}'::jsonb,
 '{"required_credentials": ["supabase_url", "supabase_key"]}'::jsonb),
('sa-http', 'HTTP Agent', 'Generic HTTP requests agent',
 '["get", "post", "put", "delete", "patch"]'::jsonb,
 '{"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}, "headers": {"type": "object"}, "body": {"type": "object"}}}'::jsonb,
 '{}'::jsonb);
