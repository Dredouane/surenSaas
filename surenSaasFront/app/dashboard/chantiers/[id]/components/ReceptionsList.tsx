'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Plus,
  Search,
  Calendar,
  Users,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  XCircle,
  Eye,
  MessageSquare,
} from 'lucide-react';
import { Reception, ReceptionStatut, ReceptionType } from '@/types/chantier';
import { scrollToDetail } from '@/lib/scroll-to-detail';
import { getTachesDeReception } from '@/lib/chantier-data';

interface ReceptionsListProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
}

export default function ReceptionsList({ chantierId, orgId, onRefresh }: ReceptionsListProps) {
  const [receptions, setReceptions] = useState<Reception[]>([]);
  const [search, setSearch] = useState('');
  const [filterStatut, setFilterStatut] = useState<ReceptionStatut | 'all'>('all');
  const [filterType, setFilterType] = useState<ReceptionType | 'all'>('all');
  const [selectedReception, setSelectedReception] = useState<Reception | null>(null);
  const [editReceptionMode, setEditReceptionMode] = useState(false);
  const [editReceptionForm, setEditReceptionForm] = useState({ date: '', type: '' as ReceptionType, commentaires: '' });

  useEffect(() => {
    fetchReceptions();
  }, [chantierId]);

  const fetchReceptions = async () => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/receptions?org_id=${orgId}`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setReceptions(data.map((r: any) => ({
          id: r.id,
          chantierId: r.chantier_id,
          date: r.date || r.created_at,
          type: r.type || 'suivi',
          statut: r.statut || 'planifiee',
          participants: r.participants || [],
          ordreDuJour: r.ordre_du_jour || '',
          decisions: r.decisions || '',
          pointsARegler: r.points_a_regler || '',
          documents: r.documents || [],
          createdAt: r.created_at,
          updatedAt: r.updated_at || r.created_at,
        })));
      }
    } catch (err) {
      console.error('Erreur chargement réceptions:', err);
    }
  };

  // Filtrer les réceptions
  const filteredReceptions = receptions.filter(reception => {
    if (search && !reception.ordreDuJour.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (filterStatut !== 'all' && reception.statut !== filterStatut) {
      return false;
    }
    if (filterType !== 'all' && reception.type !== filterType) {
      return false;
    }
    return true;
  });

  // Obtenir le badge de statut
  const getStatutBadge = (statut: ReceptionStatut) => {
    switch (statut) {
      case 'planifiee':
        return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200"><Clock className="w-3 h-3 mr-1" /> Planifiée</Badge>;
      case 'en_cours':
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200"><AlertCircle className="w-3 h-3 mr-1" /> En cours</Badge>;
      case 'terminee':
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle className="w-3 h-3 mr-1" /> Terminée</Badge>;
      case 'annulee':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> Annulée</Badge>;
    }
  };

  // Obtenir le badge de type
  const getTypeBadge = (type: ReceptionType) => {
    switch (type) {
      case 'livraison':
        return <Badge variant="secondary" className="bg-purple-50 text-purple-700">Livraison</Badge>;
      case 'validation':
        return <Badge variant="secondary" className="bg-green-50 text-green-700">Validation</Badge>;
      case 'probleme':
        return <Badge variant="secondary" className="bg-red-50 text-red-700">Problème</Badge>;
      case 'suivi':
        return <Badge variant="secondary" className="bg-blue-50 text-blue-700">Suivi</Badge>;
    }
  };

  // Formater la date
  const formatDate = (dateString: string | Date) => {
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Obtenir les tâches d'une réception
  const getTachesForReception = (receptionId: string) => {
    return getTachesDeReception(receptionId);
  };

  // Handler pour voir les détails
  const handleViewDetails = (reception: Reception) => {
    setSelectedReception(reception);
    scrollToDetail();
  };

  // Handler pour fermer les détails
  const handleCloseDetails = () => {
    setSelectedReception(null);
  };

  const handleCreateReception = async () => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/receptions?org_id=${orgId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: new Date().toISOString(),
          type: 'suivi',
          statut: 'planifiee',
          participants: [],
          ordre_du_jour: 'Nouvelle réception',
        }),
      });
      if (!res.ok) throw new Error('Erreur création réception');
      fetchReceptions();
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  const handleUpdateReception = async (id: string, updates: any) => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/receptions/${id}?org_id=${orgId}`, {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!res.ok) throw new Error('Erreur mise à jour réception');
      fetchReceptions();
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  const handleValidateReception = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/receptions/${id}?org_id=${orgId}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statut: 'terminee' }),
      });
      if (!res.ok) throw new Error('Erreur validation réception');
      fetchReceptions();
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  return (
    <div className="space-y-6">
      {/* En-tête avec filtres */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Réceptions client
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Rechercher dans l'ordre du jour..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex gap-4">
              <Select value={filterStatut} onValueChange={(value: ReceptionStatut | 'all') => setFilterStatut(value)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous statuts</SelectItem>
                  <SelectItem value="planifiee">Planifiée</SelectItem>
                  <SelectItem value="en_cours">En cours</SelectItem>
                  <SelectItem value="terminee">Terminée</SelectItem>
                  <SelectItem value="annulee">Annulée</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterType} onValueChange={(value: ReceptionType | 'all') => setFilterType(value)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous types</SelectItem>
                  <SelectItem value="livraison">Livraison</SelectItem>
                  <SelectItem value="validation">Validation</SelectItem>
                  <SelectItem value="probleme">Problème</SelectItem>
                  <SelectItem value="suivi">Suivi</SelectItem>
                </SelectContent>
              </Select>
              <Button className="gap-2" onClick={handleCreateReception}>
                <Plus className="h-4 w-4" />
                Nouvelle réception
              </Button>
            </div>
          </div>

          {/* Tableau des réceptions */}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Ordre du jour</TableHead>
                  <TableHead>Participants</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Tâches</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredReceptions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                      Aucune réception trouvée
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredReceptions.map((reception) => {
                    const taches = getTachesForReception(reception.id);
                    return (
                      <TableRow key={reception.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-gray-400" />
                            {formatDate(reception.date)}
                          </div>
                        </TableCell>
                        <TableCell>{getTypeBadge(reception.type)}</TableCell>
                        <TableCell className="max-w-xs truncate" title={reception.ordreDuJour}>
                          {reception.ordreDuJour}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Users className="h-4 w-4 text-gray-400" />
                            <span className="truncate max-w-[150px]" title={reception.participants.join(', ')}>
                              {reception.participants.length} participant(s)
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>{getStatutBadge(reception.statut)}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={taches.length > 0 ? 'bg-gray-50' : ''}>
                            {taches.length} tâche(s)
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewDetails(reception)}
                            className="gap-2"
                          >
                            <Eye className="h-4 w-4" />
                            Détails
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>

          {/* Résumé */}
          <div className="mt-4 text-sm text-gray-500">
            {filteredReceptions.length} réception(s) trouvée(s)
            {filterStatut !== 'all' && ` • Statut: ${filterStatut}`}
            {filterType !== 'all' && ` • Type: ${filterType}`}
          </div>
        </CardContent>
      </Card>

      {/* Modal de détails */}
      {selectedReception && (
        <Card id="detail-card" className="mt-6">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Détails de la réception
              </CardTitle>
              <div className="flex gap-2">
                {editReceptionMode && <Button size="sm" onClick={async () => {
                  await handleUpdateReception(selectedReception.id, editReceptionForm);
                  setEditReceptionMode(false);
                }}>Sauvegarder</Button>}
                <Button variant={editReceptionMode ? "outline" : "default"} size="sm" onClick={() => {
                  if (!editReceptionMode) {
                    const d = typeof selectedReception.date === 'string' ? selectedReception.date.split('T')[0] : '';
                    setEditReceptionForm({ date: d, type: selectedReception.type, commentaires: '' });
                  }
                  setEditReceptionMode(!editReceptionMode);
                }}>{editReceptionMode ? 'Annuler' : 'Modifier'}</Button>
                <Button variant="ghost" size="sm" onClick={() => { setEditReceptionMode(false); handleCloseDetails(); }}>Fermer</Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {editReceptionMode ? (
              <>
                <div className="space-y-2">
                  <Label>Date</Label>
                  <Input type="date" value={editReceptionForm.date} onChange={(e) => setEditReceptionForm({...editReceptionForm, date: e.target.value})} />
                </div>
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select value={editReceptionForm.type} onValueChange={(v: ReceptionType) => setEditReceptionForm({...editReceptionForm, type: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="livraison">Livraison</SelectItem>
                      <SelectItem value="validation">Validation</SelectItem>
                      <SelectItem value="probleme">Problème</SelectItem>
                      <SelectItem value="suivi">Suivi</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Commentaires</Label>
                  <Textarea value={editReceptionForm.commentaires} onChange={(e) => setEditReceptionForm({...editReceptionForm, commentaires: e.target.value})} rows={4} />
                </div>
              </>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm font-medium text-gray-500">Date</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Calendar className="h-4 w-4 text-gray-400" />
                      {formatDate(selectedReception.date)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-500">Type</div>
                    <div className="mt-1">{getTypeBadge(selectedReception.type)}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-500">Statut</div>
                    <div className="mt-1">{getStatutBadge(selectedReception.statut)}</div>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500 mb-2">Participants</div>
                  <div className="flex flex-wrap gap-2">
                    {selectedReception.participants.map((p, i) => (
                      <Badge key={i} variant="outline" className="bg-gray-50"><Users className="h-3 w-3 mr-1" />{p}</Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500 mb-2">Ordre du jour</div>
                  <div className="p-4 bg-gray-50 rounded-md whitespace-pre-line">{selectedReception.ordreDuJour}</div>
                </div>
                {selectedReception.decisions && (
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">Décisions prises</div>
                    <div className="p-4 bg-green-50 rounded-md whitespace-pre-line">{selectedReception.decisions}</div>
                  </div>
                )}
                {selectedReception.pointsARegler && (
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">Points à régler</div>
                    <div className="p-4 bg-yellow-50 rounded-md whitespace-pre-line">{selectedReception.pointsARegler}</div>
                  </div>
                )}
              </>
            )}

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button onClick={() => handleValidateReception(selectedReception.id)}>Valider la réception</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}