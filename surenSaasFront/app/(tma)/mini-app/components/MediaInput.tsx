'use client';

import { useRef, useCallback, useState, useEffect } from 'react';
import { VoiceRecorder } from './VoiceRecorder';
import { tmaFetch } from './tmaFetch';

interface MediaInputProps {
  workflow: string;
  onResult: (data: any, inputText?: string) => void;
  onError?: (error: string) => void;
  placeholder?: string;
}

export function MediaInput({ workflow, onResult, onError, placeholder }: MediaInputProps) {
  const [textInput, setTextInput] = useState('');
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);

  const processInput = useCallback(async (formData: FormData) => {
    setSaving(true);
    try {
      const res = await tmaFetch('/api/v1/tma/process', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.is_valid && data.data) {
          onResult(data.data, textInput);
        } else {
          onError?.(data.error || 'Échec extraction');
        }
      } else {
        onError?.('Erreur serveur');
      }
    } catch {
      onError?.('Erreur réseau');
    } finally {
      setSaving(false);
    }
  }, [textInput, onResult, onError]);

  const handleTextExtract = useCallback(async () => {
    if (!textInput.trim()) return;
    const fd = new FormData();
    fd.append('text', textInput);
    fd.append('workflow', workflow);
    await processInput(fd);
  }, [textInput, workflow, processInput]);

  const [cameraBlocked, setCameraBlocked] = useState(false);

  const handleFileProcess = useCallback(async (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('workflow', workflow);
    await processInput(fd);
  }, [workflow, processInput]);

  const tryCameraPermission = useCallback(async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      stream.getTracks().forEach((t) => t.stop());
      return true;
    } catch (err: any) {
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        setCameraBlocked(true);
      }
      return false;
    }
  }, []);

  const handlePhotoClick = useCallback(async () => {
    let stream: MediaStream | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    } catch (err: any) {
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        setCameraBlocked(true);
      }
      photoInputRef.current?.click();
      return;
    }

    // Permission accordée : créer une video invisible, capturer une frame
    const video = document.createElement('video');
    video.srcObject = stream;
    video.setAttribute('playsinline', '');
    video.style.position = 'fixed';
    video.style.top = '-9999px';
    video.style.left = '-9999px';
    video.style.width = '1px';
    video.style.height = '1px';
    document.body.appendChild(video);

    await video.play();

    // Attendre un frame pour que la caméra s'initialise
    await new Promise((resolve) => { video.onloadeddata = resolve; setTimeout(resolve, 300); });

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1920;
    canvas.height = video.videoHeight || 1080;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(async (blob) => {
        if (blob) {
          const file = new File([blob], 'photo.jpg', { type: 'image/jpeg' });
          await handleFileProcess(file);
        }
      }, 'image/jpeg', 0.9);
    }

    // Nettoyage
    stream.getTracks().forEach((t) => t.stop());
    document.body.removeChild(video);
  }, [handleFileProcess]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <div style={{ flex: 1, display: 'flex', gap: 4 }}>
          <input value={textInput} onChange={(e) => setTextInput(e.target.value)}
            placeholder={placeholder || 'Décris...'}
            onKeyDown={(e) => e.key === 'Enter' && handleTextExtract()}
            style={{
              flex: 1, padding: '12px 14px', backgroundColor: '#0F172A',
              border: '1px solid #334155', borderRadius: 10, color: '#F8FAFC', fontSize: 14,
            }}
          />
          <VoiceRecorder workflow={workflow} onResult={onResult} onError={onError} />
        </div>
        <button onClick={handleTextExtract} disabled={saving || !textInput.trim()}
          style={{
            padding: '12px 18px', backgroundColor: '#FF6B35',
            border: 'none', borderRadius: 10, color: '#FFF',
            fontSize: 14, fontWeight: 600, minWidth: 60,
            cursor: saving || !textInput.trim() ? 'not-allowed' : 'pointer',
            opacity: saving || !textInput.trim() ? 0.7 : 1,
            animation: saving ? 'pulse 0.8s ease-in-out infinite' : 'none',
          }}
        >{saving ? '⏳' : '📎 IA'}
        <style>{`@keyframes pulse { 0%,100% { opacity: 0.7; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.97); } }`}</style>
        </button>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={handlePhotoClick}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: 8, color: '#94A3B8', fontSize: 13, cursor: 'pointer' }}>
          📸 Prendre une photo
        </button>
        <button onClick={() => fileInputRef.current?.click()}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: 8, color: '#94A3B8', fontSize: 13, cursor: 'pointer' }}>
          📄 Joindre un PDF
        </button>
      </div>
      {cameraBlocked && (
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <span style={{ fontSize: 11, color: '#EF4444' }}>Appareil photo bloqué</span>
          <a href="https://t.me/settings" target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, color: '#FF6B35', textDecoration: 'underline' }}>
            Ouvrir les réglages Telegram
          </a>
        </div>
      )}
      {!cameraBlocked && (
        <div style={{ fontSize: 11, color: '#475569', marginTop: 4 }}>
          Appareil photo prêt. La photo sera capturée automatiquement après autorisation.
        </div>
      )}

      <input ref={photoInputRef} type="file" accept="image/*" capture="environment" style={{ display: 'none' }}
        onChange={async (e) => { const f = e.target?.files?.[0]; if (f) { await handleFileProcess(f); } e.target.value = ''; }} />
      <input ref={fileInputRef} type="file" accept=".pdf,image/*" style={{ display: 'none' }}
        onChange={async (e) => { const f = e.target?.files?.[0]; if (f) { await handleFileProcess(f); } e.target.value = ''; }} />
    </div>
  );
}
