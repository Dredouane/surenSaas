# Task: Phase 1 — Extraire le tool `create_depense` propre

## Objective
Extraire la logique de persistance DB de `handle_save_depense()` (dans `app/api/bot_construction_depenses.py:95-136`) dans un tool LangGraph pur à `app/agents/tools/depense_tools.py`.

Le tool NE DOIT PAS :
- Poser des questions à l'utilisateur
- Envoyer des messages Telegram
- Gérer les notifications
- Gérer les états de session (set_state/get_state)

Le tool DOIT :
- Prendre un objet JSON validé et le persister en DB
- Retourner un résultat clair (succès/échec + id créé)

## Context

### Source à extraire

**`/opt/projects/suren/saas/surenSaas/surenSaasBack/app/api/bot_construction_depenses.py:95-136`**
```python
async def handle_save_depense(telegram_id, bot_config, supabase, org_id):
    state = await get_state(telegram_id, supabase, org_id)
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    data = state.get('last_state_data', {})
    depense_data = {
        "chantier_id": chantier["id"],
        "org_id": org_id,
        "description": data.get('description', '...'),
        "fournisseur": data.get('fournisseur', 'Telegram'),
        "montant": float(data.get('montant', 0)),
        "date": date.today().isoformat(),
        "categorie": data.get('categorie', 'autre')
    }
    supabase.table("chantier_depenses").insert(depense_data).execute()
    # ... notifications + messages (on enlève tout ça)
    return {"ok": True}
```

### Cible à créer

**`/opt/projects/suren/saas/surenSaas/surenSaasBack/app/agents/tools/depense_tools.py`**

Créer la fonction :
```python
from typing import Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)

async def create_depense(
    supabase,
    chantier_id: str,
    org_id: str,
    description: str,
    montant: float,
    fournisseur: Optional[str] = None,
    categorie: str = "autre",
    date_depense: Optional[str] = None,  # ISO format, default today
) -> dict:
    """
    Persiste une dépense en DB avec statut=en_attente_validation.
    
    Args:
        supabase: Supabase client
        chantier_id: UUID du chantier
        org_id: UUID de l'organisation
        description: Description textuelle
        montant: Montant TTC (float)
        fournisseur: Nom du fournisseur (optionnel, défaut "Telegram")
        categorie: Catégorie parmi: fournisseur, sous_traitant, achat_direct, location, carburant, divers
        date_depense: Date ISO (optionnel, défaut aujourd'hui)
    
    Returns:
        dict avec {"ok": bool, "id": str|None, "error": str|None}
    """
    depense_data = {
        "chantier_id": chantier_id,
        "org_id": org_id,
        "description": description,
        "fournisseur": fournisseur or "Telegram",
        "montant": float(montant),
        "date": date_depense or date.today().isoformat(),
        "categorie": categorie,
        "statut": "en_attente_validation",
    }
    
    try:
        result = supabase.table("chantier_depenses").insert(depense_data).execute()
        created_id = result.data[0]["id"] if result.data else None
        logger.info("[DEPENSE_TOOL] Dépense créée: %s", created_id)
        return {"ok": True, "id": created_id, "error": None}
    except Exception as e:
        logger.error("[DEPENSE_TOOL] Erreur création dépense: %s", e)
        return {"ok": False, "id": None, "error": str(e)}
```

### Constraints
- Utiliser la convention `statut` et pas `status`
- Les catégories valides: fournisseur, sous_traitant, achat_direct, location, carburant, divers
- Retourner TOUJOURS un dict avec les 3 clés: ok, id, error
- Logger avec préfixe [DEPENSE_TOOL]
- Ne PAS importer de modules d'envoi Telegram

## Expected Outcome
- `/opt/projects/suren/saas/surenSaas/surenSaasBack/app/agents/tools/depense_tools.py` créé avec `create_depense()`
- La fonction est self-contained (ne dépend que de supabase, pas de state/notifications/telegram)
- Peut être appelée depuis n'importe où (LangGraph, test, script)
