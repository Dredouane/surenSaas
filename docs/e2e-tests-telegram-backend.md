# Tests E2E Telegram ↔ Backend — Architecture

> **Statut :** Plan d'architecture validé  
> **Dernière mise à jour :** Avril 2026

## Objectif

Créer un orchestrateur de tests E2E local capable de piloter un **Shadow Bot Telegram** (via un compte utilisateur simulé avec Telethon) et de valider les impacts en base de données Supabase. Ce sous-projet sert de fondation pour du développement en TDD.

---

## Structure du sous-projet

```
surenSaasBack/
├── tests_e2e/                         # Nouveau dossier — tests E2E Telegram
│   ├── __init__.py
│   ├── conftest.py                    # Fixtures globales E2E (org_id, company, supabase, bot)
│   ├── docker-compose.e2e.yml         # Services : backend-saas + telegram-bot-api
│   ├── run_e2e_tests.sh               # Orchestrateur : docker up → wait → pytest → docker down
│   ├── requirements-e2e.txt           # Dépendances additionnelles (telethon, etc.)
│   │
│   ├── fixtures/                      # Documents uploadés pendant les tests
│   │   ├── CCTP-ESSET-Rue-Thenard.pdf  # Template : upload CCTP → validation DB
│   │   └── .gitkeep
│   │
│   ├── sim/                           # Simulateurs d'interactions
│   │   ├── __init__.py
│   │   └── telegram_user_sim.py       # TelegramUserSim (Telethon)
│   │
│   ├── validators/                    # Frameworks de validation
│   │   ├── __init__.py
│   │   └── db_validator.py            # DBValidator (interroge Supabase)
│   │
│   └── tests/                         # Scénarios de test pytest
│       ├── __init__.py
│       └── test_cctp_upload.py        # Template : upload CCTP
│
├── tests/                             # Tests existants (inchangé)
│   ├── test_telegram_construction_bot.py
│   └── ...
```

---

## 1. Orchestration Docker-Compose (`docker-compose.e2e.yml`)

| Service | Image | Rôle |
|---------|-------|------|
| `backend-saas` | build `./surenSaasBack` | API FastAPI, healthcheck `/health` |
| `telegram-bot-api` | `aiogram/telegram-bot-api:latest` | Serveur Telegram local, port 8081 |

Le `telegram-bot-api` est initialisé avec le token du bot E2E via la variable `TELEGRAM_TOKEN`.  
Le backend est configuré pour pointer vers `http://telegram-bot-api:8081/bot{TOKEN}` au lieu de `https://api.telegram.org`.

---

## 2. Script d'orchestration (`run_e2e_tests.sh`)

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐     ┌──────────────┐
│ docker      │ ──→ │ Wait for     │ ──→ │ pytest   │ ──→ │ docker       │
│ compose up  │     │ healthcheck  │     │ tests_e2e│     │ compose down │
│ -d          │     │ (curl)       │     │ -v       │     │ -v           │
└─────────────┘     └──────────────┘     └──────────┘     └──────────────┘
```

Étapes :
1. `docker compose -f docker-compose.e2e.yml up -d`
2. Polling des healthchecks (backend `/health`, telegram-bot-api `/ping`)
3. Création/réinitialisation du webhook du bot via l'API locale
4. Activation du venv + `pip install -r requirements-e2e.txt`
5. `pytest tests_e2e/ -v`
6. `docker compose -f docker-compose.e2e.yml down -v` (cleanup idempotent)
7. Exit avec le code du pytest

---

## 3. Simulateur Telegram (`TelegramUserSim`)

Classe Python basée sur **Telethon** (MTProto) pour agir comme un vrai utilisateur Telegram.

```python
class TelegramUserSim:
    async def send_text(self, msg: str) -> Message         # Envoie un message texte
    async def click_button(self, label: str) -> Message    # Clique sur un inline keyboard
    async def upload_file(self, path: str | Path) -> Message  # Upload d'un fichier (PDF/photo)
    async def send_voice(self, path: str | Path) -> Message   # Envoie un message vocal
    async def wait_for_bot_response(self, timeout: int = 10) -> Message  # Attend la réponse du bot
```

Configuration via variables d'environnement :
- `SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN` — token du bot E2E
- `SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_URL` — URL de l'API Telegram (locale ou officielle)

---

## 4. Validateur base de données (`DBValidator`)

Utilitaire qui interroge Supabase via `get_supabase()` (même client que le backend).

```python
class DBValidator:
    def assert_operation_created(
        self, org_id: str, source: str, since: datetime | None = None
    ) -> dict
    # Vérifie qu'une ligne est apparue dans chantier_operations_htl
    # avec le org_id et la source donnés, depuis le timestamp `since`.
    # Retourne la ligne trouvée pour assertions supplémentaires.

    def assert_document_created(
        self, org_id: str, candidature_id: str | None = None
    ) -> dict
    # Vérifie qu'un document a été créé dans ao_documents.
```

Tables cibles pour la validation :

| Sous-domaine | Table | Statut initial attendu |
|---|---|---|
| Opérations | `chantier_operations_htl` | `en_attente` |
| Dépenses | `chantier_depenses` | — |
| Situations | `chantier_situations` | — |
| Tâches | `chantier_taches` | `en_attente` |
| Pointages | `chantier_pointages` | — |

---

## 5. Données de test et configuration

### Constantes partagées (dans `conftest.py`)

```python
TEST_ORG_SLUG = "REDACTED_ORG_SLUG"      # NEXT_PUBLIC_ORG_SLUG du .env.test
TEST_COMPANY_SLUG = "construction"

# Résolus dynamiquement depuis Supabase au moment du conftest
TEST_ORG_ID = "<résolu depuis organizations.slug>"
TEST_COMPANY_ID = "<résolu depuis companies.slug>"
```

### Fixtures

```python
@pytest.fixture(scope="session")
def org_id() -> str               # Résout TEST_ORG_ID depuis la DB

@pytest.fixture(scope="session")
def company_id() -> str           # Résout TEST_COMPANY_ID depuis la DB

@pytest.fixture(scope="session")
def db_validator() -> DBValidator  # Instance connectée à Supabase

@pytest.fixture(scope="session")
async def tg_user() -> TelegramUserSim  # Client Telethon connecté

@pytest.fixture(scope="session")
def supabase()                    # Client Supabase (get_supabase())
```

---

## 6. Premier test template (`test_cctp_upload.py`)

Scénario :
1. `tg_user.upload_file("fixtures/CCTP-ESSET-Rue-Thenard.pdf")`
2. `tg_user.wait_for_bot_response(timeout=15)`
3. Vérifier la réponse du bot (pattern regex : confirmation de réception)
4. `db_validator.assert_operation_created(...)` — vérifie qu'une entrée est créée dans la table cible avec `statut = 'en_attente'`

Ce test ne juge **pas** le contenu extrait — seulement le fait qu'une entrée apparaît en DB.

---

## 7. Flexibilité des environnements

Le `TelegramUserSim` utilise `SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_URL` pour choisir entre :
- **Serveur local** : `http://localhost:8081` (Docker `telegram-bot-api`)
- **API officielle** : `https://api.telegram.org`

Le `conftest.py` charge automatiquement le bon endpoint en fonction de la variable d'environnement.

---

## 8. Dépendances additionnelles

```txt
# requirements-e2e.txt
telethon>=1.34.0
pytest-asyncio>=0.21.0
```

Installées automatiquement par `run_e2e_tests.sh` dans le venv existant.

---

## 9. Nettoyage et idempotence

- Pas de nettoyage DB après les tests : les données créées restent dans Supabase (base de test partagée).
- Les containers Docker sont détruits avec `docker compose down -v` pour garantir un état propre au prochain run.
- Les sessions Telethon sont éphémères (pas de fichier `.session` persistant).

---

## 10. Workflow TDD

1. Écrire un test E2E qui décrit le comportement attendu
2. `./tests_e2e/run_e2e_tests.sh` → le test échoue (RED)
3. Coder la feature dans le backend
4. `./tests_e2e/run_e2e_tests.sh` → le test passe (GREEN)
5. Refactorer si nécessaire

---

## Annexes

### Variables d'environnement requises

| Variable | Source | Description |
|---|---|---|
| `SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN` | `~/.bashrc` | Token du bot Telegram E2E |
| `SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_URL` | `~/.bashrc` | URL de l'API Telegram |
| `ENVIRONMENT` | `.env.test` | `test` |
| `SUPABASE_URL` | `.env.test` | URL Supabase |
| `SUPABASE_SERVICE_KEY` | `~/.bashrc` | Service key Supabase |
| `TEST_ORG_SLUG` | `.env.test` | `REDACTED_ORG_SLUG` |
| `TEST_COMPANY_SLUG` | constant | `construction` |
