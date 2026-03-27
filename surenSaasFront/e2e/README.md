# Documentation E2E - SurenSaaS

## 🎯 Objectif

Cette suite de tests E2E (End-to-End) teste les **parcours utilisateurs complets** de l'application SurenSaaS en simulant des interactions réelles avec le navigateur.

### Ce qui est testé :
- ✅ Flux d'authentification (login/signup/logout)
- ✅ Création et gestion des factures
- ✅ Upload de factures via Telegram
- ✅ Workflows métier complets (conducteur → gérant → comptable)

### Ce qui n'est PAS testé ici :
- ❌ Tests unitaires (cf. `surenSaasBack/tests/`)
- ❌ Tests d'intégration API (cf. `surenSaasBack/tests/`)
- ❌ Tests de performance (à ajouter plus tard)

---

## 🛠️ Stack Technique

| Outil | Version | Usage |
|-------|---------|-------|
| **Playwright** | ^1.58.2 | Framework E2E (navigateur automatisé) |
| **@playwright/test** | ^1.58.2 | Runner de tests |
| **Firefox** | Latest | Navigateur par défaut (Chromium a trop de dépendances système) |

### Pourquoi Playwright ?
- **Multi-navigateurs** : Chrome, Firefox, Safari
- **Auto-waiting** : Attend automatiquement les éléments
- **Screenshots/Vidéos** : Capture automatique sur échec
- **Trace viewer** : Debug interactif
- **Parallélisation** : Tests rapides

---

## 📁 Structure des Dossiers

```
e2e/
├── _setup/                    # ⚙️ Configuration partagée
│   ├── helpers.ts            # Fonctions utilitaires (login, createInvoice, etc.)
│   ├── fixtures.ts           # Données de test (emails, mots de passe)
│   └── auth.setup.ts         # Pré-authentification (optionnel)
│
├── 01-auth/                   # 🚪 Authentification
│   ├── login.spec.ts         # Connexion
│   ├── signup.spec.ts        # Inscription
│   ├── logout.spec.ts        # Déconnexion
│   └── _flows/
│       └── complete-auth-flow.spec.ts
│
├── 02-dashboard/              # 📊 Tableau de bord
│   ├── dashboard.spec.ts
│   └── _flows/
│       └── navigation.spec.ts
│
├── 03-invoices/               # 📄 Factures (fonctionnalité clé)
│   ├── list.spec.ts
│   ├── create.spec.ts
│   ├── detail.spec.ts
│   └── _flows/
│       ├── create-and-validate.spec.ts
│       └── upload-via-bot.spec.ts
│
├── 04-clients/                # 👥 Gestion clients
├── 05-telegram/               # 🤖 Intégration Telegram
├── 06-settings/               # ⚙️ Paramètres
├── 99-end-to-end/             # 🔄 Scénarios complexes métier
│
├── SCENARIOS.md              # 📋 Documentation scénarios
└── README.md                 # 📖 Ce fichier
```

### Convention de nommage :
- **Dossiers** : `XX-nom-feature/` (numérotation pour ordre logique)
- **Fichiers** : `[action]-[objet].spec.ts`
- **Emojis** : Chaque module a un emoji (🚪 Auth, 📄 Invoices, etc.)

---

## 🚀 Commandes

```bash
# Depuis surenSaasFront/

# Lancer tous les tests
npm run test:e2e

# Tests en local (localhost:3000)
npm run test:e2e:local

# Tests sur environnement TEST
npm run test:e2e:test

# Mode interactif (UI)
npm run test:e2e:ui

# Mode debug (step-by-step)
npm run test:e2e:debug

# Voir le rapport HTML
npm run test:e2e:report

# Lancer un fichier spécifique
npx playwright test e2e/01-auth/login.spec.ts

# Lancer avec headed (voir le navigateur)
npx playwright test --headed
```

---

## ⚙️ Configuration

### Environnements

3 environnements supportés (définis dans `playwright.config.ts`) :

| Environnement | URL Frontend | URL Backend | Commande |
|---------------|--------------|-------------|----------|
| **local** | http://localhost:3000 | http://localhost:8080 | `npm run test:e2e:local` |
| **test** | URL TEST | URL TEST API | `npm run test:e2e:test` |
| **prod** | URL PROD | URL PROD API | `npm run test:e2e:prod` |

### Variables d'environnement

Créer un fichier `.env.local` à la racine de `surenSaasFront/` :

```bash
# URLs
TEST_FRONTEND_URL=https://test-surensaas.example.com
TEST_API_URL=https://test-api.example.com

# Credentials de test
TEST_ADMIN_EMAIL=admin@test.com
TEST_ADMIN_PASSWORD=password123
TEST_CONDUCTEUR_EMAIL=conducteur@test.com
TEST_CONDUCTEUR_PASSWORD=password123
```

---

## 🧪 Écrire un Nouveau Test

### 1. Test simple (unitaire)

```typescript
// e2e/01-auth/login.spec.ts
import { test, expect } from '@playwright/test';

test('✅ Login avec email valide', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'test@example.com');
  await page.click('button:has-text("Continuer")');
  
  await expect(page).toHaveURL(/.*password.*/);
});
```

### 2. Test utilisant les helpers

```typescript
// e2e/03-invoices/create.spec.ts
import { test, expect } from '@playwright/test';
import { loginAs, createInvoice } from '../_setup/helpers';

test('✅ Conducteur crée une facture', async ({ page }) => {
  // Utiliser le helper pour login
  await loginAs(page, 'conducteur');
  
  // Utiliser le helper pour créer une facture
  const invoiceId = await createInvoice(page, {
    supplier: 'Fournisseur Test',
    amount: 1000,
    description: 'Test E2E'
  });
  
  // Vérifier
  await expect(page.locator('.status')).toHaveText('En attente');
});
```

### 3. Test de flux (workflow complet)

```typescript
// e2e/03-invoices/_flows/create-and-validate.spec.ts
import { test, expect } from '@playwright/test';
import { loginAs, logout } from '../../_setup/helpers';

test('🔄 Conducteur crée → Gérant valide', async ({ page }) => {
  // Étape 1: Login conducteur
  await loginAs(page, 'conducteur');
  
  // Étape 2: Créer facture
  await page.goto('/dashboard/invoices/create');
  await page.fill('[name="supplier"]', 'Fournisseur Test');
  await page.click('button:has-text("Créer")');
  
  // Étape 3: Vérifier statut
  await expect(page.locator('.status')).toHaveText('En attente');
  
  // Étape 4: Logout
  await logout(page);
  
  // Étape 5: Login gérant
  await loginAs(page, 'gerant');
  
  // Étape 6: Valider
  await page.goto('/dashboard/invoices');
  await page.click('text=Fournisseur Test');
  await page.click('button:has-text("Valider")');
  
  // Étape 7: Vérifier
  await expect(page.locator('.status')).toHaveText('Validée');
});
```

---

## 🔧 Helpers Disponibles

### `helpers.ts`

| Fonction | Description | Exemple |
|----------|-------------|---------|
| `loginAs(page, role)` | Connecte un utilisateur par rôle | `await loginAs(page, 'admin')` |
| `logout(page)` | Déconnexion | `await logout(page)` |
| `createInvoice(page, data)` | Crée une facture | `await createInvoice(page, {supplier: 'Test', amount: 1000})` |
| `generateTestEmail(prefix)` | Génère email unique | `generateTestEmail('test')` |
| `waitForElement(page, selector)` | Attend un élément | `await waitForElement(page, 'text=Success')` |
| `screenshot(page, name)` | Capture d'écran | `await screenshot(page, 'erreur')` |

### Rôles disponibles

- `admin` : Administrateur (tous les droits)
- `conducteur` : Créer des factures via Telegram
- `gerant` : Valider/rejeter les factures
- `comptable` : Voir les factures validées

---

## 🐛 Debugging

### 1. Voir le rapport HTML

```bash
npm run test:e2e:report
```

Le rapport contient :
- Screenshots sur échec
- Vidéos des tests
- Traces détaillées (clics, navigations)

### 2. Mode UI (interactif)

```bash
npm run test:e2e:ui
```

Interface graphique pour :
- Lancer les tests un par un
- Voir les traces en temps réel
- Inspecter les éléments

### 3. Mode Debug (step-by-step)

```bash
npm run test:e2e:debug
```

Le test s'arrête à chaque ligne pour inspection.

### 4. Screenshots manuels

```typescript
// Dans un test
await page.screenshot({ path: 'debug.png', fullPage: true });
```

---

## 📊 Bonnes Pratiques

### ✅ À FAIRE

- Utiliser les **helpers** pour éviter la duplication
- Attendre les **éléments** avant d'interagir (`waitForSelector`)
- Utiliser des **sélecteurs robustes** (texte visible, role) pas des classes CSS
- **Nettoyer** les données de test en fin de test
- Ajouter des **logs** (`console.log`) pour suivre le déroulement

### ❌ À ÉVITER

- Attendre des **temps fixes** (`waitForTimeout(1000)`)
- Utiliser des **sélecteurs fragiles** (`.btn-primary`, `#id-123`)
- Tester des **détails d'implémentation** (structure HTML exacte)
- Oublier de **gérer les erreurs** (try/catch sur les actions critiques)

---

## 🔄 Cycle de Vie d'un Test

```
Setup → Action → Assertion → Cleanup
  ↓       ↓          ↓          ↓
Login   Remplir    Vérifier   Logout
        formulaire   résultat   Cleanup DB
```

### Exemple complet :

```typescript
import { test } from '@playwright/test';
import { loginAs, logout, generateTestEmail } from './_setup/helpers';

test('✅ Créer une facture', async ({ page }) => {
  // 1. SETUP
  const testEmail = generateTestEmail('facture');
  await loginAs(page, 'conducteur');
  
  // 2. ACTION
  await page.goto('/dashboard/invoices/create');
  await page.fill('[name="supplier"]', 'Fournisseur Test');
  await page.fill('[name="amount"]', '1000');
  await page.click('button:has-text("Créer")');
  
  // 3. ASSERTION
  await expect(page).toHaveURL(/.*invoices.*/);
  await expect(page.locator('.success')).toBeVisible();
  
  // 4. CLEANUP
  await logout(page);
});
```

---

## 🚀 Pour un Autre LLM / Développeur

### Comment reprendre ce travail :

1. **Lire `SCENARIOS.md`** : Liste complète des scénarios prévus
2. **Regarder les helpers** : `e2e/_setup/helpers.ts` pour réutiliser
3. **Suivre la convention** : Nomenclature des fichiers et dossiers
4. **Tester localement d'abord** : `npm run test:e2e:local`
5. **Ajouter des tests par priorité** : Voir section "Scénarios Prioritaires" dans SCENARIOS.md

### Points d'attention :

- Les tests utilisent **Firefox** par défaut (pas Chromium à cause des dépendances système)
- Les **timeouts** sont à 10s par défaut
- Le **backend doit tourner** avant de lancer les tests (`./scripts/run-local-back_test.sh`)
- Le **frontend doit tourner** aussi (`./scripts/run-local-front_test.sh`)

---

## 📚 Ressources

- [Documentation Playwright](https://playwright.dev/docs/intro)
- [Sélecteurs Playwright](https://playwright.dev/docs/selectors)
- [Assertions](https://playwright.dev/docs/test-assertions)
- [Best Practices](https://playwright.dev/docs/best-practices)

---

## 📝 Changelog

| Date | Auteur | Changement |
|------|--------|------------|
| 2026-03-16 | AI | Création structure E2E avec Playwright |
| 2026-03-16 | AI | Mise en place helpers (login, createInvoice, etc.) |
| 2026-03-16 | AI | Documentation complète (README.md + SCENARIOS.md) |

---

**Questions ?** Consulter la documentation Playwright ou le fichier `SCENARIOS.md` pour voir les scénarios prévus.
