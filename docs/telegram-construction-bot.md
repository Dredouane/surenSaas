# Construction Telegram Bot - Documentation

## Overview

The Construction Telegram bot allows users (site supervisors) to send invoices (photos or PDFs) directly from Telegram. OCR with **Google Gemini Flash 1.5** automatically extracts the data and creates an invoice in "draft" status.

### End-to-End Flow

```
Telegram site supervisor
        ↓
📎 Photo/PDF submission
        ↓
Webhook (/api/v1/{org_id}/telegram/webhook/{token})
        ↓
📥 File download → /tmp
        ↓
🔍 OCR Gemini Flash 1.5
        ↓
💾 Invoice Creation (status: draft)
        ↓
📋 Display of extracted data + buttons
   [✅ Validate] [✏️ Edit] [❌ Cancel]
        ↓
If ✅ Validated:
   → Status: en_attente_validation
   → 📧 Notification to managers
        ↓
Managers (Web App)
   → Final validation ✅/❌
   → 📧 Notification to the site supervisor
```

## Architecture

### File structure (Multi-Bot Structure)

```
surenSaasBack/app/api/
├── telegram_core.py              # Generic router + API Helpers (~200 lines)
├── bot_construction.py           # Construction-specific handler (~300 lines)
├── bot_construction_commands.py  # Construction commands (~150 lines)
├── telegram_invitation_service.py # Invitation link generation (existing)
└── [bot_livraison.py]            # ⬅️ Future bot (easy to add!)

app/services/telegram/
├── upload_invoice/
│   └── service.py                # Upload + Gemini OCR workflow (~180 lines)
├── notification_service.py       # Notifications to users (~230 lines)
└── audit_service.py              # Audit trail (~280 lines)

app/agents/
├── generic_extractor.py          # Gemini extractor (entry point)
├── base/gemini_client.py         # Vertex AI client
├── processors/file_processor.py  # File processing
└── prompts/extraction_prompts.py # System prompts
```

**Why this structure?**
- ✅ **Generic code** in `telegram_core.py` (reusable)
- ✅ **One file = one bot** (`bot_construction.py`, `bot_livraison.py`, etc.)
- ✅ Easy to add a new bot (copy/paste + adapt)
- ✅ Clear separation between generic and specific

### Generic vs Specific Code

| Generic (`telegram_core.py`) | Specific (`bot_construction.py`) |
|-------------------------------|-----------------------------------|
| Webhook router | Message/file handler |
| Dispatch by `bot_slug` | Business workflow (invoices) |
| Telegram API helpers | Specific commands |
| Authentication | References `slug='construction'` |
| Message sending | Custom callbacks |

### File descriptions

#### `telegram_core.py` - Generic Core
- **Route**: `POST /api/v1/{org_id}/telegram/webhook/{token}`
- **Generic functions**:
  - `handle_telegram_webhook()` - Entry point
  - `_dispatch_message()` - Route to the right bot
  - `_dispatch_callback()` - Route the callbacks
  - `get_bot_token()` - Token retrieval
  - `send_simple_message()` - Message sending
  - `send_message_with_keyboard()` - Message + buttons
  - `answer_callback()` - Acknowledgment

#### `bot_construction.py` - Construction Bot
- **Specific functions**:
  - `handle_construction_message()` - Construction dispatcher
  - `handle_invoice_upload()` - Invoice upload workflow
  - `_download_telegram_file()` - File download
  - `_send_extraction_result()` - OCR result display
  - `handle_invoice_validation()` - Invoice validation
  - `handle_invoice_cancellation()` - Invoice cancellation

#### `bot_construction_commands.py` - Construction Commands
- **Functions**:
  - `handle_construction_callback()` - Callback dispatcher
  - `handle_start_command()` - Onboarding
  - `handle_service_callback()` - Menu buttons
  - `send_menu_message()` - Main menu
  - `_send_welcome_message()` - Welcome

### Adding a new bot (e.g.: Delivery Bot)

To add a new bot in 3 steps:

**1. Create the files**:
```bash
touch app/api/bot_livraison.py
touch app/api/bot_livraison_commands.py
```

**2. Implement the handlers**:
```python
# bot_livraison.py
async def handle_livraison_message(message, bot_config, supabase, org_id):
    # Your business logic here
    pass

# bot_livraison_commands.py  
async def handle_livraison_callback(callback_query, ...):
    # Your callbacks here
    pass
```

**3. Add to the dispatcher** (`telegram_core.py`):
```python
async def _dispatch_message(..., bot_slug):
    if bot_slug == 'construction':
        from app.api.bot_construction import handle_construction_message
        return await handle_construction_message(...)
    elif bot_slug == 'livraison':  # ⬅️ NEW
        from app.api.bot_livraison import handle_livraison_message
        return await handle_livraison_message(...)
```

And there you go! The new bot is functional.

## Configuration

### Required environment variables

```bash
# Construction Telegram Bot
SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN="your_bot_father_token"
SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_test_bot"

# Production
SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_TOKEN="..."
SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_bot"

# Gemini API (OCR)
SUREN_TEST_GOOGLE_GEMINI_CREDENTIALS_B64="base64_api_key"
# or
SUREN_PROD_GOOGLE_GEMINI_CREDENTIALS_B64="base64_api_key"

# Secrets (optional)
TELEGRAM_INVITATION_SECRET="long_secret_for_signing_invitations"
TELEGRAM_WEBHOOK_SECRET_TEST="webhook_secret"
```

### Telegram Webhook Setup

```bash
# 1. Get the variables
export BOT_TOKEN="your_token"
export WEBHOOK_URL="https://api-test.yourdomain.com/api/v1/{org_id}/telegram/webhook/{token}"

# 2. Configure the webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${WEBHOOK_URL}\",
    \"secret_token\": \"your_webhook_secret\"
  }"

# 3. Verify
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

## Detailed workflow

### 1. User onboarding

**In the web app (Admin > Users):**
1. Admin clicks "Invite to Telegram"
2. Link generation: `https://t.me/bot?start={user_uuid}`
3. User opens the link in Telegram
4. User sends `/start`
5. Bot links the Telegram account to the app account

**Technical steps:**

#### A. Webhook reception (`telegram_main.py`)
```python
@router.post("/api/v1/{org_id}/telegram/webhook/{webhook_token}")
async def handle_telegram_webhook(...)
    # Bot authentication
    # Dispatch to handlers by type
```

#### B. File download (`telegram_invoice.py`)
```python
async def _download_telegram_file(message, bot_token):
    # 1. getFile to get file_path
    # 2. Download from Telegram CDN  
    # 3. Store in /tmp (temporary file)
    return "/tmp/tmp_xxx.pdf"
```

#### C. OCR with Gemini (`upload_invoice/service.py`)
```python
extractor = create_invoice_extractor()  # Gemini Flash 1.5
result = await extractor.extract(file_path, file_type='pdf'|'image')
```

**Extracted data:**
- Supplier (name, address, SIRET)
- Invoice (number, date, due date)
- Amounts (HT, TTC, VAT, rate)
- Description/items
- Confidence score

#### D. Invoice creation
```python
# Status: draft
# ocr_data: Raw Gemini result
# metadata: audit_log_id, confidence_score, etc.
```

#### E. User interaction (`telegram_invoice.py::_send_extraction_result`)
The bot displays:
```
✅ Invoice successfully analyzed!

📋 Extracted details:
• Supplier: Matériaux Pro SARL
• Invoice No.: FAC-2024-001
• Date: 2024-01-15
• HT amount: 1000.00€
• TTC amount: 1200.00€
• VAT: 200.00€ (20%)

[✅ Validate] [✏️ Edit] [❌ Cancel]
```

**Callbacks:**
- `invoice:validate:{invoice_id}` → `handle_invoice_validation()`
- `invoice:edit:{invoice_id}` → "coming soon" message
- `invoice:cancel:{invoice_id}` → `handle_invoice_cancellation()`

### 2. Validation by the managers

**Web App:**
- Invoice dashboard with "en_attente_validation" filter
- Detail view with Validate/Reject buttons
- Comment required if rejected

**Notifications:**
- Managers receive a Telegram notification
- Site supervisor notified of the result

## File storage

**Current:** Files temporarily stored in `/tmp`

```python
# Storage in the DB
original_file_url: "/tmp/tmp_xxx.pdf"  # TEMPORARY

# TODO: Migrate to S3 when service is chosen
# original_file_url: "s3://bucket/invoices/{org_id}/{invoice_id}/invoice.pdf"
```

**Next storage steps:**
1. Choose an S3 service (AWS, GCP, etc.)
2. Upload file to S3 after OCR
3. Update `original_file_url` with a public/presigned URL
4. Clean /tmp after successful upload

## Points of attention

### Security
- ✅ Telegram tokens in environment variables (not in DB)
- ✅ Webhook secret verification
- ✅ RLS policies on all tables
- ✅ Capability checks (`construction:facturation:write`)
- ✅ Temporary files in /tmp with unique names

### Performance
- Telegram download: ~1-5s depending on size
- Gemini OCR: ~3-10s depending on complexity
- Total timeout: 60s max

### Gemini limitations
- Max 20 MB per file
- Max 5 pages for PDF
- Images: max 4096x4096 pixels

## Monitoring

### Important logs
```
📨 Telegram webhook received
📎 Invoice upload received
✅ File downloaded: {n} bytes
🔍 Starting OCR
✅ OCR finished - Supplier: {name}, Confidence: {score}
📋 Invoice created: {invoice_id}
🔘 Callback received: invoice:validate:{id}
```

### Audit tables
- `telegram_audit` - Logs of all interactions
- `invoice_status_history` - History of status changes

**Note on enums:**
The `telegram_interaction_type` enum contains the following values:
- `message_received`, `command_received`, `button_clicked`
- `file_received` ← Used for invoice uploads
- `workflow_started`, `workflow_step`, `workflow_completed`, `workflow_failed`
- `notification_sent`, `error`

To add `invoice_upload` to the enum, run the migration:
```bash
# 017_add_invoice_upload_to_enum.sql
ALTER TYPE telegram_interaction_type ADD VALUE 'invoice_upload';
```

## Tests

### Test scenarios

1. **Onboarding:**
   - Invitation link → /start → Account linked ✅

2. **Photo upload:**
   - JPG photo → OCR → Invoice created → Validation ✅

3. **PDF upload:**
   - Multi-page PDF → OCR → Data extraction ✅

4. **Callbacks:**
   - Validate → Status changed + Managers notified ✅
   - Cancel → Invoice deleted ✅

5. **Errors:**
   - Unauthorized user → Error message ✅
   - File too big → Error ✅
   - OCR fails → User message ✅

## Migration from the old structure

**Old structure (monolithic):**
```
app/api/telegram_webhooks.py  # Single 800+ line file
```

**Intermediate structure:**
```
app/api/telegram_main.py   # Main router
app/api/telegram_invoice.py   # Invoice handling
app/api/telegram_commands.py  # Commands
app/api/telegram_helpers.py   # API helpers
```

**New structure (multi-bot):**
```
app/api/telegram_core.py              # Generic core (router + helpers)
app/api/bot_construction.py           # Construction Bot
app/api/bot_construction_commands.py  # Construction Commands
```

**Recent changes:**
- ✅ Router and helpers merged into `telegram_core.py`
- ✅ Files renamed with `bot_` prefix
- ✅ Import updated in `main.py`
- ✅ Dynamic dispatch by `bot_slug`
- ✅ Webhook URLs unchanged

## Support & Debugging

### Common problems

**"Token not found"**
→ Check the `SUREN_{ENV}_TELEGRAM_*` environment variables

**"OCR fails"**
→ Check `SUREN_{ENV}_GOOGLE_GEMINI_CREDENTIALS_B64`
→ Check Google Cloud API quotas

**"File too big"**
→ Telegram limit: 20 MB
→ Gemini limit: 20 MB

**"User not found"**
→ Verify the user has linked their account via /start

**"invalid input value for enum telegram_interaction_type"**
→ Run the migration `017_add_invoice_upload_to_enum.sql`
→ Or use `file_received` instead of `invoice_upload`

**"No module named 'telegram_invoice'" (or other module)**
→ Check the imports use the absolute format: `from app.api.xxx import ...`
→ Avoid relative imports: `from xxx import ...`
→ The Cloud Run deployment requires fully qualified absolute imports

### Useful commands

```bash
# Check Cloud Run logs
gcloud logs read "resource.type=cloud_run_revision" \
  --limit=50 \
  --format="value(textPayload)"

# Test the webhook locally
curl -X POST http://localhost:8000/api/v1/{org}/telegram/webhook/{token} \
  -H "Content-Type: application/json" \
  -d @test_webhook_payload.json
```

## Roadmap

- [ ] S3 upload (to implement when service is chosen)
- [ ] Invoice editing (inline Telegram editing)
- [ ] Improved multi-page PDF support
- [ ] OCR cache (avoid re-extraction)
- [ ] Metrics: average processing time, OCR success rate

---

**Last update:** 2024
**Structure:** Flat (4 files in app/api/)
**Status:** ✅ End-to-End working with Gemini Flash 1.5
