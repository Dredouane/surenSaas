import { useState } from 'react';

interface UseFileDownloadOptions {
  orgSlug: string;
}

export function useFileDownload({ orgSlug }: UseFileDownloadOptions) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const downloadFile = async (storagePath: string, filename?: string) => {
    setDownloading(true);
    setError(null);
    
    try {
      // Construire l'URL de téléchargement
      const params = new URLSearchParams({
        storage_path: storagePath,
      });
      
      if (filename) {
        params.append('filename', filename);
      }
      
      const downloadUrl = `/api/v1/${orgSlug}/files/download?${params.toString()}`;
      
      // Ouvrir dans un nouvel onglet (le backend redirige vers R2)
      const newWindow = window.open(downloadUrl, '_blank');
      
      if (!newWindow) {
        throw new Error('Impossible d\'ouvrir une nouvelle fenêtre. Vérifiez les bloqueurs de popups.');
      }
      
      // Optionnel: vérifier si le téléchargement a réussi
      // Note: difficile à faire car c'est une redirection vers R2
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de téléchargement');
      console.error('Erreur téléchargement fichier:', err);
    } finally {
      setDownloading(false);
    }
  };
  
  const downloadEmailAttachment = async (emailId: string, attachmentId: string) => {
    setDownloading(true);
    setError(null);
    
    try {
      const downloadUrl = `/api/v1/${orgSlug}/emails/${emailId}/attachments/${attachmentId}/download`;
      const newWindow = window.open(downloadUrl, '_blank');
      
      if (!newWindow) {
        throw new Error('Impossible d\'ouvrir une nouvelle fenêtre. Vérifiez les bloqueurs de popups.');
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de téléchargement');
      console.error('Erreur téléchargement PJ:', err);
    } finally {
      setDownloading(false);
    }
  };
  
  const downloadInvoice = async (invoiceId: string) => {
    setDownloading(true);
    setError(null);
    
    try {
      const downloadUrl = `/api/v1/${orgSlug}/invoices/${invoiceId}/download`;
      const newWindow = window.open(downloadUrl, '_blank');
      
      if (!newWindow) {
        throw new Error('Impossible d\'ouvrir une nouvelle fenêtre. Vérifiez les bloqueurs de popups.');
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de téléchargement');
      console.error('Erreur téléchargement facture:', err);
    } finally {
      setDownloading(false);
    }
  };
  
  return {
    downloadFile,
    downloadEmailAttachment,
    downloadInvoice,
    downloading,
    error,
    clearError: () => setError(null),
  };
}