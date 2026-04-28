'use client';

import { useTma } from '../providers';

export function ProgressBar() {
  const { chantier } = useTma();

  const montantRevise = chantier?.montant_revise || 0;
  const facture = chantier?.situations_facturees || 0;
  const pct = montantRevise > 0 ? Math.min(Math.round((facture / montantRevise) * 100), 100) : 0;

  return (
    <div
      style={{
        padding: '12px 20px',
        backgroundColor: '#1E293B',
        borderBottom: '1px solid #334155',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 13, color: '#94A3B8' }}>Progression facturation</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#FF6B35' }}>{pct}%</span>
      </div>
      <div
        style={{
          height: 8,
          backgroundColor: '#334155',
          borderRadius: 4,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            backgroundColor: '#FF6B35',
            borderRadius: 4,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 11, color: '#64748B' }}>
          Facturé : {facture.toLocaleString('fr-FR')} €
        </span>
        <span style={{ fontSize: 11, color: '#64748B' }}>
          Total : {montantRevise.toLocaleString('fr-FR')} €
        </span>
      </div>
    </div>
  );
}
