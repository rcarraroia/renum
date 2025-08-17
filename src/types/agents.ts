
export interface Agent {
  id: string;
  agent_id: string;
  version: string;
  name: string;
  description?: string;
  capabilities: string[];
  input_schema: Record<string, any>;
  policy: Record<string, any>;
  dependencies: string[];
  status: 'active' | 'inactive' | 'deprecated';
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAgentRequest {
  agent_id: string;
  name: string;
  description?: string;
  capabilities: string[];
  input_schema: Record<string, any>;
  policy?: Record<string, any>;
  dependencies?: string[];
}

export interface TenantConnection {
  id: string;
  tenant_id: string;
  service_name: string;
  connection_type: 'oauth' | 'api_key' | 'credentials';
  credentials: Record<string, any>;
  scopes: string[];
  status: 'active' | 'inactive' | 'expired';
  expires_at?: string;
  last_validated?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateConnectionRequest {
  service_name: string;
  connection_type: 'oauth' | 'api_key' | 'credentials';
  credentials: Record<string, any>;
  scopes?: string[];
  expires_at?: string;
}
