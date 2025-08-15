
export type WorkflowType = "sequential" | "parallel" | "conditional" | "pipeline";
export type AgentRole = "leader" | "member" | "coordinator";
export type TeamStatus = "active" | "inactive" | "archived";
export type ExecutionStatus = "running" | "completed" | "failed" | "cancelled";

export interface TeamAgentConfig {
  input_source: string;
  conditions: Array<Record<string, any>>;
  timeout_minutes?: number;
}

export interface TeamAgent {
  id: string;
  agent_id: string;
  role: AgentRole;
  order: number;
  config: TeamAgentConfig;
  agent_details?: {
    name: string;
    description: string;
    category?: string;
    capabilities?: string[];
  };
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  workflow_type: WorkflowType;
  user_id: string;
  agents: TeamAgent[];
  status: TeamStatus;
  agents_count: number;
  created_at: string;
  updated_at: string;
}

export interface TeamExecution {
  execution_id: string;
  team_id: string;
  status: ExecutionStatus;
  started_at: string;
  completed_at?: string;
  estimated_completion?: string;
  progress: {
    completed_agents: number;
    total_agents: number;
    current_step: string;
  };
  results: AgentResult[];
  logs: ExecutionLog[];
}

export interface AgentResult {
  agent_id: string;
  status: ExecutionStatus;
  output?: string;
  error_message?: string;
  execution_time_ms?: number;
  started_at: string;
  completed_at?: string;
}

export interface ExecutionLog {
  timestamp: string;
  level: "info" | "warning" | "error";
  message: string;
  agent_id?: string;
}

export interface SystemHealth {
  status: "ok" | "degraded" | "down";
  services: {
    database: { status: string; latency_ms: number };
    suna_backend: { status: string; latency_ms: number };
    websocket: { status: string; connections: number };
  };
}
