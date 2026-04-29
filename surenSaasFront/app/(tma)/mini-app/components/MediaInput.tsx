'use client';

import { useRef, useCallback, useState, useEffect } from 'react';
import { VoiceRecorder } from './VoiceRecorder';

interface MediaInputProps {
  value: string;
  onChange: (value: string) => void;
  onExtract: () => void;
  placeholder?: string;
  saving?: boolean;
}

export function MediaInput({ value, onChange, onExtract, placeholder, saving }: MediaInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);
  const [pendingVoice, setPendingVoice] = useState('');

  useEffect(() => {
    if (pendingVoice && pendingVoice === value) {
      const t = setTimeout(() => onExtract(), 300);
      return () => clearTimeout(t);
    }
  }, [value, pendingVoice, onExtract]);

  const handlePhoto = useCallback(() => {
    photoInputRef.current?.click();
  }, []);

  const handleFile = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
        <div style={{ flex: 1, display: 'flex', gap: 4 }}>
          <input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder || "Saisis ou dicte..."}
            style={{
              flex: 1,
              padding: '12px 14px',
              backgroundColor: '#0F172A',
              border: '1px solid #334155',
              borderRadius: 10,
              color: '#F8FAFC',
              fontSize: 14,
            }}
            onKeyDown={(e) => e.key === 'Enter' && onExtract()}
          />
          <VoiceRecorder
            onTranscript={(text) => { setPendingVoice(text); onChange(text); }}
          />
        </div>
        <button
          onClick={onExtract}
          disabled={saving || !value.trim()}
          style={{
            padding: '12px 18px',
            backgroundColor: saving ? '#475569' : '#FF6B35',
            border: 'none',
            borderRadius: 10,
            color: '#FFF',
            fontSize: 14,
            fontWeight: 600,
            cursor: saving || !value.trim() ? 'not-allowed' : 'pointer',
            opacity: saving || !value.trim() ? 0.6 : 1,
            minWidth: 60,
          }}
        >
          {saving ? '...' : '📎 IA'}
        </button>
      </div>
      <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#64748B' }}>
        <span>🎤 Appui long pour dicter</span>
        <button
          onClick={handlePhoto}
          style={{
            background: 'none',
            border: 'none',
            color: '#64748B',
            fontSize: 12,
            cursor: 'pointer',
            padding: 0,
          }}
        >
          📸 Photo
        </button>
        <button
          onClick={handleFile}
          style={{
            background: 'none',
            border: 'none',
            color: '#64748B',
            fontSize: 12,
            cursor: 'pointer',
            padding: 0,
          }}
        >
          📄 PDF
        </button>
      </div>
      <input
        ref={photoInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target?.files?.[0];
          if (file) {
            onChange(`[Photo: ${file.name}] ${value}`);
            setTimeout(() => onExtract(), 200);
          }
          e.target.value = '';
        }}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,image/*"
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target?.files?.[0];
          if (file) {
            onChange(`[Fichier: ${file.name}] ${value}`);
            setTimeout(() => onExtract(), 200);
          }
          e.target.value = '';
        }}
      />
    </div>
  );
}
