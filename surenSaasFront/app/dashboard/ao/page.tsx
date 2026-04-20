"use client";

/**
 * Page Liste des Appels d'Offres
 * 
 * Affiche la liste des candidatures AO avec:
 * - Filtrage par statut
 * - Recherche
 * - Création de nouvelle candidature
 * - Accès rapide aux analyses
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Plus,
  Search,
  FileText,
  FileSearch,
  Calendar,
  Building2,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  BarChart3,
  MoreHorizontal,
  FolderOpen,
} from "lucide-react";
import { useAuth } from "@/app/contexts/AuthContext";
import { cn } from "@/lib/utils";

// Types
interface AOCandidature {
  id: string;
  nom_projet: string;
  client_nom?: string;
  reference_ao?: string;
  statut: "en_cours" | "gagne" | "perdu" | "abandonne";
  montant_total?: number;
  date_depot?: string;
  date_limite_remise?: string;
  ai_score_gagner?: number;
  document_count: number;
  poste_count: number;
  created_at: string;
}

const statusConfig = {
  en_cours: { label: "En cours", color: "bg-blue-100 text-blue-800", icon: Minus },
  gagne: { label: "Gagné", color: "bg-green-100 text-green-800", icon: TrendingUp },
  perdu: { label: "Perdu", color: "bg-red-100 text-red-800", icon: TrendingDown },
  abandonne: { label: "Abandonné", color: "bg-gray-100 text-gray-800", icon: Minus },
};

export default function AOPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [candidatures, setCandidatures] = useState<AOCandidature[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [stats, setStats] = useState({
    total: 0,
    en_cours: 0,
    gagne: 0,
    perdu: 0,
    taux_reussite: 0,
  });

  // Charger les candidatures
  useEffect(() => {
    fetchCandidatures();
    fetchStats();
  }, []);

  const fetchCandidatures = async () => {
    try {
      setLoading(true);
      // Simuler l'appel API
      // const response = await fetch(`/api/ao/candidatures`);
      // const data = await response.json();
      
      // Données de test
      const mockData: AOCandidature[] = [
        {
          id: "1",
          nom_projet: "Résidence Les Lilas",
          client_nom: "ACORUS",
          reference_ao: "AO-2024-001",
          statut: "en_cours",
          montant_total: 1250000,
          date_limite_remise: "2024-03-15",
          ai_score_gagner: 0.72,
          document_count: 4,
          poste_count: 45,
          created_at: "2024-01-10T10:00:00Z",
        },
        {
          id: "2",
          nom_projet: "Centre Commercial Grand Sud",
          client_nom: "UNIBAIL",
          reference_ao: "AO-2024-015",
          statut: "gagne",
          montant_total: 2800000,
          date_depot: "2024-02-01",
          ai_score_gagner: 0.85,
          document_count: 6,
          poste_count: 120,
          created_at: "2024-01-05T14:30:00Z",
        },
        {
          id: "3",
          nom_projet: "Bureaux Défense",
          client_nom: "ICADE",
          reference_ao: "AO-2023-089",
          statut: "perdu",
          montant_total: 950000,
          date_depot: "2023-12-10",
          ai_score_gagner: 0.35,
          document_count: 5,
          poste_count: 38,
          created_at: "2023-11-20T09:15:00Z",
        },
      ];
      
      setCandidatures(mockData);
    } catch (error) {
      console.error("Erreur chargement candidatures:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    // Simuler les stats
    setStats({
      total: 12,
      en_cours: 5,
      gagne: 4,
      perdu: 3,
      taux_reussite: 57,
    });
  };

  // Filtrer les candidatures
  const filteredCandidatures = candidatures.filter((c) => {
    const matchesSearch =
      c.nom_projet.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.client_nom?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.reference_ao?.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesStatus = statusFilter === "all" || c.statut === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Non définie";
    return new Date(dateString).toLocaleDateString("fr-FR");
  };

  const formatMontant = (montant?: number) => {
    if (!montant) return "Non chiffré";
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(montant);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Appels d&apos;Offres</h1>
          <p className="text-muted-foreground">
            Gérez vos candidatures et analysez vos chances de succès
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/dashboard/ao/import">
            <Button variant="outline" className="gap-2">
              <FolderOpen className="w-4 h-4" />
              Importer dossier
            </Button>
          </Link>
          <Link href="/dashboard/ao/new">
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Nouvelle Candidature
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Candidatures
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              En Cours
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats.en_cours}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Gagnés
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.gagne}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Taux de Réussite
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              stats.taux_reussite >= 50 ? "text-green-600" : "text-orange-600"
            )}>
              {stats.taux_reussite}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filtres */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher par projet, client ou référence..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filtrer par statut" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les statuts</SelectItem>
            <SelectItem value="en_cours">En cours</SelectItem>
            <SelectItem value="gagne">Gagné</SelectItem>
            <SelectItem value="perdu">Perdu</SelectItem>
            <SelectItem value="abandonne">Abandonné</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Liste des candidatures */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredCandidatures.length === 0 ? (
        <Card className="p-12 text-center">
          <FileSearch className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">Aucune candidature trouvée</h3>
          <p className="text-muted-foreground mb-4">
            Commencez par créer votre première candidature
          </p>
          <Link href="/dashboard/ao/new">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Nouvelle Candidature
            </Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredCandidatures.map((candidature) => {
            const status = statusConfig[candidature.statut];
            const StatusIcon = status.icon;

            return (
              <Card
                key={candidature.id}
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => router.push(`/dashboard/ao/${candidature.id}`)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    {/* Info principale */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold truncate">
                          {candidature.nom_projet}
                        </h3>
                        <Badge className={cn("shrink-0", status.color)}>
                          <StatusIcon className="w-3 h-3 mr-1" />
                          {status.label}
                        </Badge>
                      </div>

                      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
                        {candidature.client_nom && (
                          <div className="flex items-center gap-1">
                            <Building2 className="w-4 h-4" />
                            {candidature.client_nom}
                          </div>
                        )}
                        
                        {candidature.reference_ao && (
                          <div className="flex items-center gap-1">
                            <FileText className="w-4 h-4" />
                            {candidature.reference_ao}
                          </div>
                        )}
                        
                        <div className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          {candidature.statut === "en_cours"
                            ? `Limite: ${formatDate(candidature.date_limite_remise)}`
                            : `Dépôt: ${formatDate(candidature.date_depot)}`}
                        </div>
                      </div>
                    </div>

                    {/* Stats et actions */}
                    <div className="flex items-center gap-6">
                      {/* Score IA */}
                      {candidature.ai_score_gagner !== undefined && (
                        <div className="text-center">
                          <div className={cn(
                            "text-lg font-bold",
                            candidature.ai_score_gagner >= 0.7 ? "text-green-600" :
                            candidature.ai_score_gagner >= 0.4 ? "text-yellow-600" :
                            "text-red-600"
                          )}>
                            {Math.round(candidature.ai_score_gagner * 100)}%
                          </div>
                          <div className="text-xs text-muted-foreground">Score IA</div>
                        </div>
                      )}

                      {/* Montant */}
                      <div className="text-right min-w-[120px]">
                        <div className="font-semibold">
                          {formatMontant(candidature.montant_total)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {candidature.document_count} docs • {candidature.poste_count} postes
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/dashboard/ao/${candidature.id}/analyze`);
                          }}
                        >
                          <BarChart3 className="w-4 h-4 mr-2" />
                          Analyser
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
