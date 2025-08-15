"""
Teste dos endpoints da API.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Testa o endpoint de health."""
    response = client.get("/health")
    print(f"Health endpoint: {response.status_code}")
    if response.status_code == 200:
        print("✅ Health endpoint funcionando")
        return True
    else:
        print(f"❌ Health endpoint falhou: {response.text}")
        return False

def test_root_endpoint():
    """Testa o endpoint raiz."""
    response = client.get("/")
    print(f"Root endpoint: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Root endpoint funcionando: {data['name']}")
        return True
    else:
        print(f"❌ Root endpoint falhou: {response.text}")
        return False

def test_teams_endpoint_without_auth():
    """Testa o endpoint de teams sem autenticação."""
    response = client.get("/api/v1/teams")
    print(f"Teams endpoint (sem auth): {response.status_code}")
    if response.status_code == 403:
        print("✅ Teams endpoint protegido corretamente")
        return True
    else:
        print(f"❌ Teams endpoint deveria retornar 403: {response.text}")
        return False

def test_executions_endpoint_without_auth():
    """Testa o endpoint de executions sem autenticação."""
    response = client.get("/api/v1/executions")
    print(f"Executions endpoint (sem auth): {response.status_code}")
    if response.status_code == 403:
        print("✅ Executions endpoint protegido corretamente")
        return True
    else:
        print(f"❌ Executions endpoint deveria retornar 403: {response.text}")
        return False

def test_openapi_docs():
    """Testa se a documentação OpenAPI está disponível."""
    response = client.get("/docs")
    print(f"OpenAPI docs: {response.status_code}")
    if response.status_code == 200:
        print("✅ Documentação OpenAPI disponível")
        return True
    else:
        print(f"❌ Documentação OpenAPI falhou: {response.text}")
        return False

def main():
    """Executa todos os testes."""
    print("🧪 Testando endpoints da API...\n")
    
    tests = [
        test_root_endpoint,
        test_health_endpoint,
        test_teams_endpoint_without_auth,
        test_executions_endpoint_without_auth,
        test_openapi_docs
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Erro no teste {test.__name__}: {e}")
            results.append(False)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Resultados: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 Todos os testes passaram!")
        return True
    else:
        print("⚠️ Alguns testes falharam")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)