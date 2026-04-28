'use client';

import { useTma } from '../providers';

const STATUT_LABELS: Record<string, { label: string; color: string }> = {
  en_cours: { label: 'En cours', color: '#22C55E' },
  termine: { label: 'Terminé', color: '#3B82F6' },
  en_attente: { label: 'En attente', color: '#F59E0B' },
  cloture: { label: 'Clôturé', color: '#64748B' },
};

export function ChantierHeader() {
  const { chantier } = useTma();

  if (!chantier) {
    return (
      <div style={{ padding: '16px 20px', backgroundColor: '#1E293B' }}>
        <div style={{ color: '#94A3B8', fontSize: 15 }}>Aucun chantier sélectionné</div>
      </div>
    );
  }

  const statutInfo = STATUT_LABELS[chantier.statut] || { label: chantier.statut, color: '#94A3B8' };

  return (
    <div
      style={{
        padding: '16px 20px',
        backgroundColor: '#1E293B',
        borderBottom: '1px solid #334155',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <h1 style={{ fontSize: 18, fontWeight: 600, margin: 0, color: '#F8FAFC' }}>
          {chantier.nom}
        </h1>
        <span
          style={{
            display: 'inline-block',
            padding: '2px 10px',
            borderRadius: 999,
            fontSize: 12,
            fontWeight: 500,
            backgroundColor: `${statutInfo.color}20`,
            color: statutInfo.color,
          }}
        >
          {statutInfo.label}
        </span>
      </div>
      <div style={{ fontSize: 13, color: '#94A3B8' }}>
        {chantier.ref} {chantier.conducteur ? `— ${chantier.conducteur}` : ''}
      </div>
    </div>
  );
}
