
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Plus, Trash2, TestTube } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { useToast } from '@/hooks/use-toast';

interface Capability {
  name: string;
  description: string;
  input_schema: Record<string, any>;
  output_schema?: Record<string, any>;
}

interface CapabilitiesBuilderProps {
  capabilities: string[];
  inputSchema: Record<string, any>;
  onChange: (capabilities: string[], inputSchema: Record<string, any>) => void;
}

const CAPABILITY_TEMPLATES = {
  send_email: {
    name: 'send_email',
    description: 'Send emails to specified recipients',
    input_schema: {
      type: 'object',
      properties: {
        to: { type: 'string', format: 'email' },
        subject: { type: 'string' },
        body: { type: 'string' },
        attachments: { 
          type: 'array', 
          items: { type: 'string' } 
        }
      },
      required: ['to', 'subject', 'body']
    }
  },
  query_database: {
    name: 'query_database',
    description: 'Execute database queries',
    input_schema: {
      type: 'object',
      properties: {
        query: { type: 'string' },
        parameters: { type: 'object' }
      },
      required: ['query']
    }
  },
  http_request: {
    name: 'http_request',
    description: 'Make HTTP requests to external APIs',
    input_schema: {
      type: 'object',
      properties: {
        url: { type: 'string', format: 'uri' },
        method: { type: 'string', enum: ['GET', 'POST', 'PUT', 'DELETE'] },
        headers: { type: 'object' },
        body: { type: 'object' }
      },
      required: ['url', 'method']
    }
  }
};

export const CapabilitiesBuilder: React.FC<CapabilitiesBuilderProps> = ({
  capabilities,
  inputSchema,
  onChange
}) => {
  const { toast } = useToast();
  const [expandedCapabilities, setExpandedCapabilities] = useState<Set<string>>(new Set());

  const addCapability = (template?: keyof typeof CAPABILITY_TEMPLATES) => {
    const newCapability = template 
      ? CAPABILITY_TEMPLATES[template].name
      : `capability_${capabilities.length + 1}`;
    
    const newCapabilities = [...capabilities, newCapability];
    const newSchema = { ...inputSchema };
    
    if (template) {
      newSchema[newCapability] = CAPABILITY_TEMPLATES[template].input_schema;
    } else {
      newSchema[newCapability] = {
        type: 'object',
        properties: {},
        required: []
      };
    }
    
    onChange(newCapabilities, newSchema);
    setExpandedCapabilities(new Set([...expandedCapabilities, newCapability]));
  };

  const removeCapability = (capabilityName: string) => {
    const newCapabilities = capabilities.filter(cap => cap !== capabilityName);
    const newSchema = { ...inputSchema };
    delete newSchema[capabilityName];
    
    onChange(newCapabilities, newSchema);
    setExpandedCapabilities(new Set([...expandedCapabilities].filter(cap => cap !== capabilityName)));
  };

  const updateCapabilitySchema = (capabilityName: string, schema: string) => {
    try {
      const parsedSchema = JSON.parse(schema);
      const newSchema = { ...inputSchema };
      newSchema[capabilityName] = parsedSchema;
      onChange(capabilities, newSchema);
    } catch (error) {
      toast({
        title: "Erro no JSON",
        description: "O schema JSON é inválido.",
        variant: "destructive"
      });
    }
  };

  const testSchema = (capabilityName: string) => {
    try {
      const schema = inputSchema[capabilityName];
      if (!schema) return;
      
      // Basic validation
      if (typeof schema !== 'object' || !schema.type) {
        throw new Error('Schema deve ter propriedade "type"');
      }
      
      toast({
        title: "Schema válido",
        description: "O schema JSON está correto.",
      });
    } catch (error) {
      toast({
        title: "Erro no schema",
        description: error instanceof Error ? error.message : "Schema inválido",
        variant: "destructive"
      });
    }
  };

  const toggleCapability = (capabilityName: string) => {
    const newExpanded = new Set(expandedCapabilities);
    if (newExpanded.has(capabilityName)) {
      newExpanded.delete(capabilityName);
    } else {
      newExpanded.add(capabilityName);
    }
    setExpandedCapabilities(newExpanded);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Capacidades do Agente ({capabilities.length})</CardTitle>
            <div className="flex items-center space-x-2">
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => addCapability()}
              >
                <Plus className="h-4 w-4 mr-2" />
                Nova Capacidade
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Quick Templates */}
          <div className="mb-6">
            <Label className="text-sm font-medium">Templates Rápidos</Label>
            <div className="flex flex-wrap gap-2 mt-2">
              {Object.keys(CAPABILITY_TEMPLATES).map((template) => (
                <Button
                  key={template}
                  size="sm"
                  variant="outline"
                  onClick={() => addCapability(template as keyof typeof CAPABILITY_TEMPLATES)}
                >
                  {template.replace('_', ' ')}
                </Button>
              ))}
            </div>
          </div>

          <Separator className="my-4" />

          {/* Capabilities List */}
          <div className="space-y-4">
            {capabilities.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>Nenhuma capacidade adicionada ainda.</p>
                <p className="text-sm">Use os templates acima ou crie uma nova capacidade.</p>
              </div>
            ) : (
              capabilities.map((capabilityName) => (
                <Card key={capabilityName} className="border">
                  <Collapsible
                    open={expandedCapabilities.has(capabilityName)}
                    onOpenChange={() => toggleCapability(capabilityName)}
                  >
                    <CollapsibleTrigger asChild>
                      <CardHeader className="cursor-pointer hover:bg-muted/50">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Badge variant="secondary">{capabilityName}</Badge>
                            <span className="text-sm text-muted-foreground">
                              {CAPABILITY_TEMPLATES[capabilityName as keyof typeof CAPABILITY_TEMPLATES]?.description || 'Capacidade customizada'}
                            </span>
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              removeCapability(capabilityName);
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>
                    
                    <CollapsibleContent>
                      <CardContent className="pt-0">
                        <div className="space-y-4">
                          <div>
                            <Label className="text-sm font-medium">Input Schema (JSON)</Label>
                            <Textarea
                              value={JSON.stringify(inputSchema[capabilityName] || {}, null, 2)}
                              onChange={(e) => updateCapabilitySchema(capabilityName, e.target.value)}
                              rows={10}
                              className="font-mono text-sm"
                              placeholder="Cole ou edite o JSON Schema aqui..."
                            />
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => testSchema(capabilityName)}
                            >
                              <TestTube className="h-4 w-4 mr-2" />
                              Validar Schema
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </CollapsibleContent>
                  </Collapsible>
                </Card>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
