"""
Aplicação principal do Renum API.

Este módulo inicializa a aplicação FastAPI com a nova arquitetura limpa,
configurando middlewares, rotas e eventos de ciclo de vida.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    yield
    
    # Encerramento
    logger.info("Shutting down Renum API v1")
    
    # Fecha conexões
    await suna_client.close()


# Cria aplicação FastAPI
app = FastAPI(
    title="Renum API",
    description="""
    API for Renum - Agent Teams Orchestration Platform
    
    This API allows you to create, manage, and execute teams of AI agents
    with different workflow strategies (sequential, parallel, pipeline, conditional).
    
    ## Features
    
    * **Team Management**: Create and manage agent teams
    * **Workflow Execution**: Execute teams with real-time monitoring
    * **Agent Integration**: Seamless integration with Suna Backend
    * **Real-time Updates**: WebSocket support for live updates
    * **Authentication**: Secure JWT-based authentication
    
    ## Authentication
    
    Include your JWT token in the Authorization header:
    ```
    Authorization: Bearer YOUR_TOKEN
    ```
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra rotas
from app.api.v1.health import router as health_router
from app.api.v1.teams import router as teams_router
from app.api.v1.executions import router as team_executions_router, executions_router
from app.api.v1.websocket import router as websocket_router

app.include_router(health_router, tags=["Health"])
app.include_router(teams_router, prefix="/api/v1", tags=["Teams"])
app.include_router(team_executions_router, prefix="/api/v1", tags=["Executions"])
app.include_router(executions_router, prefix="/api/v1", tags=["Executions"])
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])


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