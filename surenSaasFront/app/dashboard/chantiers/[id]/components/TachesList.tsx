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
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Plus,
  Search,
  Calendar,
  User,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  XCircle,
  Eye,
  MessageSquare,
  Bell,
  Building,
  Paperclip,
  Send,
} from 'lucide-react';
import { Tache, TacheStatut, TacheType, TachePriorite } from '@/types/chantier';
import { scrollToDetail } from '@/lib/scroll-to-detail';

interface TachesListProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
}

export default function TachesList({ chantierId, orgId, onRefresh }: TachesListProps) {
  const [taches, setTaches] = useState<Tache[]>([]);
  const [search, setSearch] = useState('');
  const [filterStatut, setFilterStatut] = useState<TacheStatut | 'all'>('all');
  const [filterType, setFilterType] = useState<TacheType | 'all'>('all');
  const [filterPriorite, setFilterPriorite] = useState<TachePriorite | 'all'>('all');
  const [selectedTache, setSelectedTache] = useState<Tache | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState({ titre: '', description: '', priorite: '' as TachePriorite, type: '' as TacheType });
  const [newTache, setNewTache] = useState({
    titre: '',
    description: '',
    type: 'action' as TacheType,
    assigneeId: '',
    echeance: '',
    priorite: 'moyenne' as TachePriorite,
  });

  useEffect(() => {
    fetchTaches();
  }, [chantierId]);

  const fetchTaches = async () => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/taches?org_id=${orgId}`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setTaches(data.map((t: any) => ({
          id: t.id,
          chantierId: t.chantier_id,
          titre: t.titre,
          description: t.description || '',
          type: t.type || 'action',
          source: t.source || 'direction',
          createurId: t.createur_id || '',
          createurNom: t.createur_nom || '',
          assigneeId: t.assignee_id || '',
          assigneeNom: t.assignee_nom || '',
          echeance: t.echeance || undefined,
          statut: t.statut || 'en_attente',
          priorite: t.priorite || 'moyenne',
          reponse: t.reponse || '',
          documents: t.documents || [],
          notifications: [],
          createdAt: t.created_at,
          updatedAt: t.updated_at || t.created_at,
        })));
      }
    } catch (err) {
      console.error('Erreur chargement tâches:', err);
    }
  };

  // Filtrer les tâches
  const filteredTaches = taches.filter(tache => {
    if (search && !tache.titre.toLowerCase().includes(search.toLowerCase()) && 
        !tache.description.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (filterStatut !== 'all' && tache.statut !== filterStatut) {
      return false;
    }
    if (filterType !== 'all' && tache.type !== filterType) {
      return false;
    }
    if (filterPriorite !== 'all' && tache.priorite !== filterPriorite) {
      return false;
    }
    if (chantierId && tache.chantierId !== chantierId) {
      return false;
    }
    return true;
  });

  // Obtenir le badge de statut
  const getStatutBadge = (statut: TacheStatut) => {
    switch (statut) {
      case 'en_attente':
        return <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200"><Clock className="w-3 h-3 mr-1" /> En attente</Badge>;
      case 'en_cours':
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200"><AlertCircle className="w-3 h-3 mr-1" /> En cours</Badge>;
      case 'terminee':
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle className="w-3 h-3 mr-1" /> Terminée</Badge>;
      case 'annulee':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> Annulée</Badge>;
    }
  };

  // Obtenir le badge de type
  const getTypeBadge = (type: TacheType) => {
    switch (type) {
      case 'information':
        return <Badge variant="secondary" className="bg-blue-50 text-blue-700">Information</Badge>;
      case 'action':
        return <Badge variant="secondary" className="bg-purple-50 text-purple-700">Action</Badge>;
      case 'validation':
        return <Badge variant="secondary" className="bg-green-50 text-green-700">Validation</Badge>;
      case 'rapport':
        return <Badge variant="secondary" className="bg-orange-50 text-orange-700">Rapport</Badge>;
    }
  };

  // Obtenir le badge de priorité
  const getPrioriteBadge = (priorite: TachePriorite) => {
    switch (priorite) {
      case 'basse':
        return <Badge variant="outline" className="bg-gray-50 text-gray-600">Basse</Badge>;
      case 'moyenne':
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-600">Moyenne</Badge>;
      case 'haute':
        return <Badge variant="outline" className="bg-red-50 text-red-600">Haute</Badge>;
    }
  };

  // Formater la date
  const formatDate = (dateString: string | Date | undefined) => {
    if (!dateString) return 'Non définie';
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Grouper les tâches par statut pour la vue Kanban
  const tachesParStatut = {
    en_attente: filteredTaches.filter(t => t.statut === 'en_attente'),
    en_cours: filteredTaches.filter(t => t.statut === 'en_cours'),
    terminee: filteredTaches.filter(t => t.statut === 'terminee'),
    annulee: filteredTaches.filter(t => t.statut === 'annulee'),
  };

  // Handler pour voir les détails
  const handleViewDetails = (tache: Tache) => {
    setSelectedTache(tache);
    scrollToDetail();
  };

  // Handler pour fermer les détails
  const handleCloseDetails = () => {
    setSelectedTache(null);
  };

  // Handler pour créer une nouvelle tâche
  const handleCreateTache = async () => {
    if (!newTache.titre.trim() || !newTache.description.trim()) {
      alert('Veuillez remplir le titre et la description');
      return;
    }
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/taches?org_id=${orgId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titre: newTache.titre,
          description: newTache.description,
          type: newTache.type,
          source: 'direction',
          priorite: newTache.priorite,
          statut: 'en_attente',
          assignee_nom: newTache.assigneeId === 'user-manager-001' ? 'Gérant Principal' : 'Mohsan MAHMOOD',
          createur_nom: 'Utilisateur actuel',
          echeance: newTache.echeance || undefined,
        }),
      });
      if (!res.ok) throw new Error('Erreur création tâche');
      setNewTache({ titre: '', description: '', type: 'action', assigneeId: '', echeance: '', priorite: 'moyenne' });
      setShowCreateDialog(false);
      await fetchTaches();
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  const handleUpdateTache = async (tacheId: string, updates: any) => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/taches/${tacheId}?org_id=${orgId}`, {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!res.ok) throw new Error('Erreur mise à jour');
      fetchTaches();
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  const handleUpdateTacheStatus = async (tacheId: string, newStatut: TacheStatut) => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/taches/${tacheId}?org_id=${orgId}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statut: newStatut }),
      });
      if (!res.ok) throw new Error('Erreur mise à jour tâche');
      setSelectedTache(null);
      fetchTaches();
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  // Liste des assignés disponibles
  const assignees = [
    { id: 'user-mohsan-001', nom: 'Mohsan MAHMOOD (Conducteur)' },
    { id: 'user-manager-001', nom: 'Gérant Principal' },
    { id: 'user-system-001', nom: 'Système' },
  ];

  return (
    <div className="space-y-6">
      {/* En-tête avec filtres */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Tâches {chantierId ? 'du chantier' : 'générales'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Rechercher dans les titres et descriptions..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex gap-4">
              <Select value={filterStatut} onValueChange={(value: TacheStatut | 'all') => setFilterStatut(value)}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous statuts</SelectItem>
                  <SelectItem value="en_attente">En attente</SelectItem>
                  <SelectItem value="en_cours">En cours</SelectItem>
                  <SelectItem value="terminee">Terminée</SelectItem>
                  <SelectItem value="annulee">Annulée</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterType} onValueChange={(value: TacheType | 'all') => setFilterType(value)}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous types</SelectItem>
                  <SelectItem value="information">Information</SelectItem>
                  <SelectItem value="action">Action</SelectItem>
                  <SelectItem value="validation">Validation</SelectItem>
                  <SelectItem value="rapport">Rapport</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterPriorite} onValueChange={(value: TachePriorite | 'all') => setFilterPriorite(value)}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Priorité" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes priorités</SelectItem>
                  <SelectItem value="basse">Basse</SelectItem>
                  <SelectItem value="moyenne">Moyenne</SelectItem>
                  <SelectItem value="haute">Haute</SelectItem>
                </SelectContent>
              </Select>
              <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogTrigger asChild>
                  <Button className="gap-2">
                    <Plus className="h-4 w-4" />
                    Nouvelle tâche
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[600px]">
                  <DialogHeader>
                    <DialogTitle>Créer une nouvelle tâche</DialogTitle>
                    <DialogDescription>
                      Remplissez les informations ci-dessous. Une notification Telegram sera envoyée à l'assigné.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="titre">Titre *</Label>
                      <Input
                        id="titre"
                        placeholder="Ex: Vérifier fondations, Envoyer photos..."
                        value={newTache.titre}
                        onChange={(e) => setNewTache({...newTache, titre: e.target.value})}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="description">Description *</Label>
                      <Textarea
                        id="description"
                        placeholder="Détails de la tâche, instructions spécifiques..."
                        value={newTache.description}
                        onChange={(e) => setNewTache({...newTache, description: e.target.value})}
                        rows={3}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="type">Type</Label>
                        <Select
                          value={newTache.type}
                          onValueChange={(value: TacheType) => setNewTache({...newTache, type: value})}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="information">Information</SelectItem>
                            <SelectItem value="action">Action</SelectItem>
                            <SelectItem value="validation">Validation</SelectItem>
                            <SelectItem value="rapport">Rapport</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="priorite">Priorité</Label>
                        <Select
                          value={newTache.priorite}
                          onValueChange={(value: TachePriorite) => setNewTache({...newTache, priorite: value})}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="basse">Basse</SelectItem>
                            <SelectItem value="moyenne">Moyenne</SelectItem>
                            <SelectItem value="haute">Haute</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="assignee">Assignée à</Label>
                        <Select
                          value={newTache.assigneeId}
                          onValueChange={(value) => setNewTache({...newTache, assigneeId: value})}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Sélectionner un assigné" />
                          </SelectTrigger>
                          <SelectContent>
                            {assignees.map(assignee => (
                              <SelectItem key={assignee.id} value={assignee.id}>
                                {assignee.nom}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="echeance">Échéance (optionnel)</Label>
                        <Input
                          id="echeance"
                          type="datetime-local"
                          value={newTache.echeance}
                          onChange={(e) => setNewTache({...newTache, echeance: e.target.value})}
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="documents">Documents (optionnel)</Label>
                      <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" className="gap-2">
                          <Paperclip className="h-4 w-4" />
                          Ajouter des fichiers
                        </Button>
                        <span className="text-sm text-muted-foreground">
                          Formats supportés: PDF, images, documents
                        </span>
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                      Annuler
                    </Button>
                    <Button onClick={handleCreateTache} className="gap-2">
                      <Send className="h-4 w-4" />
                      Créer et notifier
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>

          {/* Vue Kanban */}
          <div className="mb-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Colonne En attente */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-700">En attente</h3>
                  <Badge variant="outline" className="bg-gray-50">
                    {tachesParStatut.en_attente.length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {tachesParStatut.en_attente.map((tache) => (
                    <div 
                      key={tache.id} 
                      className="p-3 border rounded-md bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => handleViewDetails(tache)}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="font-medium text-sm">{tache.titre}</div>
                        {getPrioriteBadge(tache.priorite)}
                      </div>
                      <div className="text-xs text-gray-500 truncate mb-2">
                        {tache.description}
                      </div>
                      <div className="flex justify-between items-center text-xs text-gray-500">
                        <div className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {tache.assigneeNom}
                        </div>
                        {tache.echeance && (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(tache.echeance).split(' ')[0]}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {tachesParStatut.en_attente.length === 0 && (
                    <div className="text-center py-4 text-gray-400 text-sm border border-dashed rounded-md">
                      Aucune tâche
                    </div>
                  )}
                </div>
              </div>

              {/* Colonne En cours */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-700">En cours</h3>
                  <Badge variant="outline" className="bg-yellow-50">
                    {tachesParStatut.en_cours.length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {tachesParStatut.en_cours.map((tache) => (
                    <div 
                      key={tache.id} 
                      className="p-3 border rounded-md bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => handleViewDetails(tache)}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="font-medium text-sm">{tache.titre}</div>
                        {getPrioriteBadge(tache.priorite)}
                      </div>
                      <div className="text-xs text-gray-500 truncate mb-2">
                        {tache.description}
                      </div>
                      <div className="flex justify-between items-center text-xs text-gray-500">
                        <div className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {tache.assigneeNom}
                        </div>
                        {tache.echeance && (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(tache.echeance).split(' ')[0]}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {tachesParStatut.en_cours.length === 0 && (
                    <div className="text-center py-4 text-gray-400 text-sm border border-dashed rounded-md">
                      Aucune tâche
                    </div>
                  )}
                </div>
              </div>

              {/* Colonne Terminée */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-700">Terminée</h3>
                  <Badge variant="outline" className="bg-green-50">
                    {tachesParStatut.terminee.length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {tachesParStatut.terminee.map((tache) => (
                    <div 
                      key={tache.id} 
                      className="p-3 border rounded-md bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer opacity-80"
                      onClick={() => handleViewDetails(tache)}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="font-medium text-sm line-through">{tache.titre}</div>
                        {getPrioriteBadge(tache.priorite)}
                      </div>
                      <div className="text-xs text-gray-500 truncate mb-2">
                        {tache.description}
                      </div>
                      <div className="flex justify-between items-center text-xs text-gray-500">
                        <div className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {tache.assigneeNom}
                        </div>
                        {tache.echeance && (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(tache.echeance).split(' ')[0]}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {tachesParStatut.terminee.length === 0 && (
                    <div className="text-center py-4 text-gray-400 text-sm border border-dashed rounded-md">
                      Aucune tâche
                    </div>
                  )}
                </div>
              </div>

              {/* Colonne Annulée */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-700">Annulée</h3>
                  <Badge variant="outline" className="bg-red-50">
                    {tachesParStatut.annulee.length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {tachesParStatut.annulee.map((tache) => (
                    <div 
                      key={tache.id} 
                      className="p-3 border rounded-md bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer opacity-60"
                      onClick={() => handleViewDetails(tache)}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="font-medium text-sm line-through text-gray-500">{tache.titre}</div>
                        {getPrioriteBadge(tache.priorite)}
                      </div>
                      <div className="text-xs text-gray-500 truncate mb-2">
                        {tache.description}
                      </div>
                      <div className="flex justify-between items-center text-xs text-gray-500">
                        <div className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {tache.assigneeNom}
                        </div>
                        {tache.echeance && (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(tache.echeance).split(' ')[0]}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {tachesParStatut.annulee.length === 0 && (
                    <div className="text-center py-4 text-gray-400 text-sm border border-dashed rounded-md">
                      Aucune tâche
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Tableau des tâches (vue alternative) */}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Titre</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Assignée à</TableHead>
                  <TableHead>Échéance</TableHead>
                  <TableHead>Priorité</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTaches.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                      Aucune tâche trouvée
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTaches.map((tache) => (
                    <TableRow key={tache.id}>
                      <TableCell>
                        <div className="font-medium">{tache.titre}</div>
                        <div className="text-sm text-gray-500 truncate max-w-xs">
                          {tache.description}
                        </div>
                      </TableCell>
                      <TableCell>{getTypeBadge(tache.type)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-gray-400" />
                          {tache.assigneeNom}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-gray-400" />
                          {tache.echeance ? formatDate(tache.echeance) : 'Non définie'}
                        </div>
                      </TableCell>
                      <TableCell>{getPrioriteBadge(tache.priorite)}</TableCell>
                      <TableCell>{getStatutBadge(tache.statut)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewDetails(tache)}
                          className="gap-2"
                        >
                          <Eye className="h-4 w-4" />
                          Détails
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Résumé */}
          <div className="mt-4 text-sm text-gray-500">
            {filteredTaches.length} tâche(s) trouvée(s)
            {filterStatut !== 'all' && ` • Statut: ${filterStatut}`}
            {filterType !== 'all' && ` • Type: ${filterType}`}
            {filterPriorite !== 'all' && ` • Priorité: ${filterPriorite}`}
          </div>
        </CardContent>
      </Card>

      {/* Modal de détails */}
      {selectedTache && (
        <Card id="detail-card" className="mt-6">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Détails de la tâche
              </CardTitle>
              <div className="flex gap-2">
                {editMode && <Button size="sm" onClick={async () => {
                  await handleUpdateTache(selectedTache.id, editForm);
                  setEditMode(false);
                }}>Sauvegarder</Button>}
                <Button variant={editMode ? "outline" : "default"} size="sm" onClick={() => {
                  if (!editMode) {
                    setEditForm({ titre: selectedTache.titre, description: selectedTache.description, priorite: selectedTache.priorite, type: selectedTache.type });
                  }
                  setEditMode(!editMode);
                }}>{editMode ? 'Annuler' : 'Modifier'}</Button>
                <Button variant="ghost" size="sm" onClick={() => { setEditMode(false); handleCloseDetails(); }}>
                  Fermer
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {editMode ? (
              <>
                <div className="space-y-2">
                  <Label>Titre</Label>
                  <Input value={editForm.titre} onChange={(e) => setEditForm({...editForm, titre: e.target.value})} />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea value={editForm.description} onChange={(e) => setEditForm({...editForm, description: e.target.value})} rows={4} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Type</Label>
                    <Select value={editForm.type} onValueChange={(v: TacheType) => setEditForm({...editForm, type: v})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="information">Information</SelectItem>
                        <SelectItem value="action">Action</SelectItem>
                        <SelectItem value="validation">Validation</SelectItem>
                        <SelectItem value="rapport">Rapport</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Priorité</Label>
                    <Select value={editForm.priorite} onValueChange={(v: TachePriorite) => setEditForm({...editForm, priorite: v})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="basse">Basse</SelectItem>
                        <SelectItem value="moyenne">Moyenne</SelectItem>
                        <SelectItem value="haute">Haute</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm font-medium text-gray-500">Créée le</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Calendar className="h-4 w-4 text-gray-400" />
                      {formatDate(selectedTache.createdAt)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-500">Type</div>
                    <div className="mt-1">{getTypeBadge(selectedTache.type)}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-500">Priorité</div>
                    <div className="mt-1">{getPrioriteBadge(selectedTache.priorite)}</div>
                  </div>
                </div>

                <div>
                  <div className="text-sm font-medium text-gray-500 mb-2">Titre</div>
                  <div className="text-lg font-medium">{selectedTache.titre}</div>
                </div>

                <div>
                  <div className="text-sm font-medium text-gray-500 mb-2">Description</div>
                  <div className="p-4 bg-gray-50 rounded-md whitespace-pre-line">
                    {selectedTache.description}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">Assignée à</div>
                    <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-md">
                      <User className="h-5 w-5 text-gray-400" />
                      <div>
                        <div className="font-medium">{selectedTache.assigneeNom}</div>
                        <div className="text-sm text-gray-500">Conducteur de travaux</div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">Échéance</div>
                    <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-md">
                      <Calendar className="h-5 w-5 text-gray-400" />
                      <div>
                        <div className="font-medium">
                          {selectedTache.echeance ? formatDate(selectedTache.echeance) : 'Non définie'}
                        </div>
                        <div className="text-sm text-gray-500">
                          {selectedTache.echeance && (
                            new Date(selectedTache.echeance) < new Date() ? 'Échéance dépassée' : 'Dans les délais'
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {selectedTache.chantierId && (
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">Chantier associé</div>
                    <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-md">
                      <Building className="h-5 w-5 text-blue-400" />
                      <div>
                        <div className="font-medium">Chantier {selectedTache.chantierId}</div>
                        <div className="text-sm text-gray-500">Tâche spécifique au chantier</div>
                      </div>
                    </div>
                  </div>
                )}

                {selectedTache.reponse && (
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">Réponse du conducteur</div>
                    <div className="p-4 bg-green-50 rounded-md whitespace-pre-line">{selectedTache.reponse}</div>
                  </div>
                )}

                {selectedTache.documents.length > 0 && (
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">Documents joints</div>
                    <div className="space-y-2">
                      {selectedTache.documents.map((doc, index) => (
                        <div key={index} className="flex items-center gap-2 p-3 border rounded-md">
                          <FileText className="h-4 w-4 text-gray-400" />
                          <div className="flex-1">Document {index + 1}</div>
                          <Button variant="ghost" size="sm">Télécharger</Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedTache.notifications.length > 0 && (
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">Historique des notifications</div>
                    <div className="space-y-2">
                      {selectedTache.notifications.map((notif, index) => (
                        <div key={index} className="p-3 border rounded-md text-sm">
                          <div className="font-medium">{notif.titre}</div>
                          <div className="text-gray-500">{notif.message}</div>
                          <div className="text-xs text-gray-400 mt-1">{formatDate(notif.createdAt)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            <div className="flex justify-end gap-2 pt-4 border-t">
              {selectedTache.statut === 'en_attente' && (
                <Button onClick={() => handleUpdateTacheStatus(selectedTache.id, 'en_cours')}>Marquer comme en cours</Button>
              )}
              {selectedTache.statut === 'en_cours' && (
                <Button onClick={() => handleUpdateTacheStatus(selectedTache.id, 'terminee')}>Marquer comme terminée</Button>
              )}
              {selectedTache.statut === 'terminee' && (
                <Button variant="outline" onClick={() => handleUpdateTacheStatus(selectedTache.id, 'en_attente')}>Réouvrir</Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}