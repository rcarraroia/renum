#!/usr/bin/env python3
"""
Migration runner for multi-agent system database schema
Usage: python run_migrations.py
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import List
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MigrationRunner:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.migrations_dir = Path(__file__).parent
        self.migration_files = [
            '001_multi_agent_system_schema.sql',
            '002_rls_policies.sql', 
            '003_triggers_and_functions.sql',
            '004_initial_data.sql'
        ]
    
    async def create_migrations_table(self, conn):
        """Create migrations tracking table if it doesn't exist"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
    
    async def get_applied_migrations(self, conn) -> List[str]:
        """Get list of already applied migrations"""
        rows = await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")
        return [row['version'] for row in rows]
    
    async def apply_migration(self, conn, migration_file: str):
        """Apply a single migration file"""
        migration_path = self.migrations_dir / migration_file
        
        if not migration_path.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_path}")
        
        print(f"Applying migration: {migration_file}")
        
        # Read migration content
        with open(migration_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Execute migration in a transaction
        async with conn.transaction():
            try:
                await conn.execute(migration_sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)",
                    migration_file
                )
                print(f"✅ Successfully applied: {migration_file}")
            except Exception as e:
                print(f"❌ Failed to apply {migration_file}: {e}")
                raise
    
    async def run_migrations(self):
        """Run all pending migrations"""
        print("🚀 Starting database migrations...")
        
        # Connect to database
        conn = await asyncpg.connect(self.database_url)
        
        try:
            # Create migrations table
            await self.create_migrations_table(conn)
            
            # Get applied migrations
            applied_migrations = await self.get_applied_migrations(conn)
            print(f"📋 Found {len(applied_migrations)} applied migrations")
            
            # Apply pending migrations
            pending_migrations = [
                f for f in self.migration_files 
                if f not in applied_migrations
            ]
            
            if not pending_migrations:
                print("✅ All migrations are up to date!")
                return
            
            print(f"📦 Applying {len(pending_migrations)} pending migrations...")
            
            for migration_file in pending_migrations:
                await self.apply_migration(conn, migration_file)
            
            print("🎉 All migrations completed successfully!")
            
        except Exception as e:
            print(f"💥 Migration failed: {e}")
            sys.exit(1)
        finally:
            await conn.close()
    
    async def rollback_migration(self, migration_file: str):
        """Rollback a specific migration (if rollback script exists)"""
        rollback_file = migration_file.replace('.sql', '_rollback.sql')
        rollback_path = self.migrations_dir / rollback_file
        
        if not rollback_path.exists():
            print(f"⚠️  No rollback script found for {migration_file}")
            return
        
        conn = await asyncpg.connect(self.database_url)
        
        try:
            print(f"🔄 Rolling back migration: {migration_file}")
            
            with open(rollback_path, 'r', encoding='utf-8') as f:
                rollback_sql = f.read()
            
            async with conn.transaction():
                await conn.execute(rollback_sql)
                await conn.execute(
                    "DELETE FROM schema_migrations WHERE version = $1",
                    migration_file
                )
            
            print(f"✅ Successfully rolled back: {migration_file}")
            
        except Exception as e:
            print(f"❌ Failed to rollback {migration_file}: {e}")
            raise
        finally:
            await conn.close()

async def main():
    """Main entry point"""
    runner = MigrationRunner()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        if len(sys.argv) < 3:
            print("Usage: python run_migrations.py rollback <migration_file>")
            sys.exit(1)
        await runner.rollback_migration(sys.argv[2])
    else:
        await runner.run_migrations()

if __name__ == "__main__":
    asyncio.run(main())