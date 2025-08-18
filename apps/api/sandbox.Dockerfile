# Dockerfile específico para ambiente sandbox
FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para sandbox
RUN groupadd -r sandbox && useradd -r -g sandbox sandbox

# Configurar diretório de trabalho
WORKDIR /app

# Copiar requirements básicos
COPY requirements-sandbox.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements-sandbox.txt

# Criar diretórios necessários
RUN mkdir -p /app/logs /app/data && \
    chown -R sandbox:sandbox /app

# Configurar usuário
USER sandbox

# Comando padrão (será sobrescrito)
CMD ["python", "-c", "print('Sandbox container ready')"]

# Labels
LABEL maintainer="Renum Team <dev@renum.com>"
LABEL version="1.0.0"
LABEL description="Renum Sandbox Environment"
LABEL security.isolation="true"