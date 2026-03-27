/**
 * Valide une URL de redirect pour éviter les open redirects
 * - Doit être une URL relative (commence par /)
 * - Ou avoir le même hostname que l'app
 */

export function isValidRedirect(url: string, allowedHostnames: string[]): boolean {
  try {
    // Si URL vide
    if (!url || url.trim() === '') {
      return false;
    }
    
    // URL relative (commence par / et pas //)
    if (url.startsWith('/') && !url.startsWith('//')) {
      // Vérifier qu'elle ne pointe pas vers des protocoles externes
      const decoded = decodeURIComponent(url);
      const lower = decoded.toLowerCase();
      
      // Bloquer les protocoles externes
      if (lower.startsWith('http://') || 
          lower.startsWith('https://') ||
          lower.startsWith('javascript:') ||
          lower.startsWith('data:') ||
          lower.startsWith('vbscript:') ||
          lower.startsWith('file:')) {
        return false;
      }
      
      return true;
    }
    
    // URL absolue - vérifier hostname
    const parsed = new URL(url);
    
    // Vérifier que le hostname est dans la liste autorisée
    return allowedHostnames.some(hostname => 
      parsed.hostname === hostname || 
      parsed.hostname.endsWith(`.${hostname}`)
    );
    
  } catch {
    // URL invalide
    return false;
  }
}

export function getSafeRedirect(
  url: string | null | undefined, 
  allowedHostnames: string[],
  fallback: string = '/'
): string {
  if (!url) {
    return fallback;
  }
  
  if (isValidRedirect(url, allowedHostnames)) {
    return url;
  }
  
  return fallback;
}

// Hostnames autorisés (à configurer selon environnement)
export const ALLOWED_HOSTNAMES = [
  'localhost',
  'localhost:3000',
  // Ajouter les domains de prod ici
  // 'app.surensaas.fr',
];
