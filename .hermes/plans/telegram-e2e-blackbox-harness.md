# Plan — Harnais de Validation E2E Blackbox (Bot Telegram)

**Branche :** `Louky-telegram-e2e-04-05-2026`
**Date :** 2026-05-04
**Auteur :** Louki (Hermes)
**Dev :** Pi (via ACP)

## Architecture

```
                    ┌──────────────────────────────────────────────────────┐
                    │                    VPS (localhost)                    │
                    │                                                      │
                    │  ┌──────────────┐    POST /webhook    ┌───────────┐  │
                    │  │   tg-mock    │ ──────────────────►  │ Backend   │  │
                    │  │  (Go/Docker) │                     │ FastAPI   │  │
                    │  │   :8081      │ ◄────────────────── │ bot       │  │
                    │  │              │  sendMessage/photo  │ LangGraph │  │
                    │  └──────┬───────┘                     └───────────┘  │
                    │         │                                              │
                    │         │ response capturée                            │
                    │         ▼                                              │
                    │  ┌────────────────────────────────────────────┐       │
                    │  │        tests/ (pytest)                     │       │
                    │  │                                            │       │
                    │  │  conftest.py  ← tg_mock_client fixture     │       │
                    │  │  test_scenarios.py ← parametrized YAML    │       │
                    │  │  judge.py     ← Gemini Flash LLM Judge    │       │
                    │  │  models.py    ← Pydantic schemas          │       │
                    │  │  reset.py     ← state cleaner             │       │
                    │  │                                            │       │
                    │  │  scenarios/                                │       │
                    │  │    scenario_depense.yaml                   │       │
                    │  │    scenario_pointage.yaml                  │       │
                    │  │    scenario_document.yaml                  │       │
                    │  └────────────────────────────────────────────┘       │
                    └──────────────────────────────────────────────────────┘
```

## Tâches Pi

### T1 — Setup tg-mock (Docker)

- Créer un `docker-compose.telegram-test.yml` à la racine du projet ou dans `tests/`
- Service `tg-mock` : image `ghcr.io/watzon/tg-mock`, port `8081:8081`
- Configurer une variable `TELEGRAM_BASE_URL=http://localhost:8081` dans le `.env` du bot local
- Vérifier que le bot backend utilise bien cette variable pour ses appels API Telegram (sendMessage, etc.)
- Vérifier avec `curl -X POST http://localhost:8081/updates` que l'API de contrôle répond

**Fichiers :**
- `docker-compose.telegram-test.yml`
- Mise à jour potentielle du `.env` ou `config.py` pour exposer `TELEGRAM_BASE_URL`

**Critères de succès :**
- `docker compose -f docker-compose.telegram-test.yml up -d` fonctionne
- `curl http://localhost:8081/health` (ou équivalent) retourne 200
- Le backend bot peut envoyer un `sendMessage` à tg-mock sans crash

---

### T2 — Fixture pytest `tg_mock_client` + Reset d'état

- Créer `tests/conftest.py`
- Fixture `tg_mock_client` scope="session" :
  - POST /updates sur tg-mock
  - Récupère les réponses capturées depuis l'API de contrôle
  - Timeout/polling : attend jusqu'à 15s avec intervalle 0.5s
- Fixture `reset_state` scope="function" (autouse) :
  - Nettoie l'état LangGraph (thread_id, state) entre chaque scénario
  - Nettoie les enregistrements DB créés par le scénario précédent (via DELETE sur les tables concernées ou snapshot/restore)
- Fixture `judge_client` scope="session" :
  - Client Gemini Flash préconfiguré (clé API depuis `.env`)

**Fichiers :**
- `tests/conftest.py`

**Critères de succès :**
- `pytest tests/ --collect-only` détecte bien les fixtures
- Le polling timeout lève une exception claire si pas de réponse dans les 15s

---

### T3 — Modèles Pydantic + Judge (Gemini Flash)

- Créer `tests/models.py` :
  - `ScenarioInput` : type de media (text|voice|photo|document), content (texte ou path fichier), chat_id, from_user
  - `ScenarioJudge` : model, prompt, expected_verdict
  - `Scenario` : test_case, description, tags, input, judge
  - `JudgeVerdict` : score (0/1), reason (str)
- Créer `tests/judge.py` :
  - `judge_response(scenario: Scenario, bot_reply_text: str) -> JudgeVerdict`
  - Construit le prompt : "SCENARIO: {prompt}\nREPONSE: {bot_reply_text}\n\nRéponds UNIQUEMENT en JSON: {\"score\": 1|0, \"reason\": \"...\"}"
  - Appelle Gemini Flash via `google-genai` SDK ou HTTP direct
  - Parse la réponse JSON du LLM
  - Timeout 10s, retry 2x si parsing échoue

**Fichiers :**
- `tests/models.py`
- `tests/judge.py`

**Critères de succès :**
- `python -c "from tests.judge import judge_response; ..."` retourne un `JudgeVerdict`
- Un test unitaire mocké vérifie que le prompt est bien formaté

---

### T4 — Test paramétré sur les YAML

- Créer `tests/test_scenarios.py` :
  - Lit tous les fichiers `tests/scenarios/*.yaml`
  - Pour chaque scenario : injecte via tg-mock → attend réponse → appelle judge → assert score == 1
  - Test ID = `test_case` du YAML
- Gestion des médias (voice, photo, document) :
  - Si `input.media.type` != text : le fichier référencé doit exister dans `tests/fixtures/media/`
  - Le fichier est envoyé à tg-mock comme multipart/form-data ou base64 selon l'API de tg-mock
  - Le runner construit l'Update Telegram valide (avec `file_id` factice)

**Fichiers :**
- `tests/test_scenarios.py`

**Critères de succès :**
- `pytest tests/test_scenarios.py -v` exécute tous les scenarios YAML
- Chaque test output : `✓ scenario_depense` ou `✗ scenario_depense: reason...`

---

### T5 — 3 scénarios YAML de référence

- Créer `tests/scenarios/scenario_depense.yaml` :
  - Input : text "Aujourd'hui, j'ai dépensé 150€ pour le béton sur CH-016"
  - Judge : vérifie montant 150€, chantier CH-016, date du jour, confirmation
- Créer `tests/scenarios/scenario_pointage.yaml` :
  - Input : text "Je pointe Jean Dupont et la pelleteuse sur CH-016"
  - Judge : vérifie noms, type ressources, chantier, confirmation
- Créer `tests/scenarios/scenario_document.yaml` :
  - Input : document PDF (fichier factice dans `tests/fixtures/media/facture_test.pdf`)
  - Judge : vérifie que le bot accuse réception du document et propose action

- Créer les fichiers médias factices si besoin
- Créer `tests/fixtures/media/` avec un petit PDF valide

**Fichiers :**
- `tests/scenarios/scenario_depense.yaml`
- `tests/scenarios/scenario_pointage.yaml`
- `tests/scenarios/scenario_document.yaml`
- `tests/fixtures/media/facture_test.pdf` (1-page PDF avec texte "FACTURE TEST")

**Critères de succès :**
- Chaque YAML est valide (Pydantic le parse)
- Les fichiers médias existent et sont lisibles

---

### T6 — Validation E2E

- Lancer `docker compose -f docker-compose.telegram-test.yml up -d`
- Lancer le backend local (FastAPI + DB)
- Lancer `pytest tests/ -v --tb=short`
- Vérifier que :
  - T1 : tg-mock répond
  - T2 : les fixtures s'exécutent sans erreur
  - T3 : le juge retourne des verdicts cohérents
  - T4-T5 : les 3 scénarios passent (ou échouent avec reason compréhensible)
- Vérifier le reset d'état : scénario B n'est pas pollué par scénario A

**Critères de succès :**
- `pytest tests/ -v --tb=short` → `3 passed`
- Le rapport final est envoyé à Louki

---

## Règles pour Pi

1. **TDD strict** (skill `tdd-cycle`) : Red → Green → Refactor à chaque tâche
2. **Ubiquitous Language** (skill `ubiquitous-language`) : les termes du domaine (voir DOMAIN_LANGUAGE.md section Harnais de Validation) sont utilisés partout
3. **Deep Modules** (skill `deep-modules`) : `judge.py` est un module profond — interface simple `judge_response(scenario, reply) → verdict`, implémentation complexe cachée
4. **Les noms de variables suivent les conventions du projet** : `statut` pas `status`, `chantier_id` pas `site_id`
5. **Le conteneur tg-mock** doit être **optionnel** — si le backend local a déjà `TELEGRAM_BASE_URL` pointant vers tg-mock, c'est la config qui décide, pas le code
6. **Ne pas toucher au code backend métier** — le harnais est 100% blackbox
7. **Toujours logger** : chaque étape (injection, capture, jugement) doit produire une ligne de log claire
8. **IDs de test isolés** : utiliser exclusivement `chat_id: 999999`, `from_user.id: 999999`, `org_id: 0` dans les scénarios YAML. Ces IDs n'existent pas en prod/test. Le reset d'état ne DELETE que les enregistrements liés à ces IDs — jamais de `TRUNCATE` ou `DELETE FROM` sans filtre.

## Critères de succès globaux

1. ✅ Un humain (ou Louki) peut écrire un nouveau scénario en créant juste un fichier YAML + éventuellement un fichier média
2. ✅ Le même harnais marche pour les 3 environnements (local, test, prod) en changeant juste l'URL du webhook
3. ✅ Pas de faux positifs : un bot qui répond n'importe quoi doit FAIL
4. ✅ Les tests prennent moins de 30s chacun (timeout polling inclus)
