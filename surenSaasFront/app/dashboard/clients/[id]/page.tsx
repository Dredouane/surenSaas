'use client';

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Building2, Mail, Phone, MapPin, FileText, Edit, Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface Client {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  siret?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

const DEFAULT_ORG_ID = process.env.NEXT_PUBLIC_ORG_ID;

export default function ClientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const [client, setClient] = useState<Client | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const clientId = params.id as string;

  useEffect(() => {
    if (user?.org_id && clientId) {
      fetchClient();
    }
  }, [user, clientId]);

  const fetchClient = async () => {
    try {
      setLoading(true);
      const orgId = user?.org_id || DEFAULT_ORG_ID;
      const response = await fetch(
        `/api/v1/clients/${clientId}?org_id=${orgId}`,
        { credentials: 'include' }
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.error('🔴 Session invalide ou expirée - Redirection vers login');
          router.push('/login?error=session_expired');
          return;
        }
        if (response.status === 404) {
          throw new Error('Client non trouvé');
        }
        throw new Error('Erreur lors de la récupération du client');
      }

      const data = await response.json();
      setClient(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      const orgId = user?.org_id || DEFAULT_ORG_ID;
      const response = await fetch(
        `/api/v1/clients/${clientId}?org_id=${orgId}`,
        {
          method: 'DELETE',
          credentials: 'include',
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.error('🔴 Session invalide ou expirée - Redirection vers login');
          router.push('/login?error=session_expired');
          return;
        }
        throw new Error('Erreur lors de la suppression');
      }

      router.push('/dashboard/clients');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la suppression');
      setDeleting(false);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8">
        <Skeleton className="h-8 w-32 mb-6" />
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-64" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !client) {
    return (
      <div className="p-6 lg:p-8">
        <Link href="/dashboard/clients">
          <Button variant="ghost" className="mb-4 gap-2">
            <ArrowLeft className="h-4 w-4" />
            Retour aux clients
          </Button>
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-8 rounded-lg text-center">
          <h2 className="text-xl font-semibold mb-2">Erreur</h2>
          <p>{error || "Client non trouvé"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/clients">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">{client.name}</h1>
        </div>
        <div className="flex gap-2">
          <Link href={`/dashboard/clients/${clientId}/edit`}>
            <Button variant="outline" className="gap-2">
              <Edit className="h-4 w-4" />
              Modifier
            </Button>
          </Link>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" className="gap-2">
                <Trash2 className="h-4 w-4" />
                Supprimer
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
                <AlertDialogDescription>
                  Êtes-vous sûr de vouloir supprimer ce client ? Cette action est irréversible.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Annuler</AlertDialogCancel>
                <AlertDialogAction 
                  onClick={handleDelete}
                  disabled={deleting}
                  className="bg-red-600 hover:bg-red-700"
                >
                  {deleting ? 'Suppression...' : 'Supprimer'}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Informations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {client.email && (
                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Email</p>
                    <a 
                      href={`mailto:${client.email}`} 
                      className="text-blue-600 hover:underline"
                    >
                      {client.email}
                    </a>
                  </div>
                </div>
              )}
              
              {client.phone && (
                <div className="flex items-center gap-3">
                  <Phone className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Téléphone</p>
                    <a 
                      href={`tel:${client.phone}`} 
                      className="text-blue-600 hover:underline"
                    >
                      {client.phone}
                    </a>
                  </div>
                </div>
              )}
              
              {client.address && (
                <div className="flex items-center gap-3">
                  <MapPin className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Adresse</p>
                    <p>{client.address}</p>
                  </div>
                </div>
              )}
              
              {client.siret && (
                <div className="pt-4 border-t">
                  <p className="text-sm text-muted-foreground">SIRET</p>
                  <p className="font-mono">{client.siret}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {client.notes && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{client.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Détails</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="text-muted-foreground">Créé le</p>
                <p>{formatDate(client.created_at)}</p>
              </div>
              {client.updated_at && (
                <div>
                  <p className="text-muted-foreground">Dernière modification</p>
                  <p>{formatDate(client.updated_at)}</p>
                </div>
              )}
              <div>
                <p className="text-muted-foreground">ID</p>
                <p className="font-mono text-xs">{client.id}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link href={`/dashboard/invoices?client_id=${clientId}`}>
                <Button variant="outline" className="w-full">
                  Voir les factures
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
