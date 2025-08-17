
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
      agents_used: Array.isArray(workflow.agents_used) ? workflow.agents_used : [],
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
      agents_used: Array.isArray(data.agents_used) ? data.agents_used : [],
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
      agents_used: Array.isArray(data.agents_used) ? data.agents_used : [],
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
      results: Array.isArray(data.results) ? data.results : [],
      execution_logs: Array.isArray(data.execution_logs) ? data.execution_logs : [],
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
      results: Array.isArray(run.results) ? run.results : [],
      execution_logs: Array.isArray(run.execution_logs) ? run.execution_logs : [],
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

    return data || [];
  },
};
