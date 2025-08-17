
export interface Workflow {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  workflow_data: Record<string, any>;
  agents_used: string[];
  status: 'draft' | 'active' | 'archived';
  created_at: string;
  updated_at: string;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  workflow_data: Record<string, any>;
  agents_used?: string[];
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  user_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  input_data: Record<string, any>;
  results: any[];
  execution_logs: any[];
  error_message?: string;
  started_at: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ExecutionLog {
  id: string;
  run_id: string;
  agent_id?: string;
  step_number?: number;
  log_level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  metadata: Record<string, any>;
  timestamp: string;
}

export interface StartWorkflowRequest {
  workflow_id: string;
  input_data: Record<string, any>;
}

export interface IntegrationRequest {
  id: string;
  user_id: string;
  service_name: string;
  description?: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'approved' | 'rejected' | 'completed';
  votes: number;
  created_at: string;
  updated_at: string;
}

export interface CreateIntegrationRequest {
  service_name: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
}

export interface BillingMetric {
  id: string;
  user_id: string;
  run_id?: string;
  metric_type: 'workflow_execution' | 'agent_call' | 'api_request';
  agent_id?: string;
  quantity: number;
  cost_cents: number;
  metadata: Record<string, any>;
  created_at: string;
}
