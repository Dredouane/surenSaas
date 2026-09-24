# Deployment and Configuration

## Scripts Architecture

### Overview

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   RUN-LOCAL      │ │   RUN-LOCAL      │ │    DEPLOY        │
│    Backend       │ │    Frontend      │ │     GCP          │
│                  │ │                  │ │                  │
│  Localhost:8080  │ │  Localhost:3000  │ │  Cloud Run       │
│                  │ │                  │ │                  │
│ Loads:           │ │ Loads:           │ │ Loads:           │
│ • .env.test      │ │ • .env.test      │ │ • .env.test      │
│ • ~/.bashrc      │ │ • ~/.bashrc      │ │ • ~/.bashrc      │
│   (secrets)      │ │   (GCP URLs)     │ │   (secrets)      │
│                  │ │                  │ │                  │
│ Creates:         │ │ Creates:         │ │ Passes via       │
│ • .env (backend) │ │ • .env.local     │ │ --build-arg:     │
│   dynamically    │ │   dynamically    │ │ • Backend URL    │
│                  │ │ • Removes .next/ │ │ • Org ID/Slug    │
│ Kills port 8080  │ │ Kills port 3000  │ │ • Supabase       │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Available scripts

### 🏃 RUN-LOCAL scripts (Development)

| Script | Description | Backend URL |
|--------|-------------|-------------|
| `run-local-back_test.sh` | Backend only | `localhost:8080` |
| `run-local-front_test.sh` | Frontend only | `localhost:8080` |
| `run-local-front_test-gcp.sh` | Frontend with GCP backend | `$SUREN_TEST_API_BASE_URL` (bashrc) |
| `run-local_test.sh` | Backend + Frontend (2 terminals) | `localhost:8080` |

### 🚀 DEPLOY scripts (Production)

| Script | Description | Target |
|--------|-------------|-------|
| `deploy_back_test.sh` | Backend only | GCP Cloud Run |
| `deploy_front_test.sh` | Frontend only | GCP Cloud Run |

### 🔍 Utility scripts

| Script | Description |
|--------|-------------|
| `check-config.sh` | Checks that everything is configured correctly |

## Required configuration

### 1. `.env.test` file (project root)

```bash
# Organization (NEVER CHANGES)
NEXT_PUBLIC_ORG_ID=<your-org-uuid>
NEXT_PUBLIC_ORG_SLUG=REDACTED_ORG_SLUG

# Supabase (shared)
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=REDACTED_JWT

# GCP
GCP_PROJECT_ID=<your-gcp-project-id>
GCP_REGION=europe-west1
TEST_FRONT_SERVICE_NAME=test-surensaas-front
TEST_BACK_SERVICE_NAME=test-surensaas-back

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Debug
DEBUG=true
```

### 2. `~/.bashrc` file (personal secrets)

```bash
# Supabase backend
export TEST_SUPABASE_SERVICE_KEY="REDACTED_JWT"
export TEST_JWT_SECRET="your-test-jwt-secret"

# GCP URL (for run-local-front_test-gcp.sh)
export SUREN_TEST_API_BASE_URL="https://test-surensaas-back-xxx.run.app"

# Optional
export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN="..."
export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME="..."
export SUREN_GOOGLE_GEMINI_CREDENTIALS_B64="..."
```

### 3. `.gitignore` (IMPORTANT)

```
# Local environment variables
.env.local
surenSaasFront/.env.local

# Next.js cache
surenSaasFront/.next/

# Backend variables
surenSaasBack/.env
```

## Workflows

### Workflow 1: Full local development

```bash
# Terminal 1 - Backend
./scripts/run-local-back_test.sh

# Terminal 2 - Frontend
./scripts/run-local-front_test.sh
```

**What happens:**
- Backend reads `.env.test` + `~/.bashrc` → creates `surenSaasBack/.env`
- Frontend reads `.env.test` → creates `surenSaasFront/.env.local` with `localhost:8080`
- Next.js cache removed before startup
- Existing processes killed automatically

### Workflow 2: Local frontend with GCP backend

```bash
# Make sure SUREN_TEST_API_BASE_URL is up to date in ~/.bashrc
./scripts/run-local-front_test-gcp.sh
```

**What happens:**
- Frontend creates `.env.local` with the GCP URL from `~/.bashrc`
- ⚠️ Cross-origin cookies may not work
- Ideal for testing the UI without starting the local backend

### Workflow 3: Test deployment

```bash
# 1. Check the configuration
./scripts/check-config.sh

# 2. Deploy the backend (first, for CORS)
./scripts/deploy_back_test.sh

# 3. Update the URL in ~/.bashrc if it changed
#    (the script displays the new URL)

# 4. Deploy the frontend
./scripts/deploy_front_test.sh
```

**TEST deployment characteristics:**
- Scale-to-zero (min instances: 0)
- Max 5-10 instances
- Debug mode enabled
- CORS: localhost + GCP frontend URL

## Script details

### `run-local-back_test.sh`

```bash
# Actions:
1. Kills processes on port 8080
2. Loads .env.test
3. Loads ~/.bashrc (secrets)
4. Creates surenSaasBack/.env dynamically
5. Starts uvicorn on localhost:8080
```

**Variables created in `.env`:**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` (from ~/.bashrc)
- `JWT_SECRET` (from ~/.bashrc)
- `ALLOWED_ORIGINS`
- `ENVIRONMENT=test`

### `run-local-front_test.sh`

```bash
# Actions:
1. Kills processes on port 3000
2. Loads .env.test
3. Creates surenSaasFront/.env.local:
   - API_URL=http://localhost:8080
   - NEXT_PUBLIC_ORG_ID/SLUG from .env.test
   - Supabase from .env.test
4. Removes .next/ (cache)
5. Starts Next.js
```

### `run-local-front_test-gcp.sh`

```bash
# Actions:
1. Kills processes on port 3000
2. Loads .env.test
3. Loads ~/.bashrc (SUREN_TEST_API_BASE_URL)
4. Creates .env.local with the GCP URL
5. Removes .next/
6. Starts Next.js
```

### `deploy_back_test.sh`

```bash
# Actions:
1. Loads .env.test
2. Loads ~/.bashrc (secrets)
3. Creates/Updates the GCP secrets:
   - supabase-url
   - test-supabase-service-key
   - test-jwt-secret
   - test-telegram-bot-* (if set)
   - test-google-gemini-* (if set)
4. Pings the frontend to check whether it is reachable
5. Computes CORS (localhost + frontend URL if reachable)
6. Deploys to Cloud Run with:
   - Secrets mounted as env variables
   - Env variables (ORG_ID, DEBUG, etc.)
```

**IMPORTANT:** The backend is deployed with `NEXT_PUBLIC_ORG_ID` (not `TEST_ORG_ID`).

### `deploy_front_test.sh`

```bash
# Actions:
1. Loads .env.test
2. Retrieves the backend URL via gcloud
3. Creates a temporary .env file with the variables for the build:
   - NEXT_PUBLIC_API_URL=<backend_url>
   - NEXT_PUBLIC_ORG_ID/SLUG
   - NEXT_PUBLIC_SUPABASE_* (from .env.test)
4. Deploys to Cloud Run with --set-env-vars (for runtime):
   - API_URL=<backend_url>
   - ENVIRONMENT=test
   - BUILD_ID
5. Deletes the .env file after the build
```

**IMPORTANT:** The `.env` file is created temporarily and copied by the Dockerfile. Next.js reads it automatically at build time to "bake" the variables into the bundle. The file is deleted after deployment.

## Robustness features

### ✅ Conflict handling

- **Occupied ports**: Scripts automatically kill existing processes
- **Parasite cache**: `.next/` removed before each startup
- **Stale variables**: `.env.test` is the single source of truth

### ✅ Security

- **Secrets**: Only in `~/.bashrc`, never version-controlled
- **JWT**: Different secrets between test and prod
- **CORS**: Strict, configured dynamically
- **Organization**: Isolation by `org_id`

### ✅ Consistency

- **Single source**: `.env.test` for all configuration
- **Uniform names**: `NEXT_PUBLIC_ORG_ID/SLUG` everywhere
- **No hardcoded URLs**: In `.env.test`
- **No versioned .env.local**: In `.gitignore`

## Troubleshooting

### Problem: "Port already in use"

```bash
# Solution: The scripts do it automatically, but if needed:
lsof -ti:3000 | xargs kill -9
lsof -ti:8080 | xargs kill -9
```

### Problem: "Env variables not taken into account"

```bash
# Cause: Next.js cache
# Solution: Remove manually
rm -rf surenSaasFront/.next
```

### Problem: "Incorrect backend URL"

```bash
# Check the source:
echo $SUREN_TEST_API_BASE_URL  # For GCP
cat surenSaasFront/.env.local | grep API_URL  # For local
```

### Problem: "Missing secrets"

```bash
# Check ~/.bashrc
env | grep TEST_SUPABASE
env | grep TEST_JWT

# If empty, reload:
source ~/.bashrc
```

## Migrations and Evolution

### If the GCP URL changes

```bash
# 1. Update ~/.bashrc
export SUREN_TEST_API_BASE_URL="https://new-url.run.app"

# 2. Reload
source ~/.bashrc

# 3. No need to modify .env.test (no URLs in it)
```

### If the organization changes

```bash
# 1. Modify .env.test
NEXT_PUBLIC_ORG_ID=new-uuid
NEXT_PUBLIC_ORG_SLUG=new-slug

# 2. Commit + Push
git add .env.test
git commit -m "Organization change"

# 3. Restart all services (they read .env.test every time)
```

## Useful commands

```bash
# Check the configuration
./scripts/check-config.sh

# View GCP logs
gcloud logging tail --service=test-surensaas-back
gcloud logging tail --service=test-surensaas-front

# Restart a service
./scripts/run-local-back_test.sh  # or front

# View loaded variables
env | grep NEXT_PUBLIC
env | grep TEST_
```

## Summary of critical files

### Version-controlled (Git)
- `.env.test`: Organization and Supabase configuration
- `scripts/*.sh`: Automated scripts
- `.gitignore`: Ignores .env.local and cache

### Not version-controlled (Local)
- `~/.bashrc`: Secrets and GCP URLs
- `surenSaasBack/.env`: Created dynamically
- `surenSaasFront/.env.local`: Created dynamically
- `surenSaasFront/.next/`: Cache (removed every time)

---

**Last updated:** 2024-03-23
**Architecture:** Single source of truth (.env.test) + External secrets (~/.bashrc)
