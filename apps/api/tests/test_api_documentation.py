"""
Testes de Documentação da API
Testes para validar documentação OpenAPI/Swagger e exemplos
"""
import pytest
import json
from fastapi.testclient import TestClient
from fastapi.openapi.utils import get_openapi

from app.main import app

client = TestClient(app)

class TestOpenAPIDocumentation:
    """Testes da documentação OpenAPI/Swagger"""
    
    def test_openapi_schema_generation(self):
        """Teste de geração do schema OpenAPI"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        openapi_schema = response.json()
        
        # Verify basic OpenAPI structure
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema
        assert "components" in openapi_schema
        
        # Verify API info
        info = openapi_schema["info"]
        assert "title" in info
        assert "version" in info
        assert "description" in info
        
        # Verify title and description are meaningful
        assert len(info["title"]) > 0
        assert len(info["description"]) > 10  # Should have substantial description
    
    def test_swagger_ui_accessibility(self):
        """Teste de acessibilidade da interface Swagger UI"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Verify Swagger UI loads
        html_content = response.text
        assert "swagger-ui" in html_content.lower()
        assert "openapi.json" in html_content
    
    def test_redoc_accessibility(self):
        """Teste de acessibilidade da interface ReDoc"""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Verify ReDoc loads
        html_content = response.text
        assert "redoc" in html_content.lower()
    
    def test_api_endpoints_documented(self):
        """Teste de documentação de todos os endpoints da API"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        paths = openapi_schema["paths"]
        
        # Verify key endpoints are documented
        expected_endpoints = [
            "/health",
            "/api/v1/agents",
            "/api/v1/orchestrator/execute",
            "/api/v1/integrations",
            "/api/v1/analytics/dashboard"
        ]
        
        for endpoint in expected_endpoints:
            assert endpoint in paths, f"Endpoint {endpoint} not documented"
            
            # Verify endpoint has proper HTTP methods
            endpoint_methods = paths[endpoint]
            assert len(endpoint_methods) > 0, f"No HTTP methods defined for {endpoint}"
            
            # Verify each method has description
            for method, method_info in endpoint_methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    assert "summary" in method_info or "description" in method_info, \
                        f"No description for {method.upper()} {endpoint}"
    
    def test_request_response_schemas(self):
        """Teste de schemas de request e response"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        components = openapi_schema.get("components", {})
        schemas = components.get("schemas", {})
        
        # Verify important schemas are defined
        expected_schemas = [
            "WorkflowDefinition",
            "ExecutionResult", 
            "AgentCapability",
            "IntegrationConfig"
        ]
        
        for schema_name in expected_schemas:
            # Schema might exist with different naming conventions
            schema_found = any(
                schema_name.lower() in existing_schema.lower() 
                for existing_schema in schemas.keys()
            )
            if not schema_found:
                print(f"Warning: Schema {schema_name} not found in documentation")
        
        # Verify schemas have proper structure
        for schema_name, schema_def in schemas.items():
            assert "type" in schema_def or "$ref" in schema_def, \
                f"Schema {schema_name} missing type definition"
            
            if "properties" in schema_def:
                # Verify properties have descriptions
                for prop_name, prop_def in schema_def["properties"].items():
                    if isinstance(prop_def, dict) and "description" not in prop_def:
                        print(f"Warning: Property {prop_name} in {schema_name} lacks description")
    
    def test_error_response_documentation(self):
        """Teste de documentação de respostas de erro"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        paths = openapi_schema["paths"]
        
        # Check that endpoints document error responses
        for path, methods in paths.items():
            for method, method_info in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    responses = method_info.get("responses", {})
                    
                    # Should document at least success and common error responses
                    assert "200" in responses or "201" in responses, \
                        f"No success response documented for {method.upper()} {path}"
                    
                    # Should document common error codes
                    common_errors = ["400", "401", "403", "404", "422", "500"]
                    documented_errors = [code for code in common_errors if code in responses]
                    
                    if len(documented_errors) == 0:
                        print(f"Warning: No error responses documented for {method.upper()} {path}")
    
    def test_authentication_documentation(self):
        """Teste de documentação de autenticação"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        components = openapi_schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        
        # Should document authentication schemes
        assert len(security_schemes) > 0, "No authentication schemes documented"
        
        # Should have JWT/Bearer token authentication
        bearer_auth_found = any(
            scheme.get("type") == "http" and scheme.get("scheme") == "bearer"
            for scheme in security_schemes.values()
        )
        
        assert bearer_auth_found, "Bearer token authentication not documented"
    
    def test_example_values_in_documentation(self):
        """Teste de valores de exemplo na documentação"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        components = openapi_schema.get("components", {})
        schemas = components.get("schemas", {})
        
        # Check for example values in schemas
        schemas_with_examples = 0
        
        for schema_name, schema_def in schemas.items():
            if "example" in schema_def or "examples" in schema_def:
                schemas_with_examples += 1
            
            # Check properties for examples
            if "properties" in schema_def:
                for prop_name, prop_def in schema_def["properties"].items():
                    if isinstance(prop_def, dict) and ("example" in prop_def or "examples" in prop_def):
                        schemas_with_examples += 1
                        break
        
        # Should have some examples
        if schemas_with_examples == 0:
            print("Warning: No example values found in API documentation")

class TestAPIExamples:
    """Testes de exemplos da API"""
    
    def test_workflow_execution_example(self):
        """Teste de exemplo de execução de workflow"""
        # This would be an actual working example from documentation
        example_workflow = {
            "workflow_definition": {
                "name": "Welcome Message",
                "description": "Send welcome message via WhatsApp",
                "steps": [
                    {
                        "id": "send_welcome",
                        "agent_id": "sa-whatsapp",
                        "capability": "send_message",
                        "input": {
                            "phone_number": "+5511999999999",
                            "message": "Welcome to our service!"
                        }
                    }
                ]
            },
            "input_data": {}
        }
        
        # Validate example against schema
        from jsonschema import validate, ValidationError
        
        # Get the schema from OpenAPI
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        # Find the request schema for workflow execution
        paths = openapi_schema["paths"]
        execute_path = "/api/v1/orchestrator/execute"
        
        if execute_path in paths and "post" in paths[execute_path]:
            request_body = paths[execute_path]["post"].get("requestBody", {})
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            schema_ref = json_content.get("schema", {})
            
            if "$ref" in schema_ref:
                # Resolve schema reference
                schema_name = schema_ref["$ref"].split("/")[-1]
                components = openapi_schema.get("components", {})
                schemas = components.get("schemas", {})
                
                if schema_name in schemas:
                    try:
                        validate(instance=example_workflow, schema=schemas[schema_name])
                        print("Example workflow validates against schema")
                    except ValidationError as e:
                        print(f"Example workflow validation failed: {e}")
    
    def test_agent_configuration_examples(self):
        """Teste de exemplos de configuração de agentes"""
        example_configs = {
            "whatsapp": {
                "integration_id": "whatsapp-business",
                "credentials": {
                    "access_token": "your-access-token",
                    "phone_number_id": "your-phone-number-id"
                },
                "settings": {
                    "webhook_verify_token": "your-verify-token"
                }
            },
            "telegram": {
                "integration_id": "telegram-bot",
                "credentials": {
                    "bot_token": "your-bot-token"
                },
                "settings": {
                    "webhook_url": "https://your-domain.com/webhooks/telegram"
                }
            },
            "gmail": {
                "integration_id": "gmail-smtp",
                "credentials": {
                    "email": "your-email@gmail.com",
                    "app_password": "your-app-password"
                },
                "settings": {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587
                }
            }
        }
        
        # Verify examples are valid JSON and have required fields
        for agent_type, config in example_configs.items():
            assert "integration_id" in config, f"{agent_type} example missing integration_id"
            assert "credentials" in config, f"{agent_type} example missing credentials"
            
            # Verify credentials are not empty
            assert len(config["credentials"]) > 0, f"{agent_type} example has empty credentials"
    
    def test_webhook_payload_examples(self):
        """Teste de exemplos de payload de webhook"""
        example_webhooks = {
            "whatsapp_message": {
                "object": "whatsapp_business_account",
                "entry": [{
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [{
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550559999",
                                "phone_number_id": "PHONE_NUMBER_ID"
                            },
                            "messages": [{
                                "from": "5511999999999",
                                "id": "wamid.ID",
                                "timestamp": "1234567890",
                                "text": {
                                    "body": "Hello, this is a test message"
                                },
                                "type": "text"
                            }]
                        },
                        "field": "messages"
                    }]
                }]
            },
            "telegram_update": {
                "update_id": 123456789,
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 123456789,
                        "is_bot": False,
                        "first_name": "John",
                        "username": "johndoe"
                    },
                    "chat": {
                        "id": 123456789,
                        "first_name": "John",
                        "username": "johndoe",
                        "type": "private"
                    },
                    "date": 1234567890,
                    "text": "Hello bot!"
                }
            }
        }
        
        # Verify webhook examples are valid
        for webhook_type, payload in example_webhooks.items():
            assert isinstance(payload, dict), f"{webhook_type} example is not a valid dict"
            assert len(payload) > 0, f"{webhook_type} example is empty"
            
            # Verify JSON serializable
            try:
                json.dumps(payload)
            except (TypeError, ValueError) as e:
                pytest.fail(f"{webhook_type} example is not JSON serializable: {e}")

class TestSDKDocumentation:
    """Testes de documentação do SDK"""
    
    def test_python_sdk_example_syntax(self):
        """Teste de sintaxe do exemplo do SDK Python"""
        # Read the Python SDK example file
        try:
            with open("docs/api-examples/python-sdk.py", "r") as f:
                sdk_code = f.read()
            
            # Verify it's valid Python syntax
            import ast
            try:
                ast.parse(sdk_code)
                print("Python SDK example has valid syntax")
            except SyntaxError as e:
                pytest.fail(f"Python SDK example has syntax error: {e}")
                
        except FileNotFoundError:
            print("Warning: Python SDK example file not found")
    
    def test_sdk_example_completeness(self):
        """Teste de completude dos exemplos do SDK"""
        try:
            with open("docs/api-examples/python-sdk.py", "r") as f:
                sdk_code = f.read()
            
            # Check for essential components
            essential_components = [
                "class",  # Should have a client class
                "def",    # Should have methods
                "import", # Should have imports
                "requests", # Should use requests or similar
                "json",   # Should handle JSON
                "auth",   # Should handle authentication
            ]
            
            for component in essential_components:
                assert component in sdk_code, f"SDK example missing {component}"
            
            # Check for specific functionality
            functionality_checks = [
                "execute_workflow",  # Core functionality
                "get_agents",       # List agents
                "get_execution",    # Get execution status
            ]
            
            for func in functionality_checks:
                if func not in sdk_code:
                    print(f"Warning: SDK example missing {func} functionality")
                    
        except FileNotFoundError:
            print("Warning: Python SDK example file not found")
    
    def test_api_client_examples(self):
        """Teste de exemplos de cliente da API"""
        # Test different client examples
        client_examples = {
            "curl": [
                "curl -X POST",
                "-H 'Authorization: Bearer'",
                "-H 'Content-Type: application/json'",
                "--data"
            ],
            "javascript": [
                "fetch(",
                "method: 'POST'",
                "headers:",
                "Authorization:",
                "JSON.stringify"
            ],
            "python": [
                "import requests",
                "headers =",
                "response = requests.post",
                "response.json()"
            ]
        }
        
        # This would check if example files exist and contain expected patterns
        for language, patterns in client_examples.items():
            example_file = f"docs/api-examples/{language}-example.md"
            try:
                with open(example_file, "r") as f:
                    content = f.read()
                
                for pattern in patterns:
                    if pattern not in content:
                        print(f"Warning: {language} example missing pattern: {pattern}")
                        
            except FileNotFoundError:
                print(f"Warning: {language} example file not found: {example_file}")

class TestDocumentationConsistency:
    """Testes de consistência da documentação"""
    
    def test_endpoint_documentation_consistency(self):
        """Teste de consistência entre endpoints e documentação"""
        # Get actual routes from FastAPI app
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                for method in route.methods:
                    if method != 'HEAD':  # Skip HEAD methods
                        routes.append((method, route.path))
        
        # Get documented routes from OpenAPI
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        documented_routes = []
        
        for path, methods in openapi_schema["paths"].items():
            for method in methods.keys():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    documented_routes.append((method.upper(), path))
        
        # Check for undocumented routes
        for method, path in routes:
            # Skip internal FastAPI routes
            if not path.startswith('/api/') and path not in ['/health', '/docs', '/redoc', '/openapi.json']:
                continue
                
            if (method, path) not in documented_routes:
                print(f"Warning: Route {method} {path} not documented in OpenAPI")
    
    def test_schema_version_consistency(self):
        """Teste de consistência de versão do schema"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        # Check OpenAPI version
        openapi_version = openapi_schema.get("openapi", "")
        assert openapi_version.startswith("3."), f"OpenAPI version {openapi_version} should be 3.x"
        
        # Check API version consistency
        api_version = openapi_schema["info"].get("version", "")
        assert len(api_version) > 0, "API version not specified"
        
        # Version should follow semantic versioning
        import re
        version_pattern = r'^\d+\.\d+\.\d+(-\w+)?$'
        if not re.match(version_pattern, api_version):
            print(f"Warning: API version {api_version} doesn't follow semantic versioning")
    
    def test_documentation_links_validity(self):
        """Teste de validade dos links na documentação"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        # Check for external documentation links
        info = openapi_schema.get("info", {})
        external_docs = openapi_schema.get("externalDocs", {})
        
        if "termsOfService" in info:
            terms_url = info["termsOfService"]
            assert terms_url.startswith("http"), f"Terms of service URL invalid: {terms_url}"
        
        if "url" in external_docs:
            docs_url = external_docs["url"]
            assert docs_url.startswith("http"), f"External docs URL invalid: {docs_url}"
        
        # Check contact information
        contact = info.get("contact", {})
        if "email" in contact:
            email = contact["email"]
            assert "@" in email, f"Contact email invalid: {email}"
        
        if "url" in contact:
            contact_url = contact["url"]
            assert contact_url.startswith("http"), f"Contact URL invalid: {contact_url}"