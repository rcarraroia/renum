
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Team, AgentRole, WorkflowType } from '@/types/team';
import { Users, Clock, Settings, ArrowRight } from 'lucide-react';

interface TeamDetailsProps {
  team: Team;
  onClose: () => void;
}

const roleLabels: Record<AgentRole, string> = {
  leader: 'Líder',
  member: 'Membro',
  coordinator: 'Coordenador'
};

const workflowLabels: Record<WorkflowType, string> = {
  sequential: 'Sequencial',
  parallel: 'Paralelo',
  conditional: 'Condicional',
  pipeline: 'Pipeline'
};

const inputSourceLabels: Record<string, string> = {
  initial_prompt: 'Prompt Inicial',
  previous_output: 'Saída Anterior',
  data_feed: 'Feed de Dados',
  user_input: 'Entrada do Usuário'
};

export function TeamDetails({ team, onClose }: TeamDetailsProps) {
  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold">{team.name}</h2>
          {team.description && (
            <p className="text-muted-foreground">{team.description}</p>
          )}
        </div>
        <Badge variant={team.status === 'active' ? 'default' : 'secondary'}>
          {team.status}
        </Badge>
      </div>

      {/* Informações gerais */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="flex items-center space-x-2 p-4">
            <Users className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">{team.agents_count}</p>
              <p className="text-xs text-muted-foreground">Agentes</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center space-x-2 p-4">
            <Settings className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">{workflowLabels[team.workflow_type]}</p>
              <p className="text-xs text-muted-foreground">Workflow</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center space-x-2 p-4">
            <Clock className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">
                {new Date(team.created_at).toLocaleDateString('pt-BR')}
              </p>
              <p className="text-xs text-muted-foreground">Criada em</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Lista de agentes */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Agentes da Equipe</h3>
        
        <div className="space-y-3">
          {team.agents
            .sort((a, b) => a.order - b.order)
            .map((agent, index) => (
              <Card key={agent.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-full bg-renum-primary/10 flex items-center justify-center text-sm font-medium">
                        {agent.order}
                      </div>
                      <div>
                        <CardTitle className="text-base">
                          {agent.agent_details?.name || `Agente ${agent.order}`}
                        </CardTitle>
                        <CardDescription>
                          ID: {agent.agent_id}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge variant="outline">
                      {roleLabels[agent.role]}
                    </Badge>
                  </div>
                </CardHeader>
                
                <CardContent className="space-y-3">
                  {agent.agent_details?.description && (
                    <p className="text-sm text-muted-foreground">
                      {agent.agent_details.description}
                    </p>
                  )}
                  
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Fonte de Entrada
                      </p>
                      <p className="text-sm">
                        {inputSourceLabels[agent.config.input_source] || agent.config.input_source}
                      </p>
                    </div>
                    
                    {agent.config.timeout_minutes && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Timeout
                        </p>
                        <p className="text-sm">
                          {agent.config.timeout_minutes} minutos
                        </p>
                      </div>
                    )}
                  </div>

                  {agent.agent_details?.capabilities && agent.agent_details.capabilities.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                        Capacidades
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {agent.agent_details.capabilities.map((capability, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            {capability}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
                
                {index < team.agents.length - 1 && team.workflow_type === 'sequential' && (
                  <div className="flex justify-center pb-2">
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                )}
              </Card>
            ))}
        </div>
      </div>

      {/* Rodapé */}
      <div className="flex justify-between items-center pt-4 border-t">
        <div className="text-sm text-muted-foreground">
          Última atualização: {new Date(team.updated_at).toLocaleString('pt-BR')}
        </div>
        <Button onClick={onClose}>
          Fechar
        </Button>
      </div>
    </div>
  );
}
