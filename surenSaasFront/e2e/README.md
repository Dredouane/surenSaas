# E2E Documentation - SurenSaaS

## 🎯 Purpose

This E2E (End-to-End) test suite tests the **complete user journeys** of the SurenSaaS application by simulating real interactions with the browser.

### What is tested:
- ✅ Authentication flow (login/signup/logout)
- ✅ Invoice creation and management
- ✅ Invoice upload via Telegram
- ✅ Complete business workflows (driver → manager → accountant)

### What is NOT tested here:
- ❌ Unit tests (see `surenSaasBack/tests/`)
- ❌ API integration tests (see `surenSaasBack/tests/`)
- ❌ Performance tests (to be added later)

---

## 🛠️ Tech Stack

| Tool | Version | Usage |
|-------|---------|-------|
| **Playwright** | ^1.58.2 | E2E framework (automated browser) |
| **@playwright/test** | ^1.58.2 | Test runner |
| **Firefox** | Latest | Default browser (Chromium has too many system dependencies) |

### Why Playwright?
- **Multi-browser**: Chrome, Firefox, Safari
- **Auto-waiting**: Automatically waits for elements
- **Screenshots/Videos**: Automatic capture on failure
- **Trace viewer**: Interactive debugging
- **Parallelization**: Fast tests

---

## 📁 Folder Structure

```
e2e/
├── _setup/                    # ⚙️ Shared configuration
│   ├── helpers.ts            # Utility functions (login, createInvoice, etc.)
│   ├── fixtures.ts           # Test data (emails, passwords)
│   └── auth.setup.ts         # Pre-authentication (optional)
│
├── 01-auth/                   # 🚪 Authentication
│   ├── login.spec.ts         # Login
│   ├── signup.spec.ts        # Sign up
│   ├── logout.spec.ts        # Logout
│   └── _flows/
│       └── complete-auth-flow.spec.ts
│
├── 02-dashboard/              # 📊 Dashboard
│   ├── dashboard.spec.ts
│   └── _flows/
│       └── navigation.spec.ts
│
├── 03-invoices/               # 📄 Invoices (key feature)
│   ├── list.spec.ts
│   ├── create.spec.ts
│   ├── detail.spec.ts
│   └── _flows/
│       ├── create-and-validate.spec.ts
│       └── upload-via-bot.spec.ts
│
├── 04-clients/                # 👥 Client management
├── 05-telegram/               # 🤖 Telegram integration
├── 06-settings/               # ⚙️ Settings
├── 99-end-to-end/             # 🔄 Complex business scenarios
│
├── SCENARIOS.md              # 📋 Scenario documentation
└── README.md                 # 📖 This file
```

### Naming convention:
- **Folders**: `XX-feature-name/` (numbering for logical order)
- **Files**: `[action]-[object].spec.ts`
- **Emojis**: Each module has an emoji (🚪 Auth, 📄 Invoices, etc.)

---

## 🚀 Commands

```bash
# From surenSaasFront/

# Run all tests
npm run test:e2e

# Tests in local (localhost:3000)
npm run test:e2e:local

# Tests on TEST environment
npm run test:e2e:test

# Interactive mode (UI)
npm run test:e2e:ui

# Debug mode (step-by-step)
npm run test:e2e:debug

# View the HTML report
npm run test:e2e:report

# Run a specific file
npx playwright test e2e/01-auth/login.spec.ts

# Run headed (see the browser)
npx playwright test --headed
```

---

## ⚙️ Configuration

### Environments

3 supported environments (defined in `playwright.config.ts`):

| Environment | Frontend URL | Backend URL | Command |
|---------------|--------------|-------------|----------|
| **local** | http://localhost:3000 | http://localhost:8080 | `npm run test:e2e:local` |
| **test** | TEST URL | TEST API URL | `npm run test:e2e:test` |
| **prod** | PROD URL | PROD API URL | `npm run test:e2e:prod` |

### Environment variables

Create a `.env.local` file at the root of `surenSaasFront/`:

```bash
# URLs
TEST_FRONTEND_URL=https://test-surensaas.example.com
TEST_API_URL=https://test-api.example.com

# Test credentials
TEST_ADMIN_EMAIL=admin@test.com
TEST_ADMIN_PASSWORD=password123
TEST_CONDUCTEUR_EMAIL=conducteur@test.com
TEST_CONDUCTEUR_PASSWORD=password123
```

---

## 🧪 Writing a New Test

### 1. Simple test (unit)

```typescript
// e2e/01-auth/login.spec.ts
import { test, expect } from '@playwright/test';

test('✅ Login with valid email', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'test@example.com');
  await page.click('button:has-text("Continue")');
  
  await expect(page).toHaveURL(/.*password.*/);
});
```

### 2. Test using the helpers

```typescript
// e2e/03-invoices/create.spec.ts
import { test, expect } from '@playwright/test';
import { loginAs, createInvoice } from '../_setup/helpers';

test('✅ Driver creates an invoice', async ({ page }) => {
  // Use the helper to login
  await loginAs(page, 'conducteur');
  
  // Use the helper to create an invoice
  const invoiceId = await createInvoice(page, {
    supplier: 'Test Supplier',
    amount: 1000,
    description: 'E2E Test'
  });
  
  // Verify
  await expect(page.locator('.status')).toHaveText('Pending');
});
```

### 3. Flow test (complete workflow)

```typescript
// e2e/03-invoices/_flows/create-and-validate.spec.ts
import { test, expect } from '@playwright/test';
import { loginAs, logout } from '../../_setup/helpers';

test('🔄 Driver creates → Manager validates', async ({ page }) => {
  // Step 1: Driver login
  await loginAs(page, 'conducteur');
  
  // Step 2: Create invoice
  await page.goto('/dashboard/invoices/create');
  await page.fill('[name="supplier"]', 'Test Supplier');
  await page.click('button:has-text("Create")');
  
  // Step 3: Verify status
  await expect(page.locator('.status')).toHaveText('Pending');
  
  // Step 4: Logout
  await logout(page);
  
  // Step 5: Manager login
  await loginAs(page, 'gerant');
  
  // Step 6: Validate
  await page.goto('/dashboard/invoices');
  await page.click('text=Test Supplier');
  await page.click('button:has-text("Validate")');
  
  // Step 7: Verify
  await expect(page.locator('.status')).toHaveText('Validated');
});
```

---

## 🔧 Available Helpers

### `helpers.ts`

| Function | Description | Example |
|----------|-------------|---------|
| `loginAs(page, role)` | Logs in a user by role | `await loginAs(page, 'admin')` |
| `logout(page)` | Logout | `await logout(page)` |
| `createInvoice(page, data)` | Creates an invoice | `await createInvoice(page, {supplier: 'Test', amount: 1000})` |
| `generateTestEmail(prefix)` | Generates unique email | `generateTestEmail('test')` |
| `waitForElement(page, selector)` | Waits for an element | `await waitForElement(page, 'text=Success')` |
| `screenshot(page, name)` | Screenshot | `await screenshot(page, 'error')` |

### Available roles

- `admin`: Administrator (all rights)
- `conducteur`: Creates invoices via Telegram
- `gerant`: Validates/rejects invoices
- `comptable`: Views validated invoices

---

## 🐛 Debugging

### 1. View the HTML report

```bash
npm run test:e2e:report
```

The report contains:
- Screenshots on failure
- Test videos
- Detailed traces (clicks, navigations)

### 2. UI mode (interactive)

```bash
npm run test:e2e:ui
```

Graphical interface to:
- Run tests one by one
- View traces in real time
- Inspect elements

### 3. Debug mode (step-by-step)

```bash
npm run test:e2e:debug
```

The test pauses at each line for inspection.

### 4. Manual screenshots

```typescript
// In a test
await page.screenshot({ path: 'debug.png', fullPage: true });
```

---

## 📊 Best Practices

### ✅ DO

- Use the **helpers** to avoid duplication
- Wait for **elements** before interacting (`waitForSelector`)
- Use **robust selectors** (visible text, role) not CSS classes
- **Clean up** test data at the end of the test
- Add **logs** (`console.log`) to follow the execution

### ❌ AVOID

- Waiting for **fixed times** (`waitForTimeout(1000)`)
- Using **fragile selectors** (`.btn-primary`, `#id-123`)
- Testing **implementation details** (exact HTML structure)
- Forgetting to **handle errors** (try/catch on critical actions)

---

## 🔄 Test Life Cycle

```
Setup → Action → Assertion → Cleanup
  ↓       ↓          ↓          ↓
Login   Fill      Verify     Logout
        form      result     DB Cleanup
```

### Full example:

```typescript
import { test } from '@playwright/test';
import { loginAs, logout, generateTestEmail } from './_setup/helpers';

test('✅ Create an invoice', async ({ page }) => {
  // 1. SETUP
  const testEmail = generateTestEmail('invoice');
  await loginAs(page, 'conducteur');
  
  // 2. ACTION
  await page.goto('/dashboard/invoices/create');
  await page.fill('[name="supplier"]', 'Test Supplier');
  await page.fill('[name="amount"]', '1000');
  await page.click('button:has-text("Create")');
  
  // 3. ASSERTION
  await expect(page).toHaveURL(/.*invoices.*/);
  await expect(page.locator('.success')).toBeVisible();
  
  // 4. CLEANUP
  await logout(page);
});
```

---

## 🚀 For Another LLM / Developer

### How to resume this work:

1. **Read `SCENARIOS.md`**: Complete list of planned scenarios
2. **Look at the helpers**: `e2e/_setup/helpers.ts` to reuse
3. **Follow the convention**: File and folder naming
4. **Test locally first**: `npm run test:e2e:local`
5. **Add tests by priority**: See "Priority Scenarios" section in SCENARIOS.md

### Points of attention:

- Tests use **Firefox** by default (not Chromium because of system dependencies)
- **Timeouts** are 10s by default
- The **backend must be running** before running the tests (`./scripts/run-local-back_test.sh`)
- The **frontend must also be running** (`./scripts/run-local-front_test.sh`)

---

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Playwright Selectors](https://playwright.dev/docs/selectors)
- [Assertions](https://playwright.dev/docs/test-assertions)
- [Best Practices](https://playwright.dev/docs/best-practices)

---

## 📝 Changelog

| Date | Author | Change |
|------|--------|------------|
| 2026-03-16 | AI | Created E2E structure with Playwright |
| 2026-03-16 | AI | Set up helpers (login, createInvoice, etc.) |
| 2026-03-16 | AI | Complete documentation (README.md + SCENARIOS.md) |

---

**Questions?** Consult the Playwright documentation or the `SCENARIOS.md` file to see the planned scenarios.
