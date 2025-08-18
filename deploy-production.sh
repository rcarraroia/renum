#!/bin/bash
# Script de deploy de produção para Renum API

set -euo pipefail

# Configurações
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.production.yml"
BACKUP_DIR="./backups"
LOG_FILE="./logs/deploy-$(date +%Y%m%d_%H%M%S).log"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função de logging
log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp] $message${NC}" | tee -a "$LOG_FILE"
}

warn() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp] WARNING: $message${NC}" | tee -a "$LOG_FILE"
}

error() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp] ERROR: $message${NC}" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp] INFO: $message${NC}" | tee -a "$LOG_FILE"
}

# Mostrar uso
show_usage() {
    cat << EOF
Uso: $0 [OPÇÕES]

Opções:
    -h, --help              Mostrar esta ajuda
    -e, --env ENV_FILE      Arquivo de ambiente (padrão: .env.production)
    -b, --backup            Fazer backup antes do deploy
    -r, --rollback          Fazer rollback para versão anterior
    -c, --check             Apenas verificar pré-requisitos
    -f, --force             Forçar deploy sem confirmação
    -v, --verbose           Saída verbosa
    --skip-tests            Pular testes de smoke
    --skip-backup           Pular backup automático
    --dry-run               Simular deploy sem executar

Exemplos:
    $0                      # Deploy normal
    $0 --backup             # Deploy com backup
    $0 --check              # Verificar pré-requisitos
    $0 --rollback           # Rollback para versão anterior

EOF
}

# Verificar pré-requisitos
check_prerequisites() {
    log "Verificando pré-requisitos..."
    
    # Verificar se Docker está instalado e rodando
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker não está instalado"
    fi
    
    if ! docker info >/dev/null 2>&1; then
        error "Docker não está rodando"
    fi
    
    # Verificar se Docker Compose está instalado
    if ! command -v docker-compose >/dev/null 2>&1; then
        error "Docker Compose não está instalado"
    fi
    
    # Verificar se arquivo de compose existe
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Arquivo $COMPOSE_FILE não encontrado"
    fi
    
    # Verificar arquivo de ambiente
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Arquivo de ambiente $ENV_FILE não encontrado"
    fi
    
    # Verificar variáveis obrigatórias
    local required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "JWT_SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" "$ENV_FILE"; then
            error "Variável $var não definida em $ENV_FILE"
        fi
    done
    
    # Verificar espaço em disco
    local available_space=$(df . | awk 'NR==2 {print $4}')
    local required_space=1048576  # 1GB em KB
    
    if [[ $available_space -lt $required_space ]]; then
        error "Espaço em disco insuficiente. Necessário: 1GB, Disponível: $(($available_space/1024))MB"
    fi
    
    # Verificar conectividade de rede
    if ! curl -s --max-time 10 https://registry-1.docker.io/v2/ >/dev/null; then
        warn "Conectividade com Docker Hub pode estar limitada"
    fi
    
    log "✅ Todos os pré-requisitos atendidos"
}

# Fazer backup
create_backup() {
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        info "Pulando backup (--skip-backup especificado)"
        return 0
    fi
    
    log "Criando backup antes do deploy..."
    
    # Verificar se serviços estão rodando
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        # Executar script de backup
        if [[ -f "./scripts/backup.sh" ]]; then
            chmod +x ./scripts/backup.sh
            ./scripts/backup.sh
            log "✅ Backup criado com sucesso"
        else
            warn "Script de backup não encontrado, pulando..."
        fi
    else
        info "Serviços não estão rodando, pulando backup"
    fi
}

# Verificar saúde dos serviços
check_service_health() {
    local service="$1"
    local max_attempts=30
    local attempt=1
    
    log "Verificando saúde do serviço $service..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy\|Up"; then
            log "✅ Serviço $service está saudável"
            return 0
        fi
        
        info "Tentativa $attempt/$max_attempts - Aguardando $service ficar saudável..."
        sleep 10
        ((attempt++))
    done
    
    error "❌ Serviço $service não ficou saudável após $max_attempts tentativas"
}

# Executar testes de smoke
run_smoke_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        info "Pulando testes de smoke (--skip-tests especificado)"
        return 0
    fi
    
    log "Executando testes de smoke..."
    
    local api_url="http://localhost:8000"
    local tests_passed=0
    local tests_total=0
    
    # Teste 1: Health check
    ((tests_total++))
    if curl -sf "$api_url/health" >/dev/null; then
        info "✅ Health check passou"
        ((tests_passed++))
    else
        warn "❌ Health check falhou"
    fi
    
    # Teste 2: API endpoints básicos
    ((tests_total++))
    if curl -sf "$api_url/api/v1/agents" >/dev/null; then
        info "✅ Endpoint /api/v1/agents passou"
        ((tests_passed++))
    else
        warn "❌ Endpoint /api/v1/agents falhou"
    fi
    
    # Teste 3: Documentação da API
    ((tests_total++))
    if curl -sf "$api_url/docs" >/dev/null; then
        info "✅ Documentação da API passou"
        ((tests_passed++))
    else
        warn "❌ Documentação da API falhou"
    fi
    
    # Teste 4: Métricas (se disponível)
    ((tests_total++))
    if curl -sf "$api_url/metrics" >/dev/null; then
        info "✅ Endpoint de métricas passou"
        ((tests_passed++))
    else
        info "ℹ️  Endpoint de métricas não disponível (normal)"
        ((tests_passed++))  # Não é crítico
    fi
    
    log "Testes de smoke: $tests_passed/$tests_total passaram"
    
    if [[ $tests_passed -lt 2 ]]; then
        error "Muitos testes de smoke falharam. Deploy pode ter problemas."
    fi
}

# Deploy principal
perform_deploy() {
    log "=== Iniciando Deploy de Produção ==="
    
    # Verificar se há mudanças
    if docker-compose -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
        info "Configuração do Docker Compose válida"
    else
        error "Configuração do Docker Compose inválida"
    fi
    
    # Pull das imagens mais recentes
    log "Baixando imagens mais recentes..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Deploy com zero downtime
    log "Executando deploy com zero downtime..."
    
    # Estratégia: rolling update
    local services=("api" "nginx" "redis" "postgres")
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps | grep -q "$service"; then
            log "Atualizando serviço $service..."
            
            # Para serviços críticos, usar rolling update
            if [[ "$service" == "api" ]]; then
                # Scale up temporariamente
                docker-compose -f "$COMPOSE_FILE" up -d --scale api=2 --no-recreate api
                sleep 30
                
                # Verificar se nova instância está saudável
                check_service_health api
                
                # Scale down para 1 instância (remove a antiga)
                docker-compose -f "$COMPOSE_FILE" up -d --scale api=1 --no-recreate api
            else
                # Para outros serviços, update normal
                docker-compose -f "$COMPOSE_FILE" up -d --no-deps "$service"
            fi
            
            # Verificar saúde do serviço
            check_service_health "$service"
        else
            log "Iniciando novo serviço $service..."
            docker-compose -f "$COMPOSE_FILE" up -d "$service"
            check_service_health "$service"
        fi
    done
    
    # Aguardar estabilização
    log "Aguardando estabilização dos serviços..."
    sleep 30
    
    # Executar testes de smoke
    run_smoke_tests
    
    # Limpeza de imagens antigas
    log "Limpando imagens antigas..."
    docker image prune -f
    
    log "✅ Deploy concluído com sucesso!"
}

# Rollback para versão anterior
perform_rollback() {
    log "=== Iniciando Rollback ==="
    
    # Verificar se há backup disponível
    local latest_backup=$(find "$BACKUP_DIR" -name "renum_backup_*.tar.gz" -type f | sort -r | head -1)
    
    if [[ -z "$latest_backup" ]]; then
        error "Nenhum backup encontrado para rollback"
    fi
    
    log "Usando backup: $(basename "$latest_backup")"
    
    # Confirmar rollback
    if [[ "$FORCE_DEPLOY" != "true" ]]; then
        echo
        warn "⚠️  ATENÇÃO: Esta operação irá fazer rollback para uma versão anterior!"
        read -p "Deseja continuar? (digite 'yes' para confirmar): " confirm
        if [[ "$confirm" != "yes" ]]; then
            info "Rollback cancelado pelo usuário"
            exit 0
        fi
    fi
    
    # Parar serviços atuais
    log "Parando serviços atuais..."
    docker-compose -f "$COMPOSE_FILE" down
    
    # Executar restore
    if [[ -f "./scripts/restore.sh" ]]; then
        chmod +x ./scripts/restore.sh
        ./scripts/restore.sh --force "$latest_backup"
    else
        error "Script de restore não encontrado"
    fi
    
    # Reiniciar serviços
    log "Reiniciando serviços..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Verificar saúde
    sleep 30
    run_smoke_tests
    
    log "✅ Rollback concluído com sucesso!"
}

# Monitoramento pós-deploy
post_deploy_monitoring() {
    log "Iniciando monitoramento pós-deploy..."
    
    local monitoring_duration=300  # 5 minutos
    local check_interval=30        # 30 segundos
    local checks_count=$((monitoring_duration / check_interval))
    
    for ((i=1; i<=checks_count; i++)); do
        info "Verificação $i/$checks_count..."
        
        # Verificar health checks
        if ! curl -sf http://localhost:8000/health >/dev/null; then
            error "Health check falhou durante monitoramento pós-deploy"
        fi
        
        # Verificar logs por erros
        local error_count=$(docker-compose -f "$COMPOSE_FILE" logs --since=30s api 2>&1 | grep -i error | wc -l)
        if [[ $error_count -gt 5 ]]; then
            warn "Muitos erros detectados nos logs: $error_count"
        fi
        
        # Verificar uso de recursos
        local memory_usage=$(docker stats --no-stream --format "table {{.MemPerc}}" | tail -n +2 | head -1 | sed 's/%//')
        if [[ ${memory_usage%.*} -gt 90 ]]; then
            warn "Alto uso de memória detectado: ${memory_usage}%"
        fi
        
        sleep $check_interval
    done
    
    log "✅ Monitoramento pós-deploy concluído - Sistema estável"
}

# Enviar notificação
send_notification() {
    local status="$1"
    local message="$2"
    
    # Webhook de notificação (se configurado)
    if [[ -n "${DEPLOY_WEBHOOK_URL:-}" ]]; then
        curl -X POST "$DEPLOY_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{
                \"status\": \"$status\",
                \"message\": \"$message\",
                \"timestamp\": \"$(date -Iseconds)\",
                \"environment\": \"production\",
                \"version\": \"$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')\"
            }" \
            --max-time 30 \
            --silent || warn "Falha ao enviar notificação webhook"
    fi
    
    # Slack notification (se configurado)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local emoji="✅"
        if [[ "$status" != "success" ]]; then
            emoji="❌"
        fi
        
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"$emoji Deploy Renum: $message\",
                \"channel\": \"#deployments\",
                \"username\": \"Deploy Bot\"
            }" \
            --max-time 30 \
            --silent || warn "Falha ao enviar notificação Slack"
    fi
}

# Parse argumentos
ENV_FILE=".env.production"
BACKUP_BEFORE_DEPLOY=false
ROLLBACK=false
CHECK_ONLY=false
FORCE_DEPLOY=false
VERBOSE=false
SKIP_TESTS=false
SKIP_BACKUP=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -e|--env)
            ENV_FILE="$2"
            shift 2
            ;;
        -b|--backup)
            BACKUP_BEFORE_DEPLOY=true
            shift
            ;;
        -r|--rollback)
            ROLLBACK=true
            shift
            ;;
        -c|--check)
            CHECK_ONLY=true
            shift
            ;;
        -f|--force)
            FORCE_DEPLOY=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            set -x
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            error "Opção desconhecida: $1"
            ;;
    esac
done

# Criar diretório de logs
mkdir -p "$(dirname "$LOG_FILE")"

# Função principal
main() {
    log "=== Deploy de Produção Renum API ==="
    log "Timestamp: $(date -Iseconds)"
    log "Usuário: $(whoami)"
    log "Diretório: $(pwd)"
    log "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    
    # Verificar pré-requisitos
    check_prerequisites
    
    if [[ "$CHECK_ONLY" == "true" ]]; then
        log "✅ Verificação de pré-requisitos concluída"
        exit 0
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "=== MODO DRY RUN - Nenhuma alteração será feita ==="
        log "Deploy que seria executado:"
        log "  - Arquivo de ambiente: $ENV_FILE"
        log "  - Backup antes do deploy: $BACKUP_BEFORE_DEPLOY"
        log "  - Rollback: $ROLLBACK"
        exit 0
    fi
    
    # Executar operação solicitada
    if [[ "$ROLLBACK" == "true" ]]; then
        perform_rollback
        send_notification "success" "Rollback executado com sucesso"
    else
        # Backup se solicitado
        if [[ "$BACKUP_BEFORE_DEPLOY" == "true" ]]; then
            create_backup
        fi
        
        # Deploy
        perform_deploy
        
        # Monitoramento pós-deploy
        post_deploy_monitoring
        
        send_notification "success" "Deploy executado com sucesso"
    fi
    
    log "=== Operação Concluída ==="
}

# Tratamento de erros
trap 'error "Deploy interrompido por erro na linha $LINENO"' ERR
trap 'send_notification "error" "Deploy falhou"' EXIT

# Executar função principal
main "$@"

# Remover trap de erro se chegou até aqui
trap - EXIT