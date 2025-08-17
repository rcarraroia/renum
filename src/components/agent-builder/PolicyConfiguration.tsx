
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';

interface PolicyConfigurationProps {
  policy: Record<string, any>;
  onChange: (policy: Record<string, any>) => void;
}

export const PolicyConfiguration: React.FC<PolicyConfigurationProps> = ({
  policy,
  onChange
}) => {
  const updatePolicy = (key: string, value: any) => {
    onChange({
      ...policy,
      [key]: value
    });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Políticas de Execução</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Rate Limiting */}
          <div>
            <h4 className="font-medium mb-3">Rate Limiting</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="max_requests">Máximo de Requisições por Minuto</Label>
                <Input
                  id="max_requests"
                  type="number"
                  value={policy.max_requests_per_minute || 10}
                  onChange={(e) => updatePolicy('max_requests_per_minute', parseInt(e.target.value))}
                  min={1}
                  max={1000}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="max_concurrent">Execuções Concorrentes</Label>
                <Input
                  id="max_concurrent"
                  type="number"
                  value={policy.max_concurrent_executions || 3}
                  onChange={(e) => updatePolicy('max_concurrent_executions', parseInt(e.target.value))}
                  min={1}
                  max={10}
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Timeouts */}
          <div>
            <h4 className="font-medium mb-3">Timeouts</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="timeout">Timeout de Execução (segundos)</Label>
                <Input
                  id="timeout"
                  type="number"
                  value={policy.timeout_seconds || 300}
                  onChange={(e) => updatePolicy('timeout_seconds', parseInt(e.target.value))}
                  min={10}
                  max={3600}
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Security */}
          <div>
            <h4 className="font-medium mb-3">Segurança</h4>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Requer Confirmação do Usuário</Label>
                  <p className="text-sm text-muted-foreground">
                    Solicita confirmação antes de executar ações sensíveis
                  </p>
                </div>
                <Switch
                  checked={policy.require_confirmation || false}
                  onCheckedChange={(checked) => updatePolicy('require_confirmation', checked)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="allowed_domains">Domínios Permitidos</Label>
                <Input
                  id="allowed_domains"
                  value={(policy.allowed_domains || []).join(', ')}
                  onChange={(e) => {
                    const domains = e.target.value
                      .split(',')
                      .map(d => d.trim())
                      .filter(d => d.length > 0);
                    updatePolicy('allowed_domains', domains);
                  }}
                  placeholder="example.com, api.service.com"
                />
                <p className="text-xs text-muted-foreground">
                  Domínios separados por vírgula. Deixe vazio para permitir todos.
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Billing */}
          <div>
            <h4 className="font-medium mb-3">Cobrança</h4>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="cost_per_execution">Custo por Execução (centavos)</Label>
                <Input
                  id="cost_per_execution"
                  type="number"
                  value={policy.cost_per_execution || 0}
                  onChange={(e) => updatePolicy('cost_per_execution', parseInt(e.target.value))}
                  min={0}
                  max={10000}
                />
                <p className="text-xs text-muted-foreground">
                  Custo em centavos por execução. 0 = gratuito.
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Preview */}
          <div className="p-4 bg-muted rounded-lg">
            <h4 className="font-medium mb-3">Preview das Políticas</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Req/min:</span>
                  <Badge variant="secondary">{policy.max_requests_per_minute || 10}</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Concorrência:</span>
                  <Badge variant="secondary">{policy.max_concurrent_executions || 3}</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Timeout:</span>
                  <Badge variant="secondary">{policy.timeout_seconds || 300}s</Badge>
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Confirmação:</span>
                  <Badge variant={policy.require_confirmation ? "default" : "secondary"}>
                    {policy.require_confirmation ? 'Sim' : 'Não'}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Custo:</span>
                  <Badge variant="secondary">
                    {policy.cost_per_execution || 0} centavos
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Domínios:</span>
                  <Badge variant="secondary">
                    {(policy.allowed_domains || []).length || 'Todos'}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
