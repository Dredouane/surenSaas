# SurenSaaS

SaaS multi-PME (construction, nettoyage, diagnostic énergétique) avec architecture moderne.

## Architecture

- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python) + Supabase
- **Base de données**: PostgreSQL (Supabase) - partagée entre test et prod
- **Auth**: Email + Password avec pré-autorisation
- **Déploiement**: GCP Cloud Run (2 environnements: TEST + PROD)

## Stratégie Test/Production

Ce projet utilise **2 environnements distincts** sur la même base de données:

- **TEST** : Pour développer et tester les nouvelles fonctionnalités
- **PROD** : L'environnement de production stable

Chaque environnement a ses propres URLs Cloud Run mais partage la DB Supabase (isolation par `org_id`).

## Quick Start

### 1. Configuration initiale

```bash
# Vérifier que tout est configuré
./scripts/check-config.sh
```

### 2. Configuration des secrets

```bash
# Ajouter dans ~/.bashrc :
export TEST_SUPABASE_SERVICE_KEY="votre-clé-supabase"
export TEST_JWT_SECRET="votre-secret-jwt"
export SUREN_TEST_API_BASE_URL="https://test-surensaas-back-xxx.run.app"

# Recharger
source ~/.bashrc
```

### 3. Démarrer en local

```bash
# Backend (Terminal 1)
./scripts/run-local-back_test.sh

# Frontend (Terminal 2)
./scripts/run-local-front_test.sh

# Frontend: http://localhost:3000
# Backend: http://localhost:8080
```

## Déploiement GCP

### Configuration préalable

1. **Créer un projet GCP** et activer Cloud Run + Secret Manager
2. **Créer un projet Supabase** avec l'organisation
3. **Remplir `.env.test`** avec vos valeurs (organisation, Supabase)
4. **Ajouter les secrets dans `~/.bashrc`** (clés Supabase, JWT)

### Développement Local

```bash
# Vérifier la configuration
./scripts/check-config.sh

# Lancer backend + frontend
./scripts/run-local_test.sh
```

### Déployer TEST

```bash
# 1. Déployer le backend (crée les secrets GCP)
./scripts/deploy_back_test.sh

# 2. Mettre à jour l'URL dans ~/.bashrc si elle a changé

# 3. Déployer le frontend
./scripts/deploy_front_test.sh
```

### Scripts disponibles

| Script | Description |
|--------|-------------|
| `./scripts/check-config.sh` | Vérifie que tout est configuré |
| `./scripts/run-local-back_test.sh` | Backend local (localhost:8080) |
| `./scripts/run-local-front_test.sh` | Frontend local (localhost:3000) |
| `./scripts/run-local-front_test-gcp.sh` | Frontend local + backend GCP |
| `./scripts/deploy_back_test.sh` | Déploie backend sur GCP |
| `./scripts/deploy_front_test.sh` | Déploie frontend sur GCP |

📖 **Documentation complète** : Voir `docs/DEPLOYMENT.md`

## Structure du projet

```
.
├── docs/                       # Documentation technique
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md          # Guide déploiement test/prod
│   └── ...
├── db/                         # Scripts SQL
│   ├── schema/                # Tables (auth, orgs...)
│   └── policies/              # RLS policies
├── openapi/                    # Contrat API (racine projet)
│   └── api.yaml
├── scripts/                    # Scripts utilitaires
│   ├── check-config.sh        # Vérifie la configuration
│   ├── run-local-back_test.sh # Backend local
│   ├── run-local-front_test.sh # Frontend local
│   ├── run-local-front_test-gcp.sh # Frontend + GCP
│   ├── deploy_back_test.sh    # Deploy back TEST
│   └── deploy_front_test.sh   # Deploy front TEST
├── surenSaasFront/             # Next.js frontend
│   ├── Dockerfile
│   └── ...
└── surenSaasBack/              # FastAPI backend
    ├── Dockerfile
    └── ...
```

## Workflow de développement

### Nouvelle fonctionnalité

```bash
# 1. Vérifier la configuration
./scripts/check-config.sh

# 2. Développer en local (2 terminaux)
./scripts/run-local-back_test.sh    # Terminal 1
./scripts/run-local-front_test.sh   # Terminal 2

# 3. Déployer sur TEST
./scripts/deploy_back_test.sh
./scripts/deploy_front_test.sh

# 4. Tester sur l'URL de test
```

### Développement avec backend GCP

```bash
# Si vous voulez tester le frontend avec le backend déployé :
./scripts/run-local-front_test-gcp.sh
```

### Mise en production

```bash
# 1. Vérifier la config
./scripts/check-config.sh

# 2. Déployer (confirmation requise)
./scripts/deploy_back_prod.sh
./scripts/deploy_front_prod.sh

# 3. Surveiller les logs
gcloud logging tail --service=surensaas-front
gcloud logging tail --service=surensaas-back
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Déploiement Test/Prod](docs/DEPLOYMENT.md) ⭐ Important!
- [Frontend](docs/FRONTEND.md)
- [Backend](docs/BACKEND.md)
- [Authentication](docs/AUTHENTICATION.md)
- [Base de données](docs/DATABASE.md)

## Développement local

### Frontend seul

```bash
cd surenSaasFront
npm install
npm run dev
```

### Backend seul

```bash
cd surenSaasBack
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Commandes utiles

```bash
# Vérifier la configuration
./scripts/check-config.sh

# Logs en temps réel
gcloud logging tail --service=test-surensaas-front

# Lister les services déployés
gcloud run services list

# Ouvrir l'URL dans le navigateur
gcloud run services describe test-surensaas-front --format 'value(status.url)' | xargs xdg-open
```
