import React from 'react';
import { Link } from 'react-router-dom';
import { Typewriter } from 'react-simple-typewriter';
import { Users, Activity, Zap } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function Index() {
  const { user, loading, initialized } = useAuth();

  // Loading state while auth initializes
  if (!initialized || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-muted/20 to-background">
        <div className="container mx-auto px-4 py-16">
          <div className="text-center">
            <div className="animate-pulse space-y-4">
              <div className="h-16 bg-muted rounded-lg mx-auto max-w-2xl"></div>
              <div className="h-8 bg-muted rounded mx-auto max-w-lg"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-muted/20 to-background">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center space-y-8">
          {/* Hero Section */}
          <div className="space-y-6">
            <div className="inline-block">
              <div className="bg-renum-primary/10 text-renum-primary px-4 py-2 rounded-full text-sm font-medium border border-renum-primary/20">
                ✨ Powered by AI Agents
              </div>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold bg-gradient-to-r from-foreground via-renum-primary to-foreground bg-clip-text text-transparent leading-tight">
              <Typewriter 
                words={[
                  "Automatize com IA",
                  "Crie Equipes Inteligentes", 
                  "Otimize Processos",
                  "Renum - AI Teams"
                ]}
                loop={true}
                cursor={true}
                cursorStyle="|"
                typeSpeed={100}
                deleteSpeed={50}
                delaySpeed={2000}
              />
            </h1>
            
            <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
              {user ? (
                <>Bem-vindo de volta, <span className="text-renum-primary font-medium">{user.email}</span>! 
                Gerencie suas equipes de IA e monitore execuções em tempo real.</>
              ) : (
                <>Crie equipes de agentes de IA que trabalham juntos para automatizar 
                seus processos e aumentar sua produtividade.</>
              )}
            </p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            {user ? (
              <>
                <Link 
                  to="/dashboard" 
                  className="btn-primary text-lg px-8 py-4 rounded-xl hover:scale-105 transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  Acessar Dashboard
                </Link>
                <Link 
                  to="/dashboard/teams" 
                  className="btn-secondary text-lg px-8 py-4 rounded-xl hover:scale-105 transition-all duration-200"
                >
                  Gerenciar Equipes
                </Link>
              </>
            ) : (
              <>
                <Link 
                  to="/auth" 
                  className="btn-primary text-lg px-8 py-4 rounded-xl hover:scale-105 transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  Começar Agora
                </Link>
                <a 
                  href="#features" 
                  className="btn-secondary text-lg px-8 py-4 rounded-xl hover:scale-105 transition-all duration-200"
                >
                  Saiba Mais
                </a>
              </>
            )}
          </div>

          {/* Features Preview */}
          <div className="mt-20 grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <div className="p-6 rounded-2xl bg-card border border-border hover:shadow-lg transition-all duration-300 hover:scale-105">
              <div className="w-12 h-12 bg-renum-primary/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                <Users className="h-6 w-6 text-renum-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Equipes Inteligentes</h3>
              <p className="text-muted-foreground">
                Configure equipes de agentes IA com diferentes papéis e workflows
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-card border border-border hover:shadow-lg transition-all duration-300 hover:scale-105">
              <div className="w-12 h-12 bg-renum-primary/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                <Activity className="h-6 w-6 text-renum-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Monitoramento</h3>
              <p className="text-muted-foreground">
                Acompanhe execuções em tempo real com logs detalhados
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-card border border-border hover:shadow-lg transition-all duration-300 hover:scale-105">
              <div className="w-12 h-12 bg-renum-primary/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                <Zap className="h-6 w-6 text-renum-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Automação</h3>
              <p className="text-muted-foreground">
                Automatize processos complexos com workflows inteligentes
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
