'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Users,
  Truck,
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  Bell,
  Download,
  Check,
  User,
  Wrench,
} from 'lucide-react';
import { Pointage, Ressource } from '@/types/chantier';

interface PointagesListProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
  pointages?: Pointage[];
}

type PresenceState = 'present' | 'absent' | 'undefined';

interface RessourcePresence {
  id: string;
  nom: string;
  type: 'homme' | 'machine';
  specialite: string;
  presence: PresenceState;
}

export default function PointagesList({ chantierId, orgId, onRefresh }: PointagesListProps) {
  const [today] = useState<string>(new Date().toISOString().split('T')[0]);
  const [hommesPresence, setHommesPresence] = useState<RessourcePresence[]>([]);
  const [machinesPresence, setMachinesPresence] = useState<RessourcePresence[]>([]);
  const [pointages, setPointages] = useState<Pointage[]>([]);
  const [pointagesDuJour, setPointagesDuJour] = useState<Pointage[]>([]);
  const [pointageEffectue, setPointageEffectue] = useState<boolean>(false);
  const [ressourcesChantier, setRessourcesChantier] = useState<Ressource[]>([]);
  const [resourcesLoading, setResourcesLoading] = useState(true);

  useEffect(() => {
    setResourcesLoading(true);
    Promise.all([
      fetch(`/api/v1/chantiers/${chantierId}/pointages?org_id=${orgId}`, { credentials: 'include' }).then(r => r.json()),
      fetch(`/api/v1/chantiers/${chantierId}/ressources?org_id=${orgId}`, { credentials: 'include' }).then(r => r.json()),
    ]).then(([pointagesData, ressourcesData]) => {
      setResourcesLoading(false);
      setPointages(pointagesData.map((p: any) => ({
        id: p.id,
        chantierId: p.chantier_id,
        orgId: p.org_id,
        date: p.date,
        conducteurId: p.conducteur_id,
        commentaires: p.commentaires || '',
        statut: p.statut || '',
        validePar: p.valide_par || '',
        createdAt: p.created_at,
        updatedAt: p.updated_at,
        ressources: (p.ressources || []).map((r: any) => ({
          ressourceId: r.ressource_id,
          nom: r.nom,
          type: r.type,
          periode: r.periode || 'journee',
          heuresPrevues: r.heures_prevues,
        })),
      })));
      setRessourcesChantier(ressourcesData.map((r: any) => ({
        id: r.id,
        nom: r.nom,
        type: r.type,
        specialite: r.specialite || '',
        disponible: r.disponible ?? true,
        chantierId: r.chantier_id,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
      })));
    }).catch(err => { console.error('Erreur chargement pointages/ressources:', err); setResourcesLoading(false); });
  }, [chantierId, orgId]);

  // Initialiser les états de présence
  useEffect(() => {
    // Vérifier si un pointage existe pour aujourd'hui
    const pointagesAujourdhui = pointages.filter(p => 
      new Date(p.date).toISOString().split('T')[0] === today
    );
    
    setPointagesDuJour(pointagesAujourdhui);
    setPointageEffectue(pointagesAujourdhui.length > 0);

    const hommesInit: RessourcePresence[] = ressourcesChantier
      .filter(r => r.type === 'homme')
      .map(homme => ({
        id: homme.id,
        nom: homme.nom,
        type: 'homme',
        specialite: homme.specialite || '',
        presence: 'undefined' as PresenceState
      }));

    const machinesInit: RessourcePresence[] = ressourcesChantier
      .filter(r => r.type === 'machine')
      .map(machine => ({
        id: machine.id,
        nom: machine.nom,
        type: 'machine',
        specialite: machine.specialite || '',
        presence: 'undefined' as PresenceState
      }));

    setHommesPresence(hommesInit);
    setMachinesPresence(machinesInit);
  }, [chantierId, pointages, today, ressourcesChantier]);

  // Toggle présence d'une ressource
  const togglePresence = (type: 'homme' | 'machine', id: string) => {
    if (type === 'homme') {
      setHommesPresence(prev => prev.map(homme => {
        if (homme.id === id) {
          // Cycle: undefined → present → absent → undefined
          if (homme.presence === 'undefined') return { ...homme, presence: 'present' };
          if (homme.presence === 'present') return { ...homme, presence: 'absent' };
          return { ...homme, presence: 'undefined' };
        }
        return homme;
      }));
    } else {
      setMachinesPresence(prev => prev.map(machine => {
        if (machine.id === id) {
          if (machine.presence === 'undefined') return { ...machine, presence: 'present' };
          if (machine.presence === 'present') return { ...machine, presence: 'absent' };
          return { ...machine, presence: 'undefined' };
        }
        return machine;
      }));
    }
  };

  // Valider les pointages du jour
  const handleValiderPointages = async () => {
    const hommesPresents = hommesPresence.filter(h => h.presence === 'present').length;
    const hommesAbsents = hommesPresence.filter(h => h.presence === 'absent').length;
    const machinesPresentes = machinesPresence.filter(m => m.presence === 'present').length;
    const machinesAbsentes = machinesPresence.filter(m => m.presence === 'absent').length;

    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/pointages?org_id=${orgId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: new Date().toISOString().split('T')[0],
          commentaires: `Hommes: ${hommesPresents} présents, ${hommesAbsents} absents | Machines: ${machinesPresentes} présentes, ${machinesAbsentes} absentes`,
        }),
      });
      if (!res.ok) throw new Error('Erreur création pointage');
      const pointage = await res.json();
      const pointageId = pointage.id || pointage.data?.[0]?.id;

      const ressourcesWithPresence = [
        ...hommesPresence.filter(h => h.presence !== 'undefined'),
        ...machinesPresence.filter(m => m.presence !== 'undefined'),
      ];

      if (pointageId) {
        await Promise.all(ressourcesWithPresence.map(r =>
          fetch(`/api/v1/chantiers/${chantierId}/pointages/${pointageId}/ressources?org_id=${orgId}`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ressource_id: r.id,
              periode: 'journee',
              presence: r.presence === 'present',
            }),
          })
        ));
      }

      setPointageEffectue(true);
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  // Envoyer notifications matinales
  const handleEnvoyerNotifications = async () => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/notifications?org_id=${orgId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'pointage',
          titre: 'Rappel pointages',
          message: 'Bonjour, n\'oubliez pas de faire les pointages pour aujourd\'hui.',
        }),
      });
      if (!res.ok) throw new Error('Erreur envoi notification');
      alert('Notifications matinales envoyées avec succès');
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  // Exporter les pointages
  const handleExporter = () => {
    alert('Export des pointages au format Excel (fonctionnalité à implémenter)');
  };

  // Obtenir la couleur et l'icône selon l'état de présence
  const getPresenceStyle = (presence: PresenceState) => {
    switch (presence) {
      case 'present':
        return {
          bgColor: 'bg-green-100 hover:bg-green-200',
          textColor: 'text-green-800',
          borderColor: 'border-green-300',
          icon: <CheckCircle className="h-5 w-5" />,
          label: 'Présent'
        };
      case 'absent':
        return {
          bgColor: 'bg-red-100 hover:bg-red-200',
          textColor: 'text-red-800',
          borderColor: 'border-red-300',
          icon: <XCircle className="h-5 w-5" />,
          label: 'Absent'
        };
      default:
        return {
          bgColor: 'bg-gray-100 hover:bg-gray-200',
          textColor: 'text-gray-600',
          borderColor: 'border-gray-300',
          icon: <Clock className="h-5 w-5" />,
          label: 'À définir'
        };
    }
  };

  // Formater une date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', { 
      weekday: 'long',
      day: 'numeric', 
      month: 'long',
      year: 'numeric'
    });
  };

  // Statistiques
  const stats = {
    hommesPresents: hommesPresence.filter(h => h.presence === 'present').length,
    hommesAbsents: hommesPresence.filter(h => h.presence === 'absent').length,
    hommesTotal: hommesPresence.length,
    machinesPresentes: machinesPresence.filter(m => m.presence === 'present').length,
    machinesAbsentes: machinesPresence.filter(m => m.presence === 'absent').length,
    machinesTotal: machinesPresence.length,
  };

  return (
    <div className="space-y-6">
      {/* En-tête avec actions */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Pointages hommes/machines</h2>
          <p className="text-muted-foreground">
            Interface simplifiée pour marquer les présences quotidiennes
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="outline" onClick={handleExporter} className="gap-2">
            <Download className="h-4 w-4" />
            Exporter
          </Button>
          <Button onClick={handleEnvoyerNotifications} className="gap-2 bg-blue-600 hover:bg-blue-700">
            <Bell className="h-4 w-4" />
            Notifications matinales
          </Button>
        </div>
      </div>

      {/* Bannière pointage du jour */}
      <Card className={pointageEffectue ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200"}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`h-12 w-12 rounded-full flex items-center justify-center ${pointageEffectue ? 'bg-green-100' : 'bg-amber-100'}`}>
                {pointageEffectue ? (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                ) : (
                  <Clock className="h-6 w-6 text-amber-600" />
                )}
              </div>
              <div>
                <h3 className="font-semibold">
                  {pointageEffectue ? '✅ Pointages effectués aujourd\'hui' : '⚠️ Pointages non effectués aujourd\'hui'}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {pointageEffectue 
                    ? `Les pointages du ${formatDate(today)} ont été enregistrés.` 
                    : `Cliquez sur les boutons ci-dessous pour marquer les présences/absences.`}
                </p>
              </div>
            </div>
            {!pointageEffectue && (
              <Button onClick={handleValiderPointages} className="gap-2 bg-green-600 hover:bg-green-700">
                <Check className="h-4 w-4" />
                Valider les pointages
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Statistiques rapides */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Hommes présents</p>
                <p className="text-2xl font-bold text-green-600">{stats.hommesPresents}</p>
              </div>
              <Users className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Hommes absents</p>
                <p className="text-2xl font-bold text-red-600">{stats.hommesAbsents}</p>
              </div>
              <User className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Machines présentes</p>
                <p className="text-2xl font-bold text-green-600">{stats.machinesPresentes}</p>
              </div>
              <Truck className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Machines absentes</p>
                <p className="text-2xl font-bold text-red-600">{stats.machinesAbsentes}</p>
              </div>
              <Wrench className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Section Hommes */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Hommes ({stats.hommesTotal})
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Cliquez sur chaque bouton pour marquer présence (vert) / absence (rouge)
          </p>
        </CardHeader>
        <CardContent>
          {resourcesLoading ? (
            <p className="text-muted-foreground p-4">Chargement des ressources...</p>
          ) : hommesPresence.length === 0 ? (
            <p className="text-muted-foreground p-4">Aucune ressource humaine assignée à ce chantier. Ajoutez-en depuis la section Ressources.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
              {hommesPresence.map((homme) => {
                const style = getPresenceStyle(homme.presence);
                return (
                  <button key={homme.id} onClick={() => togglePresence('homme', homme.id)}
                    className={`flex flex-col items-center justify-center p-4 border-2 rounded-lg transition-all duration-200 ${style.bgColor} ${style.borderColor} ${style.textColor} hover:scale-[1.02]`}
                  >
                    <div className="mb-2">{style.icon}</div>
                    <div className="text-center">
                      <div className="font-semibold text-sm">{homme.nom}</div>
                      <div className="text-xs opacity-75 mt-1">{homme.specialite}</div>
                      <div className="text-xs font-medium mt-2">{style.label}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section Machines */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Truck className="h-5 w-5" />
            Machines ({stats.machinesTotal})
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Cliquez sur chaque bouton pour marquer présence (vert) / absence (rouge)
          </p>
        </CardHeader>
        <CardContent>
          {resourcesLoading ? (
            <p className="text-muted-foreground p-4">Chargement des machines...</p>
          ) : machinesPresence.length === 0 ? (
            <p className="text-muted-foreground p-4">Aucune machine assignée à ce chantier. Ajoutez-en depuis la section Ressources.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
              {machinesPresence.map((machine) => {
                const style = getPresenceStyle(machine.presence);
                return (
                  <button key={machine.id} onClick={() => togglePresence('machine', machine.id)}
                    className={`flex flex-col items-center justify-center p-4 border-2 rounded-lg transition-all duration-200 ${style.bgColor} ${style.borderColor} ${style.textColor} hover:scale-[1.02]`}
                  >
                    <div className="mb-2">{style.icon}</div>
                    <div className="text-center">
                      <div className="font-semibold text-sm">{machine.nom}</div>
                      <div className="text-xs opacity-75 mt-1">{machine.specialite}</div>
                      <div className="text-xs font-medium mt-2">{style.label}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bouton validation */}
      {!pointageEffectue && (
        <div className="flex justify-center">
          <Button 
            onClick={handleValiderPointages} 
            size="lg" 
            className="gap-3 px-8 py-6 text-lg bg-green-600 hover:bg-green-700"
          >
            <Check className="h-6 w-6" />
            Valider tous les pointages du jour
          </Button>
        </div>
      )}

      {/* Historique des pointages */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Historique des pointages
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Pointages des jours précédents
          </p>
        </CardHeader>
        <CardContent>
          {pointages.length === 0 ? (
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">Aucun pointage historique</h3>
              <p className="text-muted-foreground mt-2">
                Les pointages validés apparaîtront ici.
              </p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Hommes</TableHead>
                    <TableHead>Machines</TableHead>
                    <TableHead>Validé par</TableHead>
                    <TableHead>Statut</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pointages.slice(0, 10).map((pointage) => (
                    <TableRow key={pointage.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          {formatDate(String(pointage.date))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Users className="h-4 w-4 text-muted-foreground" />
                          <span>{pointage.ressources.filter(r => r.type === 'homme').length} hommes</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Truck className="h-4 w-4 text-muted-foreground" />
                          <span>{pointage.ressources.filter(r => r.type === 'machine').length} machines</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {pointage.validePar ? (
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <span>Gérant</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">Non validé</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {pointage.validePar ? (
                          <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Validé</Badge>
                        ) : (
                          <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">En attente</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section notifications Telegram */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Workflow Telegram
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Notifications automatiques pour les pointages
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <Bell className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <h4 className="font-medium">7h00 - Rappel matinal</h4>
                    <p className="text-sm text-muted-foreground">Notification aux conducteurs</p>
                  </div>
                </div>
                <p className="text-sm">
                  "Bonjour, n'oubliez pas de faire les pointages pour aujourd'hui."
                </p>
              </div>
              <div className="border rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                    <Check className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <h4 className="font-medium">Après validation</h4>
                    <p className="text-sm text-muted-foreground">Récapitulatif au gérant</p>
                  </div>
                </div>
                <p className="text-sm">
                  "Pointages du jour validés: 5 hommes présents, 2 machines présentes."
                </p>
              </div>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">Statut des notifications</h4>
                <p className="text-sm text-muted-foreground">
                  Dernière notification: Aujourd'hui 07:00
                </p>
              </div>
              <Button variant="outline" className="gap-2">
                <Bell className="h-4 w-4" />
                Tester notification
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Note prototype */}
      <div className="text-sm text-muted-foreground border-t pt-4">
        <p>
          <strong>Note prototype:</strong> Interface simplifiée pour les pointages quotidiens.
          Cliquez sur chaque bouton pour marquer présence/absence. Validation unique par jour avec notification Telegram.
        </p>
      </div>
    </div>
  );
}