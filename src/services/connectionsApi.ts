
import { supabase } from '@/integrations/supabase/client';
import { TenantConnection, CreateConnectionRequest } from '@/types/agents';

export const connectionsApi = {
  // Listar conexões do usuário
  list: async (): Promise<{ connections: TenantConnection[]; total: number }> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('tenant_connections')
      .select('*')
      .eq('tenant_id', user.id)
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error fetching connections:', error);
      throw new Error(error.message);
    }

    const connections = (data || []).map(connection => ({
      ...connection,
      scopes: Array.isArray(connection.scopes) ? connection.scopes : [],
    }));

    return {
      connections,
      total: connections.length,
    };
  },

  // Obter conexão específica
  get: async (connectionId: string): Promise<TenantConnection> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('tenant_connections')
      .select('*')
      .eq('id', connectionId)
      .eq('tenant_id', user.id)
      .single();

    if (error) {
      console.error('Error fetching connection:', error);
      throw new Error(error.message);
    }

    if (!data) {
      throw new Error('Conexão não encontrada');
    }

    return {
      ...data,
      scopes: Array.isArray(data.scopes) ? data.scopes : [],
    };
  },

  // Criar nova conexão
  create: async (connectionData: CreateConnectionRequest): Promise<TenantConnection> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('tenant_connections')
      .insert({
        ...connectionData,
        tenant_id: user.id,
      })
      .select()
      .single();

    if (error) {
      console.error('Error creating connection:', error);
      throw new Error(error.message);
    }

    return {
      ...data,
      scopes: Array.isArray(data.scopes) ? data.scopes : [],
    };
  },

  // Atualizar conexão
  update: async (connectionId: string, connectionData: Partial<CreateConnectionRequest>): Promise<TenantConnection> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('tenant_connections')
      .update(connectionData)
      .eq('id', connectionId)
      .eq('tenant_id', user.id)
      .select()
      .single();

    if (error) {
      console.error('Error updating connection:', error);
      throw new Error(error.message);
    }

    return {
      ...data,
      scopes: Array.isArray(data.scopes) ? data.scopes : [],
    };
  },

  // Deletar conexão
  delete: async (connectionId: string): Promise<void> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { error } = await supabase
      .from('tenant_connections')
      .delete()
      .eq('id', connectionId)
      .eq('tenant_id', user.id);

    if (error) {
      console.error('Error deleting connection:', error);
      throw new Error(error.message);
    }
  },
};
