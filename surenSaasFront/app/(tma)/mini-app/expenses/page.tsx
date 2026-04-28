'use client';

import { useState, useEffect, useCallback } from 'react';
import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { useTma } from '../providers';

const CATEGORIES = [
  { id: 'sous_traitant', label: 'Sous-traitant', emoji: '🔧' },
  { id: 'fournisseur', label: 'Fournisseur', emoji: '📦' },
  { id: 'autre', label: 'Autre', emoji: '📝' },
] as const;

export default function ExpensesPage() {
  const { isReady, chantier, jwt } = useTma();
  const [categorie, setCategorie] = useState('fournisseur');
  const [fournisseur, setFournisseur] = useState('');
  const [montant, setMontant] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [expenses, setExpenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<'form' | 'scanner'>('form');

  const fetchExpenses = useCallback(async () => {
    if (!chantier || !jwt) return;
    try {
      const res = await fetch(`/api/v1/chantiers/${chantier.id}/depenses?limit=10`, {
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (res.ok) {
        const data = await res.json();
        setExpenses(data.data || data || []);
      }
    } catch (err) {
      console.error('Erreur chargement dépenses:', err);
    } finally {
      setLoading(false);
    }
  }, [chantier, jwt]);

  useEffect(() => { fetchExpenses(); }, [fetchExpenses]);

  const handleSubmit = async () => {
    if (!description.trim() || !chantier || !jwt) return;
    setSaving(true);
    try {
      await fetch(`/api/v1/chantiers/${chantier.id}/depenses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
        body: JSON.stringify({
          fournisseur: fournisseur.trim() || 'Non spécifié',
          montant: parseFloat(montant) || 0,
          categorie,
          description: description.trim(),
          date: new Date().toISOString().split('T')[0],
        }),
      });
      setFournisseur('');
      setMontant('');
      setDescription('');
      await fetchExpenses();
    } catch (err) {
      console.error('Erreur création dépense:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleExtractFromPhoto = async () => {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.capture = 'environment';
    fileInput.onchange = async (e: any) => {
      const file = e.target?.files?.[0];
      if (!file || !jwt) return;
      setSaving(true);
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('workflow', 'depense');
        const res = await fetch('/api/v1/tma/extract', {
          method: 'POST',
          headers: { Authorization: `Bearer ${jwt}` },
          body: formData,
        });
        if (res.ok) {
          const extracted = await res.json();
          if (extracted.fournisseur) setFournisseur(extracted.fournisseur);
          if (extracted.montant) setMontant(String(extracted.montant));
          if (extracted.description) setDescription(extracted.description);
          if (extracted.categorie) setCategorie(extracted.categorie);
          setMode('form');
        }
      } catch (err) {
        console.error('Erreur OCR:', err);
      } finally {
        setSaving(false);
      }
    };
    fileInput.click();
  };

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 8, padding: '12px 20px', borderBottom: '1px solid #334155' }}>
        <button
          onClick={() => setMode('form')}
          style={{
            flex: 1,
            padding: '10px',
            borderRadius: 8,
            border: '1px solid',
            borderColor: mode === 'form' ? '#FF6B35' : '#334155',
            backgroundColor: mode === 'form' ? 'rgba(255, 107, 53, 0.15)' : 'transparent',
            color: mode === 'form' ? '#FF6B35' : '#94A3B8',
            fontSize: 14,
            fontWeight: mode === 'form' ? 600 : 400,
            cursor: 'pointer',
          }}
        >
          ✏️ Saisie manuelle
        </button>
        <button
          onClick={handleExtractFromPhoto}
          style={{
            flex: 1,
            padding: '10px',
            borderRadius: 8,
            border: '1px solid #334155',
            backgroundColor: mode === 'scanner' ? 'rgba(255, 107, 53, 0.15)' : 'transparent',
            color: '#94A3B8',
            fontSize: 14,
            cursor: 'pointer',
          }}
        >
          📸 Scanner facture
        </button>
      </div>

      {/* Formulaire */}
      <div style={{ padding: '16px 20px' }}>
        {/* Catégorie selector */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategorie(c.id)}
              style={{
                flex: 1,
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid',
                borderColor: categorie === c.id ? '#FF6B35' : '#334155',
                backgroundColor: categorie === c.id ? 'rgba(255, 107, 53, 0.15)' : 'transparent',
                color: categorie === c.id ? '#FF6B35' : '#94A3B8',
                fontSize: 12,
                fontWeight: categorie === c.id ? 600 : 400,
                cursor: 'pointer',
              }}
            >
              {c.emoji} {c.label}
            </button>
          ))}
        </div>

        <input
          value={fournisseur}
          onChange={(e) => setFournisseur(e.target.value)}
          placeholder="Fournisseur"
          style={{
            width: '100%',
            padding: 12,
            backgroundColor: '#0F172A',
            border: '1px solid #334155',
            borderRadius: 8,
            color: '#F8FAFC',
            fontSize: 14,
            marginBottom: 8,
          }}
        />
        <input
          value={montant}
          onChange={(e) => setMontant(e.target.value)}
          placeholder="Montant (€)"
          type="number"
          style={{
            width: '100%',
            padding: 12,
            backgroundColor: '#0F172A',
            border: '1px solid #334155',
            borderRadius: 8,
            color: '#F8FAFC',
            fontSize: 14,
            marginBottom: 8,
          }}
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description de la dépense..."
          rows={2}
          style={{
            width: '100%',
            padding: 12,
            backgroundColor: '#0F172A',
            border: '1px solid #334155',
            borderRadius: 8,
            color: '#F8FAFC',
            fontSize: 14,
            resize: 'none',
            marginBottom: 12,
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={saving || !description.trim()}
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
          {saving ? 'Envoi...' : '💰 Enregistrer la dépense'}
        </button>
      </div>

      {/* Liste des dépenses */}
      <div style={{ padding: '0 20px' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#94A3B8', marginBottom: 8 }}>
          Dépenses récentes
        </h3>
        {loading ? (
          <div style={{ color: '#64748B', fontSize: 13 }}>Chargement...</div>
        ) : expenses.length === 0 ? (
          <div style={{ color: '#64748B', fontSize: 13 }}>Aucune dépense pour l'instant.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {expenses.map((e: any) => (
              <div
                key={e.id}
                style={{
                  padding: '10px 12px',
                  backgroundColor: '#1E293B',
                  borderRadius: 8,
                  border: '1px solid #334155',
                  fontSize: 13,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#F8FAFC', fontWeight: 500 }}>{e.fournisseur}</span>
                  <span style={{ color: '#FF6B35', fontWeight: 600 }}>{e.montant?.toLocaleString('fr-FR')}€</span>
                </div>
                <div style={{ color: '#94A3B8', marginTop: 2 }}>
                  {e.description?.substring(0, 60)}
                </div>
                <div style={{ color: '#64748B', fontSize: 12, marginTop: 2 }}>
                  {e.categorie} · {e.date?.substring(0, 10)}
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
