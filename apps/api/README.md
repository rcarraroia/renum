# Renum API

API backend para o sistema Renum de orquestração de agentes AI.

## 🚀 Funcionalidades

- **Gerenciamento de Equipes**: CRUD completo para equipes de agentes
- **Execução de Workflows**: Suporte a workflows sequenciais, paralelos e condicionais
- **WebSocket em Tempo Real**: Atualizações ao vivo do status das execuções
- **Integração com Suna Backend**: Comunicação isolada com o backend de agentes
- **Autenticação JWT**: Segurança baseada em tokens
- **Documentação Automática**: OpenAPI/Swagger integrado

## 📁 Estrutura do Projeto

```
app/
├── api/v1/           # Endpoints da API v1
│   ├── teams.py      # Gerenciamento de equipes
│   ├── executions.py # Gerenciamento de execuções
│   ├── websocket.py  # WebSocket para tempo real
│   └── health.py     # Health checks
├── core/             # Configurações centrais
│   └── security.py   # Autenticação e segurança
├── domain/           # Entidades de domínio
│   └── team.py       # Entidades de equipe
├── infra/            # Infraestrutura
│   ├── suna/         # Cliente Suna Backend
│   └── websocket/    # Gerenciador WebSocket
├── schemas/          # Schemas Pydantic
│   ├── team.py       # Schemas de equipe
│   ├── execution.py  # Schemas de execução
│   └── base.py       # Schemas base
├── usecases/         # Casos de uso/serviços
│   ├── team_service.py      # Lógica de equipes
│   └── execution_service.py # Lógica de execuções
└── main.py           # Aplicação FastAPI
```

## 🛠️ Desenvolvimento

### Pré-requisitos

- Python 3.9+
- Docker (opcional)
- Git

### Instalação Rápida

```bash
# Clone o repositório
git clone <repo-url>
cd renum/apps/api

# Instale dependências
pip install -e ".[dev]"

# Execute testes básicos
python test_simple.py

# Inicie o servidor de desenvolvimento
./scripts/dev.sh start
```

### Scripts de Desenvolvimento

```bash
# Instalar dependências
./scripts/dev.sh install

# Executar testes
./scripts/dev.sh test

# Executar linting
./scripts/dev.sh lint

# Iniciar servidor (com testes e linting)
./scripts/dev.sh start

# Iniciar servidor rápido (sem testes)
./scripts/dev.sh quick

# Iniciar com Docker
./scripts/dev.sh docker
```

### Variáveis de Ambiente

```bash
# Desenvolvimento
export ENVIRONMENT=development
export LOG_LEVEL=debug
export PORT=8000

# Produção
export ENVIRONMENT=production
export LOG_LEVEL=info
export SUPABASE_URL=your_supabase_url
export SUPABASE_KEY=your_supabase_key
```

## 🧪 Testes

### Executar Todos os Testes

```bash
# Testes básicos
python test_simple.py
python test_endpoints.py

# Testes unitários (quando disponíveis)
pytest tests/ -v

# Testes com coverage
pytest tests/ --cov=app --cov-report=html
```

### Estrutura de Testes

```
tests/
├── test_websocket.py    # Testes WebSocket
├── test_teams.py        # Testes de equipes
├── test_executions.py   # Testes de execuções
└── __init__.py
```

## 🐳 Docker

### Build e Execução

```bash
# Build da imagem
docker build -t renum-api .

# Executar container
docker run -p 8000:8000 renum-api

# Com Docker Compose
docker-compose up --build
```

### Scripts de Deploy

```bash
# Deploy completo
./scripts/deploy.sh deploy

# Apenas build
./scripts/deploy.sh build

# Verificar status
./scripts/deploy.sh status

# Ver logs
./scripts/deploy.sh logs

# Parar serviço
./scripts/deploy.sh stop
```

## 📚 Documentação da API

### Endpoints Principais

- **GET /health** - Health check
- **GET /docs** - Documentação Swagger
- **GET /redoc** - Documentação ReDoc

### Teams API

- **POST /api/v1/teams** - Criar equipe
- **GET /api/v1/teams** - Listar equipes
- **GET /api/v1/teams/{id}** - Obter equipe
- **PUT /api/v1/teams/{id}** - Atualizar equipe
- **DELETE /api/v1/teams/{id}** - Deletar equipe

### Executions API

- **POST /api/v1/teams/{id}/execute** - Iniciar execução
- **GET /api/v1/executions** - Listar execuções
- **GET /api/v1/executions/{id}** - Obter execução
- **POST /api/v1/executions/{id}/cancel** - Cancelar execução

### WebSocket

- **WS /api/v1/ws** - Conexão WebSocket para tempo real

### Acesso Local

- 🌐 **API**: http://localhost:8000
- 📚 **Docs**: http://localhost:8000/docs
- 🔍 **ReDoc**: http://localhost:8000/redoc
- ❤️ **Health**: http://localhost:8000/health

## 🔧 Configuração

### Integração Suna Backend

```python
# app/infra/suna/client.py
SUNA_API_URL = "http://157.180.39.41:8000/api"
```

### Banco de Dados

O projeto usa Supabase como backend. Configure as variáveis:

```bash
export SUPABASE_URL=your_supabase_url
export SUPABASE_KEY=your_supabase_key
```

### WebSocket

O WebSocket suporta os seguintes eventos:

- `subscribe_execution` - Inscrever em execução
- `unsubscribe_execution` - Cancelar inscrição
- `ping` - Keep-alive
- `get_status` - Status da conexão

## 🚀 Deploy

### CI/CD

O projeto inclui GitHub Actions para:

- Testes automatizados
- Linting e formatação
- Verificações de segurança
- Build de imagens Docker

### Produção

```bash
# Deploy com script
./scripts/deploy.sh deploy

# Ou manualmente
docker build -t renum-api .
docker run -d --name renum-api -p 8000:8000 renum-api
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Execute os testes: `./scripts/dev.sh test`
4. Execute o linting: `./scripts/dev.sh lint`
5. Commit suas mudanças
6. Abra um Pull Request

## 📝 Licença

MIT License - veja o arquivo LICENSE para detalhes.

## 🆘 Suporte

- 📧 Email: info@renum.com
- 🐛 Issues: GitHub Issues
- 📖 Docs: http://localhost:8000/docs