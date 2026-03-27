'use client';

import { useAuth } from '@/app/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * AuthGuard - Composant wrapper qui attend le chargement de l'authentification
 * 
 * Usage:
 * <AuthGuard>
 *   <MaPage />
 * </AuthGuard>
 * 
 * Ou avec un fallback personnalisé:
 * <AuthGuard fallback={<MonSpinnerPersonnalise />}>
 *   <MaPage />
 * </AuthGuard>
 */
export function AuthGuard({ children, fallback }: AuthGuardProps) {
  const { loading, error, isAuthenticated } = useAuth();

  // Afficher un loader pendant le chargement initial
  if (loading) {
    return fallback || (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground text-sm">Chargement...</p>
        </div>
      </div>
    );
  }

  // Afficher une erreur si le chargement a échoué
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-red-600 mb-4">Erreur de chargement: {error}</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  // Si tout est OK, afficher le contenu
  return <>{children}</>;
}
