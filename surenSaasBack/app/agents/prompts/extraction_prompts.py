"""
Prompts système pour l'extraction de documents avec Gemini.

Chaque type de document a son propre prompt avec instructions spécifiques.
"""

from typing import Dict, Any


BASE_EXTRACTION_PROMPT = """
Tu es un expert en extraction de données depuis des documents.
Ta mission est d'analyser le document fourni et d'extraire TOUTES les informations pertinentes.

RÈGLES ABSOLUES:
1. Retourne UNIQUEMENT un objet JSON valide, sans texte avant ou après
2. Si une information est manquante ou illisible, utilise null (pas de chaîne vide)
3. Sois précis et exhaustif - ne rate aucune information
4. Conserve le format original des données (dates, montants, etc.)
5. Pour les documents multi-pages, analyse TOUTES les pages

FORMAT DE SORTIE:
{
    "document_type": "type_de_document",
    "extracted_data": {
        // Toutes les données extraites ici
    },
    "metadata": {
        "confidence": "high/medium/low",
        "pages_count": nombre_de_pages,
        "extraction_notes": ["note1", "note2"]
    }
}
"""

MULTI_PAGE_EXTRACTION_PROMPT = """
INSTRUCTIONS SPÉCIALES POUR DOCUMENTS MULTI-PAGES:

1. ANALYSE COMPLÈTE:
   - Analyse TOUTES les pages du document
   - Identifie les informations réparties sur plusieurs pages
   - Consolide les données similaires des différentes pages

2. STRUCTURE PAR PAGE (optionnel):
   - Si le document a une structure claire par page, tu peux organiser les données par page
   - Exemple: page 1 = en-tête, page 2 = détails, page 3 = signature

3. DONNÉES RÉPARTIES:
   - Si une information commence sur une page et continue sur la suivante, regroupe-la
   - Exemple: une liste d'articles qui s'étend sur plusieurs pages

4. CONTRÔLE DE QUALITÉ:
   - Vérifie la cohérence des données entre les pages
   - Signale les incohérences dans metadata.issues

FORMAT AVANCÉ POUR MULTI-PAGES (optionnel):
{
    "document_type": "type_de_document",
    "extracted_data": {
        // Données consolidées de toutes les pages
    },
    "page_specific_data": {
        "page_1": { /* données page 1 */ },
        "page_2": { /* données page 2 */ }
    },
    "metadata": {
        "confidence": "high/medium/low",
        "pages_count": nombre_de_pages,
        "pages_analyzed": [1, 2, 3, ...],
        "extraction_notes": ["note1", "note2"]
    }
}
"""


INVOICE_EXTRACTION_PROMPT = """
Tu es un expert comptable spécialisé dans l'extraction de factures.
Analyse cette facture et extrais toutes les informations comptables.

CHAMPS À EXTRAIRE (JSON):
{
    "document_type": "invoice",
    "extracted_data": {
        "supplier": {
            "name": "Nom du fournisseur",
            "address": "Adresse complète",
            "siret": "Numéro SIRET (14 chiffres)",
            "email": "Email si présent",
            "phone": "Téléphone si présent"
        },
        "invoice": {
            "number": "Numéro de facture",
            "date": "Date de facture (YYYY-MM-DD)",
            "due_date": "Date d'échéance (YYYY-MM-DD)",
            "purchase_order": "Numéro de bon de commande si présent"
        },
        "amounts": {
            "ht": "Montant HT (nombre)",
            "ttc": "Montant TTC (nombre)",
            "vat": "Montant TVA (nombre)",
            "vat_rate": "Taux de TVA en % (nombre)"
        },
        "line_items": [
            {
                "description": "Description de la ligne",
                "quantity": "Quantité (nombre)",
                "unit_price": "Prix unitaire HT (nombre)",
                "total_ht": "Total HT ligne (nombre)",
                "vat_rate": "Taux TVA % (nombre)"
            }
        ],
        "payment": {
            "method": "Mode de paiement si indiqué",
            "bank_details": "RIB/IBAN si présent"
        }
    },
    "metadata": {
        "confidence": "high/medium/low",
        "pages_count": 1,
        "issues": ["Problèmes éventuels"]
    }
}

RÈGLES SPÉCIFIQUES FACTURES:
- Si montants incohérents (HT + TVA ≠ TTC), note-le dans metadata.issues
- Si TVA multiple (plusieurs taux), liste-les toutes
- Si aucune TVA (auto-entrepreneur, export), mets vat: 0 et vat_rate: 0
- Pour les lignes de détail, inclues TOUS les articles/services
- Si frais de port séparés, inclue-les comme une ligne

CONVERSION:
- Tous les montants en euros (€)
- Dates au format ISO: YYYY-MM-DD
- Numéros sans espaces (SIRET: 12345678901234)
"""


RECEIPT_EXTRACTION_PROMPT = """
Tu es un expert en analyse de tickets de caisse.
Extrais toutes les informations de ce ticket.

CHAMPS À EXTRAIRE (JSON):
{
    "document_type": "receipt",
    "extracted_data": {
        "merchant": {
            "name": "Nom du magasin",
            "address": "Adresse",
            "siret": "SIRET si présent"
        },
        "transaction": {
            "date": "Date (YYYY-MM-DD)",
            "time": "Heure (HH:MM)",
            "ticket_number": "Numéro de ticket"
        },
        "items": [
            {
                "description": "Nom article",
                "quantity": 1,
                "unit_price": 10.50,
                "total": 10.50,
                "category": "catégorie si identifiable"
            }
        ],
        "amounts": {
            "subtotal": "Sous-total",
            "discount": "Remise si présente",
            "total": "Total TTC"
        },
        "payment": {
            "method": "CB/Espèces/Chèque",
            "card_last_digits": "4 derniers chiffres CB si visible"
        }
    },
    "metadata": {
        "confidence": "high/medium/low",
        "readable": true/false
    }
}
"""


CONTRACT_EXTRACTION_PROMPT = """
Tu es un expert juridique en analyse de contrats.
Extrais les clauses principales et informations contractuelles.

CHAMPS À EXTRAIRE (JSON):
{
    "document_type": "contract",
    "extracted_data": {
        "parties": {
            "party_a": {
                "name": "Nom partie A",
                "role": "Prestataire/Client/etc",
                "address": "Adresse"
            },
            "party_b": {
                "name": "Nom partie B",
                "role": "Client/Prestataire/etc",
                "address": "Adresse"
            }
        },
        "contract": {
            "title": "Titre/titre du contrat",
            "reference": "Référence/numéro",
            "start_date": "Date début (YYYY-MM-DD)",
            "end_date": "Date fin (YYYY-MM-DD)",
            "duration": "Durée en mois si précisée",
            "renewal": "Modalités de renouvellement"
        },
        "financial": {
            "total_amount": "Montant total",
            "payment_terms": "Modalités de paiement",
            "currency": "Devise"
        },
        "clauses": [
            {
                "title": "Titre clause",
                "summary": "Résumé de la clause"
            }
        ],
        "signatures": {
            "date": "Date de signature",
            "location": "Lieu de signature"
        }
    },
    "metadata": {
        "confidence": "high/medium/low",
        "pages_count": 3,
        "document_completeness": "complete/partial"
    }
}
"""


def get_prompt(document_type: str, multi_page: bool = False) -> str:
    """
    Retourne le prompt approprié pour un type de document.
    
    Args:
        document_type: Type de document (invoice, receipt, contract, etc.)
        multi_page: Inclure les instructions pour documents multi-pages
        
    Returns:
        Prompt système complet
    """
    prompts = {
        "invoice": INVOICE_EXTRACTION_PROMPT,
        "receipt": RECEIPT_EXTRACTION_PROMPT,
        "contract": CONTRACT_EXTRACTION_PROMPT,
    }
    
    prompt = prompts.get(document_type, BASE_EXTRACTION_PROMPT)
    
    # Construire le prompt complet
    full_prompt = BASE_EXTRACTION_PROMPT + "\n\n" + prompt
    
    # Ajouter les instructions multi-pages si demandé
    if multi_page:
        full_prompt += "\n\n" + MULTI_PAGE_EXTRACTION_PROMPT
    
    return full_prompt


def create_custom_prompt(
    document_type: str,
    fields: Dict[str, Any],
    instructions: str = "",
    multi_page: bool = False
) -> str:
    """
    Crée un prompt personnalisé pour un type de document spécifique.
    
    Args:
        document_type: Type de document
        fields: Dictionnaire des champs attendus
        instructions: Instructions supplémentaires
        multi_page: Inclure les instructions pour documents multi-pages
        
    Returns:
        Prompt personnalisé
    """
    schema = {
        "document_type": document_type,
        "extracted_data": fields,
        "metadata": {
            "confidence": "high/medium/low",
            "pages_count": "nombre"
        }
    }
    
    # Construire le prompt de base
    base_prompt = f"""
{BASE_EXTRACTION_PROMPT}

INSTRUCTIONS SPÉCIFIQUES:
{instructions}

SCHÉMA DE SORTIE ATTENDU:
{schema}
"""
    
    # Ajouter les instructions multi-pages si demandé
    if multi_page:
        base_prompt += "\n\n" + MULTI_PAGE_EXTRACTION_PROMPT
    
    return base_prompt
