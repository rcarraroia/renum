"""
Teste simples para verificar se a API está funcionando.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Testa se as importações funcionam."""
    try:
        from app.main import app
        print("✅ FastAPI app importado com sucesso")
        
        from app.infra.websocket.manager import ConnectionManager
        manager = ConnectionManager()
        print("✅ WebSocket manager criado com sucesso")
        
        from app.schemas.team import TeamCreate, WorkflowType, AgentRole
        print("✅ Schemas de team importados com sucesso")
        
        from app.schemas.execution import ExecutionCreate, ExecutionStatus
        print("✅ Schemas de execution importados com sucesso")
        
        print("\n🎉 Todos os imports funcionaram!")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)