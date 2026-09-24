# SurenSaaS Architecture

## Overview
Multi-SME SaaS (construction, cleaning, energy diagnostics) with front/back separation on GCP Cloud Run.

## Data flow
```
Client → Cloud Run Front (Next.js) → Cloud Run Back (FastAPI) → Supabase Postgres
                ↓                           ↓
          Auth Microsoft Entra         JWT Validation
          CSS Dynamic Theme          RLS policies
```

## Key principles
- **Local = Prod**: Docker Compose reproduces the Cloud Run environment
- **Multi-tenancy**: Routing by org `/[org]/...` on front and back
- **Contract-first**: OpenAPI generates the backend controllers
- **No Edge Functions**: Direct Supabase REST

## Services

| Service | Tech | Deployment | Scale |
|---------|------|-------------|-------|
| Frontend | Next.js 14 + App Router | Cloud Run | Always-on |
| Backend | FastAPI Python | Cloud Run | Scale-to-zero |
| Database | Supabase Postgres | Supabase Cloud | - |

## Points of attention
1. **Version force-reload**: build_id check on the front side
2. **Images unoptimized**: Next.js config for Cloud Run
3. **Strict CORS**: origin whitelist (front + Telegram bots)
4. **Secrets**: GCP Secret Manager only

## Critical environment variables
```bash
# Front
API_URL=https://back-xxx.run.app
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# Back
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ALLOWED_ORIGINS=front-url,telegram-bot-urls
```
