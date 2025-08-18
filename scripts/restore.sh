#!/bin/bash
# Script de restore para disaster recovery

set -euo pipefail

# Configurações
BACKUP_DIR="/backups"
RESTORE_DIR="/tmp/restore"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Mostrar uso
show_usage() {
    cat << EOF
Uso: $0 [OPÇÕES] BACKUP_FILE

Opções:
    -h, --help              Mostrar esta ajuda
    -l, --list              Listar backups disponíveis
    -i, --info BACKUP_FILE  Mostrar informações do backup
    -c, --check BACKUP_FILE Verificar integridade do backup
    -f, --force             Forçar restore sem confirmação
    --postgres-only         Restaurar apenas PostgreSQL
    --redis-only            Restaurar apenas Redis
    --configs-only          Restaurar apenas configurações
    --dry-run               Simular restore sem executar

Exemplos:
    $0 --list
    $0 --info renum_backup_20241215_143022.tar.gz
    $0 --check renum_backup_20241215_143022.tar.gz
    $0 renum_backup_20241215_143022.tar.gz
    $0 --postgres-only renum_backup_20241215_143022.tar.gz

EOF
}

# Listar backups disponíveis
list_backups() {
    log "Backups disponíveis em $BACKUP_DIR:"
    echo
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        warn "Diretório de backup não encontrado: $BACKUP_DIR"
        return 1
    fi
    
    local backups=($(find "$BACKUP_DIR" -name "renum_backup_*.tar.gz" -type f | sort -r))
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        warn "Nenhum backup encontrado"
        return 1
    fi
    
    printf "%-30s %-20s %-15s %-10s\n" "ARQUIVO" "DATA" "TAMANHO" "CHECKSUM"
    printf "%-30s %-20s %-15s %-10s\n" "$(printf '%*s' 30 '' | tr ' ' '-')" "$(printf '%*s' 20 '' | tr ' ' '-')" "$(printf '%*s' 15 '' | tr ' ' '-')" "$(printf '%*s' 10 '' | tr ' ' '-')"
    
    for backup in "${backups[@]}"; do
        local filename=$(basename "$backup")
        local timestamp=$(echo "$filename" | sed 's/renum_backup_\(.*\)\.tar\.gz/\1/')
        local date_formatted=$(date -d "${timestamp:0:8} ${timestamp:9:2}:${timestamp:11:2}:${timestamp:13:2}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "Invalid date")
        local size=$(du -h "$backup" | cut -f1)
        local checksum_file="${backup}.sha256"
        local checksum_status="❌"
        
        if [[ -f "$checksum_file" ]]; then
            if sha256sum -c "$checksum_file" >/dev/null 2>&1; then
                checksum_status="✅"
            fi
        fi
        
        printf "%-30s %-20s %-15s %-10s\n" "$filename" "$date_formatted" "$size" "$checksum_status"
    done
    
    echo
    log "Total: ${#backups[@]} backup(s) encontrado(s)"
}

# Mostrar informações do backup
show_backup_info() {
    local backup_file="$1"
    
    if [[ ! -f "$backup_file" ]]; then
        error "Arquivo de backup não encontrado: $backup_file"
    fi
    
    log "Informações do backup: $(basename "$backup_file")"
    echo
    
    # Extrair manifesto temporariamente
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir" --wildcards "*/backup_manifest.json" 2>/dev/null || {
        warn "Manifesto não encontrado no backup"
        rm -rf "$temp_dir"
        return 1
    }
    
    local manifest_file=$(find "$temp_dir" -name "backup_manifest.json" -type f | head -1)
    
    if [[ -f "$manifest_file" ]]; then
        # Parse JSON usando jq se disponível, senão usar grep/sed
        if command -v jq >/dev/null 2>&1; then
            echo "📅 Data do Backup: $(jq -r '.backup_date' "$manifest_file")"
            echo "🏷️  Tipo: $(jq -r '.backup_type' "$manifest_file")"
            echo "🌍 Ambiente: $(jq -r '.environment' "$manifest_file")"
            echo "📊 Tamanho: $(jq -r '.backup_size_bytes' "$manifest_file" | numfmt --to=iec)"
            echo "🗄️  Database: $(jq -r '.components.postgres.database' "$manifest_file")"
            echo "🔄 Retenção: $(jq -r '.retention_policy.retention_days' "$manifest_file") dias"
            echo
            echo "📦 Componentes incluídos:"
            jq -r '.components | keys[]' "$manifest_file" | while read component; do
                local backup_file_name=$(jq -r ".components.$component.backup_file" "$manifest_file")
                echo "  - $component: $backup_file_name"
            done
        else
            # Fallback sem jq
            echo "📅 Data do Backup: $(grep -o '"backup_date":"[^"]*' "$manifest_file" | cut -d'"' -f4)"
            echo "🏷️  Tipo: $(grep -o '"backup_type":"[^"]*' "$manifest_file" | cut -d'"' -f4)"
            echo "🌍 Ambiente: $(grep -o '"environment":"[^"]*' "$manifest_file" | cut -d'"' -f4)"
        fi
    else
        warn "Não foi possível ler o manifesto do backup"
    fi
    
    rm -rf "$temp_dir"
    
    # Verificar checksum
    local checksum_file="${backup_file}.sha256"
    if [[ -f "$checksum_file" ]]; then
        echo
        info "Verificando integridade..."
        if sha256sum -c "$checksum_file" >/dev/null 2>&1; then
            echo "✅ Checksum válido"
        else
            echo "❌ Checksum inválido - backup pode estar corrompido!"
        fi
    else
        warn "Arquivo de checksum não encontrado"
    fi
}

# Verificar integridade do backup
check_backup_integrity() {
    local backup_file="$1"
    
    log "Verificando integridade do backup: $(basename "$backup_file")"
    
    # Verificar se arquivo existe
    if [[ ! -f "$backup_file" ]]; then
        error "Arquivo de backup não encontrado: $backup_file"
    fi
    
    # Verificar checksum
    local checksum_file="${backup_file}.sha256"
    if [[ -f "$checksum_file" ]]; then
        info "Verificando checksum SHA256..."
        if sha256sum -c "$checksum_file"; then
            log "✅ Checksum válido"
        else
            error "❌ Checksum inválido - backup corrompido!"
        fi
    else
        warn "Arquivo de checksum não encontrado, pulando verificação"
    fi
    
    # Verificar se é um arquivo tar válido
    info "Verificando estrutura do arquivo tar..."
    if tar -tzf "$backup_file" >/dev/null 2>&1; then
        log "✅ Estrutura tar válida"
    else
        error "❌ Arquivo tar corrompido!"
    fi
    
    # Verificar conteúdo esperado
    info "Verificando conteúdo do backup..."
    local expected_files=("backup_manifest.json")
    local missing_files=()
    
    for file in "${expected_files[@]}"; do
        if ! tar -tzf "$backup_file" | grep -q "$file"; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -eq 0 ]]; then
        log "✅ Todos os arquivos esperados estão presentes"
    else
        warn "⚠️  Arquivos ausentes: ${missing_files[*]}"
    fi
    
    log "Verificação de integridade concluída"
}

# Extrair backup
extract_backup() {
    local backup_file="$1"
    local extract_dir="$2"
    
    log "Extraindo backup para $extract_dir..."
    
    mkdir -p "$extract_dir"
    tar -xzf "$backup_file" -C "$extract_dir" --strip-components=1
    
    if [[ $? -eq 0 ]]; then
        log "✅ Backup extraído com sucesso"
    else
        error "❌ Falha na extração do backup"
    fi
}

# Restaurar PostgreSQL
restore_postgres() {
    local restore_dir="$1"
    local postgres_file=$(find "$restore_dir" -name "postgres_*.sql" -type f | head -1)
    
    if [[ ! -f "$postgres_file" ]]; then
        warn "Arquivo de backup do PostgreSQL não encontrado"
        return 1
    fi
    
    log "Restaurando PostgreSQL de: $(basename "$postgres_file")"
    
    # Verificar variáveis de ambiente
    if [[ -z "${POSTGRES_HOST:-}" ]] || [[ -z "${POSTGRES_USER:-}" ]] || [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
        error "Variáveis de ambiente do PostgreSQL não definidas"
    fi
    
    # Confirmar restore
    if [[ "${FORCE_RESTORE:-}" != "true" ]]; then
        echo
        warn "⚠️  ATENÇÃO: Esta operação irá SOBRESCREVER o banco de dados atual!"
        read -p "Deseja continuar? (digite 'yes' para confirmar): " confirm
        if [[ "$confirm" != "yes" ]]; then
            info "Restore cancelado pelo usuário"
            return 1
        fi
    fi
    
    # Parar aplicação temporariamente
    info "Parando aplicação..."
    docker-compose -f docker-compose.production.yml stop api || warn "Falha ao parar API"
    
    # Fazer backup do banco atual
    local current_backup="/tmp/current_db_backup_$(date +%s).sql"
    info "Fazendo backup do banco atual..."
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --format=custom \
        --file="$current_backup" || warn "Falha no backup do banco atual"
    
    # Restaurar banco
    info "Restaurando banco de dados..."
    PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
        -h "$POSTGRES_HOST" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --clean \
        --if-exists \
        --verbose \
        "$postgres_file"
    
    if [[ $? -eq 0 ]]; then
        log "✅ PostgreSQL restaurado com sucesso"
        
        # Reiniciar aplicação
        info "Reiniciando aplicação..."
        docker-compose -f docker-compose.production.yml start api
        
        # Remover backup temporário
        rm -f "$current_backup"
    else
        error "❌ Falha na restauração do PostgreSQL"
    fi
}

# Restaurar Redis
restore_redis() {
    local restore_dir="$1"
    local redis_file=$(find "$restore_dir" -name "redis_*.rdb" -type f | head -1)
    
    if [[ ! -f "$redis_file" ]]; then
        warn "Arquivo de backup do Redis não encontrado"
        return 1
    fi
    
    log "Restaurando Redis de: $(basename "$redis_file")"
    
    # Parar Redis
    info "Parando Redis..."
    docker-compose -f docker-compose.production.yml stop redis
    
    # Copiar arquivo RDB
    info "Copiando arquivo RDB..."
    docker cp "$redis_file" renum-redis:/data/dump.rdb
    
    # Reiniciar Redis
    info "Reiniciando Redis..."
    docker-compose -f docker-compose.production.yml start redis
    
    # Verificar se Redis está funcionando
    sleep 5
    if redis-cli -h redis ping | grep -q PONG; then
        log "✅ Redis restaurado com sucesso"
    else
        error "❌ Falha na restauração do Redis"
    fi
}

# Restaurar configurações
restore_configs() {
    local restore_dir="$1"
    local config_file=$(find "$restore_dir" -name "configs_*.tar.gz" -type f | head -1)
    
    if [[ ! -f "$config_file" ]]; then
        warn "Arquivo de backup das configurações não encontrado"
        return 1
    fi
    
    log "Restaurando configurações de: $(basename "$config_file")"
    
    # Fazer backup das configurações atuais
    local current_config_backup="/tmp/current_configs_backup_$(date +%s).tar.gz"
    info "Fazendo backup das configurações atuais..."
    tar -czf "$current_config_backup" /etc/nginx/ /app/.env 2>/dev/null || warn "Falha no backup das configurações atuais"
    
    # Extrair configurações
    info "Extraindo configurações..."
    tar -xzf "$config_file" -C /
    
    if [[ $? -eq 0 ]]; then
        log "✅ Configurações restauradas com sucesso"
        
        # Recarregar configurações
        info "Recarregando serviços..."
        docker-compose -f docker-compose.production.yml restart nginx || warn "Falha ao reiniciar Nginx"
        
        # Remover backup temporário
        rm -f "$current_config_backup"
    else
        error "❌ Falha na restauração das configurações"
    fi
}

# Função principal de restore
perform_restore() {
    local backup_file="$1"
    local restore_type="${2:-full}"
    
    log "=== Iniciando Restore do Renum ==="
    log "Backup: $(basename "$backup_file")"
    log "Tipo: $restore_type"
    
    # Verificar integridade
    check_backup_integrity "$backup_file"
    
    # Extrair backup
    local restore_dir="$RESTORE_DIR/$(date +%s)"
    extract_backup "$backup_file" "$restore_dir"
    
    # Executar restore baseado no tipo
    case "$restore_type" in
        "postgres-only")
            restore_postgres "$restore_dir"
            ;;
        "redis-only")
            restore_redis "$restore_dir"
            ;;
        "configs-only")
            restore_configs "$restore_dir"
            ;;
        "full")
            restore_postgres "$restore_dir"
            restore_redis "$restore_dir"
            restore_configs "$restore_dir"
            ;;
        *)
            error "Tipo de restore inválido: $restore_type"
            ;;
    esac
    
    # Limpeza
    rm -rf "$restore_dir"
    
    log "=== Restore Concluído ==="
}

# Parse argumentos
BACKUP_FILE=""
RESTORE_TYPE="full"
FORCE_RESTORE=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -i|--info)
            if [[ -n "${2:-}" ]]; then
                show_backup_info "$2"
                exit 0
            else
                error "Arquivo de backup não especificado para --info"
            fi
            ;;
        -c|--check)
            if [[ -n "${2:-}" ]]; then
                check_backup_integrity "$2"
                exit 0
            else
                error "Arquivo de backup não especificado para --check"
            fi
            ;;
        -f|--force)
            FORCE_RESTORE=true
            shift
            ;;
        --postgres-only)
            RESTORE_TYPE="postgres-only"
            shift
            ;;
        --redis-only)
            RESTORE_TYPE="redis-only"
            shift
            ;;
        --configs-only)
            RESTORE_TYPE="configs-only"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -*)
            error "Opção desconhecida: $1"
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            else
                error "Múltiplos arquivos de backup especificados"
            fi
            shift
            ;;
    esac
done

# Verificar se arquivo de backup foi especificado
if [[ -z "$BACKUP_FILE" ]]; then
    error "Arquivo de backup não especificado. Use --help para ver opções."
fi

# Resolver caminho completo do backup
if [[ ! -f "$BACKUP_FILE" ]]; then
    # Tentar encontrar no diretório de backup
    local full_path="$BACKUP_DIR/$BACKUP_FILE"
    if [[ -f "$full_path" ]]; then
        BACKUP_FILE="$full_path"
    else
        error "Arquivo de backup não encontrado: $BACKUP_FILE"
    fi
fi

# Executar restore
if [[ "$DRY_RUN" == "true" ]]; then
    info "=== MODO DRY RUN - Nenhuma alteração será feita ==="
    show_backup_info "$BACKUP_FILE"
    info "Tipo de restore que seria executado: $RESTORE_TYPE"
else
    perform_restore "$BACKUP_FILE" "$RESTORE_TYPE"
fi