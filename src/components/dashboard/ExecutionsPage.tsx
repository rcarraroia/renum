import React, { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { api } from '@/services/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { TeamExecution, Team } from '@/types/team';
import { ExecutionDetails } from '@/components/dashboard/ExecutionDetails';
import { useToast } from '@/hooks/use-toast';
import { Play, Square, Eye, RefreshCw, Wifi, WifiOff } from 'lucide-react';

export function ExecutionsPage() {
  const [executions, setExecutions] = useState<TeamExecution[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedExecution, setSelectedExecution] = useState<TeamExecution | null>(null);
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);
  const { toast } = useToast();

  // WebSocket para atualizações em tempo real
  const { 
    isConnected: wsConnected, 
    lastMessage, 
    connect: connectWs, 
    disconnect: disconnectWs 
  } = useWebSocket('/executions/stream');

  useEffect(() => {
    fetchData();
    // Conectar ao WebSocket para atualizações em tempo real
    connectWs();

    return () => {
      disconnectWs();
    };
  }, []);

  // Processar mensagens do WebSocket
  useEffect(() => {
    if (lastMessage) {
      console.log('Received WebSocket message:', lastMessage);
      
      switch (lastMessage.type) {
        case 'execution_started':
          setExecutions(prev => [lastMessage.data, ...prev]);
          toast({
            title: "Execução Iniciada",
            description: `Nova execução iniciada: ${lastMessage.data.execution_id}`,
          });
          break;
          
        case 'execution_updated':
          setExecutions(prev => prev.map(exec => 
            exec.execution_id === lastMessage.data.execution_id 
              ? { ...exec, ...lastMessage.data }
              : exec
          ));
          break;
          
        case 'execution_completed':
          setExecutions(prev => prev.map(exec => 
            exec.execution_id === lastMessage.data.execution_id 
              ? { ...exec, status: 'completed', completed_at: lastMessage.data.completed_at }
              : exec
          ));
          toast({
            title: "Execução Concluída",
            description: `Execução ${lastMessage.data.execution_id} foi concluída`,
          });
          break;
          
        case 'execution_failed':
          setExecutions(prev => prev.map(exec => 
            exec.execution_id === lastMessage.data.execution_id 
              ? { ...exec, status: 'failed' }
              : exec
          ));
          toast({
            title: "Execução Falhou",
            description: `Execução ${lastMessage.data.execution_id} falhou`,
            variant: "destructive",
          });
          break;
          
        default:
          console.log('Unknown WebSocket message type:', lastMessage.type);
      }
    }
  }, [lastMessage, toast]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [executionsResponse, teamsResponse] = await Promise.all([
        api.executions.list(),
        api.teams.list()
      ]);
      setExecutions(executionsResponse.executions);
      setTeams(teamsResponse.teams);
    } catch (error) {
      console.error('Error fetching executions:', error);
      toast({
        title: "Erro",
        description: error instanceof Error ? error.message : "Não foi possível carregar as execuções",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancelExecution = async (executionId: string) => {
    if (!confirm('Tem certeza que deseja cancelar esta execução?')) return;

    try {
      const success = await api.executions.cancel(executionId);
      if (success) {
        setExecutions(prev => prev.map(exec => 
          exec.execution_id === executionId 
            ? { ...exec, status: 'cancelled' as any }
            : exec
        ));
        toast({
          title: "Sucesso",
          description: "Execução cancelada com sucesso!",
        });
      }
    } catch (error) {
      console.error('Error cancelling execution:', error);
      toast({
        title: "Erro",
        description: error instanceof Error ? error.message : "Não foi possível cancelar a execução",
        variant: "destructive",
      });
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

  const getTeamName = (teamId: string) => {
    const team = teams.find(t => t.id === teamId);
    return team?.name || 'Equipe não encontrada';
  };

  const getProgressPercentage = (execution: TeamExecution) => {
    return Math.round((execution.progress.completed_agents / execution.progress.total_agents) * 100);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Execuções</h1>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-16 bg-muted rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Execuções</h1>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-muted-foreground">
              Monitore as execuções das suas equipes
            </p>
            <div className="flex items-center gap-1">
              {wsConnected ? (
                <Wifi className="h-4 w-4 text-green-500" />
              ) : (
                <WifiOff className="h-4 w-4 text-red-500" />
              )}
              <span className="text-xs text-muted-foreground">
                {wsConnected ? 'Conectado' : 'Desconectado'}
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={connectWs} variant="outline" size="sm" disabled={wsConnected}>
            <Wifi className="mr-2 h-4 w-4" />
            Conectar WebSocket
          </Button>
          <Button onClick={fetchData} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Atualizar
          </Button>
        </div>
      </div>

      {executions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Play className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Nenhuma execução encontrada</h3>
            <p className="text-muted-foreground text-center">
              Execute uma equipe para ver o status aqui
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {executions.map((execution) => (
            <Card key={execution.execution_id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">
                      {getTeamName(execution.team_id)}
                    </CardTitle>
                    <CardDescription>
                      ID: {execution.execution_id} • 
                      Iniciada em {new Date(execution.started_at).toLocaleString('pt-BR')}
                    </CardDescription>
                  </div>
                  <Badge variant={getStatusColor(execution.status)}>
                    {getStatusLabel(execution.status)}
                  </Badge>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* Progresso */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Progresso</span>
                    <span className="font-medium">
                      {execution.progress.completed_agents}/{execution.progress.total_agents} agentes
                    </span>
                  </div>
                  <Progress 
                    value={getProgressPercentage(execution)} 
                    className="h-2"
                  />
                  <p className="text-xs text-muted-foreground">
                    {execution.progress.current_step}
                  </p>
                </div>

                {/* Tempos */}
                <div className="grid gap-4 md:grid-cols-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Iniciada:</span>
                    <p className="font-medium">
                      {new Date(execution.started_at).toLocaleString('pt-BR')}
                    </p>
                  </div>
                  {execution.completed_at && (
                    <div>
                      <span className="text-muted-foreground">Concluída:</span>
                      <p className="font-medium">
                        {new Date(execution.completed_at).toLocaleString('pt-BR')}
                      </p>
                    </div>
                  )}
                  {execution.estimated_completion && execution.status === 'running' && (
                    <div>
                      <span className="text-muted-foreground">Previsão:</span>
                      <p className="font-medium">
                        {new Date(execution.estimated_completion).toLocaleString('pt-BR')}
                      </p>
                    </div>
                  )}
                </div>

                {/* Ações */}
                <div className="flex space-x-2 pt-2">
                  <Dialog open={isDetailsDialogOpen} onOpenChange={setIsDetailsDialogOpen}>
                    <DialogTrigger asChild>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setSelectedExecution(execution)}
                      >
                        <Eye className="h-3 w-3 mr-1" />
                        Ver Detalhes
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-4xl">
                      <DialogHeader>
                        <DialogTitle>Detalhes da Execução</DialogTitle>
                      </DialogHeader>
                      {selectedExecution && (
                        <ExecutionDetails 
                          execution={selectedExecution}
                          teamName={getTeamName(selectedExecution.team_id)}
                          onClose={() => {
                            setIsDetailsDialogOpen(false);
                            setSelectedExecution(null);
                          }}
                        />
                      )}
                    </DialogContent>
                  </Dialog>

                  {execution.status === 'running' && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleCancelExecution(execution.execution_id)}
                    >
                      <Square className="h-3 w-3 mr-1" />
                      Cancelar
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
