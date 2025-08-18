# Multi-stage Dockerfile para produção otimizada
FROM python:3.11-slim as builder

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências
COPY pyproject.toml requirements.txt ./

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Estágio de produção
FROM python:3.11-slim as production

# Criar usuário não-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Instalar dependências de runtime
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretório de trabalho
WORKDIR /app

# Copiar dependências do estágio builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código da aplicação
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY start_server.py ./
COPY .env.production.example ./.env

# Criar diretórios necessários
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Configurar usuário
USER appuser

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando padrão
CMD ["python", "start_server.py"]

# Labels para metadados
LABEL maintainer="Renum Team <dev@renum.com>"
LABEL version="1.0.0"
LABEL description="Renum Multi-Agent Integration API"