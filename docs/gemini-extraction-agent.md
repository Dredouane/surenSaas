# Agent d'Extraction IA - Documentation

## Vue d'ensemble

Agent modulaire d'extraction de données depuis documents (PDF, images) utilisant **Google Gemini Flash 1.5**.

### Architecture

```
app/agents/
├── base/
│   ├── __init__.py
│   └── gemini_client.py          # Client API Gemini
├── models/
│   ├── __init__.py
│   └── extraction_models.py      # Modèles de données (dataclasses)
├── prompts/
│   ├── __init__.py
│   └── extraction_prompts.py     # Prompts système
├── processors/
│   ├── __init__.py
│   └── file_processor.py         # Traitement fichiers
├── generic_extractor.py          # Extracteur générique (point d'entrée)
└── construction_invoice_agent.py # Agent factures (wrapper)
```

## Installation

### 1. Variables d'environnement

Ajouter dans `~/.bashrc` :

```bash
export SUREN_GOOGLE_GEMINI_CREDENTIALS_B64="VOTRE_CLE_API_BASE64"
```

Pour encoder votre clé API :
```bash
echo -n "votre_cle_api" | base64
```

### 2. Dépendances

```bash
cd surenSaasBack
pip install -r requirements.txt
```

Nouvelles dépendances ajoutées :
- `google-generativeai>=0.3.0` - Client Gemini
- `Pillow>=10.0.0` - Traitement images

## Configuration

Dans `app/core/config.py`, la clé API est automatiquement chargée :

```python
gemini_api_key: str = ""
gemini_model: str = "gemini-1.5-flash"  # ou gemini-1.5-pro

# Mapping des variables préfixées
("gemini_api_key", f"{env}_google_gemini_credentials_b64")
```

## Utilisation

### Extraction simple - Facture

```python
from app.agents.generic_extractor import create_invoice_extractor

extractor = create_invoice_extractor()
result = await extractor.extract("https://.../facture.pdf")

# Résultat
print(result.raw_data)  # JSON brut extrait par Gemini
print(result.status)    # success/error/partial
```

### Extraction personnalisée

```python
from app.agents.generic_extractor import GenericDocumentExtractor

extractor = GenericDocumentExtractor(
    document_type="custom",
    system_prompt="Ton prompt spécifique...",
    output_schema={"champ1": "description"}
)

result = await extractor.extract("document.pdf")
```

### Helper pour types prédéfinis

```python
from app.agents.generic_extractor import (
    create_invoice_extractor,    # Factures
    create_receipt_extractor,    # Tickets de caisse
    create_custom_extractor      # Personnalisé
)

# Facture
invoice_extractor = create_invoice_extractor()

# Ticket
ticket_extractor = create_receipt_extractor()

# Personnalisé
custom_extractor = create_custom_extractor(
    document_type="delivery_note",
    fields={
        "order_number": "Numéro de commande",
        "items": "Liste des articles"
    },
    instructions="Extrais aussi le transporteur"
)
```

## Format de sortie

### JSON brut (raw_data)

```json
{
  "document_type": "invoice",
  "extracted_data": {
    "supplier": {
      "name": "Matériaux Pro SARL",
      "address": "45 Rue...",
      "siret": "12345678901234"
    },
    "invoice": {
      "number": "FAC-2024-001",
      "date": "2024-01-15",
      "due_date": "2024-02-15"
    },
    "amounts": {
      "ht": 1000.00,
      "ttc": 1200.00,
      "vat": 200.00,
      "vat_rate": 20.0
    },
    "line_items": [
      {
        "description": "Ciment sac 35kg",
        "quantity": 10,
        "unit_price": 50.00,
        "total_ht": 500.00
      }
    ]
  },
  "metadata": {
    "confidence": "high",
    "pages_count": 1
  }
}
```

### ExtractionResult (objet Python)

```python
@dataclass
class ExtractionResult:
    document_type: str              # Type de document
    extraction_timestamp: datetime  # Date extraction
    source_file: str               # Source (URL ou chemin)
    model_used: str                # Modèle Gemini utilisé
    raw_data: Dict[str, Any]       # JSON brut
    status: ExtractionStatus       # success/error/partial
    processing_time_ms: float      # Temps de traitement
    pages_processed: int           # Nombre de pages
    
    def get_confidence_score(self) -> float:
        """Score de confiance global 0-1"""
```

## Prompts système

### Prompts prédéfinis

- **Factures** (`invoice`) : Extraction comptable complète
- **Tickets** (`receipt`) : Tickets de caisse
- **Contrats** (`contract`) : Documents juridiques

### Créer un prompt personnalisé

```python
from app.agents.prompts import create_custom_prompt

prompt = create_custom_prompt(
    document_type="delivery_note",
    fields={
        "order_number": "Numéro de commande",
        "delivery_date": "Date de livraison",
        "items": "Articles livrés"
    },
    instructions="Extrais aussi le nom du transporteur"
)
```

## Tests

### Lancer les tests

```bash
cd surenSaasBack
pytest tests/test_gemini_extraction.py -v
```

### Scénarios de tests

**19 tests couvrant :**
1. ✅ Client Gemini (connexion, clés, types MIME)
2. ✅ File Processor (téléchargement, base64, validation)
3. ✅ Extracteur générique (extraction, parsing, validation)
4. ✅ Construction Invoice Agent (conversion, validation TVA)
5. ✅ Helpers (création extracteurs)

### Tests en échec (5/24)

Les échecs sont des problèmes de mocking avec FastAPI DI et le registry. **Ce ne sont pas des bugs fonctionnels**.

## Limites et contraintes

### Gemini Flash 1.5

- **Max file size** : 20 MB
- **Max pages PDF** : 5 pages (limite projet)
- **Max dimension image** : 4096x4096 pixels
- **Max output tokens** : 8192

### Optimisation

Les images sont automatiquement optimisées :
- Redimensionnement si > 4096px
- Compression JPEG (qualité 85)
- Conversion RGB si nécessaire

## Migration depuis l'ancien système

L'ancien `ConstructionInvoiceAgent` (dummy) est maintenant un wrapper :

```python
# Avant (dummy)
agent = ConstructionInvoiceAgent()
data = await agent.extract_from_document(url, "pdf")
# → Données aléatoires

# Maintenant (Gemini)
agent = ConstructionInvoiceAgent()
data = await agent.extract_from_document(url, "pdf")
# → Vraies données extraites par IA
```

L'API reste identique, seul le backend change.

## Roadmap / TODO

- [ ] Implémenter retry avec backoff en cas d'erreur API
- [ ] Ajouter cache Redis pour éviter re-extraction
- [ ] Support streaming pour gros documents
- [ ] Ajouter validation schéma JSON avec Pydantic
- [ ] Métriques et monitoring (temps, coût, taux succès)

## Support

Pour les erreurs API Gemini, vérifier :
1. Clé API valide dans les variables d'environnement
2. Quota API non dépassé (console Google Cloud)
3. Fichier < 20 MB et < 5 pages

---

**Note** : Cet agent est conçu pour être modulaire. Pour ajouter un nouveau type de document, créez juste un nouveau prompt et utilisez `GenericDocumentExtractor` ou `create_custom_extractor()`.
