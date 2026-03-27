/**
 * Tests End-to-End pour SurenSaaS
 * 
 * Ces tests automatisent les scénarios utilisateurs complets :
 * - Login
 * - Signup  
 * - Navigation dashboard
 * - Création de factures
 * 
 * Ils peuvent tourner contre local ou les environnements déployés.
 */

import { test, expect, Page } from '@playwright/test';

// Données de test
const TEST_USER = {
  email: 'test-e2e@suren.com',
  password: 'TestPassword123!',
};

const ADMIN_USER = {
  email: process.env.TEST_ADMIN_EMAIL || 'REDACTED_EMAIL',
  password: process.env.TEST_ADMIN_PASSWORD || 'TestPassword123!',
};

/**
 * Helper: Attendre que la page soit chargée
 */
async function waitForPageLoad(page: Page) {
  await page.waitForLoadState('networkidle');
}

/**
 * Test: Page de login s'affiche correctement
 */
test('Login page loads correctly', async ({ page }) => {
  await page.goto('/login');
  await waitForPageLoad(page);
  
  // Vérifier les éléments présents
  await expect(page.getByText('SurenSaaS')).toBeVisible();
  await expect(page.getByText('Connexion')).toBeVisible();
  await expect(page.getByPlaceholder('vous@entreprise.com')).toBeVisible();
  await expect(page.getByRole('button', { name: /continuer/i })).toBeVisible();
});

/**
 * Test: Workflow complet signup
 * 
 * Scénario:
 * 1. Aller sur /login
 * 2. Entrer email non existant
 * 3. Vérifier qu'on passe à l'étape mot de passe
 * 4. Créer le compte
 * 5. Vérifier redirection dashboard
 */
test('Complete signup workflow', async ({ page }) => {
  // Générer un email unique pour ce test
  const timestamp = Date.now();
  const uniqueEmail = `test.signup.${timestamp}@suren.com`;
  
  console.log(`🧪 Test signup avec: ${uniqueEmail}`);
  
  // 1. Aller sur la page de login
  await page.goto('/login');
  await waitForPageLoad(page);
  
  // 2. Entrer l'email
  await page.getByPlaceholder('vous@entreprise.com').fill(uniqueEmail);
  await page.getByRole('button', { name: /continuer/i }).click();
  
  // 3. Attendre que le formulaire de mot de passe apparaisse
  await page.waitForSelector('input[type="password"]', { timeout: 10000 });
  
  // 4. Vérifier qu'on est à l'étape mot de passe
  await expect(page.getByText(/créer votre compte/i)).toBeVisible();
  await expect(page.getByPlaceholder('••••••••')).toBeVisible();
  
  // 4. Entrer le mot de passe
  await page.getByPlaceholder('••••••••').fill(TEST_USER.password);
  await page.getByRole('button', { name: /créer mon compte/i }).click();
  
  // 5. Attendre la redirection vers le dashboard
  await page.waitForURL('**/dashboard', { timeout: 10000 });
  
  // 6. Vérifier qu'on est sur le dashboard
  await expect(page.getByText(/tableau de bord/i)).toBeVisible();
  
  console.log('✅ Signup workflow complet réussi!');
});

/**
 * Test: Login utilisateur existant
 */
test('Login existing user', async ({ page }) => {
  // Utiliser l'admin qui existe déjà
  console.log(`🧪 Test login avec: ${ADMIN_USER.email}`);
  
  // 1. Aller sur la page de login
  await page.goto('/login');
  await waitForPageLoad(page);
  
  // 2. Entrer l'email
  await page.getByPlaceholder('vous@entreprise.com').fill(ADMIN_USER.email);
  await page.getByRole('button', { name: /continuer/i }).click();
  
  // 3. Attendre que le formulaire de mot de passe apparaisse
  await page.waitForSelector('input[type="password"]', { timeout: 10000 });
  
  // 4. Vérifier qu'on est à l'étape mot de passe (pas "créer")
  await expect(page.getByText(/mot de passe/i).first()).toBeVisible();
  
  // 4. Entrer le mot de passe
  await page.getByPlaceholder('••••••••').fill(ADMIN_USER.password);
  await page.getByRole('button', { name: /se connecter/i }).click();
  
  // 5. Attendre la redirection
  await page.waitForURL('**/dashboard', { timeout: 10000 });
  
  // 6. Vérifier le dashboard
  await expect(page.getByText(/tableau de bord/i)).toBeVisible();
  
  console.log('✅ Login réussi!');
});

/**
 * Test: Email non autorisé est rejeté
 */
test('Unauthorized email is rejected', async ({ page }) => {
  await page.goto('/login');
  await waitForPageLoad(page);
  
  // Entrer un email qui n'est pas dans pre_authorized
  await page.getByPlaceholder('vous@entreprise.com').fill('unknown@example.com');
  await page.getByRole('button', { name: /continuer/i }).click();
  
  // Attendre le message d'erreur
  await page.waitForSelector('text=/n\'est pas autorisé/', { timeout: 10000 });
  
  // Vérifier le message d'erreur
  await expect(page.getByText(/n'est pas autorisé/i)).toBeVisible();
});

/**
 * Test: Mot de passe trop court est rejeté
 */
test('Short password is rejected', async ({ page }) => {
  const timestamp = Date.now();
  const uniqueEmail = `test.pwd.${timestamp}@suren.com`;
  
  await page.goto('/login');
  await waitForPageLoad(page);
  
  // Aller à l'étape mot de passe
  await page.getByPlaceholder('vous@entreprise.com').fill(uniqueEmail);
  await page.getByRole('button', { name: /continuer/i }).click();
  
  // Attendre que le formulaire de mot de passe apparaisse
  await page.waitForSelector('input[type="password"]', { timeout: 10000 });
  
  // Essayer un mot de passe court
  await page.getByPlaceholder('••••••••').fill('123');
  
  // Le bouton devrait être désactivé ou montrer une erreur
  const submitButton = page.getByRole('button', { name: /créer mon compte/i });
  await expect(submitButton).toBeDisabled();
});

/**
 * Test: Navigation dashboard après login
 */
test('Dashboard navigation after login', async ({ page }) => {
  // Login d'abord
  await page.goto('/login');
  await page.getByPlaceholder('vous@entreprise.com').fill(ADMIN_USER.email);
  await page.getByRole('button', { name: /continuer/i }).click();
  
  // Attendre le formulaire mot de passe
  await page.waitForSelector('input[type="password"]', { timeout: 10000 });
  
  await page.getByPlaceholder('••••••••').fill(ADMIN_USER.password);
  await page.getByRole('button', { name: /se connecter/i }).click();
  await page.waitForURL('**/dashboard', { timeout: 10000 });
  
  // Tester la navigation
  await page.getByText(/factures/i).click();
  await expect(page).toHaveURL(/.*dashboard.*/);
});

/**
 * Test: Déconnexion
 */
test('Logout works', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.getByPlaceholder('vous@entreprise.com').fill(ADMIN_USER.email);
  await page.getByRole('button', { name: /continuer/i }).click();
  
  // Attendre le formulaire mot de passe
  await page.waitForSelector('input[type="password"]', { timeout: 10000 });
  
  await page.getByPlaceholder('••••••••').fill(ADMIN_USER.password);
  await page.getByRole('button', { name: /se connecter/i }).click();
  await page.waitForURL('**/dashboard', { timeout: 10000 });
  
  // Déconnexion
  await page.getByRole('button', { name: /déconnexion/i }).click();
  
  // Vérifier qu'on est redirigé vers login
  await page.waitForURL('**/login', { timeout: 10000 });
});
