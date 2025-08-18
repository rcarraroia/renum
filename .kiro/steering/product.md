# Visão Geral do Produto

O Renum é uma plataforma de orquestração multi-agente que permite que equipes de agentes de IA especializados trabalhem juntos em tarefas complexas. A plataforma fornece gerenciamento de fluxo de trabalho, monitoramento em tempo real e capacidades de integração perfeitas.

## Funcionalidades Principais

- **Gerenciamento de Equipes de Agentes**: Criar e configurar equipes de agentes de IA com diferentes especializações
- **Orquestração de Fluxos**: Suporte para estratégias de execução sequencial, paralela, pipeline e condicional
- **Monitoramento em Tempo Real**: Atualizações ao vivo baseadas em WebSocket e rastreamento de execução
- **Sistema de Integrações**: Framework extensível de integração para serviços externos e APIs
- **Autenticação e Segurança**: Autenticação baseada em JWT com controle de acesso baseado em funções

## Usuários-Alvo

- Desenvolvedores construindo aplicações alimentadas por IA
- Organizações automatizando fluxos de trabalho complexos
- Equipes que requerem colaboração coordenada de agentes de IA

## Propostas de Valor Principais

- Coordenação multi-agente simplificada
- Visibilidade de execução em tempo real
- Ecossistema de integração extensível
- Escalabilidade pronta para produção

## Arquitetura do Sistema

- **Backend**: FastAPI com Arquitetura Limpa (Python 3.11+)
- **Frontend**: React 18 + TypeScript + Vite (futuro)
- **Banco de Dados**: Supabase (PostgreSQL) com Row Level Security
- **Autenticação**: Supabase Auth + tokens JWT
- **Tempo Real**: Conexões WebSocket
- **Integrações Externas**: Suna Backend para execução de agentes