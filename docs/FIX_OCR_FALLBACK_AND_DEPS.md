# ✅ Corrections appliquées - Gestion gracieuse OCR + Mise à jour dépendances

## 📋 Résumé des problèmes résolus

### 1. Conflit de dépendances httpx
**Problème** : 
- `supabase==1.2.0` nécessite `httpx<0.25.0`
- `google-genai>=1.0.0` nécessite `httpx>=0.25.0`
- Résultat : Gemini désactivé, OCR impossible

**Solution** : Mise à jour vers `supabase>=2.0.0` compatible avec `httpx>=0.25.0`

### 2. Violation contraintes NOT NULL
**Problème** :
- Quand OCR échoue, `amount_ttc` et autres champs sont NULL
- La DB rejette l'insertion avec erreur 23502

**Solution** : Valeurs par défaut (0.0, "") quand OCR échoue

---

## 🔧 Modifications apportées

### 1. `requirements.txt` - Mise à jour des dépendances

```diff
- supabase==1.2.0
- httpx>=0.24.0,<0.25.0
+ supabase>=2.0.0,<3.0.0
+ httpx>=0.25.0,<0.28.0
+ google-genai>=1.0.0  # Réactivé!
```

### 2. `upload_invoice/service.py` - Gestion gracieuse OCR

#### Nouvelle méthode `_create_fallback_extraction()`
Retourne des valeurs par défaut quand Gemini est indisponible :
```python
ExtractedInvoiceData(
    supplier_name="",
    supplier_address="",
    amount_ht=0.0,
    amount_ttc=0.0,  # Plus de NULL!
    vat_amount=0.0,
    vat_rate=0.0,
    confidence_score=0.0,
    raw_data={"fallback": True, "note": "À compléter manuellement"}
)
```

#### Modification `_perform_ocr()`
- Détection de l'indisponibilité de Gemini
- Fallback automatique si exception
- Valeurs par défaut pour tous les champs

#### Modification `_create_draft_invoice()`
- Garantie de valeurs non-NULL :
  - `amount_ttc: 0.0` (au lieu de None)
  - `amount_ht: 0.0`
  - `vat_amount: 0.0`
  - `supplier_name: "À compléter"`
- Flag `needs_manual_review` dans metadata

### 3. `bot_construction.py` - Messages adaptatifs

```python
if is_fallback:
    message = "⚠️ Facture reçue mais OCR indisponible..."
else:
    message = "✅ Facture analysée avec succès !"
```

---

## 📊 Comportement par scénario

### Scénario 1 : OCR fonctionne normalement
```
1. User envoie PDF
2. Gemini extrait : Fournisseur, Montants, etc.
3. Facture créée avec données complètes
4. Message : "✅ Facture analysée avec succès !"
5. User valide → Notification gérants
```

### Scénario 2 : Gemini indisponible (conflit dépendances)
```
1. User envoie PDF
2. Détection : Gemini non disponible
3. Fallback : valeurs par défaut (0, "")
4. Facture créée avec "needs_manual_review": true
5. Message : "⚠️ OCR indisponible - À compléter manuellement"
6. User doit compléter via l'application web
```

### Scénario 3 : OCR échoue (document illisible)
```
1. User envoie PDF flou
2. Gemini retourne erreur
3. Fallback : valeurs par défaut
4. Facture créée en statut "brouillon"
5. Message indique échec + nécessité de compléter
```

---

## 🧪 Tests effectués

```bash
✅ Auth/Supabase import OK
✅ InvoiceUploadService import OK
✅ Bot construction import OK
✅ Main app import OK
```

---

## 🚀 Déploiement

### 1. Mettre à jour les dépendances
```bash
cd surenSaasBack
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### 2. Vérifier les dépendances
```bash
./scripts/check_dependencies.sh
```

### 3. Déployer
```bash
./scripts/deploy_back_test.sh
```

---

## 📈 Résultat attendu

### Logs Cloud Run

**Cas nominal (OCR OK)** :
```
📝 Données extraites par OCR:
   - Fournisseur: Matériaux Pro SARL
   - Montant TTC: 1200.0€
   - Score confiance: 0.85
✅ OCR terminé
✅ Message envoyé avec mode: Markdown
```

**Cas dégradé (OCR indisponible)** :
```
⚠️ Gemini non disponible: Conflit de dépendances...
📝 Création d'une extraction par défaut (fallback)
⚠️ Facture reçue mais OCR indisponible
✅ Message envoyé avec mode: Markdown
```

### User Experience

| Scénario | Message Bot | Action User |
|----------|-------------|-------------|
| OCR OK | "✅ Facture analysée" | Valider si OK |
| OCR Fail | "⚠️ À compléter manuellement" | Compléter dans web app |

---

## 🔮 Améliorations futures

1. **Interface web** : Page de complétion pour factures avec `needs_manual_review=true`
2. **Notification** : Email aux admins quand une facture nécessite complétion
3. **Retry OCR** : Bouton "Réessayer l'OCR" si le service redevient disponible
4. **Cache** : Stocker temporairement les fichiers en attente d'OCR

---

## ✅ Checklist validation

- [ ] Déploiement réussi sans erreur
- [ ] Test upload PDF avec OCR fonctionnel
- [ ] Test upload PDF avec OCR indisponible (fallback)
- [ ] Vérification création facture en DB avec valeurs par défaut
- [ ] Test complétion manuelle via web app
- [ ] Vérification notifications gérants

**Date de mise à jour** : 2024-03-27
**Statut** : ✅ Prêt pour déploiement
