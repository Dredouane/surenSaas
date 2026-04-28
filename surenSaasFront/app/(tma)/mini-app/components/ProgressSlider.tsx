'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

interface ProgressSliderProps {
  value: number;
  onChange: (value: number) => void;
  label?: string;
}

export function ProgressSlider({ value, onChange, label }: ProgressSliderProps) {
  const [dragging, setDragging] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);

  const updateValue = useCallback((clientX: number) => {
    const track = trackRef.current;
    if (!track) return;
    const rect = track.getBoundingClientRect();
    const pct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
    onChange(Math.round(pct));
  }, [onChange]);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    setDragging(true);
    e.preventDefault();
    updateValue(e.clientX);
  }, [updateValue]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (dragging) updateValue(e.clientX);
  }, [dragging, updateValue]);

  const handlePointerUp = useCallback(() => {
    setDragging(false);
  }, []);

  useEffect(() => {
    if (dragging) {
      window.addEventListener('pointerup', handlePointerUp);
      window.addEventListener('pointercancel', handlePointerUp);
    }
    return () => {
      window.removeEventListener('pointerup', handlePointerUp);
      window.removeEventListener('pointercancel', handlePointerUp);
    };
  }, [dragging, handlePointerUp]);

  return (
    <div style={{ width: '100%', userSelect: 'none', touchAction: 'none' }}>
      {label && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 13, color: '#94A3B8' }}>{label}</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#FF6B35' }}>{value}%</span>
        </div>
      )}
      <div
        ref={trackRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        style={{
          position: 'relative',
          height: 32,
          backgroundColor: '#334155',
          borderRadius: 16,
          cursor: 'pointer',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: '100%',
            width: `${value}%`,
            backgroundColor: value >= 100 ? '#22C55E' : '#FF6B35',
            borderRadius: 16,
            transition: dragging ? 'none' : 'width 0.1s ease',
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: `calc(${value}% - 14px)`,
            transform: 'translateY(-50%)',
            width: 28,
            height: 28,
            backgroundColor: '#F8FAFC',
            borderRadius: '50%',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            transition: dragging ? 'none' : 'left 0.1s ease',
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: 12,
            fontWeight: 700,
            color: value > 50 ? '#FFFFFF' : '#F8FAFC',
            pointerEvents: 'none',
            zIndex: 1,
          }}
        >
          {value}%
        </div>
      </div>
    </div>
  );
}
