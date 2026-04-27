# TODO Refactoring — SurenSaaS

Generated: 2026-04-27
Source: Codebase analysis via `grill-me.md`, `deep-modules.md`, `ubiquitous-language.md`, `tdd-cycle.md`

---

## 🔴 IMMÉDIAT (Sécurité & Blocant)

### SEC-001: Stub `require_capability()` sur routes email
**Fichier**: `surenSaasBack/app/api/emails.py`, `email_threads.py`
**Desc**: La fonction `require_capability()` retourne un user hardcodé `{"id": "test-user", "role": "admin", "org_id": "test"}` au lieu de vérifier les droits réels. Tous les endpoints email sont accessibles sans autorisation.
**Action**: Implémenter la vraie vérification via `get_current_user` + vérification des capabilities de l'utilisateur.

### SEC-002: Import cassé `app.core.supabase`
**Fichier**: `surenSaasBack/app/services/capabilities.py:12`
**Desc**: Importe `from app.core.supabase import ...` mais `app/core/supabase.py` n'existe pas. Crash à l'exécution si le module est importé.
**Action**: Supprimer l'import mort ou créer le module manquant.

### SEC-003: Bot tokens en query string
**Fichier**: `surenSaasBack/app/api/telegram_core.py`
**Desc**: Les tokens Telegram Bot sont passés dans l'URL en query string (`https://api.telegram.org/bot{token}/...`). Si le logging est en mode debug, les tokens fuient dans les logs.
**Action**: Filtrer/sanitizer les tokens dans les logs. Vérifier que le logging ne capture pas les query strings.

### SEC-004: .env.test et .env.prod versionnés
**Fichiers**: `.env.test`, `.env.prod`, `surenSaasFront/.env`, `surenSaasFront/.env.test`
**Desc**: Ces fichiers sont dans le repo Git et peuvent contenir des secrets (API keys, DB credentials).
**Action**: Vérifier le contenu, ajouter `.env.*` à `.gitignore` si nécessaire, ou utiliser des examples files uniquement.

---

## 🔴 HAUTE (Dette Technique & Testing)

### TEC-001: Zéro test sur le module AO
**Fichier**: `surenSaasBack/app/api/ao.py` (1178 lignes, 20+ endpoints)
**Desc**: Le plus gros module de l'API n'a aucun test unitaire ni d'intégration.
**Action**: Écrire des tests pour chaque endpoint AO (via TDD cycle Red-Green-Refactor).

### TEC-002: 45 scripts Python à la racine
**Fichiers**: `*.py` à la racine du projet (tests ponctuels, debug, migrations)
**Desc**: Absence d'organisation. Mélange de scripts jetables et de tests valides. Certains contiennent des credentials.
**Action**: Trier dans `scripts/`, `tests/`, ou supprimer. Ne garder à la racine que les scripts documentés et réutilisables.

### TEC-003: Module AO shallow — 1178 lignes dans un seul fichier
**Fichier**: `surenSaasBack/app/api/ao.py`
**Desc**: Mélange de routing, parsing, orchestration, logique métier. Interface complexe.
**Action**: Appliquer Deep Module — extraire la logique métier dans `app/services/ao/`, laisser le routeur léger.

### TEC-004: Migration 019_disable_all_rls.sql
**Fichier**: `db/schema/019_disable_all_rls.sql`
**Desc**: Désactive TOUTES les RLS de la base. Suggère un problème d'auth non résolu.
**Action**: Analyser pourquoi les RLS ont été désactivées, corriger la cause racine, réactiver sélectivement.

### TEC-005: Rate limiter in-memory sans cleanup
**Fichier**: `surenSaasBack/app/core/rate_limit.py`
**Desc**: Utilise un dictionnaire `_memory_store` qui grossit indéfiniment. Fuite mémoire.
**Action**: Ajouter un cleanup périodique ou migrer vers Redis/DB-based rate limiting.

### TEC-006: Test désactivé (`.disabled`)
**Fichier**: `surenSaasBack/tests/test_chantiers_crud.py.disabled`
**Desc**: Un test désactivé sans explication ni ticket.
**Action**: Soit le réparer et le réactiver, soit le supprimer.

---

## ⚠️ MOYENNE (Design & Architecture)

### DES-001: `user_org_membership` dépréciée mais référencée
**Fichiers**: `db/schema/008_invoices.sql`, `db/policies/auth_rls.sql`
**Desc**: La table `user_org_membership` a été migrée vers `users.role`, mais les RLS policies la référencent encore.
**Action**: Mettre à jour toutes les RLS policies pour utiliser `users.role` au lieu de la table dépréciée.

### DES-002: Frontend — mock data en production
**Fichiers**: `surenSaasFront/app/dashboard/page.tsx`, `surenSaasFront/lib/chantier-data.ts`, `chantier-data-extended.ts`
**Desc**: Le dashboard affiche des données mockées statiques. Les pages chantier utilisent encore du mock data.
**Action**: Remplacer par des appels API réels ou supprimer le code mort.

### DES-003: Pas de CI/CD pipeline
**Fichier**: Absence de `.github/workflows/` ou équivalent.
**Desc**: Aucune automatisation de tests, linting, ou déploiement.
**Action**: Mettre en place GitHub Actions (tests → lint → build → déployer).

### DES-004: Pas de queue de tâches asynchrone
**Fichiers**: Tous les endpoints utilisant l'IA (OCR, extraction, analyse)
**Desc**: L'OCR et l'extraction AI sont synchrones dans le request-response cycle. Risque de timeout Cloud Run, mauvaise UX.
**Action**: Introduire une file d'attente (Celery, Redis Queue, ou Cloud Tasks) pour les opérations lourdes.

### DES-005: Multiples façons d'importer Supabase client
**Fichiers**: `app/services/database.py`, `app/api/auth.py`, `app/core/supabase` (inexistant)
**Desc**: Au moins 3 patterns d'import différents pour le client Supabase. Pas de singleton clair.
**Action**: Unifier via un seul module (`app/core/supabase.py` ou `app/services/database.py`) et l'utiliser partout.

### DES-006: Code mort dans main.py
**Fichier**: `surenSaasBack/app/main.py` (lignes 159-210)
**Desc**: Blocs try/except dupliqués avec `return` après `finally` et code mort.
**Action**: Nettoyer les gestionnaires d'erreur, supprimer le code inaccessible.

---

## 🟡 BASSE (Améliorations)

### IMP-001: Pas de monitoring
**Desc**: Aucun fichier de config pour Sentry, Datadog, Cloud Monitoring, etc.
**Action**: Ajouter Sentry pour le tracking d'erreurs en production.

### IMP-002: Pas de versioning des prompts AI
**Fichier**: `surenSaasBack/app/agents/prompts/`
**Desc**: Les prompts évoluent sans historique ni versioning. Impossible de savoir quel prompt a été utilisé à quel moment.
**Action**: Ajouter un champ `version` dans chaque fichier de prompt, ou utiliser un système de templates versionnés.

### IMP-003: Test et production sur la même DB
**Desc**: Isolation par `org_id` uniquement. Risque de fuite de données si une requête oublie le filtre.
**Action**: Déployer une base de données de test séparée.

### IMP-004: Pas de refresh token / session blacklist
**Desc**: Les sessions JWT ne peuvent pas être révoquées (HS256, pas de blacklist). Pas de refresh token.
**Action**: Implémenter une table de sessions révocables avec refresh token rotation.

### IMP-005: Agents AI — code spaghetti
**Fichiers**: `app/agents/construction_invoice_agent.py`, `generic_extractor.py`
**Desc**: Peu de structure, pas de tests, prompts en dur et dans des fichiers (mélange).
**Action**: Refactorer avec une architecture Agent/Pipeline commune, ajouter des tests unitaires.

---

## Légende

| Priorité | Délai suggéré | Signification |
|---|---|---|
| 🔴 IMMÉDIAT | 1-3 jours | Blocant ou faille de sécurité |
| 🔴 HAUTE | 1-2 semaines | Dette critique, manque de tests |
| ⚠️ MOYENNE | 1 mois | Design/architecture à corriger |
| 🟡 BASSE | 2-3 mois | Amélioration continue |

Format de chaque entrée:

```
### ID: Mini issue title
**Fichier**: chemin(s) concerné(s)
**Desc**: 1-2 phrases sur le problème
**Action**: 1 phrase sur la résolution
```
