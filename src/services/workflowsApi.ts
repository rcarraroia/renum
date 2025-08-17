
import { supabase } from '@/integrations/supabase/client';
import { Workflow, CreateWorkflowRequest, WorkflowRun, StartWorkflowRequest, ExecutionLog } from '@/types/workflows';

export const workflowsApi = {
  // Listar workflows do usuário
  list: async (): Promise<{ workflows: Workflow[]; total: number }> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('workflows')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error fetching workflows:', error);
      throw new Error(error.message);
    }

    const workflows = (data || []).map(workflow => ({
      ...workflow,
      agents_used: Array.isArray(workflow.agents_used) 
        ? (workflow.agents_used as string[]).filter((agent): agent is string => typeof agent === 'string')
        : [],
      workflow_data: workflow.workflow_data as Record<string, any> || {},
      status: (workflow.status as 'draft' | 'active' | 'archived') || 'draft',
      created_at: workflow.created_at || new Date().toISOString(),
      updated_at: workflow.updated_at || new Date().toISOString(),
      description: workflow.description || undefined,
    }));

    return {
      workflows,
      total: workflows.length,
    };
  },

  // Obter workflow específico
  get: async (workflowId: string): Promise<Workflow> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('workflows')
      .select('*')
      .eq('id', workflowId)
      .eq('user_id', user.id)
      .single();

    if (error) {
      console.error('Error fetching workflow:', error);
      throw new Error(error.message);
    }

    if (!data) {
      throw new Error('Workflow não encontrado');
    }

    return {
      ...data,
      agents_used: Array.isArray(data.agents_used) 
        ? (data.agents_used as string[]).filter((agent): agent is string => typeof agent === 'string')
        : [],
      workflow_data: data.workflow_data as Record<string, any> || {},
      status: (data.status as 'draft' | 'active' | 'archived') || 'draft',
      created_at: data.created_at || new Date().toISOString(),
      updated_at: data.updated_at || new Date().toISOString(),
      description: data.description || undefined,
    };
  },

  // Criar novo workflow
  create: async (workflowData: CreateWorkflowRequest): Promise<Workflow> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('workflows')
      .insert({
        ...workflowData,
        user_id: user.id,
      })
      .select()
      .single();

    if (error) {
      console.error('Error creating workflow:', error);
      throw new Error(error.message);
    }

    return {
      ...data,
      agents_used: Array.isArray(data.agents_used) 
        ? (data.agents_used as string[]).filter((agent): agent is string => typeof agent === 'string')
        : [],
      workflow_data: data.workflow_data as Record<string, any> || {},
      status: (data.status as 'draft' | 'active' | 'archived') || 'draft',
      created_at: data.created_at || new Date().toISOString(),
      updated_at: data.updated_at || new Date().toISOString(),
      description: data.description || undefined,
    };
  },

  // Iniciar execução de workflow
  start: async (request: StartWorkflowRequest): Promise<WorkflowRun> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('workflow_runs')
      .insert({
        workflow_id: request.workflow_id,
        user_id: user.id,
        input_data: request.input_data,
        status: 'pending',
      })
      .select()
      .single();

    if (error) {
      console.error('Error starting workflow:', error);
      throw new Error(error.message);
    }

    return {
      ...data,
      status: (data.status as 'pending' | 'running' | 'completed' | 'failed' | 'cancelled') || 'pending',
      results: Array.isArray(data.results) ? data.results : [],
      execution_logs: Array.isArray(data.execution_logs) ? data.execution_logs : [],
      input_data: data.input_data as Record<string, any> || {},
      started_at: data.started_at || new Date().toISOString(),
      created_at: data.created_at || new Date().toISOString(),
      updated_at: data.updated_at || new Date().toISOString(),
      completed_at: data.completed_at || undefined,
      error_message: data.error_message || undefined,
    };
  },

  // Listar execuções do usuário
  listRuns: async (): Promise<{ runs: WorkflowRun[]; total: number }> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('workflow_runs')
      .select(`
        *,
        workflows(name)
      `)
      .eq('user_id', user.id)
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error fetching workflow runs:', error);
      throw new Error(error.message);
    }

    const runs = (data || []).map(run => ({
      ...run,
      status: (run.status as 'pending' | 'running' | 'completed' | 'failed' | 'cancelled') || 'pending',
      results: Array.isArray(run.results) ? run.results : [],
      execution_logs: Array.isArray(run.execution_logs) ? run.execution_logs : [],
      input_data: run.input_data as Record<string, any> || {},
      started_at: run.started_at || new Date().toISOString(),
      created_at: run.created_at || new Date().toISOString(),
      updated_at: run.updated_at || new Date().toISOString(),
      completed_at: run.completed_at || undefined,
      error_message: run.error_message || undefined,
    }));

    return {
      runs,
      total: runs.length,
    };
  },

  // Obter logs de execução
  getLogs: async (runId: string): Promise<ExecutionLog[]> => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      throw new Error('Usuário não autenticado');
    }

    const { data, error } = await supabase
      .from('execution_logs')
      .select('*')
      .eq('run_id', runId)
      .order('timestamp', { ascending: true });

    if (error) {
      console.error('Error fetching execution logs:', error);
      throw new Error(error.message);
    }

    return (data || []).map(log => ({
      ...log,
      log_level: (log.log_level as 'debug' | 'info' | 'warn' | 'error') || 'info',
      metadata: log.metadata as Record<string, any> || {},
      agent_id: log.agent_id || undefined,
      step_number: log.step_number || undefined,
    }));
  },
};
