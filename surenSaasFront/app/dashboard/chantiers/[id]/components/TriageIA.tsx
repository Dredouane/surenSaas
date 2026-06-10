'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  AlertCircle,
  CheckCircle,
  XCircle,
  Brain,
  Clock,
  FileText,
  ListChecks,
  ChevronDown,
  ChevronRight,
  Edit3,
  Save,
  Trash2,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';

interface ProposedAction {
  type: string;
  payload: Record<string, unknown>;
  confidence?: number;
  status?: string;
  created_id?: string;
  rejected_reason?: string;
  modified_payload?: Record<string, unknown> | null;
}

interface Analysis {
  id: string;
  summary: string;
  detected_urgency: string;
  proposed_actions: ProposedAction[];
  analyzed_at: string;
}

interface ThreadAnalysis {
  thread_uuid: string;
  subject: string;
  status: string;
  chantier_id: string | null;
  chantier_nom: string | null;
  analysis: Analysis | null;
}

interface Props {
  chantierId: string;
  orgId: string;
}

const ACTION_LABELS: Record<string, string> = {
  CREATE_TACHE: 'Tâche',
  CREATE_TASK: 'Tâche',
  CREATE_EXPENSE: 'Dépense',
  CREATE_OPERATION: 'Opération',
  SEND_NOTIFICATION: 'Notification',
  IGNORE: 'Ignorer',
};

const ACTION_COLORS: Record<string, string> = {
  CREATE_TACHE: 'border-l-blue-500',
  CREATE_TASK: 'border-l-blue-500',
  CREATE_EXPENSE: 'border-l-green-500',
  CREATE_OPERATION: 'border-l-purple-500',
  SEND_NOTIFICATION: 'border-l-orange-500',
  IGNORE: 'border-l-gray-400',
};

function getStatusBadge(status?: string) {
  switch (status) {
    case 'executed': return <Badge className="bg-green-100 text-green-700 border-green-200">Exécutée</Badge>;
    case 'accepted': return <Badge className="bg-blue-100 text-blue-700 border-blue-200">Acceptée</Badge>;
    case 'rejected': return <Badge variant="destructive">Rejetée</Badge>;
    case 'error': return <Badge variant="destructive">Erreur</Badge>;
    default: return <Badge variant="outline" className="border-yellow-300 text-yellow-700 bg-yellow-50">En attente</Badge>;
  }
}

export default function TriageIA({ chantierId, orgId }: Props) {
  const [analyses, setAnalyses] = useState<ThreadAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingAction, setProcessingAction] = useState<string | null>(null);
  const [expandedAnalysis, setExpandedAnalysis] = useState<string | null>(null);
  const [expandedActions, setExpandedActions] = useState<Record<string, boolean>>({});
  const [editingActions, setEditingActions] = useState<Record<string, boolean>>({});
  const [actionEdits, setActionEdits] = useState<Record<string, Record<string, string>>>({});
  const [rejectDialog, setRejectDialog] = useState<{ analysisId: string; actionIndex: number } | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    if (orgId) fetchAnalyses();
  }, [chantierId, orgId]);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const fetchAnalyses = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/v1/threads?org_id=${orgId}&chantier_id=${chantierId}&status=PENDING_VALIDATION&limit=50`,
        { credentials: 'include', headers: { 'Content-Type': 'application/json' } }
      );
      if (!response.ok) throw new Error('Erreur de chargement');
      const data = await response.json();
      setAnalyses(data.data || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (analysisId: string) => {
    setExpandedAnalysis(prev => prev === analysisId ? null : analysisId);
    setExpandedActions({});
    setEditingActions({});
  };

  const toggleActionExpand = (key: string) => {
    setExpandedActions(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const startEditing = (key: string, action: ProposedAction) => {
    setEditingActions(prev => ({ ...prev, [key]: true }));
    setActionEdits(prev => ({
      ...prev,
      [key]: {
        titre: String(action.payload?.titre || ''),
        description: String(action.payload?.description || ''),
        priorite: String(action.payload?.priorite || 'moyenne'),
        date_echeance: String(action.payload?.date_echeance || ''),
      },
    }));
  };

  const cancelEditing = (key: string) => {
    setEditingActions(prev => ({ ...prev, [key]: false }));
    setActionEdits(prev => {
      const copy = { ...prev };
      delete copy[key];
      return copy;
    });
  };

  const handleValidate = async (analysisId: string, actionIndex: number, action: ProposedAction) => {
    const key = `${analysisId}-${actionIndex}`;
    setProcessingAction(key);

    const modifications = editingActions[key] ? actionEdits[key] : undefined;

    try {
      const response = await fetch(
        `/api/v1/analysis/${analysisId}/actions/${actionIndex}/validate?org_id=${orgId}`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ modifications }),
        }
      );
      const result = await response.json();
      if (result.success) {
        setToast({ type: 'success', message: result.message });
        fetchAnalyses();
      } else {
        setToast({ type: 'error', message: result.message || 'Erreur validation' });
      }
    } catch (e) {
      setToast({ type: 'error', message: 'Erreur de communication' });
    } finally {
      setProcessingAction(null);
    }
  };

  const openRejectDialog = (analysisId: string, actionIndex: number) => {
    setRejectDialog({ analysisId, actionIndex });
    setRejectReason('');
  };

  const confirmReject = async () => {
    if (!rejectDialog) return;
    const { analysisId, actionIndex } = rejectDialog;
    const key = `${analysisId}-${actionIndex}`;
    setProcessingAction(key);

    try {
      const response = await fetch(
        `/api/v1/analysis/${analysisId}/actions/${actionIndex}/reject?org_id=${orgId}`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: rejectReason || 'Aucun motif' }),
        }
      );
      const result = await response.json();
      if (result.success) {
        setToast({ type: 'success', message: 'Action rejetée' });
        fetchAnalyses();
      } else {
        setToast({ type: 'error', message: result.message || 'Erreur rejet' });
      }
    } catch (e) {
      setToast({ type: 'error', message: 'Erreur de communication' });
    } finally {
      setProcessingAction(null);
      setRejectDialog(null);
    }
  };

  const getUrgencyBadge = (urgency: string) => {
    switch (urgency) {
      case 'HIGH': return <Badge variant="destructive">🔴 Haute</Badge>;
      case 'MEDIUM': return <Badge variant="default">🟡 Moyenne</Badge>;
      case 'LOW': return <Badge variant="secondary">🟢 Basse</Badge>;
      default: return <Badge variant="outline">{urgency}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 animate-pulse bg-gray-100 rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-red-500">
          <AlertCircle className="h-8 w-8 mx-auto mb-2" />
          <p>Erreur : {error}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-white text-sm ${
          toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'
        }`}>
          {toast.type === 'success' ? <CheckCircle className="inline h-4 w-4 mr-2" /> : <AlertCircle className="inline h-4 w-4 mr-2" />}
          {toast.message}
        </div>
      )}

      {/* Reject dialog */}
      <Dialog open={!!rejectDialog} onOpenChange={() => setRejectDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rejeter l'action</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-3">
            <Label>Motif du rejet</Label>
            <Textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Pourquoi cette action est-elle rejetée ?"
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialog(null)}>Annuler</Button>
            <Button variant="destructive" onClick={confirmReject}>Confirmer le rejet</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Main content */}
      {analyses.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium mb-2">Aucune analyse en attente</p>
            <p className="text-sm">Les analyses Hermès apparaîtront ici une fois les emails traités.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">
              Triage IA — {analyses.length} analyse(s) en attente
            </h2>
          </div>

          {analyses.map((item) => {
            const analysis = item.analysis;
            if (!analysis) return null;
            const isExpanded = expandedAnalysis === analysis.id;

            return (
              <Card key={item.thread_uuid} className="border-l-4 border-l-yellow-400">
                <CardHeader
                  className="pb-3 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => toggleExpand(analysis.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-base flex items-center gap-2 flex-wrap">
                        {getUrgencyBadge(analysis.detected_urgency)}
                        <span className="font-medium">{item.subject}</span>
                      </CardTitle>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(analysis.analyzed_at).toLocaleDateString('fr-FR', {
                            day: 'numeric', month: 'long', year: 'numeric',
                            hour: '2-digit', minute: '2-digit',
                          })}
                        </span>
                        <span className="flex items-center gap-1">
                          <FileText className="h-3 w-3" />
                          {analysis.proposed_actions?.length || 0} action(s)
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {isExpanded ? 'Réduire' : 'Détails'}
                      </span>
                      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </div>
                  </div>
                </CardHeader>

                {isExpanded && (
                  <CardContent className="pt-0 pb-4">
                    <p className="text-sm text-muted-foreground mb-4 bg-muted/50 p-3 rounded-md">
                      {analysis.summary}
                    </p>

                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground flex items-center gap-1 mb-2">
                        <ListChecks className="h-3 w-3" />
                        Actions proposées :
                      </p>

                      {analysis.proposed_actions?.map((action, idx) => {
                        const key = `${analysis.id}-${idx}`;
                        const isActionExpanded = expandedActions[key];
                        const isEditing = editingActions[key];
                        const edits = actionEdits[key] || {};
                        const isPending = !action.status || action.status === 'pending';

                        return (
                          <div
                            key={idx}
                            className={`border rounded-md p-3 transition-colors ${
                              ACTION_COLORS[action.type] || 'border-l-gray-400'
                            } border-l-4 ${action.status === 'error' ? 'bg-red-50' : ''} ${
                              action.status === 'executed' ? 'bg-green-50' : ''
                            } ${action.status === 'rejected' ? 'bg-gray-50 opacity-70' : ''}`}
                          >
                            {/* Action header */}
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-medium text-muted-foreground">
                                  {ACTION_LABELS[action.type] || action.type}
                                </span>
                                {getStatusBadge(action.status)}
                                {action.confidence && isPending && (
                                  <span className="text-[10px] text-muted-foreground">
                                    Confiance : {Math.round(action.confidence * 100)}%
                                  </span>
                                )}
                              </div>
                              <button
                                onClick={(e) => { e.stopPropagation(); toggleActionExpand(key); }}
                                className="text-muted-foreground hover:text-foreground"
                              >
                                {isActionExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                              </button>
                            </div>

                            {/* Titre toujours visible */}
                            <p className="text-sm font-medium flex items-center gap-2">
                              {isEditing ? (
                                <Input
                                  value={edits.titre || ''}
                                  onChange={(e) => setActionEdits(prev => ({
                                    ...prev, [key]: { ...prev[key], titre: e.target.value }
                                  }))}
                                  className="h-7 text-sm flex-1"
                                  placeholder="Titre de l'action"
                                />
                              ) : (
                                <>
                                  <span className="flex-1">
                                    {String(action.payload?.titre || action.payload?.description || 'Sans titre')}
                                  </span>
                                  {/* Badge priorité visible même non déplié */}
                                  {isPending && action.payload?.priorite && (
                                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded whitespace-nowrap ${
                                      String(action.payload.priorite) === 'haute'
                                        ? 'bg-red-100 text-red-700'
                                        : String(action.payload.priorite) === 'basse'
                                        ? 'bg-gray-100 text-gray-600'
                                        : 'bg-yellow-100 text-yellow-700'
                                    }`}>
                                      {String(action.payload.priorite).toUpperCase()}
                                    </span>
                                  )}
                                  {/* Montant pour dépenses visible non déplié */}
                                  {action.type === 'CREATE_EXPENSE' && !isEditing && (
                                    <span className="text-xs font-medium text-green-700 whitespace-nowrap">
                                      {Number(action.payload?.montant || 0).toFixed(0)} €
                                    </span>
                                  )}
                                </>
                              )}
                            </p>

                            {/* Expanded detail */}
                            {isActionExpanded && (
                              <div className="mt-3 space-y-3 border-t pt-3">
                                {/* Description */}
                                <div>
                                  <Label className="text-xs">Description</Label>
                                  {isEditing ? (
                                    <Textarea
                                      value={edits.description || ''}
                                      onChange={(e) => setActionEdits(prev => ({
                                        ...prev, [key]: { ...prev[key], description: e.target.value }
                                      }))}
                                      className="mt-1 text-sm"
                                      rows={2}
                                    />
                                  ) : (
                                    <p className="text-sm text-muted-foreground mt-0.5">
                                      {String(action.payload?.description || 'Aucune description')}
                                    </p>
                                  )}
                                </div>

                                {/* Priorité et échéance */}
                                <div className="grid grid-cols-2 gap-3">
                                  <div>
                                    <Label className="text-xs">Priorité</Label>
                                    {isEditing ? (
                                      <select
                                        value={edits.priorite || 'moyenne'}
                                        onChange={(e) => setActionEdits(prev => ({
                                          ...prev, [key]: { ...prev[key], priorite: e.target.value }
                                        }))}
                                        className="w-full mt-1 h-8 text-sm border rounded px-2"
                                      >
                                        <option value="basse">Basse</option>
                                        <option value="moyenne">Moyenne</option>
                                        <option value="haute">Haute</option>
                                      </select>
                                    ) : (
                                      <p className="text-sm mt-0.5 capitalize">
                                        {String(action.payload?.priorite || 'moyenne')}
                                      </p>
                                    )}
                                  </div>
                                  <div>
                                    <Label className="text-xs">Échéance</Label>
                                    {isEditing ? (
                                      <Input
                                        type="date"
                                        value={edits.date_echeance || ''}
                                        onChange={(e) => setActionEdits(prev => ({
                                          ...prev, [key]: { ...prev[key], date_echeance: e.target.value }
                                        }))}
                                        className="mt-1 h-8 text-sm"
                                      />
                                    ) : (
                                      <p className="text-sm mt-0.5">
                                        {String(action.payload?.date_echeance || 'Non définie')}
                                      </p>
                                    )}
                                  </div>
                                </div>

                                {/* Montant pour dépenses */}
                                {action.type === 'CREATE_EXPENSE' && (
                                  <div>
                                    <Label className="text-xs">Montant (€)</Label>
                                    <p className="text-sm mt-0.5 font-medium">
                                      {Number(action.payload?.montant || 0).toFixed(2)} €
                                    </p>
                                  </div>
                                )}

                                {/* Message pour notification */}
                                {action.type === 'SEND_NOTIFICATION' && (
                                  <div>
                                    <Label className="text-xs">Message</Label>
                                    <p className="text-sm mt-0.5">{String(action.payload?.message || '')}</p>
                                  </div>
                                )}

                                {/* Error message */}
                                {action.status === 'error' && action.rejected_reason && (
                                  <p className="text-xs text-red-600 bg-red-50 p-2 rounded">
                                    Erreur : {action.rejected_reason}
                                  </p>
                                )}

                                {/* Created ID */}
                                {action.created_id && (
                                  <p className="text-xs text-green-600">
                                    ID créé : {action.created_id}
                                  </p>
                                )}

                                {/* Actions buttons */}
                                {isPending && (
                                  <div className="flex items-center gap-2 pt-2 border-t">
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      className="text-red-600 border-red-200 hover:bg-red-50"
                                      onClick={() => openRejectDialog(analysis.id, idx)}
                                      disabled={processingAction === key}
                                    >
                                      {processingAction === key ? (
                                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                      ) : <XCircle className="h-3 w-3 mr-1" />}
                                      Rejeter
                                    </Button>

                                    {isEditing ? (
                                      <>
                                        <Button
                                          variant="outline"
                                          size="sm"
                                          onClick={() => cancelEditing(key)}
                                          disabled={processingAction === key}
                                        >
                                          <Trash2 className="h-3 w-3 mr-1" />
                                          Annuler
                                        </Button>
                                        <Button
                                          variant="default"
                                          size="sm"
                                          className="bg-green-600 hover:bg-green-700"
                                          onClick={() => handleValidate(analysis.id, idx, action)}
                                          disabled={processingAction === key}
                                        >
                                          {processingAction === key ? (
                                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                          ) : <Save className="h-3 w-3 mr-1" />}
                                          Valider
                                        </Button>
                                      </>
                                    ) : (
                                      <>
                                        <Button
                                          variant="outline"
                                          size="sm"
                                          onClick={() => startEditing(key, action)}
                                          disabled={processingAction === key}
                                        >
                                          <Edit3 className="h-3 w-3 mr-1" />
                                          Modifier
                                        </Button>
                                        <Button
                                          variant="default"
                                          size="sm"
                                          className="bg-green-600 hover:bg-green-700"
                                          onClick={() => handleValidate(analysis.id, idx, action)}
                                          disabled={processingAction === key}
                                        >
                                          {processingAction === key ? (
                                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                          ) : <CheckCircle className="h-3 w-3 mr-1" />}
                                          Valider
                                        </Button>
                                      </>
                                    )}
                                  </div>
                                )}

                                {/* Link to created task */}
                                {action.created_id && (
                                  <div className="pt-1">
                                    <a
                                      href={`/dashboard/chantiers/${chantierId}?tab=taches`}
                                      className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                                    >
                                      <ExternalLink className="h-3 w-3" />
                                      Voir dans les tâches
                                    </a>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
