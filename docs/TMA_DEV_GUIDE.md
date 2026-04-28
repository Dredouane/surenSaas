# Guide dev — Telegram Mini App (TMA)

## Architecture réseau

```
                    ┌──────────────────────────────────────────────┐
                    │           Tunnel ngrok UNIQUE                │
                    │  https://ethics-each-bonehead.ngrok-free.dev  │
                    │         ↓ port 3000 (Frontend Next.js)       │
                    └──────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
           /mini-app (TMA)      /api/v1/* (proxy Next.js)
                    │                    │
                    │              ┌─────┴──────┐
                    │              ▼            ▼
                    │        backend:8000  auth/TMA
                    │
           WebView Telegram ← bot → webhook
```

**Principe : un seul tunnel ngrok** sur le port 3000 (frontend Next.js). Next.js proxyfie tous les appels `/api/v1/*` vers le backend sur le port 8080. Le webhook Telegram et la TMA partagent la même URL publique.

## Démarrage (3 terminaux)

```bash
# ════════════════ Terminal 1 : Backend ── port 8080 ════════════════
cd surenSaas
export TMA_HOST="ethics-each-bonehead.ngrok-free.dev"  # URL du tunnel frontend
./scripts/run-local-back_test.sh

# ════════════════ Terminal 2 : Frontend ── port 3000 ════════════════
cd surenSaas
./scripts/run-local-front_test.sh

# ════════════════ Terminal 3 : Tunnel ngrok unique ── port 3000 ════════════════
cd surenSaas
# Tue les tunnels existants
pkill -f ngrok 2>/dev/null
# Lance le tunnel frontend (un seul, pas de backend)
python3 scripts/manage_tunnel.py --env test --service frontend
# → URL: https://ethics-each-bonehead.ngrok-free.dev
```

## Configurer le webhook

```bash
curl -X POST "https://api.telegram.org/bot${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN}/setWebhook" \
  -d "url=https://ethics-each-bonehead.ngrok-free.dev/api/v1/REDACTEDORG/telegram/webhook/local_token"
```

Vérifier :
```bash
curl -s "https://api.telegram.org/bot${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN}/getWebhookInfo" \
  | python3 -m json.tool | grep url
```

## Tester

### Depuis Telegram (flow réel)
1. Ouvre le bot `@suren_construction_test_bot`
2. Tape `/start` — le menu s'affiche avec **"📱 Ouvrir l'application"** en bas
3. Clique dessus → la TMA s'ouvre dans le WebView Telegram

### Depuis le navigateur (fallback)
1. Ouvre `http://localhost:3000/mini-app`
2. Message "📱 Ouvrez cette application depuis Telegram"
3. C'est normal — pas de WebView Telegram

### Depuis l'URL ngrok (sur téléphone)
1. Ouvre `https://ethics-each-bonehead.ngrok-free.dev/mini-app`
2. Même fallback — sauf si ouvert via le bouton du bot

## Problèmes fréquents

| Problème | Cause | Solution |
|----------|-------|----------|
| `GET /mini-app` → 404 | Tunnel ngrok forwarde vers backend (8080) au lieu du frontend | `pkill -f ngrok` puis relancer `--service frontend` |
| `telegram_id manquant` | L'`id` Telegram est dans l'objet `user` du initData, pas à la racine | Vérifier que le commit `b3a07c7` est déployé |
| Bouton WebApp absent | `chantier_id` pas passé à `build_main_menu` | Vérifier que le commit `491ccb3` est déployé |
| Message "Lien d'invitation" | `/start` sans paramètre et user pas encore lié | Utiliser le lien d'invitation ou vérifier que le commit `491ccb3` est déployé |
| Deux bots répondent | Même webhook_token pour les deux bots | Configurer des tokens différents : `local_token` pour E2E, `cfc8da0d30fdc391` pour GCP |

## API TMA (sans le bot)

```bash
# S'authentifier (initData factice)
curl -X POST http://localhost:8080/api/v1/tma/auth \
  -H "Content-Type: application/json" \
  -d '{"initData": "query_id=test&user={\"id\":\"123\"}&auth_date=1700000000&hash=test"}'

# Récupérer le contexte (avec JWT)
curl http://localhost:8080/api/v1/tma/context \
  -H "Authorization: Bearer <JWT>"
```

## Tests

```bash
cd surenSaasBack
python3 -m pytest tests/ -v --tb=short \
  -k "not full_scenarios and not api_routes and not email"
```

## Déploiement GCP

Aucune config supplémentaire. Le déploiement frontend (`scripts/deploy_front_test.sh`) sert la TMA sur :
```
https://test-surensaas-front-982795023541.europe-west1.run.app/mini-app
```

Configurer `TMA_HOST` dans les variables d'env du backend GCP.
