---
name: hermes-email-domain
description: Définit le langage ubiquitaire pour le pipeline d'emails Hermès V2. Utiliser pour toute modification du flux email (ingestion, analyse HITL, exécution).
---

# Hermès Email Domain Language V2

## Cycle de vie email_processing_status

| Statut | Signification | Déclenché par |
|--------|--------------|---------------|
| `NEW` | Email reçu brut, pas encore traité | Backend (ingestion) |
| `READY_FOR_AI` | Vectorisé + chantier identifié, prêt pour Hermès | Backend (vectorisation) |
| `PENDING_VALIDATION` | Hermès a soumis son analyse, en attente de l'humain | Hermès (POST /analysis) |
| `PROCESSED` | Actions exécutées après validation humaine | Backend (POST /execute) |
| `REJECTED` | L'humain a refusé l'analyse | Backend (POST /execute reject) |
| `FAILED` | Erreur technique (OCR, embedding, etc.) | Backend |

## Rôles

- **Backend (Cloud Run)** : Plomberie (ingestion IMAP, stockage, vectorisation, endpoints API)
- **Hermès (VPS)** : Cerveau (analyse LLM, propositions d'actions, orchestration)
- **Utilisateur** : Valide ou rejette les propositions via Telegram ou Frontend

## Endpoints Hermès

| Endpoint | Rôle |
|----------|------|
| `GET /api/v1/emails/ready-for-analysis` | Hermès récupère les threads prêts (READY_FOR_AI) |
| `POST /api/v1/emails/{thread_id}/analysis` | Hermès soumet son analyse structurée |
| `POST /api/v1/analysis/{analysis_id}/execute` | L'humain valide et le backend exécute |

## Tables

- `email_ai_analysis` : Stocke les propositions Hermès (summary, proposed_actions, raw_llm_response)
- `email_threads.status` : Cycle de vie géré via l'enum email_processing_status
