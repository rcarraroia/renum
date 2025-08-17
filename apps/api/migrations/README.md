# Database Migrations for Multi-Agent System

This directory contains database migrations for the Renum multi-agent system transformation.

## Migration Files

1. **001_multi_agent_system_schema.sql** - Core database schema with all tables and indexes
2. **002_rls_policies.sql** - Row Level Security policies for data isolation
3. **003_triggers_and_functions.sql** - Database triggers and utility functions
4. **004_initial_data.sql** - Initial system data and configuration

## Running Migrations

### Prerequisites

```bash
pip install asyncpg python-dotenv
```

### Environment Setup

Ensure your `.env` file contains:

```env
DATABASE_URL=postgresql://user:password@host:port/database
```

### Run All Migrations

```bash
cd renum/apps/api/migrations
python run_migrations.py
```

### Rollback Migration (if rollback script exists)

```bash
python run_migrations.py rollback 001_multi_agent_system_schema.sql
```

## Migration Details

### Core Tables Created

#### Agent Registry
- `agents_registry` - Agent definitions with versioning
- `agent_templates` - Reusable agent templates
- `system_keys` - Public keys for manifest verification

#### Integrations
- `integrations` - User integrations with external platforms
- `webhook_logs` - Detailed webhook processing logs
- `integration_analytics` - Daily analytics per integration
- `integration_types` - Configuration for supported integration types

#### Multi-Agent Execution
- `multi_agent_executions` - Multi-agent execution sessions
- `agent_execution_steps` - Individual agent steps within executions

#### BYOC (Bring Your Own Credentials)
- `user_credentials` - Encrypted user credentials for external services

#### Admin & Governance
- `feature_toggles` - Feature flags for tenant-specific controls
- `audit_logs` - Immutable audit trail for all operations
- `sandbox_executions` - Isolated sandbox execution logs

### Security Features

#### Row Level Security (RLS)
- All tables have RLS enabled
- Users can only access their own data
- Admins have elevated permissions
- Superadmins have full system access

#### Audit Logging
- Automatic audit logging for critical operations
- Immutable audit trail (append-only)
- PII masking in logs

#### Data Protection
- Encrypted credential storage
- Automatic PII masking functions
- Secure token generation

### Performance Optimizations

#### Indexes
- Optimized indexes for common query patterns
- Composite indexes for complex queries
- Partial indexes for filtered queries

#### Functions
- Utility functions for common operations
- Manifest validation and checksum calculation
- Automatic cleanup functions

### Initial Data

#### System Configuration
- Initial system keys for manifest signing
- Feature toggles for all system features
- Integration type configurations

#### Agent Templates
- Basic email agent template
- WhatsApp bot agent template
- Database query agent template

#### System Agents
- Generic HTTP agent for unsupported integrations
- Agent orchestrator for multi-agent coordination

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure database user has CREATE privileges
   - Check if RLS policies are blocking access

2. **Migration Already Applied**
   - Check `schema_migrations` table for applied migrations
   - Use rollback if needed to reapply

3. **Connection Issues**
   - Verify DATABASE_URL format
   - Check network connectivity to database

### Manual Verification

```sql
-- Check applied migrations
SELECT * FROM schema_migrations ORDER BY applied_at;

-- Verify table creation
\dt

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'public';

-- Verify indexes
SELECT indexname, tablename, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public';
```

## Development Notes

### Adding New Migrations

1. Create new migration file with sequential number
2. Add filename to `migration_files` list in `run_migrations.py`
3. Test migration on development database
4. Create rollback script if needed

### Migration Best Practices

1. Always use transactions for atomic operations
2. Include rollback scripts for destructive changes
3. Test migrations on copy of production data
4. Use `IF NOT EXISTS` for idempotent operations
5. Document breaking changes in migration comments

### Security Considerations

1. Never include sensitive data in migration files
2. Use environment variables for configuration
3. Ensure RLS policies are applied before data insertion
4. Test permission boundaries thoroughly