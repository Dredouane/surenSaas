# Tests Backend - Documentation

> **Dernière mise à jour :** Mars 2026 (tests validation + correction RLS policies phases 1 & 2)  
> **Status :** 🟢 Tests fonctionnels - À maintenir à jour

## 📋 Vue d'ensemble

Ce document décrit l'état des tests backend de l'API SurenSaaS. Il sert de référence pour comprendre les scénarios couverts sans relire le code source.

**Comment maintenir ce document :**
- ✅ Ajouter une ligne dans la section correspondante quand un nouveau test est créé
- 🔲 Marquer comme implémenté quand un test est ajouté
- 📝 Mettre à jour la date en haut du fichier

---

## 🧪 Tests API Routes (test_api_routes.py)

### ✅ Tests Clients (`/api/v1/clients`)

| Scénario | Méthode | Status | Description |
|----------|---------|--------|-------------|
| Création client | POST | ✅ | Crée un client avec tous les champs (nom, email, téléphone, adresse, SIRET, notes) |
| Liste clients | GET | ✅ | Récupère la liste paginée des clients avec recherche optionnelle |
| Détail client | GET | ✅ | Récupère les détails d'un client par son ID |
| Mise à jour client | PUT | ✅ | Modifie les informations d'un client existant |
| Suppression client | DELETE | ✅ | Supprime un client de la base de données |

**Cas d'erreur couverts :**
- 🔲 404 - Client non trouvé
- 🔲 403 - Accès non autorisé (mauvais org_id)
- 🔲 401 - Non authentifié

---

### ✅ Tests Factures (`/api/v1/invoices`)

| Scénario | Méthode | Status | Description |
|----------|---------|--------|-------------|
| Création facture | POST | ✅ | Crée une facture avec numéro, fournisseur, montants, dates, description |
| Liste factures | GET | ✅ | Récupère la liste avec filtres (statut, client, recherche) |
| Détail facture | GET | ✅ | Récupère les détails complets d'une facture |
| Mise à jour facture | PUT | ✅ | Modifie une facture (uniquement si en brouillon) |
| Suppression facture | DELETE | ✅ | Supprime une facture (uniquement si en brouillon) |
| Validation facture | POST | ✅ | Valide une facture en attente via `/invoices/{id}/validate?action=validate` |
| Rejet facture | POST | ✅ | Rejette une facture en attente via `/invoices/{id}/validate?action=reject` |

**Cas d'erreur couverts :**
- ✅ 404 - Facture non trouvée
- 🔲 403 - Tentative de modification d'une facture non brouillon
- ✅ 401 - Non authentifié
- ✅ 400 - Action invalide (validation d'une facture pas en attente)

---

### ✅ Tests Utilisateurs (`/api/v1/users`)

| Scénario | Méthode | Status | Description |
|----------|---------|--------|-------------|
| Profil utilisateur | GET | ✅ | Récupère le profil de l'utilisateur connecté (email, org, rôle) |

**Cas d'erreur couverts :**
- 🔲 401 - Token invalide ou expiré
- 🔲 404 - Utilisateur non trouvé

---

## 🧪 Tests Scénarios Complets (test_full_scenarios.py)

### ✅ Tests Authentification

| Scénario | Status | Description |
|----------|--------|-------------|
| Check-email autorisé | ✅ | Vérifie qu'un email pré-autorisé peut s'inscrire |
| Check-email non autorisé | ✅ | Vérifie qu'un email inconnu est rejeté |
| Validation email invalide | ✅ | Vérifie le format de l'email |
| Validation body vide | ✅ | Vérifie que les champs requis sont présents |
| Workflow signup complet | ✅ | Teste le flux complet : check-email → signup → vérification DB |

### ✅ Tests Facturation (DB directe)

| Scénario | Status | Description |
|----------|--------|-------------|
| Création factures test | ✅ | Crée 3 factures de test (brouillon, attente, validée) |
| Workflow statut complet | ✅ | Teste le changement de statut : brouillon → attente → validée → traitement |

---

## 🔧 Configuration des Tests

### Variables d'environnement requises

```bash
# Credentials pour les tests API (authentification requise)
export SUREN_TEST_LOGIN="email@exemple.com"
export SUREN_TEST_PASSWORD="mot-de-passe"

# OU via fichier .env.test.local (non versionné)
```

### Lancer les tests

```bash
# Tous les tests
./scripts/run-tests.sh

# Uniquement les tests API
python tests/test_api_routes.py

# Uniquement les scénarios complets
python tests/test_full_scenarios.py
```

---

### ✅ Tests Gestion des Erreurs

| Scénario | Route | Status | Description |
|----------|-------|--------|-------------|
| 401 - Non authentifié | `/users/me` | ✅ | Retourne 401 sans cookie de session |
| 404 - Client inexistant | `/clients/{fake_id}` | ✅ | Retourne 404 pour un ID inexistant |
| 404 - Facture inexistante | `/invoices/{fake_id}` | ✅ | Retourne 404 pour un ID inexistant |
| 400 - Validation invalide | `/invoices/{id}/validate` | ✅ | Retourne 400 si la facture n'est pas en attente |

---

## 📝 À Implémenter (TODO)

### Priorité Haute
- [x] **Validation/Rejet de factures** - Tester `POST /invoices/{id}/validate?action=validate/reject`
- [x] **Tests erreurs 401** - Vérifier que les routes protégées retournent 401 sans auth
- [ ] **Tests erreurs 403** - Vérifier qu'un user ne peut pas accéder aux données d'une autre org
- [x] **Tests erreurs 404** - Vérifier le comportement sur ID inexistant

### Priorité Moyenne
- [ ] **Tests pagination** - Vérifier les paramètres limit/offset sur les listes
- [ ] **Tests recherche** - Vérifier le filtre search sur clients et factures
- [ ] **Historique statuts** - Vérifier que l'historique est bien créé lors des changements

### Priorité Basse
- [ ] **Tests upload fichiers** - Tester l'upload de PDF/factures
- [ ] **Tests Telegram** - Tester les intégrations webhook (si applicable)
- [ ] **Tests de charge** - Vérifier les performances avec beaucoup de données

---

## 🐛 Bugs Connus / Corrections

### ✅ Problèmes résolus

| Problème | Cause | Solution | Migration |
|----------|-------|----------|-----------|
| **`.single()` et `.offset()`** | Supabase Python client ne supporte pas ces méthodes | Utiliser `.execute()` et gérer la logique en Python | ✅ Corrigé dans tous les fichiers |
| **Authentification email non confirmé** | Supabase Auth requiert confirmation par défaut | Fallback avec token JWT de test | ✅ Géré dans test_api_routes.py |
| **RLS Policies - données non visibles (v1)** | Politiques utilisaient table DEPRECATED `user_org_membership` (invoices, clients) | Migration 015 créant des politiques basées sur `users.org_id` | ✅ 015_fix_rls_policies.sql |
| **RLS Policies - données non visibles (v2)** | Politiques utilisaient table DEPRECATED `user_org_membership` (telegram_bots, companies, etc.) | Migration 016 corrigeant TOUTES les tables restantes | ✅ 016_fix_all_remaining_rls_policies.sql |

### 🔴 Correction RLS Critique - Phase 1 (Mars 2026)

**Problème :** Les factures et clients n'étaient pas visibles malgré leur existence en DB

**Cause :** Les politiques RLS créées dans `008_invoices.sql` et `014_add_clients_and_update_invoices.sql` utilisaient la table `user_org_membership` qui a été désactivée par `999_cleanup_user_org_membership.sql`

**Impact :** 
- Dashboard factures : écran vide
- Dashboard clients : écran vide
- Administration users : fonctionnait (autre politique)

**Solution :** Exécuter `015_fix_rls_policies.sql`
```bash
psql "$DATABASE_URL" -f db/schema/015_fix_rls_policies.sql
```

**Politiques corrigées :**
- `members_read_invoices` : utilise `users.org_id` directement
- `members_read_clients` : utilise `users.org_id` directement
- Toutes les policies INSERT/UPDATE/DELETE mises à jour

### 🔴 Correction RLS Critique - Phase 2 (Mars 2026)

**Problème :** Les bots Telegram, companies, et autres tables ne retournaient pas de données

**Cause :** Les migrations 006-011 avaient créé des politiques utilisant `user_org_membership` mais n'ont pas été corrigées dans la phase 1

**Impact :** 
- Invitation bot Telegram : retourne liste vide
- Gestion companies : potentiellement cassée
- Audit Telegram : inaccessible
- Capabilities : gestion impossible

**Solution :** Exécuter `016_fix_all_remaining_rls_policies.sql`
```bash
psql "$DATABASE_URL" -f db/schema/016_fix_all_remaining_rls_policies.sql
```

**Tables corrigées :**
- `telegram_bots` : 2 policies (admin_manage, members_read)
- `telegram_users` : 1 policy (admin_read_org_telegram)
- `telegram_audit` : 1 policy (admin_read_audit)
- `companies` : 2 policies (members_read, admin_manage)
- `organization_capabilities` : 1 policy (admin_manage)
- `user_capabilities` : 1 policy (admin_manage)
- `invoice_status_history` : 1 policy (complément au 015)

**Total :** 7 tables, 10 policies corrigées

---

## 📊 Couverture Actuelle

**Routes API testées :** 12/13 (92%)
**Scénarios critiques :** ✅ 100% couverts
**Gestion d'erreurs :** 🔲 20% couverts (à améliorer)

**Routes non testées :**
- `/api/v1/invoices/{id}/validate` (validation/rejet)
- Routes d'erreur spécifiques (401, 403, 404)

---

## 🎯 Bonnes Pratiques

1. **Ajouter un test pour chaque nouvelle route API**
2. **Documenter ici immédiatement après création**
3. **Maintenir à jour la section "À Implémenter"**
4. **Exécuter les tests avant chaque commit important**

---

## 👥 Contributeurs

- Documentation créée : Mars 2026
- Dernier test ajouté : test_api_routes.py (Clients, Invoices, Users)

---

**💡 Besoin d'aide ?** Voir le fichier `tests/README.md` pour la structure des tests.
