'use client';

import './globals-tma.css';
import { TelegramWebAppProvider } from './providers';
import { Suspense } from 'react';

export default function TmaLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="dark">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
        <meta name="theme-color" content="#0F172A" />
        <script
          src="https://telegram.org/js/telegram-web-app.js"
          async
        />
      </head>
      <body style={{ margin: 0, padding: 0, backgroundColor: '#0F172A', color: '#F8FAFC' }}>
        <TelegramWebAppProvider>
          <Suspense fallback={
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100dvh',
              color: '#94A3B8',
              fontSize: 16,
            }}>
              Chargement...
            </div>
          }>
            {children}
          </Suspense>
        </TelegramWebAppProvider>
      </body>
    </html>
  );
}
