'use client';

interface ModalConfirmProps {
  visible: boolean;
  title: string;
  children: React.ReactNode;
  onConfirm: () => void;
  onCancel: () => void;
  saving?: boolean;
  confirmLabel?: string;
}

export function ModalConfirm({ visible, title, children, onConfirm, onCancel, saving, confirmLabel }: ModalConfirmProps) {
  if (!visible) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        zIndex: 100,
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'center',
        backgroundColor: 'rgba(0,0,0,0.6)',
        padding: 20,
      }}
      onClick={onCancel}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: 400,
          backgroundColor: '#1E293B',
          borderRadius: 16,
          border: '1px solid #334155',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #334155',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{ fontSize: 18 }}>📎</span>
          <span style={{ fontSize: 15, fontWeight: 600, color: '#FF6B35' }}>{title}</span>
        </div>

        {/* Content */}
        <div style={{ padding: '16px 20px' }}>
          {children}
        </div>

        {/* Actions */}
        <div style={{
          display: 'flex',
          gap: 10,
          padding: '12px 20px 20px',
        }}>
          <button
            onClick={onCancel}
            disabled={saving}
            style={{
              flex: 1,
              padding: '14px 0',
              backgroundColor: '#334155',
              border: 'none',
              borderRadius: 10,
              color: '#94A3B8',
              fontSize: 15,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            ❌ Annuler
          </button>
          <button
            onClick={onConfirm}
            disabled={saving}
            style={{
              flex: 1,
              padding: '14px 0',
              backgroundColor: saving ? '#475569' : '#22C55E',
              border: 'none',
              borderRadius: 10,
              color: '#FFF',
              fontSize: 15,
              fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? '⏳' : confirmLabel || '✅ Envoyer'}
          </button>
        </div>
      </div>
    </div>
  );
}
