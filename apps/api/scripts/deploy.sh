#!/bin/bash

# Script de deployment para Renum API
set -e

# Configurações
IMAGE_NAME="renum-api"
CONTAINER_NAME="renum-api-container"
PORT="8000"
ENVIRONMENT="${ENVIRONMENT:-production}"

echo "🚀 Iniciando deployment da Renum API..."

# Função para logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Função para verificar se o Docker está rodando
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log "❌ Docker não está rodando. Por favor, inicie o Docker."
        exit 1
    fi
    log "✅ Docker está rodando"
}

# Função para build da imagem
build_image() {
    log "🔨 Construindo imagem Docker..."
    docker build -t $IMAGE_NAME:latest .
    log "✅ Imagem construída com sucesso"
}

# Função para parar container existente
stop_existing() {
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        log "🛑 Parando container existente..."
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
        log "✅ Container existente removido"
    fi
}

# Função para executar testes
run_tests() {
    log "🧪 Executando testes..."
    
    # Executa testes básicos
    python test_simple.py
    python test_endpoints.py
    
    log "✅ Testes básicos passaram"
}

# Função para iniciar novo container
start_container() {
    log "🚀 Iniciando novo container..."
    
    docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $PORT:8000 \
        -e ENVIRONMENT=$ENVIRONMENT \
        $IMAGE_NAME:latest
    
    log "✅ Container iniciado na porta $PORT"
}

# Função para verificar saúde do serviço
health_check() {
    log "🏥 Verificando saúde do serviço..."
    
    # Aguarda o serviço iniciar
    sleep 10
    
    # Tenta fazer health check por até 60 segundos
    for i in {1..12}; do
        if curl -f http://localhost:$PORT/health > /dev/null 2>&1; then
            log "✅ Serviço está saudável"
            return 0
        fi
        log "⏳ Aguardando serviço iniciar... (tentativa $i/12)"
        sleep 5
    done
    
    log "❌ Serviço não respondeu ao health check"
    return 1
}

# Função para mostrar logs
show_logs() {
    log "📋 Últimos logs do container:"
    docker logs --tail 20 $CONTAINER_NAME
}

# Função para limpeza em caso de erro
cleanup_on_error() {
    log "🧹 Limpando recursos devido a erro..."
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
}

# Função principal
main() {
    # Verifica argumentos
    case "${1:-deploy}" in
        "build")
            check_docker
            build_image
            ;;
        "test")
            run_tests
            ;;
        "deploy")
            check_docker
            run_tests
            build_image
            stop_existing
            start_container
            
            if health_check; then
                log "🎉 Deployment concluído com sucesso!"
                show_logs
            else
                cleanup_on_error
                exit 1
            fi
            ;;
        "stop")
            stop_existing
            log "✅ Serviço parado"
            ;;
        "logs")
            show_logs
            ;;
        "status")
            if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
                log "✅ Serviço está rodando"
                docker ps -f name=$CONTAINER_NAME
            else
                log "❌ Serviço não está rodando"
                exit 1
            fi
            ;;
        *)
            echo "Uso: $0 {build|test|deploy|stop|logs|status}"
            echo ""
            echo "Comandos:"
            echo "  build   - Constrói apenas a imagem Docker"
            echo "  test    - Executa apenas os testes"
            echo "  deploy  - Executa deployment completo (padrão)"
            echo "  stop    - Para o serviço"
            echo "  logs    - Mostra logs do serviço"
            echo "  status  - Verifica status do serviço"
            exit 1
            ;;
    esac
}

# Executa função principal
main "$@"