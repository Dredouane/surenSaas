'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import { tmaFetch } from './tmaFetch';

type RecorderState = 'idle' | 'recording' | 'confirm' | 'loading';

interface VoiceRecorderProps {
  onTranscript: (text: string) => void;
  onStructured?: (data: { task_id: string; percentage: number; status: string; observation: string }) => void;
  onError?: (error: string) => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function VoiceRecorder({ onTranscript, onError }: VoiceRecorderProps) {
  const [state, setState] = useState<RecorderState>('idle');
  const [elapsed, setElapsed] = useState(0);
  const [blocked, setBlocked] = useState(false);

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef(0);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    setElapsed(0);
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 200);
  }, []);

  const startRecording = useCallback(async () => {
    if (state !== 'idle') return;
    chunksRef.current = [];
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = s;
    } catch {
      setBlocked(true);
      onError?.('Microphone bloqué. Utilise le bot Telegram pour envoyer un vocal.');
      return;
    }
    if (!streamRef.current) return;

    const recorder = new MediaRecorder(streamRef.current, { mimeType: 'audio/webm' });
    recorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      clearTimer();
      setState('confirm');
    };

    recorder.onerror = () => {
      clearTimer();
      setState('idle');
      onError?.('Erreur enregistrement audio');
    };

    recorder.start(250);
    startTimer();
    setState('recording');
  }, [state, clearTimer, startTimer, onError]);

  const stopRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  const sendRecording = useCallback(async () => {
    const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
    if (blob.size < 200) {
      setState('idle');
      return;
    }

    setState('loading');
    try {
      const formData = new FormData();
      formData.append('audio', blob, 'voice.webm');

      const res = await tmaFetch('/api/v1/tma/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        if (data.is_valid && data.text) {
          onTranscript(data.text);

          // Appel optionnel au pipeline Whisper + Gemini pour la structuration
          if (onStructured) {
            try {
              const structRes = await tmaFetch('/api/v1/tma/transcribe-and-structure', {
                method: 'POST',
                body: formData,
              });
              if (structRes.ok) {
                const structData = await structRes.json();
                if (structData.is_valid && structData.structured) {
                  onStructured(structData.structured);
                }
              }
            } catch {
              // Échec structuration non bloquant
            }
          }
        } else {
          onError?.(data.error || 'Échec transcription');
        }
      } else {
        onError?.('Erreur serveur transcription');
      }
    } catch {
      onError?.('Erreur réseau transcription');
    } finally {
      setState('idle');
    }
  }, [onTranscript, onStructured, onError]);

  const cancelRecording = useCallback(() => {
    chunksRef.current = [];
    setState('idle');
  }, []);

  // Nettoyage au démontage
  useEffect(() => {
    return () => {
      clearTimer();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, [clearTimer]);

  if (blocked) return null;

  if (state === 'loading') {
    return (
      <button
        disabled
        style={{
          padding: '12px',
          backgroundColor: '#475569',
          border: '1px solid #475569',
          borderRadius: 10,
          color: '#94A3B8',
          fontSize: 18,
          cursor: 'not-allowed',
          minWidth: 44,
        }}
      >
        ⏳
      </button>
    );
  }

  if (state === 'confirm') {
    return (
      <div style={{ display: 'flex', gap: 6 }}>
        <button
          onClick={sendRecording}
          title="Envoyer"
          style={{
            padding: '12px 14px',
            backgroundColor: '#22C55E',
            border: 'none',
            borderRadius: 10,
            color: '#FFF',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
            minWidth: 44,
          }}
        >
          ✅ Envoyer
        </button>
        <button
          onClick={cancelRecording}
          title="Annuler"
          style={{
            padding: '12px 14px',
            backgroundColor: '#EF4444',
            border: 'none',
            borderRadius: 10,
            color: '#FFF',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
            minWidth: 44,
          }}
        >
          ❌ Annuler
        </button>
      </div>
    );
  }

  if (state === 'recording') {
    return (
      <button
        onMouseUp={stopRecording}
        onMouseLeave={stopRecording}
        onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
        title="Relâche pour arrêter"
        style={{
          padding: '12px',
          backgroundColor: '#DC2626',
          border: '1px solid #DC2626',
          borderRadius: 10,
          color: '#FFF',
          fontSize: 14,
          fontWeight: 600,
          cursor: 'pointer',
          minWidth: 44,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          animation: 'pulse 1s ease-in-out infinite',
        }}
      >
        <span>🔴</span>
        <span>{formatTime(elapsed)}</span>
        <style>{`@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.7; } }`}</style>
      </button>
    );
  }

  return (
    <button
      onMouseDown={startRecording}
      onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
      title="Appui long pour enregistrer"
      style={{
        padding: '12px',
        backgroundColor: '#1E293B',
        border: '1px solid #334155',
        borderRadius: 10,
        color: '#94A3B8',
        fontSize: 18,
        cursor: 'pointer',
        minWidth: 44,
        transition: 'background-color 0.1s',
      }}
    >
      🎤
    </button>
  );
}
