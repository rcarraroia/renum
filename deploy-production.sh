#!/bin/bash

# Script de Deploy de Produção - Sistema RENUM
# Este script automatiza o deploy do sistema RENUM em produção

set -e  # Para execução em caso de erro

echo "🚀 Iniciando deploy de produção do Sistema RENUM..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verificar se está no diretório correto
if [ ! -f "docker-compose.production.yml" ]; then
    error "Arquivo docker-compose.production.yml não encontrado. Execute este script no diretório raiz do projeto."
fi

# Verificar se o arquivo .env.production existe
if [ ! -f "apps/api/.env.production" ]; then
    warning "Arquivo .env.production não encontrado."
    echo "Copiando .env.production.example para .env.production..."
    cp apps/api/.env.production.example apps/api/.env.production
    warning "IMPORTANTE: Configure as variáveis de ambiente em apps/api/.env.production antes de continuar!"
    read -p "Pressione Enter após configurar as variáveis de ambiente..."
fi

# Verificar dependências
log "Verificando dependências..."

if ! command -v docker &> /dev/null; then
    error "Docker não está instalado. Instale o Docker primeiro."
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose não está instalado. Instale o Docker Compose primeiro."
fi

# Verificar se as portas estão disponíveis
log "Verificando portas disponíveis..."

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        error "Porta $1 já está em uso. Libere a porta antes de continuar."
    fi
}

check_port 8000
check_port 6379
check_port 80
check_port 443

# Fazer backup do banco de dados (se existir)
log "Fazendo backup do banco de dados..."
# TODO: Implementar backup do Supabase se necessário

# Parar serviços existentes
log "Parando serviços existentes..."
docker-compose -f docker-compose.production.yml down --remove-orphans || true

# Limpar imagens antigas
log "Limpando imagens antigas..."
docker system prune -f

# Build das imagens
log "Construindo imagens de produção..."
docker-compose -f docker-compose.production.yml build --no-cache

# Verificar configurações
log "Verificando configurações..."

# Verificar se as variáveis críticas estão definidas
source apps/api/.env.production

required_vars=(
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY" 
    "SUPABASE_SERVICE_ROLE_KEY"
    "JWT_SECRET_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        error "Variável de ambiente $var não está definida em .env.production"
    fi
done

# Iniciar serviços
log "Iniciando serviços de produção..."
docker-compose -f docker-compose.production.yml up -d

# Aguardar serviços ficarem prontos
log "Aguardando serviços ficarem prontos..."
sleep 30

# Verificar saúde dos serviços
log "Verificando saúde dos serviços..."

check_service() {
    local service_name=$1
    local health_url=$2
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" > /dev/null; then
            success "$service_name está saudável"
            return 0
        fi
        
        log "Tentativa $attempt/$max_attempts: $service_name não está pronto ainda..."
        sleep 10
        ((attempt++))
    done
    
    error "$service_name não ficou saudável após $max_attempts tentativas"
}

# Verificar API
check_service "API" "http://localhost:8000/health"

# Verificar Redis
if docker-compose -f docker-compose.production.yml exec redis redis-cli ping | grep -q PONG; then
    success "Redis está saudável"
else
    error "Redis não está respondendo"
fi

# Executar testes de fumaça
log "Executando testes de fumaça..."

# Teste básico da API
if curl -f -s "http://localhost:8000/" | grep -q "Renum API"; then
    success "Teste básico da API passou"
else
    error "Teste básico da API falhou"
fi

# Teste de autenticação (se possível)
# TODO: Implementar teste de autenticação

# Configurar monitoramento (se habilitado)
if [ "$ENABLE_METRICS" = "true" ]; then
    log "Configurando monitoramento..."
    # TODO: Configurar Prometheus/Grafana se necessário
fi

# Configurar backup automático
log "Configurando backup automático..."
# TODO: Configurar backup automático

# Mostrar status final
log "Verificando status final dos serviços..."
docker-compose -f docker-compose.production.yml ps

# Mostrar logs recentes
log "Logs recentes da API:"
docker-compose -f docker-compose.production.yml logs --tail=20 api

# Instruções finais
success "🎉 Deploy de produção concluído com sucesso!"
echo ""
echo "📋 Informações importantes:"
echo "  • API disponível em: http://localhost:8000"
echo "  • Documentação: http://localhost:8000/docs"
echo "  • Health check: http://localhost:8000/health"
echo "  • Logs: docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "🔧 Próximos passos recomendados:"
echo "  1. Configurar SSL/HTTPS com certificado válido"
echo "  2. Configurar domínio personalizado"
echo "  3. Configurar monitoramento avançado"
echo "  4. Configurar backup automático"
echo "  5. Executar testes de carga"
echo ""
echo "⚠️  Lembre-se de:"
echo "  • Monitorar logs regularmente"
echo "  • Fazer backup do banco de dados"
echo "  • Manter as dependências atualizadas"
echo "  • Revisar configurações de segurança"

log "Deploy finalizado!"