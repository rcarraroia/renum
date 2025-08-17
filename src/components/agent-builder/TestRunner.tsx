
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Play, Save, FileText, Clock, DollarSign, CheckCircle, XCircle } from 'lucide-react';
import { Agent } from '@/types/agents';

interface TestResult {
  success: boolean;
  output: string;
  execution_time: number;
  cost: number;
  error?: string;
}

interface TestRunnerProps {
  agent: Agent | null;
  onTest: (testData: any) => Promise<TestResult>;
}

const TEST_EXAMPLES = {
  send_email: {
    name: 'Enviar Email',
    input: {
      to: 'test@example.com',
      subject: 'Teste do Agente',
      body: 'Este é um email de teste enviado pelo agente.'
    }
  },
  query_database: {
    name: 'Consulta ao Banco',
    input: {
      query: 'SELECT * FROM users WHERE active = true',
      parameters: {}
    }
  },
  http_request: {
    name: 'Requisição HTTP',
    input: {
      url: 'https://api.example.com/data',
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    }
  }
};

export const TestRunner: React.FC<TestRunnerProps> = ({ agent, onTest }) => {
  const [environment, setEnvironment] = useState<'sandbox' | 'production'>('sandbox');
  const [testInput, setTestInput] = useState('{}');
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedExample, setSelectedExample] = useState<string>('');

  const loadExample = (exampleKey: string) => {
    const example = TEST_EXAMPLES[exampleKey as keyof typeof TEST_EXAMPLES];
    if (example) {
      setTestInput(JSON.stringify(example.input, null, 2));
      setSelectedExample(exampleKey);
    }
  };

  const runTest = async () => {
    if (!agent) return;

    setIsRunning(true);
    try {
      const parsedInput = JSON.parse(testInput);
      const result = await onTest({
        agent_id: agent.agent_id,
        input: parsedInput,
        environment
      });
      
      setTestResults([result, ...testResults.slice(0, 4)]); // Keep last 5 results
    } catch (error) {
      const errorResult: TestResult = {
        success: false,
        output: '',
        execution_time: 0,
        cost: 0,
        error: error instanceof Error ? error.message : 'Erro desconhecido'
      };
      setTestResults([errorResult, ...testResults.slice(0, 4)]);
    } finally {
      setIsRunning(false);
    }
  };

  const saveTest = () => {
    // Implement save test functionality
    console.log('Saving test:', { input: testInput, environment });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Test Runner</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Environment Selection */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label>Ambiente de Teste</Label>
              <Select value={environment} onValueChange={(value: 'sandbox' | 'production') => setEnvironment(value)}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sandbox">
                    <div className="flex items-center">
                      <Badge variant="secondary" className="mr-2">Sandbox</Badge>
                      Seguro
                    </div>
                  </SelectItem>
                  <SelectItem value="production">
                    <div className="flex items-center">
                      <Badge variant="destructive" className="mr-2">Produção</Badge>
                      Cuidado
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center space-x-2">
              <Select value={selectedExample} onValueChange={loadExample}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Carregar exemplo" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TEST_EXAMPLES).map(([key, example]) => (
                    <SelectItem key={key} value={key}>
                      {example.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Test Input */}
          <div className="space-y-2">
            <Label>Dados de Teste (JSON)</Label>
            <Textarea
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              rows={8}
              className="font-mono"
              placeholder="Cole ou digite os dados de teste em formato JSON..."
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Button
                onClick={runTest}
                disabled={isRunning || !agent}
              >
                <Play className="h-4 w-4 mr-2" />
                {isRunning ? 'Executando...' : 'Executar Teste'}
              </Button>
              
              <Button
                variant="outline"
                onClick={saveTest}
              >
                <Save className="h-4 w-4 mr-2" />
                Salvar Teste
              </Button>
            </div>

            {environment === 'production' && (
              <Badge variant="destructive">
                ⚠️ Ambiente de Produção
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Test Results */}
      {testResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Resultados dos Testes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {testResults.map((result, index) => (
                <div
                  key={index}
                  className={`p-4 rounded-lg border ${
                    result.success 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      {result.success ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}
                      <Badge variant={result.success ? 'default' : 'destructive'}>
                        {result.success ? 'Sucesso' : 'Falha'}
                      </Badge>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                      <div className="flex items-center">
                        <Clock className="h-4 w-4 mr-1" />
                        {result.execution_time}ms
                      </div>
                      <div className="flex items-center">
                        <DollarSign className="h-4 w-4 mr-1" />
                        ${result.cost.toFixed(3)}
                      </div>
                    </div>
                  </div>

                  {result.error && (
                    <div className="mb-3">
                      <Label className="text-red-600">Erro:</Label>
                      <pre className="text-sm text-red-800 mt-1 p-2 bg-red-100 rounded">
                        {result.error}
                      </pre>
                    </div>
                  )}

                  {result.output && (
                    <div>
                      <Label>Output:</Label>
                      <pre className="text-sm mt-1 p-2 bg-muted rounded overflow-x-auto">
                        {typeof result.output === 'object' 
                          ? JSON.stringify(result.output, null, 2)
                          : result.output
                        }
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agent Status */}
      {agent && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Status do Agente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <Label>ID:</Label>
                <p className="font-mono">{agent.agent_id}</p>
              </div>
              <div>
                <Label>Versão:</Label>
                <p>{agent.version}</p>
              </div>
              <div>
                <Label>Status:</Label>
                <Badge variant={agent.status === 'active' ? 'default' : 'secondary'}>
                  {agent.status}
                </Badge>
              </div>
              <div>
                <Label>Capacidades:</Label>
                <p>{agent.capabilities.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
