'use client';

import { useState, useEffect } from 'react';
import { ChantierHeader } from './components/ChantierHeader';
import { ProgressBar } from './components/ProgressBar';
import { MainMenu } from './components/MainMenu';
import { BottomTabs } from './components/BottomTabs';
import { FeedItem } from './components/FeedItem';
import { useTma } from './providers';
import { tmaFetch, initTmaFetch } from './components/tmaFetch';

export default function TmaHomePage() {
  const { isReady, chantier, jwt, org, correlationId } = useTma();
  const [recentOps, setRecentOps] = useState<any[]>([]);

  useEffect(() => {
    if (jwt && org?.id && correlationId) {
      initTmaFetch(jwt, org.id, correlationId);
    }
  }, [jwt, org, correlationId]);

  useEffect(() => {
    if (!isReady || !chantier || !jwt) return;
    (async () => {
      const res = await tmaFetch(`/api/v1/chantiers/${chantier.id}/operations`);
      if (res.ok) {
        const data = await res.json();
        setRecentOps((data.data || data || []).slice(0, 3));
      }
    })();
  }, [isReady, chantier, jwt]);

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
        {recentOps.map((op: any) => (
          <FeedItem
            key={op.id}
            emoji="📸"
            label={`Opération: ${op.type}`}
            description={op.description?.substring(0, 60) || ''}
            time={op.date?.substring(0, 10)}
            href="/mini-app/operations"
          />
        ))}
        {recentOps.length === 0 && (
          <FeedItem
            emoji="👋"
            label="Bienvenue"
            description="Aucune activité récente. Utilise les boutons ci-dessus pour commencer."
          />
        )}
      </div>

      <BottomTabs />
    </div>
  );
}
