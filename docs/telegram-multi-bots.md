# Bot Telegram Construction - Architecture Multi-Bots

## Vue d'ensemble

Le système supporte maintenant **plusieurs bots Telegram** pour une même organisation. Chaque bot a ses propres fonctionnalités et peut être invité séparément.

### Bots disponibles

| Bot ID | Nom | Description | Icône |
|--------|-----|-------------|-------|
| `construction` | Construction | Envoi et traitement des factures | 🏗️ |
| `audit` | Audit Énergétique | Gestion des audits et rapports | ⚡ |
| `nettoyage` | Nettoyage | Planification interventions | 🧹 |
| `general` | Général | Notifications et informations | 📢 |

## Configuration

### Variables d'environnement

Ajoutez dans votre `~/.bashrc` :

```bash
# Bot Construction
export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN="XXX"
export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_test_bot"
export SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_TOKEN="YYY"
export SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_bot"

# Bot Audit (optionnel)
export SUREN_TEST_TELEGRAM_AUDIT_BOT_TOKEN="..."
export SUREN_TEST_TELEGRAM_AUDIT_BOT_USERNAME="suren_audit_test_bot"

# Bot Nettoyage (optionnel)
export SUREN_TEST_TELEGRAM_NETTOYAGE_BOT_TOKEN="..."
export SUREN_TEST_TELEGRAM_NETTOYAGE_BOT_USERNAME="suren_nettoyage_test_bot"
```

### Configuration Webhook

Utilisez le nouveau script shell qui charge les variables depuis le bashrc :

```bash
# Rendre le script exécutable
chmod +x scripts/setup-construction-bot-webhook.sh

# Configurer le webhook test
./scripts/setup-construction-bot-webhook.sh --env test

# Configurer le webhook prod
./scripts/setup-construction-bot-webhook.sh --env prod

# Supprimer le webhook
./scripts/setup-construction-bot-webhook.sh --env test --delete
```

## API Endpoints

### Lister les bots disponibles
```
GET /api/v1/admin/telegram/bots
Auth: Admin
Response:
{
  "bots": [
    {
      "bot_id": "construction",
      "bot_name": "Construction",
      "description": "Envoi et traitement des factures",
      "icon": "🏗️",
      "username": "suren_construction_bot",
      "configured": true
    }
  ],
  "environment": "test"
}
```

### Générer une invitation
```
POST /api/v1/admin/users/{user_id}/telegram-invitation
Auth: Admin
Body:
{
  "bot_id": "construction",
  "expires_in_hours": 168
}
Response:
{
  "telegram_link": "https://t.me/suren_construction_bot?start=ABC...",
  "bot_id": "construction",
  "bot_name": "Construction",
  "bot_username": "suren_construction_bot",
  "bot_icon": "🏗️",
  "description": "Envoi et traitement des factures",
  "expires_at": "2024-01-15T12:00:00",
  "user_id": "...",
  "org_id": "..."
}
```

## Interface Utilisateur

Dans la page **Admin > Utilisateurs** :

1. Cliquez sur l'icône 📱 "Inviter sur Telegram" pour un utilisateur
2. Sélectionnez le bot dans la liste déroulante
3. Générez le lien d'invitation
4. Copiez le lien ou envoyez par email

## Flux d'onboarding

### 1. Admin invite un utilisateur
- L'admin sélectionne le bot approprié (ex: Construction)
- Génère un lien d'invitation signé
- Envoie le lien à l'utilisateur

### 2. Utilisateur rejoint le bot
- L'utilisateur clique sur le lien `https://t.me/bot?start=PAYLOAD`
- Le bot décode le payload et vérifie la signature
- Le compte Telegram est lié au compte utilisateur

### 3. Utilisation du bot
- L'utilisateur peut envoyer des photos/PDF selon les fonctionnalités du bot
- Pour le bot Construction : envoi de factures avec OCR

## Architecture technique

### Fichiers clés

```
surenSaasBack/
├── app/services/telegram/
│   ├── bots_registry.py           # Registre des bots disponibles
│   ├── construction_bot_service.py # Service bot construction
│   └── ...
├── app/services/
│   └── telegram_invitation_service.py  # Gestion invitations multi-bots
├── app/api/
│   ├── admin.py                   # Routes admin (invitations)
│   └── construction_bot.py        # Webhook
└── app/agents/
    └── construction_invoice_agent.py   # Agent OCR

surenSaasFront/
└── components/telegram/
    └── invitation-dialog.tsx      # UI sélection bot + QR code
```

### Sécurité

- **Tokens** : Jamais en DB, uniquement en variables d'environnement
- **Invitations** : Signées avec HMAC + expiration
- **Webhook** : Vérification optionnelle avec secret token
- **Isolation** : Chaque invitation est liée à un bot spécifique

## Ajouter un nouveau bot

Pour ajouter un nouveau type de bot :

1. **Créer le bot** sur Telegram via @BotFather

2. **Ajouter les variables d'environnement** dans `~/.bashrc` :
```bash
export SUREN_TEST_TELEGRAM_MONBOT_BOT_TOKEN="..."
export SUREN_TEST_TELEGRAM_MONBOT_BOT_USERNAME="suren_monbot_test_bot"
```

3. **Mettre à jour le registry** dans `bots_registry.py` :
```python
BOTS_METADATA = {
    # ... bots existants ...
    'monbot': {
        'name': 'Mon Bot',
        'description': 'Description des fonctionnalités',
        'icon': '🤖',
    },
}
```

4. **Créer le service bot** (optionnel) si logique spécifique :
```python
# app/services/telegram/monbot_service.py
class MonBotService:
    async def handle_update(self, update):
        # Logique spécifique au bot
        pass
```

5. **Créer le webhook** (optionnel) si endpoint séparé :
```python
# app/api/monbot.py
@router.post("/webhook/monbot")
async def handle_monbot_webhook(request: Request):
    # Traitement des updates
    pass
```

Le bot sera automatiquement détecté et apparaîtra dans la liste des bots disponibles !

## Prochaines étapes

- [ ] Implémenter l'OCR réel avec GPT-4 Vision
- [ ] Ajouter le stockage S3 pour les fichiers
- [ ] Créer les autres bots (audit, nettoyage)
- [ ] Ajouter des statistiques d'utilisation par bot
