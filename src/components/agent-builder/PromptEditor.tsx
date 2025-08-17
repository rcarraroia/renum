
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Eye, Copy, RotateCcw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface PromptVariable {
  name: string;
  type: 'string' | 'object' | 'array';
  description: string;
  required: boolean;
  default_value?: any;
}

interface PromptEditorProps {
  prompts: Record<string, any>;
  variables: PromptVariable[];
  onChange: (prompts: Record<string, any>) => void;
}

const DEFAULT_PROMPTS = {
  system_prompt: `You are a helpful AI assistant. Follow these guidelines:

1. Be clear and concise in your responses
2. Ask for clarification when needed
3. Provide step-by-step instructions when appropriate
4. Always be polite and professional

Use the available capabilities to help the user achieve their goals.`,
  
  user_prompt_template: `User Request: {{user_input}}

Context: {{context}}

Please help the user with their request using the appropriate capabilities.`,
};

const COMMON_VARIABLES: PromptVariable[] = [
  {
    name: 'user_input',
    type: 'string',
    description: 'The user\'s input or request',
    required: true
  },
  {
    name: 'context',
    type: 'object',
    description: 'Additional context for the request',
    required: false
  },
  {
    name: 'capabilities',
    type: 'array',
    description: 'List of available capabilities',
    required: false
  },
  {
    name: 'user_data',
    type: 'object',
    description: 'User profile and preferences',
    required: false
  }
];

export const PromptEditor: React.FC<PromptEditorProps> = ({
  prompts,
  variables = [],
  onChange
}) => {
  const { toast } = useToast();
  const [previewMode, setPreviewMode] = useState(false);
  const [testVariables, setTestVariables] = useState<Record<string, any>>({
    user_input: 'Send an email to john@example.com about the meeting',
    context: { meeting_time: '2024-01-15 14:00', location: 'Conference Room A' }
  });

  const allVariables = [...COMMON_VARIABLES, ...variables];

  const insertVariable = (variableName: string, promptType: 'system_prompt' | 'user_prompt_template') => {
    const currentPrompt = prompts[promptType] || '';
    const placeholder = `{{${variableName}}}`;
    const newPrompt = currentPrompt + placeholder;
    
    onChange({
      ...prompts,
      [promptType]: newPrompt
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copiado",
      description: "Texto copiado para a área de transferência.",
    });
  };

  const resetPrompt = (promptType: 'system_prompt' | 'user_prompt_template') => {
    onChange({
      ...prompts,
      [promptType]: DEFAULT_PROMPTS[promptType]
    });
    toast({
      title: "Prompt resetado",
      description: "O prompt foi resetado para o padrão.",
    });
  };

  const renderPreview = (template: string) => {
    let preview = template;
    
    // Replace variables with test values
    allVariables.forEach(variable => {
      const placeholder = `{{${variable.name}}}`;
      const value = testVariables[variable.name] || 
                   (variable.default_value !== undefined ? variable.default_value : `[${variable.name}]`);
      
      preview = preview.replace(
        new RegExp(placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'),
        typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
      );
    });
    
    return preview;
  };

  return (
    <div className="space-y-6">
      {/* Variables Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Variáveis Disponíveis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {allVariables.map((variable) => (
              <div
                key={variable.name}
                className="p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                onClick={() => {
                  copyToClipboard(`{{${variable.name}}}`);
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <Badge variant="outline" className="text-xs">
                    {variable.name}
                  </Badge>
                  <Badge variant={variable.required ? 'default' : 'secondary'} className="text-xs">
                    {variable.type}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {variable.description}
                </p>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            Clique em uma variável para copiar. Use {`{{nome_variavel}}`} nos prompts.
          </p>
        </CardContent>
      </Card>

      {/* Prompt Editor */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Editor de Prompts</CardTitle>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setPreviewMode(!previewMode)}
            >
              <Eye className="h-4 w-4 mr-2" />
              {previewMode ? 'Editar' : 'Preview'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="system" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="system">System Prompt</TabsTrigger>
              <TabsTrigger value="user">User Template</TabsTrigger>
            </TabsList>
            
            <TabsContent value="system" className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>System Prompt</Label>
                <div className="flex items-center space-x-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => copyToClipboard(prompts.system_prompt || '')}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => resetPrompt('system_prompt')}
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              {previewMode ? (
                <div className="p-4 bg-muted rounded-lg">
                  <pre className="whitespace-pre-wrap text-sm">
                    {renderPreview(prompts.system_prompt || DEFAULT_PROMPTS.system_prompt)}
                  </pre>
                </div>
              ) : (
                <Textarea
                  value={prompts.system_prompt || DEFAULT_PROMPTS.system_prompt}
                  onChange={(e) => onChange({ ...prompts, system_prompt: e.target.value })}
                  rows={12}
                  placeholder="Digite o system prompt aqui..."
                  className="font-mono"
                />
              )}
              
              <div className="flex flex-wrap gap-2">
                {allVariables.map((variable) => (
                  <Button
                    key={variable.name}
                    size="sm"
                    variant="outline"
                    onClick={() => insertVariable(variable.name, 'system_prompt')}
                  >
                    + {variable.name}
                  </Button>
                ))}
              </div>
            </TabsContent>
            
            <TabsContent value="user" className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>User Prompt Template</Label>
                <div className="flex items-center space-x-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => copyToClipboard(prompts.user_prompt_template || '')}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => resetPrompt('user_prompt_template')}
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              {previewMode ? (
                <div className="p-4 bg-muted rounded-lg">
                  <pre className="whitespace-pre-wrap text-sm">
                    {renderPreview(prompts.user_prompt_template || DEFAULT_PROMPTS.user_prompt_template)}
                  </pre>
                </div>
              ) : (
                <Textarea
                  value={prompts.user_prompt_template || DEFAULT_PROMPTS.user_prompt_template}
                  onChange={(e) => onChange({ ...prompts, user_prompt_template: e.target.value })}
                  rows={8}
                  placeholder="Digite o template do user prompt aqui..."
                  className="font-mono"
                />
              )}
              
              <div className="flex flex-wrap gap-2">
                {allVariables.map((variable) => (
                  <Button
                    key={variable.name}
                    size="sm"
                    variant="outline"
                    onClick={() => insertVariable(variable.name, 'user_prompt_template')}
                  >
                    + {variable.name}
                  </Button>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Test Variables */}
      {previewMode && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Variáveis de Teste</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {allVariables.filter(v => v.required || testVariables[v.name] !== undefined).map((variable) => (
                <div key={variable.name} className="space-y-2">
                  <Label>{variable.name} ({variable.type})</Label>
                  <Textarea
                    value={
                      typeof testVariables[variable.name] === 'object' 
                        ? JSON.stringify(testVariables[variable.name], null, 2)
                        : String(testVariables[variable.name] || '')
                    }
                    onChange={(e) => {
                      let value: any = e.target.value;
                      if (variable.type === 'object' || variable.type === 'array') {
                        try {
                          value = JSON.parse(value);
                        } catch {
                          // Keep as string if JSON is invalid
                        }
                      }
                      setTestVariables({
                        ...testVariables,
                        [variable.name]: value
                      });
                    }}
                    rows={variable.type === 'object' || variable.type === 'array' ? 3 : 1}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
