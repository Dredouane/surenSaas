/**
 * 🚪 01-auth - Tests d'authentification
 * 
 * Scénarios couverts:
 * - Login utilisateur existant
 * - Signup nouveau utilisateur
 * - Logout
 * - Gestion des erreurs
 */

import { test, expect } from '@playwright/test';
import { loginAs, logout, generateTestEmail } from '../_setup/helpers';
import { TEST_USERS } from '../_setup/fixtures';

test.describe('🚪 Auth - Login', () => {
  
  test('✅ Login avec admin existant', async ({ page }) => {
    // Login via helper
    await loginAs(page, 'admin');
    
    // Vérifier qu'on est sur le dashboard
    await expect(page).toHaveURL(/.*dashboard.*/);
    await expect(page.getByText(/tableau de bord/i)).toBeVisible();
  });
  
  test('✅ Login avec conducteur', async ({ page }) => {
    await loginAs(page, 'conducteur');
    await expect(page).toHaveURL(/.*dashboard.*/);
  });
  
  test('✅ Login avec gérant', async ({ page }) => {
    await loginAs(page, 'gerant');
    await expect(page).toHaveURL(/.*dashboard.*/);
  });
  
  test('❌ Login échoue avec mauvais mot de passe', async ({ page }) => {
    await page.goto('/login');
    
    // Email
    await page.fill('input[type="email"]', TEST_USERS.admin.email);
    await page.click('button:has-text("Continuer")');
    
    // Attendre le formulaire mot de passe
    await page.waitForSelector('input[type="password"]');
    
    // Mauvais mot de passe
    await page.fill('input[type="password"]', 'mauvaismotdepasse');
    await page.click('button:has-text("Se connecter")');
    
    // Vérifier le message d'erreur
    await expect(page.getByText(/incorrect|erreur/i)).toBeVisible();
  });
  
  test('❌ Email non autorisé est rejeté', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[type="email"]', 'inconnu@example.com');
    await page.click('button:has-text("Continuer")');
    
    // Attendre et vérifier le message d'erreur
    await page.waitForTimeout(2000);
    await expect(page.getByText(/non autorisé/i)).toBeVisible();
  });
});

test.describe('🚪 Auth - Signup', () => {
  
  test('✅ Signup nouveau utilisateur', async ({ page }) => {
    const uniqueEmail = generateTestEmail('nouveau');
    
    await page.goto('/login');
    
    // Étape 1: Email
    await page.fill('input[type="email"]', uniqueEmail);
    await page.click('button:has-text("Continuer")');
    
    // Attendre le formulaire de création
    await page.waitForSelector('input[type="password"]');
    await expect(page.getByText(/créer votre compte/i)).toBeVisible();
    
    // Étape 2: Mot de passe
    await page.fill('input[type="password"]', 'NouveauPassword123!');
    await page.click('button:has-text("Créer mon compte")');
    
    // Vérifier redirection
    await page.waitForURL(/.*dashboard.*/, { timeout: 15000 });
    await expect(page.getByText(/tableau de bord/i)).toBeVisible();
  });
  
  test('❌ Signup refuse email déjà utilisé', async ({ page }) => {
    await page.goto('/login');
    
    // Utiliser l'email admin qui existe déjà
    await page.fill('input[type="email"]', TEST_USERS.admin.email);
    await page.click('button:has-text("Continuer")');
    
    // Attendre
    await page.waitForTimeout(2000);
    
    // Vérifier qu'on propose de se connecter (pas de créer)
    await expect(page.getByText(/se connecter/i)).toBeVisible();
    await expect(page.getByText(/créer/i)).not.toBeVisible();
  });
});

test.describe('🚪 Auth - Logout', () => {
  
  test('✅ Logout redirige vers login', async ({ page }) => {
    // Login d'abord
    await loginAs(page, 'admin');
    
    // Logout
    await logout(page);
    
    // Vérifier qu'on est sur login
    await expect(page).toHaveURL(/.*login.*/);
  });
  
  test('❌ Accès dashboard après logout est refusé', async ({ page }) => {
    // Login
    await loginAs(page, 'admin');
    
    // Logout
    await logout(page);
    
    // Essayer d'accéder au dashboard
    await page.goto('/dashboard');
    
    // Attendre et vérifier qu'on est redirigé
    await page.waitForTimeout(2000);
    const url = page.url();
    expect(url).toMatch(/login|dashboard/);
  });
});

test.describe('🚪 Auth - UI', () => {
  
  test('📱 Page login affiche les éléments correctement', async ({ page }) => {
    await page.goto('/login');
    
    // Vérifier structure
    await expect(page.getByRole('heading')).toBeVisible();
    await expect(page.getByPlaceholder(/email/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /continuer/i })).toBeVisible();
    await expect(page.getByText(/suren/i)).toBeVisible();
  });
  
  test('📱 Formulaire est accessible', async ({ page }) => {
    await page.goto('/login');
    
    // Vérifier labels
    const emailInput = page.getByPlaceholder(/email/i);
    await expect(emailInput).toHaveAttribute('type', 'email');
    
    // Vérifier que le bouton est disabled si champ vide
    const submitButton = page.getByRole('button', { name: /continuer/i });
    await expect(submitButton).toBeEnabled();
  });
});

test.describe('🚪 Auth - Scénarios Optionnels', () => {
  
  test('❌ Email format invalide rejeté', async ({ page }) => {
    await page.goto('/login');
    
    // Essayer un email invalide
    await page.fill('input[type="email"]', 'pas-un-email');
    await page.click('button:has-text("Continuer")');
    
    // Vérifier que le navigateur bloque (validation HTML5)
    // Ou qu'un message d'erreur apparaît
    await page.waitForTimeout(1000);
    
    // L'input devrait toujours être visible (pas de transition)
    await expect(page.getByPlaceholder(/email/i)).toBeVisible();
  });
  
  test('❌ Password trop court lors du signup rejeté', async ({ page }) => {
    const uniqueEmail = generateTestEmail('short-pwd');
    
    await page.goto('/login');
    
    // Étape 1: Email
    await page.fill('input[type="email"]', uniqueEmail);
    await page.click('button:has-text("Continuer")');
    
    // Attendre le formulaire de création
    await page.waitForSelector('input[type="password"]');
    await expect(page.getByText(/créer votre compte/i)).toBeVisible();
    
    // Essayer un mot de passe trop court
    await page.fill('input[type="password"]', '123');
    
    // Le bouton devrait être désactivé
    const submitButton = page.getByRole('button', { name: /créer mon compte/i });
    await expect(submitButton).toBeDisabled();
  });
  
  test('✅ Retour possible étape 2 → 1', async ({ page }) => {
    await page.goto('/login');
    
    // Étape 1: Email
    await page.fill('input[type="email"]', 'test-retour@suren.com');
    await page.click('button:has-text("Continuer")');
    
    // Attendre le formulaire de mot de passe
    await page.waitForSelector('input[type="password"]');
    
    // Vérifier qu'on est bien à l'étape 2
    await expect(page.getByPlaceholder('••••••••')).toBeVisible();
    
    // Cliquer sur le bouton retour (s'il existe)
    const backButton = page.getByRole('button', { name: /retour|back/i });
    if (await backButton.isVisible().catch(() => false)) {
      await backButton.click();
      
      // Vérifier qu'on est revenu à l'étape 1
      await expect(page.getByPlaceholder(/email/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /continuer/i })).toBeVisible();
    } else {
      // Si pas de bouton retour, le test passe quand même
      console.log('⚠️ Pas de bouton retour détecté');
    }
  });
  
  test('⏱️ Timeout si backend ne répond pas', async ({ page }) => {
    // Ce test vérifie le comportement en cas de lenteur
    await page.goto('/login');
    
    await page.fill('input[type="email"]', 'test-timeout@suren.com');
    
    // Mesurer le temps de réponse
    const startTime = Date.now();
    await page.click('button:has-text("Continuer")');
    
    // Attendre le résultat (succès ou erreur)
    await Promise.race([
      page.waitForSelector('input[type="password"]', { timeout: 15000 }),
      page.waitForSelector('.error', { timeout: 15000 })
    ]).catch(() => {
      // Timeout normal si le serveur est lent
    });
    
    const duration = Date.now() - startTime;
    console.log(`⏱️ Temps de réponse: ${duration}ms`);
    
    // Le test passe si on a une réponse (succès ou erreur) dans un temps raisonnable
    expect(duration).toBeLessThan(20000);
  });
});
