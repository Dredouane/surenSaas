from typing import Optional
from datetime import date
import logging
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.api.auth import get_supabase

logger = logging.getLogger(__name__)


class CreateDepenseSchemaV2(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    chantier_id: str = Field(description="L'ID ou la référence du chantier")
    description: str = Field(description="Description de la dépense")
    montant: float = Field(0.0, description="Montant TTC de la dépense")
    fournisseur: str = Field("Telegram", description="Nom du fournisseur")
    categorie: str = Field(
        "autre",
        description=(
            "Catégorie parmi : fournisseur, sous_traitant, "
            "achat_direct, location, carburant, divers"
        ),
    )
    date_depense: Optional[str] = Field(
        None, description="Date de la dépense (YYYY-MM-DD). Défaut : aujourd'hui."
    )


def _create_depense_internal(
    org_id: str,
    chantier_id: str,
    description: str,
    montant: float = 0.0,
    fournisseur: str = "Telegram",
    categorie: str = "autre",
    date_depense: Optional[str] = None,
    _supabase=None,
) -> dict:
    """Implémentation réelle de create_depense, sans décorateur @tool.

    Retourne un dict standard (success/data/error/suggestion/message).
    """
    # R5 : Vérifier date future
    depense_date = date_depense or date.today().isoformat()
    try:
        parsed_date = date.fromisoformat(depense_date)
        if parsed_date > date.today():
            return {
                "success": False,
                "data": None,
                "error": f"Date {depense_date} dans le futur. Impossible d'enregistrer une dépense future.",
                "suggestion": "Utilise la date réelle de la dépense (passée ou aujourd'hui).",
                "message": None,
            }
    except (ValueError, TypeError):
        return {
            "success": False,
            "data": None,
            "error": f"Format de date invalide: {depense_date!r}",
            "suggestion": "Utilise le format YYYY-MM-DD.",
            "message": None,
        }

    depense_data = {
        "chantier_id": chantier_id,
        "org_id": org_id,
        "description": description,
        "fournisseur": fournisseur,
        "montant": float(montant),
        "date": depense_date,
        "categorie": categorie,
        # 'statut' est un enum géré par la DB (default='validee')
        # 'status' est une colonne text libre pour le workflow
        "status": "en_attente_validation",
    }

    try:
        sb = _supabase or get_supabase()
        result = sb.table("chantier_depenses").insert(depense_data).execute()
        created_id = result.data[0]["id"] if result.data else None
        logger.info("[DEPENSE_TOOL] Dépense créée: %s", created_id)
        return {
            "success": True,
            "data": {"id": created_id} if created_id else {},
            "error": None,
            "suggestion": None,
            "message": f"Dépense {fournisseur} - {montant}€ enregistrée (en attente validation).",
        }
    except Exception as e:
        logger.error("[DEPENSE_TOOL] Erreur création dépense: %s", e)
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "suggestion": "Réessaie ou contacte le support.",
            "message": None,
        }


@tool("create_depense", args_schema=CreateDepenseSchemaV2)
def create_depense(
    org_id: str,
    chantier_id: str,
    description: str,
    montant: float = 0.0,
    fournisseur: str = "Telegram",
    categorie: str = "autre",
    date_depense: Optional[str] = None,
    context_summary: str = "",
) -> dict:
    """Persiste une dépense en DB avec le statut 'en_attente_validation'.

    Appelée uniquement APRÈS que le conducteur a validé les données extraites
    (HITL#1). La validation métier (règles R1-R7) est faite en amont par le LLM.
    N'affiche aucun message à l'utilisateur — se charge uniquement de l'insertion.
    """
    return _create_depense_internal(
        org_id=org_id,
        chantier_id=chantier_id,
        description=description,
        montant=montant,
        fournisseur=fournisseur,
        categorie=categorie,
        date_depense=date_depense,
    )
