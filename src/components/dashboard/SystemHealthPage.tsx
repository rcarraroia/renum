
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { api } from '@/services/api';
import { SystemHealth } from '@/types/team';
import { useToast } from '@/hooks/use-toast';
import { CheckCircle, XCircle, AlertCircle, RefreshCw, Database, Server, Wifi } from 'lucide-react';

export function SystemHealthPage() {
  const [healthData, setHealthData] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    fetchHealthData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchHealthData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchHealthData = async () => {
    try {
      setLoading(true);
      const data = await api.system.health();
      setHealthData(data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Error fetching system health:', error);
      toast({
        title: "Erro",
        description: error instanceof Error ? error.message : "Não foi possível obter o status do sistema",
        variant: "destructive",
      });
      
      // Set default error state
      setHealthData({
        status: 'down',
        services: {
          database: { status: 'unhealthy', latency_ms: 0 },
          suna_backend: { status: 'unhealthy', latency_ms: 0 },
          websocket: { status: 'unhealthy', connections: 0 }
        }
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
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'unhealthy':
      case 'down':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return <Badge className="bg-green-100 text-green-800">Saudável</Badge>;
      case 'degraded':
        return <Badge className="bg-yellow-100 text-yellow-800">Degradado</Badge>;
      case 'unhealthy':
      case 'down':
        return <Badge variant="destructive">Indisponível</Badge>;
      default:
        return <Badge variant="outline">Desconhecido</Badge>;
    }
  };

  const getLatencyColor = (latency: number) => {
    if (latency < 100) return 'text-green-600';
    if (latency < 300) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getLatencyProgress = (latency: number) => {
    // Convert latency to a percentage (0-1000ms scale)
    return Math.min((latency / 1000) * 100, 100);
  };

  if (loading && !healthData) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Saúde do Sistema</h1>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-muted rounded w-3/4"></div>
                <div className="h-3 bg-muted rounded w-1/2"></div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-3 bg-muted rounded"></div>
                  <div className="h-2 bg-muted rounded"></div>
                </div>
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
          <h1 className="text-3xl font-bold">Saúde do Sistema</h1>
          <p className="text-muted-foreground">
            Monitore o status dos serviços do Renum
          </p>
          {lastUpdated && (
            <p className="text-xs text-muted-foreground mt-1">
              Última atualização: {lastUpdated.toLocaleString('pt-BR')}
            </p>
          )}
        </div>
        <Button onClick={fetchHealthData} variant="outline" disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </div>

      {/* Status Geral */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {getStatusIcon(healthData?.status || 'down')}
              <CardTitle>Status Geral do Sistema</CardTitle>
            </div>
            {getStatusBadge(healthData?.status || 'down')}
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            {healthData?.status === 'ok' && 'Todos os serviços estão funcionando normalmente.'}
            {healthData?.status === 'degraded' && 'Alguns serviços estão com performance reduzida.'}
            {healthData?.status === 'down' && 'Um ou mais serviços estão indisponíveis.'}
          </p>
        </CardContent>
      </Card>

      {/* Status dos Serviços */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Database */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5 text-blue-500" />
                <CardTitle className="text-lg">Database</CardTitle>
              </div>
              {getStatusBadge(healthData?.services.database.status || 'unhealthy')}
            </div>
            <CardDescription>Sistema de banco de dados</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Latência</span>
                <span className={getLatencyColor(healthData?.services.database.latency_ms || 0)}>
                  {healthData?.services.database.latency_ms || 0}ms
                </span>
              </div>
              <Progress 
                value={getLatencyProgress(healthData?.services.database.latency_ms || 0)} 
                className="h-2"
              />
            </div>
          </CardContent>
        </Card>

        {/* Suna Backend */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Server className="h-5 w-5 text-purple-500" />
                <CardTitle className="text-lg">Suna Backend</CardTitle>
              </div>
              {getStatusBadge(healthData?.services.suna_backend.status || 'unhealthy')}
            </div>
            <CardDescription>Serviço de execução de agentes</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Latência</span>
                <span className={getLatencyColor(healthData?.services.suna_backend.latency_ms || 0)}>
                  {healthData?.services.suna_backend.latency_ms || 0}ms
                </span>
              </div>
              <Progress 
                value={getLatencyProgress(healthData?.services.suna_backend.latency_ms || 0)} 
                className="h-2"
              />
            </div>
          </CardContent>
        </Card>

        {/* WebSocket */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Wifi className="h-5 w-5 text-green-500" />
                <CardTitle className="text-lg">WebSocket</CardTitle>
              </div>
              {getStatusBadge(healthData?.services.websocket.status || 'unhealthy')}
            </div>
            <CardDescription>Conexões em tempo real</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span>Conexões Ativas</span>
              <span className="font-medium">
                {healthData?.services.websocket.connections || 0}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Métricas Detalhadas */}
      <Card>
        <CardHeader>
          <CardTitle>Métricas Detalhadas</CardTitle>
          <CardDescription>Informações técnicas sobre o desempenho do sistema</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <h4 className="font-medium">Database</h4>
              <div className="text-sm text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span>{healthData?.services.database.status || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Latência:</span>
                  <span>{healthData?.services.database.latency_ms || 0}ms</span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium">Suna Backend</h4>
              <div className="text-sm text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span>{healthData?.services.suna_backend.status || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Latência:</span>
                  <span>{healthData?.services.suna_backend.latency_ms || 0}ms</span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium">WebSocket</h4>
              <div className="text-sm text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span>{healthData?.services.websocket.status || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Conexões:</span>
                  <span>{healthData?.services.websocket.connections || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
