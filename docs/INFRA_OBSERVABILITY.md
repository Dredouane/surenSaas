# Infrastructure d'Observabilité & Traçabilité

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Couche 3 — Monitoring                  │
│  Dashboard de rejeu  |  Golden Dataset  |  Tests NR      │
├──────────────────────────────────────────────────────────┤
│                    Couche 2 — Guardrails                   │
│  Input : toxicité, prompt injection, taille               │
│  Output : JSON valide, schéma, bornage numérique          │
├──────────────────────────────────────────────────────────┤
│                    Couche 1 — Interception                │
│  AgentWrapper (décorateur LLM)  |  AuditService          │
│  HITL Hook (feedback humain → logs_agents)               │
├──────────────────────────────────────────────────────────┤
│              Couche 0 — Socle (ce document)               │
│  logs_activity (mutations CRUD)                          │
│  logs_agents (interactions IA)                           │
│  correlation_id (traçabilité de bout en bout)             │
│  R2 Archiving (blobs agents)                              │
└──────────────────────────────────────────────────────────┘
```

## Socle (Couche 0)

### 1. Le correlation_id

Chaque requête HTTP reçoit un `correlation_id` (UUID v4) injecté par le middleware `log_requests` dans `main.py`.

**Où le trouver :**
- Header HTTP de réponse : `X-Correlation-ID`
- Logs structurés : champ `extra_data.correlation_id`
- Base de données : colonne `correlation_id` dans `logs_activity` et `logs_agents`

**Propagation :**
```python
# Dans un handler API :
correlation_id = request.state.correlation_id

# Dans un service :
await audit.log_activity(correlation_id=correlation_id, ...)

# Dans un agent wrapper :
wrapper = AgentWrapper(audit_service, org_id=org_id, correlation_id=correlation_id)
```

### 2. logs_activity — Traçabilité des mutations

Table : `logs_activity`

Enregistre toute mutation CRUD sur n'importe quelle entité du SaaS.

**Comment l'utiliser dans une nouvelle feature :**

```python
from app.services.audit_service import AuditService

audit = AuditService(supabase_client)

# Après une création
await audit.log_activity(
    org_id=org_id,
    correlation_id=correlation_id,
    action="create",
    table_name="ma_nouvelle_table",
    entity_id=new_entity_id,
    new_state={"nom": "test", "montant": 100},
    user_id=user_id,
    source_system="api",
)

# Après une modification
await audit.log_activity(
    org_id=org_id,
    correlation_id=correlation_id,
    action="update",
    table_name="ma_nouvelle_table",
    entity_id=entity_id,
    previous_state=old_data,
    new_state=new_data,
    user_id=user_id,
)

# Après une suppression
await audit.log_activity(
    org_id=org_id,
    correlation_id=correlation_id,
    action="delete",
    table_name="ma_nouvelle_table",
    entity_id=entity_id,
    previous_state=old_data,
)
```

### 3. logs_agents — Traçabilité des interactions IA

Table : `logs_agents`

Enregistre chaque appel à un modèle LLM avec son contexte complet.

**Utilisation via le AgentWrapper (recommandé) :**

```python
from app.agents.base.agent_wrapper import AgentWrapper
from app.services.audit_service import AuditService

audit = AuditService(supabase)
wrapper = AgentWrapper(
    audit_service=audit,
    org_id=org_id,
    correlation_id=correlation_id,
)

@wrapper.wrap(
    agent_type="gemini_extraction",
    model="gemini-2.5-flash",
    entity_table="invoices",
    entity_id=invoice_id,
    input_guardrails=[guardrail_max_length(5000)],
    output_guardrails=[guardrail_json_valid, guardrail_schema(["montant", "fournisseur"])],
)
async def extract_invoice(text: str):
    return await gemini_client.extract_from_text(text)

result = await extract_invoice("Facture ACME 1000€")
```

**Utilisation manuelle (si décorateur impossible) :**

```python
log_id = await audit.log_agent(
    org_id=org_id,
    correlation_id=correlation_id,
    agent_type="gemini_chat",
    model="gemini-2.5-flash",
    user_prompt=prompt,
    response_text=response,
    status="completed",
    processing_duration_ms=duration,
    input_tokens=100,
    output_tokens=50,
    total_tokens=150,
)
```

### 4. HITL Feedback (Human-In-The-Loop)

Lier une validation humaine à un appel IA précédent :

```python
# Quand un humain valide/rejette le résultat d'un agent :
await audit.record_hitl_feedback(
    agent_log_id="<id du log_agents>",
    feedback="correct",  # ou "incorrect", "edited"
    user_id=user_id,
    action="validate",  # ou "reject", "edit"
)
```

**Requêtage des logs avec feedback HITL :**
```sql
SELECT * FROM logs_agents
WHERE hitl_feedback IS NOT NULL
  AND org_id = '...'
ORDER BY created_at DESC;
```

### 5. Archivage R2 des blobs agents

Le wrapper archive automatiquement le payload complet (prompt + réponse + métadonnées) dans R2 sous :
```
{env}/org/{org_id}/agent/{correlation_id}/{agent_type}.json
```

Le chemin est stocké dans `logs_agents.blob_storage_path`.

### 6. Guardrails prédéfinis

```python
from app.agents.base.agent_wrapper import (
    guardrail_max_length,
    guardrail_json_valid,
    guardrail_schema,
)

# Taille max de l'input
guardrail_max_length(10000)

# La sortie doit être du JSON valide
guardrail_json_valid

# La sortie JSON doit contenir des clés spécifiques
guardrail_schema(["montant", "fournisseur", "date"])
```

Pour créer un guardrail personnalisé :
```python
def mon_guardrail_sortie(result):
    if result.get("montant", 0) < 0:
        raise ValueError("Le montant ne peut pas être négatif")
```

## Migration depuis l'ancien système

| Ancien | Nouveau |
|--------|---------|
| `telegram_audit` | Supprimé (remplacé par `logs_agents` + `logs_activity`) |
| `chantier_audit_trail` | Supprimé (remplacé par `logs_activity`) |
| `invoice_status_history` | Supprimé (remplacé par `logs_activity`) |
| `TelegramAuditService` | Remplacé par `AuditService` |
| `GeminiClient.*` (appels directs) | Passer par `AgentWrapper.wrap()` |

## Ajouter l'observabilité à une nouvelle feature

1. **Dans la route API** : récupérer `correlation_id` depuis `request.state.correlation_id`
2. **Dans le service** : instancier `AuditService` et logger les mutations via `log_activity()`
3. **Pour les appels LLM** : utiliser le décorateur `@wrapper.wrap()`
4. **Pour les validations humaines** : après validation, appeler `audit.record_hitl_feedback()`

Exemple complet :
```python
from fastapi import APIRouter, Request
from app.core.logging import get_logger
from app.api.auth import get_current_user
from app.services.audit_service import AuditService
from app.agents.base.agent_wrapper import AgentWrapper

router = APIRouter(prefix="/api/v1/ma-feature", tags=["ma-feature"])

@router.post("/creer")
async def create_entity(request: Request):
    user = get_current_user(request)
    correlation_id = request.state.correlation_id
    supabase = get_supabase()
    audit = AuditService(supabase)

    entity = supabase.table("ma_table").insert({...}).execute()
    new_id = entity.data[0]["id"]

    await audit.log_activity(
        org_id=user["org_id"],
        correlation_id=correlation_id,
        action="create",
        table_name="ma_table",
        entity_id=new_id,
        new_state=entity.data[0],
        user_id=user["sub"],
    )

    return {"id": new_id}
```
