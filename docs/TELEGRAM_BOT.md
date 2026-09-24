# Telegram Bot - Construction Invoicing

## Overview

This Telegram bot allows site supervisors to submit invoices from the field via their mobile phone.

## Architecture

```
Telegram site supervisor
        ↓
   Photo/PDF submission
        ↓
   Telegram Webhook
        ↓
   Handler Service
        ↓
   Invoice Upload Service
        ↓
   OCR (stub)
        ↓
   Invoice Creation (draft)
        ↓
   Notification to Managers
```

## Primitives (Buttons/Actions)

### 1. Invoice Upload (`upload_invoice/`)
- **File**: `services/telegram/upload_invoice/service.py`
- **Action**: Receiving and processing an invoice photo or PDF
- **Workflow**:
  1. File reception
  2. Validation that user is authorized
  3. OCR (stub - returns sample data)
  4. Invoice creation in "draft" status
  5. Notification to managers

## Configuration

### Prerequisites

1. **Create a bot via @BotFather**:
   - Go to Telegram and search for @BotFather
   - Send `/newbot`
   - Follow the instructions to name your bot
   - Get the token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Environment configuration**:

Add to your `~/.bashrc`:

```bash
# Telegram Bot Configuration
export TELEGRAM_BOT_TOKEN="your_token_here"
export API_BASE_URL="https://your-backend.run.app"

# Supabase (normally already configured)
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_SERVICE_KEY="your_service_key"
```

Then reload:
```bash
source ~/.bashrc
```

### Bot initialization

```bash
# From the project root
cd surenSaasBack

# Install dependencies if needed
pip install httpx supabase

# Run the initialization script
python ../scripts/init-telegram-bot.py \
    --org-id "your-org-uuid" \
    --company-id "construction-company-uuid" \
    --description "Construction site invoicing bot"
```

### Script options

| Option | Required | Description |
|--------|--------|-------------|
| `--org-id` | Yes | UUID of the organization |
| `--company-id` | No | UUID of the subsidiary company |
| `--description` | No | Bot description |
| `--skip-db` | No | Test mode (no DB creation) |

## Services structure

```
services/telegram/
├── __init__.py
├── bot_manager.py           # Bot lifecycle management
├── webhook_handler.py       # Incoming webhook handler
├── notification_service.py  # User notifications
├── audit_service.py         # Interaction audit
└── upload_invoice/          # Primitive: invoice upload
    └── service.py
```

## Security

### Webhook Verification
Telegram webhooks are secured by:
1. **Token hash**: The URL contains a hash of the token (not the token in clear text)
2. **Secret token**: Header `X-Telegram-Bot-Api-Secret-Token` verified
3. **IP filtering**: Telegram sends from known IPs (optional)

### User Authorization
Each interaction checks:
1. Telegram user linked to an app account (`telegram_users`)
2. Required capability (`construction:facturation:write`)
3. Membership in the organization

## Database Tables

### telegram_bots
Bot configuration.

### telegram_users
Link between Telegram ID and User ID.

### telegram_audit
Audit of all interactions (monitoring/debugging).

## Invoice Upload Workflow

```python
# 1. Webhook reception
POST /{org}/telegram/webhook/{token_hash}

# 2. Handler dispatch
webhook_handler.handle_update() → upload_invoice.start_workflow()

# 3. Checks
- User authorized
- Capability present

# 4. OCR (stub)
_invoice_upload_service._perform_ocr()
# Returns: ExtractedInvoiceData (sample for now)

# 5. Invoice creation
_invoices table → status='brouillon'

# 6. Notification
notification_service.notify_invoice_pending()
```

## Invoice Statuses

| Status | Description |
|--------|-------------|
| `brouillon` | Created via OCR, awaiting supervisor validation |
| `en_attente_validation` | Submitted, awaiting manager |
| `validee` | Validated by manager |
| `rejetee` | Rejected by manager |
| `en_traitement_comptable` | Forwarded to accounting |
| `archivee` | Processed and archived |

## Monitoring

### Audit logs
```sql
-- See the last 50 interactions
SELECT * FROM telegram_audit 
WHERE org_id = 'uuid'
ORDER BY created_at DESC 
LIMIT 50;
```

### Recent errors
```sql
-- See errors from the last 24 hours
SELECT * FROM telegram_audit 
WHERE org_id = 'uuid' 
AND status = 'failed'
AND created_at > NOW() - INTERVAL '24 hours';
```

### Stats
```bash
# Via the API
GET /{org}/telegram/audit?limit=100
```

## Troubleshooting

### Bot does not respond
1. Verify the webhook is configured: `python scripts/init-telegram-bot.py --skip-db`
2. Verify the URL is reachable from the internet
3. Verify audit logs: `status = 'failed'`

### User not authorized
- Verify the user has started the bot: `telegram_users.is_verified = true`
- Verify the capability: `user_capabilities` table

### Webhook 401 errors
- Verify the `webhook_secret` matches
- Verify header `X-Telegram-Bot-Api-Secret-Token`

## Future development

### Adding a new primitive

1. Create folder: `services/telegram/primitive_name/`
2. Create `service.py` with the logic
3. Add handler in `webhook_handler.py`
4. Update `openapi/api.yaml`
5. Document in this file

### Implementing the OCR

The file `services/telegram/upload_invoice/service.py` contains a `_perform_ocr()` method that currently returns sample data.

To implement:
1. Create the `app/agents/invoice_ocr/` folder
2. Implement the agentic workflow
3. Call the agent from `_perform_ocr()`

## References

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Webhook Setup](https://core.telegram.org/bots/webhooks)
- OpenAPI: `/openapi/api.yaml`
