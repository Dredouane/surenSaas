# 🌳 E2E Scenarios - Tree Structure

## Folder Organization

```
e2e/
├── _setup/                    # Shared configuration
│   ├── auth.setup.ts         # Pre-authentication for all tests
│   ├── fixtures.ts           # Reusable test data
│   └── helpers.ts            # Utility functions
│
├── 🚪 01-auth/               # AUTHENTICATION (root)
│   ├── login.spec.ts         # Login
│   ├── signup.spec.ts        # Sign up
│   ├── logout.spec.ts        # Logout
│   └── _flows/
│       └── complete-auth-flow.spec.ts  # Full flow
│
├── 📊 02-dashboard/          # DASHBOARD (home)
│   ├── dashboard.spec.ts     # Overview
│   └── _flows/
│       └── navigation.spec.ts # Main navigation
│
├── 📄 03-invoices/           # INVOICING (key feature)
│   ├── list.spec.ts          # Invoice list
│   ├── create.spec.ts        # Invoice creation
│   ├── detail.spec.ts        # Invoice detail
│   ├── edit.spec.ts          # Invoice editing
│   └── _flows/
│       ├── create-and-validate.spec.ts    # Create + validate
│       ├── upload-via-bot.spec.ts         # Telegram upload
│       └── full-lifecycle.spec.ts         # Full cycle
│
├── 👥 04-clients/            # CLIENT MANAGEMENT
│   ├── list.spec.ts
│   ├── create.spec.ts
│   └── _flows/
│       └── client-with-invoices.spec.ts
│
├── 🤖 05-telegram/           # TELEGRAM INTEGRATION
│   ├── bot-connection.spec.ts
│   └── _flows/
│       └── invoice-upload-flow.spec.ts
│
├── ⚙️ 06-settings/           # SETTINGS
│   └── profile.spec.ts
│
└── 🔄 99-end-to-end/         # COMPLEX SCENARIOS
    ├── conducteur-journey.spec.ts      # Driver journey
    ├── gerant-validation.spec.ts       # Manager journey
    └── comptable-workflow.spec.ts      # Accountant journey
```

## Naming Convention

### Files
```
[action]-[object].spec.ts           # e.g.: create-invoice.spec.ts
[action]-[object]-[context].spec.ts # e.g.: create-invoice-error.spec.ts
```

### Tests (describe/it)
```typescript
// Hierarchical structure
describe('🚪 Auth - Login', () => {           // Module + Feature
  describe('Form', () => {              // Subsection
    test('✅ Valid with correct email', () => {});  // Positive case
    test('❌ Rejects invalid email', () => {});      // Error case
    test('⚡ Quick submission', () => {});          // Perf case
  });
});
```

### Emojis (visual system)
- 🚪 Auth (Authentication)
- 📊 Dashboard (Dashboard)
- 📄 Invoices (Invoices)
- 👥 Clients (Clients)
- 🤖 Telegram (Bot)
- ⚙️ Settings (Settings)
- 🔄 End-to-end (Full scenarios)
- ✅ Success
- ❌ Error
- ⚠️ Warning
- ✨ New
- 🧹 Cleanup

## Evolution Principle

### Add a new branch
```
📁 07-[new-module]/
  ├── [feature].spec.ts
  └── _flows/
      └── [complex-scenario].spec.ts
```

### Add a sub-scenario
```
📁 03-invoices/
  └── _flows/
      └── new-flow.spec.ts   # ← Add here
```

### Granularity levels
1. **Unit** (`*.spec.ts`): Tests an isolated action
2. **Flow** (`_flows/*.spec.ts`): Chain of 2-3 actions
3. **Journey** (`99-end-to-end/*.spec.ts`): Complete business journey

## Test Data (Fixtures)

```typescript
// e2e/_setup/fixtures.ts
export const TEST_DATA = {
  users: {
    admin: { email: 'admin@suren.com', password: '***' },
    conducteur: { email: 'conducteur@suren.com', password: '***' },
    gerant: { email: 'gerant@suren.com', password: '***' },
  },
  invoices: {
    draft: { supplier: 'Test Supplier', amount: 1000 },
    pending: { supplier: 'Supplier A', amount: 2000 },
  }
};
```

## Priority Scenarios (MVP)

### Phase 1 - Core (now)
1. 🚪 Auth: Login / Signup / Logout
2. 📄 Invoices: List / Create / View detail
3. 🤖 Telegram: Upload invoice via bot

### Phase 2 - Business (next week)
4. 🔄 Validation workflow (manager validates invoice)
5. 📄 Complete invoice cycle (creation → validation → archiving)

### Phase 3 - Advanced (later)
6. 👥 Client management linked to invoices
7. 📊 Dashboard with stats
8. ⚙️ User settings

## Example Test Structure

```typescript
// e2e/03-invoices/_flows/create-and-validate.spec.ts
import { test, expect } from '@playwright/test';
import { loginAs } from '../../_setup/helpers';

test.describe('📄 Invoices - Create + Validate Flow', () => {
  
  test('✅ Driver creates, Manager validates', async ({ page }) => {
    // Step 1: Driver login
    await loginAs(page, 'conducteur');
    
    // Step 2: Create invoice
    await page.goto('/dashboard/invoices/create');
    await page.fill('[name=supplier]', 'Test Supplier');
    await page.click('button:has-text("Create")');
    
    // Step 3: Verify "pending" status
    await expect(page.locator('.status')).toHaveText('Pending');
    
    // Step 4: Logout
    await page.click('button:has-text("Logout")');
    
    // Step 5: Manager login
    await loginAs(page, 'gerant');
    
    // Step 6: Validate invoice
    await page.goto('/dashboard/invoices');
    await page.click('text=Test Supplier');
    await page.click('button:has-text("Validate")');
    
    // Step 7: Verify "validated" status
    await expect(page.locator('.status')).toHaveText('Validated');
  });
});
```

This structure allows to:
- ✅ Quickly find a scenario (numbering + emoji)
- ✅ Easily add new modules (07-XX)
- ✅ Understand granularity (file vs _flows vs 99-end-to-end)
- ✅ Reuse helpers and fixtures
- ✅ Maintain consistency over the long term
