
import { Team, TeamExecution, SystemHealth, WorkflowType, TeamStatus, ExecutionStatus } from "@/types/team";

// Mock data
const mockTeams: Team[] = [
  {
    id: "team-1",
    name: "Marketing Team",
    description: "Team for marketing automation and content creation",
    workflow_type: "sequential" as WorkflowType,
    user_id: "user-1",
    agents: [
      {
        id: "agent-1",
        agent_id: "suna-agent-1",
        role: "leader",
        order: 1,
        config: {
          input_source: "initial_prompt",
          conditions: []
        },
        agent_details: {
          name: "Content Creator",
          description: "Creates marketing content",
          category: "marketing"
        }
      },
      {
        id: "agent-2", 
        agent_id: "suna-agent-2",
        role: "member",
        order: 2,
        config: {
          input_source: "previous_output",
          conditions: []
        },
        agent_details: {
          name: "SEO Optimizer",
          description: "Optimizes content for search engines",
          category: "marketing"
        }
      }
    ],
    status: "active" as TeamStatus,
    agents_count: 2,
    created_at: "2025-08-15T10:00:00Z",
    updated_at: "2025-08-15T10:00:00Z"
  },
  {
    id: "team-2",
    name: "Data Analysis Team",
    description: "Team for data processing and analysis",
    workflow_type: "parallel" as WorkflowType,
    user_id: "user-1",
    agents: [
      {
        id: "agent-3",
        agent_id: "suna-agent-3",
        role: "coordinator",
        order: 1,
        config: {
          input_source: "data_feed",
          conditions: []
        },
        agent_details: {
          name: "Data Processor",
          description: "Processes raw data",
          category: "analytics"
        }
      }
    ],
    status: "active" as TeamStatus,
    agents_count: 1,
    created_at: "2025-08-14T15:30:00Z",
    updated_at: "2025-08-14T15:30:00Z"
  }
];

const mockExecutions: TeamExecution[] = [
  {
    execution_id: "exec-1",
    team_id: "team-1",
    status: "running" as ExecutionStatus,
    started_at: "2025-08-15T11:00:00Z",
    estimated_completion: "2025-08-15T11:30:00Z",
    progress: {
      completed_agents: 1,
      total_agents: 2,
      current_step: "Agent 2 processing"
    },
    results: [
      {
        agent_id: "agent-1",
        status: "completed" as ExecutionStatus,
        output: "Generated marketing copy for product launch",
        execution_time_ms: 15000,
        started_at: "2025-08-15T11:00:00Z",
        completed_at: "2025-08-15T11:15:00Z"
      }
    ],
    logs: [
      {
        timestamp: "2025-08-15T11:00:00Z",
        level: "info",
        message: "Execution started",
        agent_id: undefined
      },
      {
        timestamp: "2025-08-15T11:15:00Z",
        level: "info", 
        message: "Agent 1 completed successfully",
        agent_id: "agent-1"
      }
    ]
  }
];

const mockSystemHealth: SystemHealth = {
  status: "ok",
  services: {
    database: { status: "healthy", latency_ms: 12 },
    suna_backend: { status: "healthy", latency_ms: 45 },
    websocket: { status: "healthy", connections: 23 }
  }
};

// Mock API functions
export const mockTeamApi = {
  // Teams
  getTeams: async (): Promise<{ teams: Team[]; pagination: any }> => {
    await new Promise(resolve => setTimeout(resolve, 500)); // Simulate API delay
    return {
      teams: mockTeams,
      pagination: {
        page: 1,
        limit: 10,
        total: mockTeams.length,
        pages: 1
      }
    };
  },

  getTeam: async (teamId: string): Promise<Team | null> => {
    await new Promise(resolve => setTimeout(resolve, 300));
    return mockTeams.find(team => team.id === teamId) || null;
  },

  createTeam: async (teamData: Partial<Team>): Promise<Team> => {
    await new Promise(resolve => setTimeout(resolve, 800));
    const newTeam: Team = {
      id: `team-${Date.now()}`,
      name: teamData.name || "New Team",
      description: teamData.description,
      workflow_type: teamData.workflow_type || "sequential",
      user_id: "user-1",
      agents: teamData.agents || [],
      status: "active",
      agents_count: teamData.agents?.length || 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    mockTeams.push(newTeam);
    return newTeam;
  },

  updateTeam: async (teamId: string, teamData: Partial<Team>): Promise<Team | null> => {
    await new Promise(resolve => setTimeout(resolve, 600));
    const teamIndex = mockTeams.findIndex(team => team.id === teamId);
    if (teamIndex === -1) return null;
    
    mockTeams[teamIndex] = {
      ...mockTeams[teamIndex],
      ...teamData,
      updated_at: new Date().toISOString()
    };
    return mockTeams[teamIndex];
  },

  deleteTeam: async (teamId: string): Promise<boolean> => {
    await new Promise(resolve => setTimeout(resolve, 400));
    const teamIndex = mockTeams.findIndex(team => team.id === teamId);
    if (teamIndex === -1) return false;
    
    mockTeams.splice(teamIndex, 1);
    return true;
  },

  // Executions
  executeTeam: async (teamId: string, inputData: any): Promise<TeamExecution> => {
    await new Promise(resolve => setTimeout(resolve, 600));
    const team = mockTeams.find(t => t.id === teamId);
    if (!team) throw new Error("Team not found");

    const execution: TeamExecution = {
      execution_id: `exec-${Date.now()}`,
      team_id: teamId,
      status: "running",
      started_at: new Date().toISOString(),
      estimated_completion: new Date(Date.now() + 30 * 60000).toISOString(),
      progress: {
        completed_agents: 0,
        total_agents: team.agents.length,
        current_step: "Initializing agents"
      },
      results: [],
      logs: [
        {
          timestamp: new Date().toISOString(),
          level: "info",
          message: "Execution started",
        }
      ]
    };
    
    mockExecutions.push(execution);
    return execution;
  },

  getExecution: async (executionId: string): Promise<TeamExecution | null> => {
    await new Promise(resolve => setTimeout(resolve, 200));
    return mockExecutions.find(exec => exec.execution_id === executionId) || null;
  },

  getExecutions: async (): Promise<{ executions: TeamExecution[] }> => {
    await new Promise(resolve => setTimeout(resolve, 400));
    return { executions: mockExecutions };
  },

  cancelExecution: async (executionId: string): Promise<boolean> => {
    await new Promise(resolve => setTimeout(resolve, 300));
    const execution = mockExecutions.find(exec => exec.execution_id === executionId);
    if (!execution) return false;
    
    execution.status = "cancelled";
    return true;
  },

  // System Health
  getSystemHealth: async (): Promise<SystemHealth> => {
    await new Promise(resolve => setTimeout(resolve, 200));
    return mockSystemHealth;
  }
};
