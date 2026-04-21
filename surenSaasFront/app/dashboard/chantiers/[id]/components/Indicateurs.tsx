'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import {
  BarChart3,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Target,
  PieChart,
  Calendar,
} from 'lucide-react';
import { Chantier } from '@/types/chantier';
import {
  calculerPourcentageFacture,
  calculerMargeBrute,
  calculerSoldeAFacturer,
  calculerMargePourcentage,
} from '@/lib/chantier-data';

interface IndicateursProps {
  chantier: Chantier;
}

export default function Indicateurs({ chantier }: IndicateursProps) {
  // Calculer les indicateurs
  const pourcentageFacture = calculerPourcentageFacture(chantier.montantRevise, chantier.situationsFacturees);
  const margeBrute = calculerMargeBrute(chantier.montantRevise, chantier.totalDepenses);
  const soldeAFacturer = calculerSoldeAFacturer(chantier.montantRevise, chantier.situationsFacturees);
  const margePourcentage = calculerMargePourcentage(chantier.montantRevise, chantier.totalDepenses);

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

  // Obtenir la couleur selon la valeur
  const getColorClass = (value: number, type: 'positive' | 'negative' | 'neutral' = 'neutral') => {
    if (type === 'positive') {
      return value >= 80 ? 'text-green-600' : value >= 60 ? 'text-amber-600' : 'text-red-600';
    }
    if (type === 'negative') {
      return value > 0 ? 'text-green-600' : 'text-red-600';
    }
    return 'text-gray-600';
  };

  // Obtenir l'icône de tendance
  const getTrendIcon = (value: number, type: 'positive' | 'negative' = 'positive') => {
    if (type === 'positive') {
      return value >= 80 ? (
        <TrendingUp className="h-5 w-5 text-green-600" />
      ) : value >= 60 ? (
        <TrendingUp className="h-5 w-5 text-amber-600" />
      ) : (
        <TrendingDown className="h-5 w-5 text-red-600" />
      );
    } else {
      return value > 0 ? (
        <TrendingUp className="h-5 w-5 text-green-600" />
      ) : (
        <TrendingDown className="h-5 w-5 text-red-600" />
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Indicateurs principaux */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avancement facturation</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-2xl font-bold ${getColorClass(pourcentageFacture, 'positive')}`}>
                {formatPourcentage(pourcentageFacture)}
              </div>
              {getTrendIcon(pourcentageFacture, 'positive')}
            </div>
            <Progress value={pourcentageFacture} className="h-2" />
            <div className="flex justify-between text-sm text-muted-foreground mt-2">
              <span>Facturé: {formatMontant(chantier.situationsFacturees)}</span>
              <span>Objectif: {formatMontant(chantier.montantRevise)}</span>
            </div>
            <div className="mt-4 text-sm">
              <div className="flex justify-between mb-1">
                <span>Montant base:</span>
                <span className="font-medium">{formatMontant(chantier.montantBase)}</span>
              </div>
              <div className="flex justify-between mb-1">
                <span>TS / avenants:</span>
                <span className="font-medium">{formatMontant(chantier.tsAvenants)}</span>
              </div>
              <div className="flex justify-between font-bold">
                <span>Marché révisé:</span>
                <span>{formatMontant(chantier.montantRevise)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Marge brute</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-2xl font-bold ${getColorClass(margeBrute, 'negative')}`}>
                {formatMontant(margeBrute)}
              </div>
              {getTrendIcon(margeBrute, 'negative')}
            </div>
            <div className="text-sm text-muted-foreground mb-4">
              {formatPourcentage(margePourcentage)} de marge
            </div>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Chiffre d'affaires</span>
                  <span className="font-medium">{formatMontant(chantier.montantRevise)}</span>
                </div>
                <Progress value={100} className="h-2" />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Coûts</span>
                  <span className="font-medium">{formatMontant(chantier.totalDepenses)}</span>
                </div>
                <Progress 
                  value={(chantier.totalDepenses / chantier.montantRevise) * 100} 
                  className="h-2 bg-red-100 [&>div]:bg-red-500"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Marge</span>
                  <span className="font-medium">{formatMontant(margeBrute)}</span>
                </div>
                <Progress 
                  value={margePourcentage} 
                  className="h-2 bg-green-100 [&>div]:bg-green-500"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Solde à facturer</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-2xl font-bold ${getColorClass(soldeAFacturer, 'neutral')}`}>
                {formatMontant(soldeAFacturer)}
              </div>
              <DollarSign className="h-5 w-5 text-blue-600" />
            </div>
            <div className="text-sm text-muted-foreground mb-4">
              Reste à facturer sur le marché
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Montant marché:</span>
                <span className="font-medium">{formatMontant(chantier.montantRevise)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Déjà facturé:</span>
                <span className="font-medium">{formatMontant(chantier.situationsFacturees)}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between font-bold">
                <span>Solde restant:</span>
                <span className="text-lg">{formatMontant(soldeAFacturer)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Répartition des coûts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="h-5 w-5" />
            Répartition des coûts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-4">Analyse des dépenses</h4>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Coût total du chantier</span>
                    <span className="font-medium">{formatMontant(chantier.montantRevise)}</span>
                  </div>
                  <Progress value={100} className="h-3" />
                </div>
                
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Dépenses engagées</span>
                    <span className="font-medium">{formatMontant(chantier.totalDepenses)}</span>
                  </div>
                  <Progress 
                    value={(chantier.totalDepenses / chantier.montantRevise) * 100} 
                    className="h-3 bg-blue-100 [&>div]:bg-blue-500"
                  />
                  <div className="text-xs text-muted-foreground mt-1">
                    {(chantier.totalDepenses / chantier.montantRevise * 100).toFixed(1)}% du budget
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Marge brute</span>
                    <span className="font-medium">{formatMontant(margeBrute)}</span>
                  </div>
                  <Progress 
                    value={margePourcentage} 
                    className="h-3 bg-green-100 [&>div]:bg-green-500"
                  />
                  <div className="text-xs text-muted-foreground mt-1">
                    {margePourcentage.toFixed(1)}% de marge
                  </div>
                </div>
              </div>
            </div>
            
            <div>
              <h4 className="font-medium mb-4">Indicateurs clés</h4>
              <div className="space-y-4">
                <div className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">Efficacité financière</div>
                      <div className="text-xs text-muted-foreground">Ratio marge/CA</div>
                    </div>
                    <div className={`text-lg font-bold ${margePourcentage >= 20 ? 'text-green-600' : 'text-amber-600'}`}>
                      {margePourcentage.toFixed(1)}%
                    </div>
                  </div>
                </div>
                
                <div className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">Taux de facturation</div>
                      <div className="text-xs text-muted-foreground">Avancement facturation</div>
                    </div>
                    <div className={`text-lg font-bold ${pourcentageFacture >= 80 ? 'text-green-600' : 'text-amber-600'}`}>
                      {pourcentageFacture.toFixed(1)}%
                    </div>
                  </div>
                </div>
                
                <div className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">Rentabilité projet</div>
                      <div className="text-xs text-muted-foreground">Marge absolue</div>
                    </div>
                    <div className={`text-lg font-bold ${margeBrute > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatMontant(margeBrute)}
                    </div>
                  </div>
                </div>
                
                <div className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">Potentiel restant</div>
                      <div className="text-xs text-muted-foreground">Solde à facturer</div>
                    </div>
                    <div className="text-lg font-bold text-blue-600">
                      {formatMontant(soldeAFacturer)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Projections */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Projections et objectifs
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="text-sm font-medium mb-2">Objectif facturation</div>
                <div className="text-2xl font-bold text-green-600">
                  {formatPourcentage(100)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Objectif final: {formatMontant(chantier.montantRevise)}
                </div>
              </div>
              
              <div className="p-4 border rounded-lg">
                <div className="text-sm font-medium mb-2">Marge cible</div>
                <div className="text-2xl font-bold text-green-600">
                  {formatPourcentage(25)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Objectif: {formatMontant(chantier.montantRevise * 0.25)}
                </div>
              </div>
              
              <div className="p-4 border rounded-lg">
                <div className="text-sm font-medium mb-2">Dépenses prévisionnelles</div>
                <div className="text-2xl font-bold text-blue-600">
                  {formatMontant(chantier.montantRevise * 0.75)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Basé sur 75% du CA
                </div>
              </div>
            </div>
            
            <div className="p-4 border rounded-lg bg-muted/30">
              <h4 className="font-medium mb-2">Recommandations</h4>
              <ul className="space-y-2 text-sm">
                {pourcentageFacture < 80 && (
                  <li className="flex items-start gap-2">
                    <div className="mt-1 h-2 w-2 rounded-full bg-amber-500"></div>
                    <span>
                      <strong>Accélérer la facturation:</strong> Le taux de facturation est de {pourcentageFacture.toFixed(1)}%.
                      Objectif: atteindre 80% dans les 30 jours.
                    </span>
                  </li>
                )}
                
                {margePourcentage < 20 && (
                  <li className="flex items-start gap-2">
                    <div className="mt-1 h-2 w-2 rounded-full bg-red-500"></div>
                    <span>
                      <strong>Contrôler les coûts:</strong> La marge est de {margePourcentage.toFixed(1)}%.
                      Objectif: atteindre 20% en optimisant les dépenses.
                    </span>
                  </li>
                )}
                
                {soldeAFacturer > chantier.montantRevise * 0.3 && (
                  <li className="flex items-start gap-2">
                    <div className="mt-1 h-2 w-2 rounded-full bg-blue-500"></div>
                    <span>
                      <strong>Planifier les facturations:</strong> Il reste {formatMontant(soldeAFacturer)} à facturer.
                      Recommandation: établir un échéancier de facturation.
                    </span>
                  </li>
                )}
                
                <li className="flex items-start gap-2">
                  <div className="mt-1 h-2 w-2 rounded-full bg-green-500"></div>
                  <span>
                    <strong>Suivi opérationnel:</strong> Utiliser la section "Opérations" pour suivre
                    les remontées terrain et anticiper les dépenses futures.
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Note */}
      <div className="text-sm text-muted-foreground">
        <p>
          <strong>Note:</strong> Ces indicateurs sont calculés en temps réel à partir des données
          du chantier. Ils se mettent à jour automatiquement lors de l'ajout/modification
          de situations, dépenses ou opérations.
        </p>
        <p className="mt-2">
          Dans la prochaine itération, ces calculs seront effectués côté serveur et pourront
          inclure des projections basées sur l'historique des chantiers similaires.
        </p>
      </div>
    </div>
  );
}