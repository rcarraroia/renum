# Suíte de Testes Abrangente - Renum API

Esta é a suíte completa de testes para a API do Renum, cobrindo todos os aspectos do sistema desde testes unitários até testes de performance e segurança.

## 📋 Estrutura dos Testes

### Tipos de Testes

- **🔧 Testes Unitários**: Testam componentes individuais isoladamente
- **🔗 Testes de Integração**: Testam interação entre componentes
- **⚡ Testes de Performance**: Testam performance, carga e escalabilidade
- **🔒 Testes de Segurança**: Testam segurança, autenticação e autorização
- **📚 Testes de Documentação**: Validam documentação da API e exemplos

### Arquivos de Teste

```
tests/
├── conftest.py                      # Configurações e fixtures compartilhadas
├── test_analytics.py               # Testes do sistema de analytics
├── test_api_documentation.py       # Testes da documentação da API
├── test_execution_engine.py        # Testes do motor de execução
├── test_fallback.py               # Testes do sistema de fallback
├── test_integration_complete.py    # Testes de integração end-to-end
├── test_integration_webhooks.py    # Testes de integração de webhooks
├── test_performance.py            # Testes de performance e carga
├── test_security_comprehensive.py  # Testes de segurança abrangentes
├── test_security_middleware.py     # Testes de middleware de segurança
└── test_sub_agents.py             # Testes dos sub-agentes
```

## 🚀 Executando os Testes

### Pré-requisitos

```bash
# Instalar dependências de teste
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist

# Dependências opcionais para qualidade de código
pip install black ruff mypy
```

### Comandos Básicos

```bash
# Executar todos os testes
python run_tests.py

# Executar apenas testes unitários
python run_tests.py --type unit

# Executar testes com cobertura
python run_tests.py --coverage

# Executar testes em paralelo
python run_tests.py --parallel 4

# Executar testes rápidos (pular testes lentos)
python run_tests.py --fast

# Executar arquivo específico
python run_tests.py --file test_analytics.py

# Executar função específica
python run_tests.py --file test_analytics.py --function test_metrics_collection
```

### Usando pytest Diretamente

```bash
# Executar todos os testes
pytest

# Executar por marcadores
pytest -m unit          # Apenas testes unitários
pytest -m integration   # Apenas testes de integração
pytest -m performance   # Apenas testes de performance
pytest -m security      # Apenas testes de segurança

# Executar com cobertura
pytest --cov=app --cov-report=html

# Executar em paralelo
pytest -n 4

# Executar com saída verbosa
pytest -v -s

# Executar arquivo específico
pytest tests/test_analytics.py

# Executar função específica
pytest tests/test_analytics.py::TestAnalyticsService::test_metrics_collection
```

## 📊 Cobertura de Testes

### Metas de Cobertura

- **Cobertura Geral**: ≥ 80%
- **Serviços Críticos**: ≥ 90%
- **Endpoints da API**: ≥ 85%
- **Middleware de Segurança**: ≥ 95%

### Relatórios de Cobertura

Após executar testes com `--coverage`:

- **HTML**: `htmlcov/index.html` - Relatório interativo
- **Terminal**: Resumo na saída do comando
- **XML**: `coverage.xml` - Para integração CI/CD

## 🧪 Categorias de Teste

### 1. Testes Unitários (`test_*.py`)

Testam componentes individuais:

- **Serviços**: Lógica de negócio isolada
- **Repositórios**: Acesso a dados
- **Utilitários**: Funções auxiliares
- **Validações**: Schemas e validadores

```bash
# Executar apenas testes unitários
pytest -m unit
```

### 2. Testes de Integração (`test_integration_*.py`)

Testam interação entre componentes:

- **End-to-End**: Fluxos completos de workflow
- **Webhooks**: Integração de webhooks
- **APIs Externas**: Comunicação com serviços externos
- **Banco de Dados**: Operações de persistência

```bash
# Executar testes de integração
pytest -m integration
```

### 3. Testes de Performance (`test_performance.py`)

Testam performance e escalabilidade:

- **Baseline**: Tempos de resposta base
- **Carga**: Comportamento sob carga
- **Stress**: Limites do sistema
- **Memória**: Uso de recursos

```bash
# Executar testes de performance
pytest -m performance --durations=0
```

### 4. Testes de Segurança (`test_security_*.py`)

Testam aspectos de segurança:

- **Autenticação**: JWT, tokens, sessões
- **Autorização**: RBAC, isolamento de usuários
- **Validação**: Prevenção de injeções
- **Rate Limiting**: Proteção contra abuso

```bash
# Executar testes de segurança
pytest -m security
```

## 🔧 Configuração e Fixtures

### Fixtures Principais (`conftest.py`)

- **`mock_user`**: Usuário mock para testes
- **`mock_auth_headers`**: Headers de autenticação
- **`sample_workflow_definition`**: Workflow de exemplo
- **`mock_credentials`**: Credenciais mock para agentes
- **`mock_database`**: Conexão de banco mock
- **`performance_timer`**: Timer para testes de performance

### Variáveis de Ambiente

```bash
# Configuradas automaticamente para testes
TESTING=true
DATABASE_URL=sqlite:///test.db
DEBUG=false
LOG_LEVEL=WARNING
```

## 📈 Métricas e Monitoramento

### Métricas Coletadas

- **Tempo de Execução**: Por teste e suíte
- **Taxa de Sucesso**: Percentual de testes passando
- **Cobertura**: Linhas de código testadas
- **Performance**: Tempos de resposta e throughput

### Relatórios Gerados

1. **Cobertura HTML**: Visualização interativa
2. **JUnit XML**: Para integração CI/CD
3. **Duração**: Testes mais lentos
4. **Falhas**: Detalhes de testes falhando

## 🚨 Troubleshooting

### Problemas Comuns

#### Testes Falhando

```bash
# Executar com mais detalhes
pytest -v -s --tb=long

# Executar apenas testes falhando
pytest --lf

# Parar no primeiro erro
pytest -x
```

#### Performance Lenta

```bash
# Pular testes lentos
pytest -m "not slow"

# Executar em paralelo
pytest -n auto

# Mostrar testes mais lentos
pytest --durations=10
```

#### Problemas de Dependências

```bash
# Verificar instalação
pip list | grep pytest

# Reinstalar dependências
pip install -r requirements-test.txt
```

### Logs e Debug

```bash
# Habilitar logs durante testes
pytest -s --log-cli-level=DEBUG

# Capturar stdout/stderr
pytest -s --capture=no
```

## 🔄 Integração CI/CD

### GitHub Actions

```yaml
- name: Run Tests
  run: |
    python run_tests.py --coverage --parallel 4
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: python run_tests.py --fast
        language: system
        pass_filenames: false
```

## 📝 Contribuindo

### Adicionando Novos Testes

1. **Escolha a categoria apropriada**
2. **Use fixtures existentes quando possível**
3. **Adicione marcadores apropriados**
4. **Documente casos de teste complexos**
5. **Mantenha testes independentes**

### Padrões de Nomenclatura

```python
# Classes de teste
class TestServiceName:
    
# Métodos de teste
def test_method_name_scenario(self):
    
# Fixtures
@pytest.fixture
def mock_service_name():
```

### Exemplo de Teste

```python
import pytest
from unittest.mock import patch

class TestAnalyticsService:
    """Testes do serviço de analytics"""
    
    @pytest.mark.unit
    async def test_track_execution_success(self, mock_user):
        """Teste de rastreamento de execução bem-sucedido"""
        # Arrange
        execution_data = {
            'execution_id': 'exec-123',
            'user_id': mock_user['user_id'],
            'status': 'completed'
        }
        
        # Act
        with patch('app.services.analytics_service.database') as mock_db:
            result = await analytics_service.track_execution(execution_data)
        
        # Assert
        assert result is not None
        mock_db.execute.assert_called_once()
```

## 📚 Recursos Adicionais

- [Documentação do pytest](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Guia de Testes FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)

---

**Última atualização**: Dezembro 2024  
**Versão da Suíte**: 1.0.0  
**Cobertura Atual**: 85%+