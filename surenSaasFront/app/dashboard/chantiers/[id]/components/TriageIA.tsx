'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertCircle,
  CheckCircle,
  XCircle,
  Brain,
  Clock,
  FileText,
  ListChecks,
} from 'lucide-react';

interface ProposedAction {
  type: string;
  payload: Record<string, unknown>;
  confidence?: number;
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
  analysis: Analysis | null;
}

interface Props {
  chantierId: string;
  orgId: string;
}

export default function TriageIA({ chantierId, orgId }: Props) {
  const [analyses, setAnalyses] = useState<ThreadAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    if (orgId) fetchAnalyses();
  }, [chantierId, orgId]);

  const fetchAnalyses = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/v1/emails?org_id=${orgId}&chantier_id=${chantierId}&status=PENDING_VALIDATION&limit=50`,
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

  const handleValidate = async (analysisId: string) => {
    setProcessingId(analysisId);
    try {
      const response = await fetch(`/api/v1/analysis/${analysisId}/execute?org_id=${orgId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'accept' }),
      });
      if (!response.ok) throw new Error('Erreur validation');
      setAnalyses((prev) => prev.filter((a) => a.analysis?.id !== analysisId));
    } catch (e) {
      console.error('Erreur validation:', e);
      alert('Erreur lors de la validation');
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (analysisId: string) => {
    const reason = prompt('Motif du rejet :');
    if (!reason) return;
    setProcessingId(analysisId);
    try {
      const response = await fetch(`/api/v1/analysis/${analysisId}/execute?org_id=${orgId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reject', rejection_reason: reason }),
      });
      if (!response.ok) throw new Error('Erreur rejet');
      setAnalyses((prev) => prev.filter((a) => a.analysis?.id !== analysisId));
    } catch (e) {
      console.error('Erreur rejet:', e);
      alert('Erreur lors du rejet');
    } finally {
      setProcessingId(null);
    }
  };

  const getUrgencyBadge = (urgency: string) => {
    switch (urgency) {
      case 'HIGH':
        return <Badge variant="destructive">🔴 Haute</Badge>;
      case 'MEDIUM':
        return <Badge variant="default">🟡 Moyenne</Badge>;
      case 'LOW':
        return <Badge variant="secondary">🟢 Basse</Badge>;
      default:
        return <Badge variant="outline">{urgency}</Badge>;
    }
  };

  const actionLabels: Record<string, string> = {
    CREATE_TACHE: 'Tâche',
    CREATE_EXPENSE: 'Dépense',
    CREATE_OPERATION: 'Opération',
    SEND_NOTIFICATION: 'Notification',
    IGNORE: 'Ignorer',
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-32 w-full" />
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

  if (analyses.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium mb-2">Aucune analyse en attente</p>
          <p className="text-sm">
            Les analyses Hermès apparaîtront ici une fois les emails traités.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
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

        return (
          <Card key={item.thread_uuid} className="border-l-4 border-l-yellow-400">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-base flex items-center gap-2">
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
              </div>
            </CardHeader>
            <CardContent className="pb-3">
              <p className="text-sm text-muted-foreground mb-3 line-clamp-3">
                {analysis.summary}
              </p>

              {analysis.proposed_actions && analysis.proposed_actions.length > 0 && (
                <div className="mb-3 space-y-1">
                  <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <ListChecks className="h-3 w-3" />
                    Actions proposées :
                  </p>
                  <ul className="text-xs space-y-0.5">
                    {analysis.proposed_actions.map((action, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-muted-foreground">
                        <span className="h-1 w-1 rounded-full bg-muted-foreground" />
                        {actionLabels[action.type] || action.type}
                        {action.payload?.titre && ` — ${action.payload.titre}`}
                        {action.confidence && (
                          <span className="text-[10px] opacity-60">
                            ({Math.round(action.confidence * 100)}%)
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex items-center gap-2 pt-2 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-red-600 border-red-200 hover:bg-red-50"
                  onClick={() => handleReject(analysis.id)}
                  disabled={processingId === analysis.id}
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Rejeter
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  className="bg-green-600 hover:bg-green-700"
                  onClick={() => handleValidate(analysis.id)}
                  disabled={processingId === analysis.id}
                >
                  <CheckCircle className="h-4 w-4 mr-1" />
                  {processingId === analysis.id ? 'Traitement...' : 'Valider'}
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
