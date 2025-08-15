
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import Typewriter from "@/components/Typewriter";

const Index = () => {
  const { user, initialized, loading } = useAuth();

  // Show minimal loading only while auth is initializing
  if (!initialized) {
    return (
      <div className="min-h-screen bg-renum-bg flex items-center justify-center">
        <Skeleton className="h-8 w-48" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-renum-bg">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-renum-primary/5 via-transparent to-purple-500/5" />
        
        <div className="relative container mx-auto px-4 py-20 lg:py-32">
          <div className="text-center space-y-8 max-w-4xl mx-auto">
            <h1 className="text-5xl lg:text-7xl font-bold">
              <span className="bg-gradient-to-r from-renum-primary to-purple-600 bg-clip-text text-transparent">
                Renum Builder
              </span>
            </h1>
            
            <div className="text-xl lg:text-2xl text-renum-fg/80 min-h-[2em] flex items-center justify-center">
              <Typewriter 
                texts={[
                  "Plataforma completa para criação e gerenciamento de equipes",
                  "Controle total dos seus projetos em tempo real",
                  "Colaboração eficiente para times de alta performance"
                ]}
                speed={80}
                pause={2000}
              />
            </div>

            <p className="text-lg text-renum-fg/60 max-w-2xl mx-auto leading-relaxed">
              Transforme a forma como sua equipe trabalha com ferramentas poderosas 
              para gestão de projetos e colaboração em tempo real.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mt-12">
              {user ? (
                <div className="space-y-4 text-center">
                  <p className="text-lg">
                    Bem-vindo de volta, <span className="font-semibold text-renum-primary">{user.name || user.email}</span>!
                  </p>
                  <Button 
                    className="btn btn-primary text-lg px-8 py-4 h-auto"
                    disabled
                  >
                    Acessar Dashboard
                    <span className="ml-2 text-sm opacity-70">(Em breve)</span>
                  </Button>
                </div>
              ) : (
                <>
                  <Button asChild className="btn btn-primary text-lg px-8 py-4 h-auto">
                    <Link to="/auth">
                      Começar Agora
                      <span className="ml-2">→</span>
                    </Link>
                  </Button>
                  <Button variant="outline" className="btn btn-secondary text-lg px-8 py-4 h-auto">
                    <Link to="#features">
                      Conhecer Recursos
                    </Link>
                  </Button>
                </>
              )}
            </div>

            {!user && (
              <p className="text-sm text-renum-fg/50 mt-4">
                Crie uma conta gratuita e explore todas as funcionalidades
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-gradient-to-b from-transparent to-renum-primary/5">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-renum-fg mb-4">
              Recursos Poderosos
            </h2>
            <p className="text-lg text-renum-fg/60 max-w-2xl mx-auto">
              Tudo que você precisa para levar sua equipe ao próximo nível
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 max-w-6xl mx-auto">
            <div className="bg-white rounded-2xl p-8 shadow-subtle hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="w-12 h-12 bg-renum-primary/10 rounded-lg flex items-center justify-center mb-6">
                <div className="w-6 h-6 bg-renum-primary rounded-sm"></div>
              </div>
              <h3 className="text-xl font-semibold text-renum-fg mb-3">
                Gerenciamento de Equipes
              </h3>
              <p className="text-renum-fg/60 leading-relaxed">
                Organize e gerencie suas equipes de forma eficiente. Crie equipes, 
                adicione membros e defina permissões de acesso.
              </p>
            </div>

            <div className="bg-white rounded-2xl p-8 shadow-subtle hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center mb-6">
                <div className="w-6 h-6 bg-purple-500 rounded-sm"></div>
              </div>
              <h3 className="text-xl font-semibold text-renum-fg mb-3">
                Controle de Projetos
              </h3>
              <p className="text-renum-fg/60 leading-relaxed">
                Acompanhe o progresso dos seus projetos em tempo real. 
                Visualize métricas, relatórios e dashboards personalizados.
              </p>
            </div>

            <div className="bg-white rounded-2xl p-8 shadow-subtle hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="w-12 h-12 bg-indigo-500/10 rounded-lg flex items-center justify-center mb-6">
                <div className="w-6 h-6 bg-indigo-500 rounded-sm"></div>
              </div>
              <h3 className="text-xl font-semibold text-renum-fg mb-3">
                Colaboração
              </h3>
              <p className="text-renum-fg/60 leading-relaxed">
                Trabalhe em equipe de forma colaborativa. Compartilhe documentos, 
                mensagens e mantenha todos sincronizados.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Index;
