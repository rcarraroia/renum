"""
Aplicação principal do Renum API.

Este módulo inicializa a aplicação FastAPI com a nova arquitetura limpa,
configurando middlewares, rotas e eventos de ciclo de vida.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from contextlib import asynccontextmanager
import logging

# Import security middlewares
from app.middleware.security_headers import security_headers, cors_security
from app.middleware.rate_limit import rate_limiter, ip_whitelist
from app.middleware.validation import request_validator
from app.middleware.audit_logging import audit_logging
from app.middleware.metrics import metrics_middleware
from app.core.config import get_settings

# Import monitoring services
from app.services.performance_monitor import performance_monitor
from app.services.alerting_service import alerting_service

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de ciclo de vida da aplicação."""
    # Inicialização
    logger.info("Starting Renum API v1")
    
    # Inicializa clientes de infraestrutura
    from app.infra.suna.client import suna_client
    
    try:
        # Testa conexão com Suna
        health = await suna_client.health_check()
        logger.info(f"Suna Backend status: {health['status']}")
    except Exception as e:
        logger.warning(f"Could not connect to Suna Backend: {e}")
    
    # Start monitoring services
    try:
        await performance_monitor.start_monitoring()
        logger.info("Performance monitoring started")
        
        await alerting_service.start_monitoring()
        logger.info("Alerting service started")
    except Exception as e:
        logger.error(f"Failed to start monitoring services: {e}")
    
    # Start manifest cache service
    try:
        from app.services.manifest_cache_service import manifest_cache_service
        await manifest_cache_service.start()
        logger.info("Manifest cache service started")
    except Exception as e:
        logger.error(f"Failed to start manifest cache service: {e}")
    
    yield
    
    # Encerramento
    logger.info("Shutting down Renum API v1")
    
    # Stop monitoring services
    try:
        await performance_monitor.stop_monitoring()
        await alerting_service.stop_monitoring()
        logger.info("Monitoring services stopped")
    except Exception as e:
        logger.error(f"Error stopping monitoring services: {e}")
    
    # Stop manifest cache service
    try:
        from app.services.manifest_cache_service import manifest_cache_service
        await manifest_cache_service.stop()
        logger.info("Manifest cache service stopped")
    except Exception as e:
        logger.error(f"Error stopping manifest cache service: {e}")
    
    # Fecha conexões
    await suna_client.close()


# Cria aplicação FastAPI
app = FastAPI(
    title="Renum API",
    description="""
    # Renum API - Agent Teams Orchestration Platform
    
    Welcome to the **Renum API**, a comprehensive platform for orchestrating teams of AI agents 
    with advanced workflow strategies, real-time monitoring, and intelligent fallback systems.
    
    ## 🚀 Overview
    
    Renum enables you to create, manage, and execute sophisticated multi-agent workflows with 
    support for various execution strategies including sequential, parallel, pipeline, and 
    conditional orchestration patterns.
    
    ## 🔧 Key Features
    
    ### Agent Management
    - **Sub-Agents**: Gmail, WhatsApp, Telegram, Supabase, HTTP Generic
    - **Agent Registry**: Centralized agent discovery and management
    - **Capability Matching**: Intelligent agent selection based on requirements
    
    ### Workflow Orchestration
    - **Multiple Strategies**: Sequential, Parallel, Pipeline, Conditional
    - **Real-time Execution**: WebSocket-based live updates
    - **Error Handling**: Comprehensive retry and fallback mechanisms
    
    ### Integration System
    - **Webhook Processing**: Multi-platform webhook handling
    - **Third-party Connectors**: Zapier, Make, n8n, Pipedream support
    - **Fallback System**: Intelligent suggestions for unsupported tools
    
    ### Security & Monitoring
    - **JWT Authentication**: Supabase integration + local tokens
    - **Rate Limiting**: Redis-backed with intelligent thresholds
    - **Analytics**: Real-time metrics and performance monitoring
    - **Audit Logging**: Comprehensive compliance logging
    
    ### Billing & Cost Tracking
    - **Multi-tier Billing**: Free, Starter, Professional, Enterprise
    - **Cost Analytics**: Detailed usage and cost breakdown
    - **Usage Monitoring**: Real-time tracking and alerts
    
    ## 📚 API Structure
    
    The API is organized into logical modules:
    
    - **`/health`** - System health and status checks
    - **`/api/v1/agents`** - Sub-agent management and execution
    - **`/api/v1/orchestrator`** - Multi-agent workflow orchestration
    - **`/api/v1/integrations`** - Integration and webhook management
    - **`/api/v1/credentials`** - Secure credential management (BYOC)
    - **`/api/v1/analytics`** - Analytics and monitoring endpoints
    - **`/api/v1/fallback`** - Fallback system for unsupported tools
    - **`/api/v1/admin`** - Administrative endpoints (admin only)
    
    ## 🔐 Authentication
    
    All endpoints (except health checks) require authentication via JWT tokens:
    
    ```http
    Authorization: Bearer YOUR_JWT_TOKEN
    ```
    
    ### Supported Authentication Methods:
    - **Supabase Auth**: OAuth2 with JWKS verification
    - **Local JWT**: Custom token generation and validation
    - **Admin Tokens**: Special tokens for administrative access
    
    ## 📊 Rate Limiting
    
    API requests are subject to rate limiting based on user tier:
    
    | Tier | Requests/Min | Requests/Hour | Requests/Day |
    |------|--------------|---------------|--------------|
    | Free | 60 | 1,000 | 10,000 |
    | Starter | 300 | 5,000 | 50,000 |
    | Professional | 300 | 5,000 | 50,000 |
    | Enterprise | 300 | 5,000 | 50,000 |
    
    Rate limit headers are included in all responses:
    - `X-RateLimit-Limit`: Request limit for the current window
    - `X-RateLimit-Remaining`: Remaining requests in current window
    - `X-RateLimit-Reset`: Unix timestamp when the window resets
    
    ## 🚨 Error Handling
    
    The API uses standard HTTP status codes and returns detailed error information:
    
    ```json
    {
        "error": "Validation Error",
        "message": "Invalid input parameters",
        "details": {
            "field": "email",
            "issue": "Invalid email format"
        },
        "request_id": "req_123456789"
    }
    ```
    
    ### Common Status Codes:
    - **200**: Success
    - **201**: Created
    - **400**: Bad Request (validation errors)
    - **401**: Unauthorized (invalid/missing token)
    - **403**: Forbidden (insufficient permissions)
    - **404**: Not Found
    - **429**: Too Many Requests (rate limited)
    - **500**: Internal Server Error
    
    ## 🔄 WebSocket Support
    
    Real-time updates are available via WebSocket connections:
    
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws');
    ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        console.log('Execution update:', update);
    };
    ```
    
    ## 📈 Monitoring & Analytics
    
    Built-in monitoring provides insights into:
    - API performance and response times
    - Agent execution statistics
    - Integration success rates
    - Cost tracking and billing analytics
    - System resource utilization
    
    ## 🛠️ SDKs and Examples
    
    Official SDKs and code examples are available for:
    - Python
    - JavaScript/TypeScript
    - cURL commands
    - Postman collections
    
    ## 📞 Support
    
    - **Documentation**: [https://docs.renum.com](https://docs.renum.com)
    - **GitHub**: [https://github.com/renum/api](https://github.com/renum/api)
    - **Support**: support@renum.com
    - **Status Page**: [https://status.renum.com](https://status.renum.com)
    
    ---
    
    **Version**: 1.0.0 | **Environment**: Production | **Last Updated**: December 2024 
    conditional orchestration.
    
    ## ✨ Key Features
    
    ### 🤖 Agent Management
    - **Sub-Agents**: Gmail, WhatsApp, Telegram, Supabase, HTTP Generic
    - **Agent Registry**: Centralized agent discovery and management
    - **Capability Matching**: Intelligent agent selection based on requirements
    
    ### 🔄 Workflow Orchestration
    - **Multiple Strategies**: Sequential, parallel, pipeline, conditional execution
    - **Real-time Monitoring**: Live execution tracking with WebSocket updates
    - **Error Handling**: Comprehensive retry and fallback mechanisms
    
    ### 🔗 Integration System
    - **Webhook Processing**: Support for multiple platforms (Zapier, Make, n8n, Pipedream)
    - **Third-party Connectors**: Seamless integration with external services
    - **Fallback System**: Intelligent suggestions for unsupported integrations
    
    ### 🔐 Security & Authentication
    - **JWT Authentication**: Secure token-based authentication with Supabase integration
    - **Rate Limiting**: Advanced rate limiting with Redis backend
    - **Request Validation**: Comprehensive input sanitization and security checks
    - **Audit Logging**: Complete audit trail for compliance
    
    ### 📊 Analytics & Monitoring
    - **Real-time Metrics**: Performance monitoring and analytics
    - **Cost Tracking**: Detailed billing and usage analytics
    - **Alerting System**: Proactive monitoring with customizable alerts
    - **Admin Panel**: Comprehensive system administration tools
    
    ### 🛠️ Developer Experience
    - **OpenAPI Documentation**: Complete API specification with examples
    - **SDK Support**: Client libraries and code examples
    - **Sandbox Environment**: Safe testing environment for development
    - **Comprehensive Testing**: Unit, integration, and performance tests
    
    ## 🔑 Authentication
    
    All API endpoints require authentication using JWT tokens. Include your token in the Authorization header:
    
    ```http
    Authorization: Bearer YOUR_JWT_TOKEN
    ```
    
    ### Getting Started
    
    1. **Obtain JWT Token**: Authenticate through Supabase or local auth
    2. **Explore Endpoints**: Use the interactive documentation below
    3. **Create Integrations**: Set up your first webhook integration
    4. **Execute Workflows**: Orchestrate your agent teams
    
    ## 📚 API Sections
    
    - **🏥 Health**: System health and status endpoints
    - **👥 Teams**: Agent team management
    - **⚡ Executions**: Workflow execution and monitoring
    - **🔌 WebSocket**: Real-time updates and notifications
    - **📋 Agent Registry**: Agent discovery and management
    - **🔗 Integrations**: External service integrations
    - **🪝 Webhooks**: Webhook processing and management
    - **🎭 Orchestrator**: Multi-agent workflow orchestration
    - **🔐 Credentials**: Secure credential management
    - **🤖 Sub-Agents**: Individual agent capabilities
    - **👑 Admin Panel**: System administration (admin only)
    - **📊 Analytics**: Metrics and monitoring (admin/user)
    - **🔄 Fallback System**: Unsupported integration handling
    
    ## 🌐 Base URL
    
    **Production**: `https://api.renum.com`  
    **Development**: `http://localhost:8000`
    
    ## 📞 Support
    
    - **Documentation**: [docs.renum.com](https://docs.renum.com)
    - **GitHub**: [github.com/renum/api](https://github.com/renum/api)
    - **Support**: support@renum.com
    
    ---
    
    *Built with ❤️ using FastAPI, Supabase, and modern Python technologies.*
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    contact={
        "name": "Renum API Support",
        "url": "https://renum.com/support",
        "email": "support@renum.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "https://api.renum.com",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.renum.com", 
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ],
    tags_metadata=[
        {
            "name": "Health",
            "description": "System health and status endpoints"
        },
        {
            "name": "Sub-Agents",
            "description": "Individual agent management and execution"
        },
        {
            "name": "Orchestrator", 
            "description": "Multi-agent workflow orchestration"
        },
        {
            "name": "Integrations",
            "description": "Integration and webhook management"
        },
        {
            "name": "Credentials",
            "description": "Secure credential management (BYOC)"
        },
        {
            "name": "Analytics & Monitoring",
            "description": "Performance analytics and system monitoring"
        },
        {
            "name": "Fallback System",
            "description": "Intelligent fallback for unsupported integrations"
        },
        {
            "name": "Admin Panel",
            "description": "Administrative endpoints (admin access required)"
        }
    ],
    contact={
        "name": "Renum API Support",
        "url": "https://docs.renum.com",
        "email": "support@renum.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "https://api.renum.com",
            "description": "Production server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ],
    tags_metadata=[
        {
            "name": "Health",
            "description": "System health and status monitoring endpoints",
        },
        {
            "name": "Teams",
            "description": "Agent team creation and management operations",
        },
        {
            "name": "Executions",
            "description": "Workflow execution, monitoring, and history management",
        },
        {
            "name": "WebSocket",
            "description": "Real-time updates and bidirectional communication",
        },
        {
            "name": "Agent Registry",
            "description": "Agent discovery, registration, and capability management",
        },
        {
            "name": "Integrations",
            "description": "External service integrations and webhook management",
        },
        {
            "name": "Webhooks",
            "description": "Webhook processing for various platforms and services",
        },
        {
            "name": "Orchestrator",
            "description": "Multi-agent workflow orchestration and execution strategies",
        },
        {
            "name": "Credentials",
            "description": "Secure credential storage and management (BYOC)",
        },
        {
            "name": "Sub-Agents",
            "description": "Individual agent capabilities and direct execution",
        },
        {
            "name": "Admin Panel",
            "description": "System administration, monitoring, and management tools",
        },
        {
            "name": "Analytics & Monitoring",
            "description": "Performance metrics, analytics, and system monitoring",
        },
        {
            "name": "Fallback System",
            "description": "Intelligent handling of unsupported integrations and suggestions",
        },
        {
            "name": "Sandbox Environment",
            "description": "Isolated testing environment for safe agent execution",
        },
        {
            "name": "Public Keys",
            "description": "Public key distribution for signature verification",
        },
        {
            "name": "Data Purge & Compliance",
            "description": "Data purging and PII masking for LGPD/GDPR compliance",
        },
    ]
)

# Configure security middlewares
if settings.SECURITY_HEADERS_ENABLED:
    app.middleware("http")(security_headers)
    logger.info("Security headers middleware enabled")

if settings.AUDIT_LOGGING_ENABLED:
    app.middleware("http")(audit_logging)
    logger.info("Audit logging middleware enabled")

if settings.REQUEST_VALIDATION_ENABLED:
    app.middleware("http")(request_validator)
    logger.info("Request validation middleware enabled")

# Metrics collection middleware
app.middleware("http")(metrics_middleware)
logger.info("Metrics collection middleware enabled")

if settings.RATE_LIMIT_ENABLED:
    app.middleware("http")(rate_limiter)
    logger.info("Rate limiting middleware enabled")

# IP whitelist for admin endpoints
app.middleware("http")(ip_whitelist)

# Enhanced CORS with security
app.middleware("http")(cors_security)

# Fallback CORS middleware for compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra rotas
from app.api.v1.health import router as health_router
from app.api.v1.teams import router as teams_router
from app.api.v1.executions import router as team_executions_router, executions_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.agent_registry import router as agent_registry_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.orchestrator import router as orchestrator_router
from app.api.v1.credentials import router as credentials_router
from app.api.v1.agents import router as agents_router
from app.api.v1.admin import router as admin_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.fallback import router as fallback_router
from app.api.v1.prompt_editor import router as prompt_editor_router
from app.api.v1.sandbox import router as sandbox_router
from app.api.v1.keys import router as keys_router
from app.api.v1.manifest_cache import router as manifest_cache_router
from app.api.v1.data_purge import router as data_purge_router

app.include_router(health_router, tags=["Health"])
app.include_router(teams_router, prefix="/api/v1", tags=["Teams"])
app.include_router(team_executions_router, prefix="/api/v1", tags=["Executions"])
app.include_router(executions_router, prefix="/api/v1", tags=["Executions"])
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])
app.include_router(agent_registry_router, prefix="/api/v1", tags=["Agent Registry"])
app.include_router(integrations_router, prefix="/api/v1", tags=["Integrations"])
app.include_router(webhooks_router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(orchestrator_router, prefix="/api/v1", tags=["Orchestrator"])
app.include_router(credentials_router, prefix="/api/v1", tags=["Credentials"])
app.include_router(agents_router, prefix="/api/v1", tags=["Sub-Agents"])
app.include_router(admin_router, prefix="/api/v1", tags=["Admin Panel"])
app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics & Monitoring"])
app.include_router(fallback_router, prefix="/api/v1", tags=["Fallback System"])
app.include_router(prompt_editor_router, prefix="/api/v1", tags=["Prompt Editor"])
app.include_router(sandbox_router, prefix="/api/v1", tags=["Sandbox Environment"])
app.include_router(keys_router, prefix="/api/v1", tags=["Public Keys"])
app.include_router(manifest_cache_router, prefix="/api/v1", tags=["Manifest Cache"])
app.include_router(data_purge_router, prefix="/api/v1", tags=["Data Purge & Compliance"])


@app.get("/")
async def root():
    """Endpoint raiz da aplicação."""
    return {
        "name": "Renum API",
        "version": "1.0.0",
        "description": "Agent Teams Orchestration Platform",
        "docs_url": "/docs",
        "health_url": "/health"
    }