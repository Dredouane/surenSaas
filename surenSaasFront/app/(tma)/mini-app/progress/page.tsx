'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { MediaInput } from '../components/MediaInput';
import { ModalConfirm } from '../components/ModalConfirm';
import { useTma } from '../providers';
import { tmaFetch } from '../components/tmaFetch';

export default function ProgressPage() {
  const { isReady, chantier } = useTma();
  const [saving, setSaving] = useState(false);
  const [extracted, setExtracted] = useState<any>(null);
  const [selectedSit, setSelectedSit] = useState<string | null>(null);
  const [showSituations, setShowSituations] = useState(false);
  const [situations, setSituations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSituations = useCallback(async () => {
    if (!chantier) return;
    const res = await tmaFetch(`/api/v1/chantiers/${chantier.id}/situations?statut=ouverte`);
    if (res.ok) { const d = await res.json(); setSituations(d.data || d || []); }
    setLoading(false);
  }, [chantier]);

  useEffect(() => { fetchSituations(); }, [fetchSituations]);

  const handleResult = useCallback((data: any) => {
    if (!selectedSit) { setShowSituations(true); return; }
    setExtracted(data);
  }, [selectedSit]);

  const handleError = useCallback((msg: string) => {
    if (!selectedSit) setShowSituations(true);
    console.error(msg);
  }, [selectedSit]);

  const handleConfirm = async () => {
    if (!extracted || !chantier || !selectedSit) return;
    setSaving(true);
    await tmaFetch(`/api/v1/chantiers/${chantier.id}/situations/${selectedSit}/lignes`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description: extracted.description || '',
        quantite: extracted.quantite || 0,
        prix_unitaire: extracted.prix_unitaire || 0,
        unite: extracted.unite || 'u',
        avancement_pourcentage: extracted.avancement_pourcentage || 0,
        montant_total: (extracted.quantite || 0) * (extracted.prix_unitaire || 0),
      }),
    });
    setExtracted(null);
    setSaving(false);
  };
  const handleCancel = () => setExtracted(null);

  if (!isReady || !chantier) return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />
      <div style={{ padding: '60px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: 'calc(100dvh - 180px)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>📈</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#F8FAFC', margin: 0 }}>Avancement</h2>
          <p style={{ fontSize: 13, color: '#64748B' }}>Décris, dicte ou prends une photo</p>
        </div>

        {selectedSit && (
          <div style={{ textAlign: 'center', marginBottom: 16, padding: '8px 14px', backgroundColor: 'rgba(255,107,53,0.1)', borderRadius: 8, border: '1px solid #FF6B35', fontSize: 13, color: '#FF6B35' }}>
            ✓ Situation sélectionnée · <button onClick={() => setShowSituations(true)} style={{ background: 'none', border: 'none', color: '#F8FAFC', textDecoration: 'underline', cursor: 'pointer', padding: 0, fontSize: 13 }}>Changer</button>
          </div>
        )}

        <MediaInput workflow="avancement" onResult={handleResult} onError={handleError} placeholder="Ex: Enduit facade 50m2 25€/m2 80%" />

        {!selectedSit && !showSituations && (
          <button onClick={() => setShowSituations(true)}
            style={{ marginTop: 16, padding: '12px 20px', backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: 10, color: '#94A3B8', fontSize: 14, cursor: 'pointer', width: '100%' }}>
            📄 Choisir une situation
          </button>
        )}
      </div>

      {showSituations && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 90, backgroundColor: '#0F172A', padding: '16px 20px', paddingTop: 60, overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC', margin: 0 }}>Situations ouvertes</h3>
            <button onClick={() => setShowSituations(false)} style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: 24, cursor: 'pointer', padding: 0 }}>✕</button>
          </div>
          {loading ? <div style={{ color: '#64748B' }}>Chargement...</div>
          : situations.length === 0 ? <div style={{ color: '#64748B' }}>Aucune situation ouverte.</div>
          : situations.map((s: any) => (
            <button key={s.id} onClick={() => { setSelectedSit(s.id); setShowSituations(false); }}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '14px 16px', backgroundColor: selectedSit === s.id ? 'rgba(255,107,53,0.15)' : '#1E293B', border: '1px solid', borderColor: selectedSit === s.id ? '#FF6B35' : '#334155', borderRadius: 10, cursor: 'pointer', marginBottom: 6, fontSize: 14, color: '#F8FAFC' }}>
              N°{s.numero} — {s.libelle}
              <div style={{ fontSize: 12, color: '#64748B' }}>{s.montant?.toLocaleString('fr-FR')}€</div>
            </button>
          ))}
        </div>
      )}

      <ModalConfirm visible={!!extracted && !!selectedSit} title="Avancement extrait" onConfirm={handleConfirm} onCancel={handleCancel} saving={saving} confirmLabel="✅ Envoyer">
        <div style={{ fontSize: 13, color: '#F8FAFC' }}>{extracted?.description}</div>
        <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 6 }}>
          Qté: {extracted?.quantite || '—'} · PU: {extracted?.prix_unitaire || '—'}€ · %: {extracted?.avancement_pourcentage || '—'}%
        </div>
      </ModalConfirm>

      <BottomTabs />
    </div>
  );
}
