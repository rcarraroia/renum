"""
Teste de integração simples para verificar se a API está funcionando.
"""

import asyncio
import sys
import os

# Adiciona o diretório da aplicação ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_basic_imports():
    """Testa se as importações básicas funcionam."""
    try:
        # Testa importações principais
        from app.main import app
        from app.infra.suna.client import suna_client
        from app.infra.websocket.manager import manager
        
        print("✅ Importações básicas funcionando")
        
        # Testa health check do Suna
        health = await suna_client.health_check()
        print(f"✅ Suna Backend status: {health['status']}")
        
        # Testa WebSocket manager
        connection_count = manager.get_connection_count()
        print(f"✅ WebSocket manager funcionando - Conexões: {connection_count}")
        
        print("\n🎉 Todos os testes básicos passaram!")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Limpa recursos
        await suna_client.close()

if __name__ == "__main__":
    success = asyncio.run(test_basic_imports())
    sys.exit(0 if success else 1)