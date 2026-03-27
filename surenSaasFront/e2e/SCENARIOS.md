# 🌳 Scénarios E2E - Structure Arborescente

## Organisation des Folders

```
e2e/
├── _setup/                    # Configuration partagée
│   ├── auth.setup.ts         # Pré-authentification pour tous les tests
│   ├── fixtures.ts           # Données de test réutilisables
│   └── helpers.ts            # Fonctions utilitaires
│
├── 🚪 01-auth/               # AUTHENTIFICATION (racine)
│   ├── login.spec.ts         # Connexion
│   ├── signup.spec.ts        # Inscription
│   ├── logout.spec.ts        # Déconnexion
│   └── _flows/
│       └── complete-auth-flow.spec.ts  # Flux complet
│
├── 📊 02-dashboard/          # DASHBOARD (accueil)
│   ├── dashboard.spec.ts     # Vue d'ensemble
│   └── _flows/
│       └── navigation.spec.ts # Navigation principale
│
├── 📄 03-invoices/           # FACTURATION (fonctionnalité clé)
│   ├── list.spec.ts          # Liste des factures
│   ├── create.spec.ts        # Création facture
│   ├── detail.spec.ts        # Détail facture
│   ├── edit.spec.ts          # Modification facture
│   └── _flows/
│       ├── create-and-validate.spec.ts    # Créer + valider
│       ├── upload-via-bot.spec.ts         # Upload Telegram
│       └── full-lifecycle.spec.ts         # Cycle complet
│
├── 👥 04-clients/            # GESTION CLIENTS
│   ├── list.spec.ts
│   ├── create.spec.ts
│   └── _flows/
│       └── client-with-invoices.spec.ts
│
├── 🤖 05-telegram/           # INTEGRATION TELEGRAM
│   ├── bot-connection.spec.ts
│   └── _flows/
│       └── invoice-upload-flow.spec.ts
│
├── ⚙️ 06-settings/           # PARAMÈTRES
│   └── profile.spec.ts
│
└── 🔄 99-end-to-end/         # SCÉNARIOS COMPLEXES
    ├── conducteur-journey.spec.ts      # Parcours conducteur
    ├── gerant-validation.spec.ts       # Parcours gérant
    └── comptable-workflow.spec.ts      # Parcours comptable
```

## Convention de Nommage

### Fichiers
```
[action]-[objet].spec.ts           # ex: create-invoice.spec.ts
[action]-[objet]-[context].spec.ts # ex: create-invoice-error.spec.ts
```

### Tests (describe/it)
```typescript
// Structure hiérarchique
describe('🚪 Auth - Login', () => {           // Module + Feature
  describe('Formulaire', () => {              // Sous-section
    test('✅ Valide avec email correct', () => {});  // Cas positif
    test('❌ Refuse email invalide', () => {});      // Cas erreur
    test('⚡ Soumission rapide', () => {});          // Cas perf
  });
});
```

### Emojis (système visuel)
- 🚪 Auth (Authentification)
- 📊 Dashboard (Tableau de bord)
- 📄 Invoices (Factures)
- 👥 Clients (Clients)
- 🤖 Telegram (Bot)
- ⚙️ Settings (Paramètres)
- 🔄 End-to-end (Scénarios complets)
- ✅ Succès
- ❌ Erreur
- ⚠️ Warning
- ✨ Nouveau
- 🧹 Cleanup

## Principe d'Évolution

### Ajouter une nouvelle branche
```
📁 07-[nouveau-module]/
  ├── [feature].spec.ts
  └── _flows/
      └── [scenario-complexe].spec.ts
```

### Ajouter un sous-scénario
```
📁 03-invoices/
  └── _flows/
      └── nouveau-flux.spec.ts   # ← Ajouter ici
```

### Niveaux de granularité
1. **Unitaire** (`*.spec.ts`) : Teste une action isolée
2. **Flow** (`_flows/*.spec.ts`) : Chaîne 2-3 actions
3. **Journey** (`99-end-to-end/*.spec.ts`) : Parcours complet métier

## Données de Test (Fixtures)

```typescript
// e2e/_setup/fixtures.ts
export const TEST_DATA = {
  users: {
    admin: { email: 'admin@suren.com', password: '***' },
    conducteur: { email: 'conducteur@suren.com', password: '***' },
    gerant: { email: 'gerant@suren.com', password: '***' },
  },
  invoices: {
    draft: { supplier: 'Test Fournisseur', amount: 1000 },
    pending: { supplier: 'Fournisseur A', amount: 2000 },
  }
};
```

## Scénarios Prioritaires (MVP)

### Phase 1 - Core (maintenant)
1. 🚪 Auth : Login / Signup / Logout
2. 📄 Invoices : Liste / Créer / Voir détail
3. 🤖 Telegram : Upload facture via bot

### Phase 2 - Métier (semaine prochaine)
4. 🔄 Validation workflow (gérant valide facture)
5. 📄 Cycle complet facture (création → validation → archivage)

### Phase 3 - Avancé (plus tard)
6. 👥 Gestion clients liée aux factures
7. 📊 Dashboard avec stats
8. ⚙️ Paramètres utilisateur

## Exemple de Structure d'un Test

```typescript
// e2e/03-invoices/_flows/create-and-validate.spec.ts
import { test, expect } from '@playwright/test';
import { loginAs } from '../../_setup/helpers';

test.describe('📄 Factures - Flux Créer + Valider', () => {
  
  test('✅ Conducteur crée, Gérant valide', async ({ page }) => {
    // Étape 1: Login conducteur
    await loginAs(page, 'conducteur');
    
    // Étape 2: Créer facture
    await page.goto('/dashboard/invoices/create');
    await page.fill('[name=supplier]', 'Fournisseur Test');
    await page.click('button:has-text("Créer")');
    
    // Étape 3: Vérifier statut "en attente"
    await expect(page.locator('.status')).toHaveText('En attente');
    
    // Étape 4: Logout
    await page.click('button:has-text("Déconnexion")');
    
    // Étape 5: Login gérant
    await loginAs(page, 'gerant');
    
    // Étape 6: Valider facture
    await page.goto('/dashboard/invoices');
    await page.click('text=Fournisseur Test');
    await page.click('button:has-text("Valider")');
    
    // Étape 7: Vérifier statut "validée"
    await expect(page.locator('.status')).toHaveText('Validée');
  });
});
```

Cette structure permet de :
- ✅ Trouver rapidement un scénario (numérotation + emoji)
- ✅ Ajouter facilement de nouveaux modules (07-XX)
- ✅ Comprendre la granularité (fichier vs _flows vs 99-end-to-end)
- ✅ Réutiliser les helpers et fixtures
- ✅ Maintenir la cohérence sur le long terme
