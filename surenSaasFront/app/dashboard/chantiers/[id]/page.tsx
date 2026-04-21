'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  ArrowLeft,
  Building,
  User,
  MapPin,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  DollarSign,
  BarChart3,
  ListChecks,
  History,
  Download,
  Edit,
} from 'lucide-react';
import { ChantierWithDetails } from '@/types/chantier';
import { chantierCRFComplet } from '@/lib/chantier-data';
import SituationsTable from './components/SituationsTable';
import DepensesTable from './components/DepensesTable';
import OperationsList from './components/OperationsList';
import Indicateurs from './components/Indicateurs';

export default function ChantierDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [chantier, setChantier] = useState<ChantierWithDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('infos');

  const chantierId = params.id as string;

  // Simuler le chargement des données
  useEffect(() => {
    const timer = setTimeout(() => {
      // Pour le prototype, on utilise les données statiques du CRF
      // Dans la prochaine itération, on fera un appel API
      if (chantierId === 'chantier-crf-001') {
        setChantier(chantierCRFComplet);
      } else {
        // Pour les autres chantiers, créer une structure basique
        setChantier({
          id: chantierId,
          ref: 'CH-XXX',
          nom: 'Chantier exemple',
          adresse: 'Adresse non définie',
          conducteur: 'Conducteur non défini',
          montantBase: 0,
          tsAvenants: 0,
          montantRevise: 0,
          situationsFacturees: 0,
          pourcentageFacture: 0,
          totalDepenses: 0,
          margeBrute: 0,
          soldeAFacturer: 0,
          statut: 'en_attente',
          priorite: 0,
          commentaires: 'Chantier de démonstration',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          situations: [],
          depenses: [],
          operations: [],
          auditTrail: [],
        });
      }
      setLoading(false);
    }, 500);

    return () => clearTimeout(timer);
  }, [chantierId]);

  // Formater un montant
  const formatMontant = (montant: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(montant);
  };

  // Formater une date
  const formatDate = (dateString?: string | Date) => {
    if (!dateString) return 'Non définie';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR');
  };

  // Obtenir la couleur du badge selon le statut
  const getStatutBadge = (statut: string) => {
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

  // Obtenir l'icône de priorité
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

  // Handler pour le bouton Export
  const handleExport = () => {
    alert('Fonctionnalité d\'export à implémenter dans la prochaine itération');
  };

  // Handler pour le bouton Modifier
  const handleEdit = () => {
    alert('Fonctionnalité d\'édition à implémenter dans la prochaine itération');
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8">
        <div className="flex items-center gap-4 mb-6">
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-8 w-48" />
        </div>
        <div className="grid gap-6">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  if (!chantier) {
    return (
      <div className="p-6 lg:p-8">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium">Chantier non trouvé</h3>
          <p className="text-muted-foreground mt-2">
            Le chantier que vous recherchez n'existe pas ou a été supprimé.
          </p>
          <Button asChild className="mt-4">
            <Link href="/dashboard/chantiers">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Retour à la liste
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      {/* En-tête */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/chantiers">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">{chantier.ref} - {chantier.nom}</h1>
              {getStatutBadge(chantier.statut)}
              <div className="flex items-center">
                {getPrioriteIcon(chantier.priorite)}
                <span className="ml-2 text-sm">Priorité {chantier.priorite}</span>
              </div>
            </div>
            <p className="text-muted-foreground mt-2">
              Fiche chantier détaillée - Suivi financier et opérationnel
            </p>
          </div>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="outline" onClick={handleExport} className="gap-2">
            <Download className="h-4 w-4" />
            Exporter
          </Button>
          <Button variant="outline" onClick={handleEdit} className="gap-2">
            <Edit className="h-4 w-4" />
            Modifier
          </Button>
        </div>
      </div>

      {/* Indicateurs rapides */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Montant marché</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatMontant(chantier.montantRevise)}</div>
            <p className="text-xs text-muted-foreground">
              Base: {formatMontant(chantier.montantBase)} + TS: {formatMontant(chantier.tsAvenants)}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">% facturé</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{chantier.pourcentageFacture.toFixed(2)}%</div>
            <p className="text-xs text-muted-foreground">
              {formatMontant(chantier.situationsFacturees)} facturés
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Marge brute</CardTitle>
            <DollarSign className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatMontant(chantier.margeBrute)}
            </div>
            <p className="text-xs text-muted-foreground">
              {((chantier.margeBrute / chantier.montantRevise) * 100).toFixed(1)}% de marge
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Solde à facturer</CardTitle>
            <FileText className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {formatMontant(chantier.soldeAFacturer)}
            </div>
            <p className="text-xs text-muted-foreground">
              Reste à facturer sur le marché
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Onglets */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-2 lg:grid-cols-6">
          <TabsTrigger value="infos" className="gap-2">
            <Building className="h-4 w-4" />
            <span className="hidden sm:inline">Infos générales</span>
          </TabsTrigger>
          <TabsTrigger value="situations" className="gap-2">
            <FileText className="h-4 w-4" />
            <span className="hidden sm:inline">Situations</span>
          </TabsTrigger>
          <TabsTrigger value="depenses" className="gap-2">
            <DollarSign className="h-4 w-4" />
            <span className="hidden sm:inline">Dépenses</span>
          </TabsTrigger>
          <TabsTrigger value="operations" className="gap-2">
            <ListChecks className="h-4 w-4" />
            <span className="hidden sm:inline">Opérations</span>
          </TabsTrigger>
          <TabsTrigger value="indicateurs" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">Indicateurs</span>
          </TabsTrigger>
          <TabsTrigger value="audit" className="gap-2">
            <History className="h-4 w-4" />
            <span className="hidden sm:inline">Audit</span>
          </TabsTrigger>
        </TabsList>

        {/* Onglet: Infos générales */}
        <TabsContent value="infos" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Informations générales du chantier</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Référence</h3>
                    <p className="text-lg font-medium">{chantier.ref}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Nom du chantier</h3>
                    <p className="text-lg font-medium">{chantier.nom}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Adresse</h3>
                    <div className="flex items-start gap-2">
                      <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                      <p className="text-lg">{chantier.adresse}</p>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Conducteur de travaux</h3>
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <p className="text-lg font-medium">{chantier.conducteur}</p>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Dates OPR</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">Prévue</span>
                        </div>
                        <p className="font-medium">{formatDate(chantier.dateOPRPrevue)}</p>
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">Réalisée</span>
                        </div>
                        <p className="font-medium">{formatDate(chantier.dateOPRRealisee)}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Statut et priorité</h3>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        {getStatutBadge(chantier.statut)}
                      </div>
                      <div className="flex items-center gap-2">
                        {getPrioriteIcon(chantier.priorite)}
                        <span>Priorité {chantier.priorite}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              {chantier.commentaires && (
                <>
                  <Separator />
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Commentaires</h3>
                    <p className="text-muted-foreground whitespace-pre-line">{chantier.commentaires}</p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Données marché */}
          <Card>
            <CardHeader>
              <CardTitle>Données marché</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">Montant base marché</h3>
                  <p className="text-2xl font-bold">{formatMontant(chantier.montantBase)}</p>
                </div>
                
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">TS / avenants</h3>
                  <p className="text-2xl font-bold">{formatMontant(chantier.tsAvenants)}</p>
                </div>
                
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">Montant marché révisé</h3>
                  <p className="text-2xl font-bold text-blue-600">{formatMontant(chantier.montantRevise)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Onglet: Situations */}
        <TabsContent value="situations">
          <SituationsTable chantierId={chantierId} situations={chantier.situations} />
        </TabsContent>

        {/* Onglet: Dépenses */}
        <TabsContent value="depenses">
          <DepensesTable chantierId={chantierId} depenses={chantier.depenses} />
        </TabsContent>

        {/* Onglet: Opérations */}
        <TabsContent value="operations">
          <OperationsList chantierId={chantierId} operations={chantier.operations} />
        </TabsContent>

        {/* Onglet: Indicateurs */}
        <TabsContent value="indicateurs">
          <Indicateurs chantier={chantier} />
        </TabsContent>

        {/* Onglet: Audit */}
        <TabsContent value="audit">
          <Card>
            <CardHeader>
              <CardTitle>Audit trail</CardTitle>
              <p className="text-sm text-muted-foreground">
                Historique complet des actions sur ce chantier
              </p>
            </CardHeader>
            <CardContent>
              {chantier.auditTrail.length === 0 ? (
                <div className="text-center py-12">
                  <History className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium">Aucun historique d'audit</h3>
                  <p className="text-muted-foreground mt-2">
                    L'historique des actions sera enregistré ici.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {chantier.auditTrail.map((audit) => (
                    <div key={audit.id} className="flex items-start gap-4 p-4 border rounded-lg">
                      <div className="flex-shrink-0">
                        <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                          <History className="h-4 w-4" />
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <h4 className="font-medium">{audit.userName}</h4>
                          <span className="text-sm text-muted-foreground">
                            {new Date(audit.timestamp).toLocaleDateString('fr-FR')} à{' '}
                            {new Date(audit.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{audit.details}</p>
                        <div className="mt-2">
                          <Badge variant="outline" className="text-xs">
                            {audit.action}
                          </Badge>
                          <Badge variant="outline" className="text-xs ml-2">
                            {audit.entityType}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Note de bas de page */}
      <div className="mt-8 text-sm text-muted-foreground border-t pt-4">
        <p>
          <strong>Note prototype:</strong> Cette interface reproduit fidèlement les 6 sections du fichier Excel.
          Les données sont servies statiquement depuis le backend Next.js. La structure CRUD est prête pour
          être connectée au backend FastAPI dans la prochaine itération.
        </p>
        <p className="mt-2">
          La section "Opérations/Tâches à faire" démontre le mécanisme HITL (Human-in-the-Loop) qui sera
          alimenté par le bot Telegram pour la remontée d'informations terrain.
        </p>
      </div>
    </div>
  );
}