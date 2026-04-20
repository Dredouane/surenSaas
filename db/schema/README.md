# Migrations SQL - Documentation

## Ordre d'exécution des migrations

Les migrations doivent être exécutées dans l'ordre numérique. Voici la séquence complète :

### Phase 1 : Structure de base (001-007)
1. `001_organizations.sql` - Table des organisations
2. `002_users.sql` - Table des utilisateurs avec org_id et role
3. `003_pre_authorized_emails.sql` - Emails pré-autorisés
4. `004_user_org_membership.sql` - Table de liaison (DEPRECATED après 999)
5. `005_auth_triggers.sql` - Triggers pour auth.users
6. `006_companies.sql` - Table des entreprises
7. `007_pre_authorized_emails_unique.sql` - Contrainte unique sur emails

### Phase 2 : Métier (008-014)
8. `008_invoices.sql` - Table des factures + RLS initiales
9. `009_invoices_amount_precision.sql` - Précision des montants
10. `010_invoices_add_metadata.sql` - Colonnes metadata
11. `011_telegram_bots.sql` - Configuration Telegram
12. `012_invoice_status_history.sql` - Historique des statuts
13. `013_invoices_add_company_id.sql` - Lien vers companies
14. `014_add_clients_and_update_invoices.sql` - Table clients + colonne client_id

### Phase 3 : Corrections critiques (015-016)
15. **`015_fix_rls_policies.sql`** - ⚠️ **IMPORTANT** - Correction des politiques RLS (v1)
    - Corrige les policies pour `invoices`, `clients`, `invoice_status_history`
    - Met à jour pour utiliser `users.org_id` directement
    - **À exécuter si les factures/clients n'apparaissent pas dans le dashboard**

16. **`016_fix_all_remaining_rls_policies.sql`** - ⚠️ **IMPORTANT** - Correction complète des RLS
    - Corrige TOUTES les tables restantes : `telegram_bots`, `telegram_users`, `telegram_audit`
    - Corrige également : `companies`, `organization_capabilities`, `user_capabilities`
    - Met à jour pour utiliser `users.org_id` directement
    - **À exécuter après 015 si d'autres tables ne fonctionnent pas (bots Telegram, companies, etc.)**

### Phase 4 : Module Emails (020)
17. **`020_email_tables.sql`** - Module d'ingestion et vectorisation des emails
    - **Architecture** : Multi-tenant par aliasing Gmail (`REDACTED_EMAIL`)
    - **Séparateur** : Configurable via `EMAIL_ALIAS_SEPARATOR` (défaut: `#`)
    - **Extraction forward** : Détection et extraction du mail original (transparence Gmail)
    - **Vectorisation** : Vertex AI text-embedding-004 + Matryoshka slicing (768 dims)
    - Crée extension `vector` (pgvector) pour embeddings
    - Table `email_accounts` : Configuration Gmail OAuth (compte unique partagé TEST/PROD)
    - Table `emails` : Stockage avec routing (`company_id`, `delivered_to_alias`, `routing_status`)
    - Table `email_attachments` : Pièces jointes avec OCR (hérite `company_id`)
    - Table `email_embeddings` : Vecteurs 768 dims pour RAG (hérite `company_id`)
    - Types ENUM : `email_status`, `embedding_source`
    - Fonctions utilitaires : `search_similar_emails()`, `get_email_thread()`
    - **Prérequis** : Activer extension pgvector dans Supabase Dashboard
    - **Routing strict** : Emails ignorés si alias invalide (pas de fallback)

### Phase 5 : Nettoyage (999)
999. `999_cleanup_user_org_membership.sql` - Nettoyage de la table dépréciée
    - Désactive RLS sur user_org_membership
    - Migre les données vers users.role
    - **Doit être exécuté APRÈS 015**

## ⚠️ Cas particulier : Problème de visibilité des données

**Symptômes :**
- Dashboard factures vide
- Dashboard clients vide
- Mais les données existent en base

**Cause :** Les politiques RLS (Row Level Security) utilisent une table obsolète

**Solution rapide :**
```bash
# Exécuter uniquement la migration corrective
psql "$DATABASE_URL" -f db/schema/015_fix_rls_policies.sql
```

## Commandes utiles

### Exécuter toutes les migrations
```bash
cd /home/redouane/dev/AI-ERA/surenSaas
./scripts/migrate.sh
```

### Exécuter une migration spécifique
```bash
psql "$DATABASE_URL" -f db/schema/015_fix_rls_policies.sql
```

### Vérifier les politiques RLS actuelles
```sql
-- Voir toutes les policies sur une table
SELECT * FROM pg_policies WHERE tablename = 'invoices';

-- Voir si RLS est activé
SELECT relname, relrowsecurity FROM pg_class WHERE relname IN ('invoices', 'clients');
```

## Structure des migrations futures

Pour ajouter une nouvelle migration :
1. Nommer selon le schéma : `XXX_description_breve.sql`
2. Mettre à jour ce README
3. Documenter dans TESTS.md si impact sur les tests
