'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Calendar, Clock, Check, Bell, Download,
} from 'lucide-react';
import type { Pointage } from '@/types/chantier';
import PointageDetailView from './PointageDetailView';
import PointageMobileList from './PointageMobileList';

interface PointagesListProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
  pointages?: Pointage[];
}

export default function PointagesList({ chantierId, orgId, onRefresh }: PointagesListProps) {
  const [pointages, setPointages] = useState<Pointage[]>([]);
  const [selectedPointage, setSelectedPointage] = useState<Pointage | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchPointages = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/pointages?org_id=${orgId}`, { credentials: 'include' });
      if (!res.ok) throw new Error('Erreur chargement');
      const data = await res.json();
      const mapped = data.map((p: any) => ({
        id: p.id,
        date: p.date,
        chantierId: p.chantier_id,
        conducteurId: p.conducteur_id || '',
        ressources: (p.ressources || []).map((r: any) => ({
          ressourceId: r.ressource_id,
          ressourceNom: r.nom,
          type: r.type,
          periode: r.periode || 'journee',
          heuresPrevues: r.heures_prevues,
        })),
        commentaires: p.commentaires || '',
        validePar: p.valide_par || '',
        valideLe: p.valide_le || undefined,
        status: p.status || '',
        createdAt: p.created_at,
        updatedAt: p.updated_at || p.created_at,
      }));
      console.log('Pointages raw data:', data);
      console.log('Mapped pointage:', mapped[0]);
      console.log('First ressource nom:', mapped[0]?.ressources[0]?.ressourceNom);
      console.log('First ressource keys:', Object.keys(mapped[0]?.ressources[0] || {}));
      setPointages(mapped);
    } catch (err) {
      console.error('Erreur chargement pointages:', err);
    } finally {
      setLoading(false);
    }
  }, [chantierId, orgId]);

  useEffect(() => { fetchPointages(); }, [fetchPointages]);

  const handleRefresh = () => {
    fetchPointages();
    onRefresh?.();
  };

  const today = new Date().toISOString().split('T')[0];
  const pointageAujourdhui = pointages.find(p =>
    new Date(p.date).toISOString().split('T')[0] === today
  );

  // Vue détail
  if (selectedPointage) {
    console.log('SELECTED pointage:', selectedPointage);
    console.log('SELECTED ressources:', selectedPointage.ressources);
    console.log('SELECTED first ressource keys:', Object.keys(selectedPointage.ressources[0] || {}));
    const detailRessources = selectedPointage.ressources.map(r => ({
      ressourceId: r.ressourceId,
      nom: (r as any).ressourceNom || (r as any).nom || (r as any).name || 'INCONNU',
      type: r.type as 'homme' | 'machine',
      periode: r.periode,
      heuresPrevues: r.heuresPrevues,
    }));
    console.log('DETAIL ressources result:', detailRessources);
    return (
      <PointageDetailView
        pointage={selectedPointage}
        ressources={detailRessources}
        chantierId={chantierId}
        orgId={orgId}
        onBack={() => setSelectedPointage(null)}
        onRefresh={handleRefresh}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Bannière du jour */}
      <Card className={pointageAujourdhui ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200"}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`h-12 w-12 rounded-full flex items-center justify-center ${pointageAujourdhui ? 'bg-green-100' : 'bg-amber-100'}`}>
                {pointageAujourdhui ? (
                  <Check className="h-6 w-6 text-green-600" />
                ) : (
                  <Clock className="h-6 w-6 text-amber-600" />
                )}
              </div>
              <div>
                <h3 className="font-semibold">
                  {pointageAujourdhui ? '✅ Pointage enregistré aujourd\'hui' : '⚠️ Aucun pointage aujourd\'hui'}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {pointageAujourdhui
                    ? `${pointageAujourdhui.ressources.filter(r => r.type === 'homme').length} hommes, ${pointageAujourdhui.ressources.filter(r => r.type === 'machine').length} machines`
                    : 'Aucun pointage n\'a été enregistré pour aujourd\'hui.'}
                </p>
              </div>
            </div>
            {pointageAujourdhui && (
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => setSelectedPointage(pointageAujourdhui)}
              >
                Voir le détail
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Liste des pointages (utilise le composant mobile natif même sur desktop) */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Calendar className="h-5 w-5" />
            Historique des pointages
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground py-8 text-center">Chargement...</p>
          ) : (
            <PointageMobileList
              pointages={pointages}
              onSelect={setSelectedPointage}
            />
          )}
        </CardContent>
      </Card>

      {/* Notifications matinales — simplifié */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Bell className="h-5 w-5" />
            Notifications
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Rappel automatique aux conducteurs chaque matin à 7h00.
          </p>
          <Button variant="outline" size="sm" className="gap-2" onClick={handleEnvoyerNotifications}>
            <Bell className="h-4 w-4" />
            Tester
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

async function handleEnvoyerNotifications() {
  try {
    await fetch('/api/v1/notifications', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'pointage',
        titre: 'Rappel pointages',
        message: 'Bonjour, n\'oubliez pas de faire les pointages pour aujourd\'hui.',
      }),
    });
    alert('Notification test envoyée');
  } catch {
    alert('Erreur envoi notification');
  }
}
