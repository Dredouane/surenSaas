# Telegram Bot Construction - Multi-Bots Architecture

## Overview

The system now supports **multiple Telegram bots** for the same organization. Each bot has its own features and can be invited separately.

### Available bots

| Bot ID | Name | Description | Icon |
|--------|-----|-------------|-------|
| `construction` | Construction | Invoice submission and processing | 🏗️ |
| `audit` | Energy Audit | Managing audits and reports | ⚡ |
| `nettoyage` | Cleaning | Scheduling interventions | 🧹 |
| `general` | General | Notifications and information | 📢 |

## Configuration

### Environment variables

Add to your `~/.bashrc`:

```bash
# Construction Bot
export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN="XXX"
export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_test_bot"
export SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_TOKEN="YYY"
export SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_bot"

# Audit Bot (optional)
export SUREN_TEST_TELEGRAM_AUDIT_BOT_TOKEN="..."
export SUREN_TEST_TELEGRAM_AUDIT_BOT_USERNAME="suren_audit_test_bot"

# Nettoyage Bot (optional)
export SUREN_TEST_TELEGRAM_NETTOYAGE_BOT_TOKEN="..."
export SUREN_TEST_TELEGRAM_NETTOYAGE_BOT_USERNAME="suren_nettoyage_test_bot"
```

### Webhook configuration

Use the new shell script that loads variables from the bashrc:

```bash
# Make the script executable
chmod +x scripts/setup-construction-bot-webhook.sh

# Configure the test webhook
./scripts/setup-construction-bot-webhook.sh --env test

# Configure the prod webhook
./scripts/setup-construction-bot-webhook.sh --env prod

# Delete the webhook
./scripts/setup-construction-bot-webhook.sh --env test --delete
```

## API Endpoints

### List available bots
```
GET /api/v1/admin/telegram/bots
Auth: Admin
Response:
{
  "bots": [
    {
      "bot_id": "construction",
      "bot_name": "Construction",
      "description": "Invoice submission and processing",
      "icon": "🏗️",
      "username": "suren_construction_bot",
      "configured": true
    }
  ],
  "environment": "test"
}
```

### Generate an invitation
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
  "description": "Invoice submission and processing",
  "expires_at": "2024-01-15T12:00:00",
  "user_id": "...",
  "org_id": "..."
}
```

## User Interface

On the **Admin > Users** page:

1. Click the 📱 "Invite to Telegram" icon for a user
2. Select the bot from the dropdown list
3. Generate the invitation link
4. Copy the link or send it by email

## Onboarding flow

### 1. Admin invites a user
- The admin selects the appropriate bot (e.g.: Construction)
- Generates a signed invitation link
- Sends the link to the user

### 2. User joins the bot
- The user clicks the link `https://t.me/bot?start=PAYLOAD`
- The bot decodes the payload and verifies the signature
- The Telegram account is linked to the user account

### 3. Using the bot
- The user can send photos/PDFs according to the bot's features
- For the Construction bot: invoice submission with OCR

## Technical architecture

### Key files

```
surenSaasBack/
├── app/services/telegram/
│   ├── bots_registry.py           # Registry of available bots
│   ├── construction_bot_service.py # Construction bot service
│   └── ...
├── app/services/
│   └── telegram_invitation_service.py  # Multi-bot invitation management
├── app/api/
│   ├── admin.py                   # Admin routes (invitations)
│   └── construction_bot.py        # Webhook
└── app/agents/
    └── construction_invoice_agent.py   # OCR agent

surenSaasFront/
└── components/telegram/
    └── invitation-dialog.tsx      # Bot selection UI + QR code
```

### Security

- **Tokens**: Never in the DB, only in environment variables
- **Invitations**: Signed with HMAC + expiration
- **Webhook**: Optional verification with secret token
- **Isolation**: Each invitation is tied to a specific bot

## Adding a new bot

To add a new bot type:

1. **Create the bot** on Telegram via @BotFather

2. **Add the environment variables** in `~/.bashrc`:
```bash
export SUREN_TEST_TELEGRAM_MONBOT_BOT_TOKEN="..."
export SUREN_TEST_TELEGRAM_MONBOT_BOT_USERNAME="suren_monbot_test_bot"
```

3. **Update the registry** in `bots_registry.py`:
```python
BOTS_METADATA = {
    # ... existing bots ...
    'monbot': {
        'name': 'My Bot',
        'description': 'Description of features',
        'icon': '🤖',
    },
}
```

4. **Create the bot service** (optional) if specific logic:
```python
# app/services/telegram/monbot_service.py
class MonBotService:
    async def handle_update(self, update):
        # Bot-specific logic
        pass
```

5. **Create the webhook** (optional) if separate endpoint:
```python
# app/api/monbot.py
@router.post("/webhook/monbot")
async def handle_monbot_webhook(request: Request):
    # Processing of updates
    pass
```

The bot will be automatically detected and will appear in the list of available bots!

## Next steps

- [ ] Implement real OCR with GPT-4 Vision
- [ ] Add S3 storage for files
- [ ] Create the other bots (audit, nettoyage)
- [ ] Add usage statistics per bot
