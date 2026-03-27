import { defineConfig, devices } from '@playwright/test';

/**
 * Configuration Playwright pour SurenSaaS
 * 
 * Tests E2E qui peuvent tourner contre:
 * - Local: http://localhost:3000 (frontend) + http://localhost:8080 (backend)
 * - Test GCP: URL de test déployée
 * 
 * Usage:
 *   npm run test:e2e:local    # Tests en local
 *   npm run test:e2e:test     # Tests sur environnement TEST
 *   npm run test:e2e:prod     # Tests sur PROD (⚠️ attention)
 */

// Détection de l'environnement cible
const TARGET = process.env.TEST_TARGET || 'local';

const BASE_URLS: Record<string, string> = {
  local: 'http://localhost:3000',
  test: 'https://test-surensaas-front-982795023541.europe-west1.run.app',  // Frontend déployé test
  prod: process.env.PROD_FRONTEND_URL || 'https://app.surensaas.com',
};

const API_URLS: Record<string, string> = {
  local: 'http://localhost:8080',
  test: 'https://test-surensaas-back-REDACTED-ew.a.run.app',
  prod: process.env.PROD_API_URL || 'https://api.surensaas.com',
};

console.log(`🎯 Playwright target: ${TARGET}`);
console.log(`   Frontend: ${BASE_URLS[TARGET]}`);
console.log(`   Backend: ${API_URLS[TARGET]}`);

export default defineConfig({
  testDir: './e2e',
  
  // Exécuter les tests en parallèle (sauf en local pour éviter les conflits)
  fullyParallel: TARGET === 'local' ? false : true,
  
  // Nombre de workers
  workers: TARGET === 'local' ? 1 : 3,
  
  // Répéter les tests flaky
  retries: TARGET === 'local' ? 0 : 2,
  
  // Reporter
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  
  // Configuration globale
  use: {
    baseURL: BASE_URLS[TARGET],
    
    // Traces pour debug
    trace: 'on-first-retry',
    
    // Screenshots sur erreur
    screenshot: 'only-on-failure',
    
    // Vidéo sur échec
    video: 'on-first-retry',
    
    // Timeout par action (augmenté pour systèmes lents)
    actionTimeout: 20000,
    
    // Timeout de navigation
    navigationTimeout: 30000,
    
    // Viewport
    viewport: { width: 1280, height: 720 },
    
    // Headers par défaut
    extraHTTPHeaders: {
      'Accept': 'application/json',
    },
    
    // Lancement navigateur avec options pour systèmes lents
    launchOptions: {
      slowMo: 100, // 100ms de délai entre chaque action
    },
  },
  
  // Projets (navigateurs)
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Désactiver la sandbox pour environnement CI/conteneur
        launchOptions: {
          args: ['--no-sandbox', '--disable-setuid-sandbox'],
        },
      },
    },
  ],
  
  // Ne pas démarrer de serveur - utilise le serveur déjà en cours
  // webServer: TARGET === 'local' ? {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: true,
  //   timeout: 120000,
  // } : undefined,
  
  // Timeout global par test
  timeout: 60000,
  
  // Expect timeout (augmenté pour systèmes lents)
  expect: {
    timeout: 15000,
  },
});
