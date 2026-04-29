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

## Écrans TMA

| Écran | Route | Fonctionnalités |
|-------|-------|----------------|
| **📈 Situations** | `/mini-app/progress` | Feed situations ouvertes → sélection → saisie texte/voice/photo → extraction IA → modal confirmation → POST ligne |
| **📸 Opérations** | `/mini-app/operations` | Saisie texte/voice/photo → extraction IA → modal confirmation → POST opération → historique détaché |
| **💰 Dépenses** | `/mini-app/expenses` | Saisie texte/voice/photo → extraction IA → modal confirmation → POST dépense → guardrails |
| **👷 Équipe** | `/mini-app/attendance` | Sélecteur date ◀▶, toggle Homme/Machine, cycle null→present→absent→null |
| **📅 Réunions** | `/mini-app/reunions` | Liste réceptions (lecture seule) |

## Composants clés

### MediaInput (`components/MediaInput.tsx`)
Input unique qui gère : texte + 🎤 voix (MediaRecorder) + 📸 caméra (video→canvas) + 📄 PDF.
Appelle `POST /api/v1/tma/process` avec le bon `workflow` et retourne les données structurées dans `onResult`.

### CameraCapture (`components/CameraCapture.tsx`)
- **Preview live** : flux vidéo `getUserMedia` haute résolution (3840×2160)
- **Snapshot** : au clic, pause vidéo + canvas → affiche l'aperçu
- **Multi-photos** : confirmation rapide → vidéo play immédiat (synchrone) + thumbnail + création `File` en arrière-plan (asynchrone non bloquant)
- **Miniatures** : barre horizontale avec suppression individuelle
- **Envoi groupé** : bouton "✅ Envoyer (X)" pour tout envoyer en une fois
- **Stop stream** : libère la caméra après envoi

### VoiceRecorder (`components/VoiceRecorder.tsx`)
- **Permission unique** : `getUserMedia` une fois, stream réutilisé
- **Timer + boutons** : 🔴 XX:XX pendant l'enregistrement → ✅ Envoyer / ❌ Annuler au relâche
- **Envoi** : blob audio → `POST /api/v1/tma/process` → transcription + extraction structurée

### ModalConfirm (`components/ModalConfirm.tsx`)
Modal bottom-sheet : affiche les données extraites par l'IA + ✅ Envoyer / ❌ Annuler.

### tmaFetch (`components/tmaFetch.ts`)
Wrapper `fetch` qui ajoute automatiquement :
- `org_id` en query param
- `Authorization: Bearer <JWT>` header
- `X-Correlation-ID` header

## Flux d'extraction unifié

```
Texte saisi → POST /api/v1/tma/process (text + workflow)
Voice → blob audio → POST /api/v1/tma/process (audio + workflow)
Photo → video→canvas snapshot → File → POST /api/v1/tma/process (file + workflow)
PDF → File → POST /api/v1/tma/process (file + workflow)

Tout retourne → { is_valid, data, guardrail_issues } → ModalConfirm → ✅ Envoyer → POST en DB
```

## Problèmes résolus

| Problème | Cause | Solution |
|----------|-------|----------|
| `GET /mini-app` → 404 | Tunnel ngrok sur 8080 (backend) au lieu de 3000 | Tunnel unique `--service frontend` |
| `telegram_id manquant` | `id` dans l'objet `user` du initData, pas à la racine | Extraire `user.id` en priorité |
| Bouton WebApp absent | `chantier_id` pas passé à `build_main_menu` | Passer `chantier_id` au menu |
| Message "Lien d'invitation" | `/start` sans paramètre | Vérifier `telegram_users` existant |
| Deux bots répondent | Même `webhook_token` | `local_token` pour E2E, `cfc8da0d30fdc391` pour GCP |
| Photo → galerie (pas caméra) | Android Photo Picker | `getUserMedia` → video preview → canvas snapshot, pas d'input file |
| Valider photo ne fait rien | `capturing.current` bloquait `confirm` | Supprimer le guard |
| 3 appels `/process` au lieu d'1 | Unmount/remount de CameraCapture pendant l'appel | `setShowCamera(false)` APRÈS `await processInput()` |
| Vidéo ne revient pas après Ajouter | `toBlob` asynchrone bloquait le retour | `canvas.toDataURL()` synchrone → play vidéo → `toBlob` en arrière-plan |
| Microphone saute le recording | Stream gardé en mémoire | `getUserMedia` à chaque fois, stop après usage |
| 401 sur endpoints chantiers | JWT TMA n'a pas `sub` | `_get_user_id(user)` helper |
| initTmaFetch pas dispo | Appelé seulement dans `page.tsx` | Déplacé dans `TelegramWebAppProvider` |
| Ressources = 0 | Filtre `chantier_id` trop restrictif | Fallback org-wide |
| Extraction lente | Modèle `gemini-2.5-flash` | `tma_extraction_model = lite` |

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

Le bouton WebApp du bot pointe automatiquement vers l'URL du frontend GCP (via `FRONTEND_URL` variable d'env du backend). En local, utiliser `TMA_HOST`.

## Endpoints backend

| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/api/v1/tma/auth` | Valide initData Telegram, retourne JWT (15 min) |
| GET | `/api/v1/tma/context` | Retourne chantier + user + org (JWT requis) |
| POST | `/api/v1/tma/extract` | Extraction structurée depuis texte (guardrails) |
| POST | `/api/v1/tma/process` | Endpoint unique : texte/audio/file → extraction structurée |
| POST | `/api/v1/tma/extract-file` | OCR depuis fichier (photo/PDF) |
| POST | `/api/v1/tma/transcribe` | Transcription audio via Gemini |
