<div align="center">

# Renum Suna Core - Plataforma de Agentes de IA

![Renum Screenshot](frontend/public/banner.png)

**Renum Suna Core** é uma plataforma avançada de agentes de IA que combina o poder do Suna (assistente de IA generalista open source) com funcionalidades especializadas para equipes de agentes coordenados. A plataforma permite criar, gerenciar e executar equipes de agentes especializados que trabalham em conjunto para resolver tarefas complexas através de conversação natural.

A plataforma oferece automação de navegador para extrair dados da web, gerenciamento de arquivos para criação e edição de documentos, web crawling e busca estendida, execução de linha de comando, deploy de websites, integração com APIs diversas, e o diferencial único de **equipes de agentes coordenados** que podem trabalhar em estratégias sequenciais, paralelas, condicionais ou em pipeline.

[![License](https://img.shields.io/badge/License-Apache--2.0-blue)](./license)

</div>

## Índice

- [Arquitetura do Projeto](#arquitetura-do-projeto)
  - [Backend Suna (Core)](#backend-suna-core)
  - [Backend Renum (Equipes de Agentes)](#backend-renum-equipes-de-agentes)
  - [Frontend Suna](#frontend-suna)
  - [Frontend Renum](#frontend-renum)
  - [Painel Administrativo Renum](#painel-administrativo-renum)
  - [Agent Docker](#agent-docker)
  - [Banco de Dados Supabase](#banco-de-dados-supabase)
- [Estrutura de Diretórios](#estrutura-de-diretorios)
- [Casos de Uso](#casos-de-uso)
- [Configuração e Instalação](#configuracao-e-instalacao)
- [Desenvolvimento Local](#desenvolvimento-local)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Contribuição](#contribuicao)
- [Licença](#licenca)

## Arquitetura do Projeto

![Architecture Diagram](docs/images/diagram.png)

A plataforma Renum Suna Core é composta por múltiplos componentes especializados:

### Backend Suna (Core)
**Localização**: `backend/`

Serviço Python/FastAPI que fornece a base do sistema Suna original, incluindo:
- Endpoints REST para comunicação com clientes
- Gerenciamento de threads e conversações
- Integração com LLMs (Anthropic, OpenAI, etc.) via LiteLLM
- Automação de navegador e ferramentas básicas
- Sistema de execução de agentes individuais

### Backend Renum (Equipes de Agentes)
**Localização**: `renum-backend/`

Sistema especializado para gerenciamento de equipes de agentes coordenados:
- ✅ Criação e gerenciamento de equipes de agentes especializados
- ✅ Execução com múltiplas estratégias (sequencial, paralelo, condicional, pipeline)
- ✅ Monitoramento em tempo real das execuções
- ✅ Contexto compartilhado entre agentes da mesma equipe
- ✅ Sistema de mensagens inter-agentes
- ✅ Gerenciamento seguro de API keys por equipe
- ✅ Integração completa com Suna Core

**API**: `http://localhost:9000/api/v1` | **Docs**: `http://localhost:9000/docs`

### Frontend Suna
**Localização**: `src/` (raiz do projeto)

Interface original do Suna construída com Vite + React:
- **Status**: Mantido para compatibilidade e atualizações futuras
- **Uso**: Não é utilizado ativamente no projeto Renum
- **Importância**: **NÃO PODE SER DELETADO** - necessário para:
  - Receber atualizações do projeto Suna upstream
  - Processo de reinstalação do sistema
  - Manter compatibilidade com ferramentas de desenvolvimento

### Frontend Renum
**Localização**: `renum-frontend/`

Interface visual principal do projeto Renum construída com Next.js 15:
- Interface de usuário responsiva com chat avançado
- Dashboard para gerenciamento de equipes de agentes
- Monitoramento em tempo real das execuções
- Configuração de estratégias de execução
- Gerenciamento de contexto compartilhado
- Integração com ambos os backends

### Painel Administrativo Renum
**Localização**: `renum-admin/`

Sistema administrativo independente construído com Next.js:
- **Independência**: Funciona completamente separado dos outros componentes
- Gerenciamento avançado de usuários e permissões
- Configurações globais do sistema
- Monitoramento de recursos e performance
- Relatórios e analytics detalhados
- Configuração de integrações e API keys

### Agent Docker

Ambiente de execução isolado para cada agente:
- Automação de navegador com Playwright
- Interpretador de código seguro
- Acesso controlado ao sistema de arquivos
- Integração com ferramentas especializadas
- Recursos de segurança avançados

### Banco de Dados Supabase

Gerencia persistência de dados com:
- Autenticação e gerenciamento de usuários
- Histórico de conversações e execuções
- Armazenamento de arquivos e contextos
- Estado dos agentes e equipes
- Analytics e métricas em tempo real
- Subscrições em tempo real para monitoramento

## Estrutura de Diretórios

```
renum-suna-core/
├── backend/                    # Backend Suna (Core) - Python/FastAPI
├── renum-backend/             # Backend Renum (Equipes de Agentes) - Python/FastAPI
├── src/                       # Frontend Suna (Vite + React) - Mantido para compatibilidade
├── renum-frontend/            # Frontend Renum (Next.js 15) - Interface principal
├── renum-admin/               # Painel Administrativo (Next.js) - Sistema independente
├── docs/                      # Documentação completa
├── supabase/                  # Configurações do banco de dados
├── docker-compose.yaml        # Orquestração de containers
├── setup.py                   # Wizard de configuração
└── start.py                   # Script de gerenciamento de serviços
```

### Componentes por Tecnologia

**Python/FastAPI Backends:**
- `backend/` - Suna Core (porta 8000)
- `renum-backend/` - Renum Teams (porta 9000)

**Next.js Frontends:**
- `renum-frontend/` - Interface principal do usuário
- `renum-admin/` - Painel administrativo independente

**React/Vite Frontend:**
- `src/` - Frontend Suna original (mantido para compatibilidade)

## Casos de Uso

1. **Competitor Analysis** ([Watch](https://www.suna.so/share/5ee791ac-e19c-4986-a61c-6d0659d0e5bc)) - _"Analyze the market for my next company in the healthcare industry, located in the UK. Give me the major players, their market size, strengths, and weaknesses, and add their website URLs. Once done, generate a PDF report."_

2. **VC List** ([Watch](https://www.suna.so/share/804d20a3-cf1c-4adb-83bb-0e77cc6adeac)) - _"Give me the list of the most important VC Funds in the United States based on Assets Under Management. Give me website URLs, and if possible an email to reach them out."_

3. **Looking for Candidates** ([Watch](https://www.suna.so/share/3ae581b0-2db8-4c63-b324-3b8d29762e74)) - _"Go on LinkedIn, and find me 10 profiles available - they are not working right now - for a junior software engineer position, who are located in Munich, Germany. They should have at least one bachelor's degree in Computer Science or anything related to it, and 1-year of experience in any field/role."_

4. **Planning Company Trip** ([Watch](https://www.suna.so/share/725e64a0-f1e2-4bb6-8a1f-703c2833fd72)) - _"Generate me a route plan for my company. We should go to California. We'll be in 8 people. Compose the trip from the departure (Paris, France) to the activities we can do considering that the trip will be 7 days long - departure on the 21st of Apr 2025. Check the weather forecast and temperature for the upcoming days, and based on that, you can plan our activities (outdoor vs indoor)."_

5. **Working on Excel** ([Watch](https://www.suna.so/share/128f23a4-51cd-42a6-97a0-0b458b32010e)) - _"My company asked me to set up an Excel spreadsheet with all the information about Italian lottery games (Lotto, 10eLotto, and Million Day). Based on that, generate and send me a spreadsheet with all the basic information (public ones)."_

6. **Automate Event Speaker Prospecting** ([Watch](https://www.suna.so/share/7a7592ea-ed44-4c69-bcb5-5f9bb88c188c)) - _"Find 20 AI ethics speakers from Europe who've spoken at conferences in the past year. Scrapes conference sites, cross-references LinkedIn and YouTube, and outputs contact info + talk summaries."_

7. **Summarize and Cross-Reference Scientific Papers** ([Watch](https://www.suna.so/share/c2081b3c-786e-4e7c-9bf4-46e9b23bb662)) - _"Research and compare scientific papers talking about Alcohol effects on our bodies during the last 5 years. Generate a report about the most important scientific papers talking about the topic I wrote before."_

8. **Research + First Contact Draft** ([Watch](https://www.suna.so/share/6b6296a6-8683-49e5-9ad0-a32952d12c44)) - _"Research my potential customers (B2B) on LinkedIn. They should be in the clean tech industry. Find their websites and their email addresses. After that, based on the company profile, generate a personalized first contact email where I present my company which is offering consulting services to cleantech companies to maximize their profits and reduce their costs."_

9. **SEO Analysis** ([Watch](https://www.suna.so/share/43491cb0-cd6c-45f0-880c-66ddc8c4b842)) - _"Based on my website suna.so, generate an SEO report analysis, find top-ranking pages by keyword clusters, and identify topics I'm missing."_

10. **Generate a Personal Trip** ([Watch](https://www.suna.so/share/37b31907-8349-4f63-b0e5-27ca597ed02a)) - _"Generate a personal trip to London, with departure from Bangkok on the 1st of May. The trip will last 10 days. Find an accommodation in the center of London, with a rating on Google reviews of at least 4.5. Find me interesting outdoor activities to do during the journey. Generate a detailed itinerary plan."_

11. **Recently Funded Startups** ([Watch](https://www.suna.so/share/8b2a897e-985a-4d5e-867b-15239274f764)) - _"Go on Crunchbase, Dealroom, and TechCrunch, filter by Series A funding rounds in the SaaS Finance Space, and build a report with company data, founders, and contact info for outbound sales."_

12. **Scrape Forum Discussions** ([Watch](https://www.suna.so/share/7d7a5d93-a20d-48b0-82cc-e9a876e9fd04)) - _"I need to find the best beauty centers in Rome, but I want to find them by using open forums that speak about this topic. Go on Google, and scrape the forums by looking for beauty center discussions located in Rome. Then generate a list of 5 beauty centers with the best comments about them."_

## Configuração e Instalação

A plataforma Renum Suna Core pode ser hospedada em sua própria infraestrutura usando nosso wizard de configuração abrangente.

### Início Rápido com Docker (Recomendado)

1. **Clone o repositório**:

```bash
git clone <YOUR_REPOSITORY_URL>
cd renum-suna-core
```

2. **Execute o wizard de configuração**:

```bash
python setup.py
```

O wizard irá guiá-lo através de 14 etapas com salvamento de progresso, permitindo retomar se interrompido.

3. **Inicie ou pare os containers**:

```bash
python start.py
```

### Configuração Manual dos Componentes

#### Backend Suna (Core)
```bash
cd backend
cp .env.example .env
# Configure suas variáveis de ambiente
uv run api.py
```

#### Backend Renum (Equipes)
```bash
cd renum-backend
cp .env.example .env
# Configure suas variáveis de ambiente
docker-compose up -d
# ou instalação local:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/apply_team_tables.py
python scripts/run_server.py
```

#### Frontend Renum (Interface Principal)
```bash
cd renum-frontend
cp .env.development .env.local
# Configure suas variáveis de ambiente
npm install
npm run dev
```

#### Painel Administrativo Renum
```bash
cd renum-admin
cp .env.example .env.local
# Configure suas variáveis de ambiente
npm install
npm run dev
```

### Processo de Configuração Inclui:

- Configuração de projeto Supabase para banco de dados e autenticação
- Configuração do Redis para cache e gerenciamento de sessões
- Configuração do Daytona para execução segura de agentes
- Integração com provedores de LLM (Anthropic, OpenAI, OpenRouter, etc.)
- Configuração de busca web e scraping (Tavily, Firecrawl)
- Configuração do QStash para processamento de jobs em background
- Configuração de webhooks para tarefas automatizadas
- Integrações opcionais (RapidAPI, Smithery para agentes customizados)

## Desenvolvimento Local

### Pré-requisitos
- Python 3.11+
- Node.js 18+
- Docker e Docker Compose
- Conta Supabase
- API keys dos provedores de LLM

### Executando Todos os Serviços

**Opção 1: Docker Compose (Recomendado)**
```bash
docker-compose up -d
```

**Opção 2: Desenvolvimento Manual**
```bash
# Serviços de infraestrutura
docker-compose up redis rabbitmq -d

# Backend Suna (terminal 1)
cd backend
uv run api.py

# Backend Renum (terminal 2)
cd renum-backend
python scripts/run_server.py

# Worker de background (terminal 3)
cd backend
uv run dramatiq run_agent_background

# Frontend Renum (terminal 4)
cd renum-frontend
npm run dev

# Painel Admin (terminal 5)
cd renum-admin
npm run dev
```

### URLs de Desenvolvimento
- **Frontend Renum**: http://localhost:3000
- **Painel Admin**: http://localhost:3001
- **Backend Suna**: http://localhost:8000
- **Backend Renum**: http://localhost:9000
- **Docs API Suna**: http://localhost:8000/docs
- **Docs API Renum**: http://localhost:9000/docs

### Testes

```bash
# Testes do Backend Suna
cd backend
uv run pytest

# Testes do Backend Renum
cd renum-backend
python -m pytest

# Testes do Frontend Renum
cd renum-frontend
npm run test

# Testes do Painel Admin
cd renum-admin
npm run test
```

## Tecnologias Utilizadas

### Backend Technologies
- **Python 3.11+** - Linguagem principal dos backends
- **FastAPI** - Framework web para APIs REST
- **Supabase (PostgreSQL)** - Banco de dados e autenticação
- **Redis** - Cache e gerenciamento de sessões
- **RabbitMQ** - Fila de mensagens
- **Dramatiq** - Processamento em background
- **LiteLLM** - Integração com múltiplos provedores de LLM
- **Daytona** - Execução segura de agentes
- **QStash** - Processamento de jobs
- **Sentry** - Monitoramento e logging

### Frontend Technologies
- **Next.js 15** - Framework React para produção
- **React 18** - Biblioteca de interface de usuário
- **TypeScript** - Tipagem estática
- **TailwindCSS 4** - Framework de estilos
- **Zustand** - Gerenciamento de estado
- **React Query** - Gerenciamento de estado servidor
- **Radix UI** - Componentes de interface
- **React Hook Form** - Gerenciamento de formulários
- **Zod** - Validação de esquemas
- **React PDF** - Manipulação de PDFs

### Infrastructure & Tools
- **Docker** - Containerização
- **Playwright** - Automação de navegador
- **Firecrawl** - Web scraping
- **Tavily** - Capacidades de busca
- **uv** - Gerenciador de pacotes Python
- **npm** - Gerenciador de pacotes JavaScript

### LLM Providers Suportados
- **Anthropic** (Claude)
- **OpenAI** (GPT-4, GPT-3.5)
- **Groq** - Inferência rápida
- **OpenRouter** - Múltiplos modelos
- **AWS Bedrock** - Modelos empresariais

## Documentação Adicional

### Renum Backend
- 📖 [Resumo da Implementação](./renum-backend/IMPLEMENTATION_SUMMARY.md)
- 🚀 [Instruções de Execução](./renum-backend/EXECUTION_INSTRUCTIONS.md)
- 📚 [Documentação da API](./renum-backend/API_DOCUMENTATION.md)
- ✅ [Conclusão](./renum-backend/CONCLUSAO.md)

### Documentação Geral
- 🏗️ [Guia de Auto-Hospedagem](./docs/SELF-HOSTING.md)
- 🔧 [Guia de Configuração](./docs/CONFIGURATION_GUIDE.md)
- 🚀 [Guia de Deploy](./docs/DEPLOYMENT_GUIDE.md)
- 🐛 [Guia de Troubleshooting](./docs/TROUBLESHOOTING_GUIDE.md)

## Contribuição

Contribuições da comunidade são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Principais Contribuidores

### Projeto Suna Original
- [Adam Cohen Hillel](https://x.com/adamcohenhillel)
- [Dat-lequoc](https://x.com/datlqqq)
- [Marko Kraemer](https://twitter.com/markokraemer)

### Extensões Renum
- Equipe de desenvolvimento Renum

## Licença

Este projeto é licenciado sob a Apache License, Version 2.0. Veja [LICENSE](./LICENSE) para o texto completo da licença.

---

**Renum Suna Core** - Transformando a forma como equipes de agentes de IA trabalham juntas para resolver problemas complexos.
