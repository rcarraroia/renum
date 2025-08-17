-- Migration: 003_triggers_and_functions.sql
-- Description: Database triggers and functions for multi-agent system
-- Date: 2025-08-16
-- Author: Kiro AI Assistant

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to create audit log entry
CREATE OR REPLACE FUNCTION create_audit_log()
RETURNS TRIGGER AS $$
DECLARE
    action_type VARCHAR(10);
    old_values JSONB;
    new_values JSONB;
BEGIN
    -- Determine action type
    IF TG_OP = 'INSERT' THEN
        action_type := 'INSERT';
        old_values := NULL;
        new_values := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        action_type := 'UPDATE';
        old_values := to_jsonb(OLD);
        new_values := to_jsonb(NEW);
    ELSIF TG_OP = 'DELETE' THEN
        action_type := 'DELETE';
        old_values := to_jsonb(OLD);
        new_values := NULL;
    END IF;

    -- Insert audit log
    INSERT INTO audit_logs (
        user_id,
        action,
        resource_type,
        resource_id,
        old_values,
        new_values,
        ip_address,
        user_agent
    ) VALUES (
        auth.uid(),
        action_type,
        TG_TABLE_NAME,
        COALESCE(NEW.id::text, OLD.id::text),
        old_values,
        new_values,
        inet_client_addr(),
        current_setting('request.headers', true)::json->>'user-agent'
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to generate secure token
CREATE OR REPLACE FUNCTION generate_secure_token(length INTEGER DEFAULT 32)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(gen_random_bytes(length), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Function to mask PII data
CREATE OR REPLACE FUNCTION mask_pii(input_text TEXT, mask_type VARCHAR DEFAULT 'email')
RETURNS TEXT AS $$
BEGIN
    CASE mask_type
        WHEN 'email' THEN
            -- Mask email: fulano@email.com -> f***o@email.com
            RETURN regexp_replace(input_text, '(.)[^@]*(.@.*)', '\1***\2', 'g');
        WHEN 'phone' THEN
            -- Mask phone: +5511999999999 -> +55***999999
            RETURN regexp_replace(input_text, '(\+\d{2})\d*(\d{6})', '\1***\2', 'g');
        WHEN 'cpf' THEN
            -- Mask CPF: 12345678901 -> 123***901
            RETURN regexp_replace(input_text, '(\d{3})\d*(\d{3})', '\1***\2', 'g');
        ELSE
            -- Generic masking: show first and last 2 chars
            RETURN CASE 
                WHEN length(input_text) <= 4 THEN '***'
                ELSE substring(input_text, 1, 2) || '***' || substring(input_text, length(input_text)-1)
            END;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Function to validate agent manifest
CREATE OR REPLACE FUNCTION validate_agent_manifest(manifest JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check required fields
    IF NOT (manifest ? 'agent_id' AND manifest ? 'version' AND manifest ? 'capabilities') THEN
        RETURN FALSE;
    END IF;
    
    -- Validate agent_id format
    IF NOT (manifest->>'agent_id' ~ '^[a-z0-9-]+$') THEN
        RETURN FALSE;
    END IF;
    
    -- Validate version format (semantic versioning)
    IF NOT (manifest->>'version' ~ '^\d+\.\d+\.\d+$') THEN
        RETURN FALSE;
    END IF;
    
    -- Validate capabilities is array
    IF NOT (jsonb_typeof(manifest->'capabilities') = 'array') THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate manifest checksum
CREATE OR REPLACE FUNCTION calculate_manifest_checksum(manifest JSONB)
RETURNS VARCHAR AS $$
BEGIN
    RETURN encode(digest(manifest::text, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS FOR UPDATED_AT
-- =====================================================

-- Agents Registry
CREATE TRIGGER update_agents_registry_updated_at
    BEFORE UPDATE ON agents_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Agent Templates
CREATE TRIGGER update_agent_templates_updated_at
    BEFORE UPDATE ON agent_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Integrations
CREATE TRIGGER update_integrations_updated_at
    BEFORE UPDATE ON integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- User Credentials
CREATE TRIGGER update_user_credentials_updated_at
    BEFORE UPDATE ON user_credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Feature Toggles
CREATE TRIGGER update_feature_toggles_updated_at
    BEFORE UPDATE ON feature_toggles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- TRIGGERS FOR AUDIT LOGGING
-- =====================================================

-- Agents Registry Audit
CREATE TRIGGER audit_agents_registry
    AFTER INSERT OR UPDATE OR DELETE ON agents_registry
    FOR EACH ROW
    EXECUTE FUNCTION create_audit_log();

-- Integrations Audit
CREATE TRIGGER audit_integrations
    AFTER INSERT OR UPDATE OR DELETE ON integrations
    FOR EACH ROW
    EXECUTE FUNCTION create_audit_log();

-- User Credentials Audit (sensitive operations)
CREATE TRIGGER audit_user_credentials
    AFTER INSERT OR UPDATE OR DELETE ON user_credentials
    FOR EACH ROW
    EXECUTE FUNCTION create_audit_log();

-- Feature Toggles Audit
CREATE TRIGGER audit_feature_toggles
    AFTER INSERT OR UPDATE OR DELETE ON feature_toggles
    FOR EACH ROW
    EXECUTE FUNCTION create_audit_log();

-- System Keys Audit
CREATE TRIGGER audit_system_keys
    AFTER INSERT OR UPDATE OR DELETE ON system_keys
    FOR EACH ROW
    EXECUTE FUNCTION create_audit_log();

-- =====================================================
-- TRIGGERS FOR BUSINESS LOGIC
-- =====================================================

-- Auto-generate token for integrations
CREATE OR REPLACE FUNCTION auto_generate_integration_token()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.token IS NULL OR NEW.token = '' THEN
        NEW.token := 'renum_' || generate_secure_token(32);
    END IF;
    
    -- Generate webhook URL if not provided
    IF NEW.webhook_url IS NULL THEN
        NEW.webhook_url := '/webhook/' || NEW.id::text;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER generate_integration_token
    BEFORE INSERT ON integrations
    FOR EACH ROW
    EXECUTE FUNCTION auto_generate_integration_token();

-- Auto-calculate manifest checksum for agents
CREATE OR REPLACE FUNCTION auto_calculate_agent_checksum()
RETURNS TRIGGER AS $$
DECLARE
    manifest JSONB;
BEGIN
    -- Build manifest from agent data
    manifest := jsonb_build_object(
        'agent_id', NEW.agent_id,
        'version', NEW.version,
        'name', NEW.name,
        'description', NEW.description,
        'capabilities', NEW.capabilities,
        'input_schema', NEW.input_schema,
        'policy', NEW.policy
    );
    
    -- Validate manifest
    IF NOT validate_agent_manifest(manifest) THEN
        RAISE EXCEPTION 'Invalid agent manifest structure';
    END IF;
    
    -- Calculate checksum
    NEW.manifest_checksum := calculate_manifest_checksum(manifest);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_agent_checksum
    BEFORE INSERT OR UPDATE ON agents_registry
    FOR EACH ROW
    EXECUTE FUNCTION auto_calculate_agent_checksum();

-- Update integration analytics
CREATE OR REPLACE FUNCTION update_integration_analytics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update daily analytics for the integration
    INSERT INTO integration_analytics (
        integration_id,
        date,
        total_requests,
        successful_requests,
        failed_requests,
        avg_response_time_ms
    ) VALUES (
        NEW.integration_id,
        CURRENT_DATE,
        1,
        CASE WHEN NEW.response_status BETWEEN 200 AND 299 THEN 1 ELSE 0 END,
        CASE WHEN NEW.response_status NOT BETWEEN 200 AND 299 THEN 1 ELSE 0 END,
        NEW.processing_time_ms
    )
    ON CONFLICT (integration_id, date) DO UPDATE SET
        total_requests = integration_analytics.total_requests + 1,
        successful_requests = integration_analytics.successful_requests + 
            CASE WHEN NEW.response_status BETWEEN 200 AND 299 THEN 1 ELSE 0 END,
        failed_requests = integration_analytics.failed_requests + 
            CASE WHEN NEW.response_status NOT BETWEEN 200 AND 299 THEN 1 ELSE 0 END,
        avg_response_time_ms = (
            (integration_analytics.avg_response_time_ms * integration_analytics.total_requests + NEW.processing_time_ms) / 
            (integration_analytics.total_requests + 1)
        );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_webhook_analytics
    AFTER INSERT ON webhook_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_integration_analytics();

-- =====================================================
-- CLEANUP FUNCTIONS
-- =====================================================

-- Function to cleanup old webhook logs
CREATE OR REPLACE FUNCTION cleanup_old_webhook_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM webhook_logs 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old audit logs
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(days_to_keep INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_logs 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old sandbox executions
CREATE OR REPLACE FUNCTION cleanup_old_sandbox_executions(days_to_keep INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sandbox_executions 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;