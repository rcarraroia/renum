from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from contextlib import asynccontextmanager
import logging
import structlog

from app.core.config import get_settings

# Configuração de logging estruturado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configurações
settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)# Reconfigura aplicação FastAPI com configurações dinâmicas
app = FastAPI(# Configura CORS com configurações dinâmicas
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# Adiciona middleware de rate limiting
app.add_middleware(SlowAPIMiddleware)@app.get("/")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/minute")
async def root(request: Request):
    """Endpoint raiz da aplicação."""
    logger.info("Root endpoint accessed", extra={"endpoint": "/"})
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Agent Teams Orchestration Platform",
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "health_url": "/health"
    }# Registra rotas
from app.api.v1.health import router as health_router
from app.api.v1.teams import router as teams_router
from app.api.v1.executions import router as team_executions_router, executions_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.webhooks import router as webhooks_router

app.include_router(health_router, tags=["Health"])
app.include_router(teams_router, prefix="/api/v1", tags=["Teams"])
app.include_router(team_executions_router, prefix="/api/v1", tags=["Executions"])
app.include_router(executions_router, prefix="/api/v1", tags=["Executions"])
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])
app.include_router(integrations_router, prefix="/api/v1", tags=["Integrations"])
app.include_router(webhooks_router, prefix="/api/v1", tags=["Webhooks"])