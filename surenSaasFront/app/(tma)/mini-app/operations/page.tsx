'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { MediaInput } from '../components/MediaInput';
import { ModalConfirm } from '../components/ModalConfirm';
import { useTma } from '../providers';
import { tmaFetch, tmaExtract } from '../components/tmaFetch';

const OP_TYPES = [
  { id: 'demolition', emoji: '🏗️' }, { id: 'nettoyage', emoji: '🧹' },
  { id: 'pose_bso', emoji: '🪟' }, { id: 'commande', emoji: '📦' },
  { id: 'achat_materiel', emoji: '🛒' }, { id: 'sous_traitance', emoji: '🔧' },
  { id: 'autre', emoji: '📝' },
];

export default function OperationsPage() {
  const { isReady, chantier } = useTma();
  const [textInput, setTextInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [extracted, setExtracted] = useState<any>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [operations, setOperations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchOps = useCallback(async () => {
    if (!chantier) return;
    const res = await tmaFetch(`/api/v1/chantiers/${chantier.id}/operations`);
    if (res.ok) {
      const data = await res.json();
      setOperations(data.data || data || []);
    }
    setLoading(false);
  }, [chantier]);

  useEffect(() => { fetchOps(); }, [fetchOps]);

  const handleExtract = async () => {
    if (!textInput.trim()) return;
    setSaving(true);
    const result = await tmaExtract(textInput, 'operation');
    if (result?.data) setExtracted(result.data);
    setSaving(false);
  };

  const handleFileExtracted = async (t: string) => {
    setTextInput(t);
    setSaving(true);
    const r = await tmaExtract(t, 'operation');
    if (r?.data) setExtracted(r.data);
    setSaving(false);
  };

  const handleConfirm = async () => {
    if (!extracted || !chantier) return;
    setSaving(true);
    await tmaFetch(`/api/v1/chantiers/${chantier.id}/operations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description: extracted.description || textInput,
        type: extracted.type || 'autre',
        montant: extracted.montant || 0,
        quantite: extracted.quantite || 0,
        unite: extracted.unite || '',
        source: 'telegram_text',
      }),
    });
    setTextInput('');
    setExtracted(null);
    await fetchOps();
    setSaving(false);
  };

  const handleCancel = () => setExtracted(null);

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />

      <div style={{ padding: '60px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: 'calc(100dvh - 180px)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>📸</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#F8FAFC', margin: 0 }}>Nouvelle opération</h2>
          <p style={{ fontSize: 13, color: '#64748B', margin: '4px 0 0' }}>Décris, dicte ou prends une photo</p>
        </div>

        <MediaInput
          value={textInput}
          onChange={setTextInput}
          onExtract={handleExtract}
          onFileExtracted={handleFileExtracted}
          placeholder="Ex: Pose fenetres 5000€..."
          saving={saving}
        />
      </div>

      <div style={{ position: 'fixed', bottom: 80, right: 16, zIndex: 10 }}>
        <button onClick={() => setShowHistory(!showHistory)}
          style={{ width: 48, height: 48, borderRadius: '50%', backgroundColor: '#1E293B', border: '1px solid #334155', fontSize: 20, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          📋
        </button>
      </div>

      {showHistory && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 90, backgroundColor: '#0F172A', padding: '16px 20px', paddingTop: 60, overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC', margin: 0 }}>Opérations récentes</h3>
            <button onClick={() => setShowHistory(false)} style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: 24, cursor: 'pointer', padding: 0 }}>✕</button>
          </div>
          {loading ? <div style={{ color: '#64748B', fontSize: 13 }}>Chargement...</div>
          : operations.length === 0 ? <div style={{ color: '#64748B', fontSize: 13 }}>Aucune opération.</div>
          : operations.map((op: any) => (
            <div key={op.id} style={{ padding: '12px 14px', backgroundColor: '#1E293B', borderRadius: 8, border: '1px solid #334155', fontSize: 13, marginBottom: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#F8FAFC', fontWeight: 500 }}>{OP_TYPES.find(t=>t.id===op.type)?.emoji} {op.type}</span>
                <span style={{ color: op.statut === 'en_attente' ? '#F59E0B' : '#22C55E', fontSize: 11 }}>{op.statut}</span>
              </div>
              <div style={{ color: '#94A3B8', marginTop: 2, fontSize: 12 }}>{op.description?.substring(0, 80)}</div>
            </div>
          ))}
        </div>
      )}

      <ModalConfirm
        visible={!!extracted}
        title="Opération extraite"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        saving={saving}
        confirmLabel="✅ Envoyer"
      >
        <div style={{ fontSize: 13, color: '#F8FAFC' }}>
          {extracted?.type && <>{OP_TYPES.find(t => t.id === extracted.type)?.emoji} <strong>{extracted.type}</strong><br /></>}
          {extracted?.description}
        </div>
        <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 6 }}>
          Montant: <span style={{ color: '#FF6B35', fontWeight: 600 }}>{extracted?.montant || '—'}€</span>
          {extracted?.quantite ? ` · Qté: ${extracted.quantite} ${extracted.unite || ''}` : ''}
        </div>
        {extracted?.guardrail_issues?.length > 0 && (
          <div style={{ fontSize: 12, color: '#F59E0B', marginTop: 6 }}>⚠️ {extracted.guardrail_issues.join(', ')}</div>
        )}
      </ModalConfirm>

      <BottomTabs />
    </div>
  );
}
