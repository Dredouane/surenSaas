'use client';

import { useState } from 'react';
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
  FileText,
  Calendar,
  DollarSign,
} from 'lucide-react';
import { Situation } from '@/types/chantier';

interface SituationsTableProps {
  chantierId: string;
  situations: Situation[];
}

export default function SituationsTable({ chantierId, situations }: SituationsTableProps) {
  const [search, setSearch] = useState('');
  const [filterStatut, setFilterStatut] = useState('');

  // Filtrer les situations
  const filteredSituations = situations.filter(situation => {
    if (search && !situation.libelle.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    // Ici on pourrait filtrer par statut si on avait un champ statut
    return true;
  });

  // Calculer le total
  const totalSituations = filteredSituations.reduce((total, situation) => total + situation.montant, 0);

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

  // Handler pour ajouter une situation
  const handleAddSituation = () => {
    alert('Fonctionnalité d\'ajout à implémenter dans la prochaine itération');
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <CardTitle>Situations facturées</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              {filteredSituations.length} situation{filteredSituations.length > 1 ? 's' : ''} • Total: {formatMontant(totalSituations)}
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher une situation..."
                className="pl-10 w-full sm:w-[200px]"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            
            <Button onClick={handleAddSituation} className="gap-2">
              <Plus className="h-4 w-4" />
              Ajouter une situation
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filteredSituations.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium">Aucune situation facturée</h3>
            <p className="text-muted-foreground mt-2">
              Ajoutez des situations pour suivre les facturations de ce chantier.
            </p>
            <Button onClick={handleAddSituation} className="mt-4">
              <Plus className="h-4 w-4 mr-2" />
              Ajouter la première situation
            </Button>
          </div>
        ) : (
          <div className="rounded-md border overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">Date</TableHead>
                    <TableHead className="w-[100px]">N°</TableHead>
                    <TableHead>Libellé</TableHead>
                    <TableHead className="text-right w-[150px]">Montant (€ HT)</TableHead>
                    <TableHead>Règlement / Observation</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSituations.map((situation) => (
                    <TableRow key={situation.id} className="hover:bg-muted/50">
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          {formatDate(situation.date)}
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">
                        <Badge variant="outline">#{situation.numero}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{situation.libelle}</TableCell>
                      <TableCell className="text-right font-bold">
                        <div className="flex items-center justify-end gap-2">
                          <DollarSign className="h-4 w-4 text-muted-foreground" />
                          {formatMontant(situation.montant)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-muted-foreground">
                          {situation.reglementObservation || '—'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" className="w-full">
                          Voir détails
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  
                  {/* Ligne de total */}
                  <TableRow className="bg-muted/30">
                    <TableCell colSpan={3} className="text-right font-bold">
                      Total cumulé:
                    </TableCell>
                    <TableCell className="text-right font-bold text-lg">
                      {formatMontant(totalSituations)}
                    </TableCell>
                    <TableCell colSpan={2}></TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
        )}
        
        {/* Note */}
        <div className="mt-6 text-sm text-muted-foreground">
          <p>
            <strong>Note:</strong> Ce tableau reproduit exactement la structure de l'Excel "Situations facturées".
            Les 11 lignes correspondent aux situations du chantier CRF.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}