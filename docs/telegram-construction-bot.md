# Documentation : Bot Telegram Construction

## Architecture Générique (PR 6)
Tous les modules métiers (Opérations, Pointages, Dépenses, Tâches) utilisent désormais `BaseTelegramWorkflow` pour standardiser :
1. **Extraction :** Via agent Gemini (découplé du métier).
2. **Cycle HITL :** Statut systématique `en_attente_validation`.
3. **Persistance :** JSONB `ocr_data` et `metadata` pour le suivi audit.

### Status workflows
*   **Opérations :** OK (Auto-création avec IA)
*   **Pointages :** OK (Paginations + Toggle + Validation)
*   **Dépenses :** OK (Workflow générique)
*   **Réunions :** OK (Liste + points)
*   **Factures :** Migré sur dispatcher, validation HITL active.

## Architecture détaillée (Session Avril 2026)

### Arborescence du dispatcher
```
app/api/
├── telegram_core.py                   # Router générique + helpers
├── bot_construction.py                # Dispatch principal + facture upload
├── bot_construction_commands.py       # Menu principal + callbacks → dispatche vers sous-modules
├── bot_construction_operations.py     # Opérations HTL (création, liste, validation)
├── bot_construction_pointages.py      # Pointages (présence, toggle, pagination)
├── bot_construction_taches.py         # Tâches (liste, marquer faite)
├── bot_construction_depenses.py       # Dépenses (création simple, consultation)
├── bot_construction_invoices.py       # Factures (validation, annulation)
└── bot_construction_receptions.py     # Réunions (liste, ajouter point)

app/services/telegram/
├── base_workflow.py                   # Moteur générique Workflow (extraction → validation → save)
├── construction_menu.py               # Logique des menus (layout + callbacks map)
├── chantier_context.py                # Sélection/persistance du chantier actif + state machine
├── upload_invoice/service.py          # (inchangé - workflow factures OCR)
├── notification_service.py            # Notifications
└── audit_service.py                   # Audit trail
```

### Workflow complet "Signaler une opération"
```
1. User clique "Signaler une opération" → menu sous-types
2. User choisit type (démolition, commande, etc.)
3. Bot set_state("op_awaiting_description") dans telegram_users.last_state
4. User envoie texte/photo/vocal
5. bot_construction.py détecte state → appelle handle_operation_media()
6. handle_operation_media() stocke la description + type + envoie clavier validation
7. User clique "✅ Valider"
8. Dispatcher route vers op:final_save → handle_save_operation()
9. Insertion dans chantier_operations_htl avec statut="en_attente"
10. Nettoyage state → retour au menu principal
```

### Workflow "Pointer présence" (Resources Humaines & Machines)
```
1. User clique "Pointer présence" → sous-menu : Humains / Machines
2. User clique "Ressources Humaines" → pointage:list:human
3. Handle_list_human() fetch chantier_ressources WHERE type='homme' AND org_id=...
4. Affichage paginé (5 par page) avec boutons ◀️ ▶️
5. Chaque ressource est un bouton avec callback pt:t:{id}:{page}:homme
6. User clique pour toggler présence (✅ / ❌)
7. Fetch chantier_pointages du jour, toggle dans chantier_pointage_ressources
8. User clique "🚀 Valider" → pointage:validate
9. Mise à jour du statut à "en_attente_validation"
10. Retour au menu principal
```

### Architecture backend multi-workers
- Uvicorn lancé avec `--workers 8` (multi-process)
- Chaque worker est un processus indépendant avec son event loop
- Pas de state partagé (stateless)
- Pointage configuré via scripts/run-local-back_test.sh et scripts/deploy_back_test.sh

### Gestion d'état (State Machine)
- `chantier_context.py` : set_state() et get_state() sur telegram_users.last_state
- États possibles : op_awaiting_description, op_awaiting_validation, idle
- Stockage dans colonnes last_state (TEXT) et last_state_data (JSONB)
- Migration SQL nécessaire : ALTER TABLE telegram_users ADD COLUMN last_state TEXT, ADD COLUMN last_state_data JSONB DEFAULT '{}'

### Migration DB nécessaire
```sql
ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS last_state TEXT;
ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS last_state_data JSONB DEFAULT '{}';
ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS last_chantier_id UUID REFERENCES chantiers(id) ON DELETE SET NULL;
```

### Architecture du Local Bot API (Docker)
```yaml
services:
  telegram-bot-api:
    image: aiogram/telegram-bot-api:latest
    entrypoint: /usr/local/bin/telegram-bot-api --local --api-id=${TELEGRAM_API_ID} --api-hash=${TELEGRAM_API_HASH} --http-port=8081
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
    ports:
      - "8081:8081"
```

### Variables d'environnement nécessaires
```bash
# Token du bot E2E (local)
export TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN="..."

# URL de l'API Telegram (locale ou distante)
export TELEGRAM_API_URL="http://localhost:8081"  # Pour le Local Bot API Server

# Identifiants Telegram (nécessaires pour Local Bot API)
export TELEGRAM_API_ID="..."
export TELEGRAM_API_HASH="..."
```

### Configuration des projets sur GCP
```bash
# Déploiement backend (avec 8 workers)
./scripts/deploy_back_test.sh

# Déploiement frontend
./scripts/deploy_front_test.sh
```

## Problèmes résolus dans cette session
1. **Webhook 403 (secret token invalide)** : Passage de webhook_secret à vide dans Supabase
2. **404 sur webhook** : Correction de l'URL dans la table telegram_bots avec le bon format `/api/v1/{org_id}/telegram/webhook/{token}`
3. **Bot non reconnu (slug vide)** : Ajout du mapping pour username personnalisé
4. **Colonne last_state manquante** : Migration SQL ajoutée
5. **PGRST116/PGRST200 (jointures)** : Simplification des requêtes update/select
6. **Fichier corrompu OperationsList.tsx** : Nettoyage du composant lazy loading
7. **OperationsList/PointagesList/TachesList/...** : Passage en lazy loading complet (fetch interne)
8. **Chargement lent du frontend** : Suppression du Promise.all dans page.tsx, chargement par onglet

