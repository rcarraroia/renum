-- Criação da tabela de execuções
-- Execute este script no Supabase SQL Editor

-- Tabela de execuções
CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    input_data JSONB NOT NULL DEFAULT '{}',
    execution_config JSONB NOT NULL DEFAULT '{}',
    progress JSONB NOT NULL DEFAULT '{}',
    results JSONB NOT NULL DEFAULT '[]',
    logs JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    estimated_completion TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_executions_user_id ON executions(user_id);
CREATE INDEX IF NOT EXISTS idx_executions_team_id ON executions(team_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_created_at ON executions(created_at DESC);

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_executions_updated_at 
    BEFORE UPDATE ON executions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- RLS (Row Level Security) para execuções
ALTER TABLE executions ENABLE ROW LEVEL SECURITY;

-- Política: usuários só podem ver suas próprias execuções
CREATE POLICY "Users can view own executions" ON executions
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Política: usuários só podem inserir execuções para si mesmos
CREATE POLICY "Users can insert own executions" ON executions
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

-- Política: usuários só podem atualizar suas próprias execuções
CREATE POLICY "Users can update own executions" ON executions
    FOR UPDATE USING (auth.uid()::text = user_id::text);

-- Política: usuários só podem deletar suas próprias execuções
CREATE POLICY "Users can delete own executions" ON executions
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- Comentários para documentação
COMMENT ON TABLE executions IS 'Armazena execuções de equipes de agentes';
COMMENT ON COLUMN executions.id IS 'ID único da execução';
COMMENT ON COLUMN executions.team_id IS 'ID da equipe sendo executada';
COMMENT ON COLUMN executions.user_id IS 'ID do usuário que iniciou a execução';
COMMENT ON COLUMN executions.status IS 'Status da execução (pending, running, completed, failed, cancelled)';
COMMENT ON COLUMN executions.input_data IS 'Dados de entrada para a execução';
COMMENT ON COLUMN executions.execution_config IS 'Configuração da execução (timeout, retry, etc)';
COMMENT ON COLUMN executions.progress IS 'Progresso atual da execução';
COMMENT ON COLUMN executions.results IS 'Resultados dos agentes executados';
COMMENT ON COLUMN executions.logs IS 'Logs da execução';
COMMENT ON COLUMN executions.started_at IS 'Timestamp de início da execução';
COMMENT ON COLUMN executions.completed_at IS 'Timestamp de conclusão da execução';
COMMENT ON COLUMN executions.estimated_completion IS 'Estimativa de conclusão';
COMMENT ON COLUMN executions.error_message IS 'Mensagem de erro se houver falha';