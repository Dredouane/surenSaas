'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { useTma } from '../providers';
import { tmaFetch, tmaExtract } from '../components/tmaFetch';

export default function ExpensesPage() {
  const { isReady, chantier } = useTma();
  const [textInput, setTextInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [extracted, setExtracted] = useState<any>(null);
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
    setExtracted(null);
    const result = await tmaExtract(textInput, 'depense');
    if (result?.data) setExtracted(result.data);
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

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />
      <div style={{ padding: '16px 20px' }}>
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
            <input value={textInput} onChange={(e) => setTextInput(e.target.value)}
              placeholder="Décris la dépense (ou dicte-la)..."
              style={{
                flex: 1, padding: '12px 14px', backgroundColor: '#0F172A',
                border: '1px solid #334155', borderRadius: 10, color: '#F8FAFC', fontSize: 14,
              }}
              onKeyDown={(e) => e.key === 'Enter' && handleExtract()}
            />
            <button onClick={handleExtract} disabled={saving || !textInput.trim()}
              style={{
                padding: '12px 18px', backgroundColor: saving ? '#475569' : '#FF6B35',
                border: 'none', borderRadius: 10, color: '#FFF',
                fontSize: 14, fontWeight: 600,
                cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1,
              }}
            >{saving ? '...' : '📎 IA'}</button>
          </div>
          <div style={{ fontSize: 12, color: '#64748B', display: 'flex', gap: 12 }}>
            <span>🎤 Dictée vocale</span>
            <span>📸 Scanner facture</span>
          </div>
        </div>

        {extracted && (
          <div style={{ backgroundColor: '#1E293B', borderRadius: 10, padding: 14, marginBottom: 16, border: '1px solid #334155' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#FF6B35', marginBottom: 8 }}>📎 Dépense extraite</div>
            <div style={{ fontSize: 13, color: '#F8FAFC', marginBottom: 2 }}>
              {extracted.fournisseur && `🏢 ${extracted.fournisseur}`}
            </div>
            <div style={{ fontSize: 13, color: '#F8FAFC', marginBottom: 2 }}>{extracted.description}</div>
            <div style={{ fontSize: 12, color: '#94A3B8' }}>
              Montant: {extracted.montant || '—'}€ · Catégorie: {extracted.categorie || '—'}
            </div>
            {extracted.guardrail_issues?.length > 0 && (
              <div style={{ fontSize: 12, color: '#F59E0B', marginTop: 4 }}>
                ⚠️ {extracted.guardrail_issues.join(', ')}
              </div>
            )}
            <button onClick={handleConfirm} disabled={saving}
              style={{
                width: '100%', padding: 12, marginTop: 12,
                backgroundColor: '#22C55E', border: 'none', borderRadius: 8,
                color: '#FFF', fontSize: 14, fontWeight: 600, cursor: 'pointer',
              }}
            >✅ Confirmer la dépense</button>
          </div>
        )}

        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#94A3B8', marginBottom: 8 }}>Dépenses récentes</h3>
        {loading ? <div style={{ color: '#64748B', fontSize: 13 }}>Chargement...</div>
        : expenses.length === 0 ? <div style={{ color: '#64748B', fontSize: 13 }}>Aucune dépense.</div>
        : expenses.slice(0, 10).map((e: any) => (
          <div key={e.id} style={{
            padding: '10px 12px', backgroundColor: '#1E293B', borderRadius: 8,
            border: '1px solid #334155', fontSize: 13, marginBottom: 6,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#F8FAFC', fontWeight: 500 }}>{e.fournisseur}</span>
              <span style={{ color: '#FF6B35', fontWeight: 600 }}>{e.montant?.toLocaleString('fr-FR')}€</span>
            </div>
            <div style={{ color: '#94A3B8', fontSize: 12 }}>{e.description?.substring(0, 60)}</div>
          </div>
        ))}
      </div>
      <BottomTabs />
    </div>
  );
}
