#!/bin/bash

# Script de desenvolvimento para Renum API
set -e

# Configurações
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-true}"
LOG_LEVEL="${LOG_LEVEL:-debug}"

echo "🔧 Iniciando Renum API em modo desenvolvimento..."

# Função para logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Função para verificar dependências
check_dependencies() {
    log "🔍 Verificando dependências..."
    
    # Verifica se Python está instalado
    if ! command -v python &> /dev/null; then
        log "❌ Python não encontrado. Por favor, instale Python 3.9+"
        exit 1
    fi
    
    # Verifica versão do Python
    python_version=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version < 3.9" | bc -l) -eq 1 ]]; then
        log "❌ Python 3.9+ é necessário. Versão atual: $python_version"
        exit 1
    fi
    
    log "✅ Python $python_version encontrado"
}

# Função para instalar dependências
install_dependencies() {
    log "📦 Instalando dependências..."
    
    # Instala dependências de desenvolvimento
    pip install -e ".[dev]"
    
    log "✅ Dependências instaladas"
}

# Função para executar testes
run_tests() {
    log "🧪 Executando testes rápidos..."
    
    # Executa testes básicos
    python test_simple.py
    python test_endpoints.py
    
    log "✅ Testes básicos passaram"
}

# Função para executar linting
run_linting() {
    log "🔍 Executando linting..."
    
    # Executa ruff para verificar código
    if command -v ruff &> /dev/null; then
        ruff check app --fix
        ruff format app
        log "✅ Linting concluído"
    else
        log "⚠️ Ruff não encontrado, pulando linting"
    fi
}

# Função para iniciar servidor de desenvolvimento
start_dev_server() {
    log "🚀 Iniciando servidor de desenvolvimento na porta $PORT..."
    
    # Configura variáveis de ambiente para desenvolvimento
    export ENVIRONMENT=development
    export LOG_LEVEL=$LOG_LEVEL
    
    # Inicia servidor com reload automático
    if [[ "$RELOAD" == "true" ]]; then
        uvicorn app.main:app \
            --host 0.0.0.0 \
            --port $PORT \
            --reload \
            --reload-dir app \
            --log-level $LOG_LEVEL \
            --access-log
    else
        uvicorn app.main:app \
            --host 0.0.0.0 \
            --port $PORT \
            --log-level $LOG_LEVEL \
            --access-log
    fi
}

# Função para executar com Docker Compose
start_with_docker() {
    log "🐳 Iniciando com Docker Compose..."
    
    # Verifica se docker-compose está disponível
    if command -v docker-compose &> /dev/null; then
        docker-compose up --build
    elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose up --build
    else
        log "❌ Docker Compose não encontrado"
        exit 1
    fi
}

# Função para mostrar informações úteis
show_info() {
    log "📋 Informações do servidor:"
    echo "  🌐 API: http://localhost:$PORT"
    echo "  📚 Docs: http://localhost:$PORT/docs"
    echo "  🔍 ReDoc: http://localhost:$PORT/redoc"
    echo "  ❤️ Health: http://localhost:$PORT/health"
    echo ""
    echo "  🔧 Modo: desenvolvimento"
    echo "  🔄 Reload: $RELOAD"
    echo "  📊 Log Level: $LOG_LEVEL"
    echo ""
    echo "  ⌨️ Pressione Ctrl+C para parar"
}

# Função principal
main() {
    case "${1:-start}" in
        "install")
            check_dependencies
            install_dependencies
            ;;
        "test")
            run_tests
            ;;
        "lint")
            run_linting
            ;;
        "docker")
            start_with_docker
            ;;
        "start")
            check_dependencies
            run_tests
            run_linting
            show_info
            start_dev_server
            ;;
        "quick")
            # Inicia sem testes e linting para desenvolvimento rápido
            check_dependencies
            show_info
            start_dev_server
            ;;
        *)
            echo "Uso: $0 {install|test|lint|start|quick|docker}"
            echo ""
            echo "Comandos:"
            echo "  install - Instala dependências de desenvolvimento"
            echo "  test    - Executa testes rápidos"
            echo "  lint    - Executa linting e formatação"
            echo "  start   - Inicia servidor de desenvolvimento (padrão)"
            echo "  quick   - Inicia servidor sem testes/linting"
            echo "  docker  - Inicia com Docker Compose"
            echo ""
            echo "Variáveis de ambiente:"
            echo "  PORT=8000        - Porta do servidor"
            echo "  RELOAD=true      - Habilita reload automático"
            echo "  LOG_LEVEL=debug  - Nível de log"
            exit 1
            ;;
    esac
}

# Executa função principal
main "$@"