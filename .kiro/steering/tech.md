# Stack Tecnológico

## Arquitetura Backend

- **Framework**: FastAPI (Python 3.11+)
- **Padrão Arquitetural**: Clean Architecture com Domain-Driven Design
- **Banco de Dados**: Supabase (PostgreSQL) com Row Level Security
- **Autenticação**: Supabase Auth + tokens JWT
- **Tempo Real**: Conexões WebSocket
- **Cliente HTTP**: httpx para chamadas de API externas
- **Rate Limiting**: slowapi middleware
- **Logging**: structlog para logging estruturado

## Dependências Principais

```python
# Framework Core
fastapi>=0.115.0
uvicorn[standard]>=0.27.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Banco de Dados & Auth
supabase>=2.17.0

# Comunicação
httpx>=0.28.0
websockets>=13.1
aiohttp>=3.8.0

# Segurança
pyjwt>=2.10.0
python-jose[cryptography]>=3.3.0
cryptography>=45.0.0

# Utilitários
python-dotenv>=1.0.0
python-multipart>=0.0.6
structlog>=25.4.0
redis>=5.0.0
slowapi>=0.1.9
```

## Ferramentas de Desenvolvimento

- **Testes**: pytest com suporte asyncio
- **Qualidade de Código**: black, ruff, mypy
- **Gerenciamento de Pacotes**: pip com pyproject.toml
- **Pre-commit**: hooks para qualidade de código

## Comandos Comuns

### Configuração de Desenvolvimento
```bash
cd apps/api
pip install -e .
# Configurar .env baseado em .env.production.example
python start_server.py
```

### Operações de Banco de Dados
```bash
cd apps/api/migrations
python run_migrations.py
```

### Testes
```bash
cd apps/api
pytest                    # Executar todos os testes
pytest -m unit           # Apenas testes unitários
pytest -m integration    # Apenas testes de integração
pytest --cov=app         # Com cobertura
pytest -v                # Modo verboso
```

### Qualidade de Código
```bash
black .                   # Formatar código
ruff check .             # Lint código
mypy app/                # Verificação de tipos
pre-commit run --all-files  # Executar hooks
```

### Deploy de Produção
```bash
./deploy-production.sh   # Deploy completo de produção
docker-compose -f docker-compose.production.yml up -d
```

## Integrações Externas

- **Suna Backend**: Motor principal de execução de agentes IA
  - API: `http://157.180.39.41:8000/api`
  - WebSocket: `ws://157.180.39.41:8000/ws`
- **Supabase**: Provedor de banco de dados e autenticação
- **Redis**: Cache e sessões (opcional)

## Configurações de Ambiente

### Variáveis Obrigatórias
```env
# Supabase
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# JWT
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Suna Backend
SUNA_API_URL=http://157.180.39.41:8000/api
SUNA_WS_URL=ws://157.180.39.41:8000/ws
SUNA_API_KEY=...

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

## Padrões de Código

- **Async/Await**: Usar sempre para operações I/O
- **Type Hints**: Obrigatório em todas as funções
- **Docstrings**: Documentar classes e métodos públicos
- **Error Handling**: Usar HTTPException para erros de API
- **Logging**: Usar structlog para logs estruturados