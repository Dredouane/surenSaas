'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { TelegramBackend } from './components/TelegramBackend';
import { initTmaFetch } from './components/tmaFetch';

// Types
export interface TmaUser {
  id: string;
  email?: string;
  full_name?: string;
  role: string;
}

export interface TmaChantier {
  id: string;
  ref: string;
  nom: string;
  adresse?: string;
  statut: string;
  montant_revise?: number;
  situations_facturees?: number;
  conducteur?: string;
}

export interface TmaOrg {
  id: string;
  name: string;
  slug: string;
}

export interface TmaContext {
  user: TmaUser | null;
  chantier: TmaChantier | null;
  org: TmaOrg | null;
  correlationId: string;
  jwt: string | null;
  isReady: boolean;
  isWebView: boolean;
  deviceInfo: Record<string, unknown>;
}

const defaultContext: TmaContext = {
  user: null,
  chantier: null,
  org: null,
  correlationId: '',
  jwt: null,
  isReady: false,
  isWebView: false,
  deviceInfo: {},
};

const TmaContext_ = createContext<TmaContext>(defaultContext);

export const useTma = () => useContext(TmaContext_);

function generateCorrelationId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function getDeviceInfo(): Record<string, unknown> {
  if (typeof window !== 'undefined' && (window as any).Telegram?.WebApp) {
    const tg = (window as any).Telegram.WebApp;
    return {
      platform: tg.platform || 'unknown',
      app_version: tg.version || 'unknown',
      connection_type: 'unknown',
    };
  }
  return {
    platform: navigator.platform || 'unknown',
    app_version: 'browser',
    connection_type: 'unknown',
  };
}

function getStartParam(): string | null {
  if (typeof window === 'undefined') return null;

  // Depuis l'URL (fallback browser)
  const urlParams = new URLSearchParams(window.location.search);
  const sp = urlParams.get('start_param') || urlParams.get('tgWebAppStartParam');
  if (sp) return sp;

  // Depuis Telegram WebApp SDK
  try {
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.initDataUnsafe?.start_param) {
      return tg.initDataUnsafe.start_param;
    }
  } catch {
    // ignore
  }

  return null;
}

export function TelegramWebAppProvider({ children }: { children: React.ReactNode }) {
  const [context, setContext] = useState<TmaContext>(defaultContext);
  const [authDone, setAuthDone] = useState(false);
  const [isWebView, setIsWebView] = useState(false);

  const initTelegram = useCallback(() => {
    if (typeof window === 'undefined') return;

    const hasWebApp = !!(window as any).Telegram?.WebApp;
    setIsWebView(hasWebApp);

    if (hasWebApp) {
      try {
        const tg = (window as any).Telegram.WebApp;
        tg.ready();
        tg.expand();

        // Appliquer le thème Telegram
        const colorScheme = tg.colorScheme || 'dark';
        document.documentElement.className = colorScheme;
        if (tg.setHeaderColor) tg.setHeaderColor('bg_color');
        if (tg.setBackgroundColor) tg.setBackgroundColor('bg_color');
      } catch {
        // fallback
      }
    }
  }, []);

  const authenticate = useCallback(async (correlationId: string) => {
    const startParam = getStartParam();
    const deviceInfo = getDeviceInfo();

    try {
      // Init Telegram SDK
      const tg = (window as any).Telegram?.WebApp;
      const initData = tg?.initData || '';

      const response = await fetch('/api/v1/tma/auth', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Correlation-ID': correlationId,
          'X-Device-Info': JSON.stringify(deviceInfo),
        },
        body: JSON.stringify({
          initData,
          start_param: startParam,
        }),
      });

      if (!response.ok) {
        console.warn('TMA Auth failed:', response.status);
        setAuthDone(true);
        return;
      }

      const { token } = await response.json();

      // Récupérer le contexte
      const ctxResponse = await fetch('/api/v1/tma/context', {
        headers: {
          Authorization: `Bearer ${token}`,
          'X-Correlation-ID': correlationId,
        },
      });

      if (!ctxResponse.ok) {
        console.warn('TMA Context failed:', ctxResponse.status);
        setAuthDone(true);
        return;
      }

      const ctx = await ctxResponse.json();

      initTmaFetch(token, ctx.org?.id || '', correlationId);

      setContext({
        user: ctx.user || null,
        chantier: ctx.chantier || null,
        org: ctx.org || null,
        correlationId,
        jwt: token,
        isReady: true,
        isWebView,
        deviceInfo,
      });
    } catch (err) {
      console.error('TMA Auth error:', err);
    } finally {
      setAuthDone(true);
    }
  }, [isWebView]);

  useEffect(() => {
    const correlationId = generateCorrelationId();
    initTelegram();
    authenticate(correlationId);
  }, [initTelegram, authenticate]);

  // Fallback WebView : si pas de WebView, afficher le fallback
  if (authDone && !isWebView) {
    return <TelegramBackend />;
  }

  // En attente d'auth
  if (!authDone || !context.isReady) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100dvh',
          color: '#94A3B8',
          fontSize: 16,
          backgroundColor: '#0F172A',
          gap: 12,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            border: '3px solid #334155',
            borderTopColor: '#FF6B35',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <span>Connexion en cours...</span>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return <TmaContext_.Provider value={context}>{children}</TmaContext_.Provider>;
}
