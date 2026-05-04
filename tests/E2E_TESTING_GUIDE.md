# 🧪 Harnais de Validation E2E — Bot Telegram

**Auteur :** Louky (Hermes Agent)  
**Date :** 04/05/2026  
**Branche :** `Louky-telegram-e2e-04-05-2026`  
**Statut :** ✅ 3/3 tests PASSED (8.25s)

---

## Table des Matières

1. [Présentation](#1-présentation)
2. [Architecture](#2-architecture)
3. [Lancement Rapide](#3-lancement-rapide)
4. [Structure des Tests](#4-structure-des-tests)
5. [Écriture d'un Scénario](#5-écriture-dun-scénario)
6. [Troubleshooting — Le Journal de Bord](#6-troubleshooting--le-journal-de-bord)
7. [Maintenance & Évolution](#7-maintenance--évolution)

---

## 1. Présentation

Ce harnais permet de tester le bot Telegram **SurenSaaS** en local, sans envoyer de vrais messages à Telegram. Il simule un webhook Telegram entrant, déclenche le flux agentique LangGraph/Gemini, capture la réponse du bot et la juge via un petit LLM.

### Pourquoi ne pas tester directement sur Telegram ?

- Pas besoin de déployer
- Pas de latence réseau
- Pas de pollution des logs métier
- Reproductible à l'infini
- Coût zéro (Gemini Flash, pas de messages SMS)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         pytest                              │
│                                                             │
│   test_scenarios.py                                         │
│       │                                                     │
│       ▼                                                     │
│   conftest.py — TgMockClient                                │
│       │                                                     │
│       │ POST /api/v1/{org_id}/telegram/webhook/{token}      │
│       ▼                                                     │
│   ✅ send_text/send_document/send_photo/send_voice          │
│       │                                                     │
│       ▼                                                     │
│   ← réponse HTTP avec reply_text intégré                    │
│       │                                                     │
│       ▼                                                     │
│   LLM Judge (gemini-2.0-flash) → score 1|0 + raison        │
│       │                                                     │
│       ▼                                                     │
│   PASS / FAIL                                               │
└───────────┬─────────────────────────────────────────────────┘
            │
            │ HTTP
            ▼
┌───────────────────┐     ┌───────────────────┐     ┌──────────────┐
│  Backend FastAPI  │────►│    tg-mock:8081   │     │  Supabase    │
│  localhost:8080   │     │    (Docker)        │     │  (externe)   │
│                   │     │   sendMessage → 200│     │              │
│  LangGraph/Gemini │     │   (getUpdates vide)│     │  org_id test │
└───────────────────┘     └───────────────────┘     └──────────────┘
```

### Composants

| Service | Port | Rôle | Technologie |
|---|---|---|---|
| Backend SurenSaaS | 8080 | Reçoit le webhook, exécute LangGraph, appelle Gemini | FastAPI + uvicorn |
| tg-mock | 8081 | Mime l'API Telegram Bot (répond 200 à sendMessage) | Image Go statique, Docker |
| Supabase | externe | Stocke les données métier (chantiers, dépenses, orgs) | PostgreSQL managé |
| Gemini/Vertex AI | externe | LLM agentique + LLM judge | Flash + Pro via Google Cloud |

### Flux

1. **pytest** construit un `Update` Telegram simulé (message texte, photo, etc.)
2. **POST** direct vers le webhook backend (`localhost:8080`)
3. **Backend** : identifie le bot `Arev_travaux_test_e2e_bot` → flux construction LangGraph
4. **LangGraph** → appelle **Gemini Flash** (Vertex AI) → reçoit une réponse structurée
5. **Backend** : envoie `sendMessage` à **tg-mock** (Docker, port 8081)
6. **tg-mock** répond 200 ✅ (mais ne stocke pas dans getUpdates — cf. Troubleshooting #6)
7. **Backend** : renvoie `reply_text` dans la **réponse HTTP** du webhook
8. **pytest** : extrait `reply_text`, envoie au **LLM Judge** (gemini-2.0-flash)
9. **Judge** : vérifie la pertinence → score 1/0

---

## 3. Lancement Rapide

### Prérequis

```bash
# Python 3.11+ avec venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# tg-mock en Docker
docker compose -f docker-compose.telegram-test.yml up -d

# Vars d'env (secrets dans ~/.bashrc)
source ~/.bashrc
```

### Étape 1 — Lancer le backend

```bash
bash scripts/run-local-back_test.sh
```

Attendre le message : `🚀 Application démarrée` (environ 15s à cause du chargement Vertex AI et connexion Supabase).

### Étape 2 — Lancer les tests

```bash
# Terminal 2
cd /opt/projects/suren/saas/surenSaas
source ~/.bashrc
source surenSaasBack/venv/bin/activate
set -a && source .env.test && set +a

TEST_WEBHOOK_TOKEN="local_token" \
BACKEND_WEBHOOK_URL="http://localhost:8080/api/v1/{org_id}/telegram/webhook/{webhook_token}" \
TELEGRAM_CONSTRUCTION_BOT_TOKEN="${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN}" \
python -m pytest tests/ -v
```

Résultat attendu :

```
tests/test_scenarios.py::test_scenario[scenario_depense]  PASSED
tests/test_scenarios.py::test_scenario[scenario_document]  PASSED
tests/test_scenarios.py::test_scenario[scenario_pointage]  PASSED
```

⚠️ La commande est longue, mais chaque var est nécessaire : `.env.test` apporte `TEST_ORG_ID`, les vars d'env concrètes (BACKEND_WEBHOOK_URL, TELEGRAM_CONSTRUCTION_BOT_TOKEN) écrasent les valeurs par défaut.

---

## 4. Structure des Tests

```
tests/
├── conftest.py                  # Fixtures pytest + TgMockClient
│   ├── BOT_TOKEN               # Vrai token E2E (depuis env)
│   ├── ORG_ID                  # REDACTED-...
│   ├── WEBHOOK_TOKEN           # local_token
│   ├── BACKEND_WEBHOOK_URL     # Template d'URL
│   │
│   ├── TgMockClient            # Client pour envoyer des webhooks et lire les réponses
│   │   ├── send_text()         # Injecte un message texte
│   │   ├── send_photo()        # Injecte une photo (nécessite un fichier local)
│   │   ├── send_document()     # Injecte un document (PDF)
│   │   ├── send_voice()        # Injecte un message vocal (audio .ogg)
│   │   ├── _parse_result()     # Extrait reply_text depuis la réponse HTTP
│   │   └── get_replies()       # (déprécié) Polling tg-mock
│   │
│   └── judge_response()        # LLM Judge
│
├── test_scenarios.py           # Test unique paramétré
│   └── test_scenario[scenario] # Boucle sur tous les YAML
│
├── fixtures/media/             # Fichiers médias de test
│   └── facture_test.pdf        # PDF facture
│
└── scenarios/                  # Scénarios YAML
    ├── scenario_depense.yaml   # Texte : "150€ béton sur CH-016"
    ├── scenario_document.yaml  # Document : PDF facture
    └── scenario_pointage.yaml  # Texte : "Jean Dupont + pelleteuse"
```

---

## 5. Écriture d'un Scénario

Les scénarios sont en YAML pur. Aucun code Python nécessaire. Format :

```yaml
test_case: "Nom court et descriptif"
description: >
  Description longue de ce que le scénario teste.
tags: [tag1, tag2]
input:
  chat_id: 999999
  from_user:
    id: 999999
    first_name: "Test"
    is_bot: false
  media:
    type: text|document|photo|voice
    content: "Message texte de l'utilisateur"
    # Pour document/photo/voice :
    file_path: "tests/fixtures/media/fichier.pdf"
    caption: "Légende optionnelle"
judge:
  model: gemini-2.0-flash
  prompt: |
    Vérifie que la réponse du bot :
    1. Critère 1
    2. Critère 2
    ...
    Réponds UNIQUEMENT en JSON : {"score": 1|0, "reason": "..."}
  expected_verdict: pass
```

### Chat IDs réservés

| ID | Usage |
|---|---|
| `999999` | Utilisateur/chat de test (tous les scénarios) |
| Tous les IDs dans `9xxxxx` | Réservés pour l'automatisation |

### Règles d'isolation

- `chat_id` doit être un ID de test, pas un vrai chat Telegram
- `from_user.id` doit correspondre au `chat_id`
- Les chantiers test sont préfixés `CH-` (ex: `CH-016`)
- L'org de test est `REDACTEDORG`
- Purge des données de test possible via :
  ```sql
  DELETE FROM table WHERE org_id = 'REDACTEDORG';
  ```

---

## 6. Troubleshooting — Le Journal de Bord

Cette section documente chaque problème rencontré pendant la mise en place du harnais, la cause racine et la solution appliquée. Conservez-la comme référence.

### Problème #1 : Module `langchain_google_genai` manquant

**Symptôme :** Le backend démarre mais le flux agentique échoue avec `ModuleNotFoundError: No module named 'langchain_google_genai'`

**Cause :** Le `requirements.txt` ne liste pas ce module. Il est importé dynamiquement par le code LangGraph.

**Solution :** Installer manuellement :
```bash
pip install langchain-google-genai
```
Puis redémarrer uvicorn (le reloader ne recharge pas les nouveaux packages).

### Problème #2 : `chat not found` sur sendMessage

**Symptôme :** Le backend logge `❌ Telegram API error (400): {"description":"Bad Request: chat not found"}`

**Cause :** Le chat `999999` n'existe pas dans l'état de tg-mock. La première injection crée la conversation (update avec message), mais `sendMessage` arrive avant que l'update soit traité.

**Solution :** `_ensure_chat_exists()` envoie un message "/start" au chat 999999 dans le constructeur de TgMockClient, avant que le test ne commence.

**Code pertinent :**
```python
def _ensure_chat_exists(self):
    """Ensure the test chat exists in tg-mock by sending an init message."""
    init_update = {
        "update_id": 0,
        "message": {
            "message_id": 0,
            "from": {"id": 999999, "is_bot": False, "first_name": "Init"},
            "chat": {"id": 999999, "type": "private", "first_name": "Init"},
            "date": int(time.time()),
            "text": "/start",
        },
    }
    resp = self._client.post(f"/bot{self.bot_token}/sendMessage", json={
        "chat_id": 999999, "text": "init"
    })
```

### Problème #3 : Connection refused — port 8000 vs 8080

**Symptôme :** `httpx.ConnectError: [Errno 111] Connection refused` lors du POST du webhook.

**Cause :** Le conftest.py a une valeur par défaut `BACKEND_WEBHOOK_URL="http://localhost:8000/..."` mais le backend tourne sur **8080** (défini dans `run-local-back_test.sh`). La var d'env `BACKEND_WEBHOOK_URL` n'était pas passée aux tests.

**Solution :** Passer explicitement dans la commande pytest :
```bash
BACKEND_WEBHOOK_URL="http://localhost:8080/api/v1/{org_id}/telegram/webhook/{webhook_token}"
```

**Leçon :** Toujours spécifier le port. Ne jamais compter sur les valeurs par défaut.

### Problème #4 : `TEST_ORG_ID` non chargé — URL mal formée

**Symptôme :** Log backend : `POST /api/v1//telegram/webhook/local_token` — **double slash**, 404.

**Cause :** Les tests utilisent `set -a && source .env.test` mais l'ordre des sources compte. Si les vars d'env inline sont avant `source .env.test`, elles sont écrasées.

**Solution :** Charger `.env.test` en premier (`set -a && source .env.test && set +a`), puis passer les vars d'override après :
```bash
set -a && source .env.test && set +a
TEST_WEBHOOK_TOKEN="local_token" \
BACKEND_WEBHOOK_URL="..." \
TELEGRAM_CONSTRUCTION_BOT_TOKEN="..." \
python -m pytest tests/ -v
```

**Leçon :** Les vars d'env inline écrasent les vars du fichier sourcé (plus tard dans l'ordre des arguments = prioritaire).

### Problème #5 : `TELEGRAM_API_URL` ignoré par le backend

**Symptôme :** Le backend envoie les messages au vrai Telegram (`api.telegram.org`) au lieu de tg-mock (`localhost:8081`). `chat not found` car le vrai Telegram ne connaît pas le chat 999999.

**Cause :** `app/services/telegram/interface.py` ligne 17 avait `self.base_url = f"https://api.telegram.org/bot{bot_token}"` — **hardcodé**. Le champ `settings.telegram_api_url` n'était jamais consulté.

**Solution :** Patcher `interface.py` pour utiliser `settings.telegram_api_url` :

```python
# Avant :
self.base_url = f"https://api.telegram.org/bot{bot_token}"

# Après :
base = (api_url or settings.telegram_api_url or "https://api.telegram.org").rstrip("/")
self.base_url = f"{base}/bot{bot_token}"
```

**Et** ajouter `export TELEGRAM_API_URL="http://localhost:8081"` dans `run-local-back_test.sh`.

**Leçon :** Le hardcoding des URLs d'API distantes est un piège classique. Toujours utiliser les settings/config même pour les valeurs par défaut.

### Problème #6 : tg-mock ne stocke pas les messages dans getUpdates

**Symptôme :** Le log backend dit `✅ Telegram 200 OK` mais `getUpdates` retourne toujours `{"ok":true,"result":[]}`. Le test attend 30s et timeout.

**Cause :** L'image Go `tg-mock` répond 200 à `sendMessage` mais **ne stocke pas le message dans sa queue `getUpdates`**. C'est un comportement normal de certaines implémentations de mock Telegram — `sendMessage` et `getUpdates` sont deux APIs indépendantes.

**Solution :** Au lieu de passer par tg-mock pour lire la réponse du bot, on la capture depuis la **réponse HTTP du webhook backend** :

1. Modifier `webhook_handler.py` pour renvoyer `reply_text` dans le JSON de réponse :
   ```python
   return {"status": "ok", "reply_text": text_to_send, "reply_action": str(parsed.action) if parsed else None}
   ```
2. Modifier toutes les méthodes `send_*` du `TgMockClient` pour extraire `reply_text` via `_parse_result()`
3. Simplifier le test : plus de polling, lecture directe depuis la réponse

**Alternative envisagée :** Changer l'image tg-mock pour une version qui supporte getUpdates correctement. Cette solution est plus propre mais nécessite de builder/maintenir une image custom. La solution du `reply_text` est plus rapide et n'affecte pas la production (Telegram ignore le body des réponses 200).

**Leçon :** Ne jamais faire confiance à une implémentation de mock sans vérifier son comportement exact. `sendMessage` n'implique pas `getUpdates`.

### Problème #7 : Script non-idempotent — workers uvicorn orphelins

**Symptôme :** Relancer `run-local-back_test.sh` → le port 8080 est déjà pris → erreur silencieuse (à cause de `set -e`).

**Cause :** Le script utilisait `lsof -ti:8080 | xargs kill -9` mais le reloader uvicorn recrée des workers qui écoutent encore brièvement après le kill. De plus, `set -e` arrête le script à la première erreur silencieuse.

**Solution :**
1. Remplacer `kill -9` par `kill` (SIGTERM) pour permettre un arrêt propre
2. Ajouter `sleep 2` après le kill pour laisser le temps au port de se libérer
3. Ajouter une boucle `pgrep -f "uvicorn app.main:app"` pour tuer tout processus uvicorn orphelin
4. Ajouter un log de confirmation `✅ Port 8080 libre`

**Leçon :** Les scripts avec `set -e` donnent l'illusion de la robustesse mais cachent les échecs silencieux. Toujours ajouter des logs de confirmation après chaque étape critique.

---

## 7. Maintenance & Évolution

### Ajouter un nouveau scénario

1. Créer un fichier YAML dans `tests/scenarios/`
2. Le nom du fichier = `scenario_mafonctionnalite.yaml`
3. pytest le découvre automatiquement via la fixture `scenario_files` dans conftest.py

### Migrer vers une autre image tg-mock

Si on veut que `getUpdates` fonctionne :
1. Trouver une image Docker de mock Telegram Bot API qui supporte `sendMessage` → `getUpdates`
2. Modifier `docker-compose.telegram-test.yml`
3. Dans conftest.py, réactiver `get_replies()` avec `reply_text` comme fallback optionnel

### CI/CD — GitHub Actions

Workflow à créer :
```yaml
- name: Start backend & tg-mock
  run: |
    docker compose -f docker-compose.telegram-test.yml up -d
    bash scripts/run-local-back_test.sh &
    sleep 20  # le temps que tout démarre

- name: Run E2E tests
  run: |
    python -m pytest tests/ -v
```

### Dette technique connue

- **webhook_handler.py** retourne `reply_text` et `reply_action` dans la réponse HTTP. C'est une sonde de test dans du code de production. Si un jour le format de réponse du webhook devait changer (ex: pour un standard Telegram), il faudra soit garder la sonde, soit passer par un middleware de test.
- **tg-mock getUpdates** ne fonctionne pas. La solution actuelle contourne le problème. À remplacer si on a besoin de tests multi-tours (conversation avec plusieurs messages du bot).
