---
name: hermes-email-technical
description: Technical implementation details of the Hermès email pipeline — LLM with_structured_output, pgvector RPC, async patterns, dispatch logic. Use when modifying the pipeline code.
---

# Hermès Email Integration: Technical Deep Dive

## 1. Chantier Routing (`services/emails/chantier_router.py`)

**3-pass strategy:**

- **Pass 1 — Keyword**: SQL ILIKE on `chantiers.nom`/`ref`. Confidence 0.90. Requires unique match.
- **Pass 2 — Vector**: Generate embedding → pgvector `match_chantiers` RPC. Threshold 0.72.
- **Pass 3 — LLM**: Gemini with_structured_output. Threshold 0.60. Validates UUID against DB.

Uses `vertex_service.get_chat_model().with_structured_output(_LLMRoutingOutput)`.

## 2. Hermès Extractor (`services/emails/hermes_extractor.py`)

- **LLM**: `.with_structured_output(HermesExtractionResult)`.
- **Dispatch**: Calls `_manage_taches_internal`, `_create_depense_internal`, `NotificationService`.
- **Audit**: Every action logged to `hermes_dispatch_log`.
- **LLM calls wrapped** in `run_in_executor` (sync LangChain invoke).

## 3. Async Pipeline

Triggered in `sync_service.py` via `asyncio.create_task(_run_hermes_pipeline(...))` after vectorization.

Flow: `ChantierRouter.route()` → update `email_threads` → `HermesExtractor.extract_and_dispatch()`.

## 4. Database

- Supabase client via `get_supabase()`.
- pgvector for `chantier_embeddings` and `match_chantiers` RPC.
- Migrations in `db/schema/NNN_*.sql`.

## 5. Email Accounts

Table: `email_accounts` with columns `id, org_id, email_address, oauth_refresh_token, is_active`.

The base Gmail address is `REDACTED_EMAIL`. Alias format: `+{org_slug}#{company_slug}` (separator configurable via `EMAIL_ALIAS_SEPARATOR`, default `#`).

## 6. Key Files

| File | Role |
|------|------|
| `services/emails/sync_service.py` | Orchestrator: Gmail poll → process → vectorize → Hermès |
| `services/emails/chantier_router.py` | 3-pass Chantier routing |
| `services/emails/hermes_extractor.py` | LLM extraction + dispatch |
| `services/emails/alias_router.py` | Parse `Delivered-To` alias → org/company |
| `services/emails/embedding_service.py` | Vector generation (text-embedding-004) |
| `scripts/hermes_email_sync.py` | Cron entrypoint |
| `db/schema/020_hermes_email_chantier.sql` | Migration: new tables + RPC |
