"use client";

/**
 * LensSidebar - Sidebar d'analyse avec les Lentilles
 * 
 * Affiche les différentes lentilles d'analyse disponibles
 * et permet de lancer les analyses sur la candidature.
 */

import React, { useState } from 'react';
import { 
  BarChart3, 
  Pencil, 
  AlertTriangle, 
  Scale,
  TrendingUp,
  ChevronRight,
  Loader2,
  CheckCircle2,
  XCircle,
  HelpCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type LensType = 'pricing' | 'redaction' | 'risque' | 'comparaison' | 'opportunite';

export interface Lens {
  id: LensType;
  label: string;
  icon: React.ReactNode;
  description: string;
  color: string;
  bgColor: string;
}

export const AVAILABLE_LENSES: Lens[] = [
  {
    id: 'pricing',
    label: 'Analyse Pricing',
    icon: <BarChart3 className="w-5 h-5" />,
    description: 'Compare le BPU avec l\'historique de victoires et identifie les écarts >20%',
    color: 'text-green-700',
    bgColor: 'bg-green-100'
  },
  {
    id: 'redaction',
    label: 'Rédaction Mémoire',
    icon: <Pencil className="w-5 h-5" />,
    description: 'Rédige des chapitres du mémoire technique en s\'appuyant sur les dossiers gagnants',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100'
  },
  {
    id: 'risque',
    label: 'Scoring Risque',
    icon: <AlertTriangle className="w-5 h-5" />,
    description: 'Analyse le RC pour identifier les clauses contractuelles à risque',
    color: 'text-orange-700',
    bgColor: 'bg-orange-100'
  },
  {
    id: 'comparaison',
    label: 'Comparaison Historique',
    icon: <Scale className="w-5 h-5" />,
    description: 'Compare avec les AO gagnés/perdus similaires',
    color: 'text-purple-700',
    bgColor: 'bg-purple-100'
  },
  {
    id: 'opportunite',
    label: 'Analyse Opportunité',
    icon: <TrendingUp className="w-5 h-5" />,
    description: 'Évalue l\'attractivité de l\'opportunité et recommande GO/NO-GO',
    color: 'text-teal-700',
    bgColor: 'bg-teal-100'
  }
];

export interface LensResult {
  lensId: LensType;
  status: 'pending' | 'running' | 'completed' | 'error';
  result?: any;
  error?: string;
  timestamp?: Date;
}

interface LensSidebarProps {
  candidatureId: string;
  onRunLens: (lens: Lens) => Promise<void>;
  results: Record<LensType, LensResult>;
  className?: string;
}

export function LensSidebar({ 
  candidatureId, 
  onRunLens, 
  results,
  className 
}: LensSidebarProps) {
  const [expandedLens, setExpandedLens] = useState<LensType | null>(null);

  const handleLensClick = async (lens: Lens) => {
    if (results[lens.id]?.status === 'running') return;
    
    setExpandedLens(lens.id);
    await onRunLens(lens);
  };

  const getStatusIcon = (status: LensResult['status']) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className={cn("bg-white border-l flex flex-col h-full", className)}>
      {/* Header */}
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold text-gray-900">🔍 Lentilles d'Analyse</h2>
        <p className="text-sm text-gray-500 mt-1">
          Choisissez une lentille pour analyser la candidature
        </p>
      </div>

      {/* Liste des Lentilles */}
      <div className="flex-1 overflow-auto p-4 space-y-3">
        {AVAILABLE_LENSES.map((lens) => {
          const result = results[lens.id];
          const isExpanded = expandedLens === lens.id;
          const isRunning = result?.status === 'running';

          return (
            <div
              key={lens.id}
              className={cn(
                "border rounded-xl transition-all duration-200",
                isExpanded ? "border-blue-300 shadow-sm" : "border-gray-200 hover:border-gray-300",
                result?.status === 'completed' && "bg-gray-50"
              )}
            >
              {/* Header de la lentille */}
              <button
                onClick={() => handleLensClick(lens)}
                disabled={isRunning}
                className="w-full p-4 flex items-start gap-3 text-left"
              >
                <div className={cn("p-2.5 rounded-lg shrink-0", lens.bgColor, lens.color)}>
                  {lens.icon}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-gray-900">{lens.label}</h3>
                    {getStatusIcon(result?.status)}
                  </div>
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                    {lens.description}
                  </p>
                </div>

                <ChevronRight className={cn(
                  "w-5 h-5 text-gray-400 transition-transform shrink-0",
                  isExpanded && "rotate-90"
                )} />
              </button>

              {/* Contenu détaillé */}
              {isExpanded && result && (
                <div className="px-4 pb-4">
                  {result.status === 'completed' && result.result && (
                    <LensResultDisplay lensId={lens.id} result={result.result} />
                  )}
                  
                  {result.status === 'error' && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">{result.error}</p>
                    </div>
                  )}

                  {result.status === 'pending' && (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-center">
                      <p className="text-sm text-gray-500">Cliquez pour lancer l'analyse</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="p-4 border-t bg-gray-50">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <HelpCircle className="w-4 h-4" />
          <span>Les analyses utilisent Gemini 2.5 Pro/Flash</span>
        </div>
      </div>
    </div>
  );
}

// ========== AFFICHAGE DES RÉSULTATS ==========

interface LensResultDisplayProps {
  lensId: LensType;
  result: any;
}

function LensResultDisplay({ lensId, result }: LensResultDisplayProps) {
  switch (lensId) {
    case 'pricing':
      return <PricingResult result={result} />;
    case 'risque':
      return <RisqueResult result={result} />;
    case 'redaction':
      return <RedactionResult result={result} />;
    case 'comparaison':
      return <ComparaisonResult result={result} />;
    case 'opportunite':
      return <OpportuniteResult result={result} />;
    default:
      return <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto">{JSON.stringify(result, null, 2)}</pre>;
  }
}

// --- Pricing Result ---
function PricingResult({ result }: { result: any }) {
  const anomalies = result.anomalies || [];
  const opportunites = result.opportunites || [];

  return (
    <div className="space-y-3">
      {/* Synthèse */}
      {result.synthese && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-blue-900">Risque Global</span>
            <span className={cn(
              "px-2 py-0.5 rounded text-xs font-medium",
              result.synthese.risque_global === 'faible' && "bg-green-100 text-green-800",
              result.synthese.risque_global === 'moyen' && "bg-yellow-100 text-yellow-800",
              result.synthese.risque_global === 'élevé' && "bg-red-100 text-red-800"
            )}>
              {result.synthese.risque_global}
            </span>
          </div>
          <p className="text-sm text-blue-800">{result.synthese.recommandation_strategique}</p>
        </div>
      )}

      {/* Anomalies */}
      {anomalies.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-red-700 mb-2">
            ⚠️ {anomalies.length} Anomalie(s) détectée(s)
          </h4>
          <div className="space-y-2">
            {anomalies.slice(0, 3).map((anomalie: any, i: number) => (
              <div key={i} className="p-2 bg-red-50 border border-red-100 rounded text-sm">
                <div className="flex justify-between">
                  <span className="font-medium">{anomalie.poste_description || anomalie.poste_numero}</span>
                  <span className="text-red-600 font-medium">{anomalie.ecart_pct}</span>
                </div>
                <p className="text-xs text-gray-600 mt-1">{anomalie.recommandation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Opportunités */}
      {opportunites.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-green-700 mb-2">
            ✅ {opportunites.length} Opportunité(s)
          </h4>
          <ul className="space-y-1">
            {opportunites.slice(0, 3).map((opp: any, i: number) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-green-500 mt-0.5">•</span>
                <span>{typeof opp === 'string' ? opp : opp.description}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// --- Risque Result ---
function RisqueResult({ result }: { result: any }) {
  const score = result.score_global || result.score;
  const niveau = result.niveau_risque || result.niveau;
  const risques = result.risques_identifies || [];

  return (
    <div className="space-y-3">
      {/* Score */}
      <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
        <div className={cn(
          "w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold",
          score >= 70 ? "bg-green-100 text-green-700" :
          score >= 40 ? "bg-yellow-100 text-yellow-700" :
          "bg-red-100 text-red-700"
        )}>
          {score}
        </div>
        <div>
          <p className="text-sm font-medium text-gray-700">Score Global</p>
          <p className={cn(
            "text-sm font-medium",
            niveau === 'faible' && "text-green-600",
            niveau === 'moyen' && "text-yellow-600",
            niveau === 'élevé' && "text-red-600"
          )}>
            Risque {niveau}
          </p>
        </div>
      </div>

      {/* Risques identifiés */}
      {risques.length > 0 && (
        <div className="space-y-2">
          {risques.slice(0, 3).map((risque: any, i: number) => (
            <div key={i} className="p-2 border rounded">
              <div className="flex items-center gap-2">
                <span className={cn(
                  "w-2 h-2 rounded-full",
                  risque.niveau === 'élevé' && "bg-red-500",
                  risque.niveau === 'moyen' && "bg-yellow-500",
                  risque.niveau === 'faible' && "bg-green-500"
                )} />
                <span className="font-medium text-sm">{risque.categorie || 'Risque'}</span>
              </div>
              <p className="text-xs text-gray-600 mt-1">{risque.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recommandations */}
      {result.recommandations && result.recommandations.length > 0 && (
        <div className="p-2 bg-blue-50 rounded">
          <p className="text-xs font-medium text-blue-800 mb-1">Recommandations:</p>
          <ul className="text-xs text-blue-700 space-y-0.5">
            {result.recommandations.slice(0, 3).map((rec: string, i: number) => (
              <li key={i}>• {rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// --- Rédaction Result ---
function RedactionResult({ result }: { result: any }) {
  const content = result.content || '';
  const suggestions = result.suggestions || [];

  return (
    <div className="space-y-3">
      <div className="max-h-48 overflow-y-auto p-3 bg-gray-50 rounded border text-sm">
        <div 
          className="prose prose-sm max-w-none"
          dangerouslySetInnerHTML={{ 
            __html: content.length > 500 ? content.substring(0, 500) + '...' : content 
          }}
        />
      </div>

      {suggestions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-700 mb-1">💡 Suggestions:</p>
          <div className="flex flex-wrap gap-1">
            {suggestions.map((suggestion: string, i: number) => (
              <span key={i} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                {suggestion}
              </span>
            ))}
          </div>
        </div>
      )}

      <button className="w-full py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
        Ouvrir dans le Sandbox
      </button>
    </div>
  );
}

// --- Comparaison Result ---
function ComparaisonResult({ result }: { result: any }) {
  const probabilite = result.probabilite_gain || result.probabilite;
  const positionnement = result.positionnement_prix;

  return (
    <div className="space-y-3">
      {/* Probabilité */}
      <div className="p-3 bg-gray-50 rounded">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Probabilité de gain</span>
          <span className={cn(
            "text-lg font-bold",
            probabilite >= 0.6 ? "text-green-600" :
            probabilite >= 0.4 ? "text-yellow-600" :
            "text-red-600"
          )}>
            {Math.round((probabilite || 0) * 100)}%
          </span>
        </div>
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className={cn(
              "h-full transition-all",
              probabilite >= 0.6 ? "bg-green-500" :
              probabilite >= 0.4 ? "bg-yellow-500" :
              "bg-red-500"
            )}
            style={{ width: `${(probabilite || 0) * 100}%` }}
          />
        </div>
      </div>

      {/* Positionnement prix */}
      {positionnement && (
        <div className="p-2 border rounded">
          <p className="text-xs text-gray-500">Positionnement vs historique</p>
          <div className="flex justify-between text-sm mt-1">
            <span>vs Gagnés:</span>
            <span className={positionnement.vs_gagnes?.startsWith('+') ? 'text-red-600' : 'text-green-600'}>
              {positionnement.vs_gagnes}
            </span>
          </div>
        </div>
      )}

      {/* Facteurs de succès */}
      {result.facteurs_succes_identifies && (
        <div>
          <p className="text-xs font-medium text-green-700 mb-1">✅ Facteurs de succès</p>
          <ul className="text-xs text-gray-600 space-y-0.5">
            {result.facteurs_succes_identifies.slice(0, 3).map((facteur: string, i: number) => (
              <li key={i}>• {facteur}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// --- Opportunité Result ---
function OpportuniteResult({ result }: { result: any }) {
  const attractivite = result.attractivite || {};
  const recommandation = result.recommandation;

  return (
    <div className="space-y-3">
      {/* Score attractivité */}
      <div className="flex items-center gap-3">
        <div className={cn(
          "px-3 py-1 rounded-lg font-medium",
          attractivite.score >= 70 ? "bg-green-100 text-green-800" :
          attractivite.score >= 40 ? "bg-yellow-100 text-yellow-800" :
          "bg-red-100 text-red-800"
        )}>
          {attractivite.score}/100
        </div>
        <div>
          <p className="text-sm font-medium">Attractivité</p>
          <p className="text-xs text-gray-500">{attractivite.niveau}</p>
        </div>
      </div>

      {/* GO / NO-GO */}
      {recommandation && (
        <div className={cn(
          "p-3 rounded-lg text-center font-medium",
          recommandation === 'GO' ? "bg-green-100 text-green-800" :
          recommandation === 'NO-GO' ? "bg-red-100 text-red-800" :
          "bg-yellow-100 text-yellow-800"
        )}>
          Recommandation: {recommandation}
        </div>
      )}

      {/* Forces et Faiblesses */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-xs font-medium text-green-700 mb-1">Forces</p>
          <ul className="text-xs text-gray-600 space-y-0.5">
            {(result.forces || []).slice(0, 2).map((force: string, i: number) => (
              <li key={i}>• {force}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium text-red-700 mb-1">Faiblesses</p>
          <ul className="text-xs text-gray-600 space-y-0.5">
            {(result.faiblesses || []).slice(0, 2).map((faiblesse: string, i: number) => (
              <li key={i}>• {faiblesse}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
