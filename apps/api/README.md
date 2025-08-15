# Renum API

API para orquestração de equipes de agentes IA.

## 🚀 Configuração Rápida

### 1. Instalar Dependências

```bash
pip install -e .
```

### 2. Configurar Supabase

**IMPORTANTE**: Execute o script SQL no Supabase Dashboard:

1. Acesse: https://ldfzypnyjqoyzqcnkcdy.supabase.co
2. Vá em SQL Editor
3. Execute o conteúdo do arquivo `setup_supabase.sql`

### 3. Testar Conexão

```bash
python test_supabase.py
```

### 4. Iniciar o Servidor

```bash
python start_server.py
```

O servidor estará disponível em: http://localhost:8000

### 5. Testar API Completa

```bash
python test_complete.py
```

## Endpoints Disponíveis

### Autenticação

- `POST /api/v1/auth/signup` - Registrar novo usuário
- `POST /api/v1/auth/login` - Fazer login
- `GET /api/v1/auth/me` - Obter informações do usuário atual
- `POST /api/v1/auth/refresh` - Renovar token

### Health Check

- `GET /health` - Verificar saúde da aplicação
- `GET /health/services` - Verificar saúde dos serviços

### Documentação

- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc

## Exemplo de Uso

### Registro

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "name": "User Name"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Usar Token

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Status

✅ **Autenticação** - Endpoints `/login` e `/signup` funcionando
✅ **Health Checks** - Monitoramento básico
🚧 **Teams** - Em desenvolvimento
🚧 **Executions** - Em desenvolvimento
🚧 **WebSocket** - Em desenvolvimento

## Arquitetura

- **FastAPI** - Framework web
- **Supabase** - Autenticação e banco de dados
- **JWT** - Tokens de acesso
- **Pydantic** - Validação de dados
- **Suna Backend** - Integração com agentes IA