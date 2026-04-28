'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useTma } from '../providers';

const TABS = [
  { emoji: '📊', label: 'Chantier', href: '/mini-app' },
  { emoji: '📈', label: 'Progression', href: '/mini-app/progress' },
  { emoji: '💰', label: 'Dépenses', href: '/mini-app/expenses' },
  { emoji: '👷', label: 'Équipe', href: '/mini-app/attendance' },
] as const;

export function BottomTabs() {
  const pathname = usePathname();
  const router = useRouter();
  const { isReady } = useTma();

  if (!isReady) return null;

  const isActive = (href: string) => {
    if (href === '/mini-app') return pathname === '/mini-app';
    return pathname.startsWith(href);
  };

  return (
    <nav
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        display: 'flex',
        backgroundColor: '#1E293B',
        borderTop: '1px solid #334155',
        paddingBottom: 'env(safe-area-inset-bottom, 4px)',
      }}
    >
      {TABS.map((tab) => {
        const active = isActive(tab.href);
        return (
          <button
            key={tab.href}
            onClick={() => router.push(tab.href)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 2,
              padding: '8px 4px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              WebkitTapHighlightColor: 'transparent',
              opacity: active ? 1 : 0.5,
              transition: 'opacity 0.15s',
            }}
          >
            <span style={{ fontSize: 22, lineHeight: 1 }}>{tab.emoji}</span>
            <span style={{
              fontSize: 10,
              fontWeight: active ? 600 : 400,
              color: active ? '#FF6B35' : '#94A3B8',
            }}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
