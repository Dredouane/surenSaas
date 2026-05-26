---
name: hermes-email-domain
description: Defines ubiquitous language for Hermès email processing, including Chantiers, Email Threads, routing, extraction, and dispatch actions. Use when working on the email agent pipeline.
---

# Hermès Email Processing Domain Language

Core terminology for the SurenSaaS email integration.

## Core Entities

- **Chantier**: A construction project. Primary context for incoming emails. Linked via `chantier_id`.
- **Email**: Individual email message stored after ingestion. Has `gmail_thread_id` for threading.
- **EmailThread**: A conversation thread. Can span multiple emails. Linked to a Chantier via `chantier_id`.
- **Hermes Pipeline**: Automated workflow: Ingestion → Routing → Vectorization → Extraction → Dispatch.

## Key Concepts

- **Email Ingestion**: Gmail sync via `SyncService`, `GmailClient`, `EmailChainService`.
- **Chantier Routing**: Associate email with correct Chantier (3 passes: keyword, vector, LLM).
- **Embedding**: Vector representation (768-dim, text-embedding-004) for similarity search.
- **Structured Extraction**: Pydantic models from LLM (tasks, expenses, notifications).
- **Dispatch**: Auto-create tasks, expenses, notifications in backend.
- **Alias Routing**: `REDACTED_EMAIL` format.
- **Notifications**: Telegram alerts via NotificationService.
