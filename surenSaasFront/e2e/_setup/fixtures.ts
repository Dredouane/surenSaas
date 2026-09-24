/**
 * 📦 Fixtures - Données de Test
 * 
 * Données réutilisables pour tous les tests E2E
 * Organisées par domaine métier
 */

import { generateTestEmail } from './helpers';

/**
 * 👤 Utilisateurs de test
 * Ces emails doivent exister dans pre_authorized_emails
 */
export const TEST_USERS = {
  admin: {
    email: process.env.TEST_ADMIN_EMAIL || 'test.admin@suren.com',
    password: process.env.TEST_ADMIN_PASSWORD || 'TestPassword123!',
    role: 'admin' as const,
    description: 'Administrateur avec tous les droits',
  },
  
  conducteur: {
    email: process.env.TEST_CONDUCTEUR_EMAIL || 'test.conducteur@suren.com',
    password: process.env.TEST_CONDUCTEUR_PASSWORD || 'TestPassword123!',
    role: 'conducteur' as const,
    description: 'Conducteur de travaux - crée des factures via Telegram',
    capabilities: ['construction:facturation:write'],
  },
  
  gerant: {
    email: process.env.TEST_GERANT_EMAIL || 'test.gerant@suren.com',
    password: process.env.TEST_GERANT_PASSWORD || 'TestPassword123!',
    role: 'gerant' as const,
    description: 'Gérant - valide/rejette les factures',
    capabilities: ['construction:facturation:read', 'construction:facturation:validate'],
  },
  
  comptable: {
    email: process.env.TEST_COMPTABLE_EMAIL || 'test.comptable@suren.com',
    password: process.env.TEST_COMPTABLE_PASSWORD || 'TestPassword123!',
    role: 'comptable' as const,
    description: 'Comptable - traite les factures validées',
    capabilities: ['construction:facturation:read'],
  },
};

/**
 * 📄 Données de factures de test
 */
export const TEST_INVOICES = {
  /**
   * Facture minimale (champs obligatoires uniquement)
   */
  minimal: {
    supplier_name: 'Fournisseur Test',
    amount_ttc: 1200.00,
    status: 'brouillon' as const,
  },
  
  /**
   * Facture complète (tous les champs)
   */
  complete: {
    supplier_name: 'Fournisseur Complet SA',
    supplier_address: '123 Rue Example, 75000 Paris',
    supplier_siret: '12345678900012',
    amount_ht: 1000.00,
    amount_ttc: 1200.00,
    vat_amount: 200.00,
    vat_rate: 20.0,
    invoice_date: '2024-03-15',
    due_date: '2024-04-15',
    description: 'Matériaux de construction',
    invoice_number: 'FAC-2024-TEST',
    status: 'brouillon' as const,
  },
  
  /**
   * Générateur de facture unique pour éviter les conflits
   */
  generateUnique: () => ({
    supplier_name: `Fournisseur ${Date.now()}`,
    amount_ttc: Math.floor(Math.random() * 10000) + 100,
    description: `Test E2E ${new Date().toISOString()}`,
    status: 'brouillon' as const,
  }),
};

/**
 * 👥 Données de clients de test
 */
export const TEST_CLIENTS = {
  standard: {
    name: 'Client Test SA',
    email: 'client@test.com',
    phone: '+33 1 23 45 67 89',
    address: '45 Avenue Test, 75008 Paris',
    siret: '98765432100021',
  },
  
  generateUnique: () => ({
    name: `Client ${Date.now()}`,
    email: generateTestEmail('client'),
    phone: '+33 1 23 45 67 89',
  }),
};

/**
 * 🤖 Configuration Telegram de test
 */
export const TEST_TELEGRAM = {
  bot: {
    username: '@suren_construction_test_bot',
    token: process.env.TEST_TELEGRAM_BOT_TOKEN || 'test-token',
  },
  
  user: {
    telegram_id: 123456789,
    username: 'test_conducteur',
    first_name: 'Test',
    last_name: 'Conducteur',
  },
};

/**
 * 🏢 Organisation de test
 */
export const TEST_ORG = {
  id: process.env.NEXT_PUBLIC_ORG_ID ?? '',
  slug: 'REDACTED_ORG_SLUG',
  name: 'Suren - TEST',
};

/**
 * ⏱️ Timeouts (en millisecondes)
 */
export const TIMEOUTS = {
  action: 10000,      // Actions utilisateur (click, fill)
  navigation: 30000,  // Navigation de page
  api: 15000,         // Appels API
  fileUpload: 60000,  // Upload de fichiers
};

/**
 * 🎨 Sélecteurs CSS communs
 * 
 * ⚠️ À utiliser avec précaution - privilégier les sélecteurs texte/role
 */
export const SELECTORS = {
  // Auth
  loginForm: '[data-testid="login-form"]',
  emailInput: 'input[type="email"]',
  passwordInput: 'input[type="password"]',
  submitButton: 'button[type="submit"]',
  
  // Navigation
  sidebar: '[data-testid="sidebar"]',
  navInvoices: 'a[href*="invoices"]',
  navClients: 'a[href*="clients"]',
  
  // Invoices
  invoiceList: '[data-testid="invoice-list"]',
  invoiceCard: '[data-testid="invoice-card"]',
  createInvoiceButton: 'button:has-text("Nouvelle facture")',
};
