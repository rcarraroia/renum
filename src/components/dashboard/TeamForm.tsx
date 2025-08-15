
import React from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, Trash2 } from 'lucide-react';
import { Team, WorkflowType, AgentRole } from '@/types/team';

const teamFormSchema = z.object({
  name: z.string().min(1, 'Nome é obrigatório'),
  description: z.string().optional(),
  workflow_type: z.enum(['sequential', 'parallel', 'conditional', 'pipeline']),
  agents: z.array(z.object({
    agent_id: z.string().min(1, 'ID do agente é obrigatório'),
    role: z.enum(['leader', 'member', 'coordinator']),
    order: z.number().min(1),
    config: z.object({
      input_source: z.string().min(1, 'Fonte de entrada é obrigatória'),
      conditions: z.array(z.any()).default([]),
      timeout_minutes: z.number().optional()
    })
  })).min(1, 'Pelo menos um agente é obrigatório')
});

type TeamFormData = z.infer<typeof teamFormSchema>;

interface TeamFormProps {
  initialData?: Team;
  onSubmit: (data: Partial<Team>) => void;
  onCancel: () => void;
}

export function TeamForm({ initialData, onSubmit, onCancel }: TeamFormProps) {
  const form = useForm<TeamFormData>({
    resolver: zodResolver(teamFormSchema),
    defaultValues: {
      name: initialData?.name || '',
      description: initialData?.description || '',
      workflow_type: initialData?.workflow_type || 'sequential',
      agents: initialData?.agents.map(agent => ({
        agent_id: agent.agent_id,
        role: agent.role,
        order: agent.order,
        config: {
          input_source: agent.config.input_source,
          conditions: agent.config.conditions,
          timeout_minutes: agent.config.timeout_minutes
        }
      })) || [{
        agent_id: '',
        role: 'member' as AgentRole,
        order: 1,
        config: {
          input_source: 'initial_prompt',
          conditions: []
        }
      }]
    }
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'agents'
  });

  const handleSubmit = (data: TeamFormData) => {
    const teamData = {
      ...data,
      agents: data.agents.map((agent, index) => ({
        id: initialData?.agents[index]?.id || `agent-${Date.now()}-${index}`,
        agent_id: agent.agent_id,
        role: agent.role,
        order: agent.order,
        config: {
          input_source: agent.config.input_source,
          conditions: agent.config.conditions || [],
          timeout_minutes: agent.config.timeout_minutes
        }
      }))
    };
    
    onSubmit(teamData);
  };

  const addAgent = () => {
    append({
      agent_id: '',
      role: 'member' as AgentRole,
      order: fields.length + 1,
      config: {
        input_source: 'previous_output',
        conditions: []
      }
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Nome da Equipe</FormLabel>
                <FormControl>
                  <Input placeholder="Ex: Marketing Team" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="workflow_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Tipo de Workflow</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione o tipo" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="sequential">Sequencial</SelectItem>
                    <SelectItem value="parallel">Paralelo</SelectItem>
                    <SelectItem value="conditional">Condicional</SelectItem>
                    <SelectItem value="pipeline">Pipeline</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Descrição</FormLabel>
              <FormControl>
                <Textarea 
                  placeholder="Descreva o propósito da equipe..."
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Descrição opcional da equipe
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Agentes</h3>
            <Button type="button" variant="outline" onClick={addAgent}>
              <Plus className="h-4 w-4 mr-2" />
              Adicionar Agente
            </Button>
          </div>

          {fields.map((field, index) => (
            <Card key={field.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    Agente {index + 1}
                  </CardTitle>
                  {fields.length > 1 && (
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <FormField
                    control={form.control}
                    name={`agents.${index}.agent_id`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>ID do Agente</FormLabel>
                        <FormControl>
                          <Input placeholder="suna-agent-id" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name={`agents.${index}.role`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Papel</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="leader">Líder</SelectItem>
                            <SelectItem value="member">Membro</SelectItem>
                            <SelectItem value="coordinator">Coordenador</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name={`agents.${index}.order`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Ordem</FormLabel>
                        <FormControl>
                          <Input 
                            type="number" 
                            min="1"
                            {...field}
                            onChange={e => field.onChange(parseInt(e.target.value))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <FormField
                    control={form.control}
                    name={`agents.${index}.config.input_source`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Fonte de Entrada</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="initial_prompt">Prompt Inicial</SelectItem>
                            <SelectItem value="previous_output">Saída Anterior</SelectItem>
                            <SelectItem value="data_feed">Feed de Dados</SelectItem>
                            <SelectItem value="user_input">Entrada do Usuário</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name={`agents.${index}.config.timeout_minutes`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Timeout (minutos)</FormLabel>
                        <FormControl>
                          <Input 
                            type="number" 
                            min="1"
                            max="60"
                            placeholder="30"
                            {...field}
                            onChange={e => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                          />
                        </FormControl>
                        <FormDescription>
                          Opcional (1-60 minutos)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancelar
          </Button>
          <Button type="submit">
            {initialData ? 'Atualizar' : 'Criar'} Equipe
          </Button>
        </div>
      </form>
    </Form>
  );
}
