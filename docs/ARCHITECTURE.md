# Architecture SurenSaaS

## Vue d'ensemble
SaaS multi-PME (construction, nettoyage, diagnostic énergétique) avec séparation front/back sur GCP Cloud Run.

## Flux de données
```
Client → Cloud Run Front (Next.js) → Cloud Run Back (FastAPI) → Supabase Postgres
                ↓                           ↓
         Auth Microsoft Entra         JWT Validation
         Theme dynamique CSS          RLS policies
```

## Principes clés
- **Local = Prod** : Docker Compose reproduit l'environnement Cloud Run
- **Multi-tenancy** : Routing par org `/[org]/...` au front et back
- **Contract-first** : OpenAPI génère les contrôleurs backend
- **No Edge Functions** : REST Supabase direct

## Services

| Service | Tech | Déploiement | Scale |
|---------|------|-------------|-------|
| Frontend | Next.js 14 + App Router | Cloud Run | Always-on |
| Backend | FastAPI Python | Cloud Run | Scale-to-zero |
| Database | Supabase Postgres | Supabase Cloud | - |

## Points d'attention
1. **Version force-reload** : build_id check côté front
2. **Images unoptimized** : config Next.js pour Cloud Run
3. **CORS strict** : whitelist origines (front + bots Telegram)
4. **Secrets** : GCP Secret Manager uniquement

## Variables d'environnement critiques
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
