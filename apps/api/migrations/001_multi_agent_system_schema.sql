-- Migration: 001_multi_agent_system_schema.sql
-- Description: Create complete database schema for multi-agent system
-- Date: 2025-08-16
-- Author: Kiro AI Assistant

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- AGENT REGISTRY TABLES
-- =====================================================

-- Table: agents_registry
-- Purpose: Store agent definitions with versioning and approval workflow
CREATE TABLE IF NOT EXISTS agents_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    input_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'staged', 'approved', 'deprecated')),
    manifest_checksum VARCHAR(64),
    manifest_signature TEXT,
    signature_key_id VARCHAR(50),
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, version)
);

-- Table: agent_templates
-- Purpose: Store reusable agent templates for quick creation
CREATE TABLE IF NOT EXISTS agent_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    template_data JSONB NOT NULL,
    is_public BOOLEAN DEFAULT false,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INTEGRATION TABLES
-- =====================================================

-- Table: integrations
-- Purpose: Store user integrations with external platforms
CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('whatsapp', 'telegram', 'zapier', 'n8n', 'make', 'gmail', 'supabase', 'generic')),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    token VARCHAR(500) NOT NULL,
    webhook_url TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error', 'expired')),
    rate_limit_per_minute INTEGER DEFAULT 60,
    last_used_at TIMESTAMP WITH TIME ZONE,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: webhook_logs
-- Purpose: Store detailed logs of webhook processing
CREATE TABLE IF NOT EXISTS webhook_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_id UUID REFERENCES integrations(id) ON DELETE CASCADE,
    request_id VARCHAR(100),
    method VARCHAR(10) NOT NULL,
    headers JSONB,
    payload JSONB,
    response_status INTEGER,
    response_body JSONB,
    processing_time_ms INTEGER,
    error_message TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: integration_analytics
-- Purpose: Store daily analytics for integrations
CREATE TABLE IF NOT EXISTS integration_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_id UUID REFERENCES integrations(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    avg_response_time_ms DECIMAL(10,2),
    total_cost DECIMAL(10,4) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(integration_id, date)
);

-- =====================================================
-- MULTI-AGENT EXECUTION TABLES
-- =====================================================

-- Table: multi_agent_executions
-- Purpose: Store multi-agent execution sessions
CREATE TABLE IF NOT EXISTS multi_agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    orchestrator_session_id VARCHAR(100),
    plan JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    agents_used JSONB DEFAULT '[]'::jsonb,
    total_cost DECIMAL(10,4) DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: agent_execution_steps
-- Purpose: Store individual agent execution steps within a multi-agent execution
CREATE TABLE IF NOT EXISTS agent_execution_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID REFERENCES multi_agent_executions(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    agent_version VARCHAR(20) NOT NULL,
    step_order INTEGER NOT NULL,
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    error_message TEXT,
    execution_time_ms INTEGER,
    cost DECIMAL(10,4) DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- BYOC (BRING YOUR OWN CREDENTIALS) TABLES
-- =====================================================

-- Table: user_credentials
-- Purpose: Store encrypted user credentials for external services
CREATE TABLE IF NOT EXISTS user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    service_type VARCHAR(50) NOT NULL,
    service_name VARCHAR(200),
    encrypted_credentials TEXT NOT NULL,
    scopes JSONB DEFAULT '[]'::jsonb,
    expires_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'error', 'revoked')),
    last_validated_at TIMESTAMP WITH TIME ZONE,
    validation_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- ADMIN AND GOVERNANCE TABLES
-- =====================================================

-- Table: feature_toggles
-- Purpose: Store feature flags for tenant-specific controls
CREATE TABLE IF NOT EXISTS feature_toggles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_name VARCHAR(100) NOT NULL,
    description TEXT,
    enabled_globally BOOLEAN DEFAULT false,
    tenant_rules JSONB DEFAULT '{}'::jsonb,
    rollout_percentage INTEGER DEFAULT 0 CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(feature_name)
);

-- Table: audit_logs
-- Purpose: Store immutable audit trail for all critical operations
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: system_keys
-- Purpose: Store public keys for manifest signature verification
CREATE TABLE IF NOT EXISTS system_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id VARCHAR(50) NOT NULL UNIQUE,
    key_type VARCHAR(20) NOT NULL DEFAULT 'RSA256',
    public_key TEXT NOT NULL,
    private_key_hash VARCHAR(64), -- Hash of private key for verification
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'expired')),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- SANDBOX AND TESTING TABLES
-- =====================================================

-- Table: sandbox_executions
-- Purpose: Store sandbox execution logs separate from production
CREATE TABLE IF NOT EXISTS sandbox_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    agent_version VARCHAR(20) NOT NULL,
    test_scenario JSONB,
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    error_message TEXT,
    execution_time_ms INTEGER,
    resource_usage JSONB, -- CPU, memory usage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Agents Registry Indexes
CREATE INDEX IF NOT EXISTS idx_agents_registry_agent_id ON agents_registry(agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_registry_status ON agents_registry(status);
CREATE INDEX IF NOT EXISTS idx_agents_registry_created_by ON agents_registry(created_by);

-- Integrations Indexes
CREATE INDEX IF NOT EXISTS idx_integrations_user_id ON integrations(user_id);
CREATE INDEX IF NOT EXISTS idx_integrations_type ON integrations(type);
CREATE INDEX IF NOT EXISTS idx_integrations_status ON integrations(status);
CREATE INDEX IF NOT EXISTS idx_integrations_token ON integrations(token);

-- Webhook Logs Indexes
CREATE INDEX IF NOT EXISTS idx_webhook_logs_integration_id ON webhook_logs(integration_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_request_id ON webhook_logs(request_id);

-- Multi-Agent Executions Indexes
CREATE INDEX IF NOT EXISTS idx_multi_agent_executions_user_id ON multi_agent_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_executions_status ON multi_agent_executions(status);
CREATE INDEX IF NOT EXISTS idx_multi_agent_executions_session_id ON multi_agent_executions(orchestrator_session_id);

-- Agent Execution Steps Indexes
CREATE INDEX IF NOT EXISTS idx_agent_execution_steps_execution_id ON agent_execution_steps(execution_id);
CREATE INDEX IF NOT EXISTS idx_agent_execution_steps_agent_id ON agent_execution_steps(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_execution_steps_status ON agent_execution_steps(status);

-- User Credentials Indexes
CREATE INDEX IF NOT EXISTS idx_user_credentials_user_id ON user_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credentials_service_type ON user_credentials(service_type);
CREATE INDEX IF NOT EXISTS idx_user_credentials_status ON user_credentials(status);

-- Audit Logs Indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Analytics Indexes
CREATE INDEX IF NOT EXISTS idx_integration_analytics_integration_id ON integration_analytics(integration_id);
CREATE INDEX IF NOT EXISTS idx_integration_analytics_date ON integration_analytics(date);

-- Sandbox Indexes
CREATE INDEX IF NOT EXISTS idx_sandbox_executions_user_id ON sandbox_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_sandbox_executions_agent_id ON sandbox_executions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sandbox_executions_created_at ON sandbox_executions(created_at);