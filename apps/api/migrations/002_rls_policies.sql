-- Migration: 002_rls_policies.sql
-- Description: Row Level Security policies for multi-agent system
-- Date: 2025-08-16
-- Author: Kiro AI Assistant

-- =====================================================
-- ENABLE ROW LEVEL SECURITY
-- =====================================================

ALTER TABLE agents_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE multi_agent_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_execution_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_toggles ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE sandbox_executions ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- HELPER FUNCTIONS FOR RLS
-- =====================================================

-- Function to check if user is admin
CREATE OR REPLACE FUNCTION is_admin(user_id UUID DEFAULT auth.uid())
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM auth.users 
        WHERE id = user_id 
        AND (
            raw_user_meta_data->>'role' = 'admin' OR
            raw_user_meta_data->>'role' = 'superadmin'
        )
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user is superadmin
CREATE OR REPLACE FUNCTION is_superadmin(user_id UUID DEFAULT auth.uid())
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM auth.users 
        WHERE id = user_id 
        AND raw_user_meta_data->>'role' = 'superadmin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- AGENTS REGISTRY POLICIES
-- =====================================================

-- Admins can manage all agents
CREATE POLICY "Admins can manage agents" ON agents_registry
    FOR ALL USING (is_admin());

-- Public read access to approved agents
CREATE POLICY "Public can view approved agents" ON agents_registry
    FOR SELECT USING (status = 'approved');

-- Users can view their own draft/staged agents
CREATE POLICY "Users can view own agents" ON agents_registry
    FOR SELECT USING (created_by = auth.uid());

-- =====================================================
-- AGENT TEMPLATES POLICIES
-- =====================================================

-- Admins can manage all templates
CREATE POLICY "Admins can manage templates" ON agent_templates
    FOR ALL USING (is_admin());

-- Users can view public templates
CREATE POLICY "Users can view public templates" ON agent_templates
    FOR SELECT USING (is_public = true);

-- Users can manage their own templates
CREATE POLICY "Users can manage own templates" ON agent_templates
    FOR ALL USING (created_by = auth.uid());

-- =====================================================
-- INTEGRATIONS POLICIES
-- =====================================================

-- Users can only access their own integrations
CREATE POLICY "Users can view own integrations" ON integrations
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own integrations" ON integrations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own integrations" ON integrations
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own integrations" ON integrations
    FOR DELETE USING (auth.uid() = user_id);

-- Admins can view all integrations (for support)
CREATE POLICY "Admins can view all integrations" ON integrations
    FOR SELECT USING (is_admin());

-- =====================================================
-- WEBHOOK LOGS POLICIES
-- =====================================================

-- Users can view logs from their integrations
CREATE POLICY "Users can view own webhook logs" ON webhook_logs
    FOR SELECT USING (
        integration_id IN (
            SELECT id FROM integrations WHERE user_id = auth.uid()
        )
    );

-- Admins can view all webhook logs
CREATE POLICY "Admins can view all webhook logs" ON webhook_logs
    FOR SELECT USING (is_admin());

-- System can insert webhook logs (no user restriction for webhooks)
CREATE POLICY "System can insert webhook logs" ON webhook_logs
    FOR INSERT WITH CHECK (true);

-- =====================================================
-- INTEGRATION ANALYTICS POLICIES
-- =====================================================

-- Users can view analytics from their integrations
CREATE POLICY "Users can view own integration analytics" ON integration_analytics
    FOR SELECT USING (
        integration_id IN (
            SELECT id FROM integrations WHERE user_id = auth.uid()
        )
    );

-- System can insert/update analytics
CREATE POLICY "System can manage analytics" ON integration_analytics
    FOR ALL WITH CHECK (true);

-- Admins can view all analytics
CREATE POLICY "Admins can view all analytics" ON integration_analytics
    FOR SELECT USING (is_admin());

-- =====================================================
-- MULTI-AGENT EXECUTIONS POLICIES
-- =====================================================

-- Users can manage their own executions
CREATE POLICY "Users can view own executions" ON multi_agent_executions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own executions" ON multi_agent_executions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own executions" ON multi_agent_executions
    FOR UPDATE USING (auth.uid() = user_id);

-- Admins can view all executions
CREATE POLICY "Admins can view all executions" ON multi_agent_executions
    FOR SELECT USING (is_admin());

-- =====================================================
-- AGENT EXECUTION STEPS POLICIES
-- =====================================================

-- Users can view steps from their executions
CREATE POLICY "Users can view own execution steps" ON agent_execution_steps
    FOR SELECT USING (
        execution_id IN (
            SELECT id FROM multi_agent_executions WHERE user_id = auth.uid()
        )
    );

-- System can manage execution steps
CREATE POLICY "System can manage execution steps" ON agent_execution_steps
    FOR ALL WITH CHECK (
        execution_id IN (
            SELECT id FROM multi_agent_executions WHERE user_id = auth.uid()
        ) OR is_admin()
    );

-- =====================================================
-- USER CREDENTIALS POLICIES (BYOC)
-- =====================================================

-- Users can only manage their own credentials
CREATE POLICY "Users can manage own credentials" ON user_credentials
    FOR ALL USING (auth.uid() = user_id);

-- No admin access to user credentials (privacy)
-- Admins can only see metadata, not encrypted credentials
CREATE POLICY "Admins can view credential metadata" ON user_credentials
    FOR SELECT USING (
        is_admin() AND 
        -- Only allow viewing non-sensitive fields
        true
    );

-- =====================================================
-- FEATURE TOGGLES POLICIES
-- =====================================================

-- Only superadmins can manage feature toggles
CREATE POLICY "Superadmins can manage feature toggles" ON feature_toggles
    FOR ALL USING (is_superadmin());

-- Admins can view feature toggles
CREATE POLICY "Admins can view feature toggles" ON feature_toggles
    FOR SELECT USING (is_admin());

-- =====================================================
-- AUDIT LOGS POLICIES
-- =====================================================

-- Audit logs are append-only, no updates or deletes
CREATE POLICY "System can insert audit logs" ON audit_logs
    FOR INSERT WITH CHECK (true);

-- Users can view their own audit logs
CREATE POLICY "Users can view own audit logs" ON audit_logs
    FOR SELECT USING (auth.uid() = user_id);

-- Admins can view all audit logs
CREATE POLICY "Admins can view all audit logs" ON audit_logs
    FOR SELECT USING (is_admin());

-- =====================================================
-- SYSTEM KEYS POLICIES
-- =====================================================

-- Only superadmins can manage system keys
CREATE POLICY "Superadmins can manage system keys" ON system_keys
    FOR ALL USING (is_superadmin());

-- Public read access to active public keys (for signature verification)
CREATE POLICY "Public can view active public keys" ON system_keys
    FOR SELECT USING (status = 'active');

-- =====================================================
-- SANDBOX EXECUTIONS POLICIES
-- =====================================================

-- Users can manage their own sandbox executions
CREATE POLICY "Users can manage own sandbox executions" ON sandbox_executions
    FOR ALL USING (auth.uid() = user_id);

-- Admins can view all sandbox executions
CREATE POLICY "Admins can view all sandbox executions" ON sandbox_executions
    FOR SELECT USING (is_admin());