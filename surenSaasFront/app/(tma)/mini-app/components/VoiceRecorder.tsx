'use client';

import { useRef, useState, useCallback } from 'react';
import { tmaFetch } from './tmaFetch';

interface VoiceRecorderProps {
  onTranscript: (text: string) => void;
  onError?: (error: string) => void;
}

export function VoiceRecorder({ onTranscript, onError }: VoiceRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    if (recording) return;
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setRecording(false);

        if (blob.size < 200) return;

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
            } else {
              onError?.(data.error || 'Échec transcription');
            }
          } else {
            onError?.('Erreur serveur transcription');
          }
        } catch (err) {
          onError?.('Erreur réseau transcription');
        }
      };

      recorder.onerror = () => {
        setRecording(false);
        stream.getTracks().forEach((t) => t.stop());
        onError?.('Erreur enregistrement audio');
      };

      recorder.start(250);
      setRecording(true);
    } catch (err: any) {
      setBlocked(true);
      const msg = err?.name === 'NotAllowedError'
        ? 'Microphone bloqué. Utilise le bot Telegram pour envoyer un vocal.'
        : 'Microphone indisponible. Utilise le bot Telegram pour envoyer un vocal.';
      onError?.(msg);
    }
  }, [recording, onTranscript, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  if (blocked) return null;

  return (
    <button
      onMouseDown={startRecording}
      onMouseUp={stopRecording}
      onMouseLeave={recording ? stopRecording : undefined}
      onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
      onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
      title={recording ? 'Relâche pour envoyer' : 'Appui long pour enregistrer'}
      style={{
        padding: '12px',
        backgroundColor: recording ? '#22C55E' : '#1E293B',
        border: '1px solid #334155',
        borderRadius: 10,
        color: recording ? '#FFF' : '#94A3B8',
        fontSize: 18,
        cursor: 'pointer',
        minWidth: 44,
        transition: 'background-color 0.1s',
      }}
    >
      {recording ? '🔴' : '🎤'}
    </button>
  );
}
