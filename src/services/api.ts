
import { supabase } from '@/integrations/supabase/client';
import { Team, TeamExecution, SystemHealth } from '@/types/team';

const API_BASE_URL = 'https://ldfzypnyjqoyzqcnkcdy.functions.supabase.co/functions/v1';

// Função auxiliar para fazer requisições autenticadas
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
  // Autenticação
  auth: {
    login: async (email: string, password: string) => {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Erro no login');
      }

      return response.json();
    },

    signup: async (email: string, password: string, name: string) => {
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Erro no cadastro');
      }

      return response.json();
    },

    refresh: async (refreshToken: string) => {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        throw new Error('Erro ao renovar token');
      }

      return response.json();
    },
  },

  // Gerenciamento de equipes
  teams: {
    list: async (): Promise<{ teams: Team[]; total: number }> => {
      return makeAuthenticatedRequest('/teams');
    },

    get: async (teamId: string): Promise<Team> => {
      return makeAuthenticatedRequest(`/teams/${teamId}`);
    },

    create: async (teamData: Partial<Team>): Promise<Team> => {
      return makeAuthenticatedRequest('/teams', {
        method: 'POST',
        body: JSON.stringify(teamData),
      });
    },

    update: async (teamId: string, teamData: Partial<Team>): Promise<Team> => {
      return makeAuthenticatedRequest(`/teams/${teamId}`, {
        method: 'PUT',
        body: JSON.stringify(teamData),
      });
    },

    delete: async (teamId: string): Promise<void> => {
      return makeAuthenticatedRequest(`/teams/${teamId}`, {
        method: 'DELETE',
      });
    },

    execute: async (teamId: string, executionData: { initial_prompt: string }) => {
      return makeAuthenticatedRequest(`/teams/${teamId}/execute`, {
        method: 'POST',
        body: JSON.stringify(executionData),
      });
    },
  },

  // Execuções
  executions: {
    list: async (): Promise<{ executions: TeamExecution[] }> => {
      return makeAuthenticatedRequest('/executions');
    },

    get: async (executionId: string): Promise<TeamExecution> => {
      return makeAuthenticatedRequest(`/executions/${executionId}`);
    },

    cancel: async (executionId: string): Promise<boolean> => {
      await makeAuthenticatedRequest(`/executions/${executionId}/cancel`, {
        method: 'POST',
      });
      return true;
    },
  },

  // Sistema
  system: {
    health: async (): Promise<SystemHealth> => {
      return makeAuthenticatedRequest('/system/health');
    },
  },
};
