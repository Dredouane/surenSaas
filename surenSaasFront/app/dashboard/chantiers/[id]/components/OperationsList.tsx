'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Plus, Search, CheckCircle, Clock, XCircle, Mic, Camera, MessageSquare, FileText, User, Calendar, ListChecks } from 'lucide-react';
import { Operation } from '@/types/chantier';
import { scrollToDetail } from '@/lib/scroll-to-detail';

interface OperationsListProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
}

export default function OperationsList({ chantierId, orgId, onRefresh }: OperationsListProps) {
  const [operations, setOperations] = useState<Operation[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterStatut, setFilterStatut] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [filterSource, setFilterSource] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedOperation, setSelectedOperation] = useState<Operation | null>(null);
  const [newOperation, setNewOperation] = useState({ description: '', type: 'autre', montant: '', quantite: '', unite: '' });
  const [editOpMode, setEditOpMode] = useState(false);
  const [editOpForm, setEditOpForm] = useState({ description: '', type: 'autre', montant: '', commentaire: '' });

  useEffect(() => {
    fetchOperations();
  }, [chantierId]);

  const fetchOperations = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/chantiers/${chantierId}/operations?org_id=${orgId}`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setOperations(data.map((o: any) => ({
            id: o.id,
            chantierId: o.chantier_id,
            description: o.description,
            type: o.type || 'autre',
            date: o.date || o.created_at,
            source: o.source || 'manuel',
            sourceDetails: o.source_details || '',
            statut: o.statut || 'en_attente',
            commentaire: o.commentaire,
            montant: o.montant,
            unite: o.unite,
            quantite: o.quantite,
            createdAt: o.created_at,
            updatedAt: o.updated_at || o.created_at,
        })));
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredOperations = operations.filter(operation => {
    if (search && !operation.description.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterStatut !== 'all' && operation.statut !== filterStatut) return false;
    if (filterType !== 'all' && operation.type !== filterType) return false;
    if (filterSource !== 'all' && operation.source !== filterSource) return false;
    return true;
  });

  const stats = {
    total: operations.length,
    valide: operations.filter(op => op.statut === 'valide').length,
    enAttente: operations.filter(op => op.statut === 'en_attente').length,
    reject: operations.filter(op => op.statut === 'rejete').length,
  };

  const getStatutBadge = (statut: string) => {
    switch (statut) {
      case 'valide':
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle className="w-3 h-3 mr-1" /> Validée</Badge>;
      case 'en_attente':
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200"><Clock className="w-3 h-3 mr-1" /> En attente</Badge>;
      case 'rejete':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> Rejetée</Badge>;
      default:
        return <Badge variant="outline">{statut}</Badge>;
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'demolition': return <Badge variant="secondary" className="bg-orange-50 text-orange-700">Démolition</Badge>;
      case 'nettoyage': return <Badge variant="secondary" className="bg-cyan-50 text-cyan-700">Nettoyage</Badge>;
      case 'pose_bso': return <Badge variant="secondary" className="bg-blue-50 text-blue-700">Pose BSO</Badge>;
      case 'commande': return <Badge variant="secondary" className="bg-purple-50 text-purple-700">Commande</Badge>;
      case 'achat_materiel': return <Badge variant="secondary" className="bg-indigo-50 text-indigo-700">Achat matériel</Badge>;
      case 'sous_traitance': return <Badge variant="secondary" className="bg-pink-50 text-pink-700">Sous-traitance</Badge>;
      default: return <Badge variant="secondary">{type}</Badge>;
    }
  };

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'telegram_voice': return <Mic className="w-4 h-4 text-blue-500" />;
      case 'telegram_photo': return <Camera className="w-4 h-4 text-green-500" />;
      case 'telegram_text': return <MessageSquare className="w-4 h-4 text-gray-500" />;
      case 'manuel': return <FileText className="w-4 h-4 text-orange-500" />;
      default: return <ListChecks className="w-4 h-4 text-gray-400" />;
    }
  };

  const formatDate = (dateString: string | Date) => {
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  const handleCreateOperation = async () => {
    if (!newOperation.description.trim()) { alert('Veuillez entrer une description'); return; }
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/operations?org_id=${orgId}`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: newOperation.description,
          type: newOperation.type,
          source: 'manuel',
          montant: parseFloat(newOperation.montant) || undefined,
          quantite: parseFloat(newOperation.quantite) || undefined,
          unite: newOperation.unite || undefined,
        }),
      });
      if (!res.ok) throw new Error('Erreur création opération');
      setShowCreateDialog(false);
      setNewOperation({ description: '', type: 'autre', montant: '', quantite: '', unite: '' });
      fetchOperations();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  const handleValidateOperation = async (id: string, statut: string) => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/operations/${id}?org_id=${orgId}`, {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statut }),
      });
      if (!res.ok) throw new Error('Erreur mise à jour opération');
      setSelectedOperation(null);
      fetchOperations();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  const handleResetFilters = () => {
    setSearch('');
    setFilterStatut('all');
    setFilterType('all');
    setFilterSource('all');
  };

  if (loading) return <div className="p-4">Chargement...</div>;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <CardTitle>Opérations ({stats.total})</CardTitle>
            <div className="flex gap-2">
              <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogTrigger asChild>
                  <Button size="sm" className="gap-2"><Plus className="h-4 w-4" />Nouvelle opération</Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[500px]">
                  <DialogHeader>
                    <DialogTitle>Signaler une opération</DialogTitle>
                    <DialogDescription>Ajouter une opération manuelle au chantier.</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Description *</Label>
                      <Textarea placeholder="Décrivez l'opération..." value={newOperation.description} onChange={(e) => setNewOperation({...newOperation, description: e.target.value})} rows={3} />
                    </div>
                    <div className="space-y-2">
                      <Label>Type</Label>
                      <Select value={newOperation.type} onValueChange={(v) => setNewOperation({...newOperation, type: v})}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="demolition">Démolition</SelectItem>
                          <SelectItem value="nettoyage">Nettoyage</SelectItem>
                          <SelectItem value="pose_bso">Pose BSO</SelectItem>
                          <SelectItem value="commande">Commande</SelectItem>
                          <SelectItem value="achat_materiel">Achat matériel</SelectItem>
                          <SelectItem value="sous_traitance">Sous-traitance</SelectItem>
                          <SelectItem value="autre">Autre</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>Montant (€)</Label>
                        <Input type="number" step="0.01" min="0" placeholder="0" value={newOperation.montant} onChange={(e) => setNewOperation({...newOperation, montant: e.target.value})} />
                      </div>
                      <div className="space-y-2">
                        <Label>Quantité</Label>
                        <Input type="number" step="1" min="0" placeholder="0" value={newOperation.quantite} onChange={(e) => setNewOperation({...newOperation, quantite: e.target.value})} />
                      </div>
                      <div className="space-y-2">
                        <Label>Unité</Label>
                        <Input placeholder="m², unités..." value={newOperation.unite} onChange={(e) => setNewOperation({...newOperation, unite: e.target.value})} />
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Annuler</Button>
                    <Button onClick={handleCreateOperation}>Créer</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              <Button onClick={fetchOperations} size="sm">Rafraîchir</Button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary" className="bg-green-50 text-green-700">{stats.valide} validée(s)</Badge>
            <Badge variant="secondary" className="bg-yellow-50 text-yellow-700">{stats.enAttente} en attente</Badge>
            <Badge variant="secondary" className="bg-red-50 text-red-700">{stats.reject} rejetée(s)</Badge>
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Rechercher..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-8" />
            </div>
            <Select value={filterStatut} onValueChange={setFilterStatut}>
              <SelectTrigger className="w-[140px]"><SelectValue placeholder="Statut" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                <SelectItem value="en_attente">En attente</SelectItem>
                <SelectItem value="valide">Validée</SelectItem>
                <SelectItem value="rejete">Rejetée</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-[140px]"><SelectValue placeholder="Type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                <SelectItem value="demolition">Démolition</SelectItem>
                <SelectItem value="nettoyage">Nettoyage</SelectItem>
                <SelectItem value="pose_bso">Pose BSO</SelectItem>
                <SelectItem value="commande">Commande</SelectItem>
                <SelectItem value="achat_materiel">Achat matériel</SelectItem>
                <SelectItem value="sous_traitance">Sous-traitance</SelectItem>
                <SelectItem value="autre">Autre</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterSource} onValueChange={setFilterSource}>
              <SelectTrigger className="w-[140px]"><SelectValue placeholder="Source" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes</SelectItem>
                <SelectItem value="telegram_text">Texte</SelectItem>
                <SelectItem value="telegram_voice">Vocal</SelectItem>
                <SelectItem value="telegram_photo">Photo</SelectItem>
                <SelectItem value="manuel">Manuelle</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="ghost" size="sm" onClick={handleResetFilters}>Réinitialiser</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filteredOperations.length === 0 ? (
          <p className="text-muted-foreground p-4">Aucune opération trouvée.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredOperations.map((op) => (
                <TableRow key={op.id}>
                  <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                    <Calendar className="w-3 h-3 inline mr-1" />
                    {formatDate(op.date)}
                  </TableCell>
                  <TableCell className="font-medium max-w-xs truncate">{op.description}</TableCell>
                  <TableCell>{getTypeBadge(op.type)}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {getSourceIcon(op.source)}
                      <span className="text-xs text-muted-foreground">{op.source}</span>
                    </div>
                  </TableCell>
                  <TableCell>{getStatutBadge(op.statut)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex gap-1 justify-end">
                      <Button variant="ghost" size="sm" onClick={() => { setSelectedOperation(op); scrollToDetail(); }}>Détails</Button>
                      {op.statut === 'en_attente' && (
                        <Button variant="outline" size="sm" className="text-green-600" onClick={() => handleValidateOperation(op.id, 'valide')}>Valider</Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {selectedOperation && (
        <Card id="detail-card" className="mt-6">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2">
                <ListChecks className="h-5 w-5" />
                Détail de l'opération
              </CardTitle>
              <div className="flex gap-2">
                {editOpMode && <Button size="sm" onClick={async () => {
                  await fetch(`/api/v1/chantiers/${chantierId}/operations/${selectedOperation.id}?org_id=${orgId}`, {
                    method: 'PUT', credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ...editOpForm, montant: parseFloat(editOpForm.montant) || undefined }),
                  });
                  setEditOpMode(false);
                  fetchOperations();
                }}>Sauvegarder</Button>}
                <Button variant={editOpMode ? "outline" : "default"} size="sm" onClick={() => {
                  if (!editOpMode) {
                    setEditOpForm({
                      description: selectedOperation.description,
                      type: selectedOperation.type,
                      montant: String(selectedOperation.montant || ''),
                      commentaire: selectedOperation.commentaire || '',
                    });
                  }
                  setEditOpMode(!editOpMode);
                }}>{editOpMode ? 'Annuler' : 'Modifier'}</Button>
                <Button variant="ghost" size="sm" onClick={() => { setSelectedOperation(null); setEditOpMode(false); }}>Fermer</Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {editOpMode ? (
              <>
                <div className="space-y-2"><Label>Description</Label><Textarea value={editOpForm.description} onChange={(e) => setEditOpForm({...editOpForm, description: e.target.value})} rows={3} /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Type</Label>
                    <Select value={editOpForm.type} onValueChange={(v) => setEditOpForm({...editOpForm, type: v})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="demolition">Démolition</SelectItem>
                        <SelectItem value="nettoyage">Nettoyage</SelectItem>
                        <SelectItem value="pose_bso">Pose BSO</SelectItem>
                        <SelectItem value="commande">Commande</SelectItem>
                        <SelectItem value="achat_materiel">Achat matériel</SelectItem>
                        <SelectItem value="sous_traitance">Sous-traitance</SelectItem>
                        <SelectItem value="autre">Autre</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2"><Label>Montant (€)</Label><Input type="number" step="0.01" value={editOpForm.montant} onChange={(e) => setEditOpForm({...editOpForm, montant: e.target.value})} /></div>
                </div>
                <div className="space-y-2"><Label>Commentaire</Label><Textarea value={editOpForm.commentaire} onChange={(e) => setEditOpForm({...editOpForm, commentaire: e.target.value})} rows={2} /></div>
              </>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2"><Label>Description</Label><p className="font-medium">{selectedOperation.description}</p></div>
                <div><Label>Type</Label><p>{getTypeBadge(selectedOperation.type)}</p></div>
                <div><Label>Statut</Label><p>{getStatutBadge(selectedOperation.statut)}</p></div>
                <div><Label>Date</Label><p className="text-sm">{formatDate(selectedOperation.date)}</p></div>
                <div><Label>Source</Label><p className="text-sm">{selectedOperation.source}</p></div>
                {selectedOperation.montant && <div><Label>Montant</Label><p>{selectedOperation.montant}€</p></div>}
                {selectedOperation.commentaire && <div><Label>Commentaire</Label><p className="text-sm">{selectedOperation.commentaire}</p></div>}
              </div>
            )}
            {selectedOperation.statut === 'en_attente' && (
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => { handleValidateOperation(selectedOperation.id, 'rejete'); setSelectedOperation(null); }} className="text-red-600">Rejeter</Button>
                <Button onClick={() => { handleValidateOperation(selectedOperation.id, 'valide'); setSelectedOperation(null); }}>Valider</Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </Card>
  );
}
