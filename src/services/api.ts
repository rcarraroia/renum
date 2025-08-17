
import { supabase } from '@/integrations/supabase/client';
import { Team, TeamExecution, SystemHealth } from '@/types/team';
import { teamsApi } from './teamsApi';
import { agentsApi } from './agentsApi';
import { workflowsApi } from './workflowsApi';
import { connectionsApi } from './connectionsApi';

const API_BASE_URL = 'http://localhost:8000';

// Função auxiliar para fazer requisições autenticadas para o backend Python
const makeAuthenticatedRequest = async (endpoint: string, options: RequestInit = {}) => {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const api = {
  // Autenticação (usando Supabase diretamente)
  auth: {
    login: async (email: string, password: string) => {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        throw new Error(error.message);
      }

      return {
        access_token: data.session?.access_token,
        user: data.user,
      };
    },

    signup: async (email: string, password: string, name: string) => {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            name: name,
          },
        },
      });

      if (error) {
        throw new Error(error.message);
      }

      return {
        access_token: data.session?.access_token,
        user: data.user,
      };
    },

    refresh: async (refreshToken: string) => {
      const { data, error } = await supabase.auth.refreshSession({
        refresh_token: refreshToken,
      });

      if (error) {
        throw new Error(error.message);
      }

      return {
        access_token: data.session?.access_token,
        refresh_token: data.session?.refresh_token,
      };
    },
  },

  // Gerenciamento de equipes (legado - mantido para compatibilidade)
  teams: teamsApi,

  // Novo sistema de agentes
  agents: agentsApi,

  // Sistema de workflows multiagente
  workflows: workflowsApi,

  // Conexões BYOC (Bring Your Own Credentials)
  connections: connectionsApi,

  // Execuções (mock por enquanto, futuramente será integrado com o backend Python)
  executions: {
    list: async (): Promise<{ executions: TeamExecution[] }> => {
      // Mock implementation - futuramente será integrado com o backend
      return { executions: [] };
    },

    get: async (executionId: string): Promise<TeamExecution> => {
      // Mock implementation - futuramente será integrado com o backend
      throw new Error('Execução não encontrada');
    },

    cancel: async (executionId: string): Promise<boolean> => {
      // Mock implementation - futuramente será integrado com o backend
      return true;
    },
  },

  // Sistema (usando backend Python quando disponível)
  system: {
    health: async (): Promise<SystemHealth> => {
      try {
        // Tenta conectar com o backend Python primeiro
        const backendHealth = await makeAuthenticatedRequest('/health');
        return backendHealth;
      } catch (error) {
        // Se o backend não estiver disponível, retorna status do Supabase
        const { data: { user } } = await supabase.auth.getUser();
        
        return {
          status: 'ok' as const,
          services: {
            database: { 
              status: 'ok', 
              latency_ms: 50 
            },
            suna_backend: { 
              status: 'down', 
              latency_ms: 0 
            },
            websocket: { 
              status: 'down', 
              connections: 0 
            },
          },
        };
      }
    },
  },
};
