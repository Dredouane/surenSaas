'use client';

import { BottomTabs } from '../components/BottomTabs';
import { ChantierHeader } from '../components/ChantierHeader';
import { useTma } from '../providers';

export default function AttendancePage() {
  const { isReady, chantier } = useTma();

  if (!isReady || !chantier) {
    return <div style={{ padding: 24, color: '#94A3B8' }}>Chargement...</div>;
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />
      <div style={{ padding: '24px 20px', textAlign: 'center', color: '#94A3B8' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>👷</div>
        <h2 style={{ fontSize: 18, fontWeight: 600, color: '#F8FAFC', marginBottom: 8 }}>
          Pointage de l&apos;équipe
        </h2>
        <p style={{ fontSize: 14, lineHeight: 1.5 }}>
          Togglez la présence des ressources (hommes et machines)
          pour la journée, puis validez le pointage.
        </p>
      </div>
      <BottomTabs />
    </div>
  );
}
