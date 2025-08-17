
import { supabase } from '@/integrations/supabase/client';
import { Agent, CreateAgentRequest } from '@/types/agents';

export const agentsApi = {
  // Listar agentes ativos (público)
  list: async (): Promise<{ agents: Agent[]; total: number }> => {
    const { data, error } = await supabase
      .from('agents_registry')
      .select('*')
      .eq('status', 'active')
      .order('name', { ascending: true });

    if (error) {
      console.error('Error fetching agents:', error);
      throw new Error(error.message);
    }

    const agents = (data || []).map(agent => ({
      ...agent,
      capabilities: Array.isArray(agent.capabilities) ? agent.capabilities : [],
      dependencies: Array.isArray(agent.dependencies) ? agent.dependencies : [],
    }));

    return {
      agents,
      total: agents.length,
    };
  },

  // Obter agente específico
  get: async (agentId: string): Promise<Agent> => {
    const { data, error } = await supabase
      .from('agents_registry')
      .select('*')
      .eq('agent_id', agentId)
      .eq('status', 'active')
      .single();

    if (error) {
      console.error('Error fetching agent:', error);
      throw new Error(error.message);
    }

    if (!data) {
      throw new Error('Agente não encontrado');
    }

    return {
      ...data,
      capabilities: Array.isArray(data.capabilities) ? data.capabilities : [],
      dependencies: Array.isArray(data.dependencies) ? data.dependencies : [],
    };
  },

  // Criar novo agente (apenas usuários autenticados)
  create: async (agentData: CreateAgentRequest): Promise<Agent> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('agents_registry')
      .insert({
        ...agentData,
        created_by: user.id,
      })
      .select()
      .single();

    if (error) {
      console.error('Error creating agent:', error);
      throw new Error(error.message);
    }

    return {
      ...data,
      capabilities: Array.isArray(data.capabilities) ? data.capabilities : [],
      dependencies: Array.isArray(data.dependencies) ? data.dependencies : [],
    };
  },

  // Listar agentes criados pelo usuário
  listOwn: async (): Promise<{ agents: Agent[]; total: number }> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('agents_registry')
      .select('*')
      .eq('created_by', user.id)
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error fetching own agents:', error);
      throw new Error(error.message);
    }

    const agents = (data || []).map(agent => ({
      ...agent,
      capabilities: Array.isArray(agent.capabilities) ? agent.capabilities : [],
      dependencies: Array.isArray(agent.dependencies) ? agent.dependencies : [],
    }));

    return {
      agents,
      total: agents.length,
    };
  },
};
