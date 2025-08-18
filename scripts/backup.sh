#!/bin/bash
# Script de backup automatizado para produção

set -euo pipefail

# Configurações
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Verificar variáveis de ambiente
check_env() {
    local required_vars=("POSTGRES_HOST" "POSTGRES_DB" "POSTGRES_USER" "POSTGRES_PASSWORD")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Variável de ambiente $var não definida"
        fi
    done
}

# Criar diretório de backup
create_backup_dir() {
    local backup_path="$BACKUP_DIR/$TIMESTAMP"
    mkdir -p "$backup_path"
    echo "$backup_path"
}

# Backup do PostgreSQL
backup_postgres() {
    local backup_path="$1"
    local db_backup_file="$backup_path/postgres_${POSTGRES_DB}_${TIMESTAMP}.sql"
    
    log "Iniciando backup do PostgreSQL..."
    
    # Backup completo
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="$db_backup_file"
    
    if [[ $? -eq 0 ]]; then
        log "Backup do PostgreSQL concluído: $db_backup_file"
        
        # Verificar integridade do backup
        PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
            --list "$db_backup_file" > /dev/null
        
        if [[ $? -eq 0 ]]; then
            log "Verificação de integridade do backup PostgreSQL: OK"
        else
            error "Backup do PostgreSQL corrompido!"
        fi
    else
        error "Falha no backup do PostgreSQL"
    fi
}

# Backup do Redis
backup_redis() {
    local backup_path="$1"
    local redis_backup_file="$backup_path/redis_${TIMESTAMP}.rdb"
    
    log "Iniciando backup do Redis..."
    
    # Forçar save do Redis
    redis-cli -h redis BGSAVE
    
    # Aguardar conclusão do BGSAVE
    while [[ $(redis-cli -h redis LASTSAVE) -eq $(redis-cli -h redis LASTSAVE) ]]; do
        sleep 1
    done
    
    # Copiar arquivo RDB
    docker cp renum-redis:/data/dump.rdb "$redis_backup_file"
    
    if [[ $? -eq 0 ]]; then
        log "Backup do Redis concluído: $redis_backup_file"
    else
        error "Falha no backup do Redis"
    fi
}

# Backup dos logs
backup_logs() {
    local backup_path="$1"
    local logs_backup_file="$backup_path/logs_${TIMESTAMP}.tar.gz"
    
    log "Iniciando backup dos logs..."
    
    tar -czf "$logs_backup_file" -C /var/log renum/ nginx/ 2>/dev/null || true
    
    if [[ -f "$logs_backup_file" ]]; then
        log "Backup dos logs concluído: $logs_backup_file"
    else
        warn "Nenhum log encontrado para backup"
    fi
}

# Backup das configurações
backup_configs() {
    local backup_path="$1"
    local config_backup_file="$backup_path/configs_${TIMESTAMP}.tar.gz"
    
    log "Iniciando backup das configurações..."
    
    # Lista de arquivos de configuração importantes
    local config_files=(
        "/app/.env"
        "/etc/nginx/nginx.conf"
        "/etc/nginx/conf.d/"
        "/etc/prometheus/prometheus.yml"
        "/etc/grafana/grafana.ini"
    )
    
    # Criar arquivo temporário com lista de arquivos existentes
    local temp_list=$(mktemp)
    for file in "${config_files[@]}"; do
        if [[ -e "$file" ]]; then
            echo "$file" >> "$temp_list"
        fi
    done
    
    if [[ -s "$temp_list" ]]; then
        tar -czf "$config_backup_file" -T "$temp_list" 2>/dev/null || true
        log "Backup das configurações concluído: $config_backup_file"
    else
        warn "Nenhuma configuração encontrada para backup"
    fi
    
    rm -f "$temp_list"
}

# Backup dos dados de aplicação
backup_app_data() {
    local backup_path="$1"
    local data_backup_file="$backup_path/app_data_${TIMESTAMP}.tar.gz"
    
    log "Iniciando backup dos dados da aplicação..."
    
    if [[ -d "/app/data" ]]; then
        tar -czf "$data_backup_file" -C /app data/
        log "Backup dos dados da aplicação concluído: $data_backup_file"
    else
        warn "Diretório de dados da aplicação não encontrado"
    fi
}

# Criar manifesto do backup
create_manifest() {
    local backup_path="$1"
    local manifest_file="$backup_path/backup_manifest.json"
    
    log "Criando manifesto do backup..."
    
    cat > "$manifest_file" << EOF
{
    "backup_timestamp": "$TIMESTAMP",
    "backup_date": "$(date -Iseconds)",
    "backup_type": "full",
    "environment": "production",
    "components": {
        "postgres": {
            "database": "$POSTGRES_DB",
            "host": "$POSTGRES_HOST",
            "backup_file": "postgres_${POSTGRES_DB}_${TIMESTAMP}.sql"
        },
        "redis": {
            "backup_file": "redis_${TIMESTAMP}.rdb"
        },
        "logs": {
            "backup_file": "logs_${TIMESTAMP}.tar.gz"
        },
        "configs": {
            "backup_file": "configs_${TIMESTAMP}.tar.gz"
        },
        "app_data": {
            "backup_file": "app_data_${TIMESTAMP}.tar.gz"
        }
    },
    "backup_size_bytes": $(du -sb "$backup_path" | cut -f1),
    "retention_policy": {
        "retention_days": $RETENTION_DAYS,
        "delete_after": "$(date -d "+$RETENTION_DAYS days" -Iseconds)"
    }
}
EOF
    
    log "Manifesto criado: $manifest_file"
}

# Comprimir backup completo
compress_backup() {
    local backup_path="$1"
    local compressed_file="$BACKUP_DIR/renum_backup_${TIMESTAMP}.tar.gz"
    
    log "Comprimindo backup completo..."
    
    tar -czf "$compressed_file" -C "$BACKUP_DIR" "$(basename "$backup_path")"
    
    if [[ $? -eq 0 ]]; then
        log "Backup comprimido: $compressed_file"
        
        # Remover diretório temporário
        rm -rf "$backup_path"
        
        # Calcular checksum
        local checksum=$(sha256sum "$compressed_file" | cut -d' ' -f1)
        echo "$checksum" > "${compressed_file}.sha256"
        
        log "Checksum SHA256: $checksum"
    else
        error "Falha na compressão do backup"
    fi
}

# Limpeza de backups antigos
cleanup_old_backups() {
    log "Limpando backups antigos (> $RETENTION_DAYS dias)..."
    
    find "$BACKUP_DIR" -name "renum_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "renum_backup_*.tar.gz.sha256" -mtime +$RETENTION_DAYS -delete
    
    local deleted_count=$(find "$BACKUP_DIR" -name "renum_backup_*.tar.gz" -mtime +$RETENTION_DAYS | wc -l)
    
    if [[ $deleted_count -gt 0 ]]; then
        log "Removidos $deleted_count backups antigos"
    else
        log "Nenhum backup antigo para remover"
    fi
}

# Enviar notificação (webhook, email, etc.)
send_notification() {
    local status="$1"
    local message="$2"
    
    # Webhook de notificação (se configurado)
    if [[ -n "${BACKUP_WEBHOOK_URL:-}" ]]; then
        curl -X POST "$BACKUP_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{
                \"status\": \"$status\",
                \"message\": \"$message\",
                \"timestamp\": \"$(date -Iseconds)\",
                \"environment\": \"production\",
                \"backup_id\": \"$TIMESTAMP\"
            }" \
            --max-time 30 \
            --silent || warn "Falha ao enviar notificação webhook"
    fi
}

# Função principal
main() {
    log "=== Iniciando Backup Automatizado do Renum ==="
    log "Timestamp: $TIMESTAMP"
    
    # Verificar pré-requisitos
    check_env
    
    # Criar diretório de backup
    local backup_path
    backup_path=$(create_backup_dir)
    
    # Executar backups
    backup_postgres "$backup_path"
    backup_redis "$backup_path"
    backup_logs "$backup_path"
    backup_configs "$backup_path"
    backup_app_data "$backup_path"
    
    # Criar manifesto
    create_manifest "$backup_path"
    
    # Comprimir backup
    compress_backup "$backup_path"
    
    # Limpeza
    cleanup_old_backups
    
    log "=== Backup Concluído com Sucesso ==="
    
    # Notificação de sucesso
    send_notification "success" "Backup do Renum concluído com sucesso em $TIMESTAMP"
}

# Tratamento de erros
trap 'error "Backup interrompido por erro"' ERR
trap 'send_notification "error" "Backup do Renum falhou em $TIMESTAMP"' EXIT

# Executar backup
main "$@"

# Remover trap de erro se chegou até aqui
trap - EXIT