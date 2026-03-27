# Bot Telegram - Facturation Chantiers

## Vue d'ensemble

Ce bot Telegram permet aux conducteurs de travaux de soumettre des factures depuis le terrain via leur téléphone mobile.

## Architecture

```
Conducteur Telegram
        ↓
   Envoi photo/PDF
        ↓
   Webhook Telegram
        ↓
   Handler Service
        ↓
   Invoice Upload Service
        ↓
   OCR (coquille)
        ↓
   Création Facture (brouillon)
        ↓
   Notification Gérants
```

## Primitives (Boutons/Actions)

### 1. Upload Facture (`upload_invoice/`)
- **Fichier**: `services/telegram/upload_invoice/service.py`
- **Action**: Réception et traitement d'une photo ou PDF de facture
- **Workflow**:
  1. Réception fichier
  2. Validation user autorisé
  3. OCR (coquille - retourne données d'exemple)
  4. Création facture en status "brouillon"
  5. Notification gérants

## Configuration

### Prérequis

1. **Créer un bot via @BotFather**:
   - Allez sur Telegram et cherchez @BotFather
   - Envoyez `/newbot`
   - Suivez les instructions pour nommer votre bot
   - Récupérez le token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Configuration environnement**:

Ajoutez dans votre `~/.bashrc`:

```bash
# Telegram Bot Configuration
export TELEGRAM_BOT_TOKEN="votre_token_ici"
export API_BASE_URL="https://votre-backend.run.app"

# Supabase (déjà configuré normalement)
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_SERVICE_KEY="votre_clé_service"
```

Puis rechargez:
```bash
source ~/.bashrc
```

### Initialisation du bot

```bash
# Depuis la racine du projet
cd surenSaasBack

# Installer les dépendances si nécessaire
pip install httpx supabase

# Lancer le script d'initialisation
python ../scripts/init-telegram-bot.py \
    --org-id "uuid-de-votre-org" \
    --company-id "uuid-de-lentreprise-construction" \
    --description "Bot facturation chantiers"
```

### Options du script

| Option | Requis | Description |
|--------|--------|-------------|
| `--org-id` | Oui | UUID de l'organisation |
| `--company-id` | Non | UUID de l'entreprise filiale |
| `--description` | Non | Description du bot |
| `--skip-db` | Non | Mode test (pas de création en base) |

## Structure des services

```
services/telegram/
├── __init__.py
├── bot_manager.py           # Gestion lifecycle bot
├── webhook_handler.py       # Handler webhooks entrants
├── notification_service.py  # Notifications users
├── audit_service.py         # Audit interactions
└── upload_invoice/          # Primitive: upload facture
    └── service.py
```

## Security

### Webhook Verification
Les webhooks Telegram sont sécurisés par:
1. **Token hash**: L'URL contient un hash du token (pas le token en clair)
2. **Secret token**: Header `X-Telegram-Bot-Api-Secret-Token` vérifié
3. **IP filtering**: Telegram envoie depuis IPs connues (optionnel)

### User Authorization
Chaque interaction vérifie:
1. User Telegram lié à un compte app (`telegram_users`)
2. Capability requise (`construction:facturation:write`)
3. Appartenance à l'organisation

## Tables Database

### telegram_bots
Configuration des bots.

### telegram_users
Lien entre Telegram ID et User ID.

### telegram_audit
Audit de toutes les interactions (monitoring/debugging).

## Workflow Upload Facture

```python
# 1. Réception webhook
POST /{org}/telegram/webhook/{token_hash}

# 2. Handler dispatch
webhook_handler.handle_update() → upload_invoice.start_workflow()

# 3. Vérifications
- User autorisé
- Capability présente

# 4. OCR (coquille)
_invoice_upload_service._perform_ocr()
# Retourne: ExtractedInvoiceData (exemple pour l'instant)

# 5. Création facture
_invoices table → status='brouillon'

# 6. Notification
notification_service.notify_invoice_pending()
```

## Status Factures

| Status | Description |
|--------|-------------|
| `brouillon` | Créée via OCR, en attente validation conducteur |
| `en_attente_validation` | Soumise, en attente gérant |
| `validee` | Validée par gérant |
| `rejetee` | Rejetée par gérant |
| `en_traitement_comptable` | Transmise à la compta |
| `archivee` | Traitée et archivée |

## Monitoring

### Logs d'audit
```sql
-- Voir les 50 dernières interactions
SELECT * FROM telegram_audit 
WHERE org_id = 'uuid'
ORDER BY created_at DESC 
LIMIT 50;
```

### Erreurs récentes
```sql
-- Voir les erreurs des dernières 24h
SELECT * FROM telegram_audit 
WHERE org_id = 'uuid' 
AND status = 'failed'
AND created_at > NOW() - INTERVAL '24 hours';
```

### Stats
```bash
# Via l'API
GET /{org}/telegram/audit?limit=100
```

## Troubleshooting

### Bot ne répond pas
1. Vérifier webhook configuré: `python scripts/init-telegram-bot.py --skip-db`
2. Vérifier URL accessible depuis internet
3. Vérifier logs audit: `status = 'failed'`

### User non autorisé
- Vérifier que le user a démarré le bot: `telegram_users.is_verified = true`
- Vérifier la capability: `user_capabilities` table

### Webhook erreurs 401
- Vérifier le `webhook_secret` correspond
- Vérifier header `X-Telegram-Bot-Api-Secret-Token`

## Développement futur

### Ajouter une nouvelle primitive

1. Créer dossier: `services/telegram/nom_primitive/`
2. Créer `service.py` avec la logique
3. Ajouter handler dans `webhook_handler.py`
4. Mettre à jour `openapi/api.yaml`
5. Documenter dans ce fichier

### Implémenter l'OCR

Le fichier `services/telegram/upload_invoice/service.py` contient une méthode `_perform_ocr()` qui retourne actuellement des données d'exemple.

Pour implémenter:
1. Créer le dossier `app/agents/invoice_ocr/`
2. Implémenter le workflow agentic
3. Appeler l'agent depuis `_perform_ocr()`

## Références

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Webhook Setup](https://core.telegram.org/bots/webhooks)
- OpenAPI: `/openapi/api.yaml`
