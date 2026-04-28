'use client';

import { useEffect, useState } from 'react';

const BOT_USERNAME = 'suren_construction_test_bot';

export function TelegramBackend() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100dvh',
        backgroundColor: '#0F172A',
        color: '#94A3B8',
      }}>
        Chargement...
      </div>
    );
  }

  const botUrl = `https://t.me/${BOT_USERNAME}`;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100dvh',
        backgroundColor: '#0F172A',
        color: '#F8FAFC',
        padding: 24,
        textAlign: 'center',
        gap: 24,
      }}
    >
      <div style={{ fontSize: 64, lineHeight: 1 }}>📱</div>
      <h1 style={{
        fontSize: 22,
        fontWeight: 600,
        margin: 0,
        color: '#F8FAFC',
      }}>
        Ouvrez cette application depuis Telegram
      </h1>
      <p style={{
        fontSize: 15,
        color: '#94A3B8',
        margin: 0,
        maxWidth: 320,
        lineHeight: 1.5,
      }}>
        L&apos;application de terrain SurenSaaS est conçue pour fonctionner
        dans le WebView Telegram. Veuillez utiliser le bot ci-dessous pour y accéder.
      </p>
      <a
        href={botUrl}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '14px 32px',
          backgroundColor: '#FF6B35',
          color: '#FFFFFF',
          borderRadius: 12,
          fontSize: 16,
          fontWeight: 600,
          textDecoration: 'none',
          minHeight: 48,
          transition: 'transform 0.1s ease',
        }}
        target="_blank"
        rel="noopener noreferrer"
      >
        Ouvrir dans Telegram
      </a>
      <p style={{
        fontSize: 13,
        color: '#64748B',
        margin: 0,
      }}>
        Pas encore de compte ? Contactez votre gérant pour obtenir une invitation.
      </p>
    </div>
  );
}
