---
name: hermes-email-technical
description: Détails techniques du pipeline email V2 — endpoints API, migration SQL, structure email_ai_analysis, execution dispatch.
---

# Hermès Email Technical V2

## Flux complet

```
Ingestion IMAP → Stockage → Vectorisation → ChantierRouter
    → email_threads.status = READY_FOR_AI
    → Hermès poll GET /ready-for-analysis
    → Hermès analyse (LLM Gemini)
    → Hermès POST /{thread_id}/analysis
    → email_ai_analysis créé + status = PENDING_VALIDATION
    → Humain clique "Valider" sur Telegram/Front
    → POST /analysis/{id}/execute
    → Backend exécute proposed_actions (dépenses/tâches/notifications)
    → status = PROCESSED
```

## Endpoints

### GET /api/v1/emails/ready-for-analysis
- **Query** : `org_id`, `company_id` (opt), `limit` (max 50)
- **Filtre** : `email_threads.status = 'READY_FOR_AI' AND detected_chantier_id IS NOT NULL`
- **Retourne** : Threads avec emails, attachments, infos chantier

### POST /api/v1/emails/{thread_id}/analysis
- **Body** : `{summary, detected_urgency, proposed_actions, raw_llm_response}`
- **Validation** : Thread doit être en `READY_FOR_AI`
- **Effet** : Crée `email_ai_analysis` + passe thread en `PENDING_VALIDATION`

### POST /api/v1/analysis/{analysis_id}/execute
- **Body** : `{action: "accept"|"reject", rejection_reason?}`
- **Validation** : Analyse doit exister, thread en `PENDING_VALIDATION`
- **Effet accept** : Exécute `proposed_actions` (CREATE_EXPENSE, CREATE_TASK, SEND_NOTIFICATION)
- **Effet reject** : Marque thread `REJECTED` avec raison

## proposed_actions

```json
[{"type": "CREATE_EXPENSE", "payload": {"montant": 450, "fournisseur": "..."}},
 {"type": "CREATE_TASK", "payload": {"titre": "...", "priorite": "haute"}},
 {"type": "SEND_NOTIFICATION", "payload": {"message": "...", "urgence": "critical"}}]
```

## Migration SQL

`db/schema/022_email_v2_cycle_vie.sql` :
- Crée l'enum `email_processing_status`
- Ajoute `status` + `detected_chantier_id` à `email_threads`
- Crée `email_ai_analysis`
- Migre les statuts existants vers `READY_FOR_AI`
