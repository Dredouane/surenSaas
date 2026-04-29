'use client';

import { useRef, useState, useCallback, useEffect } from 'react';

interface CameraCaptureProps {
  onCapture: (files: File[]) => void;
  onClose: () => void;
}

export function CameraCapture({ onCapture, onClose }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [preview, setPreview] = useState<string | null>(null);
  const [photos, setPhotos] = useState<string[]>([]);
  const filesRef = useRef<File[]>([]);
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

  const addSnapshot = useCallback((dataUrl: string) => {
    setPhotos((prev) => [...prev, dataUrl]);
    setPreview(null);
    videoRef.current?.play();
  }, []);

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

  const confirmSnapshot = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
        filesRef.current.push(file);
        const url = canvas.toDataURL('image/jpeg', 0.7);
        addSnapshot(url);
      }
    }, 'image/jpeg', 0.92);
  }, [addSnapshot]);

  const retake = useCallback(() => {
    setPreview(null);
    videoRef.current?.play();
  }, []);

  const sendAll = useCallback(() => {
    if (doneRef.current || filesRef.current.length === 0) return;
    doneRef.current = true;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    onCapture(filesRef.current);
  }, [onCapture]);

  const removePhoto = useCallback((idx: number) => {
    setPhotos((prev) => prev.filter((_, i) => i !== idx));
    filesRef.current = filesRef.current.filter((_, i) => i !== idx);
  }, []);

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 200, backgroundColor: '#000', display: 'flex', flexDirection: 'column',
    }}>
      {/* Preview vidéo ou snapshot */}
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

      {/* Actions */}
      {error ? (
        <div style={{ padding: 20, textAlign: 'center' }}>
          <div style={{ color: '#EF4444', marginBottom: 12 }}>{error}</div>
          <button onClick={onClose} style={{ padding: '10px 24px', backgroundColor: '#FF6B35', border: 'none', borderRadius: 8, color: '#FFF', fontSize: 14, cursor: 'pointer' }}>Fermer</button>
        </div>
      ) : preview ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 24, padding: '16px', paddingBottom: 'calc(16px + env(safe-area-inset-bottom, 0px))', backgroundColor: '#0F172A' }}>
          <button onClick={retake}
            style={{ padding: '14px 20px', backgroundColor: '#334155', border: 'none', borderRadius: 12, color: '#94A3B8', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>
            🔄 Refaire
          </button>
          <button onClick={confirmSnapshot}
            style={{ padding: '14px 28px', backgroundColor: '#22C55E', border: 'none', borderRadius: 12, color: '#FFF', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>
            ✅ Ajouter
          </button>
        </div>
      ) : ready ? (
        <div style={{ padding: '12px 16px', paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))', backgroundColor: '#0F172A' }}>
          {/* Miniatures des photos prises */}
          {photos.length > 0 && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 12, overflowX: 'auto', paddingBottom: 4 }}>
              {photos.map((url, i) => (
                <div key={i} style={{ position: 'relative', flexShrink: 0 }}>
                  <img src={url} alt={`Photo ${i + 1}`}
                    style={{ width: 56, height: 56, borderRadius: 8, objectFit: 'cover', border: '1px solid #334155' }} />
                  <button onClick={() => removePhoto(i)}
                    style={{ position: 'absolute', top: -4, right: -4, width: 18, height: 18, borderRadius: '50%', backgroundColor: '#EF4444', border: 'none', color: '#FFF', fontSize: 10, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0 }}>
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
            <button onClick={onClose}
              style={{ padding: '12px 20px', backgroundColor: '#334155', border: 'none', borderRadius: 12, color: '#94A3B8', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>
              ❌ Annuler
            </button>
            <button onClick={shoot}
              style={{ width: 64, height: 64, borderRadius: '50%', backgroundColor: '#FFFFFF', border: '4px solid #FF6B35', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 20px rgba(255,107,53,0.3)' }}>
              <div style={{ width: 48, height: 48, borderRadius: '50%', backgroundColor: '#FF6B35' }} />
            </button>
            {photos.length > 0 && (
              <button onClick={sendAll}
                style={{ padding: '12px 24px', backgroundColor: '#22C55E', border: 'none', borderRadius: 12, color: '#FFF', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>
                ✅ Envoyer ({photos.length})
              </button>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
