# 🚀 Renum API - Guia de Produção

Este guia contém todas as informações necessárias para deploy e operação do Renum API em ambiente de produção.

## 📋 Pré-requisitos

### Sistema Operacional
- Ubuntu 20.04+ ou CentOS 8+
- Mínimo 4GB RAM, 2 CPU cores
- 50GB de espaço em disco disponível

### Software Necessário
- Docker 24.0+
- Docker Compose 2.0+
- Git
- curl
- Certificados SSL (para HTTPS)

## 🔧 Configuração Inicial

### 1. Clonar Repositório
```bash
git clone https://github.com/your-org/renum.git
cd renum
```

### 2. Configurar Variáveis de Ambiente
```bash
# Copiar arquivo de exemplo
cp apps/api/.env.production.example apps/api/.env.production

# Editar configurações
nano apps/api/.env.production
```

### 3. Configurar SSL (Opcional)
```bash
# Criar diretório SSL
mkdir -p ssl

# Copiar certificados
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem
```

## 🚀 Deploy

### Deploy Automático
```bash
# Deploy completo com backup
./deploy-production.sh --backup

# Deploy apenas com verificações
./deploy-production.sh --check

# Deploy forçado (sem confirmação)
./deploy-production.sh --force
```

### Deploy Manual
```bash
# Subir todos os serviços
docker-compose -f docker-compose.production.yml up -d

# Verificar status
docker-compose -f docker-compose.production.yml ps

# Ver logs
docker-compose -f docker-compose.production.yml logs -f api
```

## 📊 Monitoramento

### Dashboards Disponíveis

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Grafana | http://localhost:3000 | Dashboards e visualizações |
| Prometheus | http://localhost:9090 | Métricas e alertas |
| Jaeger | http://localhost:16686 | Tracing distribuído |
| API Docs | http://localhost:8000/docs | Documentação da API |

### Credenciais Padrão
- **Grafana**: admin / (definido em GRAFANA_PASSWORD)
- **Prometheus**: Sem autenticação
- **Jaeger**: Sem autenticação

### Métricas Principais

#### API Health
```promql
# Status da API
up{job="renum-api"}

# Taxa de requisições
rate(http_requests_total{job="renum-api"}[5m])

# Tempo de resposta (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="renum-api"}[5m]))
```

#### Workflows
```promql
# Execuções de workflow
rate(renum_workflow_executions_total[5m])

# Taxa de falha de workflows
rate(renum_workflow_executions_total{status="failed"}[5m]) / rate(renum_workflow_executions_total[5m])
```

#### Agentes
```promql
# Performance dos agentes
rate(renum_agent_executions_total[5m])

# Tempo de execução dos agentes
renum_agent_execution_duration_seconds
```

## 🔒 Segurança

### Configurações de Segurança
- Rate limiting habilitado por padrão
- CORS configurado para domínios específicos
- Headers de segurança aplicados via Nginx
- Autenticação JWT obrigatória

### Certificados SSL
```bash
# Renovar certificados (Let's Encrypt)
certbot renew --nginx

# Verificar expiração
openssl x509 -in ssl/cert.pem -text -noout | grep "Not After"
```

### Firewall
```bash
# Portas necessárias
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH
```

## 💾 Backup e Restore

### Backup Automático
```bash
# Backup manual
./scripts/backup.sh

# Configurar cron para backup diário
0 2 * * * /opt/renum/scripts/backup.sh
```

### Restore
```bash
# Listar backups disponíveis
./scripts/restore.sh --list

# Verificar integridade do backup
./scripts/restore.sh --check backup_file.tar.gz

# Restore completo
./scripts/restore.sh backup_file.tar.gz

# Restore apenas banco de dados
./scripts/restore.sh --postgres-only backup_file.tar.gz
```

## 🔧 Manutenção

### Logs
```bash
# Ver logs da API
docker-compose -f docker-compose.production.yml logs -f api

# Ver logs do Nginx
docker-compose -f docker-compose.production.yml logs -f nginx

# Ver logs de todos os serviços
docker-compose -f docker-compose.production.yml logs -f
```

### Atualizações
```bash
# Atualizar código
git pull origin main

# Rebuild e deploy
./deploy-production.sh --backup

# Rollback se necessário
./deploy-production.sh --rollback
```

### Limpeza
```bash
# Limpar imagens antigas
docker image prune -f

# Limpar volumes não utilizados
docker volume prune -f

# Limpar logs antigos
find ./logs -name "*.log" -mtime +30 -delete
```

## 🚨 Troubleshooting

### Problemas Comuns

#### API não responde
```bash
# Verificar status dos containers
docker-compose -f docker-compose.production.yml ps

# Verificar logs
docker-compose -f docker-compose.production.yml logs api

# Reiniciar API
docker-compose -f docker-compose.production.yml restart api
```

#### Alto uso de memória
```bash
# Verificar uso de recursos
docker stats

# Verificar logs por memory leaks
docker-compose -f docker-compose.production.yml logs api | grep -i memory
```

#### Banco de dados lento
```bash
# Verificar conexões ativas
docker exec renum-postgres psql -U renum_user -d renum -c "SELECT count(*) FROM pg_stat_activity;"

# Verificar queries lentas
docker exec renum-postgres psql -U renum_user -d renum -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### Health Checks

#### Verificação Manual
```bash
# API Health
curl -f http://localhost:8000/health

# Nginx Status
curl -f http://localhost/health

# Prometheus Targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'
```

#### Alertas Críticos
- API Down por mais de 1 minuto
- Taxa de erro > 10% por 5 minutos
- Uso de memória > 85%
- Espaço em disco < 10%

## 📞 Suporte

### Contatos de Emergência
- **DevOps**: devops@renum.com
- **Desenvolvimento**: dev@renum.com
- **Slack**: #renum-alerts

### Documentação Adicional
- [API Documentation](http://localhost:8000/docs)
- [Grafana Dashboards](http://localhost:3000)
- [Runbook Interno](./docs/runbook.md)

## 📈 Escalabilidade

### Scaling Horizontal
```bash
# Escalar API (múltiplas instâncias)
docker-compose -f docker-compose.production.yml up -d --scale api=3

# Load balancer automático via Nginx
```

### Otimizações de Performance
- Connection pooling habilitado
- Cache Redis configurado
- Compressão gzip ativa
- CDN para assets estáticos (recomendado)

### Limites de Recursos
```yaml
# Configurado em docker-compose.production.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

---

**Última atualização**: Dezembro 2024  
**Versão**: 1.0.0  
**Ambiente**: Produção