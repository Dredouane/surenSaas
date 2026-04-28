'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { useTma } from '../providers';
import { tmaFetch } from '../components/tmaFetch';

type RessourceType = 'homme' | 'machine';

interface Ressource {
  id: string;
  nom: string;
  type: RessourceType;
  present: boolean;
  specialite?: string;
}

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

function formatDisplay(date: Date): string {
  const today = new Date();
  const diff = Math.round((today.getTime() - date.getTime()) / 86400000);
  if (diff === 0) return "Aujourd'hui";
  if (diff === 1) return 'Hier';
  if (diff === 2) return 'Avant-hier';
  return date.toLocaleDateString('fr-FR');
}

export default function AttendancePage() {
  const { isReady, chantier } = useTma();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [ressources, setRessources] = useState<Ressource[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [selectedType, setSelectedType] = useState<RessourceType>('homme');

  const fetchRessources = useCallback(async () => {
    if (!chantier) return;
    setLoading(true);
    try {
      const res = await tmaFetch(`/api/v1/chantiers/${chantier.id}/ressources`);
      if (res.ok) {
        const data = await res.json();
        const items = (data.data || data || []).map((r: any) => ({
          id: r.id,
          nom: r.nom,
          type: r.type || 'homme',
          present: true,
          specialite: r.specialite,
        }));
        setRessources(items);
      }
    } catch (err) {
      console.error('Erreur chargement ressources:', err);
    } finally {
      setLoading(false);
    }
  }, [chantier]);

  useEffect(() => { fetchRessources(); }, [fetchRessources]);

  const togglePresence = (id: string) => {
    setRessources((prev) =>
      prev.map((r) => (r.id === id ? { ...r, present: !r.present } : r))
    );
  };

  const handleValidate = async () => {
    if (!chantier) return;
    setSaving(true);
    try {
      const dateStr = formatDate(currentDate);
      const presentes = displayed.filter((r) => r.present);
      const absentes = displayed.filter((r) => !r.present);

      await tmaFetch(`/api/v1/chantiers/${chantier.id}/pointages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: dateStr,
          commentaires: `${presentes.length} présent(s), ${absentes.length} absent(s)`,
        }),
      });

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Erreur validation pointage:', err);
    } finally {
      setSaving(false);
    }
  };

  const changeDate = (delta: number) => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + delta);
    setCurrentDate(d);
    setSaved(false);
  };

  const hommes = ressources.filter((r) => r.type === 'homme');
  const machines = ressources.filter((r) => r.type === 'machine');
  const displayed = selectedType === 'homme' ? hommes : machines;
  const presentCount = displayed.filter((r) => r.present).length;
  const absentCount = displayed.filter((r) => !r.present).length;

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />

      {/* Date selector */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
        padding: '12px 20px',
        borderBottom: '1px solid #334155',
      }}>
        <button
          onClick={() => changeDate(-1)}
          style={{
            padding: '10px 14px',
            backgroundColor: '#1E293B',
            border: '1px solid #334155',
            borderRadius: 8,
            color: '#94A3B8',
            fontSize: 18,
            cursor: 'pointer',
          }}
        >
          ◀
        </button>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>{formatDisplay(currentDate)}</div>
          <div style={{ fontSize: 12, color: '#64748B' }}>{currentDate.toLocaleDateString('fr-FR')}</div>
        </div>
        <button
          onClick={() => changeDate(1)}
          style={{
            padding: '10px 14px',
            backgroundColor: '#1E293B',
            border: '1px solid #334155',
            borderRadius: 8,
            color: '#94A3B8',
            fontSize: 18,
            cursor: 'pointer',
          }}
        >
          ▶
        </button>
      </div>

      {/* Type toggle */}
      <div style={{ display: 'flex', gap: 8, padding: '12px 20px', borderBottom: '1px solid #334155' }}>
        <button
          onClick={() => setSelectedType('homme')}
          style={{
            flex: 1,
            padding: '10px',
            borderRadius: 8,
            border: '1px solid',
            borderColor: selectedType === 'homme' ? '#22C55E' : '#334155',
            backgroundColor: selectedType === 'homme' ? 'rgba(34, 197, 94, 0.15)' : 'transparent',
            color: selectedType === 'homme' ? '#22C55E' : '#94A3B8',
            fontSize: 14,
            fontWeight: selectedType === 'homme' ? 600 : 400,
            cursor: 'pointer',
          }}
        >
          👷 Hommes ({hommes.length})
        </button>
        <button
          onClick={() => setSelectedType('machine')}
          style={{
            flex: 1,
            padding: '10px',
            borderRadius: 8,
            border: '1px solid',
            borderColor: selectedType === 'machine' ? '#3B82F6' : '#334155',
            backgroundColor: selectedType === 'machine' ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
            color: selectedType === 'machine' ? '#3B82F6' : '#94A3B8',
            fontSize: 14,
            fontWeight: selectedType === 'machine' ? 600 : 400,
            cursor: 'pointer',
          }}
        >
          🚜 Machines ({machines.length})
        </button>
      </div>

      {/* Liste ressources */}
      <div style={{ padding: '12px 20px' }}>
        {loading ? (
          <div style={{ color: '#64748B', textAlign: 'center', padding: 20 }}>Chargement...</div>
        ) : displayed.length === 0 ? (
          <div style={{ color: '#64748B', textAlign: 'center', padding: 20 }}>
            Aucune {selectedType === 'homme' ? 'ressource humaine' : 'machine'} sur ce chantier.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {displayed.map((r) => (
              <button
                key={r.id}
                onClick={() => togglePresence(r.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  backgroundColor: '#1E293B',
                  border: '1px solid',
                  borderColor: r.present ? '#22C55E' : '#334155',
                  borderRadius: 10,
                  cursor: 'pointer',
                  WebkitTapHighlightColor: 'transparent',
                  transition: 'border-color 0.15s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 20 }}>{selectedType === 'homme' ? '👷' : '🚜'}</span>
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: 14, fontWeight: 500, color: '#F8FAFC' }}>{r.nom}</div>
                    {r.specialite && (
                      <div style={{ fontSize: 11, color: '#64748B' }}>{r.specialite}</div>
                    )}
                  </div>
                </div>
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    backgroundColor: r.present ? '#22C55E' : '#334155',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 14,
                    color: '#FFFFFF',
                    transition: 'background-color 0.15s',
                  }}
                >
                  {r.present ? '✓' : '✗'}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Résumé */}
      <div style={{ padding: '0 20px', marginBottom: 12 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: '10px 14px',
          backgroundColor: '#1E293B',
          borderRadius: 8,
          fontSize: 13,
        }}>
          <span style={{ color: '#22C55E' }}>✅ Présents: {presentCount}</span>
          <span style={{ color: '#EF4444' }}>❌ Absents: {absentCount}</span>
          <span style={{ color: '#94A3B8' }}>Total: {displayed.length}</span>
        </div>
      </div>

      {/* Bouton valider */}
      <div style={{ padding: '0 20px' }}>
        <button
          onClick={handleValidate}
          disabled={saving}
          style={{
            width: '100%',
            padding: 14,
            backgroundColor: saved ? '#22C55E' : saving ? '#475569' : '#FF6B35',
            border: 'none',
            borderRadius: 10,
            color: '#FFFFFF',
            fontSize: 15,
            fontWeight: 600,
            cursor: saving ? 'not-allowed' : 'pointer',
            opacity: saving ? 0.6 : 1,
          }}
        >
          {saved ? '✅ Pointage enregistré !' : saving ? 'Enregistrement...' : '🚀 Valider le pointage'}
        </button>
      </div>

      <BottomTabs />
    </div>
  );
}
