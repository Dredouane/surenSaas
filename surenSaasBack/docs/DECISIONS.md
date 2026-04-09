# Décisions Backend

## ADR-001 : Contract-first OpenAPI
**Choix** : OpenAPI YAML génère le code FastAPI
**Pourquoi** : API documentée dès la conception, synchro front/back
**Outil** : openapi-generator-cli

## ADR-002 : Pas d'ORM
**Choix** : Supabase client direct (pas SQLAlchemy ORM)
**Pourquoi** : RLS policies Supabase déjà en place, moins de couche
**Alternative** : Prisma (rejeté - complexité inutile)

## ADR-003 : Scale-to-zero backend
**Choix** : Cloud Run avec min instances = 0
**Pourquoi** : Économies sur environnements non-prod
**Cold start** : Acceptable (<2s) pour backend API

## ADR-004 : Workers séparés
**Choix** : Agents IA dans process séparé (Celery)
**Pourquoi** : Cloud Run stateless, pas de long-running dans API
**Queue** : Redis ou Cloud Tasks

## ADR-005 : Validation JWT manuelle
**Choix** : Validation JWT dans FastAPI (pas dépendance Supabase)
**Pourquoi** : Contrôle total claims, vérification authorized_users

## ADR-006 : Auth Magic Link + Password
**Choix** : Système email+password avec table pre_authorized_emails
**Pourquoi** : 
- Plus simple à maintenir que Microsoft SSO
- Pas de dépendance externe (Azure)
- Contrôle total sur invitations
- Rate limiting facile à implémenter
**Alternatives** : Microsoft Entra ID (rejeté - complexité, coût, dépendance)

## ADR-007 : Rate limiting mémoire
**Choix** : Stockage en mémoire Python (pas Redis)
**Pourquoi** : Pas de dépendance externe, suffisant pour scale Cloud Run, plus simple
**Implémentation** : Dictionnaire {hash(IP+UA): [timestamps]} avec nettoyage auto

## ADR-008 : Pas de validation password complexe
**Choix** : Min 8 caractères seulement
**Pourquoi** : NIST recommande longueur > complexité
**UX** : Moins de friction pour les utilisateurs

## ADR-009 : Système de Capabilities
**Choix** : Permissions granulaires `resource:action` au lieu de rôles binaires
**Pourquoi** : 
- Flexibilité pour multi-PME (construction, nettoyage, etc.)
- Capabilities spécifiques par entreprise filiale
- Admin bypass automatique
**Format** : `construction:facturation:read`
**Implémentation** : Tables `user_capabilities` + `organization_capabilities`

## ADR-010 : Bot Telegram par entreprise
**Choix** : Un bot peut être lié à une entreprise filiale ou à l'org globale
**Pourquoi** : 
- Séparation des préoccupations
- Configuration personnalisée par métier
- Notifications ciblées
**Architecture** : Services séparés par primitive (bouton)

## ADR-011 : Audit complet Telegram
**Choix** : Table `telegram_audit` logue toutes les interactions
**Pourquoi** : 
- Debugging des workflows
- Monitoring des erreurs
- Traçabilité métier
**Data** : Payload, result, timing, errors

## ADR-012 : OCR Agentic - Coquille
**Choix** : Structure workflow prête mais OCR non implémenté
**Pourquoi** : 
- Architecture extensible
- Définition des contrats d'abord
- Implémentation IA dans second temps
**Structure** : `app/agents/invoice_ocr/workflow.py` + `contracts.py`

## ADR-013 : Factures multi-status
**Choix** : Workflow à 6 status avec historique complet
**Status** : brouillon → en_attente_validation → [validee/rejetee] → en_traitement_comptable → archivee
**Pourquoi** : Traçabilité complète du cycle de vie
**Table** : `invoice_status_history` logue tous les changements

## ADR-014 : Security Webhook Telegram
**Choix** : Double sécurité sur webhooks
**Mécanismes** :
1. Token hash dans l'URL (pas le token en clair)
2. Header `X-Telegram-Bot-Api-Secret-Token` vérifié
**Pourquoi** : Sécurité même si URL leakée

## ADR-015 : Admin Space - Gestion utilisateurs et permissions
**Choix** : Interface admin dédiée pour gérer les accès
**Fonctionnalités** :
1. **Pré-autorisation emails** : Admin ajoute/supprime emails autorisés à rejoindre l'org
2. **Capabilities granulaires** : Assigner permissions `resource:action` par utilisateur
3. **Scope par ressource** : Capabilities globales ou limitées à une entreprise filiale
**Routes API** : `/admin/*` (OpenAPI contract-first)
**Architecture** : 
- Service layer `app/services/admin_service.py` appelle Supabase REST API
- Pages frontend sous `/dashboard/settings/admin/`
- Guard component `AdminGuard.tsx` pour protection routes
**Pourquoi** :
- Contrôle total sur qui peut rejoindre l'organisation
- Permissions fines adaptées au multi-PME
- Séparation claire admin vs utilisateur standard

## ADR-016 : Module Emails - Architecture Data Layer
**Choix** : Séparation stricte entre ingestion emails (data) et secrétariat IA (logic)
**Architecture** :
- **Module Emails** : Ingestion Gmail, stockage, vectorisation (`docs/EMAILS.md`)
- **Module Secrétariat** : Analyse métier, workflows, décisions (`docs/SECRETARIAT.md`)
**Pourquoi** :
- **Testabilité** : Tester l'ingestion sans logique métier complexe
- **Évolution** : Remplacer Gmail par Outlook sans toucher le secrétariat
- **Performance** : Vectorisation batch, secrétariat temps réel
- **Équipe** : Data engineer = Emails, Métier/IA = Secrétariat

## ADR-017 : Gmail OAuth2 pour ingestion emails
**Choix** : OAuth2 avec refresh tokens pour accès API Gmail
**Implémentation** :
- Refresh tokens chiffrés stockés en DB (`email_accounts.oauth_refresh_token`)
- Polling incrémental via UID Gmail (pas de webhook pour l'instant)
- Scopes limités : `gmail.readonly` uniquement
**Pourquoi** :
- Sécurité : Pas de stockage mot de passe
- Fiabilité : Refresh tokens longue durée vs access tokens courts
- Simplicité : Pas de webhook complexe à gérer (polling HTTP trigger)

## ADR-018 : Stockage embeddings séparé (pgvector)
**Choix** : Table `email_embeddings` séparée de `emails`
**Structure** :
- `emails` = métadonnées + contenu texte
- `email_embeddings` = vecteurs + chunks de texte
**Pourquoi** :
- Un email → N embeddings (corps chunké + N pièces jointes)
- Recherche vectorielle plus performante (moins de données à scanner)
- Flexibilité : plusieurs modèles/version d'embeddings cohabitent
**Tech** : Supabase pgvector extension, dimension 1536 (OpenAI)

## ADR-019 : Polling synchrone HTTP pour emails
**Choix** : Endpoint HTTP déclencheur synchrone, pas de workers async
**Implémentation** :
- `POST /api/v1/{org}/emails/sync` déclenche le polling complet
- Traitement synchrone dans la requête HTTP
- Pas de Celery/Redis/Cloud Tasks pour l'instant
**Pourquoi** :
- **Simplicité** : Pas d'infrastructure supplémentaire
- **Cloud Run compatible** : Pas de long-running processes
- **Contrôle** : Déclenchement manuel ou via cron externe (Cloud Scheduler)
- **Futur** : Migrera vers async workers si volume important
