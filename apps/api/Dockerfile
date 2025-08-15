# Dockerfile para Renum API
FROM python:3.11-slim

# Configurações de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN useradd --create-home --shell /bin/bash renum

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos de dependências
COPY pyproject.toml ./

# Instala dependências Python
RUN pip install -e .

# Copia código da aplicação
COPY app/ ./app/

# Muda para usuário não-root
USER renum

# Expõe porta
EXPOSE 8000

# Comando padrão
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]