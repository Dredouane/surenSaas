'use client';

import { useState } from 'react';
import { ProgressSlider } from './ProgressSlider';

interface Ligne {
  id?: string;
  description: string;
  quantite: number;
  unite?: string;
  prix_unitaire: number;
  avancement_pourcentage: number;
  montant_total?: number;
  photo_url?: string;
}

interface SituationCardProps {
  situation: {
    id: string;
    numero: number;
    libelle: string;
    montant: number;
    lignes?: Ligne[];
  };
  onAddLigne: (situationId: string, ligne: Ligne) => void;
  readOnly?: boolean;
}

export function SituationCard({ situation, onAddLigne, readOnly }: SituationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [description, setDescription] = useState('');
  const [quantite, setQuantite] = useState('');
  const [prixUnitaire, setPrixUnitaire] = useState('');
  const [avancement, setAvancement] = useState(0);

  const lignes = situation.lignes || [];
  const montantTotalLignes = lignes.reduce((s, l) => s + (l.montant_total || l.quantite * l.prix_unitaire), 0);

  const handleSubmit = () => {
    if (!description.trim()) return;
    const qte = parseFloat(quantite) || 0;
    const pu = parseFloat(prixUnitaire) || 0;
    onAddLigne(situation.id, {
      description: description.trim(),
      quantite: qte,
      prix_unitaire: pu,
      avancement_pourcentage: avancement,
      montant_total: qte * pu,
    });
    setDescription('');
    setQuantite('');
    setPrixUnitaire('');
    setAvancement(0);
  };

  return (
    <div
      style={{
        backgroundColor: '#1E293B',
        borderRadius: 12,
        border: '1px solid #334155',
        overflow: 'hidden',
      }}
    >
      <button
        onClick={() => !readOnly && setExpanded(!expanded)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 16px',
          backgroundColor: 'transparent',
          border: 'none',
          cursor: readOnly ? 'default' : 'pointer',
          WebkitTapHighlightColor: 'transparent',
        }}
      >
        <div style={{ textAlign: 'left' }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#F8FAFC' }}>
            N°{situation.numero} — {situation.libelle}
          </div>
          <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>
            {lignes.length} ligne{lignes.length !== 1 ? 's' : ''} · {montantTotalLignes.toLocaleString('fr-FR')}€ / {situation.montant.toLocaleString('fr-FR')}€
          </div>
        </div>
        {!readOnly && (
          <span style={{ fontSize: 18, color: '#64748B', transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
            ▾
          </span>
        )}
      </button>

      {expanded && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid #334155' }}>
          {/* Lignes existantes */}
          {lignes.length > 0 && (
            <div style={{ marginTop: 12, marginBottom: 12 }}>
              {lignes.map((l, i) => (
                <div
                  key={l.id || i}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom: '1px solid #1E293B',
                    fontSize: 13,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ color: '#F8FAFC' }}>{l.description}</div>
                    <div style={{ color: '#64748B', fontSize: 11 }}>
                      {l.quantite} {l.unite || 'u'} × {l.prix_unitaire}€
                    </div>
                  </div>
                  <div style={{ color: '#FF6B35', fontWeight: 600, fontSize: 14, marginLeft: 8 }}>
                    {l.avancement_pourcentage}%
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Nouvelle ligne */}
          <div style={{ marginTop: 8 }}>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description du travail réalisé..."
              rows={2}
              style={{
                width: '100%',
                padding: 10,
                backgroundColor: '#0F172A',
                border: '1px solid #334155',
                borderRadius: 8,
                color: '#F8FAFC',
                fontSize: 14,
                resize: 'none',
              }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <input
                value={quantite}
                onChange={(e) => setQuantite(e.target.value)}
                placeholder="Qté"
                type="number"
                style={{
                  flex: 1,
                  padding: 10,
                  backgroundColor: '#0F172A',
                  border: '1px solid #334155',
                  borderRadius: 8,
                  color: '#F8FAFC',
                  fontSize: 14,
                }}
              />
              <input
                value={prixUnitaire}
                onChange={(e) => setPrixUnitaire(e.target.value)}
                placeholder="PU (€)"
                type="number"
                style={{
                  flex: 1,
                  padding: 10,
                  backgroundColor: '#0F172A',
                  border: '1px solid #334155',
                  borderRadius: 8,
                  color: '#F8FAFC',
                  fontSize: 14,
                }}
              />
            </div>
            <div style={{ marginTop: 12 }}>
              <ProgressSlider value={avancement} onChange={setAvancement} label="Avancement" />
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
              <button
                onClick={() => {}}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '10px 16px',
                  backgroundColor: '#334155',
                  border: '1px solid #475569',
                  borderRadius: 8,
                  color: '#94A3B8',
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                📸 Photo
              </button>
              <button
                onClick={handleSubmit}
                style={{
                  flex: 1,
                  padding: '10px 16px',
                  backgroundColor: '#FF6B35',
                  border: 'none',
                  borderRadius: 8,
                  color: '#FFFFFF',
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                ✅ Ajouter
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
