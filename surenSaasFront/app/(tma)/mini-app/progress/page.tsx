'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { SituationCard } from '../components/SituationCard';
import { useTma } from '../providers';

interface Situation {
  id: string;
  numero: number;
  libelle: string;
  montant: number;
  lignes?: {
    description: string;
    quantite: number;
    unite?: string;
    prix_unitaire: number;
    avancement_pourcentage: number;
    montant_total?: number;
    photo_url?: string;
  }[];
}

export default function ProgressPage() {
  const { isReady, chantier, jwt } = useTma();
  const [situations, setSituations] = useState<Situation[]>([]);
  const [textInput, setTextInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchSituations = useCallback(async () => {
    if (!chantier || !jwt) return;
    try {
      const res = await fetch(`/api/v1/chantiers/${chantier.id}/situations?statut=ouverte`, {
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (res.ok) {
        const data = await res.json();
        const items = (data.data || data || []).map((s: any) => ({
          id: s.id,
          numero: s.numero,
          libelle: s.libelle,
          montant: s.montant,
          lignes: [],
        }));
        setSituations(items);
      }
    } catch (err) {
      console.error('Erreur chargement situations:', err);
    } finally {
      setLoading(false);
    }
  }, [chantier, jwt]);

  useEffect(() => {
    fetchSituations();
  }, [fetchSituations]);

  const handleExtractText = async () => {
    if (!textInput.trim()) return;
    setSaving(true);
    try {
      const res = await fetch('/api/v1/tma/extract', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${jwt}`,
        },
        body: JSON.stringify({
          text: textInput,
          workflow: 'avancement',
        }),
      });
      if (res.ok) {
        const extracted = await res.json();
        if (situations.length > 0) {
          const firstSit = situations[0];
          const qte = extracted.quantite || 0;
          const pu = extracted.prix_unitaire || 0;
          const pct = extracted.avancement_pourcentage || 0;
          const ligne = {
            description: extracted.description || textInput,
            quantite: qte,
            prix_unitaire: pu,
            avancement_pourcentage: pct,
            montant_total: qte * pu,
          };
          await submitLigne(firstSit.id, ligne);
        }
      }
    } catch (err) {
      console.error('Erreur extraction:', err);
    } finally {
      setSaving(false);
      setTextInput('');
    }
  };

  const submitLigne = async (situationId: string, ligne: any) => {
    if (!chantier || !jwt) return;
    try {
      const res = await fetch(`/api/v1/chantiers/${chantier.id}/situations/${situationId}/lignes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${jwt}`,
        },
        body: JSON.stringify(ligne),
      });
      if (res.ok) {
        setSituations((prev) =>
          prev.map((s) =>
            s.id === situationId
              ? { ...s, lignes: [...(s.lignes || []), ligne] }
              : s
          )
        );
      }
    } catch (err) {
      console.error('Erreur sauvegarde ligne:', err);
    }
  };

  const handleAddLigne = async (situationId: string, ligne: any) => {
    await submitLigne(situationId, ligne);
  };

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />
      <div style={{ padding: '16px 20px' }}>
        {/* Barre de saisie texte + extraction IA */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Décris l'avancement (ex: Enduit façade 50m2 25€/m2 80%)"
              style={{
                flex: 1,
                padding: '12px 14px',
                backgroundColor: '#0F172A',
                border: '1px solid #334155',
                borderRadius: 10,
                color: '#F8FAFC',
                fontSize: 14,
              }}
              onKeyDown={(e) => e.key === 'Enter' && handleExtractText()}
            />
            <button
              onClick={handleExtractText}
              disabled={saving || !textInput.trim()}
              style={{
                padding: '12px 18px',
                backgroundColor: saving ? '#475569' : '#FF6B35',
                border: 'none',
                borderRadius: 10,
                color: '#FFFFFF',
                fontSize: 14,
                fontWeight: 600,
                cursor: saving ? 'not-allowed' : 'pointer',
                opacity: saving ? 0.6 : 1,
              }}
            >
              {saving ? '...' : '📎 IA'}
            </button>
          </div>
          <div style={{ fontSize: 12, color: '#64748B', display: 'flex', gap: 16 }}>
            <span>🎤 Dictée vocale (maintenir)</span>
            <span>📸 Photo</span>
          </div>
        </div>

        {/* Feed des situations */}
        {loading ? (
          <div style={{ color: '#94A3B8', textAlign: 'center', padding: 24 }}>Chargement des situations...</div>
        ) : situations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: '#94A3B8' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📈</div>
            <div style={{ fontSize: 15 }}>Aucune situation ouverte sur ce chantier.</div>
            <div style={{ fontSize: 13, marginTop: 4 }}>Crée une situation depuis l'application web.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {situations.map((s) => (
              <SituationCard key={s.id} situation={s} onAddLigne={handleAddLigne} />
            ))}
          </div>
        )}
      </div>
      <BottomTabs />
    </div>
  );
}
