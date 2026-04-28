'use client';

import { useRouter } from 'next/navigation';

interface ActionCardProps {
  emoji: string;
  label: string;
  href: string;
  color?: string;
}

export function ActionCard({ emoji, label, href, color = '#FF6B35' }: ActionCardProps) {
  const router = useRouter();

  return (
    <button
      onClick={() => router.push(href)}
      className="tma-touch"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        padding: 20,
        backgroundColor: '#1E293B',
        border: '1px solid #334155',
        borderRadius: 12,
        cursor: 'pointer',
        width: '100%',
        aspectRatio: '1 / 1',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
      <span style={{ fontSize: 32, lineHeight: 1 }}>{emoji}</span>
      <span style={{ fontSize: 13, fontWeight: 500, color: '#F8FAFC', textAlign: 'center' }}>
        {label}
      </span>
    </button>
  );
}
