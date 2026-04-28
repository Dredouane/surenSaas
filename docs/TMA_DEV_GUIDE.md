# Guide dev — Telegram Mini App (TMA)

## Démarrage rapide (5 terminaux)

```bash
# ─── Terminal 1 : Backend ───
cd surenSaas/surenSaasBack
source ~/.bashrc
python3 app/main.py

# ─── Terminal 2 : Frontend ───
cd surenSaas/surenSaasFront
npx next dev -p 3000

# ─── Terminal 3 : Tunnel Frontend ───
cd surenSaas
python3 scripts/manage_tunnel.py --env test --service frontend
# → note l'URL : https://xxx.ngrok-free.dev

# ─── Terminal 4 : Backend relancé avec TMA_HOST ───
cd surenSaas/surenSaasBack
export TMA_HOST="xxx.ngrok-free.dev"  # <-- colle l'URL du tunnel frontend
source ~/.bashrc
python3 app/main.py

# ─── Terminal 5 : Tunnel Backend ───
cd surenSaas
python3 scripts/manage_tunnel.py --env test --service backend
```

## Tester la TMA

### Depuis Telegram (le vrai flow)

1. Ouvre le bot `@suren_construction_test_bot`
2. Tape `/start` ou clique n'importe où
3. Dans le menu, clique sur **"📱 Ouvrir l'application"**
4. La TMA s'ouvre dans le WebView Telegram → tu vois l'accueil mosaïque

### Depuis le navigateur (fallback)

1. Ouvre `http://localhost:3000/mini-app` dans Chrome
2. Tu vois le message "📱 Ouvrez cette application depuis Telegram"
3. C'est normal — le fallback WebView fonctionne

### Depuis l'URL ngrok (sur téléphone)

1. Ouvre `https://xxx.ngrok-free.dev/mini-app` sur ton téléphone
2. Tu vois aussi le fallback (pas de WebView Telegram)

## API TMA (sans le bot)

```bash
# S'authentifier (initData factice — test uniquement)
curl -X POST http://localhost:8000/api/v1/tma/auth \
  -H "Content-Type: application/json" \
  -d '{"initData": "query_id=test&user={\"id\":\"123\"}&auth_date=1700000000&hash=test"}'

# Récupérer le contexte (avec JWT)
curl http://localhost:8000/api/v1/tma/context \
  -H "Authorization: Bearer <JWT>"
```

## Tests

```bash
cd surenSaasBack
python3 -m pytest tests/ -v --tb=short -k "not full_scenarios and not api_routes and not email"
```

## Déploiement

Aucune config supplémentaire. Le même `scripts/deploy*.sh` (Cloud Run) sert la TMA sur `https://suren-front-xxx.run.app/mini-app`.
