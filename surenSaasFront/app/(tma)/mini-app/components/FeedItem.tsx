'use client';

interface FeedItemProps {
  emoji: string;
  label: string;
  description: string;
  time?: string;
}

export function FeedItem({ emoji, label, description, time }: FeedItemProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        padding: '10px 0',
        borderBottom: '1px solid #1E293B',
      }}
    >
      <span style={{ fontSize: 20, lineHeight: 1, marginTop: 2 }}>{emoji}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: '#F8FAFC', marginBottom: 2 }}>
          {label}
        </div>
        <div style={{ fontSize: 13, color: '#94A3B8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {description}
        </div>
      </div>
      {time && (
        <span style={{ fontSize: 11, color: '#64748B', whiteSpace: 'nowrap' }}>{time}</span>
      )}
    </div>
  );
}
