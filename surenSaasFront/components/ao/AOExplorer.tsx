"use client";

/**
 * AOExplorer - Vue "Explorateur AO" (Split-Screen)
 * 
 * Layout:
 * - Gauche: Visualiseur de document (PDF/Texte) + Drafting Sandbox (bulle flottante)
 * - Droite: Sidebar d'analyse avec les Lentilles (Pricing, Rédaction, Risque)
 */

import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Eye, 
  BarChart3, 
  Pencil, 
  AlertTriangle, 
  ChevronRight,
  X,
  MessageSquare,
  Send,
  Loader2,
  Download,
  ExternalLink,
  File
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
interface AODocument {
  id: string;
  type_doc: string;
  nom_fichier: string;
  statut_traitement: 'pending' | 'processing' | 'processed' | 'error';
  metadata?: Record<string, any>;
}

interface AOCandidature {
  id: string;
  nom_projet: string;
  client_nom?: string;
  statut: 'en_cours' | 'gagne' | 'perdu' | 'abandonne';
  montant_total?: number;
}

interface AOLens {
  id: string;
  type: 'pricing' | 'redaction' | 'risque' | 'comparaison';
  label: string;
  icon: React.ReactNode;
  description: string;
}

const LENSES: AOLens[] = [
  {
    id: 'pricing',
    type: 'pricing',
    label: 'Analyse Pricing',
    icon: <BarChart3 className="w-4 h-4" />,
    description: 'Compare le BPU avec l\'historique de victoires'
  },
  {
    id: 'redaction',
    type: 'redaction',
    label: 'Rédaction Mémoire',
    icon: <Pencil className="w-4 h-4" />,
    description: 'Génère des chapitres du mémoire technique'
  },
  {
    id: 'risque',
    type: 'risque',
    label: 'Scoring Risque',
    icon: <AlertTriangle className="w-4 h-4" />,
    description: 'Analyse les clauses à risque du RC'
  }
];

interface AOExplorerProps {
  candidature: AOCandidature;
  documents: AODocument[];
  className?: string;
}

export function AOExplorer({ candidature, documents, className }: AOExplorerProps) {
  const [selectedDocument, setSelectedDocument] = useState<AODocument | null>(documents[0] || null);
  const [activeLens, setActiveLens] = useState<string | null>(null);
  const [isSandboxOpen, setIsSandboxOpen] = useState(false);
  const [lensResults, setLensResults] = useState<Record<string, any>>({});
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Contenu simulé du draft
  const [draftContent, setDraftContent] = useState(`<h3>Chapitre 3: Moyens Techniques</h3>
<p>Notre entreprise met à disposition de ce projet :</p>
<ul>
  <li><strong>Personnel qualifié</strong> : 2 chefs de chantier, 5 ouvriers expérimentés</li>
  <li><strong>Matériel adapté</strong> : camion-benne, bétonnière, échafaudages</li>
  <li><strong>Suivi qualité</strong> : contrôle à chaque phase par notre bureau d'études</li>
</ul>
<p>Ces moyens nous permettent de garantir le respect des délais et la qualité des ouvrages.</p>`);

  const handleDownloadDocument = async (documentId: string, filename: string) => {
    try {
      // Appeler l'API de téléchargement
      const response = await fetch(`/api/v1/ao/documents/${documentId}/download`, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (response.ok) {
        // La réponse est une redirection vers l'URL signée S3
        // Le navigateur gère automatiquement le téléchargement
        window.location.href = `/api/v1/ao/documents/${documentId}/download`;
      } else {
        console.error('Erreur lors du téléchargement:', response.statusText);
        alert('Erreur lors du téléchargement du document');
      }
    } catch (error) {
      console.error('Erreur téléchargement:', error);
      alert('Erreur lors du téléchargement du document');
    }
  };

  const handlePreviewDocument = async (documentId: string) => {
    try {
      // Appeler l'API de prévisualisation
      const response = await fetch(`/api/v1/ao/documents/${documentId}/preview`, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Ouvrir l'URL de prévisualisation dans un nouvel onglet
        if (data.preview_info.preview_url) {
          window.open(data.preview_info.preview_url, '_blank');
        }
        
        // Si c'est un PDF, on pourrait aussi intégrer un visualiseur
        if (data.preview_info.is_pdf) {
          // Option: intégrer un visualiseur PDF ici
          console.log('Document PDF disponible pour visualisation:', data);
        }
      } else {
        console.error('Erreur lors de la prévisualisation:', response.statusText);
        alert('Erreur lors de la prévisualisation du document');
      }
    } catch (error) {
      console.error('Erreur prévisualisation:', error);
      alert('Erreur lors de la prévisualisation du document');
    }
  };

  const handleRunLens = async (lens: AOLens) => {
    setActiveLens(lens.id);
    setIsAnalyzing(true);
    
    // Simuler l'appel API
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Résultats simulés
    const mockResults: Record<string, any> = {
      pricing: {
        anomalies: [
          { poste: 'Béton armé', ecart: '+18%', recommandation: 'Optimiser ferraillage' },
          { poste: 'Menuiseries', ecart: '+25%', recommandation: 'Changer fournisseur' }
        ],
        opportunites: ['Charpente compétitive', 'Peinture dans la moyenne']
      },
      redaction: {
        content: '<h3>Chapitre généré</h3><p>Contenu généré par IA...</p>',
        suggestions: ['Ajouter références', 'Détailler moyens humains']
      },
      risque: {
        score: 65,
        niveau: 'moyen',
        risques: [
          { clause: 'Pénalités retard', niveau: 'élevé' },
          { clause: 'Garantie décennale', niveau: 'normal' }
        ]
      }
    };
    
    setLensResults(prev => ({ ...prev, [lens.id]: mockResults[lens.type] }));
    setIsAnalyzing(false);
  };

  const handleIterateDraft = (instruction: string) => {
    // Simuler l'itération
    setDraftContent(prev => `${prev}\n<!-- Modifié: ${instruction} -->\n<p>[Contenu modifié selon: ${instruction}]</p>`);
  };

  return (
    <div className={cn("flex h-[calc(100vh-4rem)] bg-gray-50", className)}>
      {/* ========== PANNEAU GAUCHE: Visualiseur de Document ========== */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Barre d'outils documents */}
        <div className="bg-white border-b px-4 py-2 flex items-center gap-2 overflow-x-auto">
          <span className="text-sm font-medium text-gray-500 mr-2">Documents:</span>
          {documents.map((doc) => (
            <button
              key={doc.id}
              onClick={() => setSelectedDocument(doc)}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors",
                selectedDocument?.id === doc.id
                  ? "bg-blue-100 text-blue-700 border border-blue-200"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
            >
              <FileText className="w-4 h-4" />
              {doc.nom_fichier}
              {doc.statut_traitement === 'processed' && (
                <span className="w-2 h-2 rounded-full bg-green-500" />
              )}
            </button>
          ))}
        </div>

        {/* Zone de visualisation */}
        <div className="flex-1 p-4 overflow-auto">
          {selectedDocument ? (
            <div className="bg-white rounded-lg shadow-sm border h-full p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Eye className="w-5 h-5 text-gray-500" />
                  <h3 className="text-lg font-semibold truncate max-w-md">
                    {selectedDocument.nom_fichier}
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "px-2 py-1 rounded text-xs font-medium",
                    selectedDocument.type_doc === 'BPU' && "bg-green-100 text-green-800",
                    selectedDocument.type_doc === 'RC' && "bg-blue-100 text-blue-800",
                    selectedDocument.type_doc === 'CCTP' && "bg-purple-100 text-purple-800"
                  )}>
                    {selectedDocument.type_doc}
                  </span>
                  
                  {/* Boutons d'action */}
                  <button
                    onClick={() => handlePreviewDocument(selectedDocument.id)}
                    className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    title="Prévisualiser le document"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => handleDownloadDocument(selectedDocument.id, selectedDocument.nom_fichier)}
                    className="p-2 text-gray-600 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                    title="Télécharger le document"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* Zone d'information et prévisualisation */}
              <div className="space-y-4">
                {/* Informations du document */}
                <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="font-medium text-blue-800">Type de document</p>
                      <p className="text-blue-600">{selectedDocument.type_doc}</p>
                    </div>
                    <div>
                      <p className="font-medium text-blue-800">Statut traitement</p>
                      <p className={cn(
                        "font-medium",
                        selectedDocument.statut_traitement === 'processed' && "text-green-600",
                        selectedDocument.statut_traitement === 'processing' && "text-yellow-600",
                        selectedDocument.statut_traitement === 'error' && "text-red-600",
                        selectedDocument.statut_traitement === 'pending' && "text-gray-600"
                      )}>
                        {selectedDocument.statut_traitement === 'processed' && '✓ Traité'}
                        {selectedDocument.statut_traitement === 'processing' && '⏳ En cours'}
                        {selectedDocument.statut_traitement === 'error' && '❌ Erreur'}
                        {selectedDocument.statut_traitement === 'pending' && '⏱ En attente'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Actions rapides */}
                <div className="flex gap-3">
                  <button
                    onClick={() => handlePreviewDocument(selectedDocument.id)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span>Ouvrir dans un nouvel onglet</span>
                  </button>
                  
                  <button
                    onClick={() => handleDownloadDocument(selectedDocument.id, selectedDocument.nom_fichier)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    <span>Télécharger le document</span>
                  </button>
                </div>

                {/* Métadonnées extraites */}
                {selectedDocument.metadata && Object.keys(selectedDocument.metadata).length > 0 && (
                  <div className="bg-white border rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                      <File className="w-4 h-4" />
                      Métadonnées extraites par IA
                    </h4>
                    <div className="space-y-3">
                      {Object.entries(selectedDocument.metadata).map(([key, value]) => (
                        <div key={key} className="flex items-start">
                          <div className="w-1/3 font-medium text-gray-700 text-sm">{key}:</div>
                          <div className="w-2/3 text-gray-600 text-sm">
                            {typeof value === 'object' ? (
                              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto">
                                {JSON.stringify(value, null, 2)}
                              </pre>
                            ) : (
                              String(value)
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Note pour l'intégration future */}
                <div className="bg-gray-50 border rounded-lg p-4 text-center text-gray-500 text-sm">
                  <FileText className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p>
                    <strong>Visualiseur PDF intégré</strong> - En développement
                  </p>
                  <p className="mt-1">
                    Utilisez les boutons ci-dessus pour ouvrir ou télécharger le document.
                    Un visualiseur PDF intégré sera bientôt disponible.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <p>Sélectionnez un document à visualiser</p>
            </div>
          )}
        </div>
      </div>

      {/* ========== PANNEAU DROIT: Sidebar d'Analyse ========== */}
      <div className="w-96 bg-white border-l flex flex-col">
        {/* Header */}
        <div className="p-4 border-b">
          <h2 className="font-semibold text-gray-900">🔍 Analyse IA</h2>
          <p className="text-sm text-gray-500 mt-1">
            {candidature.nom_projet}
          </p>
        </div>

        {/* Liste des Lentilles */}
        <div className="p-4 space-y-3">
          {LENSES.map((lens) => (
            <div
              key={lens.id}
              className={cn(
                "border rounded-lg p-3 cursor-pointer transition-all",
                activeLens === lens.id
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
              )}
              onClick={() => handleRunLens(lens)}
            >
              <div className="flex items-center gap-3">
                <div className={cn(
                  "p-2 rounded-lg",
                  lens.type === 'pricing' && "bg-green-100 text-green-700",
                  lens.type === 'redaction' && "bg-blue-100 text-blue-700",
                  lens.type === 'risque' && "bg-orange-100 text-orange-700"
                )}>
                  {lens.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm">{lens.label}</h4>
                  <p className="text-xs text-gray-500 truncate">{lens.description}</p>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>

              {/* Résultats de la lentille */}
              {activeLens === lens.id && lensResults[lens.id] && (
                <div className="mt-3 pt-3 border-t">
                  {lens.type === 'pricing' && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-orange-600">
                        ⚠️ {lensResults.pricing.anomalies.length} anomalies détectées
                      </p>
                      {lensResults.pricing.anomalies.map((a: any, i: number) => (
                        <div key={i} className="text-xs bg-white p-2 rounded border">
                          <span className="font-medium">{a.poste}</span>
                          <span className="text-red-500 ml-2">{a.ecart}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {lens.type === 'risque' && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl font-bold">{lensResults.risque.score}</span>
                        <span className={cn(
                          "px-2 py-0.5 rounded text-xs",
                          lensResults.risque.niveau === 'moyen' && "bg-yellow-100 text-yellow-800"
                        )}>
                          {lensResults.risque.niveau}
                        </span>
                      </div>
                    </div>
                  )}

                  {lens.type === 'redaction' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setIsSandboxOpen(true);
                      }}
                      className="w-full mt-2 px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                    >
                      Ouvrir dans le Sandbox
                    </button>
                  )}
                </div>
              )}

              {/* Indicateur de chargement */}
              {activeLens === lens.id && isAnalyzing && (
                <div className="mt-3 flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyse en cours...
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Espace réservé pour autres infos */}
        <div className="flex-1 p-4 border-t">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Métriques</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Documents</span>
              <span className="font-medium">{documents.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Statut</span>
              <span className={cn(
                "px-2 py-0.5 rounded text-xs",
                candidature.statut === 'en_cours' && "bg-blue-100 text-blue-800",
                candidature.statut === 'gagne' && "bg-green-100 text-green-800",
                candidature.statut === 'perdu' && "bg-red-100 text-red-800"
              )}>
                {candidature.statut}
              </span>
            </div>
            {candidature.montant_total && (
              <div className="flex justify-between">
                <span className="text-gray-500">Montant</span>
                <span className="font-medium">
                  {candidature.montant_total.toLocaleString('fr-FR')} €
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ========== DRAFTING SANDBOX (Bulle Flottante) ========== */}
      {isSandboxOpen && (
        <DraftingSandbox
          content={draftContent}
          onContentChange={setDraftContent}
          onIterate={handleIterateDraft}
          onClose={() => setIsSandboxOpen(false)}
        />
      )}
    </div>
  );
}

// ========== DRAFTING SANDBOX ==========
interface DraftingSandboxProps {
  content: string;
  onContentChange: (content: string) => void;
  onIterate: (instruction: string) => void;
  onClose: () => void;
}

function DraftingSandbox({ content, onContentChange, onIterate, onClose }: DraftingSandboxProps) {
  const [instruction, setInstruction] = useState('');
  const [history, setHistory] = useState<string[]>([]);

  const handleSend = () => {
    if (!instruction.trim()) return;
    
    setHistory(prev => [...prev, instruction]);
    onIterate(instruction);
    setInstruction('');
  };

  return (
    <div className="fixed bottom-4 right-4 w-[500px] bg-white rounded-xl shadow-2xl border flex flex-col max-h-[70vh] z-50">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b bg-gray-50 rounded-t-xl">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-blue-600" />
          <span className="font-medium">Drafting Sandbox</span>
        </div>
        <button 
          onClick={onClose}
          className="p-1 hover:bg-gray-200 rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Éditeur */}
      <div className="flex-1 p-4 overflow-auto min-h-[300px]">
        <div 
          className="prose prose-sm max-w-none"
          contentEditable
          onBlur={(e) => onContentChange(e.currentTarget.innerHTML)}
          dangerouslySetInnerHTML={{ __html: content }}
        />
      </div>

      {/* Historique des itérations */}
      {history.length > 0 && (
        <div className="px-4 py-2 bg-gray-50 border-y text-xs">
          <p className="text-gray-500 mb-1">Modifications:</p>
          <ul className="space-y-1">
            {history.map((h, i) => (
              <li key={i} className="text-gray-700">• {h}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Input "Petit Prompt" */}
    <div className="p-3 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Demander une modification... (ex: 'Raccourcir de 20%')"
            className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={!instruction.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          💡 Essayez: "Rendre plus formel", "Ajouter détails techniques", "Raccourcir"
        </p>
      </div>
    </div>
  );
}
