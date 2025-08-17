
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { AgentBasicInfoPanel } from '@/components/agent-builder/AgentBasicInfoPanel';
import { CapabilitiesBuilder } from '@/components/agent-builder/CapabilitiesBuilder';
import { PromptEditor } from '@/components/agent-builder/PromptEditor';
import { PolicyConfiguration } from '@/components/agent-builder/PolicyConfiguration';
import { TestRunner } from '@/components/agent-builder/TestRunner';
import { AgentPreview } from '@/components/agent-builder/AgentPreview';
import { useAgentBuilder } from '@/hooks/useAgentBuilder';
import { Save, Play, Eye, ArrowLeft } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export const AgentBuilder = () => {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('basic');
  
  const {
    currentAgent,
    isEditing,
    isDirty,
    isLoading,
    validationErrors,
    updateAgent,
    saveAgent,
    testAgent,
    loadAgent
  } = useAgentBuilder(agentId);

  useEffect(() => {
    if (agentId && agentId !== 'new') {
      loadAgent(agentId);
    }
  }, [agentId, loadAgent]);

  const handleSave = async () => {
    try {
      await saveAgent();
      toast({
        title: "Agente salvo",
        description: "O agente foi salvo com sucesso.",
      });
    } catch (error) {
      toast({
        title: "Erro ao salvar",
        description: "Ocorreu um erro ao salvar o agente.",
        variant: "destructive"
      });
    }
  };

  const handleTest = async () => {
    try {
      const result = await testAgent();
      toast({
        title: "Teste executado",
        description: "O teste foi executado com sucesso.",
      });
    } catch (error) {
      toast({
        title: "Erro no teste",
        description: "Ocorreu um erro durante o teste.",
        variant: "destructive"
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Carregando agente...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => navigate('/admin/agents')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar
          </Button>
          <div>
            <h1 className="text-2xl font-bold">
              {agentId === 'new' ? 'Novo Agente' : `Editando: ${currentAgent?.name || 'Agente'}`}
            </h1>
            {currentAgent && (
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant={currentAgent.status === 'active' ? 'default' : 'secondary'}>
                  {currentAgent.status}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  v{currentAgent.version}
                </span>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={handleTest}
            disabled={!currentAgent || validationErrors.length > 0}
          >
            <Play className="h-4 w-4 mr-2" />
            Testar
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setActiveTab('preview')}
          >
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>
          <Button 
            onClick={handleSave}
            disabled={!isDirty || validationErrors.length > 0}
          >
            <Save className="h-4 w-4 mr-2" />
            Salvar
          </Button>
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Erros de Validação</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside space-y-1">
              {validationErrors.map((error, index) => (
                <li key={index} className="text-sm text-destructive">
                  {error.message}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Navigation */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Configuração</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Tabs 
                value={activeTab} 
                onValueChange={setActiveTab}
                orientation="vertical"
                className="w-full"
              >
                <TabsList className="grid w-full grid-cols-1 h-auto bg-transparent">
                  <TabsTrigger value="basic" className="justify-start">
                    Informações Básicas
                  </TabsTrigger>
                  <TabsTrigger value="capabilities" className="justify-start">
                    Capacidades
                  </TabsTrigger>
                  <TabsTrigger value="prompts" className="justify-start">
                    Prompts
                  </TabsTrigger>
                  <TabsTrigger value="policy" className="justify-start">
                    Políticas
                  </TabsTrigger>
                  <TabsTrigger value="test" className="justify-start">
                    Testes
                  </TabsTrigger>
                  <TabsTrigger value="preview" className="justify-start">
                    Preview
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Area */}
        <div className="lg:col-span-3">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsContent value="basic">
              <AgentBasicInfoPanel 
                agent={currentAgent}
                onChange={updateAgent}
              />
            </TabsContent>

            <TabsContent value="capabilities">
              <CapabilitiesBuilder 
                capabilities={currentAgent?.capabilities || []}
                inputSchema={currentAgent?.input_schema || {}}
                onChange={(capabilities, inputSchema) => 
                  updateAgent({ 
                    capabilities, 
                    input_schema: inputSchema 
                  })
                }
              />
            </TabsContent>

            <TabsContent value="prompts">
              <PromptEditor 
                prompts={currentAgent?.policy?.prompts || {}}
                variables={currentAgent?.policy?.variables || []}
                onChange={(prompts) => 
                  updateAgent({ 
                    policy: { 
                      ...currentAgent?.policy, 
                      prompts 
                    } 
                  })
                }
              />
            </TabsContent>

            <TabsContent value="policy">
              <PolicyConfiguration 
                policy={currentAgent?.policy || {}}
                onChange={(policy) => updateAgent({ policy })}
              />
            </TabsContent>

            <TabsContent value="test">
              <TestRunner 
                agent={currentAgent}
                onTest={testAgent}
              />
            </TabsContent>

            <TabsContent value="preview">
              <AgentPreview 
                agent={currentAgent}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};
