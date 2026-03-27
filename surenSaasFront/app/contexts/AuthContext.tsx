'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface UserProfile {
  id: string;
  email: string;
  org_id: string;
  org_slug: string;
  org_name: string;
  role: string;
  created_at?: string;
}

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  setUser: (user: UserProfile | null) => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Nombre de tentatives en cas d'échec
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // ms

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const fetchUserProfile = useCallback(async (attempt = 0): Promise<void> => {
    console.log(`🔍 [Attempt ${attempt + 1}/${MAX_RETRIES}] Fetching user profile...`);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
      
      const response = await fetch(`/api/v1/users/me`, {
        credentials: 'include',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        }
      });
      
      clearTimeout(timeoutId);

      console.log('📡 Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Error response:', errorText);
        
        if (response.status === 401) {
          console.log('🔒 Non authentifié (401)');
          setUser(null);
          setLoading(false);
          return;
        }
        
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log('✅ User profile loaded:', data);
      
      // Vérifier que les données essentielles sont présentes
      if (!data.id || !data.email || !data.org_id) {
        throw new Error('Données utilisateur incomplètes');
      }
      
      console.log('📝 Setting user:', data.email, 'role:', data.role);
      setUser(data);
      console.log('📝 User set, calling setError(null)');
      setError(null);
      setRetryCount(0);
      setLoading(false);
      console.log('📝 All state updated');
    } catch (err) {
      console.error(`❌ Error fetching profile (attempt ${attempt + 1}):`, err);
      
      // Retry si on n'a pas atteint le max
      if (attempt < MAX_RETRIES - 1) {
        console.log(`🔄 Retrying in ${RETRY_DELAY}ms...`);
        setRetryCount(attempt + 1);
        setTimeout(() => fetchUserProfile(attempt + 1), RETRY_DELAY);
        return;
      }
      
      // Max retries atteint
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
      setUser(null);
    } finally {
      // S'assurer que loading passe à false dans tous les cas
      console.log('🏁 Finally - attempt:', attempt);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUserProfile();
  }, [fetchUserProfile]);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    setRetryCount(0);
    await fetchUserProfile();
  }, [fetchUserProfile]);

  console.log('🎨 AuthProvider RENDER:', { loading, hasUser: !!user, error: !!error });
  
  const value = {
    user,
    loading,
    error,
    refetch,
    setUser,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
