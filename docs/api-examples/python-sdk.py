"""
Renum API Python SDK Examples
Complete examples for using the Renum API with Python
"""
import asyncio
import httpx
import json
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime

class RenumAPIClient:
    """Python SDK for Renum API"""
    
    def __init__(self, base_url: str = "https://api.renum.com", api_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._get_headers(),
            timeout=30.0
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for API requests"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Renum-Python-SDK/1.0.0"
        }
        
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        return headers
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()
    
    # Agent Management
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List available agents"""
        response = await self.client.get("/api/v1/agents")
        response.raise_for_status()
        return response.json()
    
    async def execute_agent(
        self,
        agent_id: str,
        capability: str,
        input_data: Dict[str, Any],
        credential_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute an agent capability"""
        payload = {
            "agent_id": agent_id,
            "capability": capability,
            "input_data": input_data
        }
        
        if credential_id:
            payload["credential_id"] = credential_id
        
        response = await self.client.post("/api/v1/agents/execute", json=payload)
        response.raise_for_status()
        return response.json()
    
    # Orchestrator
    async def execute_workflow(
        self,
        workflow_name: str,
        strategy: str,
        agents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a multi-agent workflow"""
        payload = {
            "workflow_name": workflow_name,
            "strategy": strategy,
            "agents": agents
        }
        
        response = await self.client.post("/api/v1/orchestrator/execute", json=payload)
        response.raise_for_status()
        return response.json()
    
    # Credentials Management
    async def create_credential(
        self,
        name: str,
        provider: str,
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new credential"""
        payload = {
            "name": name,
            "provider": provider,
            "credentials": credentials
        }
        
        response = await self.client.post("/api/v1/credentials", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def list_credentials(self) -> List[Dict[str, Any]]:
        """List user credentials"""
        response = await self.client.get("/api/v1/credentials")
        response.raise_for_status()
        return response.json()
    
    # Integrations
    async def create_integration(
        self,
        name: str,
        provider: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new integration"""
        payload = {
            "name": name,
            "provider": provider,
            "settings": settings
        }
        
        response = await self.client.post("/api/v1/integrations", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def list_integrations(self) -> List[Dict[str, Any]]:
        """List user integrations"""
        response = await self.client.get("/api/v1/integrations")
        response.raise_for_status()
        return response.json()
    
    # Analytics
    async def get_agent_analytics(
        self,
        agent_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get analytics for a specific agent"""
        response = await self.client.get(
            f"/api/v1/analytics/agents/{agent_id}",
            params={"hours": hours}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_billing_summary(
        self,
        tier: str = "free",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get billing summary"""
        params = {"tier": tier}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        response = await self.client.get("/api/v1/analytics/billing/summary", params=params)
        response.raise_for_status()
        return response.json()
    
    # Fallback System
    async def handle_unsupported_integration(
        self,
        integration_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle unsupported integration request"""
        payload = {
            "integration_name": integration_name,
            "context": context
        }
        
        response = await self.client.post("/api/v1/fallback/unsupported", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_integration_suggestions(
        self,
        target_integration: str,
        required_capabilities: List[str],
        use_case: Optional[str] = None,
        strategy: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """Get integration suggestions"""
        payload = {
            "target_integration": target_integration,
            "required_capabilities": required_capabilities,
            "use_case": use_case,
            "strategy": strategy
        }
        
        response = await self.client.post("/api/v1/fallback/suggestions", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Example Usage Functions

async def example_send_whatsapp_message():
    """Example: Send WhatsApp message using Renum API"""
    client = RenumAPIClient(api_token="your-api-token-here")
    
    try:
        # 1. Create WhatsApp credentials
        whatsapp_creds = await client.create_credential(
            name="My WhatsApp Business",
            provider="whatsapp_business",
            credentials={
                "access_token": "your-whatsapp-access-token",
                "phone_number_id": "your-phone-number-id",
                "business_account_id": "your-business-account-id"
            }
        )
        
        print(f"Created WhatsApp credentials: {whatsapp_creds['id']}")
        
        # 2. Execute WhatsApp agent to send message
        result = await client.execute_agent(
            agent_id="sa-whatsapp",
            capability="send_message",
            input_data={
                "recipient": "+1234567890",
                "message": "Hello from Renum API!",
                "message_type": "text"
            },
            credential_id=whatsapp_creds['id']
        )
        
        print(f"Message sent successfully: {result}")
        
    finally:
        await client.close()

async def example_multi_agent_workflow():
    """Example: Execute multi-agent workflow"""
    client = RenumAPIClient(api_token="your-api-token-here")
    
    try:
        # Execute workflow: Email notification + Database update + WhatsApp alert
        workflow_result = await client.execute_workflow(
            workflow_name="Customer Onboarding",
            strategy="sequential",
            agents=[
                {
                    "agent_id": "sa-gmail",
                    "capability": "send_email",
                    "input_data": {
                        "to": "customer@example.com",
                        "subject": "Welcome to our platform!",
                        "body": "Thank you for signing up. Here's how to get started..."
                    }
                },
                {
                    "agent_id": "sa-supabase",
                    "capability": "create_record",
                    "input_data": {
                        "table": "customers",
                        "data": {
                            "email": "customer@example.com",
                            "status": "onboarded",
                            "onboarded_at": datetime.utcnow().isoformat()
                        }
                    }
                },
                {
                    "agent_id": "sa-whatsapp",
                    "capability": "send_notification",
                    "input_data": {
                        "recipient": "+1234567890",
                        "message": "New customer onboarded: customer@example.com"
                    }
                }
            ]
        )
        
        print(f"Workflow executed: {workflow_result}")
        print(f"Status: {workflow_result['status']}")
        print(f"Success rate: {workflow_result['success_rate']}%")
        
    finally:
        await client.close()

async def example_handle_unsupported_integration():
    """Example: Handle unsupported integration with intelligent suggestions"""
    client = RenumAPIClient(api_token="your-api-token-here")
    
    try:
        # Request handling for unsupported integration
        result = await client.handle_unsupported_integration(
            integration_name="slack",
            context={
                "use_case": "team communication",
                "required_features": ["send_message", "receive_message", "file_sharing"],
                "complexity_preference": "simple",
                "cost_sensitive": True
            }
        )
        
        print(f"Integration: {result['integration_name']}")
        print(f"Supported: {result['supported']}")
        print(f"Can use generic HTTP: {result['can_use_generic_http']}")
        print(f"Estimated development time: {result['estimated_development_time']}")
        
        print("\nSuggestions:")
        for suggestion in result['suggestions']:
            print(f"  - {suggestion['title']}")
            print(f"    Type: {suggestion['type']}")
            print(f"    Confidence: {suggestion['confidence_score']:.1%}")
            print(f"    Effort: {suggestion['implementation_effort']}")
            print(f"    Available now: {suggestion['available_now']}")
            print()
        
        # Get detailed suggestions
        suggestions = await client.get_integration_suggestions(
            target_integration="slack",
            required_capabilities=["send_message", "receive_message"],
            use_case="team communication",
            strategy="hybrid"
        )
        
        print("Detailed suggestions:")
        for suggestion in suggestions:
            print(f"  - {suggestion['integration_name']} (Score: {suggestion['match_score']:.2f})")
            print(f"    Setup: {suggestion['setup_complexity']} ({suggestion['estimated_setup_time']})")
            print(f"    Pros: {', '.join(suggestion['pros'][:3])}")
            print(f"    Cons: {', '.join(suggestion['cons'][:2])}")
            print()
        
    finally:
        await client.close()

async def example_analytics_and_monitoring():
    """Example: Get analytics and monitoring data"""
    client = RenumAPIClient(api_token="your-api-token-here")
    
    try:
        # Get agent analytics
        agent_analytics = await client.get_agent_analytics("sa-whatsapp", hours=24)
        print(f"WhatsApp Agent Analytics (24h):")
        print(f"  Total executions: {agent_analytics['total_count']}")
        print(f"  Success rate: {agent_analytics['success_rate_percent']:.1f}%")
        print(f"  Average execution time: {agent_analytics['execution_stats']['avg']:.0f}ms")
        
        # Get billing summary
        billing = await client.get_billing_summary(tier="starter")
        print(f"\nBilling Summary:")
        print(f"  Tier: {billing['tier']}")
        print(f"  Monthly fee: ${billing['costs']['monthly_fee_cents'] / 100:.2f}")
        print(f"  Usage - Executions: {billing['usage']['executions']}")
        print(f"  Usage - API requests: {billing['usage']['api_requests']}")
        print(f"  Total cost: ${billing['costs']['total_cost_cents'] / 100:.2f}")
        
    finally:
        await client.close()

# Main execution examples
if __name__ == "__main__":
    # Set your API token
    import os
    api_token = os.getenv("RENUM_API_TOKEN", "your-api-token-here")
    
    print("Renum API Python SDK Examples")
    print("=" * 40)
    
    # Run examples
    asyncio.run(example_send_whatsapp_message())
    print("\n" + "-" * 40 + "\n")
    
    asyncio.run(example_multi_agent_workflow())
    print("\n" + "-" * 40 + "\n")
    
    asyncio.run(example_handle_unsupported_integration())
    print("\n" + "-" * 40 + "\n")
    
    asyncio.run(example_analytics_and_monitoring())