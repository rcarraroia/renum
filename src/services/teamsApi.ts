
import { supabase } from '@/integrations/supabase/client';
import { Team, TeamAgent } from '@/types/team';
import { Database } from '@/integrations/supabase/types';

type DbTeam = Database['public']['Tables']['teams']['Row'];
type DbTeamInsert = Database['public']['Tables']['teams']['Insert'];
type DbTeamUpdate = Database['public']['Tables']['teams']['Update'];

// Helper function to convert database team to frontend team
const convertDbTeamToTeam = (dbTeam: DbTeam): Team => {
  const agents = (dbTeam.agents as TeamAgent[]) || [];
  
  return {
    id: dbTeam.id,
    name: dbTeam.name,
    description: dbTeam.description || undefined,
    workflow_type: dbTeam.workflow_type as any,
    user_id: dbTeam.user_id,
    agents,
    status: dbTeam.status as any || 'active',
    agents_count: agents.length,
    created_at: dbTeam.created_at || new Date().toISOString(),
    updated_at: dbTeam.updated_at || new Date().toISOString(),
  };
};

// Helper function to convert frontend team to database team
const convertTeamToDbTeam = (team: Partial<Team>): Partial<DbTeamInsert | DbTeamUpdate> => {
  return {
    name: team.name,
    description: team.description,
    workflow_type: team.workflow_type,
    agents: team.agents as any,
    status: team.status,
  };
};

export const teamsApi = {
  list: async (): Promise<{ teams: Team[]; total: number }> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('teams')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error fetching teams:', error);
      throw new Error(error.message);
    }

    const teams = (data || []).map(convertDbTeamToTeam);
    
    return {
      teams,
      total: teams.length,
    };
  },

  get: async (teamId: string): Promise<Team> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('teams')
      .select('*')
      .eq('id', teamId)
      .single();

    if (error) {
      console.error('Error fetching team:', error);
      throw new Error(error.message);
    }

    if (!data) {
      throw new Error('Equipe não encontrada');
    }

    return convertDbTeamToTeam(data);
  },

  create: async (teamData: Partial<Team>): Promise<Team> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const dbTeamData: DbTeamInsert = {
      ...convertTeamToDbTeam(teamData),
      user_id: user.id,
    };

    const { data, error } = await supabase
      .from('teams')
      .insert(dbTeamData)
      .select()
      .single();

    if (error) {
      console.error('Error creating team:', error);
      throw new Error(error.message);
    }

    return convertDbTeamToTeam(data);
  },

  update: async (teamId: string, teamData: Partial<Team>): Promise<Team> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const dbTeamData: DbTeamUpdate = convertTeamToDbTeam(teamData);

    const { data, error } = await supabase
      .from('teams')
      .update(dbTeamData)
      .eq('id', teamId)
      .select()
      .single();

    if (error) {
      console.error('Error updating team:', error);
      throw new Error(error.message);
    }

    return convertDbTeamToTeam(data);
  },

  delete: async (teamId: string): Promise<void> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { error } = await supabase
      .from('teams')
      .delete()
      .eq('id', teamId);

    if (error) {
      console.error('Error deleting team:', error);
      throw new Error(error.message);
    }
  },

  execute: async (teamId: string, executionData: { initial_prompt: string }) => {
    // Esta é uma implementação mock para agora
    // Na implementação real, isso faria uma chamada para o backend Python
    return {
      execution_id: `exec_${Date.now()}`,
      team_id: teamId,
      status: 'running' as const,
      started_at: new Date().toISOString(),
      progress: {
        completed_agents: 0,
        total_agents: 1,
        current_step: 'Iniciando execução...',
      },
      results: [],
      logs: [
        {
          timestamp: new Date().toISOString(),
          level: 'info' as const,
          message: 'Execução iniciada',
        },
      ],
    };
  },
};
