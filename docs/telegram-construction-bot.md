# Bot Telegram Construction - Documentation

## Vue d'ensemble

Le bot Telegram Construction permet aux utilisateurs (conducteurs de travaux) d'envoyer des factures (photos ou PDF) directement depuis Telegram. L'OCR avec **Google Gemini Flash 1.5** extrait automatiquement les données et crée une facture en statut "brouillon".

### Flux End-to-End

```
Conducteur Telegram
        ↓
📎 Envoi Photo/PDF
        ↓
Webhook (/api/v1/{org_id}/telegram/webhook/{token})
        ↓
📥 Téléchargement fichier → /tmp
        ↓
🔍 OCR Gemini Flash 1.5
        ↓
💾 Création Facture (status: brouillon)
        ↓
📋 Affichage données extraites + boutons
   [✅ Valider] [✏️ Modifier] [❌ Annuler]
        ↓
Si ✅ Validé:
   → Status: en_attente_validation
   → 📧 Notification aux gérants
        ↓
Gérants (Web App)
   → Validation finale ✅/❌
   → 📧 Notification au conducteur
```

## Architecture

### Structure des fichiers (Structure Multi-Bot)

```
surenSaasBack/app/api/
├── telegram_core.py              # Router générique + Helpers API (~200 lignes)
├── bot_construction.py           # Handler spécifique Construction (~300 lignes)
├── bot_construction_commands.py  # Commandes Construction (~150 lignes)
├── telegram_invitation_service.py # Génération liens d'invitation (existant)
└── [bot_livraison.py]            # ⬅️ Futur bot (facile à ajouter !)

app/services/telegram/
├── upload_invoice/
│   └── service.py                # Workflow upload + OCR Gemini (~180 lignes)
├── notification_service.py       # Notifications aux utilisateurs (~230 lignes)
└── audit_service.py              # Audit trail (~280 lignes)

app/agents/
├── generic_extractor.py          # Extracteur Gemini (point d'entrée)
├── base/gemini_client.py         # Client Vertex AI
├── processors/file_processor.py  # Traitement fichiers
└── prompts/extraction_prompts.py # Prompts système
```

**Pourquoi cette structure ?**
- ✅ **Code générique** dans `telegram_core.py` (réutilisable)
- ✅ **Un fichier = un bot** (`bot_construction.py`, `bot_livraison.py`, etc.)
- ✅ Facile d'ajouter un nouveau bot (copier/coller + adapter)
- ✅ Séparation claire entre générique et spécifique

### Code Générique vs Spécifique

| Générique (`telegram_core.py`) | Spécifique (`bot_construction.py`) |
|-------------------------------|-----------------------------------|
| Router webhook | Handler messages/fichiers |
| Dispatch selon `bot_slug` | Workflow métier (factures) |
| Helpers API Telegram | Commandes spécifiques |
| Authentification | Références `slug='construction'` |
| Envoi messages | Callbacks personnalisés |

### Description des fichiers

#### `telegram_core.py` - Core Générique
- **Route**: `POST /api/v1/{org_id}/telegram/webhook/{token}`
- **Fonctions génériques**:
  - `handle_telegram_webhook()` - Point d'entrée
  - `_dispatch_message()` - Route vers le bon bot
  - `_dispatch_callback()` - Route les callbacks
  - `get_bot_token()` - Récupération token
  - `send_simple_message()` - Envoi message
  - `send_message_with_keyboard()` - Message + boutons
  - `answer_callback()` - Accusé réception

#### `bot_construction.py` - Bot Construction
- **Fonctions spécifiques**:
  - `handle_construction_message()` - Dispatcher construction
  - `handle_invoice_upload()` - Workflow upload facture
  - `_download_telegram_file()` - Téléchargement fichier
  - `_send_extraction_result()` - Affichage résultat OCR
  - `handle_invoice_validation()` - Validation facture
  - `handle_invoice_cancellation()` - Annulation facture

#### `bot_construction_commands.py` - Commandes Construction
- **Fonctions**:
  - `handle_construction_callback()` - Dispatcher callbacks
  - `handle_start_command()` - Onboarding
  - `handle_service_callback()` - Boutons menu
  - `send_menu_message()` - Menu principal
  - `_send_welcome_message()` - Bienvenue

### Ajouter un nouveau bot (ex: Bot Livraison)

Pour ajouter un nouveau bot en 3 étapes :

**1. Créer les fichiers**:
```bash
touch app/api/bot_livraison.py
touch app/api/bot_livraison_commands.py
```

**2. Implémenter les handlers**:
```python
# bot_livraison.py
async def handle_livraison_message(message, bot_config, supabase, org_id):
    # Votre logique métier ici
    pass

# bot_livraison_commands.py  
async def handle_livraison_callback(callback_query, ...):
    # Vos callbacks ici
    pass
```

**3. Ajouter au dispatcher** (`telegram_core.py`):
```python
async def _dispatch_message(..., bot_slug):
    if bot_slug == 'construction':
        from app.api.bot_construction import handle_construction_message
        return await handle_construction_message(...)
    elif bot_slug == 'livraison':  # ⬅️ NOUVEAU
        from app.api.bot_livraison import handle_livraison_message
        return await handle_livraison_message(...)
```

Et voilà ! Le nouveau bot est fonctionnel.

## Configuration

### Variables d'environnement requises

```bash
# Bot Telegram Construction
SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN="votre_token_bot_father"
SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_test_bot"

# Production
SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_TOKEN="..."
SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_bot"

# Gemini API (OCR)
SUREN_TEST_GOOGLE_GEMINI_CREDENTIALS_B64="base64_api_key"
# ou
SUREN_PROD_GOOGLE_GEMINI_CREDENTIALS_B64="base64_api_key"

# Secrets (optionnels)
TELEGRAM_INVITATION_SECRET="secret_long_pour_signer_invitations"
TELEGRAM_WEBHOOK_SECRET_TEST="secret_webhook"
```

### Setup Webhook Telegram

```bash
# 1. Récupérer les variables
export BOT_TOKEN="votre_token"
export WEBHOOK_URL="https://api-test.votredomaine.com/api/v1/{org_id}/telegram/webhook/{token}"

# 2. Configurer le webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${WEBHOOK_URL}\",
    \"secret_token\": \"votre_secret_webhook\"
  }"

# 3. Vérifier
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

## Workflow détaillé

### 1. Onboarding utilisateur

**Dans l'application web (Admin > Utilisateurs):**
1. Admin clique "Inviter sur Telegram" 
2. Génération lien: `https://t.me/bot?start={user_uuid}`
3. Utilisateur clique le lien → ouvre Telegram
4. Bot exécute `/start {user_uuid}`
5. Liaison automatique compte Telegram ↔ User

**Fichiers concernés:**
- `telegram_invitation_service.py` - Génération liens
- `telegram_commands.py::handle_start_command()` - Liaison compte

### 2. Envoi de facture

**Étapes techniques:**

#### A. Réception webhook (`telegram_main.py`)
```python
@router.post("/api/v1/{org_id}/telegram/webhook/{webhook_token}")
async def handle_telegram_webhook(...)
    # Authentification bot
    # Dispatch vers handlers selon type
```

#### B. Téléchargement fichier (`telegram_invoice.py`)
```python
async def _download_telegram_file(message, bot_token):
    # 1. getFile pour obtenir file_path
    # 2. Téléchargement depuis Telegram CDN  
    # 3. Stockage dans /tmp (fichier temporaire)
    return "/tmp/tmp_xxx.pdf"
```

#### C. OCR avec Gemini (`upload_invoice/service.py`)
```python
extractor = create_invoice_extractor()  # Gemini Flash 1.5
result = await extractor.extract(file_path, file_type='pdf'|'image')
```

**Données extraites:**
- Fournisseur (nom, adresse, SIRET)
- Facture (numéro, date, échéance)
- Montants (HT, TTC, TVA, taux)
- Description/articles
- Score de confiance

#### D. Création facture
```python
# Status: brouillon
# ocr_data: Résultat brut Gemini
# metadata: audit_log_id, confidence_score, etc.
```

#### E. Interaction utilisateur (`telegram_invoice.py::_send_extraction_result`)
Le bot affiche:
```
✅ Facture analysée avec succès !

📋 Détails extraits :
• Fournisseur: Matériaux Pro SARL
• N° Facture: FAC-2024-001
• Date: 2024-01-15
• Montant HT: 1000.00€
• Montant TTC: 1200.00€
• TVA: 200.00€ (20%)

[✅ Valider] [✏️ Modifier] [❌ Annuler]
```

**Callbacks:**
- `invoice:validate:{invoice_id}` → `handle_invoice_validation()`
- `invoice:edit:{invoice_id}` → Message "à venir"
- `invoice:cancel:{invoice_id}` → `handle_invoice_cancellation()`

### 3. Validation par les gérants

**Web App:**
- Dashboard factures avec filtre "en_attente_validation"
- Vue détail avec boutons Valider/Rejeter
- Commentaire obligatoire si rejet

**Notifications:**
- Gérants reçoivent notification Telegram
- Conducteur notifié du résultat

## Stockage fichiers

**Actuel:** Fichiers stockés temporairement dans `/tmp`

```python
# Stockage dans la DB
original_file_url: "/tmp/tmp_xxx.pdf"  # TEMPORAIRE

# TODO: Migrer vers S3 quand service choisi
# original_file_url: "s3://bucket/invoices/{org_id}/{invoice_id}/facture.pdf"
```

**Prochaines étapes stockage:**
1. Choisir service S3 (AWS, GCP, etc.)
2. Upload fichier vers S3 après OCR
3. Mettre à jour `original_file_url` avec URL publique/presignée
4. Nettoyer /tmp après upload réussi

## Points d'attention

### Sécurité
- ✅ Tokens Telegram en variables d'environnement (pas en DB)
- ✅ Vérification webhook secret
- ✅ RLS policies sur toutes les tables
- ✅ Capability checks (`construction:facturation:write`)
- ✅ Fichiers temporaires dans /tmp avec noms uniques

### Performance
- Téléchargement Telegram: ~1-5s selon taille
- OCR Gemini: ~3-10s selon complexité
- Timeout total: 60s max

### Limitations Gemini
- Max 20 MB par fichier
- Max 5 pages pour PDF
- Images: max 4096x4096 pixels

## Monitoring

### Logs importants
```
📨 Webhook Telegram reçu
📎 Upload de facture reçu
✅ Fichier téléchargé: {n} bytes
🔍 Démarrage OCR
✅ OCR terminé - Fournisseur: {name}, Confiance: {score}
📋 Facture créée: {invoice_id}
🔘 Callback reçu: invoice:validate:{id}
```

### Tables d'audit
- `telegram_audit` - Logs toutes les interactions
- `invoice_status_history` - Historique changements status

**Note sur les enums:**
L'enum `telegram_interaction_type` contient les valeurs suivantes:
- `message_received`, `command_received`, `button_clicked`
- `file_received` ← Utilisé pour les uploads de factures
- `workflow_started`, `workflow_step`, `workflow_completed`, `workflow_failed`
- `notification_sent`, `error`

Pour ajouter `invoice_upload` à l'enum, exécutez la migration:
```bash
# 017_add_invoice_upload_to_enum.sql
ALTER TYPE telegram_interaction_type ADD VALUE 'invoice_upload';
```

## Tests

### Scénarios de test

1. **Onboarding:**
   - Lien invitation → /start → Compte lié ✅

2. **Upload photo:**
   - Photo JPG → OCR → Facture créée → Validation ✅

3. **Upload PDF:**
   - PDF multi-pages → OCR → Extraction données ✅

4. **Callbacks:**
   - Valider → Status changé + Notif gérants ✅
   - Annuler → Suppression facture ✅

5. **Erreurs:**
   - User non autorisé → Message d'erreur ✅
   - Fichier trop gros → Erreur ✅
   - OCR échoue → Message utilisateur ✅

## Migration depuis l'ancienne structure

**Ancienne structure (monolithique):**
```
app/api/telegram_webhooks.py  # 1 fichier de 800+ lignes
```

**Structure intermédiaire:**
```
app/api/telegram_main.py      # Router principal
app/api/telegram_invoice.py   # Gestion factures
app/api/telegram_commands.py  # Commandes
app/api/telegram_helpers.py   # Helpers API
```

**Nouvelle structure (multi-bot):**
```
app/api/telegram_core.py              # Core générique (router + helpers)
app/api/bot_construction.py           # Bot Construction
app/api/bot_construction_commands.py  # Commandes Construction
```

**Changements récents:**
- ✅ Router et helpers fusionnés dans `telegram_core.py`
- ✅ Fichiers renommés avec préfixe `bot_`
- ✅ Import mis à jour dans `main.py`
- ✅ Dispatch dynamique selon `bot_slug`
- ✅ URLs webhook inchangées

## Support & Debugging

### Problèmes courants

**"Token non trouvé"**
→ Vérifier variables d'environnement `SUREN_{ENV}_TELEGRAM_*`

**"OCR échoue"**
→ Vérifier `SUREN_{ENV}_GOOGLE_GEMINI_CREDENTIALS_B64`
→ Vérifier quotas API Google Cloud

**"Fichier trop gros"**
→ Limite Telegram: 20 MB
→ Limite Gemini: 20 MB

**"User non trouvé"**
→ Vérifier que user a bien lié son compte via /start

**"invalid input value for enum telegram_interaction_type"**
→ Exécutez la migration `017_add_invoice_upload_to_enum.sql`
→ Ou utilisez `file_received` au lieu de `invoice_upload`

**"No module named 'telegram_invoice'" (ou autre module)**
→ Vérifiez que les imports utilisent le format absolu : `from app.api.xxx import ...`
→ Évitez les imports relatifs : `from xxx import ...`
→ Le déploiement Cloud Run nécessite des imports absolus complets

### Commandes utiles

```bash
# Vérifier logs Cloud Run
gcloud logs read "resource.type=cloud_run_revision" \
  --limit=50 \
  --format="value(textPayload)"

# Tester webhook localement
curl -X POST http://localhost:8000/api/v1/{org}/telegram/webhook/{token} \
  -H "Content-Type: application/json" \
  -d @test_webhook_payload.json
```

## Roadmap

- [ ] Upload S3 (à implémenter quand service choisi)
- [ ] Modification facture (édition inline Telegram)
- [ ] Support multi-pages PDF amélioré
- [ ] Cache OCR (éviter re-extraction)
- [ ] Métriques: temps moyen traitement, taux succès OCR

---

**Dernière mise à jour:** 2024
**Structure:** Plate (4 fichiers dans app/api/)
**Statut:** ✅ End-to-End fonctionnel avec Gemini Flash 1.5
