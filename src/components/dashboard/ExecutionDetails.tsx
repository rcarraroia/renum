
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { TeamExecution } from '@/types/team';
import { CheckCircle, XCircle, Clock, AlertCircle, Play } from 'lucide-react';

interface ExecutionDetailsProps {
  execution: TeamExecution;
  teamName: string;
  onClose: () => void;
}

export function ExecutionDetails({ execution, teamName, onClose }: ExecutionDetailsProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running': return <Play className="h-4 w-4 text-blue-500" />;
      default: return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'default';
      case 'completed': return 'secondary';
      case 'failed': return 'destructive';
      case 'cancelled': return 'outline';
      default: return 'outline';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'running': return 'Em Execução';
      case 'completed': return 'Concluída';
      case 'failed': return 'Falhou';
      case 'cancelled': return 'Cancelada';
      default: return status;
    }
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'error': return <XCircle className="h-3 w-3 text-red-500" />;
      case 'warning': return <AlertCircle className="h-3 w-3 text-yellow-500" />;
      default: return <CheckCircle className="h-3 w-3 text-blue-500" />;
    }
  };

  const progressPercentage = Math.round(
    (execution.progress.completed_agents / execution.progress.total_agents) * 100
  );

  const executionDuration = execution.completed_at 
    ? new Date(execution.completed_at).getTime() - new Date(execution.started_at).getTime()
    : Date.now() - new Date(execution.started_at).getTime();

  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold">{teamName}</h2>
          <p className="text-muted-foreground">
            Execução: {execution.execution_id}
          </p>
        </div>
        <Badge variant={getStatusColor(execution.status)}>
          {getStatusLabel(execution.status)}
        </Badge>
      </div>

      {/* Métricas principais */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              {getStatusIcon(execution.status)}
              <div>
                <p className="text-sm font-medium">Status</p>
                <p className="text-xs text-muted-foreground">
                  {getStatusLabel(execution.status)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Duração</p>
                <p className="text-xs text-muted-foreground">
                  {formatDuration(executionDuration)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Play className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Progresso</p>
                <p className="text-xs text-muted-foreground">
                  {execution.progress.completed_agents}/{execution.progress.total_agents} agentes
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Concluídos</p>
                <p className="text-xs text-muted-foreground">
                  {progressPercentage}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Barra de progresso */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Progresso da Execução</CardTitle>
          <CardDescription>{execution.progress.current_step}</CardDescription>
        </CardHeader>
        <CardContent>
          <Progress value={progressPercentage} className="h-3" />
          <p className="text-sm text-muted-foreground mt-2">
            {execution.progress.completed_agents} de {execution.progress.total_agents} agentes concluídos
          </p>
        </CardContent>
      </Card>

      {/* Resultados dos agentes */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Resultados dos Agentes</h3>
        
        {execution.results.length === 0 ? (
          <Card>
            <CardContent className="flex items-center justify-center py-8">
              <p className="text-muted-foreground">Nenhum resultado disponível ainda</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {execution.results.map((result, index) => (
              <Card key={result.agent_id}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">
                      Agente {index + 1}
                    </CardTitle>
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(result.status)}
                      <Badge variant={getStatusColor(result.status)}>
                        {getStatusLabel(result.status)}
                      </Badge>
                    </div>
                  </div>
                  <CardDescription>
                    ID: {result.agent_id}
                  </CardDescription>
                </CardHeader>
                
                <CardContent className="space-y-3">
                  {result.output && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                        Saída
                      </p>
                      <div className="p-3 bg-muted rounded-md">
                        <p className="text-sm">{result.output}</p>
                      </div>
                    </div>
                  )}
                  
                  {result.error_message && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                        Erro
                      </p>
                      <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                        <p className="text-sm text-red-700">{result.error_message}</p>
                      </div>
                    </div>
                  )}
                  
                  <div className="grid gap-3 md:grid-cols-2 text-sm">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Iniciado
                      </p>
                      <p>{new Date(result.started_at).toLocaleString('pt-BR')}</p>
                    </div>
                    
                    {result.completed_at && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Concluído
                        </p>
                        <p>{new Date(result.completed_at).toLocaleString('pt-BR')}</p>
                      </div>
                    )}
                    
                    {result.execution_time_ms && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Tempo de Execução
                        </p>
                        <p>{formatDuration(result.execution_time_ms)}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Logs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Logs da Execução</CardTitle>
          <CardDescription>
            Histórico detalhado da execução
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-64">
            <div className="space-y-2">
              {execution.logs.map((log, index) => (
                <div key={index} className="flex items-start space-x-3 text-sm">
                  {getLevelIcon(log.level)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-muted-foreground">
                        {new Date(log.timestamp).toLocaleTimeString('pt-BR')}
                      </span>
                      {log.agent_id && (
                        <Badge variant="outline" className="text-xs">
                          {log.agent_id}
                        </Badge>
                      )}
                    </div>
                    <p className="break-words">{log.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Rodapé */}
      <div className="flex justify-between items-center pt-4 border-t">
        <div className="text-sm text-muted-foreground">
          Iniciada em: {new Date(execution.started_at).toLocaleString('pt-BR')}
        </div>
        <Button onClick={onClose}>
          Fechar
        </Button>
      </div>
    </div>
  );
}
