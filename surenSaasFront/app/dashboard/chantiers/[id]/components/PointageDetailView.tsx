'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft, Calendar, CheckCircle, XCircle, Clock,
  Users, Truck, User, Check, Trash2, ShieldCheck,
} from 'lucide-react';
import type { Pointage, Ressource } from '@/types/chantier';

interface PointageDetailViewProps {
  pointage: Pointage;
  ressources: {
    ressourceId: string;
    nom: string;
    type: 'homme' | 'machine';
    periode: string;
    heuresPrevues?: number;
  }[];
  chantierId: string;
  orgId: string;
  onBack: () => void;
  onRefresh: () => void;
}

export default function PointageDetailView({
  pointage, ressources, chantierId, orgId, onBack, onRefresh,
}: PointageDetailViewProps) {
  const [validating, setValidating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hommes = ressources.filter(r => r.type === 'homme');
  const machines = ressources.filter(r => r.type === 'machine');

  const formatDate = (dateString: string | Date) => {
    const d = new Date(dateString);
    return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  };

  const statusBadge = () => {
    const s = pointage.validePar ? 'valide' : (pointage as any).status;
    switch (s) {
      case 'brouillon':
        return <Badge className="bg-gray-100 text-gray-800"><Clock className="h-3 w-3 mr-1" />Brouillon</Badge>;
      case 'en_attente_validation':
        return <Badge className="bg-amber-100 text-amber-800"><Clock className="h-3 w-3 mr-1" />En attente</Badge>;
      case 'valide':
        return <Badge className="bg-green-100 text-green-800"><CheckCircle className="h-3 w-3 mr-1" />Validé</Badge>;
      default:
        return <Badge variant="outline">{s || 'Inconnu'}</Badge>;
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/pointages/${pointage.id}/validate?org_id=${orgId}`, {
        method: 'PUT',
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erreur validation');
      }
      onRefresh();
      onBack();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur');
    } finally {
      setValidating(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Supprimer ce pointage ?')) return;
    setDeleting(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/pointages/${pointage.id}?org_id=${orgId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erreur suppression');
      }
      onRefresh();
      onBack();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur');
    } finally {
      setDeleting(false);
    }
  };

  const status = (pointage as any).status || '';
  const isBrouillon = !pointage.validePar && status !== 'en_attente_validation' && status !== 'valide';

  return (
    <div className="space-y-4">
      <Button variant="ghost" onClick={onBack} className="gap-2 -ml-2">
        <ArrowLeft className="h-4 w-4" />
        Retour à la liste
      </Button>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="h-5 w-5" />
              {formatDate(pointage.date)}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Créé le {new Date(pointage.createdAt).toLocaleDateString('fr-FR')}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {statusBadge()}
          </div>
        </CardHeader>
        <CardContent>
          {pointage.commentaires && (
            <p className="text-sm text-muted-foreground mb-4">{pointage.commentaires}</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Hommes */}
            <div>
              <h4 className="text-sm font-medium flex items-center gap-2 mb-3">
                <Users className="h-4 w-4" />
                Personnel ({hommes.length})
              </h4>
              {hommes.length === 0 ? (
                <p className="text-sm text-muted-foreground">Aucun</p>
              ) : (
                <div className="space-y-2">
                  {hommes.map(r => (
                    <div key={r.ressourceId} className="flex items-center gap-2 text-sm p-2 bg-green-50 rounded border border-green-200">
                      <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                      <span>{r.nom}</span>
                      <span className="text-xs text-muted-foreground ml-auto">{r.periode}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Machines */}
            <div>
              <h4 className="text-sm font-medium flex items-center gap-2 mb-3">
                <Truck className="h-4 w-4" />
                Machines ({machines.length})
              </h4>
              {machines.length === 0 ? (
                <p className="text-sm text-muted-foreground">Aucune</p>
              ) : (
                <div className="space-y-2">
                  {machines.map(r => (
                    <div key={r.ressourceId} className="flex items-center gap-2 text-sm p-2 bg-green-50 rounded border border-green-200">
                      <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                      <span>{r.nom}</span>
                      <span className="text-xs text-muted-foreground ml-auto">{r.periode}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
              {error}
            </div>
          )}

          {isBrouillon && (
            <>
              <Separator className="my-4" />
              <div className="flex gap-3">
                <Button onClick={handleValidate} disabled={validating} className="gap-2 bg-green-600 hover:bg-green-700">
                  <ShieldCheck className="h-4 w-4" />
                  {validating ? 'Validation...' : 'Valider le pointage'}
                </Button>
                <Button onClick={handleDelete} disabled={deleting} variant="outline" className="gap-2 text-red-600 border-red-200 hover:bg-red-50">
                  <Trash2 className="h-4 w-4" />
                  {deleting ? 'Suppression...' : 'Supprimer'}
                </Button>
              </div>
            </>
          )}

          {pointage.validePar && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-sm flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-green-600" />
              <span>Validé par <strong>Gérant</strong> le {new Date(pointage.valideLe || '').toLocaleDateString('fr-FR')}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
