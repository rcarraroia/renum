# Multi-stage Dockerfile para Renum API
FROM python:3.11-slim as builder

# Configurações de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instala dependências de build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos de dependências
COPY pyproject.toml README.md ./

# Instala dependências em um ambiente virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel
RUN pip install -e .

# Estágio de produção
FROM python:3.11-slim as production

# Configurações de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Instala apenas dependências de runtime
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia ambiente virtual do estágio de build
COPY --from=builder /opt/venv /opt/venv

# Cria usuário não-root
RUN useradd --create-home --shell /bin/bash --uid 1000 renum

# Define diretório de trabalho
WORKDIR /app

# Copia código da aplicação
COPY app/ ./app/
COPY pyproject.toml README.md ./

# Muda propriedade dos arquivos
RUN chown -R renum:renum /app

# Muda para usuário não-root
USER renum

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expõe porta
EXPOSE 8000

# Comando padrão com configurações otimizadas
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log", \
     "--log-level", "info"]