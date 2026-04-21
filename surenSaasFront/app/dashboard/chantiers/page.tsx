'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Search,
  Filter,
  Plus,
  Download,
  Eye,
  Building,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { Chantier, ChantierStatut } from '@/types/chantier';
import { tousLesChantiers } from '@/lib/chantier-data';

export default function ChantiersPage() {
  const router = useRouter();
  const [chantiers, setChantiers] = useState<Chantier[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    statut: 'all',
    priorite: 'all',
    search: '',
  });

  // Simuler le chargement des données
  useEffect(() => {
    const timer = setTimeout(() => {
      setChantiers(tousLesChantiers);
      setLoading(false);
    }, 500);

    return () => clearTimeout(timer);
  }, []);

  // Filtrer les chantiers
  const filteredChantiers = chantiers.filter(chantier => {
    if (filters.statut !== 'all' && chantier.statut !== filters.statut) return false;
    if (filters.priorite !== 'all' && chantier.priorite.toString() !== filters.priorite) return false;
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        chantier.ref.toLowerCase().includes(searchLower) ||
        chantier.nom.toLowerCase().includes(searchLower) ||
        chantier.adresse.toLowerCase().includes(searchLower) ||
        chantier.conducteur.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  // Statistiques
  const stats = {
    total: chantiers.length,
    enCours: chantiers.filter(c => c.statut === 'en_cours').length,
    termines: chantiers.filter(c => c.statut === 'termine').length,
    enAttente: chantiers.filter(c => c.statut === 'en_attente').length,
  };

  // Fonction pour obtenir la couleur du badge selon le statut
  const getStatutBadge = (statut: ChantierStatut) => {
    switch (statut) {
      case 'en_cours':
        return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">En cours</Badge>;
      case 'termine':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Terminé</Badge>;
      case 'en_attente':
        return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">En attente</Badge>;
      case 'cloture':
        return <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100">Clôturé</Badge>;
      default:
        return <Badge variant="outline">{statut}</Badge>;
    }
  };

  // Fonction pour obtenir l'icône de priorité
  const getPrioriteIcon = (priorite: number) => {
    switch (priorite) {
      case 0:
        return <span className="text-gray-400">●</span>;
      case 1:
        return <span className="text-blue-500">●</span>;
      case 2:
        return <span className="text-amber-500">●</span>;
      case 3:
        return <span className="text-red-500">●</span>;
      default:
        return <span className="text-gray-400">●</span>;
    }
  };

  // Formater un montant
  const formatMontant = (montant: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(montant);
  };

  // Formater un pourcentage
  const formatPourcentage = (pourcentage: number) => {
    return `${pourcentage.toFixed(2)}%`;
  };

  // Handler pour le bouton Export (placeholder)
  const handleExport = () => {
    alert('Fonctionnalité d\'export à implémenter dans la prochaine itération');
  };

  // Handler pour le bouton Nouveau chantier
  const handleNouveauChantier = () => {
    alert('Fonctionnalité de création à implémenter dans la prochaine itération');
  };

  return (
    <div className="p-6 lg:p-8">
      {/* En-tête */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Gestion des chantiers</h1>
          <p className="text-muted-foreground mt-2">
            Suivi financier et opérationnel de tous vos chantiers
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="outline" onClick={handleExport} className="gap-2">
            <Download className="h-4 w-4" />
            Exporter
          </Button>
          <Button onClick={handleNouveauChantier} className="gap-2">
            <Plus className="h-4 w-4" />
            Nouveau chantier
          </Button>
        </div>
      </div>

      {/* Cartes de statistiques */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total chantiers</CardTitle>
            <Building className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">Tous statuts confondus</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">En cours</CardTitle>
            <Clock className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats.enCours}</div>
            <p className="text-xs text-muted-foreground">Chantiers actifs</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Terminés</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.termines}</div>
            <p className="text-xs text-muted-foreground">Livrés et clôturés</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">En attente</CardTitle>
            <AlertCircle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">{stats.enAttente}</div>
            <p className="text-xs text-muted-foreground">En attente de démarrage</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtres */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Rechercher par réf, nom, adresse, conducteur..."
                  className="pl-10"
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                />
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-3">
              <Select
                value={filters.statut}
                onValueChange={(value) => setFilters({ ...filters, statut: value })}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="en_cours">En cours</SelectItem>
                  <SelectItem value="termine">Terminé</SelectItem>
                  <SelectItem value="en_attente">En attente</SelectItem>
                  <SelectItem value="cloture">Clôturé</SelectItem>
                </SelectContent>
              </Select>
              
              <Select
                value={filters.priorite}
                onValueChange={(value) => setFilters({ ...filters, priorite: value })}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Priorité" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes priorités</SelectItem>
                  <SelectItem value="0">Normale (0)</SelectItem>
                  <SelectItem value="1">Basse (1)</SelectItem>
                  <SelectItem value="2">Moyenne (2)</SelectItem>
                  <SelectItem value="3">Haute (3)</SelectItem>
                </SelectContent>
              </Select>
              
              <Button
                variant="outline"
                onClick={() => setFilters({ statut: 'all', priorite: 'all', search: '' })}
                className="gap-2"
              >
                <Filter className="h-4 w-4" />
                Réinitialiser
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tableau des chantiers */}
      <Card>
        <CardHeader>
          <CardTitle>Tableau de suivi des chantiers</CardTitle>
          <p className="text-sm text-muted-foreground">
            {filteredChantiers.length} chantier{filteredChantiers.length > 1 ? 's' : ''} trouvé{filteredChantiers.length > 1 ? 's' : ''}
          </p>
        </CardHeader>
        <CardContent>
          {loading ? (
            // Skeleton loader
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-full" />
                </div>
              ))}
            </div>
          ) : filteredChantiers.length === 0 ? (
            // Aucun résultat
            <div className="text-center py-12">
              <Building className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">Aucun chantier trouvé</h3>
              <p className="text-muted-foreground mt-2">
                Aucun chantier ne correspond à vos critères de recherche.
              </p>
              <Button
                variant="outline"
                onClick={() => setFilters({ statut: '', priorite: '', search: '' })}
                className="mt-4"
              >
                Réinitialiser les filtres
              </Button>
            </div>
          ) : (
            // Tableau
            <div className="rounded-md border overflow-hidden">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[80px]">Réf.</TableHead>
                      <TableHead>Nom du chantier</TableHead>
                      <TableHead>Adresse</TableHead>
                      <TableHead>Conducteur</TableHead>
                      <TableHead className="text-right">Montant marché</TableHead>
                      <TableHead className="text-right">% facturé</TableHead>
                      <TableHead className="text-right">Marge brute</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead className="w-[80px]">Priorité</TableHead>
                      <TableHead className="w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredChantiers.map((chantier) => (
                      <TableRow key={chantier.id} className="hover:bg-muted/50">
                        <TableCell className="font-medium">{chantier.ref}</TableCell>
                        <TableCell>
                          <div className="font-medium">{chantier.nom}</div>
                          {chantier.commentaires && (
                            <div className="text-xs text-muted-foreground truncate max-w-[200px]">
                              {chantier.commentaires}
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">
                          {chantier.adresse}
                        </TableCell>
                        <TableCell>{chantier.conducteur}</TableCell>
                        <TableCell className="text-right font-medium">
                          {formatMontant(chantier.montantRevise)}
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={chantier.pourcentageFacture >= 80 ? 'text-green-600 font-medium' : ''}>
                            {formatPourcentage(chantier.pourcentageFacture)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={chantier.margeBrute > 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                            {formatMontant(chantier.margeBrute)}
                          </span>
                        </TableCell>
                        <TableCell>{getStatutBadge(chantier.statut)}</TableCell>
                        <TableCell>
                          <div className="flex items-center justify-center">
                            {getPrioriteIcon(chantier.priorite)}
                            <span className="ml-2 text-sm">{chantier.priorite}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            asChild
                            className="w-full"
                          >
                            <Link href={`/dashboard/chantiers/${chantier.id}`}>
                              <Eye className="h-4 w-4 mr-2" />
                              Voir
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Légende */}
      <div className="mt-6 text-sm text-muted-foreground">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-blue-500">●</span>
            <span>Priorité basse (1)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-amber-500">●</span>
            <span>Priorité moyenne (2)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-red-500">●</span>
            <span>Priorité haute (3)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">●</span>
            <span>Priorité normale (0)</span>
          </div>
        </div>
        <p className="mt-2">
          <strong>Note:</strong> Ce tableau reproduit la structure du fichier Excel de suivi financier.
          Les données sont statiques pour le prototype et seront connectées au backend dans la prochaine itération.
        </p>
      </div>
    </div>
  );
}