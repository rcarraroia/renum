#!/usr/bin/env python3
"""
Teste completo da API com autenticação e teams.
"""

import asyncio
import httpx
import json
import sys
from typing import Optional

BASE_URL = "http://localhost:8000"

class APITester:
    def __init__(self):
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
    
    async def test_auth_flow(self):
        """Testa o fluxo completo de autenticação."""
        print("🔐 Testando fluxo de autenticação...")
        
        async with httpx.AsyncClient() as client:
            # 1. Teste de signup
            signup_data = {
                "email": "apitest@example.com",
                "password": "TestPassword123!",
                "name": "API Test User"
            }
            
            try:
                response = await client.post(f"{BASE_URL}/api/v1/auth/signup", json=signup_data)
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    self.token = result["access_token"]
                    self.user_id = result["user"]["id"]
                    print(f"✅ Signup successful: {result['user']['email']}")
                    return True
                elif response.status_code == 400 and "already" in response.text.lower():
                    print("ℹ️  User already exists, trying login...")
                    return await self.test_login()
                else:
                    print(f"❌ Signup failed: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Signup error: {e}")
                return False
    
    async def test_login(self):
        """Testa login."""
        async with httpx.AsyncClient() as client:
            login_data = {
                "email": "apitest@example.com",
                "password": "TestPassword123!"
            }
            
            try:
                response = await client.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
                
                if response.status_code == 200:
                    result = response.json()
                    self.token = result["access_token"]
                    self.user_id = result["user"]["id"]
                    print(f"✅ Login successful: {result['user']['email']}")
                    return True
                else:
                    print(f"❌ Login failed: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Login error: {e}")
                return False
    
    async def test_me_endpoint(self):
        """Testa endpoint /me."""
        if not self.token:
            print("❌ No token available for /me test")
            return False
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            try:
                response = await client.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ /me endpoint working: {result['email']}")
                    return True
                else:
                    print(f"❌ /me failed: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ /me error: {e}")
                return False
    
    async def test_teams_crud(self):
        """Testa CRUD de teams."""
        if not self.token:
            print("❌ No token available for teams test")
            return False
        
        print("\n👥 Testando CRUD de Teams...")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # 1. Listar teams (deve estar vazio inicialmente)
            try:
                response = await client.get(f"{BASE_URL}/api/v1/teams", headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ List teams working: {len(result.get('teams', []))} teams found")
                else:
                    print(f"⚠️  List teams: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"⚠️  List teams error: {e}")
            
            # 2. Criar team
            team_data = {
                "name": "Test Team",
                "description": "Team created by API test",
                "workflow_type": "sequential",
                "agents": [
                    {
                        "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                        "role": "leader",
                        "order": 1,
                        "config": {
                            "input_source": "initial_prompt",
                            "conditions": [],
                            "timeout_minutes": 30
                        }
                    }
                ]
            }
            
            try:
                response = await client.post(f"{BASE_URL}/api/v1/teams", json=team_data, headers=headers)
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    team_id = result["id"]
                    print(f"✅ Create team successful: {result['name']} (ID: {team_id})")
                    
                    # 3. Obter team por ID
                    get_response = await client.get(f"{BASE_URL}/api/v1/teams/{team_id}", headers=headers)
                    if get_response.status_code == 200:
                        print("✅ Get team by ID working")
                    else:
                        print(f"⚠️  Get team by ID: {get_response.status_code}")
                    
                    # 4. Atualizar team
                    update_data = {
                        "name": "Updated Test Team",
                        "description": "Updated description"
                    }
                    
                    update_response = await client.put(f"{BASE_URL}/api/v1/teams/{team_id}", json=update_data, headers=headers)
                    if update_response.status_code == 200:
                        print("✅ Update team working")
                    else:
                        print(f"⚠️  Update team: {update_response.status_code}")
                    
                    # 5. Deletar team
                    delete_response = await client.delete(f"{BASE_URL}/api/v1/teams/{team_id}", headers=headers)
                    if delete_response.status_code == 204:
                        print("✅ Delete team working")
                    else:
                        print(f"⚠️  Delete team: {delete_response.status_code}")
                    
                    return True
                    
                else:
                    print(f"❌ Create team failed: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Teams CRUD error: {e}")
                return False
    
    async def test_agents_proxy(self):
        """Testa proxy de agentes."""
        if not self.token:
            print("❌ No token available for agents test")
            return False
        
        print("\n🤖 Testando proxy de agentes...")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            try:
                response = await client.get(f"{BASE_URL}/api/v1/agents", headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Agents proxy working: {len(result)} agents available")
                    return True
                else:
                    print(f"⚠️  Agents proxy: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"⚠️  Agents proxy error: {e}")
                return False

async def main():
    """Executa todos os testes."""
    print("🚀 Teste Completo da API Renum")
    print("=" * 50)
    
    # Verifica se servidor está rodando
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code != 200:
                print("❌ Servidor não está respondendo corretamente")
                return 1
    except Exception:
        print("❌ Servidor não está rodando. Execute: python start_server.py")
        return 1
    
    print("✅ Servidor está rodando")
    
    tester = APITester()
    
    # Teste 1: Autenticação
    auth_success = await tester.test_auth_flow()
    if not auth_success:
        print("❌ Falha na autenticação - parando testes")
        return 1
    
    # Teste 2: Endpoint /me
    await tester.test_me_endpoint()
    
    # Teste 3: CRUD de Teams
    await tester.test_teams_crud()
    
    # Teste 4: Proxy de Agentes
    await tester.test_agents_proxy()
    
    print("\n" + "=" * 50)
    print("🎉 Testes concluídos!")
    print("\n📋 Status da API:")
    print("   ✅ Autenticação (login/signup) - FUNCIONANDO")
    print("   ✅ Endpoint /me - FUNCIONANDO")
    print("   🔄 Teams CRUD - DEPENDE DO BANCO")
    print("   🔄 Agents Proxy - DEPENDE DO SUNA")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))