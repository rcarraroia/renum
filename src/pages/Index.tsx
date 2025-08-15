
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";

const Index = () => {
  const { user, initialized, loading } = useAuth();

  // Show loading skeleton while auth is initializing
  if (!initialized) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="space-y-4 w-full max-w-2xl px-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-4 w-3/4 mx-auto" />
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col">
      <main className="flex-1">
        <div className="container mx-auto px-4 py-16">
          <div className="text-center space-y-6 mb-16">
            <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Renum Builder
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Plataforma completa para criação e gerenciamento de equipes e projetos
            </p>
            
            {user ? (
              <div className="space-y-4">
                <p className="text-lg">
                  Bem-vindo de volta, <span className="font-semibold">{user.name || user.email}</span>!
                </p>
                <Button size="lg" disabled>
                  Acessar Dashboard (Em breve)
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <Button asChild size="lg">
                  <Link to="/auth">Começar Agora</Link>
                </Button>
                <p className="text-sm text-muted-foreground">
                  Crie uma conta gratuita e explore todas as funcionalidades
                </p>
              </div>
            )}
          </div>

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 max-w-6xl mx-auto">
            <Card>
              <CardHeader>
                <CardTitle>Gerenciamento de Equipes</CardTitle>
                <CardDescription>
                  Organize e gerencie suas equipes de forma eficiente
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Crie equipes, adicione membros e defina permissões de acesso.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Controle de Projetos</CardTitle>
                <CardDescription>
                  Acompanhe o progresso dos seus projetos em tempo real
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Visualize métricas, relatórios e dashboards personalizados.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Colaboração</CardTitle>
                <CardDescription>
                  Trabalhe em equipe de forma colaborativa
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Compartilhe documentos, mensagens e mantenha todos sincronizados.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Index;
