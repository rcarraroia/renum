
import React, { createContext, useContext, useEffect, useState } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';
import { api } from '@/services/api';
import { AuthContextType, AuthState, LoginCredentials, SignupCredentials } from '@/types/auth';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    session: null,
    loading: true,
    initialized: false,
  });

  useEffect(() => {
    // Set up auth state listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('Auth state changed:', event, session?.user?.email);
        
        let user = null;
        if (session?.user) {
          // Fetch user profile data
          const { data: profile } = await supabase
            .from('profiles')
            .select('name')
            .eq('id', session.user.id)
            .single();

          user = {
            id: session.user.id,
            email: session.user.email!,
            name: profile?.name || session.user.email!,
          };
        }

        setAuthState({
          user,
          session,
          loading: false,
          initialized: true,
        });
      }
    );

    // Check for existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!authState.initialized) {
        // Initial session check will be handled by onAuthStateChange
        return;
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const login = async (credentials: LoginCredentials): Promise<{ error?: string }> => {
    try {
      setAuthState(prev => ({ ...prev, loading: true }));
      
      // Tentar primeiro com a API do backend
      try {
        const backendResponse = await api.auth.login(credentials.email, credentials.password);
        console.log('Backend login successful:', backendResponse);
        
        // Se o backend retornar sucesso, fazer login no Supabase também
        const { error: supabaseError } = await supabase.auth.signInWithPassword({
          email: credentials.email,
          password: credentials.password,
        });

        if (supabaseError) {
          console.warn('Supabase login failed, but backend succeeded:', supabaseError);
          // Continuar mesmo se o Supabase falhar, pois o backend funcionou
        }

        return {};
      } catch (backendError) {
        console.log('Backend login failed, falling back to Supabase:', backendError);
        
        // Fallback para Supabase se o backend falhar
        const { error: supabaseError } = await supabase.auth.signInWithPassword({
          email: credentials.email,
          password: credentials.password,
        });

        if (supabaseError) {
          setAuthState(prev => ({ ...prev, loading: false }));
          return { error: supabaseError.message };
        }

        return {};
      }
    } catch (error) {
      setAuthState(prev => ({ ...prev, loading: false }));
      return { error: 'Erro inesperado. Tente novamente.' };
    }
  };

  const signup = async (credentials: SignupCredentials): Promise<{ error?: string }> => {
    try {
      if (credentials.password !== credentials.confirmPassword) {
        return { error: 'As senhas não coincidem.' };
      }

      setAuthState(prev => ({ ...prev, loading: true }));
      
      // Tentar primeiro com a API do backend
      try {
        const backendResponse = await api.auth.signup(
          credentials.email, 
          credentials.password, 
          credentials.name
        );
        console.log('Backend signup successful:', backendResponse);
      } catch (backendError) {
        console.log('Backend signup failed, proceeding with Supabase:', backendError);
      }

      // Sempre fazer signup no Supabase para gerenciar a sessão
      const redirectUrl = `${window.location.origin}/`;
      
      const { error } = await supabase.auth.signUp({
        email: credentials.email,
        password: credentials.password,
        options: {
          emailRedirectTo: redirectUrl,
          data: {
            name: credentials.name,
          }
        }
      });

      if (error) {
        setAuthState(prev => ({ ...prev, loading: false }));
        return { error: error.message };
      }

      setAuthState(prev => ({ ...prev, loading: false }));
      return {};
    } catch (error) {
      setAuthState(prev => ({ ...prev, loading: false }));
      return { error: 'Erro inesperado. Tente novamente.' };
    }
  };

  const logout = async (): Promise<void> => {
    await supabase.auth.signOut();
  };

  const value: AuthContextType = {
    ...authState,
    login,
    signup,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
