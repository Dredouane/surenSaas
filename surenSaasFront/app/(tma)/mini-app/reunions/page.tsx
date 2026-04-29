'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { useTma } from '../providers';
import { tmaFetch } from '../components/tmaFetch';

export default function ReunionsPage() {
  const { isReady, chantier } = useTma();
  const [reunions, setReunions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [textInput, setTextInput] = useState('');

  const fetch = useCallback(async () => {
    if (!chantier) return;
    const res = await tmaFetch(`/api/v1/chantiers/${chantier.id}/receptions`);
    if (res.ok) {
      const data = await res.json();
      setReunions(data.data || data || []);
    }
    setLoading(false);
  }, [chantier]);

  useEffect(() => { fetch(); }, [fetch]);

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />
      <div style={{ padding: '16px 20px' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#94A3B8', marginBottom: 8 }}>Réunions</h3>
        {loading ? (
          <div style={{ color: '#64748B', fontSize: 13 }}>Chargement...</div>
        ) : reunions.length === 0 ? (
          <div style={{ color: '#64748B', fontSize: 13, textAlign: 'center', padding: 24 }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📅</div>
            Aucune réunion planifiée.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {reunions.map((r: any) => (
              <div key={r.id} style={{
                padding: '12px 14px', backgroundColor: '#1E293B', borderRadius: 8,
                border: '1px solid #334155', fontSize: 13,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#F8FAFC', fontWeight: 500 }}>{r.type}</span>
                  <span style={{ color: '#64748B', fontSize: 12 }}>{r.date?.substring(0, 10)}</span>
                </div>
                <div style={{ color: '#94A3B8', marginTop: 2 }}>
                  {r.ordre_du_jour?.substring(0, 100)}
                </div>
                <div style={{ color: r.statut === 'planifiee' ? '#F59E0B' : '#22C55E', fontSize: 11, marginTop: 4 }}>
                  {r.statut}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <BottomTabs />
    </div>
  );
}
