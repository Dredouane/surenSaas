"use client";

/**
 * Page Détail d'une Candidature AO
 * 
 * Affiche le détail complet avec:
 * - Informations générales
 * - Liste des documents
 * - Postes pricing
 * - Interface d'analyse (LensSidebar)
 * - Drafting Sandbox
 */

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/app/contexts/AuthContext";
import { AOExplorer } from "@/components/ao/AOExplorer";
import { LensSidebar, AVAILABLE_LENSES } from "@/components/ao/LensSidebar";
import { DocumentUploader } from "@/components/ao/DocumentUploader";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  Building2,
  Calendar,
  FileText,
  Euro,
  Clock,
  Loader2,
  BarChart3,
  FileSearch,
} from "lucide-react";

// Types
interface AOCandidature {
  id: string;
  nom_projet: string;
  client_nom?: string;
  reference_ao?: string;
  description?: string;
  statut: "en_cours" | "gagne" | "perdu" | "abandonne";
  montant_total?: number;
  montant_maximum?: number;
  date_depot?: string;
  date_ouverture?: string;
  date_notification?: string;
  date_limite_remise?: string;
  duree_travaux_jours?: number;
  ai_summary?: string;
  ai_score_gagner?: number;
  document_count: number;
  poste_count: number;
  dossier_id?: string;
  dossier_name?: string;
  created_at: string;
}

interface AODocument {
  id: string;
  type_doc: string;
  nom_fichier: string;
  statut_traitement: "pending" | "processing" | "processed" | "error";
  taille_bytes?: number;
  metadata?: Record<string, any>;
  created_at: string;
}

const statusConfig = {
  en_cours: { label: "En cours", color: "bg-blue-100 text-blue-800" },
  gagne: { label: "Gagné", color: "bg-green-100 text-green-800" },
  perdu: { label: "Perdu", color: "bg-red-100 text-red-800" },
  abandonne: { label: "Abandonné", color: "bg-gray-100 text-gray-800" },
};

export default function AODetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const candidatureId = params.id as string;

  const [candidature, setCandidature] = useState<AOCandidature | null>(null);
  const [documents, setDocuments] = useState<AODocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [showExplorer, setShowExplorer] = useState(false);

  // Charger la candidature
  useEffect(() => {
    fetchCandidature();
    fetchDocuments();
  }, [candidatureId]);

  const fetchCandidature = async () => {
    try {
      setLoading(true);
      // Simuler l'appel API
      // const response = await fetch(`/api/ao/candidatures/${candidatureId}`);
      // const data = await response.json();
      
      // Données de test
      const mockData: AOCandidature = {
        id: candidatureId,
        nom_projet: "Résidence Les Lilas",
        client_nom: "ACORUS",
        reference_ao: "AO-2024-001",
        description: "Construction d'une résidence de 50 logements avec sous-sol",
        statut: "en_cours",
        montant_total: 1250000,
        montant_maximum: 1500000,
        date_limite_remise: "2024-03-15",
        date_ouverture: "2024-03-20",
        duree_travaux_jours: 180,
        ai_summary: "Projet de construction résidentielle dans le 19ème arrondissement. Client connu et fiable. Délai serré mais faisable.",
        ai_score_gagner: 0.72,
        document_count: 4,
        poste_count: 45,
        dossier_name: "Résidence Les Lilas",
        created_at: "2024-01-10T10:00:00Z",
      };
      
      setCandidature(mockData);
    } catch (error) {
      console.error("Erreur chargement candidature:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDocuments = async () => {
    // Simuler les documents
    const mockDocs: AODocument[] = [
      {
        id: "doc1",
        type_doc: "RC",
        nom_fichier: "RC_Residence_Lilas.pdf",
        statut_traitement: "processed",
        taille_bytes: 1250000,
        metadata: { client_nom: "ACORUS", pages: 12 },
        created_at: "2024-01-10T10:00:00Z",
      },
      {
        id: "doc2",
        type_doc: "CCTP",
        nom_fichier: "CCTP_Residence_Lilas.pdf",
        statut_traitement: "processed",
        taille_bytes: 2800000,
        metadata: { pages: 45 },
        created_at: "2024-01-10T10:05:00Z",
      },
      {
        id: "doc3",
        type_doc: "BPU",
        nom_fichier: "BPU_Residence_Lilas.csv",
        statut_traitement: "processed",
        taille_bytes: 45000,
        metadata: { postes_count: 45, montant_total: 1250000 },
        created_at: "2024-01-10T10:10:00Z",
      },
      {
        id: "doc4",
        type_doc: "DAO",
        nom_fichier: "DAO_Complet.zip",
        statut_traitement: "processed",
        taille_bytes: 15000000,
        created_at: "2024-01-10T10:15:00Z",
      },
    ];
    
    setDocuments(mockDocs);
  };

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

  const handleRunLens = async (lens: any) => {
    console.log("Running lens:", lens.id);
    // TODO: Appeler l'API pour lancer l'analyse
  };

  // État initial des résultats des lentilles
  const lensResults = {
    pricing: { lensId: "pricing" as const, status: "pending" as const },
    redaction: { lensId: "redaction" as const, status: "pending" as const },
    risque: { lensId: "risque" as const, status: "pending" as const },
    comparaison: { lensId: "comparaison" as const, status: "pending" as const },
    opportunite: { lensId: "opportunite" as const, status: "pending" as const },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!candidature) {
    return (
      <div className="p-6">
        <Card className="p-12 text-center">
          <FileSearch className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">Candidature non trouvée</h3>
          <Link href="/dashboard/ao">
            <Button variant="outline">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Retour à la liste
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const status = statusConfig[candidature.statut];

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Contenu principal */}
      <div className="flex-1 overflow-auto">
        <div className="p-6 space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <Link href="/dashboard/ao">
                <Button variant="outline" size="icon">
                  <ArrowLeft className="w-4 h-4" />
                </Button>
              </Link>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold">{candidature.nom_projet}</h1>
                  <Badge className={status.color}>{status.label}</Badge>
                </div>
                {candidature.reference_ao && (
                  <p className="text-muted-foreground">{candidature.reference_ao}</p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => setShowExplorer(!showExplorer)}
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                {showExplorer ? "Masquer l'analyse" : "Analyser"}
              </Button>
              <Button variant="outline">Modifier</Button>
            </div>
          </div>

          {/* Info cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  <Building2 className="w-4 h-4 inline mr-2" />
                  Client
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-medium">{candidature.client_nom || "Non défini"}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  <Euro className="w-4 h-4 inline mr-2" />
                  Montant
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-medium">{formatMontant(candidature.montant_total)}</div>
                {candidature.montant_maximum && (
                  <div className="text-xs text-muted-foreground">
                    Max: {formatMontant(candidature.montant_maximum)}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  <Calendar className="w-4 h-4 inline mr-2" />
                  Date limite
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-medium">
                  {formatDate(candidature.date_limite_remise)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  <Clock className="w-4 h-4 inline mr-2" />
                  Score IA
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={cn(
                  "font-bold text-lg",
                  (candidature.ai_score_gagner || 0) >= 0.7 ? "text-green-600" :
                  (candidature.ai_score_gagner || 0) >= 0.4 ? "text-yellow-600" :
                  "text-red-600"
                )}>
                  {candidature.ai_score_gagner
                    ? `${Math.round(candidature.ai_score_gagner * 100)}%`
                    : "N/A"}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="overview">Vue d'ensemble</TabsTrigger>
              <TabsTrigger value="documents">
                Documents ({documents.length})
              </TabsTrigger>
              <TabsTrigger value="pricing">Pricing</TabsTrigger>
              <TabsTrigger value="analyses">Analyses</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              {candidature.ai_summary && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Résumé IA</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">{candidature.ai_summary}</p>
                  </CardContent>
                </Card>
              )}

              {candidature.description && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Description</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">{candidature.description}</p>
                  </CardContent>
                </Card>
              )}

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Planning</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Ouverture des plis</span>
                      <span>{formatDate(candidature.date_ouverture)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Notification</span>
                      <span>{formatDate(candidature.date_notification)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Durée des travaux</span>
                      <span>{candidature.duree_travaux_jours || "Non définie"} jours</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Documents</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {documents.map((doc) => (
                      <div key={doc.id} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm">{doc.nom_fichier}</span>
                        </div>
                        <Badge variant="outline">{doc.type_doc}</Badge>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="documents" className="space-y-4">
              <DocumentUploader
                candidatureId={candidatureId}
                onUploadComplete={() => {
                  // Rafraîchir la liste des documents
                  fetchDocuments();
                }}
              />

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Documents ({documents.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="divide-y">
                    {documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between py-4"
                      >
                        <div className="flex items-center gap-3">
                          <FileText className="w-8 h-8 text-blue-600" />
                          <div>
                            <p className="font-medium">{doc.nom_fichier}</p>
                            <p className="text-sm text-muted-foreground">
                              {doc.type_doc} • {((doc.taille_bytes || 0) / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <Badge
                          className={cn(
                            doc.statut_traitement === "processed" && "bg-green-100 text-green-800",
                            doc.statut_traitement === "error" && "bg-red-100 text-red-800",
                            doc.statut_traitement === "processing" && "bg-yellow-100 text-yellow-800"
                          )}
                        >
                          {doc.statut_traitement}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="pricing">
              <Card>
                <CardHeader>
                  <CardTitle>Postes Pricing ({candidature.poste_count})</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Les postes pricing seront affichés  après extraction du BPU.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="analyses">
              <Card>
                <CardHeader>
                  <CardTitle>Analyses IA</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground mb-4">
                    Lancez une analyse pour obtenir des insights sur cette candidature.
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    {AVAILABLE_LENSES.slice(0, 4).map((lens) => (
                      <Card
                        key={lens.id}
                        className="cursor-pointer hover:border-primary transition-colors"
                        onClick={() => setShowExplorer(true)}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3">
                            <div className={cn("p-2 rounded-lg", lens.bgColor, lens.color)}>
                              {lens.icon}
                            </div>
                            <div>
                              <h4 className="font-medium">{lens.label}</h4>
                              <p className="text-sm text-muted-foreground">
                                {lens.description}
                              </p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Sidebar d'analyse (optionnelle) */}
      {showExplorer && (
        <div className="w-96 border-l bg-white">
          <LensSidebar
            candidatureId={candidatureId}
            onRunLens={handleRunLens}
            results={lensResults}
          />
        </div>
      )}
    </div>
  );
}
