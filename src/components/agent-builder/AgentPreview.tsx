
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Agent } from '@/types/agents';
import { Bot, Settings, Zap, Shield, Clock, DollarSign } from 'lucide-react';

interface AgentPreviewProps {
  agent: Agent | null;
}

export const AgentPreview: React.FC<AgentPreviewProps> = ({ agent }) => {
  if (!agent) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center text-muted-foreground">
            <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Nenhum agente para preview</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const policy = agent.policy || {};

  return (
    <div className="space-y-6">
      {/* Agent Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Bot className="h-6 w-6 text-primary" />
              </div>
              <div>
                <CardTitle className="text-xl">{agent.name}</CardTitle>
                <div className="flex items-center space-x-2 mt-1">
                  <Badge variant={agent.status === 'active' ? 'default' : 'secondary'}>
                    {agent.status}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    v{agent.version}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-medium mb-2">Identificação</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="space-y-1">
                  <span className="text-muted-foreground">Agent ID:</span>
                  <p className="font-mono bg-muted px-2 py-1 rounded">
                    {agent.agent_id}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-muted-foreground">Criado em:</span>
                  <p>{new Date(agent.created_at).toLocaleDateString('pt-BR')}</p>
                </div>
              </div>
            </div>

            {agent.description && (
              <>
                <Separator />
                <div>
                  <h4 className="font-medium mb-2">Descrição</h4>
                  <p className="text-sm text-muted-foreground">
                    {agent.description}
                  </p>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Capabilities */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Zap className="h-5 w-5" />
            <CardTitle>Capacidades ({agent.capabilities.length})</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {agent.capabilities.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nenhuma capacidade definida
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {agent.capabilities.map((capability, index) => (
                <div
                  key={index}
                  className="p-3 border rounded-lg"
                >
                  <Badge variant="outline" className="mb-2">
                    {capability}
                  </Badge>
                  <p className="text-xs text-muted-foreground">
                    Capacidade do agente
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Input Schema Preview */}
      {agent.input_schema && Object.keys(agent.input_schema).length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Settings className="h-5 w-5" />
              <CardTitle>Schema de Entrada</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
              {JSON.stringify(agent.input_schema, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Policies */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <CardTitle>Políticas de Execução</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Requisições/minuto:</span>
                <Badge variant="secondary">
                  {policy.max_requests_per_minute || 10}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Execuções concorrentes:</span>
                <Badge variant="secondary">
                  {policy.max_concurrent_executions || 3}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Timeout:</span>
                <Badge variant="secondary">
                  <Clock className="h-3 w-3 mr-1" />
                  {policy.timeout_seconds || 300}s
                </Badge>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Requer confirmação:</span>
                <Badge variant={policy.require_confirmation ? 'default' : 'secondary'}>
                  {policy.require_confirmation ? 'Sim' : 'Não'}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Custo por execução:</span>
                <Badge variant="secondary">
                  <DollarSign className="h-3 w-3 mr-1" />
                  {policy.cost_per_execution || 0} centavos
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Domínios permitidos:</span>
                <Badge variant="secondary">
                  {(policy.allowed_domains || []).length || 'Todos'}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Prompts Preview */}
      {policy.prompts && (
        <Card>
          <CardHeader>
            <CardTitle>Prompts do Sistema</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {policy.prompts.system_prompt && (
                <div>
                  <h4 className="font-medium mb-2">System Prompt</h4>
                  <div className="p-3 bg-muted rounded text-sm">
                    <pre className="whitespace-pre-wrap">
                      {policy.prompts.system_prompt}
                    </pre>
                  </div>
                </div>
              )}
              
              {policy.prompts.user_prompt_template && (
                <div>
                  <h4 className="font-medium mb-2">User Prompt Template</h4>
                  <div className="p-3 bg-muted rounded text-sm">
                    <pre className="whitespace-pre-wrap">
                      {policy.prompts.user_prompt_template}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
