'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Plus, Search, FileText, Calendar, DollarSign,
} from 'lucide-react';
import { Situation } from '@/types/chantier';

interface SituationsTableProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
}

export default function SituationsTable({ chantierId, orgId, onRefresh }: SituationsTableProps) {
  const [situations, setSituations] = useState<Situation[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [newNumero, setNewNumero] = useState(1);
  const [newLibelle, setNewLibelle] = useState('');
  const [newMontant, setNewMontant] = useState(0);
  const [newStatut, setNewStatut] = useState('ouverte');

  useEffect(() => {
    fetchSituations();
  }, [chantierId]);

  const fetchSituations = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/chantiers/${chantierId}/situations?org_id=${orgId}`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setSituations(data.map((s: any) => ({
            id: s.id,
            chantierId: s.chantier_id,
            date: s.date || s.created_at,
            numero: s.numero,
            libelle: s.libelle || `Situation n°${s.numero}`,
            montant: s.montant,
            reglementObservation: s.reglement_observation,
            statut: s.statut,
            createdAt: s.created_at,
            updatedAt: s.updated_at || s.created_at,
        })));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const body = {
        date: new Date().toISOString().split('T')[0],
        numero: newNumero,
        libelle: newLibelle,
        montant: newMontant,
        statut: newStatut,
      };
      const res = await fetch(`/api/v1/chantiers/${chantierId}/situations?org_id=${orgId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setShowDialog(false);
        setNewNumero(situations.length + 1);
        setNewLibelle('');
        setNewMontant(0);
        setNewStatut('ouverte');
        fetchSituations();
        if (onRefresh) onRefresh();
      }
    } catch (e) {
      console.error("Erreur création situation:", e);
    }
  };

  const filteredSituations = situations.filter(situation =>
    !search || situation.libelle.toLowerCase().includes(search.toLowerCase())
  );

  const totalSituations = filteredSituations.reduce((total, s) => total + s.montant, 0);

  const formatDate = (dateString: string | Date) => new Date(dateString).toLocaleDateString('fr-FR');
  const formatMontant = (montant: number) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(montant);

  const statutBadge = (statut?: string) => {
    switch (statut) {
      case 'ouverte': return <Badge className="bg-blue-100 text-blue-800">Ouverte</Badge>;
      case 'validee': return <Badge className="bg-green-100 text-green-800">Validée</Badge>;
      case 'transmise': return <Badge className="bg-amber-100 text-amber-800">Transmise</Badge>;
      case 'payee': return <Badge className="bg-gray-100 text-gray-800">Payée</Badge>;
      default: return null;
    }
  };

  if (loading) return <div>Chargement des situations...</div>;

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center flex-wrap gap-2">
            <CardTitle>Situations</CardTitle>
            <div className="flex gap-2">
              <Dialog open={showDialog} onOpenChange={setShowDialog}>
                <DialogTrigger asChild>
                  <Button size="sm"><Plus className="h-4 w-4 mr-1" /> Nouvelle situation</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Nouvelle situation</DialogTitle>
                    <DialogDescription>Crée une situation ouverte pour le chantier.</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div>
                      <Label>Numéro</Label>
                      <Input type="number" value={newNumero} onChange={e => setNewNumero(parseInt(e.target.value) || 1)} />
                    </div>
                    <div>
                      <Label>Libellé</Label>
                      <Input value={newLibelle} onChange={e => setNewLibelle(e.target.value)} placeholder="Ex: Situation n°1" />
                    </div>
                    <div>
                      <Label>Montant (€)</Label>
                      <Input type="number" step="0.01" value={newMontant} onChange={e => setNewMontant(parseFloat(e.target.value) || 0)} />
                    </div>
                    <div>
                      <Label>Statut</Label>
                      <Select value={newStatut} onValueChange={setNewStatut}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ouverte">Ouverte</SelectItem>
                          <SelectItem value="validee">Validée</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowDialog(false)}>Annuler</Button>
                    <Button onClick={handleCreate}>Créer</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              <Button onClick={fetchSituations} size="sm">Rafraîchir</Button>
            </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Rechercher..." className="pl-10" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        {filteredSituations.length === 0 ? <p>Aucune situation</p> : (
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>N°</TableHead>
                        <TableHead>Libellé</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead className="text-right">Montant</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {filteredSituations.map((s) => (
                        <TableRow key={s.id}>
                            <TableCell>{formatDate(s.date)}</TableCell>
                            <TableCell><Badge variant="outline">#{s.numero}</Badge></TableCell>
                            <TableCell>{s.libelle}</TableCell>
                            <TableCell>{statutBadge(s.statut)}</TableCell>
                            <TableCell className="text-right">{formatMontant(s.montant)}</TableCell>
                        </TableRow>
                    ))}
                    <TableRow className="bg-muted/30">
                        <TableCell colSpan={4} className="text-right font-bold">Total:</TableCell>
                        <TableCell className="text-right font-bold">{formatMontant(totalSituations)}</TableCell>
                    </TableRow>
                </TableBody>
            </Table>
        )}
      </CardContent>
    </Card>
  );
}
