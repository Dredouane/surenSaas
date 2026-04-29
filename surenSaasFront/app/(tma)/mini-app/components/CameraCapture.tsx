'use client';

import { useRef, useState, useCallback, useEffect } from 'react';

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  onClose: () => void;
}

export function CameraCapture({ onCapture, onClose }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [preview, setPreview] = useState<string | null>(null);
  const doneRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 3840 }, height: { ideal: 2160 } },
        });
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = s;
        if (videoRef.current) videoRef.current.srcObject = s;
      } catch {
        setError('Impossible d\'accéder à la caméra');
      }
    })();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const handleVideoReady = useCallback(() => setReady(true), []);

  const shoot = useCallback(() => {
    const video = videoRef.current;
    if (!video || doneRef.current || preview) return;
    video.pause();
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = video.videoWidth || 1920;
    canvas.height = video.videoHeight || 1080;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    setPreview(canvas.toDataURL('image/jpeg', 0.92));
  }, [preview]);

  const retake = useCallback(() => {
    setPreview(null);
    videoRef.current?.play();
  }, []);

  const confirm = useCallback(() => {
    if (doneRef.current) return;
    doneRef.current = true;
    const canvas = canvasRef.current;
    if (!canvas) { doneRef.current = false; return; }
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        onCapture(file);
      } else {
        doneRef.current = false;
      }
    }, 'image/jpeg', 0.92);
  }, [onCapture]);

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 200, backgroundColor: '#000', display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {preview ? (
          <img src={preview} alt="Snapshot" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
        ) : (
          <video ref={videoRef} onCanPlay={handleVideoReady}
            onLoadedMetadata={() => videoRef.current?.play()}
            playsInline autoPlay muted
            style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        )}
        <canvas ref={canvasRef} style={{ display: 'none' }} />
        {!ready && !error && !preview && (
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', color: '#FFF', fontSize: 16 }}>
            Activation de la caméra...
          </div>
        )}
      </div>

      {error ? (
        <div style={{ padding: 20, textAlign: 'center' }}>
          <div style={{ color: '#EF4444', marginBottom: 12 }}>{error}</div>
          <button onClick={onClose} style={{ padding: '10px 24px', backgroundColor: '#FF6B35', border: 'none', borderRadius: 8, color: '#FFF', fontSize: 14, cursor: 'pointer' }}>Fermer</button>
        </div>
      ) : preview ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 24, padding: '20px 16px', paddingBottom: 'calc(20px + env(safe-area-inset-bottom, 0px))', backgroundColor: '#0F172A' }}>
          <button onClick={retake}
            style={{ padding: '14px 20px', backgroundColor: '#334155', border: 'none', borderRadius: 12, color: '#94A3B8', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>
            🔄 Refaire
          </button>
          <button onClick={confirm}
            style={{ padding: '14px 28px', backgroundColor: '#22C55E', border: 'none', borderRadius: 12, color: '#FFF', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>
            ✅ Valider
          </button>
        </div>
      ) : ready ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 24, padding: '20px 16px', paddingBottom: 'calc(20px + env(safe-area-inset-bottom, 0px))', backgroundColor: '#0F172A' }}>
          <button onClick={onClose}
            style={{ padding: '14px 20px', backgroundColor: '#334155', border: 'none', borderRadius: 12, color: '#94A3B8', fontSize: 15, fontWeight: 600, cursor: 'pointer', minWidth: 80 }}>
            ❌ Annuler
          </button>
          <button onClick={shoot}
            style={{ width: 72, height: 72, borderRadius: '50%', backgroundColor: '#FFFFFF', border: '4px solid #FF6B35', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 20px rgba(255,107,53,0.3)' }}>
            <div style={{ width: 56, height: 56, borderRadius: '50%', backgroundColor: '#FF6B35' }} />
          </button>
        </div>
      ) : null}
    </div>
  );
}
