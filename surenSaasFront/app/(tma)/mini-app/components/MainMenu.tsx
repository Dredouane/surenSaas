'use client';

import { ActionCard } from './ActionCard';

const MENU_ITEMS = [
  { emoji: '📸', label: 'Opérations', href: '/mini-app/operations', color: '#FF6B35' },
  { emoji: '👷', label: 'Pointage', href: '/mini-app/attendance', color: '#22C55E' },
  { emoji: '💰', label: 'Dépenses', href: '/mini-app/expenses', color: '#3B82F6' },
  { emoji: '📈', label: 'Avancement', href: '/mini-app/progress', color: '#F59E0B' },
  { emoji: '📋', label: 'Tâches', href: '/mini-app/progress', color: '#8B5CF6' },
  { emoji: '📄', label: 'Situations', href: '/mini-app/progress', color: '#EC4899' },
];

export function MainMenu() {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 12,
        padding: '16px 20px',
      }}
    >
      {MENU_ITEMS.map((item) => (
        <ActionCard key={item.href} {...item} />
      ))}
    </div>
  );
}
