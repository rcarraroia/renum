
import { useState, useCallback } from 'react';
import { Agent, CreateAgentRequest } from '@/types/agents';
import { agentsApi } from '@/services/agentsApi';

interface ValidationError {
  field: string;
  message: string;
}

interface TestResult {
  success: boolean;
  output: string;
  execution_time: number;
  cost: number;
  error?: string;
}

export const useAgentBuilder = (agentId?: string) => {
  const [currentAgent, setCurrentAgent] = useState<Agent | null>(null);
  const [originalAgent, setOriginalAgent] = useState<Agent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);

  const isEditing = agentId !== 'new';
  const isDirty = JSON.stringify(currentAgent) !== JSON.stringify(originalAgent);

  const validateAgent = useCallback((agent: Agent | null): ValidationError[] => {
    const errors: ValidationError[] = [];
    
    if (!agent) {
      errors.push({ field: 'general', message: 'Agente é obrigatório' });
      return errors;
    }

    if (!agent.name || agent.name.trim().length < 3) {
      errors.push({ field: 'name', message: 'Nome deve ter pelo menos 3 caracteres' });
    }

    if (!agent.agent_id || !/^[a-z0-9-]+$/.test(agent.agent_id)) {
      errors.push({ field: 'agent_id', message: 'ID deve conter apenas letras minúsculas, números e hífens' });
    }

    if (!agent.version || !/^\d+\.\d+\.\d+$/.test(agent.version)) {
      errors.push({ field: 'version', message: 'Versão deve seguir o formato semântico (ex: 1.0.0)' });
    }

    if (agent.capabilities.length === 0) {
      errors.push({ field: 'capabilities', message: 'Pelo menos uma capacidade é obrigatória' });
    }

    return errors;
  }, []);

  const loadAgent = useCallback(async (id: string) => {
    if (id === 'new') return;

    setIsLoading(true);
    try {
      const agent = await agentsApi.get(id);
      setCurrentAgent(agent);
      setOriginalAgent(agent);
      setValidationErrors(validateAgent(agent));
    } catch (error) {
      console.error('Error loading agent:', error);
    } finally {
      setIsLoading(false);
    }
  }, [validateAgent]);

  const updateAgent = useCallback((updates: Partial<Agent>) => {
    if (!currentAgent && updates) {
      // Create new agent
      const newAgent: Agent = {
        id: crypto.randomUUID(),
        agent_id: updates.agent_id || '',
        version: updates.version || '1.0.0',
        name: updates.name || '',
        description: updates.description,
        capabilities: updates.capabilities || [],
        input_schema: updates.input_schema || {},
        policy: updates.policy || {},
        dependencies: updates.dependencies || [],
        status: updates.status || 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        ...updates
      };
      setCurrentAgent(newAgent);
      setValidationErrors(validateAgent(newAgent));
    } else if (currentAgent) {
      const updatedAgent = {
        ...currentAgent,
        ...updates,
        updated_at: new Date().toISOString()
      };
      setCurrentAgent(updatedAgent);
      setValidationErrors(validateAgent(updatedAgent));
    }
  }, [currentAgent, validateAgent]);

  const saveAgent = useCallback(async () => {
    if (!currentAgent) throw new Error('No agent to save');

    const errors = validateAgent(currentAgent);
    if (errors.length > 0) {
      setValidationErrors(errors);
      throw new Error('Validation errors exist');
    }

    setIsLoading(true);
    try {
      if (isEditing) {
        // Update existing agent - would need update API
        console.log('Update agent not implemented yet');
      } else {
        // Create new agent
        const createRequest: CreateAgentRequest = {
          agent_id: currentAgent.agent_id,
          name: currentAgent.name,
          description: currentAgent.description,
          capabilities: currentAgent.capabilities,
          input_schema: currentAgent.input_schema,
          policy: currentAgent.policy,
          dependencies: currentAgent.dependencies
        };
        
        const savedAgent = await agentsApi.create(createRequest);
        setCurrentAgent(savedAgent);
        setOriginalAgent(savedAgent);
      }
    } finally {
      setIsLoading(false);
    }
  }, [currentAgent, isEditing, validateAgent]);

  const testAgent = useCallback(async (testData?: any): Promise<TestResult> => {
    if (!currentAgent) throw new Error('No agent to test');

    // Mock test implementation
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          success: Math.random() > 0.3, // 70% success rate for demo
          output: `Test completed for ${currentAgent.name}`,
          execution_time: Math.floor(Math.random() * 1000) + 100,
          cost: Math.random() * 0.01,
          error: Math.random() > 0.7 ? undefined : 'Mock error for demonstration'
        });
      }, 1000 + Math.random() * 2000); // 1-3 second delay
    });
  }, [currentAgent]);

  return {
    currentAgent,
    isEditing,
    isDirty,
    isLoading,
    validationErrors,
    updateAgent,
    saveAgent,
    testAgent,
    loadAgent
  };
};
