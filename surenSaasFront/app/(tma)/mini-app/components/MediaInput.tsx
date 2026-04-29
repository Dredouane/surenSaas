'use client';

import { useRef, useCallback, useState, useEffect } from 'react';
import { VoiceRecorder } from './VoiceRecorder';
import { tmaFetch } from './tmaFetch';

interface MediaInputProps {
  value: string;
  onChange: (value: string) => void;
  onExtract: () => void;
  onFileExtracted?: (text: string) => void;
  placeholder?: string;
  saving?: boolean;
  mediaLabel?: string;
}

export function MediaInput({ value, onChange, onExtract, onFileExtracted, placeholder, saving, mediaLabel }: MediaInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const extractGuardRef = useRef(false);

  useEffect(() => {
    if (!extractGuardRef.current) return;
    extractGuardRef.current = false;
    const t = setTimeout(() => onExtract(), 300);
    return () => clearTimeout(t);
  }, [value, onExtract]);

  const uploadAndExtract = useCallback(async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('workflow', 'ocr');
      const res = await tmaFetch('/api/v1/tma/extract-file', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.text) {
          onChange(data.text);
          if (onFileExtracted) {
            setTimeout(() => onFileExtracted(data.text), 200);
          } else {
            setTimeout(() => onExtract(), 400);
          }
          return;
        }
      }
      const label = file.type.startsWith('image/') ? 'Photo' : 'Fichier';
      onChange(`[${label}: ${file.name}]`);
    } catch {
      onChange(`[Erreur: ${file.name}]`);
    }
  }, [onChange, onExtract]);

  const handleVoiceResult = useCallback((text: string) => {
    extractGuardRef.current = true;
    onChange(text);
  }, [onChange]);

  return (
    <div>
      {/* Ligne input + bouton IA */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <div style={{ flex: 1, display: 'flex', gap: 4 }}>
          <input value={value} onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder || 'Décris...'}
            onKeyDown={(e) => e.key === 'Enter' && onExtract()}
            style={{
              flex: 1, padding: '12px 14px', backgroundColor: '#0F172A',
              border: '1px solid #334155', borderRadius: 10, color: '#F8FAFC', fontSize: 14,
            }}
          />
          <VoiceRecorder onTranscript={handleVoiceResult} />
        </div>
        <button onClick={onExtract} disabled={saving || !value.trim()}
          style={{
            padding: '12px 18px', backgroundColor: saving ? '#FF6B35' : '#FF6B35',
            border: 'none', borderRadius: 10, color: '#FFF',
            fontSize: 14, fontWeight: 600, minWidth: 60,
            cursor: saving || !value.trim() ? 'not-allowed' : 'pointer',
            opacity: saving || !value.trim() ? 0.7 : 1,
            animation: saving ? 'pulse 0.8s ease-in-out infinite' : 'none',
          }}
        >{saving ? '⏳' : '📎 IA'}
        <style>{`@keyframes pulse { 0%,100% { opacity: 0.7; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.97); } }`}</style>
        </button>
      </div>

      {/* Barre d'actions média — grands boutons visibles */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={() => photoInputRef.current?.click()}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '8px 14px', backgroundColor: '#1E293B',
            border: '1px solid #334155', borderRadius: 8,
            color: '#94A3B8', fontSize: 13, cursor: 'pointer',
          }}
        >📸 Galerie</button>
        <button onClick={() => cameraInputRef.current?.click()}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '8px 14px', backgroundColor: '#1E293B',
            border: '1px solid #334155', borderRadius: 8,
            color: '#94A3B8', fontSize: 13, cursor: 'pointer',
          }}
        >📷 Appareil photo</button>
        <button onClick={() => fileInputRef.current?.click()}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '8px 14px', backgroundColor: '#1E293B',
            border: '1px solid #334155', borderRadius: 8,
            color: '#94A3B8', fontSize: 13, cursor: 'pointer',
          }}
        >📄 PDF</button>
      </div>

      {/* Inputs cachés — upload + extraction automatique */}
      <input ref={photoInputRef} type="file" accept="image/*" style={{ display: 'none' }}
        onChange={async (e) => { const f = e.target?.files?.[0]; if (f) { onChange('Analyse en cours...'); await uploadAndExtract(f); } e.target.value = ''; }} />
      <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" style={{ display: 'none' }}
        onChange={async (e) => { const f = e.target?.files?.[0]; if (f) { onChange('Analyse en cours...'); await uploadAndExtract(f); } e.target.value = ''; }} />
      <input ref={fileInputRef} type="file" accept=".pdf,image/*" style={{ display: 'none' }}
        onChange={async (e) => { const f = e.target?.files?.[0]; if (f) { onChange('Analyse en cours...'); await uploadAndExtract(f); } e.target.value = ''; }} />
    </div>
  );
}
