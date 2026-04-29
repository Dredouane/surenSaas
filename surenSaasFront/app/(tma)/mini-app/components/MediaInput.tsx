'use client';

import { useRef, useState } from 'react';

interface MediaInputProps {
  value: string;
  onChange: (value: string) => void;
  onExtract: () => void;
  placeholder?: string;
  saving?: boolean;
}

export function MediaInput({ value, onChange, onExtract, placeholder, saving }: MediaInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [recording, setRecording] = useState(false);

  const handlePhoto = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    input.onchange = (e: any) => {
      const file = e.target?.files?.[0];
      if (file) {
        onChange(`[Photo: ${file.name}] ${value}`);
        onExtract();
      }
    };
    input.click();
  };

  const handleFile = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,image/*';
    input.onchange = (e: any) => {
      const file = e.target?.files?.[0];
      if (file) {
        onChange(`[Fichier: ${file.name}] ${value}`);
        onExtract();
      }
    };
    input.click();
  };

  const handleVoice = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      onChange(value + ' (dictée non supportée sur ce navigateur)');
      return;
    }
    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.interimResults = false;
    recognition.continuous = false;

    setRecording(true);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      onChange(transcript);
      setRecording(false);
      setTimeout(() => onExtract(), 100);
    };
    recognition.onerror = () => setRecording(false);
    recognition.onend = () => setRecording(false);
    recognition.start();
  };

  const hasNativeVoice = typeof window !== 'undefined' &&
    (('webkitSpeechRecognition' in window) || ('SpeechRecognition' in window));

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
          <button
            onClick={handleVoice}
            title="Dicter"
            style={{
              padding: '12px',
              backgroundColor: recording ? '#22C55E' : '#1E293B',
              border: '1px solid #334155',
              borderRadius: 10,
              color: recording ? '#FFF' : '#94A3B8',
              fontSize: 18,
              cursor: 'pointer',
            }}
          >
            🎤
          </button>
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
          }}
        >
          {saving ? '...' : '📎 IA'}
        </button>
      </div>
      <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#64748B' }}>
        <span style={{ cursor: 'pointer' }} onClick={handleVoice}>
          🎤 Dictée vocale
        </span>
        <span style={{ cursor: 'pointer' }} onClick={handlePhoto}>
          📸 Photo
        </span>
        <span style={{ cursor: 'pointer' }} onClick={handleFile}>
          📄 PDF
        </span>
      </div>
      <input ref={fileInputRef} type="file" accept="image/*,.pdf" style={{ display: 'none' }} />
    </div>
  );
}
