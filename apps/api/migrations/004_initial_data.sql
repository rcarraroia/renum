-- Migration: 004_initial_data.sql
-- Description: Initial data and configuration for multi-agent system
-- Date: 2025-08-16
-- Author: Kiro AI Assistant

-- =====================================================
-- INITIAL SYSTEM KEYS
-- =====================================================

-- Generate initial system key for manifest signing
INSERT INTO system_keys (
    key_id,
    key_type,
    public_key,
    private_key_hash,
    status,
    expires_at
) VALUES (
    'renum-system-key-001',
    'RSA256',
    '-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1234567890abcdef...
-----END PUBLIC KEY-----',
    'sha256_hash_of_private_key_here',
    'active',
    NOW() + INTERVAL '2 years'
) ON CONFLICT (key_id) DO NOTHING;

-- =====================================================
-- INITIAL FEATURE TOGGLES
-- =====================================================

-- Core system features
INSERT INTO feature_toggles (feature_name, description, enabled_globally, rollout_percentage) VALUES
('multi_agent_orchestration', 'Enable multi-agent orchestration system', true, 100),
('webhook_integrations', 'Enable webhook integrations', true, 100),
('byoc_credentials', 'Enable Bring Your Own Credentials', true, 100),
('sandbox_testing', 'Enable sandbox testing environment', true, 100),
('agent_registry', 'Enable agent registry and versioning', true, 100),
('admin_panel', 'Enable administrative panel', true, 100),
('audit_logging', 'Enable comprehensive audit logging', true, 100),
('rate_limiting', 'Enable rate limiting for integrations', true, 100),
('pii_masking', 'Enable PII masking in logs', true, 100),
('manifest_signing', 'Enable agent manifest digital signing', true, 100)
ON CONFLICT (feature_name) DO NOTHING;

-- Beta features (disabled by default)
INSERT INTO feature_toggles (feature_name, description, enabled_globally, rollout_percentage) VALUES
('ai_prompt_optimization', 'AI-powered prompt optimization suggestions', false, 0),
('advanced_analytics', 'Advanced analytics and insights', false, 10),
('auto_scaling', 'Automatic scaling based on load', false, 0),
('multi_tenant_isolation', 'Enhanced multi-tenant isolation', false, 5),
('real_time_collaboration', 'Real-time collaborative agent editing', false, 0)
ON CONFLICT (feature_name) DO NOTHING;

-- =====================================================
-- INITIAL AGENT TEMPLATES
-- =====================================================

-- Basic Email Agent Template
INSERT INTO agent_templates (
    name,
    description,
    category,
    template_data,
    is_public
) VALUES (
    'Basic Email Agent',
    'Template for creating email automation agents',
    'communication',
    '{
        "agent_id": "sa-email-basic",
        "capabilities": [
            {
                "name": "send_email",
                "description": "Send email via SMTP or API",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "format": "email"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                        "html": {"type": "boolean", "default": false}
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        ],
        "required_credentials": ["gmail", "smtp"],
        "policy": {
            "max_emails_per_hour": 100,
            "allowed_domains": ["*"],
            "require_confirmation": false
        }
    }',
    true
),
(
    'WhatsApp Bot Agent',
    'Template for creating WhatsApp bot agents',
    'messaging',
    '{
        "agent_id": "sa-whatsapp-bot",
        "capabilities": [
            {
                "name": "send_message",
                "description": "Send WhatsApp message",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"},
                        "message": {"type": "string"},
                        "media_url": {"type": "string", "format": "uri"}
                    },
                    "required": ["phone", "message"]
                }
            }
        ],
        "required_credentials": ["whatsapp_business"],
        "policy": {
            "max_messages_per_day": 1000,
            "business_hours_only": true,
            "require_opt_in": true
        }
    }',
    true
),
(
    'Database Query Agent',
    'Template for creating database query agents',
    'data',
    '{
        "agent_id": "sa-database-query",
        "capabilities": [
            {
                "name": "execute_query",
                "description": "Execute safe database queries",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "parameters": {"type": "object"},
                        "limit": {"type": "integer", "maximum": 1000}
                    },
                    "required": ["query"]
                }
            }
        ],
        "required_credentials": ["supabase", "postgresql"],
        "policy": {
            "allowed_operations": ["SELECT"],
            "max_rows": 1000,
            "timeout_seconds": 30
        }
    }',
    true
)
ON CONFLICT DO NOTHING;

-- =====================================================
-- INITIAL SYSTEM AGENTS
-- =====================================================

-- HTTP Generic Agent (for unsupported integrations)
INSERT INTO agents_registry (
    agent_id,
    version,
    name,
    description,
    capabilities,
    input_schema,
    policy,
    status
) VALUES (
    'sa-http-generic',
    '1.0.0',
    'Generic HTTP Agent',
    'Generic agent for making HTTP requests to any API',
    '[
        {
            "name": "http_request",
            "description": "Make HTTP request to any endpoint",
            "input_schema": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                    "url": {"type": "string", "format": "uri"},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                    "timeout": {"type": "integer", "default": 30}
                },
                "required": ["method", "url"]
            }
        }
    ]',
    '{
        "type": "object",
        "properties": {
            "method": {"type": "string"},
            "url": {"type": "string"},
            "headers": {"type": "object"},
            "body": {"type": "object"}
        }
    }',
    '{
        "max_requests_per_minute": 60,
        "allowed_domains": ["*"],
        "timeout_seconds": 30,
        "max_response_size": "10MB"
    }',
    'approved'
),
(
    'sa-orchestrator',
    '1.0.0',
    'Agent Orchestrator',
    'Main orchestrator agent for coordinating multi-agent workflows',
    '[
        {
            "name": "analyze_requirements",
            "description": "Analyze user requirements and generate execution plan",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_message": {"type": "string"},
                    "context": {"type": "object"},
                    "available_agents": {"type": "array"}
                },
                "required": ["user_message"]
            }
        },
        {
            "name": "execute_plan",
            "description": "Execute multi-agent plan",
            "input_schema": {
                "type": "object",
                "properties": {
                    "plan": {"type": "object"},
                    "user_id": {"type": "string"}
                },
                "required": ["plan", "user_id"]
            }
        }
    ]',
    '{
        "type": "object",
        "properties": {
            "user_message": {"type": "string"},
            "context": {"type": "object"}
        }
    }',
    '{
        "max_concurrent_executions": 10,
        "max_agents_per_plan": 20,
        "timeout_minutes": 30
    }',
    'approved'
)
ON CONFLICT (agent_id, version) DO NOTHING;

-- =====================================================
-- INITIAL INTEGRATION TYPES CONFIGURATION
-- =====================================================

-- This would typically be stored in a configuration table or as constants in code
-- For now, we'll create a simple reference table for integration types

CREATE TABLE IF NOT EXISTS integration_types (
    type VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    config_schema JSONB NOT NULL,
    webhook_supported BOOLEAN DEFAULT false,
    oauth_supported BOOLEAN DEFAULT false,
    api_key_supported BOOLEAN DEFAULT false,
    documentation_url TEXT,
    is_active BOOLEAN DEFAULT true
);

INSERT INTO integration_types (type, display_name, description, config_schema, webhook_supported, oauth_supported, api_key_supported, documentation_url) VALUES
(
    'whatsapp',
    'WhatsApp Business',
    'WhatsApp Business API integration for messaging',
    '{
        "type": "object",
        "properties": {
            "business_phone_number": {"type": "string"},
            "access_token": {"type": "string"},
            "webhook_verify_token": {"type": "string"}
        },
        "required": ["business_phone_number", "access_token"]
    }',
    true,
    false,
    true,
    'https://developers.facebook.com/docs/whatsapp'
),
(
    'telegram',
    'Telegram Bot',
    'Telegram Bot API integration for messaging',
    '{
        "type": "object",
        "properties": {
            "bot_token": {"type": "string"},
            "webhook_secret": {"type": "string"}
        },
        "required": ["bot_token"]
    }',
    true,
    false,
    true,
    'https://core.telegram.org/bots/api'
),
(
    'zapier',
    'Zapier Webhooks',
    'Zapier webhook integration for automation',
    '{
        "type": "object",
        "properties": {
            "webhook_url": {"type": "string", "format": "uri"},
            "secret_key": {"type": "string"}
        },
        "required": ["webhook_url"]
    }',
    true,
    false,
    false,
    'https://zapier.com/help/webhooks'
),
(
    'gmail',
    'Gmail API',
    'Gmail API integration for email operations',
    '{
        "type": "object",
        "properties": {
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
            "refresh_token": {"type": "string"}
        },
        "required": ["client_id", "client_secret", "refresh_token"]
    }',
    false,
    true,
    false,
    'https://developers.google.com/gmail/api'
),
(
    'supabase',
    'Supabase Database',
    'Supabase database integration',
    '{
        "type": "object",
        "properties": {
            "project_url": {"type": "string", "format": "uri"},
            "api_key": {"type": "string"},
            "service_role_key": {"type": "string"}
        },
        "required": ["project_url", "api_key"]
    }',
    false,
    false,
    true,
    'https://supabase.com/docs/reference/api'
)
ON CONFLICT (type) DO NOTHING;