
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
      connection_type: connection.connection_type as 'oauth' | 'api_key' | 'credentials',
      scopes: Array.isArray(connection.scopes) 
        ? (connection.scopes as string[]).filter((scope): scope is string => typeof scope === 'string')
        : [],
      credentials: connection.credentials as Record<string, any>,
      status: (connection.status as 'active' | 'inactive' | 'expired') || 'active',
      created_at: connection.created_at || new Date().toISOString(),
      updated_at: connection.updated_at || new Date().toISOString(),
      expires_at: connection.expires_at || undefined,
      last_validated: connection.last_validated || undefined,
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
      connection_type: data.connection_type as 'oauth' | 'api_key' | 'credentials',
      scopes: Array.isArray(data.scopes) 
        ? (data.scopes as string[]).filter((scope): scope is string => typeof scope === 'string')
        : [],
      credentials: data.credentials as Record<string, any>,
      status: (data.status as 'active' | 'inactive' | 'expired') || 'active',
      created_at: data.created_at || new Date().toISOString(),
      updated_at: data.updated_at || new Date().toISOString(),
      expires_at: data.expires_at || undefined,
      last_validated: data.last_validated || undefined,
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
      connection_type: data.connection_type as 'oauth' | 'api_key' | 'credentials',
      scopes: Array.isArray(data.scopes) 
        ? (data.scopes as string[]).filter((scope): scope is string => typeof scope === 'string')
        : [],
      credentials: data.credentials as Record<string, any>,
      status: (data.status as 'active' | 'inactive' | 'expired') || 'active',
      created_at: data.created_at || new Date().toISOString(),
      updated_at: data.updated_at || new Date().toISOString(),
      expires_at: data.expires_at || undefined,
      last_validated: data.last_validated || undefined,
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
      connection_type: data.connection_type as 'oauth' | 'api_key' | 'credentials',
      scopes: Array.isArray(data.scopes) 
        ? (data.scopes as string[]).filter((scope): scope is string => typeof scope === 'string')
        : [],
      credentials: data.credentials as Record<string, any>,
      status: (data.status as 'active' | 'inactive' | 'expired') || 'active',
      created_at: data.created_at || new Date().toISOString(),
      updated_at: data.updated_at || new Date().toISOString(),
      expires_at: data.expires_at || undefined,
      last_validated: data.last_validated || undefined,
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
