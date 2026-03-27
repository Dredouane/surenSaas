# TODO-Sécurité-Capabilities.md

## 📊 Analyse de l'état actuel du système de sécurité et capabilities

**Date** : 2026-03-27  
**Contexte** : Problème d'accès aux factures (401 Unauthorized) et manque de gestion des capabilities

---

## 🔴 Problèmes identifiés

### 1. Problème d'accès 401 - Cookie de session manquant

**Erreur observée** :
```
WARNING | auth:92 | Cookie de session manquant
Requête GET /api/v1/invoices/{id} - 401
```

**Fichier concerné** : `surenSaasBack/app/api/invoices.py:69`

**Code actuel** :
```python
def check_user_org_access(request: Request, org_id: str):
    user = get_current_user_from_cookie(request)
    if user["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    return user
```

**Analyse** :
- La fonction vérifie uniquement que l'utilisateur appartient à l'org
- Elle ne vérifie PAS les capabilities (ex: `facture:read`)
- Le cookie peut être absent ou expiré
- Le problème vient probablement de la gestion des cookies cross-domain (frontend vs backend)

---

### 2. Système de Capabilities - État détaillé

#### ✅ Ce qui est implémenté

**Tables Base de données** (Migration 006) :
- `organization_capabilities` : Liste des capabilities disponibles par organisation
- `user_capabilities` : Assignation capabilities → utilisateurs
- Vue `user_active_capabilities` : Vue agrégée des capabilities actives

**Backend - Services** (`app/services/admin_service.py`) :
- `get_organization_capabilities()` - Liste capabilities org
- `get_user_capabilities()` - Liste capabilities user
- `assign_capability_to_user()` - Assigner capability
- `revoke_user_capability()` - Révoquer capability

**Backend - API** (`app/api/admin.py`) :
```python
GET  /organization-capabilities      # Liste capabilities org
POST /organization-capabilities      # Créer capability
GET  /users/{id}/capabilities        # Liste capabilities user
POST /users/{id}/capabilities        # Assigner capability
PUT  /users/{id}/capabilities        # Mise à jour batch
DELETE /users/{id}/capabilities/{code}  # Révoquer
```

#### ❌ Ce qui manque

**1. Middleware/Decorator de vérification capabilities**

Actuellement aucun mécanisme pour protéger les routes API avec des capabilities.

**2. Page de gestion des capabilities (Frontend)**

Lien existe dans `page.tsx:420` mais la page n'est pas implémentée.

**3. Menu frontend conditionné par capabilities**

Actuellement le menu est statique, pas de vérification capability.

---

### 3. RLS Supabase - Problèmes

Les RLS policies utilisent `auth.uid()` qui ne fonctionne pas avec le service key (backend).

**Solution temporaire** : Désactiver RLS pour le prototypage
**Solution production** : Remplacer RLS par vérification capabilities côté backend

---

### 4. Line_items manquants

**Problème** : Les items de facture extraits par Gemini ne sont pas stockés

**Cause** : `ExtractedInvoiceData` ne récupère pas les line_items (service.py ligne 270-296)

**Table invoices** : Champ `items` = `'[]'` (tableau vide)

**Solution** :
1. Modifier `ExtractedInvoiceData` pour inclure `line_items`
2. Modifier `_perform_ocr` pour extraire les line_items
3. Modifier `_create_draft_invoice` pour stocker les items

---

## 🛠️ Actions immédiates recommandées

### 1. Désactiver RLS (Prototypage)

**Fichier** : `db/scripts/disable_rls_prototyping.sql`

```sql
-- Script pour désactiver RLS temporairement (PROTOTYPAGE UNIQUEMENT)
ALTER TABLE invoices DISABLE ROW LEVEL SECURITY;
ALTER TABLE clients DISABLE ROW LEVEL SECURITY;
ALTER TABLE companies DISABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_users DISABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_bots DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_capabilities DISABLE ROW LEVEL SECURITY;
ALTER TABLE organization_capabilities DISABLE ROW LEVEL SECURITY;
```

### 2. Corriger le bug invoices.py ligne 176

Remplacer `return result.data[0] if result.data and len(result.data) > 0 else update_data` 
par `return result.data[0]`

### 3. Ajouter line_items dans l'extraction

Modifier `_perform_ocr` pour récupérer et stocker les line_items extraits par Gemini.

---

## 📋 Plan complet d'implémentation

### Phase 1 : Corrections immédiates (1-2 jours)

- [ ] Corriger le bug ligne 176 dans `invoices.py`
- [ ] Ajouter line_items dans l'extraction OCR
- [ ] Désactiver RLS temporairement
- [ ] Investiguer le problème de cookie 401

### Phase 2 : Implémentation Capabilities (3-5 jours)

- [ ] Créer le decorator `require_capability`
- [ ] Appliquer aux routes API existantes
- [ ] Créer la page frontend de gestion des capabilities
- [ ] Implémenter le hook `useCapabilities`
- [ ] Conditionner le menu par capabilities

### Phase 3 : Sécurisation (2-3 jours)

- [ ] Audit de toutes les routes
- [ ] Tests des permissions
- [ ] Documentation pour les admins

---

**Prochaine action recommandée** : Exécuter le script `disable_rls_prototyping.sql` pour débloquer l'accès immédiat.

---

## ✅ Corrections appliquées le 2026-03-27

### 1. Gestion du cookie expiré - Redirection auto vers login

**Problème** : Quand le cookie de session expire, l'utilisateur reste sur la page et reçoit des erreurs 401

**Solution** :
- Création de `AuthenticationError` dans `auth.py` avec flag `redirect_to_login`
- Ajout de headers spécifiques (`X-Auth-Redirect`, `X-Auth-Error`) dans les réponses 401
- Modification du proxy API (`route.ts`) pour détecter ces headers et rediriger
- Création du hook `useApiErrorHandler.ts` pour gérer les erreurs côté client
- Création du middleware Next.js (`middleware.ts`) pour vérifier le cookie avant d'accéder aux routes protégées

**Fichiers modifiés** :
- `surenSaasBack/app/api/auth.py` - Exception personnalisée et gestion des erreurs
- `surenSaasBack/app/api/invoices.py` - Gestion des AuthenticationError
- `surenSaasFront/app/api/v1/[[...path]]/route.ts` - Détection des erreurs auth
- `surenSaasFront/middleware.ts` - Vérification du cookie (NOUVEAU)
- `surenSaasFront/hooks/useApiErrorHandler.ts` - Hook de gestion des erreurs (NOUVEAU)

### 2. Création de la table invoice_items

**Migration SQL** : `db/schema/018_create_invoice_items_table.sql`

**Structure** :
```sql
CREATE TABLE invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity DECIMAL(10, 2),
    unit_price DECIMAL(10, 2),
    total_ht DECIMAL(10, 2),
    vat_rate DECIMAL(5, 2),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Fichiers modifiés** :
- `surenSaasBack/app/services/telegram/upload_invoice/service.py` :
  - Ajout du champ `line_items` dans `ExtractedInvoiceData`
  - Extraction des line_items depuis la réponse Gemini
  - Insertion des items dans `invoice_items` lors de la création de facture
- `surenSaasBack/app/api/invoices.py` :
  - Ajout du modèle `InvoiceItem` dans les schémas Pydantic
  - Modification de `InvoiceCreate` et `InvoiceUpdate` pour accepter les items
  - Modification de `InvoiceResponse` pour retourner les items
  - Modification de `create_invoice` pour créer les items
  - Modification de `get_invoice` pour récupérer les items
  - Modification de `update_invoice` pour mettre à jour les items
  - Correction du bug ligne 174 et 197 (`else update_data` → code correct)

### 3. Modifications du service OCR

**Changements dans `_perform_ocr`** :
```python
# Extraction des line_items depuis Gemini
line_items = extracted.get("line_items", [])
if line_items:
    logger.info(f"📋 {len(line_items)} ligne(s) de détail extraite(s)")

extracted_data = ExtractedInvoiceData(
    # ... champs existants ...
    line_items=line_items,  # NOUVEAU
    raw_data={...}
)
```

**Changements dans `_create_draft_invoice`** :
```python
# Insérer les lignes de détail (items) si présents
if extracted_data.line_items and len(extracted_data.line_items) > 0:
    items_data = []
    for idx, item in enumerate(extracted_data.line_items):
        item_data = {
            'invoice_id': invoice_id,
            'org_id': org_id,
            'description': item.get('description', ''),
            'quantity': item.get('quantity'),
            'unit_price': item.get('unit_price'),
            'total_ht': item.get('total_ht'),
            'vat_rate': item.get('vat_rate'),
            'sort_order': idx
        }
        items_data.append(item_data)
    
    self.supabase.table('invoice_items').insert(items_data).execute()
```

---

## 🧪 Tests recommandés

### Test 1 : Cookie expiré
1. Se connecter
2. Attendre expiration du cookie (ou supprimer manuellement)
3. Cliquer sur une facture
4. Vérifier la redirection vers `/login?error=session_expired`

### Test 2 : Extraction OCR avec items
1. Envoyer une facture PDF via Telegram
2. Vérifier que les items sont extraits (log backend)
3. Vérifier que les items sont stockés en DB :
   ```sql
   SELECT * FROM invoice_items WHERE invoice_id = '...';
   ```
4. Vérifier que les items apparaissent dans l'API :
   ```bash
   curl /api/v1/invoices/{id}?org_id=...
   ```

### Test 3 : CRUD des items
1. Créer une facture avec items via API
2. Vérifier les items créés
3. Modifier la facture avec nouveaux items
4. Vérifier que les anciens items sont remplacés

---

## 📋 Scripts SQL à exécuter

### 1. Créer la table invoice_items
```bash
# Exécuter dans Supabase Dashboard → SQL Editor
cat db/schema/018_create_invoice_items_table.sql
```

### 2. Désactiver RLS temporairement (si bloquant)
```bash
# Exécuter en cas de problèmes d'accès
cat db/scripts/disable_rls_prototyping.sql
```

---

## 🎯 Prochaines étapes suggérées

1. **Tests** : Vérifier que tout fonctionne correctement
2. **Déploiement** : Déployer backend et frontend
3. **Documentation** : Mettre à jour la documentation utilisateur
4. **Future** : Implémenter la vérification des capabilities dans les routes API

