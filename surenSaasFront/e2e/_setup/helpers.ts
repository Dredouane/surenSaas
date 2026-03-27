/**
 * 🔧 Helpers E2E Partagés
 * 
 * Fonctions utilitaires réutilisables dans tous les tests E2E
 */

import { Page, expect } from '@playwright/test';

// Configuration
const BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:3000';

// Timeouts augmentés pour les systèmes lents
const TIMEOUTS = {
  element: 30000,    // 30s pour trouver un élément
  navigation: 30000, // 30s pour la navigation
  action: 15000,     // 15s pour une action (fill, click)
};

/**
 * Types d'utilisateurs disponibles pour les tests
 */
export type UserRole = 'admin' | 'conducteur' | 'gerant' | 'comptable';

/**
 * Données de test par rôle
 */
export const TEST_USERS: Record<UserRole, { email: string; password: string }> = {
  admin: {
    email: process.env.TEST_ADMIN_EMAIL || 'test-e2e-admin@suren.com',
    password: process.env.TEST_ADMIN_PASSWORD || 'TestPassword123!',
  },
  conducteur: {
    email: process.env.TEST_CONDUCTEUR_EMAIL || 'test-e2e-conducteur@suren.com',
    password: process.env.TEST_CONDUCTEUR_PASSWORD || 'TestPassword123!',
  },
  gerant: {
    email: process.env.TEST_GERANT_EMAIL || 'test-e2e-gerant@suren.com',
    password: process.env.TEST_GERANT_PASSWORD || 'TestPassword123!',
  },
  comptable: {
    email: process.env.TEST_COMPTABLE_EMAIL || 'test-e2e-comptable@suren.com',
    password: process.env.TEST_COMPTABLE_PASSWORD || 'TestPassword123!',
  },
};

/**
 * 🔑 Login avec un rôle spécifique
 * @param page - Instance Playwright
 * @param role - Rôle de l'utilisateur
 */
export async function loginAs(page: Page, role: UserRole): Promise<void> {
  const user = TEST_USERS[role];
  
  console.log(`🔑 Login as ${role}: ${user.email}`);
  
  // Aller sur la page de login
  console.log('  → Navigating to /login...');
  await page.goto('/login');
  console.log('  → Waiting for page load...');
  await page.waitForLoadState('networkidle');
  
  // Attendre que le Suspense de React se résolve et que le formulaire apparaisse
  // On attend l'input email spécifique avec son id
  console.log('  → Waiting for login form to be ready...');
  try {
    await page.waitForSelector('input#email', { timeout: TIMEOUTS.element });
    console.log('  ✓ Email input found');
  } catch (e) {
    // Debug: prendre un screenshot pour voir l'état de la page
    await screenshot(page, 'login-error-no-form');
    console.log('  ⚠️ Email input not found after timeout');
    console.log('  → Current URL:', page.url());
    console.log('  → Page title:', await page.title());
    throw e;
  }
  
  // Étape 1: Email
  console.log('  → Filling email field...');
  const emailField = page.locator('input#email');
  await emailField.fill(user.email);
  console.log('  ✓ Email filled');
  
  // Trouver et cliquer sur le bouton Continuer
  console.log('  → Looking for continue button...');
  const continueButton = page.locator('button:has-text("Continuer")');
  await continueButton.waitFor({ state: 'visible', timeout: TIMEOUTS.element });
  await continueButton.click();
  console.log('  ✓ Continue clicked');
  
  // Attendre que le formulaire de mot de passe apparaisse
  console.log('  → Waiting for password form...');
  await page.waitForSelector('input#password', { timeout: TIMEOUTS.element });
  console.log('  ✓ Password form loaded');
  
  // Étape 2: Mot de passe
  console.log('  → Filling password field...');
  const passwordField = page.locator('input#password');
  await passwordField.fill(user.password);
  console.log('  ✓ Password filled');
  
  // Cliquer sur le bouton de connexion/création
  console.log('  → Looking for submit button...');
  // Le bouton peut avoir différents textes selon si l'utilisateur existe
  const submitButton = page.locator('button[type="submit"]').last();
  await submitButton.waitFor({ state: 'visible', timeout: TIMEOUTS.element });
  await submitButton.click();
  console.log('  ✓ Submit clicked');
  
  // Attendre la redirection vers le dashboard
  console.log('  → Waiting for dashboard...');
  await page.waitForURL('**/dashboard', { timeout: TIMEOUTS.navigation });
  console.log('  ✓ Dashboard loaded');
  
  console.log(`✅ Logged in as ${role}`);
}

/**
 * 🚪 Déconnexion
 * @param page - Instance Playwright
 */
export async function logout(page: Page): Promise<void> {
  console.log('🚪 Logout');
  
  const logoutButton = page.getByRole('button', { name: /déconnexion|logout/i });
  await logoutButton.waitFor({ state: 'visible', timeout: TIMEOUTS.element });
  await logoutButton.click();
  await page.waitForURL('**/login', { timeout: TIMEOUTS.navigation });
  
  console.log('✅ Logged out');
}

/**
 * 📄 Créer une facture de test
 * @param page - Instance Playwright
 * @param data - Données de la facture
 */
export async function createInvoice(page: Page, data: {
  supplier: string;
  amount: number;
  description?: string;
}): Promise<string> {
  console.log(`📄 Creating invoice: ${data.supplier}`);
  
  await page.goto('/dashboard/invoices/create');
  await page.waitForLoadState('networkidle');
  
  // Remplir le formulaire avec attentes
  const supplierField = page.locator('[name="supplier_name"]');
  await supplierField.waitFor({ state: 'visible', timeout: TIMEOUTS.element });
  await supplierField.fill(data.supplier);
  
  const amountField = page.locator('[name="total_amount"]');
  await amountField.waitFor({ state: 'visible', timeout: TIMEOUTS.element });
  await amountField.fill(data.amount.toString());
  
  if (data.description) {
    const descField = page.locator('[name="description"]');
    await descField.waitFor({ state: 'visible', timeout: TIMEOUTS.element });
    await descField.fill(data.description);
  }
  
  // Soumettre
  const submitButton = page.locator('button:has-text("Créer")');
  await submitButton.waitFor({ state: 'visible', timeout: TIMEOUTS.element });
  await submitButton.click();
  
  // Attendre la création et récupérer l'ID
  await page.waitForURL(/.*\/invoices\/.*/, { timeout: TIMEOUTS.navigation });
  const url = page.url();
  const invoiceId = url.split('/').pop() || '';
  
  console.log(`✅ Invoice created: ${invoiceId}`);
  return invoiceId;
}

/**
 * ⏱️ Attendre qu'un élément soit visible avec retry
 * @param page - Instance Playwright
 * @param selector - Sélecteur CSS ou texte
 * @param timeout - Timeout en ms (défaut: 30s pour systèmes lents)
 */
export async function waitForElement(
  page: Page, 
  selector: string, 
  timeout = TIMEOUTS.element
): Promise<void> {
  if (selector.startsWith('text=') || selector.startsWith('has-text=')) {
    await page.getByText(selector.replace(/^(text=|has-text=)/, '')).waitFor({ timeout });
  } else {
    await page.locator(selector).waitFor({ timeout });
  }
}

/**
 * 📸 Prendre un screenshot nommé avec timestamp
 * @param page - Instance Playwright
 * @param name - Nom du screenshot
 */
export async function screenshot(page: Page, name: string): Promise<void> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  await page.screenshot({ 
    path: `test-results/screenshots/${name}-${timestamp}.png`,
    fullPage: true 
  });
}

/**
 * 🧹 Nettoyer les données de test (à appeler en fin de test)
 * @param page - Instance Playwright
 */
export async function cleanupTestData(page: Page): Promise<void> {
  // Cette fonction peut appeler une API de cleanup si nécessaire
  console.log('🧹 Cleanup test data');
}

/**
 * 🔍 Vérifier qu'on est sur une page spécifique
 * @param page - Instance Playwright
 * @param path - Chemin attendu (ex: /dashboard)
 */
export async function expectToBeOnPage(page: Page, path: string): Promise<void> {
  await expect(page).toHaveURL(new RegExp(`.*${path}.*`));
}

/**
 * ✨ Générer un email unique pour les tests
 * @param prefix - Préfixe de l'email
 */
export function generateTestEmail(prefix: string = 'test'): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 1000);
  return `${prefix}.${timestamp}.${random}@suren-test.com`;
}
