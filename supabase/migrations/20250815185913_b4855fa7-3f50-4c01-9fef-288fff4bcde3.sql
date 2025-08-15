
-- Script SQL para configurar o banco Supabase
-- Execute este script no SQL Editor do Supabase Dashboard

-- 1. Criar tabela de teams
CREATE TABLE IF NOT EXISTS public.teams (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    workflow_type VARCHAR(20) NOT NULL DEFAULT 'sequential',
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agents JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_teams_user_id ON public.teams(user_id);
CREATE INDEX IF NOT EXISTS idx_teams_status ON public.teams(status);
CREATE INDEX IF NOT EXISTS idx_teams_created_at ON public.teams(created_at);

-- 3. Habilitar RLS (Row Level Security)
ALTER TABLE public.teams ENABLE ROW LEVEL SECURITY;

-- 4. Criar políticas de segurança
-- Usuários só podem ver suas próprias teams
CREATE POLICY "Users can view own teams" ON public.teams
    FOR SELECT USING (auth.uid() = user_id);

-- Usuários só podem inserir teams para si mesmos
CREATE POLICY "Users can insert own teams" ON public.teams
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Usuários só podem atualizar suas próprias teams
CREATE POLICY "Users can update own teams" ON public.teams
    FOR UPDATE USING (auth.uid() = user_id);

-- Usuários só podem deletar suas próprias teams
CREATE POLICY "Users can delete own teams" ON public.teams
    FOR DELETE USING (auth.uid() = user_id);

-- 5. Criar função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. Criar trigger para atualizar updated_at
CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON public.teams
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 7. Criar tabela de execuções (para futuro)
CREATE TABLE IF NOT EXISTS public.team_executions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id UUID NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    input_data JSONB DEFAULT '{}'::jsonb,
    results JSONB DEFAULT '[]'::jsonb,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. RLS para execuções
ALTER TABLE public.team_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own executions" ON public.team_executions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own executions" ON public.team_executions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own executions" ON public.team_executions
    FOR UPDATE USING (auth.uid() = user_id);

-- 9. Trigger para execuções
CREATE TRIGGER set_updated_at_executions
    BEFORE UPDATE ON public.team_executions
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- Verificar se tudo foi criado corretamente
SELECT 
    schemaname,
    tablename,
    tableowner,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('teams', 'team_executions');

-- Verificar políticas RLS
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies 
WHERE schemaname = 'public' 
AND tablename IN ('teams', 'team_executions');
