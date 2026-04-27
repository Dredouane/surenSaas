'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Plus,
  Search,
  FileText,
  Calendar,
  DollarSign,
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
            createdAt: s.created_at,
            updatedAt: s.updated_at || s.created_at,
        })));
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredSituations = situations.filter(situation => 
    !search || situation.libelle.toLowerCase().includes(search.toLowerCase())
  );

  const totalSituations = filteredSituations.reduce((total, s) => total + s.montant, 0);

  const formatDate = (dateString: string | Date) => new Date(dateString).toLocaleDateString('fr-FR');
  const formatMontant = (montant: number) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(montant);

  if (loading) return <div>Chargement des situations...</div>;

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
            <CardTitle>Situations facturées</CardTitle>
            <Button onClick={fetchSituations} size="sm">Rafraîchir</Button>
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
                        <TableHead className="text-right">Montant</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {filteredSituations.map((s) => (
                        <TableRow key={s.id}>
                            <TableCell>{formatDate(s.date)}</TableCell>
                            <TableCell><Badge variant="outline">#{s.numero}</Badge></TableCell>
                            <TableCell>{s.libelle}</TableCell>
                            <TableCell className="text-right">{formatMontant(s.montant)}</TableCell>
                        </TableRow>
                    ))}
                    <TableRow className="bg-muted/30">
                        <TableCell colSpan={3} className="text-right font-bold">Total:</TableCell>
                        <TableCell className="text-right font-bold">{formatMontant(totalSituations)}</TableCell>
                    </TableRow>
                </TableBody>
            </Table>
        )}
      </CardContent>
    </Card>
  );
}
