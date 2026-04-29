'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { MediaInput } from '../components/MediaInput';
import { ModalConfirm } from '../components/ModalConfirm';
import { useTma } from '../providers';
import { tmaFetch, tmaExtract } from '../components/tmaFetch';

export default function ExpensesPage() {
  const { isReady, chantier } = useTma();
  const [textInput, setTextInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [extracted, setExtracted] = useState<any>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [expenses, setExpenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchExpenses = useCallback(async () => {
    if (!chantier) return;
    const res = await tmaFetch(`/api/v1/chantiers/${chantier.id}/depenses`);
    if (res.ok) {
      const data = await res.json();
      setExpenses(data.data || data || []);
    }
    setLoading(false);
  }, [chantier]);

  useEffect(() => { fetchExpenses(); }, [fetchExpenses]);

  const handleExtract = async () => {
    if (!textInput.trim()) return;
    setSaving(true);
    const result = await tmaExtract(textInput, 'depense');
    if (result?.data) setExtracted(result.data);
    setSaving(false);
  };

  const handleFileExtracted = async (t: string) => {
    setTextInput(t);
    setSaving(true);
    const r = await tmaExtract(t, 'depense');
    if (r?.data) setExtracted(r.data);
    setSaving(false);
  };

  const handleConfirm = async () => {
    if (!extracted || !chantier) return;
    setSaving(true);
    await tmaFetch(`/api/v1/chantiers/${chantier.id}/depenses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fournisseur: extracted.fournisseur || 'Non spécifié',
        montant: extracted.montant || 0,
        categorie: extracted.categorie || 'autre',
        description: extracted.description || textInput,
        date: new Date().toISOString().split('T')[0],
      }),
    });
    setTextInput('');
    setExtracted(null);
    await fetchExpenses();
    setSaving(false);
  };

  const handleCancel = () => {
    setExtracted(null);
  };

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />

      {/* Plein écran : barre de saisie + boutons média */}
      <div style={{ padding: '60px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: 'calc(100dvh - 180px)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>💰</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#F8FAFC', margin: 0 }}>Nouvelle dépense</h2>
          <p style={{ fontSize: 13, color: '#64748B', margin: '4px 0 0' }}>Décris, dicte ou prends une photo</p>
        </div>

        <MediaInput
          value={textInput}
          onChange={setTextInput}
          onExtract={handleExtract}
          onFileExtracted={handleFileExtracted}
          placeholder="Ex: Ciment Batimat 1500€..."
          saving={saving}
        />
      </div>

      {/* Bouton historique */}
      <div style={{
        position: 'fixed',
        bottom: 80,
        right: 16,
        zIndex: 10,
      }}>
        <button
          onClick={() => setShowHistory(!showHistory)}
          style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            backgroundColor: '#1E293B',
            border: '1px solid #334155',
            fontSize: 20,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          📋
        </button>
      </div>

      {/* Historique (panneau latéral) */}
      {showHistory && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          zIndex: 90,
          backgroundColor: '#0F172A',
          padding: '16px 20px',
          paddingTop: 60,
          overflowY: 'auto',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC', margin: 0 }}>Dépenses récentes</h3>
            <button onClick={() => setShowHistory(false)}
              style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: 24, cursor: 'pointer', padding: 0 }}>
              ✕
            </button>
          </div>
          {loading ? <div style={{ color: '#64748B', fontSize: 13 }}>Chargement...</div>
          : expenses.length === 0 ? <div style={{ color: '#64748B', fontSize: 13 }}>Aucune dépense.</div>
          : expenses.map((e: any) => (
            <div key={e.id} style={{
              padding: '12px 14px', backgroundColor: '#1E293B', borderRadius: 8,
              border: '1px solid #334155', fontSize: 13, marginBottom: 6,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#F8FAFC', fontWeight: 500 }}>{e.fournisseur}</span>
                <span style={{ color: '#FF6B35', fontWeight: 600 }}>{e.montant?.toLocaleString('fr-FR')}€</span>
              </div>
              <div style={{ color: '#94A3B8', fontSize: 12 }}>{e.description?.substring(0, 60)}</div>
              <div style={{ color: '#64748B', fontSize: 11, marginTop: 2 }}>{e.date?.substring(0, 10)}</div>
            </div>
          ))}
        </div>
      )}

      {/* Modal de confirmation */}
      <ModalConfirm
        visible={!!extracted}
        title="Dépense extraite"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        saving={saving}
        confirmLabel="✅ Envoyer"
      >
        <div style={{ fontSize: 13, color: '#F8FAFC', marginBottom: 4 }}>
          {extracted?.fournisseur && <>🏢 <strong>{extracted.fournisseur}</strong><br /></>}
          {extracted?.description}
        </div>
        <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 6 }}>
          Montant: <span style={{ color: '#FF6B35', fontWeight: 600 }}>{extracted?.montant || '—'}€</span>
          {' · '}Catégorie: {extracted?.categorie || '—'}
        </div>
        {extracted?.guardrail_issues?.length > 0 && (
          <div style={{ fontSize: 12, color: '#F59E0B', marginTop: 6 }}>
            ⚠️ {extracted.guardrail_issues.join(', ')}
          </div>
        )}
      </ModalConfirm>

      <BottomTabs />
    </div>
  );
}
