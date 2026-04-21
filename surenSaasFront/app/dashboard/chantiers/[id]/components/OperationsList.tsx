'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
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
import { Separator } from '@/components/ui/separator';
import {
  Plus,
  Search,
  Filter,
  CheckCircle,
  Clock,
  XCircle,
  Mic,
  Camera,
  MessageSquare,
  FileText,
  User,
  Calendar,
  History,
} from 'lucide-react';
import { Operation, OperationStatut, OperationType, OperationSource } from '@/types/chantier';

interface OperationsListProps {
  chantierId: string;
  operations: Operation[];
}

export default function OperationsList({ chantierId, operations }: OperationsListProps) {
  const [search, setSearch] = useState('');
  const [filterStatut, setFilterStatut] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [filterSource, setFilterSource] = useState('all');

  // Filtrer les opérations
  const filteredOperations = operations.filter(operation => {
    if (search && !operation.description.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (filterStatut !== 'all' && operation.statut !== filterStatut) {
      return false;
    }
    if (filterType !== 'all' && operation.type !== filterType) {
      return false;
    }
    if (filterSource !== 'all' && operation.source !== filterSource) {
      return false;
    }
    return true;
  });

  // Statistiques
  const stats = {
    total: operations.length,
    valide: operations.filter(op => op.statut === 'valide').length,
    enAttente: operations.filter(op => op.statut === 'en_attente').length,
    rejete: operations.filter(op => op.statut === 'rejete').length,
  };

  // Formater une date
  const formatDate = (dateString: string | Date) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR') + ' à ' + date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  // Formater un montant
  const formatMontant = (montant?: number) => {
    if (!montant) return '—';
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(montant);
  };

  // Obtenir la couleur du badge selon le statut
  const getStatutBadge = (statut: OperationStatut) => {
    switch (statut) {
      case 'valide':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100 gap-1">
          <CheckCircle className="h-3 w-3" />
          Validé
        </Badge>;
      case 'en_attente':
        return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100 gap-1">
          <Clock className="h-3 w-3" />
          En attente
        </Badge>;
      case 'rejete':
        return <Badge className="bg-red-100 text-red-800 hover:bg-red-100 gap-1">
          <XCircle className="h-3 w-3" />
          Rejeté
        </Badge>;
      default:
        return <Badge variant="outline">{statut}</Badge>;
    }
  };

  // Obtenir l'icône selon le type
  const getTypeIcon = (type: OperationType) => {
    switch (type) {
      case 'demolition':
        return <span className="text-red-500">⚒️</span>;
      case 'nettoyage':
        return <span className="text-blue-500">🧹</span>;
      case 'pose_bso':
        return <span className="text-green-500">🔧</span>;
      case 'commande':
        return <span className="text-purple-500">📦</span>;
      case 'achat_materiel':
        return <span className="text-amber-500">🛒</span>;
      case 'sous_traitance':
        return <span className="text-indigo-500">👥</span>;
      default:
        return <span className="text-gray-500">📝</span>;
    }
  };

  // Obtenir l'icône selon la source
  const getSourceIcon = (source: OperationSource) => {
    switch (source) {
      case 'telegram_voice':
        return <Mic className="h-4 w-4 text-blue-500" />;
      case 'telegram_photo':
        return <Camera className="h-4 w-4 text-green-500" />;
      case 'telegram_text':
        return <MessageSquare className="h-4 w-4 text-purple-500" />;
      case 'telegram_pdf':
        return <FileText className="h-4 w-4 text-red-500" />;
      case 'email':
        return <MessageSquare className="h-4 w-4 text-amber-500" />;
      case 'manuel':
        return <User className="h-4 w-4 text-gray-500" />;
      default:
        return <History className="h-4 w-4 text-gray-500" />;
    }
  };

  // Obtenir le libellé du type
  const getTypeLabel = (type: OperationType) => {
    switch (type) {
      case 'demolition': return 'Démolition';
      case 'nettoyage': return 'Nettoyage';
      case 'pose_bso': return 'Pose BSO';
      case 'commande': return 'Commande';
      case 'achat_materiel': return 'Achat matériel';
      case 'sous_traitance': return 'Sous-traitance';
      case 'autre': return 'Autre';
      default: return type;
    }
  };

  // Handler pour ajouter une opération manuellement
  const handleAddOperation = () => {
    alert('Fonctionnalité d\'ajout manuel à implémenter dans la prochaine itération');
  };

  // Handler pour valider une opération (HITL)
  const handleValidateOperation = (operationId: string) => {
    alert(`Fonctionnalité de validation HITL à implémenter pour l'opération ${operationId}`);
  };

  // Handler pour réinitialiser les filtres
  const handleResetFilters = () => {
    setSearch('');
    setFilterStatut('all');
    setFilterType('all');
    setFilterSource('all');
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <CardTitle>Opérations / Tâches à faire</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              Suivi des opérations terrain avec mécanisme HITL (Human-in-the-Loop)
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-3">
            <Button onClick={handleAddOperation} className="gap-2">
              <Plus className="h-4 w-4" />
              Ajouter manuellement
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Statistiques */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="p-4 border rounded-lg bg-green-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-800">Validées</p>
                <p className="text-2xl font-bold text-green-900">{stats.valide}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
          </div>
          
          <div className="p-4 border rounded-lg bg-amber-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-amber-800">En attente</p>
                <p className="text-2xl font-bold text-amber-900">{stats.enAttente}</p>
              </div>
              <Clock className="h-8 w-8 text-amber-600" />
            </div>
          </div>
          
          <div className="p-4 border rounded-lg bg-gray-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-800">Total opérations</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
              </div>
              <History className="h-8 w-8 text-gray-600" />
            </div>
          </div>
        </div>

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
              value={filterStatut}
              onValueChange={setFilterStatut}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Statut" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous statuts</SelectItem>
                <SelectItem value="valide">Validé</SelectItem>
                <SelectItem value="en_attente">En attente</SelectItem>
                <SelectItem value="rejete">Rejeté</SelectItem>
              </SelectContent>
            </Select>
            
            <Select
              value={filterType}
              onValueChange={setFilterType}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous types</SelectItem>
                <SelectItem value="demolition">Démolition</SelectItem>
                <SelectItem value="nettoyage">Nettoyage</SelectItem>
                <SelectItem value="pose_bso">Pose BSO</SelectItem>
                <SelectItem value="commande">Commande</SelectItem>
                <SelectItem value="achat_materiel">Achat matériel</SelectItem>
                <SelectItem value="sous_traitance">Sous-traitance</SelectItem>
                <SelectItem value="autre">Autre</SelectItem>
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

        {filteredOperations.length === 0 ? (
          <div className="text-center py-12">
            <History className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium">Aucune opération trouvée</h3>
            <p className="text-muted-foreground mt-2">
              Aucune opération ne correspond à vos critères de recherche.
            </p>
            <Button onClick={handleResetFilters} className="mt-4">
              Réinitialiser les filtres
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredOperations.map((operation) => (
              <div key={operation.id} className="border rounded-lg p-4 hover:bg-muted/30 transition-colors">
                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-start gap-3">
                      <div className="mt-1">
                        {getTypeIcon(operation.type)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h4 className="font-medium text-lg">{operation.description}</h4>
                          {getStatutBadge(operation.statut)}
                        </div>
                        
                        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground mb-3">
                          <div className="flex items-center gap-1">
                            {getSourceIcon(operation.source)}
                            <span>{operation.sourceDetails}</span>
                          </div>
                          
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            <span>{formatDate(operation.date)}</span>
                          </div>
                          
                          <div className="flex items-center gap-1">
                            <span className="font-medium">{getTypeLabel(operation.type)}</span>
                          </div>
                          
                          {operation.quantite && (
                            <div className="flex items-center gap-1">
                              <span className="font-medium">{operation.quantite} {operation.unite || 'unités'}</span>
                            </div>
                          )}
                          
                          {operation.montant && (
                            <div className="flex items-center gap-1">
                              <span className="font-medium">{formatMontant(operation.montant)}</span>
                            </div>
                          )}
                        </div>
                        
                        {operation.commentaire && (
                          <div className="bg-muted/30 p-3 rounded-md">
                            <p className="text-sm">{operation.commentaire}</p>
                          </div>
                        )}
                        
                        {operation.validePar && (
                          <div className="mt-3 flex items-center gap-2 text-sm">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">Validé par:</span>
                            <span>{operation.validePar}</span>
                            <span className="text-muted-foreground">le {formatDate(operation.valideLe!)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row gap-2">
                    {operation.statut === 'en_attente' && (
                      <>
                        <Button
                          size="sm"
                          className="gap-2 bg-green-600 hover:bg-green-700"
                          onClick={() => handleValidateOperation(operation.id)}
                        >
                          <CheckCircle className="h-4 w-4" />
                          Valider
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-2"
                          onClick={() => handleValidateOperation(operation.id)}
                        >
                          <XCircle className="h-4 w-4" />
                          Rejeter
                        </Button>
                      </>
                    )}
                    <Button variant="ghost" size="sm">
                      Voir détails
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Note HITL */}
        <div className="mt-8 p-4 border border-blue-200 rounded-lg bg-blue-50">
          <div className="flex items-start gap-3">
            <div className="mt-1">
              <User className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h4 className="font-medium text-blue-900">Mécanisme HITL (Human-in-the-Loop)</h4>
              <p className="text-sm text-blue-800 mt-1">
                Cette section démontre le processus de validation humaine des opérations terrain.
                Les conducteurs remontent des informations via Telegram (voice, photo, texte, PDF),
                qui apparaissent ici en "En attente" pour validation par le gérant.
              </p>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="text-sm">
                  <span className="font-medium">Flux actuel:</span>
                  <ul className="list-disc list-inside mt-1 text-blue-800">
                    <li>Conducteur → Telegram → Dashboard → "En attente"</li>
                    <li>Gérant valide/rejette → Mise à jour automatique</li>
                  </ul>
                </div>
                <div className="text-sm">
                  <span className="font-medium">Prochaine itération:</span>
                  <ul className="list-disc list-inside mt-1 text-blue-800">
                    <li>Intégration réelle avec bot Telegram</li>
                    <li>Classification automatique par IA</li>
                    <li>Notifications en temps réel</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Note prototype */}
        <div className="mt-6 text-sm text-muted-foreground">
          <p>
            <strong>Note prototype:</strong> Cette section "Opérations/Tâches à faire" est la nouveauté
            qui démontre l'intégration Telegram + HITL. Les opérations sont classées par type, source
            et statut de validation.
          </p>
          <p className="mt-2">
            Dans la prochaine itération, cette section sera alimentée en temps réel par le bot Telegram
            construction via les webhooks existants.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}