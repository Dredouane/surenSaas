'use client';

import { ChantierHeader } from './components/ChantierHeader';
import { ProgressBar } from './components/ProgressBar';
import { MainMenu } from './components/MainMenu';
import { BottomTabs } from './components/BottomTabs';
import { FeedItem } from './components/FeedItem';
import { useTma } from './providers';

export default function TmaHomePage() {
  const { isReady, chantier } = useTma();

  if (!isReady || !chantier) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100dvh',
        color: '#94A3B8',
        fontSize: 16,
        backgroundColor: '#0F172A',
      }}>
        Chargement...
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100dvh', backgroundColor: '#0F172A', paddingBottom: 72 }}>
      <ChantierHeader />
      <ProgressBar />
      <MainMenu />

      <div style={{ padding: '16px 20px' }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: '#94A3B8', marginBottom: 8 }}>
          Dernières activités
        </h2>
        <FeedItem
          emoji="📸"
          label="Opération signalée"
          description="Pose BSO — Bâtiment A, 2e étage"
          time="10:32"
        />
        <FeedItem
          emoji="👷"
          label="Pointage validé"
          description="5 présents, 1 absent"
          time="09:15"
        />
        <FeedItem
          emoji="💰"
          label="Dépense enregistrée"
          description="Fournisseur Batimat — Ciment 25t"
          time="Hier"
        />
      </div>

      <BottomTabs />
    </div>
  );
}
