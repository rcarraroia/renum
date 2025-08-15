
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { mockTeamApi } from '@/services/mockApi';
import { SystemHealth } from '@/types/team';
import { useToast } from '@/hooks/use-toast';
import { 
  Activity, 
  Database, 
  Wifi, 
  Server, 
  RefreshCw, 
  CheckCircle, 
  AlertTriangle, 
  XCircle 
} from 'lucide-react';

export function SystemHealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastCheck, setLastCheck] = useState<Date>(new Date());
  const { toast } = useToast();

  useEffect(() => {
    fetchSystemHealth();
    const interval = setInterval(fetchSystemHealth, 30000); // Auto-refresh a cada 30s
    return () => clearInterval(interval);
  }, []);

  const fetchSystemHealth = async () => {
    try {
      const healthData = await mockTeamApi.getSystemHealth();
      setHealth(healthData);
      setLastCheck(new Date());
    } catch (error) {
      console.error('Error fetching system health:', error);
      toast({
        title: "Erro",
        description: "Não foi possível verificar a saúde do sistema",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'degraded':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'down':
      case 'unhealthy':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return 'secondary';
      case 'degraded':
        return 'outline';
      case 'down':
      case 'unhealthy':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return 'Saudável';
      case 'degraded':
        return 'Degradado';
      case 'down':
      case 'unhealthy':
        return 'Indisponível';
      default:
        return status;
    }
  };

  const getLatencyColor = (latency: number) => {
    if (latency < 50) return 'text-green-600';
    if (latency < 100) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getLatencyLevel = (latency: number) => {
    if (latency < 50) return 'Excelente';
    if (latency < 100) return 'Bom';
    if (latency < 200) return 'Regular';
    return 'Ruim';
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Saúde do Sistema</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4].map((i) => (
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

  if (!health) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Saúde do Sistema</h1>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <XCircle className="h-12 w-12 text-red-500 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Erro ao carregar dados</h3>
            <p className="text-muted-foreground text-center mb-4">
              Não foi possível verificar a saúde do sistema
            </p>
            <Button onClick={fetchSystemHealth}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Tentar Novamente
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Saúde do Sistema</h1>
          <p className="text-muted-foreground">
            Monitore o status dos componentes do sistema
          </p>
        </div>
        <Button onClick={fetchSystemHealth} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          Atualizar
        </Button>
      </div>

      {/* Status geral */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {getStatusIcon(health.status)}
              <div>
                <CardTitle className="text-xl">Status Geral</CardTitle>
                <CardDescription>
                  Última verificação: {lastCheck.toLocaleString('pt-BR')}
                </CardDescription>
              </div>
            </div>
            <Badge variant={getStatusColor(health.status)} className="text-base px-3 py-1">
              {getStatusLabel(health.status)}
            </Badge>
          </div>
        </CardHeader>
      </Card>

      {/* Serviços */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Database */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5 text-muted-foreground" />
                <CardTitle className="text-base">Database</CardTitle>
              </div>
              {getStatusIcon(health.services.database.status)}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Badge variant={getStatusColor(health.services.database.status)}>
                {getStatusLabel(health.services.database.status)}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Latência:</span>
              <span className={`text-sm font-medium ${getLatencyColor(health.services.database.latency_ms)}`}>
                {health.services.database.latency_ms}ms
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              {getLatencyLevel(health.services.database.latency_ms)}
            </div>
          </CardContent>
        </Card>

        {/* Suna Backend */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Server className="h-5 w-5 text-muted-foreground" />
                <CardTitle className="text-base">Suna Backend</CardTitle>
              </div>
              {getStatusIcon(health.services.suna_backend.status)}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Badge variant={getStatusColor(health.services.suna_backend.status)}>
                {getStatusLabel(health.services.suna_backend.status)}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Latência:</span>
              <span className={`text-sm font-medium ${getLatencyColor(health.services.suna_backend.latency_ms)}`}>
                {health.services.suna_backend.latency_ms}ms
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              {getLatencyLevel(health.services.suna_backend.latency_ms)}
            </div>
          </CardContent>
        </Card>

        {/* WebSocket */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Wifi className="h-5 w-5 text-muted-foreground" />
                <CardTitle className="text-base">WebSocket</CardTitle>
              </div>
              {getStatusIcon(health.services.websocket.status)}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Badge variant={getStatusColor(health.services.websocket.status)}>
                {getStatusLabel(health.services.websocket.status)}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Conexões:</span>
              <span className="text-sm font-medium">
                {health.services.websocket.connections}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Conexões ativas
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Métricas detalhadas */}
      <Card>
        <CardHeader>
          <CardTitle>Métricas de Performance</CardTitle>
          <CardDescription>
            Desempenho dos componentes do sistema
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Database Response Time</span>
              <span className={getLatencyColor(health.services.database.latency_ms)}>
                {health.services.database.latency_ms}ms
              </span>
            </div>
            <Progress 
              value={Math.min((health.services.database.latency_ms / 200) * 100, 100)} 
              className="h-2"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Suna Backend Response Time</span>
              <span className={getLatencyColor(health.services.suna_backend.latency_ms)}>
                {health.services.suna_backend.latency_ms}ms
              </span>
            </div>
            <Progress 
              value={Math.min((health.services.suna_backend.latency_ms / 200) * 100, 100)} 
              className="h-2"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>WebSocket Connections</span>
              <span className="font-medium">
                {health.services.websocket.connections}
              </span>
            </div>
            <Progress 
              value={Math.min((health.services.websocket.connections / 100) * 100, 100)} 
              className="h-2"
            />
          </div>
        </CardContent>
      </Card>

      {/* Informações adicionais */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Dicas de Performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>• Mantenha as conexões WebSocket abaixo de 50 para melhor performance</p>
            <p>• Latência de database abaixo de 50ms é considerada excelente</p>
            <p>• Verifique a conectividade com o Suna Backend regularmente</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Status dos Alertas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>Todos os serviços operando normalmente</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>Nenhum alerta crítico ativo</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>Performance dentro dos parâmetros</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
