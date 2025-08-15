import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { Plus, Edit, Trash2, Play, Users, Settings } from 'lucide-react';
import { TeamForm } from './TeamForm';
import { TeamDetails } from './TeamDetails';
import { Team } from '@/types/team';
import { api } from '@/services/api';
import { useToast } from '@/hooks/use-toast';

export function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      setLoading(true);
      const data = await api.teams.list();
      setTeams(data.teams);
    } catch (error) {
      console.error('Error loading teams:', error);
      toast({
        title: 'Erro',
        description: error instanceof Error ? error.message : 'Falha ao carregar equipes',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async (teamData: Partial<Team>) => {
    try {
      const newTeam = await api.teams.create(teamData);
      setTeams(prev => [newTeam, ...prev]);
      setIsCreateDialogOpen(false);
      toast({
        title: 'Sucesso',
        description: 'Equipe criada com sucesso',
      });
    } catch (error) {
      console.error('Error creating team:', error);
      toast({
        title: 'Erro',
        description: error instanceof Error ? error.message : 'Falha ao criar equipe',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateTeam = async (teamData: Partial<Team>) => {
    if (!selectedTeam) return;
    
    try {
      const updatedTeam = await api.teams.update(selectedTeam.id, teamData);
      if (updatedTeam) {
        setTeams(prev => prev.map(team => 
          team.id === selectedTeam.id ? updatedTeam : team
        ));
      }
      setIsEditDialogOpen(false);
      setSelectedTeam(null);
      toast({
        title: 'Sucesso',
        description: 'Equipe atualizada com sucesso',
      });
    } catch (error) {
      console.error('Error updating team:', error);
      toast({
        title: 'Erro',
        description: error instanceof Error ? error.message : 'Falha ao atualizar equipe',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteTeam = async (teamId: string) => {
    try {
      await api.teams.delete(teamId);
      setTeams(prev => prev.filter(team => team.id !== teamId));
      toast({
        title: 'Sucesso',
        description: 'Equipe excluída com sucesso',
      });
    } catch (error) {
      console.error('Error deleting team:', error);
      toast({
        title: 'Erro',
        description: error instanceof Error ? error.message : 'Falha ao excluir equipe',
        variant: 'destructive',
      });
    }
  };

  const handleExecuteTeam = async (teamId: string) => {
    try {
      const execution = await api.teams.execute(teamId, { 
        initial_prompt: 'Executar equipe via dashboard' 
      });
      toast({
        title: 'Execução Iniciada',
        description: `Execução ${execution.execution_id} iniciada com sucesso`,
      });
    } catch (error) {
      console.error('Error executing team:', error);
      toast({
        title: 'Erro',
        description: error instanceof Error ? error.message : 'Falha ao executar equipe',
        variant: 'destructive',
      });
    }
  };

  const getWorkflowTypeLabel = (type: string) => {
    switch (type) {
      case 'sequential': return 'Sequencial';
      case 'parallel': return 'Paralelo';
      case 'conditional': return 'Condicional';
      case 'pipeline': return 'Pipeline';
      default: return type;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
      case 'inactive': return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
      case 'archived': return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active': return 'Ativa';
      case 'inactive': return 'Inativa';
      case 'archived': return 'Arquivada';
      default: return status;
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Equipes</h1>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-muted rounded w-3/4"></div>
                <div className="h-3 bg-muted rounded w-1/2"></div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-3 bg-muted rounded"></div>
                  <div className="h-3 bg-muted rounded w-2/3"></div>
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
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Equipes</h1>
          <p className="text-muted-foreground">
            Gerencie suas equipes de agentes IA
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nova Equipe
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Criar Nova Equipe</DialogTitle>
            </DialogHeader>
            <TeamForm
              onSubmit={handleCreateTeam}
              onCancel={() => setIsCreateDialogOpen(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {teams.length === 0 ? (
        <Card className="p-8 text-center">
          <div className="mx-auto w-12 h-12 bg-muted rounded-lg flex items-center justify-center mb-4">
            <Users className="h-6 w-6 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Nenhuma equipe encontrada</h3>
          <p className="text-muted-foreground mb-4">
            Crie sua primeira equipe de agentes IA para começar
          </p>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Criar Primeira Equipe
          </Button>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => (
            <Card key={team.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">{team.name}</CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {getWorkflowTypeLabel(team.workflow_type)}
                      </Badge>
                      <Badge className={`text-xs ${getStatusColor(team.status)}`}>
                        {getStatusLabel(team.status)}
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {team.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {team.description}
                    </p>
                  )}
                  
                  <div className="flex items-center text-sm text-muted-foreground">
                    <Users className="h-4 w-4 mr-1" />
                    {team.agents_count} agente{team.agents_count !== 1 ? 's' : ''}
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedTeam(team);
                          setIsDetailsDialogOpen(true);
                        }}
                      >
                        <Settings className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedTeam(team);
                          setIsEditDialogOpen(true);
                        }}
                      >
                        <Edit className="h-3 w-3" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Excluir Equipe</AlertDialogTitle>
                            <AlertDialogDescription>
                              Tem certeza que deseja excluir a equipe "{team.name}"? 
                              Esta ação não pode ser desfeita.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancelar</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDeleteTeam(team.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              Excluir
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                    <Button 
                      size="sm"
                      onClick={() => handleExecuteTeam(team.id)}
                      disabled={team.status !== 'active'}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      Executar
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Team Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Editar Equipe</DialogTitle>
          </DialogHeader>
          {selectedTeam && (
            <TeamForm
              initialData={selectedTeam}
              onSubmit={handleUpdateTeam}
              onCancel={() => {
                setIsEditDialogOpen(false);
                setSelectedTeam(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Team Details Dialog */}
      <Dialog open={isDetailsDialogOpen} onOpenChange={setIsDetailsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Detalhes da Equipe</DialogTitle>
          </DialogHeader>
          {selectedTeam && (
            <TeamDetails 
              team={selectedTeam}
              onClose={() => {
                setIsDetailsDialogOpen(false);
                setSelectedTeam(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
