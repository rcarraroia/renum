
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Users, Play, Activity, Clock } from 'lucide-react';
import { mockTeamApi } from '@/services/mockApi';
import { Team, TeamExecution } from '@/types/team';

export function DashboardOverview() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [executions, setExecutions] = useState<TeamExecution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [teamsResponse, executionsResponse] = await Promise.all([
          mockTeamApi.getTeams(),
          mockTeamApi.getExecutions()
        ]);
        setTeams(teamsResponse.teams);
        setExecutions(executionsResponse.executions);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const activeTeams = teams.filter(team => team.status === 'active').length;
  const runningExecutions = executions.filter(exec => exec.status === 'running').length;
  const completedExecutions = executions.filter(exec => exec.status === 'completed').length;

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Visão geral das suas equipes e execuções
        </p>
      </div>

      {/* Métricas principais */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Equipes Ativas
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeTeams}</div>
            <p className="text-xs text-muted-foreground">
              {teams.length} equipes no total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Execuções em Andamento
            </CardTitle>
            <Play className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningExecutions}</div>
            <p className="text-xs text-muted-foreground">
              execuções ativas
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Execuções Concluídas
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{completedExecutions}</div>
            <p className="text-xs text-muted-foreground">
              nas últimas 24h
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Tempo Médio
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">15m</div>
            <p className="text-xs text-muted-foreground">
              por execução
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Lista de equipes recentes */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Equipes Recentes</CardTitle>
            <CardDescription>
              Suas equipes mais recentemente criadas
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {teams.slice(0, 3).map((team) => (
                <div key={team.id} className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {team.name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {team.agents_count} agentes • {team.workflow_type}
                    </p>
                  </div>
                  <Badge variant={team.status === 'active' ? 'default' : 'secondary'}>
                    {team.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Execuções Recentes</CardTitle>
            <CardDescription>
              Últimas execuções realizadas
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {executions.slice(0, 3).map((execution) => {
                const team = teams.find(t => t.id === execution.team_id);
                return (
                  <div key={execution.execution_id} className="flex items-center justify-between">
                    <div className="space-y-1">
                      <p className="text-sm font-medium leading-none">
                        {team?.name || 'Equipe não encontrada'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {execution.progress.completed_agents}/{execution.progress.total_agents} agentes
                      </p>
                    </div>
                    <Badge 
                      variant={
                        execution.status === 'running' ? 'default' :
                        execution.status === 'completed' ? 'secondary' :
                        execution.status === 'failed' ? 'destructive' : 'outline'
                      }
                    >
                      {execution.status}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
