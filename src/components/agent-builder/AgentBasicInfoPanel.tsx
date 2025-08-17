
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Agent } from '@/types/agents';

interface AgentBasicInfoPanelProps {
  agent: Agent | null;
  onChange: (updates: Partial<Agent>) => void;
}

export const AgentBasicInfoPanel: React.FC<AgentBasicInfoPanelProps> = ({ 
  agent, 
  onChange 
}) => {
  const generateAgentId = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, '-')
      .replace(/^-+|-+$/g, '');
  };

  const handleNameChange = (name: string) => {
    const agentId = generateAgentId(name);
    onChange({ name, agent_id: agentId });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Informações Básicas</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nome</Label>
            <Input
              id="name"
              value={agent?.name || ''}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Ex: Email Assistant"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="agent_id">ID do Agente</Label>
            <Input
              id="agent_id"
              value={agent?.agent_id || ''}
              onChange={(e) => onChange({ agent_id: e.target.value })}
              placeholder="email-assistant"
              pattern="^[a-z0-9-]+$"
            />
            <p className="text-xs text-muted-foreground">
              Apenas letras minúsculas, números e hífens
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="version">Versão</Label>
            <Input
              id="version"
              value={agent?.version || '1.0.0'}
              onChange={(e) => onChange({ version: e.target.value })}
              placeholder="1.0.0"
              pattern="^\d+\.\d+\.\d+$"
            />
            <p className="text-xs text-muted-foreground">
              Formato: major.minor.patch (ex: 1.0.0)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select 
              value={agent?.status || 'active'} 
              onValueChange={(value: 'active' | 'inactive' | 'deprecated') => 
                onChange({ status: value })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Ativo</SelectItem>
                <SelectItem value="inactive">Inativo</SelectItem>
                <SelectItem value="deprecated">Descontinuado</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Descrição</Label>
          <Textarea
            id="description"
            value={agent?.description || ''}
            onChange={(e) => onChange({ description: e.target.value })}
            placeholder="Descreva o que este agente faz e suas principais funcionalidades..."
            rows={4}
          />
        </div>

        <div className="p-4 bg-muted rounded-lg">
          <h4 className="font-medium mb-2">Preview do Agente</h4>
          <div className="text-sm text-muted-foreground space-y-1">
            <p><strong>ID:</strong> {agent?.agent_id || 'agent-id'}</p>
            <p><strong>Nome:</strong> {agent?.name || 'Nome do Agente'}</p>
            <p><strong>Versão:</strong> {agent?.version || '1.0.0'}</p>
            <p><strong>Status:</strong> {agent?.status || 'active'}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
