#!/usr/bin/env python3
"""
Script para testar e diagnosticar a conexão com Supabase.
"""

import os
import sys
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

def test_supabase_connection():
    """Testa a conexão com Supabase."""
    print("🔍 Testando conexão com Supabase...")
    print("=" * 50)
    
    # Verifica variáveis de ambiente
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    print(f"SUPABASE_URL: {supabase_url}")
    print(f"SUPABASE_ANON_KEY: {'*' * 20 if supabase_anon_key else 'NOT SET'}")
    
    if not supabase_url or not supabase_anon_key:
        print("❌ Variáveis de ambiente não configuradas!")
        return False
    
    try:
        from supabase import create_client, Client
        
        # Cria cliente
        supabase: Client = create_client(supabase_url, supabase_anon_key)
        print("✅ Cliente Supabase criado com sucesso")
        
        # Testa autenticação básica
        print("\n🔐 Testando funcionalidades de autenticação...")
        
        # Tenta fazer signup de teste
        test_email = "testuser123@gmail.com"  # Email mais realista
        test_password = "TestPassword123!"
        
        try:
            # Primeiro, tenta fazer login para ver se o usuário já existe
            login_response = supabase.auth.sign_in_with_password({
                "email": test_email,
                "password": test_password
            })
            
            if login_response.user:
                print(f"✅ Login funcionando - Usuário existe: {login_response.user.email}")
                return True
                
        except Exception as login_error:
            print(f"ℹ️  Login falhou (esperado se usuário não existe): {login_error}")
            
            # Tenta fazer signup
            try:
                signup_response = supabase.auth.sign_up({
                    "email": test_email,
                    "password": test_password,
                    "options": {
                        "data": {"name": "Test User"}
                    }
                })
                
                if signup_response.user:
                    print(f"✅ Signup funcionando - Usuário criado: {signup_response.user.email}")
                    print(f"   ID: {signup_response.user.id}")
                    print(f"   Confirmado: {signup_response.user.email_confirmed_at is not None}")
                    return True
                else:
                    print("❌ Signup falhou - Nenhum usuário retornado")
                    return False
                    
            except Exception as signup_error:
                print(f"❌ Signup falhou: {signup_error}")
                return False
        
    except Exception as e:
        print(f"❌ Erro ao conectar com Supabase: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_access():
    """Testa acesso ao banco de dados."""
    print("\n📊 Testando acesso ao banco de dados...")
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        supabase = create_client(supabase_url, supabase_anon_key)
        
        # Tenta listar tabelas (pode falhar por permissões)
        try:
            # Tenta acessar uma tabela comum do Supabase
            response = supabase.table('auth.users').select('*').limit(1).execute()
            print("✅ Acesso ao banco funcionando")
            return True
        except Exception as e:
            if "permission denied" in str(e).lower():
                print("ℹ️  Sem permissão para acessar auth.users (normal)")
                
                # Tenta criar uma tabela de teste
                try:
                    # Verifica se consegue executar uma query básica
                    response = supabase.rpc('version').execute()
                    print("✅ Conexão com banco estabelecida")
                    return True
                except Exception as rpc_error:
                    print(f"⚠️  RPC falhou: {rpc_error}")
                    return False
            else:
                print(f"❌ Erro de acesso ao banco: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao testar banco: {e}")
        return False

def create_teams_table():
    """Cria a tabela de teams se não existir."""
    print("\n🏗️  Criando tabela de teams...")
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        supabase = create_client(supabase_url, supabase_anon_key)
        
        # SQL para criar tabela de teams
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS teams (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            workflow_type VARCHAR(20) NOT NULL DEFAULT 'sequential',
            user_id UUID NOT NULL,
            agents JSONB DEFAULT '[]'::jsonb,
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- RLS (Row Level Security)
        ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
        
        -- Policy para usuários só verem suas próprias teams
        CREATE POLICY IF NOT EXISTS "Users can view own teams" ON teams
            FOR SELECT USING (auth.uid() = user_id);
            
        CREATE POLICY IF NOT EXISTS "Users can insert own teams" ON teams
            FOR INSERT WITH CHECK (auth.uid() = user_id);
            
        CREATE POLICY IF NOT EXISTS "Users can update own teams" ON teams
            FOR UPDATE USING (auth.uid() = user_id);
            
        CREATE POLICY IF NOT EXISTS "Users can delete own teams" ON teams
            FOR DELETE USING (auth.uid() = user_id);
        """
        
        # Executa o SQL
        response = supabase.rpc('exec_sql', {'sql': create_table_sql}).execute()
        print("✅ Tabela teams criada/verificada com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela teams: {e}")
        # Isso pode falhar se não tivermos permissões de admin
        print("ℹ️  Isso é normal se não tivermos permissões de admin no Supabase")
        return False

def main():
    """Função principal."""
    print("🚀 Diagnóstico de Conexão Supabase")
    print("=" * 50)
    
    success = True
    
    # Teste 1: Conexão básica
    success &= test_supabase_connection()
    
    # Teste 2: Acesso ao banco
    success &= test_database_access()
    
    # Teste 3: Criar tabela (opcional)
    create_teams_table()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCESSO! Supabase está funcionando corretamente.")
        print("\n📋 Próximos passos:")
        print("   1. A autenticação está funcionando")
        print("   2. Você pode iniciar o servidor da API")
        print("   3. Os endpoints /login e /signup devem funcionar")
    else:
        print("❌ PROBLEMAS encontrados na conexão com Supabase.")
        print("\n🔧 Possíveis soluções:")
        print("   1. Verifique as credenciais no arquivo .env")
        print("   2. Confirme que o projeto Supabase está ativo")
        print("   3. Verifique as configurações de RLS no Supabase")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())