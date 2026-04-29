'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { MediaInput } from '../components/MediaInput';
import { useTma } from '../providers';
import { tmaFetch, tmaExtract } from '../components/tmaFetch';

export default function SituationsPage() {
  const { isReady, chantier } = useTma();
  const [situations, setSituations] = useState<any[]>([]);
  const [textInput, setTextInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [extracted, setExtracted] = useState<any>(null);
  const [selectedSituation, setSelectedSituation] = useState<string | null>(null);

  const fetchSituations = useCallback(async () => {
    if (!chantier) return;
    const res = await tmaFetch(`/api/v1/chantiers/${chantier.id}/situations?statut=ouverte`);
    if (res.ok) {
      const data = await res.json();
      setSituations(data.data || data || []);
    }
    setLoading(false);
  }, [chantier]);

  useEffect(() => { fetchSituations(); }, [fetchSituations]);

  const handleExtract = async () => {
    if (!textInput.trim()) return;
    setSaving(true);
    setExtracted(null);
    const result = await tmaExtract(textInput, 'avancement');
    console.log('🔍 extract result:', result);
    if (result?.data) {
      console.log('✅ extracted data:', result.data);
      setExtracted(result.data);
    } else {
      console.warn('⚠️ no data in extract result');
    }
    setSaving(false);
  };

  const handleConfirm = async () => {
    if (!extracted || !selectedSituation || !chantier) return;
    setSaving(true);
    const ligne = {
      description: extracted.description || textInput,
      quantite: extracted.quantite || 0,
      prix_unitaire: extracted.prix_unitaire || 0,
      unite: extracted.unite || 'u',
      avancement_pourcentage: extracted.avancement_pourcentage || 0,
      montant_total: (extracted.quantite || 0) * (extracted.prix_unitaire || 0),
    };
    await tmaFetch(`/api/v1/chantiers/${chantier.id}/situations/${selectedSituation}/lignes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ligne),
    });
    setTextInput('');
    setExtracted(null);
    await fetchSituations();
    setSaving(false);
  };

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />
      <div style={{ padding: '16px 20px' }}>
        {/* Barre de saisie texte + extraction IA + media */}
        <div style={{ marginBottom: 16 }}>
          <MediaInput
            value={textInput}
            onChange={setTextInput}
            onExtract={handleExtract}
            onFileExtracted={async (t) => { setTextInput(t); setSaving(true); setExtracted(null); const r = await tmaExtract(t, 'avancement'); if (r?.data) setExtracted(r.data); setSaving(false); }}
            placeholder="Décris l'avancement..."
            saving={saving}
          />
        </div>

        {/* Résultat extraction */}
        {extracted && (
          <div style={{ backgroundColor: '#1E293B', borderRadius: 10, padding: 14, marginBottom: 16, border: '1px solid #334155' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#FF6B35', marginBottom: 8 }}>📎 Données extraites</div>
            <div style={{ fontSize: 13, color: '#F8FAFC', marginBottom: 4 }}>{extracted.description}</div>
            <div style={{ fontSize: 12, color: '#94A3B8' }}>
              Qté: {extracted.quantite || '—'} · PU: {extracted.prix_unitaire || '—'}€ · %: {extracted.avancement_pourcentage || '—'}%
            </div>
            {!extracted.is_valid && extracted.guardrail_issues && (
              <div style={{ fontSize: 12, color: '#EF4444', marginTop: 4 }}>
                ⚠️ {extracted.guardrail_issues.join(', ')}
              </div>
            )}
          </div>
        )}

        {/* Sélection situation */}
        {loading ? (
          <div style={{ color: '#94A3B8', textAlign: 'center', padding: 24 }}>Chargement...</div>
        ) : situations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: '#94A3B8' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📄</div>
            <div style={{ fontSize: 15 }}>Aucune situation ouverte.</div>
          </div>
        ) : (
          <div>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#94A3B8', marginBottom: 8 }}>
              Situations ouvertes
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {situations.map((s: any) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedSituation(s.id)}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '12px 14px',
                    backgroundColor: selectedSituation === s.id ? 'rgba(255,107,53,0.15)' : '#1E293B',
                    border: '1px solid', borderColor: selectedSituation === s.id ? '#FF6B35' : '#334155',
                    borderRadius: 10, cursor: 'pointer', width: '100%',
                    WebkitTapHighlightColor: 'transparent',
                  }}
                >
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: 14, fontWeight: 500, color: '#F8FAFC' }}>N°{s.numero} — {s.libelle}</div>
                    <div style={{ fontSize: 12, color: '#64748B' }}>{s.montant?.toLocaleString('fr-FR')}€</div>
                  </div>
                  {selectedSituation === s.id && <span style={{ color: '#FF6B35' }}>✓</span>}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Bouton confirmer */}
        {extracted && selectedSituation && (
          <button onClick={handleConfirm} disabled={saving}
            style={{
              width: '100%', padding: 14, marginTop: 16,
              backgroundColor: saving ? '#475569' : '#FF6B35',
              border: 'none', borderRadius: 10, color: '#FFF',
              fontSize: 15, fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer',
            }}
          >{saving ? 'Enregistrement...' : '✅ Confirmer l\'avancement'}</button>
        )}
      </div>
      <BottomTabs />
    </div>
  );
}
