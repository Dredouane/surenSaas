"use client";

import { useRouter } from 'next/navigation';
import { useCallback } from 'react';

interface ApiError {
  status: number;
  message: string;
  redirectToLogin?: boolean;
}

export function useApiErrorHandler() {
  const router = useRouter();

  const handleError = useCallback((error: ApiError) => {
    if (error.status === 401 || error.redirectToLogin) {
      console.error('Session expirée, redirection vers login...');
      // Supprimer le cookie côté client
      document.cookie = 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      // Rediriger vers la page de login
      router.push('/login?error=session_expired');
      return true; // Erreur gérée
    }
    return false; // Erreur non gérée
  }, [router]);

  const fetchWithAuth = useCallback(async (url: string, options: RequestInit = {}) => {
    try {
      const response = await fetch(url, {
        ...options,
        credentials: 'include', // Important: envoyer les cookies
      });

      if (response.status === 401) {
        const errorData = await response.json().catch(() => ({}));
        handleError({
          status: 401,
          message: errorData.detail || 'Session invalide',
          redirectToLogin: true,
        });
        throw new Error('Session expirée');
      }

      return response;
    } catch (error) {
      if (error instanceof Error && error.message === 'Session expirée') {
        throw error;
      }
      // Pour les autres erreurs, on les relance
      throw error;
    }
  }, [handleError]);

  return { handleError, fetchWithAuth };
}

// Helper pour les composants qui utilisent fetch directement
export function handleApiError(error: any, router: ReturnType<typeof useRouter>) {
  if (error?.status === 401 || error?.message?.includes('Session')) {
    console.error('Session expirée, redirection vers login...');
    document.cookie = 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    router.push('/login?error=session_expired');
    return true;
  }
  return false;
}
