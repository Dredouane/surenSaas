'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { useTma } from '../providers';

const OPERATION_TYPES = [
  { id: 'demolition', label: 'Démolition', emoji: '🏗️' },
  { id: 'nettoyage', label: 'Nettoyage', emoji: '🧹' },
  { id: 'pose_bso', label: 'Pose BSO', emoji: '🪟' },
  { id: 'commande', label: 'Commande', emoji: '📦' },
  { id: 'achat_materiel', label: 'Achat', emoji: '🛒' },
  { id: 'sous_traitance', label: 'Sous-traitance', emoji: '🔧' },
  { id: 'autre', label: 'Autre', emoji: '📝' },
] as const;

export default function OperationsPage() {
  const { isReady, chantier, jwt } = useTma();
  const [selectedType, setSelectedType] = useState<string>('autre');
  const [textInput, setTextInput] = useState('');
  const [montant, setMontant] = useState('');
  const [saving, setSaving] = useState(false);
  const [operations, setOperations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchOperations = useCallback(async () => {
    if (!chantier || !jwt) return;
    try {
      const res = await fetch(`/api/v1/chantiers/${chantier.id}/operations?limit=10`, {
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (res.ok) {
        const data = await res.json();
        setOperations(data.data || data || []);
      }
    } catch (err) {
      console.error('Erreur chargement opérations:', err);
    } finally {
      setLoading(false);
    }
  }, [chantier, jwt]);

  useEffect(() => { fetchOperations(); }, [fetchOperations]);

  const handleSubmit = async () => {
    if (!textInput.trim() || !chantier || !jwt) return;
    setSaving(true);
    try {
      const payload: any = {
        description: textInput.trim(),
        type: selectedType,
        source: 'telegram_text',
      };
      if (montant) payload.montant = parseFloat(montant);

      await fetch(`/api/v1/chantiers/${chantier.id}/operations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
        body: JSON.stringify(payload),
      });

      setTextInput('');
      setMontant('');
      await fetchOperations();
    } catch (err) {
      console.error('Erreur création opération:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />

      {/* Sélecteur de type horizontal */}
      <div style={{
        overflowX: 'auto',
        padding: '12px 16px',
        borderBottom: '1px solid #334155',
        WebkitOverflowScrolling: 'touch',
      }}>
        <div style={{ display: 'flex', gap: 8, minWidth: 'max-content' }}>
          {OPERATION_TYPES.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelectedType(t.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 14px',
                borderRadius: 20,
                border: '1px solid',
                borderColor: selectedType === t.id ? '#FF6B35' : '#334155',
                backgroundColor: selectedType === t.id ? 'rgba(255, 107, 53, 0.15)' : 'transparent',
                color: selectedType === t.id ? '#FF6B35' : '#94A3B8',
                fontSize: 13,
                fontWeight: selectedType === t.id ? 600 : 400,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                WebkitTapHighlightColor: 'transparent',
              }}
            >
              <span>{t.emoji}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Formulaire */}
      <div style={{ padding: '16px 20px' }}>
        <textarea
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Décris l'opération (ou dicte-la)..."
          rows={3}
          style={{
            width: '100%',
            padding: 12,
            backgroundColor: '#0F172A',
            border: '1px solid #334155',
            borderRadius: 10,
            color: '#F8FAFC',
            fontSize: 14,
            resize: 'none',
            marginBottom: 10,
          }}
        />
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <input
            value={montant}
            onChange={(e) => setMontant(e.target.value)}
            placeholder="Montant (€) optionnel"
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
          <button
            onClick={() => {}}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '10px 14px',
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
        </div>
        <button
          onClick={handleSubmit}
          disabled={saving || !textInput.trim()}
          style={{
            width: '100%',
            padding: 14,
            backgroundColor: saving ? '#475569' : '#FF6B35',
            border: 'none',
            borderRadius: 10,
            color: '#FFFFFF',
            fontSize: 15,
            fontWeight: 600,
            cursor: saving ? 'not-allowed' : 'pointer',
            opacity: saving ? 0.6 : 1,
          }}
        >
          {saving ? 'Envoi...' : `📸 Signaler ${OPERATION_TYPES.find(t => t.id === selectedType)?.emoji}`}
        </button>
      </div>

      {/* Liste des opérations récentes */}
      <div style={{ padding: '0 20px' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#94A3B8', marginBottom: 8 }}>
          Opérations récentes
        </h3>
        {loading ? (
          <div style={{ color: '#64748B', fontSize: 13 }}>Chargement...</div>
        ) : operations.length === 0 ? (
          <div style={{ color: '#64748B', fontSize: 13 }}>Aucune opération pour l'instant.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {operations.map((op: any) => (
              <div
                key={op.id}
                style={{
                  padding: '10px 12px',
                  backgroundColor: '#1E293B',
                  borderRadius: 8,
                  border: '1px solid #334155',
                  fontSize: 13,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#F8FAFC', fontWeight: 500 }}>
                    {OPERATION_TYPES.find(t => t.id === op.type)?.emoji} {op.type}
                  </span>
                  <span style={{
                    color: op.statut === 'en_attente' ? '#F59E0B' : op.statut === 'valide' ? '#22C55E' : '#EF4444',
                    fontSize: 11,
                    fontWeight: 500,
                  }}>
                    {op.statut}
                  </span>
                </div>
                <div style={{ color: '#94A3B8', marginTop: 2 }}>
                  {op.description?.substring(0, 80)}
                  {op.description?.length > 80 ? '...' : ''}
                </div>
                {op.montant && (
                  <div style={{ color: '#64748B', fontSize: 12, marginTop: 2 }}>
                    {op.montant}€ · {op.date?.substring(0, 10)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <BottomTabs />
    </div>
  );
}
