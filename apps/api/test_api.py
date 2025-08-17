#!/usr/bin/env python3
"""
Script para testar os endpoints de autenticação.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

async def test_health():
    """Testa o endpoint de health."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"Health Check: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

async def test_signup():
    """Testa o endpoint de signup."""
    async with httpx.AsyncClient() as client:
        try:
            signup_data = {
                "email": "test@example.com",
                "password": "testpassword123",
                "name": "Test User"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/signup",
                json=signup_data
            )
            
            print(f"Signup: {response.status_code}")
            if response.status_code == 201 or response.status_code == 200:
                result = response.json()
                print(f"Signup successful: {result['user']['email']}")
                return result
            else:
                print(f"Signup failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Signup test failed: {e}")
            return None

async def test_login():
    """Testa o endpoint de login."""
    async with httpx.AsyncClient() as client:
        try:
            login_data = {
                "email": "test@example.com",
                "password": "testpassword123"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=login_data
            )
            
            print(f"Login: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Login successful: {result['user']['email']}")
                print(f"Token: {result['access_token'][:50]}...")
                return result
            else:
                print(f"Login failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Login test failed: {e}")
            return None

async def test_me(token: str):
    """Testa o endpoint /me."""
    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                f"{BASE_URL}/api/v1/auth/me",
                headers=headers
            )
            
            print(f"Me endpoint: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"User info: {result}")
                return result
            else:
                print(f"Me endpoint failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Me endpoint test failed: {e}")
            return None

async def main():
    """Executa todos os testes."""
    print("🚀 Testando API de Autenticação...")
    print("=" * 50)
    
    # Testa health
    print("\n1. Testando Health Check...")
    health_ok = await test_health()
    
    if not health_ok:
        print("❌ Servidor não está respondendo. Certifique-se de que está rodando.")
        return
    
    print("✅ Servidor está funcionando!")
    
    # Testa signup
    print("\n2. Testando Signup...")
    signup_result = await test_signup()
    
    # Testa login
    print("\n3. Testando Login...")
    login_result = await test_login()
    
    if login_result and login_result.get("access_token"):
        # Testa endpoint /me
        print("\n4. Testando endpoint /me...")
        await test_me(login_result["access_token"])
    
    print("\n" + "=" * 50)
    print("🎉 Testes concluídos!")

if __name__ == "__main__":
    asyncio.run(main())