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
  Filter,
  DollarSign,
  Calendar,
  Building,
  Package,
  Clock,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Depense } from '@/types/chantier';
import { scrollToDetail } from '@/lib/scroll-to-detail';
import DepenseDetailView from './DepenseDetailView';

interface DepensesTableProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
}

export default function DepensesTable({ chantierId, orgId, onRefresh }: DepensesTableProps) {
  const [depenses, setDepenses] = useState<Depense[]>([]);
  const [search, setSearch] = useState('');
  const [filterCategorie, setFilterCategorie] = useState('all');
  const [filterFournisseur, setFilterFournisseur] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedDepense, setSelectedDepense] = useState<any>(null);
  const [editDepenseMode, setEditDepenseMode] = useState(false);
  const [editDepenseForm, setEditDepenseForm] = useState({ fournisseur: '', description: '', montant: '', categorie: 'autre', date: '' });
  const [newDepense, setNewDepense] = useState({
    fournisseur: '',
    description: '',
    montant: '',
    categorie: 'autre',
  });

  useEffect(() => {
    fetchDepenses();
  }, [chantierId]);

  const fetchDepenses = async () => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/depenses?org_id=${orgId}`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setDepenses(data.map((d: any) => ({
          id: d.id,
          chantierId: d.chantier_id,
          date: d.date || d.created_at,
          fournisseur: d.fournisseur || '',
          categorie: d.categorie || 'autre',
          description: d.description || '',
          montant: d.montant,
          factureRef: d.facture_ref,
          statut: d.statut || 'validee',
          validePar: d.valide_par || '',
          invoiceId: d.invoice_id,
          invoiceItems: d.invoice_items || [],
          createdAt: d.created_at,
          updatedAt: d.updated_at || d.created_at,
        })));
      }
    } catch (err) {
      console.error('Erreur chargement depenses:', err);
    }
  };

  // Filtrer les dépenses
  const filteredDepenses = depenses.filter(depense => {
    if (search && !depense.description.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (filterCategorie !== 'all' && depense.categorie !== filterCategorie) {
      return false;
    }
    if (filterFournisseur !== 'all' && !depense.fournisseur.toLowerCase().includes(filterFournisseur.toLowerCase())) {
      return false;
    }
    return true;
  });

  // Calculer les totaux
  const totalDepenses = filteredDepenses.reduce((total, depense) => total + depense.montant, 0);
  
  // Calculer par catégorie
  const totalSousTraitant = filteredDepenses
    .filter(d => d.categorie === 'sous_traitant')
    .reduce((total, d) => total + d.montant, 0);
  
  const totalFournisseur = filteredDepenses
    .filter(d => d.categorie === 'fournisseur')
    .reduce((total, d) => total + d.montant, 0);
  
  const totalAutre = filteredDepenses
    .filter(d => d.categorie === 'autre')
    .reduce((total, d) => total + d.montant, 0);

  // Liste unique des fournisseurs
  const fournisseurs = Array.from(new Set(depenses.map(d => d.fournisseur)));

  // Formater une date
  const formatDate = (dateString: string | Date) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR');
  };

  // Formater un montant
  const formatMontant = (montant: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(montant);
  };

  // Obtenir la couleur du badge selon la catégorie
  const getCategorieBadge = (categorie: string) => {
    switch (categorie) {
      case 'sous_traitant':
        return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Sous-traitant</Badge>;
      case 'fournisseur':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Fournisseur</Badge>;
      case 'autre':
        return <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100">Autre</Badge>;
      default:
        return <Badge variant="outline">{categorie}</Badge>;
    }
  };

  // Handler pour créer une dépense via dialog
  const handleCreateDepense = async () => {
    if (!newDepense.fournisseur.trim() || !newDepense.description.trim() || !newDepense.montant) {
      alert('Veuillez remplir le fournisseur, la description et le montant');
      return;
    }
    const montant = parseFloat(newDepense.montant);
    if (isNaN(montant) || montant <= 0) {
      alert('Montant invalide');
      return;
    }
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/depenses?org_id=${orgId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: new Date().toISOString().split('T')[0],
          fournisseur: newDepense.fournisseur,
          categorie: newDepense.categorie,
          description: newDepense.description,
          montant,
        }),
      });
      if (!res.ok) throw new Error('Erreur création dépense');
      setShowCreateDialog(false);
      setNewDepense({ fournisseur: '', description: '', montant: '', categorie: 'autre' });
      fetchDepenses();
      onRefresh?.();
    } catch (err) {
      alert('Erreur lors de la création : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  // Handler pour réinitialiser les filtres
  const handleResetFilters = () => {
    setSearch('');
    setFilterCategorie('all');
    setFilterFournisseur('all');
  };

  // Vue détail d'une dépense
  if (selectedDepense) {
    return (
      <DepenseDetailView
        depense={{
          id: selectedDepense.id,
          fournisseur: selectedDepense.fournisseur,
          montant: selectedDepense.montant,
          description: selectedDepense.description,
          date: selectedDepense.date,
          categorie: selectedDepense.categorie,
          statut: selectedDepense.statut,
          invoice_id: selectedDepense.invoiceId,
          invoice_items: selectedDepense.invoiceItems,
          facture_ref: selectedDepense.factureRef,
        }}
        onBack={() => setSelectedDepense(null)}
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <CardTitle>Dépenses chantier</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              {filteredDepenses.length} dépense{filteredDepenses.length > 1 ? 's' : ''} • Total: {formatMontant(totalDepenses)}
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-3">
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <DialogTrigger asChild>
                <Button className="gap-2">
                  <Plus className="h-4 w-4" />
                  Ajouter une dépense
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                  <DialogTitle>Nouvelle dépense</DialogTitle>
                  <DialogDescription>Ajouter une dépense au chantier.</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label>Fournisseur *</Label>
                    <Input
                      placeholder="Nom du fournisseur"
                      value={newDepense.fournisseur}
                      onChange={(e) => setNewDepense({...newDepense, fournisseur: e.target.value})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Description *</Label>
                    <Input
                      placeholder="Description de la dépense"
                      value={newDepense.description}
                      onChange={(e) => setNewDepense({...newDepense, description: e.target.value})}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Montant HT (€) *</Label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="0.00"
                        value={newDepense.montant}
                        onChange={(e) => setNewDepense({...newDepense, montant: e.target.value})}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Catégorie</Label>
                      <Select
                        value={newDepense.categorie}
                        onValueChange={(v) => setNewDepense({...newDepense, categorie: v})}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="sous_traitant">Sous-traitant</SelectItem>
                          <SelectItem value="fournisseur">Fournisseur</SelectItem>
                          <SelectItem value="autre">Autre</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Annuler</Button>
                  <Button onClick={handleCreateDepense}>Créer la dépense</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Filtres */}
        <div className="flex flex-col lg:flex-row gap-4 mb-6 p-4 border rounded-lg bg-muted/20">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher par description..."
                className="pl-10"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-3">
            <Select
              value={filterCategorie}
              onValueChange={setFilterCategorie}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Catégorie" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes catégories</SelectItem>
                <SelectItem value="sous_traitant">Sous-traitant</SelectItem>
                <SelectItem value="fournisseur">Fournisseur</SelectItem>
                <SelectItem value="autre">Autre</SelectItem>
              </SelectContent>
            </Select>
            
            <Select
              value={filterFournisseur}
              onValueChange={setFilterFournisseur}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Fournisseur" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous fournisseurs</SelectItem>
                {fournisseurs.map(fournisseur => (
                  <SelectItem key={fournisseur} value={fournisseur}>
                    {fournisseur}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Button
              variant="outline"
              onClick={handleResetFilters}
              className="gap-2"
            >
              <Filter className="h-4 w-4" />
              Réinitialiser
            </Button>
          </div>
        </div>

        {/* Statistiques rapides */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="p-4 border rounded-lg bg-blue-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-blue-800">Sous-traitants</p>
                <p className="text-2xl font-bold text-blue-900">{formatMontant(totalSousTraitant)}</p>
              </div>
              <Building className="h-8 w-8 text-blue-600" />
            </div>
          </div>
          
          <div className="p-4 border rounded-lg bg-green-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-800">Fournisseurs</p>
                <p className="text-2xl font-bold text-green-900">{formatMontant(totalFournisseur)}</p>
              </div>
              <Package className="h-8 w-8 text-green-600" />
            </div>
          </div>
          
          <div className="p-4 border rounded-lg bg-gray-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-800">Autres dépenses</p>
                <p className="text-2xl font-bold text-gray-900">{formatMontant(totalAutre)}</p>
              </div>
              <DollarSign className="h-8 w-8 text-gray-600" />
            </div>
          </div>
        </div>

        {filteredDepenses.length === 0 ? (
          <div className="text-center py-12">
            <DollarSign className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium">Aucune dépense trouvée</h3>
            <p className="text-muted-foreground mt-2">
              Aucune dépense ne correspond à vos critères de recherche.
            </p>
            <Button onClick={handleResetFilters} className="mt-4">
              Réinitialiser les filtres
            </Button>
          </div>
        ) : (
          <div className="rounded-md border overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">Date</TableHead>
                    <TableHead>Fournisseur</TableHead>
                    <TableHead className="w-[120px]">Catégorie</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right w-[150px]">Montant (€ HT)</TableHead>
                    <TableHead className="w-[120px]">Facture</TableHead>
                    <TableHead className="w-[110px]">Statut</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDepenses.map((depense) => (
                    <TableRow
                      key={depense.id}
                      className="hover:bg-muted/50 cursor-pointer"
                      onClick={() => {
                        setSelectedDepense(depense);
                        scrollToDetail();
                      }}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          {formatDate(depense.date)}
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">{depense.fournisseur}</TableCell>
                      <TableCell>{getCategorieBadge(depense.categorie)}</TableCell>
                      <TableCell>{depense.description}</TableCell>
                      <TableCell className="text-right font-bold">
                        <div className="flex items-center justify-end gap-2">
                          <DollarSign className="h-4 w-4 text-muted-foreground" />
                          {formatMontant(depense.montant)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-muted-foreground">
                          {depense.factureRef || '—'}
                        </div>
                      </TableCell>
                      <TableCell>
                        {depense.statut === 'en_attente' ? (
                          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200"><Clock className="w-3 h-3 mr-1" /> En attente</Badge>
                        ) : depense.statut === 'validee' ? (
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle className="w-3 h-3 mr-1" /> Validée</Badge>
                        ) : (
                          <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> Rejetée</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {(depense.invoiceId && (depense.invoiceItems ?? []).length > 0) && (
                          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                            <Package className="w-3 h-3 mr-1" />
                            {(depense.invoiceItems ?? []).length} lignes
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {depense.statut === 'en_attente' && (
                            <>
                              <Button variant="ghost" size="sm" className="text-green-600" onClick={async (e) => {
                                e.stopPropagation();
                                await fetch(`/api/v1/chantiers/${chantierId}/depenses/${depense.id}?org_id=${orgId}`, {
                                  method: 'PUT', credentials: 'include',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ statut: 'validee' }),
                                });
                                fetchDepenses();
                              }}>Valider</Button>
                              <Button variant="ghost" size="sm" className="text-red-600" onClick={async (e) => {
                                e.stopPropagation();
                                await fetch(`/api/v1/chantiers/${chantierId}/depenses/${depense.id}?org_id=${orgId}`, {
                                  method: 'PUT', credentials: 'include',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ statut: 'rejetee' }),
                                });
                                fetchDepenses();
                              }}>Rejeter</Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  
                  {/* Ligne de total */}
                  <TableRow className="bg-muted/30">
                    <TableCell colSpan={4} className="text-right font-bold">
                      Total dépenses:
                    </TableCell>
                    <TableCell className="text-right font-bold text-lg">
                      {formatMontant(totalDepenses)}
                    </TableCell>
                    <TableCell colSpan={2}></TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
        )}
        
      </CardContent>

      {/* Carte détail dépense en bas */}
      {selectedDepense && (
        <Card id="detail-card" className="mt-6">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Détail de la dépense
              </CardTitle>
              <div className="flex gap-2">
                {editDepenseMode && <Button size="sm" onClick={async () => {
                  await fetch(`/api/v1/chantiers/${chantierId}/depenses/${selectedDepense.id}?org_id=${orgId}`, {
                    method: 'PUT', credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ...editDepenseForm, montant: parseFloat(editDepenseForm.montant) }),
                  });
                  setEditDepenseMode(false);
                  fetchDepenses();
                }}>Sauvegarder</Button>}
                <Button variant={editDepenseMode ? "outline" : "default"} size="sm" onClick={() => {
                  if (!editDepenseMode) {
                    setEditDepenseForm({
                      fournisseur: selectedDepense.fournisseur,
                      description: selectedDepense.description,
                      montant: String(selectedDepense.montant),
                      categorie: selectedDepense.categorie,
                      date: typeof selectedDepense.date === 'string' ? selectedDepense.date.split('T')[0] : '',
                    });
                  }
                  setEditDepenseMode(!editDepenseMode);
                }}>{editDepenseMode ? 'Annuler' : 'Modifier'}</Button>
                <Button variant="ghost" size="sm" onClick={() => { setSelectedDepense(null); setEditDepenseMode(false); }}>Fermer</Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {editDepenseMode ? (
              <>
                <div className="space-y-2"><Label>Fournisseur</Label><Input value={editDepenseForm.fournisseur} onChange={(e) => setEditDepenseForm({...editDepenseForm, fournisseur: e.target.value})} /></div>
                <div className="space-y-2"><Label>Description</Label><Input value={editDepenseForm.description} onChange={(e) => setEditDepenseForm({...editDepenseForm, description: e.target.value})} /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>Montant HT</Label><Input type="number" step="0.01" value={editDepenseForm.montant} onChange={(e) => setEditDepenseForm({...editDepenseForm, montant: e.target.value})} /></div>
                  <div className="space-y-2"><Label>Date</Label><Input type="date" value={editDepenseForm.date} onChange={(e) => setEditDepenseForm({...editDepenseForm, date: e.target.value})} /></div>
                </div>
                <div className="space-y-2">
                  <Label>Catégorie</Label>
                  <Select value={editDepenseForm.categorie} onValueChange={(v) => setEditDepenseForm({...editDepenseForm, categorie: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sous_traitant">Sous-traitant</SelectItem>
                      <SelectItem value="fournisseur">Fournisseur</SelectItem>
                      <SelectItem value="autre">Autre</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div><Label>Fournisseur</Label><p className="font-medium">{selectedDepense.fournisseur}</p></div>
                  <div><Label>Catégorie</Label><p>{getCategorieBadge(selectedDepense.categorie)}</p></div>
                  <div className="md:col-span-2"><Label>Description</Label><p>{selectedDepense.description}</p></div>
                  <div><Label>Montant HT</Label><p className="text-lg font-bold">{formatMontant(selectedDepense.montant)}</p></div>
                  <div><Label>Date</Label><p>{formatDate(selectedDepense.date)}</p></div>
                  <div><Label>Statut</Label><p>{selectedDepense.statut === 'en_attente' ? 'En attente' : selectedDepense.statut === 'validee' ? 'Validée' : 'Rejetée'}</p></div>
                  {selectedDepense.factureRef && <div><Label>Réf. facture</Label><p>{selectedDepense.factureRef}</p></div>}
                </div>
              )}
              {selectedDepense.invoiceId && selectedDepense.invoiceItems && selectedDepense.invoiceItems.length > 0 && (
                <div className="border-t pt-4 mt-4">
                  <Label className="text-base font-medium mb-3 block">Lignes de facture</Label>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Description</TableHead>
                          <TableHead className="text-right">Qté</TableHead>
                          <TableHead className="text-right">PU</TableHead>
                          <TableHead className="text-right">Total HT</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedDepense.invoiceItems.map((item: any, i: number) => (
                          <TableRow key={i}>
                            <TableCell>{item.description}</TableCell>
                            <TableCell className="text-right">{item.quantity}</TableCell>
                            <TableCell className="text-right">{item.unit_price?.toFixed(2)}€</TableCell>
                            <TableCell className="text-right">{item.total_ht?.toFixed(2)}€</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                </div>
              )}
          </CardContent>
        </Card>
      )}
    </Card>
  );
}