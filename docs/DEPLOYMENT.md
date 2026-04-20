# Déploiement et Configuration

## Architecture des Scripts

### Vue d'ensemble

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   RUN-LOCAL      │ │   RUN-LOCAL      │ │    DEPLOY        │
│    Backend       │ │    Frontend      │ │     GCP          │
│                  │ │                  │ │                  │
│  Localhost:8080  │ │  Localhost:3000  │ │  Cloud Run       │
│                  │ │                  │ │                  │
│ Charge:          │ │ Charge:          │ │ Charge:          │
│ • .env.test      │ │ • .env.test      │ │ • .env.test      │
│ • ~/.bashrc      │ │ • ~/.bashrc      │ │ • ~/.bashrc      │
│   (secrets)      │ │   (URLs GCP)     │ │   (secrets)      │
│                  │ │                  │ │                  │
│ Crée:            │ │ Crée:            │ │ Passe via        │
│ • .env (backend) │ │ • .env.local     │ │ --build-arg:     │
│   dynamique      │ │   dynamique      │ │ • URL backend    │
│                  │ │ • Supprime .next/│ │ • Org ID/Slug    │
│ Tue port 8080    │ │ Tue port 3000    │ │ • Supabase       │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Scripts disponibles

### 🏃 Scripts RUN-LOCAL (Développement)

| Script | Description | Backend URL |
|--------|-------------|-------------|
| `run-local-back_test.sh` | Backend uniquement | `localhost:8080` |
| `run-local-front_test.sh` | Frontend uniquement | `localhost:8080` |
| `run-local-front_test-gcp.sh` | Frontend avec backend GCP | `$SUREN_TEST_API_BASE_URL` (bashrc) |
| `run-local_test.sh` | Backend + Frontend (2 terminaux) | `localhost:8080` |

### 🚀 Scripts DEPLOY (Production)

| Script | Description | Cible |
|--------|-------------|-------|
| `deploy_back_test.sh` | Backend uniquement | GCP Cloud Run |
| `deploy_front_test.sh` | Frontend uniquement | GCP Cloud Run |

### 🔍 Scripts utilitaires

| Script | Description |
|--------|-------------|
| `check-config.sh` | Vérifie que tout est configuré correctement |

## Configuration requise

### 1. Fichier `.env.test` (racine du projet)

```bash
# Organisation (NE CHANGE JAMAIS)
NEXT_PUBLIC_ORG_ID=REDACTEDORG
NEXT_PUBLIC_ORG_SLUG=REDACTED_ORG_SLUG


# GCP
GCP_PROJECT_ID=suren-saas
GCP_REGION=europe-west1
TEST_FRONT_SERVICE_NAME=test-surensaas-front
TEST_BACK_SERVICE_NAME=test-surensaas-back

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Debug
DEBUG=true
```

### 2. Fichier `~/.bashrc` (secrets personnels)

```bash
# Backend Supabase
export TEST_SUPABASE_SERVICE_KEY="REDACTED_JWT"
export TEST_JWT_SECRET="votre-secret-jwt-test"

# URL GCP (pour run-local-front_test-gcp.sh)
export SUREN_TEST_API_BASE_URL="https://test-surensaas-back-xxx.run.app"

# Optionnels
export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN="..."
export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME="..."
export SUREN_GOOGLE_GEMINI_CREDENTIALS_B64="..."
```

### 3. `.gitignore` (IMPORTANT)

```
# Variables d'environnement locales
.env.local
surenSaasFront/.env.local

# Cache Next.js
surenSaasFront/.next/

# Variables backend
surenSaasBack/.env
```

## Workflows

### Workflow 1 : Développement complet en local

```bash
# Terminal 1 - Backend
./scripts/run-local-back_test.sh

# Terminal 2 - Frontend
./scripts/run-local-front_test.sh
```

**Ce qui se passe :**
- Backend lit `.env.test` + `~/.bashrc` → crée `surenSaasBack/.env`
- Frontend lit `.env.test` → crée `surenSaasFront/.env.local` avec `localhost:8080`
- Cache Next.js supprimé avant démarrage
- Processus existants tués automatiquement

### Workflow 2 : Frontend local avec backend GCP

```bash
# Assurez-vous que SUREN_TEST_API_BASE_URL est à jour dans ~/.bashrc
./scripts/run-local-front_test-gcp.sh
```

**Ce qui se passe :**
- Frontend crée `.env.local` avec l'URL GCP depuis `~/.bashrc`
- ⚠️ Cookies cross-origin peuvent ne pas fonctionner
- Idéal pour tester l'UI sans démarrer le backend local

### Workflow 3 : Déploiement Test

```bash
# 1. Vérifier la configuration
./scripts/check-config.sh

# 2. Déployer le backend (d'abord pour CORS)
./scripts/deploy_back_test.sh

# 3. Mettre à jour l'URL dans ~/.bashrc si elle a changé
#    (le script affiche la nouvelle URL)

# 4. Déployer le frontend
./scripts/deploy_front_test.sh
```

**Caractéristiques du déploiement TEST :**
- Scale-to-zero (min instances: 0)
- Max 5-10 instances
- Debug mode activé
- CORS: localhost + URL frontend GCP

## Détails des scripts

### `run-local-back_test.sh`

```bash
# Actions :
1. Tue les processus sur le port 8080
2. Charge .env.test
3. Charge ~/.bashrc (secrets)
4. Crée surenSaasBack/.env dynamiquement
5. Démarre uvicorn sur localhost:8080
```

**Variables créées dans `.env` :**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` (depuis ~/.bashrc)
- `JWT_SECRET` (depuis ~/.bashrc)
- `ALLOWED_ORIGINS`
- `ENVIRONMENT=test`

### `run-local-front_test.sh`

```bash
# Actions :
1. Tue les processus sur le port 3000
2. Charge .env.test
3. Crée surenSaasFront/.env.local :
   - API_URL=http://localhost:8080
   - NEXT_PUBLIC_ORG_ID/SLUG depuis .env.test
   - Supabase depuis .env.test
4. Supprime .next/ (cache)
5. Démarre Next.js
```

### `run-local-front_test-gcp.sh`

```bash
# Actions :
1. Tue les processus sur le port 3000
2. Charge .env.test
3. Charge ~/.bashrc (SUREN_TEST_API_BASE_URL)
4. Crée .env.local avec l'URL GCP
5. Supprime .next/
6. Démarre Next.js
```

### `deploy_back_test.sh`

```bash
# Actions :
1. Charge .env.test
2. Charge ~/.bashrc (secrets)
3. Crée/Met à jour les secrets GCP :
   - supabase-url
   - test-supabase-service-key
   - test-jwt-secret
   - test-telegram-bot-* (si défini)
   - test-google-gemini-* (si défini)
4. Ping le frontend pour vérifier s'il est accessible
5. Calcule les CORS (localhost + URL frontend si accessible)
6. Déploie sur Cloud Run avec :
   - Secrets montés comme variables d'env
   - Variables d'env (ORG_ID, DEBUG, etc.)
```

**IMPORTANT :** Le backend est déployé avec `NEXT_PUBLIC_ORG_ID` (pas `TEST_ORG_ID`).

### `deploy_front_test.sh`

```bash
# Actions :
1. Charge .env.test
2. Récupère l'URL du backend via gcloud
3. Crée un fichier .env temporaire avec les variables pour le build :
   - NEXT_PUBLIC_API_URL=<url_backend>
   - NEXT_PUBLIC_ORG_ID/SLUG
   - NEXT_PUBLIC_SUPABASE_* (depuis .env.test)
4. Déploie sur Cloud Run avec --set-env-vars (pour le runtime) :
   - API_URL=<url_backend>
   - ENVIRONMENT=test
   - BUILD_ID
5. Supprime le fichier .env après le build
```

**IMPORTANT :** Le fichier `.env` est créé temporairement et copié par le Dockerfile. Next.js le lit automatiquement au build time pour "baker" les variables dans le bundle. Le fichier est supprimé après le déploiement.

## Caractéristiques de robustesse

### ✅ Gestion des conflits

- **Ports occupés** : Scripts tuent automatiquement les processus existants
- **Cache parasite** : `.next/` supprimé avant chaque démarrage
- **Variables obsolètes** : `.env.test` est la seule source de vérité

### ✅ Sécurité

- **Secrets** : Uniquement dans `~/.bashrc`, jamais versionnés
- **JWT** : Secrets différents entre test et prod
- **CORS** : Strict, configuré dynamiquement
- **Organisation** : Isolation par `org_id`

### ✅ Cohérence

- **Une seule source** : `.env.test` pour toute la configuration
- **Noms uniformes** : `NEXT_PUBLIC_ORG_ID/SLUG` partout
- **Pas d'URLs hardcodées** : Dans `.env.test`
- **Pas de .env.local versionné** : Dans `.gitignore`

## Dépannage

### Problème : "Port déjà utilisé"

```bash
# Solution : Les scripts le font automatiquement, mais si besoin :
lsof -ti:3000 | xargs kill -9
lsof -ti:8080 | xargs kill -9
```

### Problème : "Variables d'env pas prises en compte"

```bash
# Cause : Cache Next.js
# Solution : Supprimer manuellement
rm -rf surenSaasFront/.next
```

### Problème : "URL backend incorrecte"

```bash
# Vérifier la source :
echo $SUREN_TEST_API_BASE_URL  # Pour GCP
cat surenSaasFront/.env.local | grep API_URL  # Pour local
```

### Problème : "Secrets manquants"

```bash
# Vérifier ~/.bashrc
env | grep TEST_SUPABASE
env | grep TEST_JWT

# Si vide, recharger :
source ~/.bashrc
```

## Migrations et Évolutions

### Si l'URL GCP change

```bash
# 1. Mettre à jour ~/.bashrc
export SUREN_TEST_API_BASE_URL="https://nouvelle-url.run.app"

# 2. Recharger
source ~/.bashrc

# 3. Pas besoin de modifier .env.test (pas d'URLs dedans)
```

### Si l'organisation change

```bash
# 1. Modifier .env.test
NEXT_PUBLIC_ORG_ID=nouvel-uuid
NEXT_PUBLIC_ORG_SLUG=nouveau-slug

# 2. Commit + Push
git add .env.test
git commit -m "Changement d'organisation"

# 3. Redémarrer tous les services (ils lisent .env.test à chaque fois)
```

## Commandes utiles

```bash
# Vérifier la configuration
./scripts/check-config.sh

# Voir les logs GCP
gcloud logging tail --service=test-surensaas-back
gcloud logging tail --service=test-surensaas-front

# Redémarrer un service
./scripts/run-local-back_test.sh  # ou front

# Voir les variables chargées
env | grep NEXT_PUBLIC
env | grep TEST_
```

## Résumé des fichiers critiques

### Versionnés (Git)
- `.env.test` : Configuration organisation et Supabase
- `scripts/*.sh` : Scripts automatisés
- `.gitignore` : Ignore .env.local et cache

### Non versionnés (Local)
- `~/.bashrc` : Secrets et URLs GCP
- `surenSaasBack/.env` : Créé dynamiquement
- `surenSaasFront/.env.local` : Créé dynamiquement
- `surenSaasFront/.next/` : Cache (supprimé à chaque fois)

---

**Dernière mise à jour :** 2024-03-23
**Architecture :** Source de vérité unique (.env.test) + Secrets externes (~/.bashrc)
