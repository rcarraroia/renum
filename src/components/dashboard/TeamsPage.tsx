
import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Play, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { mockTeamApi } from '@/services/mockApi';
import { Team } from '@/types/team';
import { TeamForm } from '@/components/dashboard/TeamForm';
import { TeamDetails } from '@/components/dashboard/TeamDetails';
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
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      setLoading(true);
      const response = await mockTeamApi.getTeams();
      setTeams(response.teams);
    } catch (error) {
      console.error('Error fetching teams:', error);
      toast({
        title: "Erro",
        description: "Não foi possível carregar as equipes",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async (teamData: Partial<Team>) => {
    try {
      const newTeam = await mockTeamApi.createTeam(teamData);
      setTeams(prev => [...prev, newTeam]);
      setIsCreateDialogOpen(false);
      toast({
        title: "Sucesso",
        description: "Equipe criada com sucesso!",
      });
    } catch (error) {
      console.error('Error creating team:', error);
      toast({
        title: "Erro",
        description: "Não foi possível criar a equipe",
        variant: "destructive",
      });
    }
  };

  const handleUpdateTeam = async (teamData: Partial<Team>) => {
    if (!selectedTeam) return;

    try {
      const updatedTeam = await mockTeamApi.updateTeam(selectedTeam.id, teamData);
      if (updatedTeam) {
        setTeams(prev => prev.map(team => 
          team.id === selectedTeam.id ? updatedTeam : team
        ));
        setIsEditDialogOpen(false);
        setSelectedTeam(null);
        toast({
          title: "Sucesso",
          description: "Equipe atualizada com sucesso!",
        });
      }
    } catch (error) {
      console.error('Error updating team:', error);
      toast({
        title: "Erro",
        description: "Não foi possível atualizar a equipe",
        variant: "destructive",
      });
    }
  };

  const handleDeleteTeam = async (teamId: string) => {
    if (!confirm('Tem certeza que deseja excluir esta equipe?')) return;

    try {
      const success = await mockTeamApi.deleteTeam(teamId);
      if (success) {
        setTeams(prev => prev.filter(team => team.id !== teamId));
        toast({
          title: "Sucesso",
          description: "Equipe excluída com sucesso!",
        });
      }
    } catch (error) {
      console.error('Error deleting team:', error);
      toast({
        title: "Erro",
        description: "Não foi possível excluir a equipe",
        variant: "destructive",
      });
    }
  };

  const handleExecuteTeam = async (teamId: string) => {
    try {
      const execution = await mockTeamApi.executeTeam(teamId, {
        prompt: "Iniciar execução manual"
      });
      toast({
        title: "Execução Iniciada",
        description: `Execução ${execution.execution_id} foi iniciada com sucesso!`,
      });
    } catch (error) {
      console.error('Error executing team:', error);
      toast({
        title: "Erro",
        description: "Não foi possível iniciar a execução",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Equipes</h1>
          <Button disabled>
            <Plus className="mr-2 h-4 w-4" />
            Nova Equipe
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-24 bg-muted rounded"></div>
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
          <h1 className="text-3xl font-bold">Equipes</h1>
          <p className="text-muted-foreground">
            Gerencie suas equipes de agentes
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Nova Equipe
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Criar Nova Equipe</DialogTitle>
              <DialogDescription>
                Configure uma nova equipe de agentes
              </DialogDescription>
            </DialogHeader>
            <TeamForm onSubmit={handleCreateTeam} onCancel={() => setIsCreateDialogOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {teams.map((team) => (
          <Card key={team.id} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{team.name}</CardTitle>
                <Badge variant={team.status === 'active' ? 'default' : 'secondary'}>
                  {team.status}
                </Badge>
              </div>
              <CardDescription>
                {team.description || 'Sem descrição'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Agentes:</span>
                  <span className="font-medium">{team.agents_count}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Workflow:</span>
                  <span className="font-medium capitalize">{team.workflow_type}</span>
                </div>
                
                <div className="flex space-x-2 pt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedTeam(team);
                      setIsDetailsDialogOpen(true);
                    }}
                  >
                    <Eye className="h-3 w-3 mr-1" />
                    Ver
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedTeam(team);
                      setIsEditDialogOpen(true);
                    }}
                  >
                    <Edit className="h-3 w-3 mr-1" />
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleExecuteTeam(team.id)}
                    className="bg-renum-primary hover:bg-renum-primary/90"
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Executar
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleDeleteTeam(team.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {teams.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Users className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Nenhuma equipe encontrada</h3>
            <p className="text-muted-foreground text-center mb-4">
              Crie sua primeira equipe de agentes para começar
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Criar Primeira Equipe
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Dialog para editar equipe */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Editar Equipe</DialogTitle>
            <DialogDescription>
              Atualize as configurações da equipe
            </DialogDescription>
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

      {/* Dialog para detalhes da equipe */}
      <Dialog open={isDetailsDialogOpen} onOpenChange={setIsDetailsDialogOpen}>
        <DialogContent className="max-w-3xl">
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
