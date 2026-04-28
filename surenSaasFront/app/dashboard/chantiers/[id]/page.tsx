'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/app/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
  Users,
  Bell,
  ClipboardCheck,
  Target,
} from 'lucide-react';
import SituationsTable from './components/SituationsTable';
import DepensesTable from './components/DepensesTable';
import OperationsList from './components/OperationsList';
import Indicateurs from './components/Indicateurs';
import ReceptionsList from './components/ReceptionsList';
import TachesList from './components/TachesList';
import PointagesList from './components/PointagesList';
import NotificationsPanel from './components/NotificationsPanel';
import ValidationProduction from './components/ValidationProduction';
import type { ChantierWithDetails, Situation, Depense, Operation, Reception, Tache, Pointage, Notification } from '@/types/chantier';

const DEFAULT_ORG_ID = process.env.NEXT_PUBLIC_ORG_ID;

export default function ChantierDetailPage() {
  const { user } = useAuth();
  const params = useParams();
  const [chantier, setChantier] = useState<ChantierWithDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('receptions');

  const chantierId = params.id as string;
  const orgId = user?.org_id || DEFAULT_ORG_ID || '';

  useEffect(() => {
    if (orgId) {
      fetchChantierBase(orgId);
    }
  }, [chantierId, orgId]);

  const fetchChantierBase = async (orgId: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/chantiers/${chantierId}?org_id=${orgId}`, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Erreur de chargement');
      const c = await response.json();
      setChantier({
        id: c.id,
        ref: c.ref || 'CH-000',
        nom: c.nom || 'Chantier sans nom',
        adresse: c.adresse || '',
        conducteur: c.conducteur || '',
        montantBase: Number(c.montant_base) || 0,
        tsAvenants: Number(c.ts_avenants) || 0,
        montantRevise: Number(c.montant_revise) || 0,
        situationsFacturees: Number(c.situations_facturees) || 0,
        pourcentageFacture: Number(c.pourcentage_facture) || 0,
        totalDepenses: Number(c.total_depenses) || 0,
        margeBrute: Number(c.marge_brute) || 0,
        soldeAFacturer: Number(c.solde_a_facturer) || 0,
        statut: c.statut,
        priorite: c.priorite || 0,
        dateOPRPrevue: c.date_opr_prevue,
        dateOPRRealisee: c.date_opr_realisee,
        commentaires: c.commentaires || '',
        createdAt: c.created_at,
        updatedAt: c.updated_at,
        situations: [], // Chargé à la demande
        depenses: [],
        operations: [],
        receptions: [],
        taches: [],
        pointages: [],
        notifications: [],
        auditTrail: [],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur');
    } finally {
      setLoading(false);
    }
  };


  const handleRefresh = () => {
    const o = user?.org_id || DEFAULT_ORG_ID;
    if (o) fetchChantierBase(o);
  };

  const formatMontant = (montant: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(montant);
  };

  const formatDate = (dateString?: string | Date) => {
    if (!dateString) return 'Non définie';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR');
  };

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

  const handleExport = () => {
    alert('Fonctionnalité d\'export à implémenter dans la prochaine itération');
  };

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

  if (error) {
    return (
      <div className="p-6 lg:p-8">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium">Erreur de chargement</h3>
          <p className="text-muted-foreground mt-2">{error}</p>
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

      {/* Onglets modernes - design compact */}
      <div className="mb-8">
        <div className="flex flex-wrap gap-1 border-b pb-1">
          <button
            onClick={() => setActiveTab('receptions')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'receptions' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <ClipboardCheck className="h-4 w-4" />
            <span>Réceptions</span>
          </button>
          <button
            onClick={() => setActiveTab('taches')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'taches' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <Target className="h-4 w-4" />
            <span>Tâches</span>
          </button>
          <button
            onClick={() => setActiveTab('pointages')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'pointages' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <Users className="h-4 w-4" />
            <span>Pointages</span>
          </button>
          <button
            onClick={() => setActiveTab('notifications')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'notifications' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <Bell className="h-4 w-4" />
            <span>Notifications</span>
          </button>
          <button
            onClick={() => setActiveTab('production')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'production' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <Target className="h-4 w-4" />
            <span>Production</span>
          </button>
          <button
            onClick={() => setActiveTab('situations')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'situations' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <FileText className="h-4 w-4" />
            <span>Situations</span>
          </button>
          <button
            onClick={() => setActiveTab('depenses')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'depenses' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <DollarSign className="h-4 w-4" />
            <span>Dépenses</span>
          </button>
          <button
            onClick={() => setActiveTab('operations')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'operations' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <ListChecks className="h-4 w-4" />
            <span>Opérations</span>
          </button>
          <button
            onClick={() => setActiveTab('indicateurs')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'indicateurs' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <BarChart3 className="h-4 w-4" />
            <span>Indicateurs</span>
          </button>
          <button
            onClick={() => setActiveTab('infos')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'infos' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <Building className="h-4 w-4" />
            <span>Infos</span>
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === 'audit' ? 'bg-white border border-b-0 border-gray-200 text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
          >
            <History className="h-4 w-4" />
            <span>Audit</span>
          </button>
        </div>
      </div>

      {/* Contenu des onglets */}
      <div className="mt-6">
        {activeTab === 'receptions' && (
          <ReceptionsList chantierId={chantierId} orgId={orgId} onRefresh={handleRefresh} />
        )}
        
        {activeTab === 'taches' && (
          <TachesList chantierId={chantierId} orgId={orgId} onRefresh={handleRefresh} />
        )}
        
        {activeTab === 'pointages' && (
          <PointagesList chantierId={chantierId} orgId={orgId} onRefresh={handleRefresh} />
        )}
        
        {activeTab === 'notifications' && (
          <NotificationsPanel chantierId={chantierId} orgId={orgId} onRefresh={handleRefresh} />
        )}
        
        {activeTab === 'production' && (
          <ValidationProduction chantierId={chantierId} orgId={orgId} onRefresh={handleRefresh} />
        )}
        
        {activeTab === 'situations' && (
          <SituationsTable chantierId={chantierId} orgId={orgId} onRefresh={handleRefresh} />
        )}
        
        {activeTab === 'depenses' && (
          <DepensesTable chantierId={chantierId} orgId={orgId} onRefresh={handleRefresh} />
        )}
        
        {activeTab === 'operations' && (
          <OperationsList chantierId={chantierId} orgId={orgId} onRefresh={handleRefresh} />
        )}
        
        {activeTab === 'indicateurs' && (
          <Indicateurs chantier={chantier} />
        )}
        
        {activeTab === 'infos' && (
          <div className="space-y-6">
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
          </div>
        )}
        
        {activeTab === 'audit' && (
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
        )}
      </div>

      {/* Note de bas de page */}
      <div className="mt-8 text-sm text-muted-foreground border-t pt-4">
        <p>
          <strong>Note:</strong> Données chargées depuis l'API.
        </p>
      </div>
    </div>
  );
}

// Mappers snake_case -> camelCase pour correspondre aux types frontend

function mapSituation(s: any): Situation {
  return {
    id: s.id,
    chantierId: s.chantier_id,
    date: s.date || s.created_at,
    numero: s.numero,
    libelle: s.libelle || `Situation n°${s.numero}`,
    montant: s.montant,
    reglementObservation: s.reglement_observation,
    createdAt: s.created_at,
    updatedAt: s.updated_at || s.created_at,
  };
}

function mapDepense(d: any): Depense {
  return {
    id: d.id,
    chantierId: d.chantier_id,
    date: d.date || d.created_at,
    fournisseur: d.fournisseur || 'Non renseigné',
    categorie: (d.categorie as any) || 'autre',
    description: d.description,
    montant: d.montant,
    factureRef: d.facture_ref,
    createdAt: d.created_at,
    updatedAt: d.updated_at || d.created_at,
  };
}

function mapOperation(o: any): Operation {
  return {
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
  };
}

function mapReception(r: any): Reception {
  return {
    id: r.id,
    chantierId: r.chantier_id,
    date: r.date || r.created_at,
    type: r.type || 'suivi',
    statut: r.statut || 'planifiee',
    participants: r.participants || [],
    ordreDuJour: r.ordre_du_jour || '',
    decisions: r.decisions || '',
    pointsARegler: r.points_a_regler || '',
    documents: r.documents || [],
    createdAt: r.created_at,
    updatedAt: r.updated_at || r.created_at,
  };
}

function mapTache(t: any): Tache {
  return {
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
  };
}

function mapPointage(p: any): Pointage {
  return {
    id: p.id,
    date: p.date || p.created_at,
    chantierId: p.chantier_id,
    conducteurId: p.conducteur_id || '',
    ressources: (p.ressources || []).map((r: any) => ({
      ressourceId: r.ressource_id,
      ressourceNom: r.nom,
      type: r.type,
      periode: r.periode,
      heuresPrevues: r.heures_prevues,
    })),
    commentaires: p.commentaires,
    validePar: p.valide_par || '',
    valideLe: p.valide_le || undefined,
    createdAt: p.created_at,
    updatedAt: p.updated_at || p.created_at,
  };
}

function mapNotification(n: any): Notification {
  return {
    id: n.id,
    userId: n.user_id || '',
    type: n.type || 'info',
    entityType: 'chantier',
    entityId: n.chantier_id || '',
    titre: n.titre,
    message: n.message,
    url: n.url || '',
    statut: n.statut || 'envoyee',
    telegramMessageId: n.telegram_message_id || '',
    createdAt: n.created_at,
  };
}

function mapStatut(apiStatut?: string): 'en_cours' | 'termine' | 'en_attente' | 'cloture' {
  switch (apiStatut) {
    case 'en_cours': return 'en_cours';
    case 'termine': return 'termine';
    case 'cloture': return 'cloture';
    default: return 'en_attente';
  }
}


