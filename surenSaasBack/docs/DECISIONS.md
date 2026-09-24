# Backend Decisions

## ADR-001 : Contract-first OpenAPI
**Choice**: OpenAPI YAML generates the FastAPI code
**Why**: API documented from the design phase, front/back sync
**Tool**: openapi-generator-cli

## ADR-002 : No ORM
**Choice**: Direct Supabase client (no SQLAlchemy ORM)
**Why**: Supabase RLS policies already in place, fewer layers
**Alternative**: Prisma (rejected - unnecessary complexity)

## ADR-003 : Scale-to-zero backend
**Choice**: Cloud Run with min instances = 0
**Why**: Savings on non-prod environments
**Cold start**: Acceptable (<2s) for an API backend

## ADR-004 : Separate workers
**Choice**: AI agents in a separate process (Celery)
**Why**: Cloud Run is stateless, no long-running in the API
**Queue**: Redis or Cloud Tasks

## ADR-005 : Manual JWT validation
**Choice**: JWT validation in FastAPI (no Supabase dependency)
**Why**: Full control over claims, verification of authorized_users

## ADR-006 : Magic Link + Password Auth
**Choice**: Email+password system with pre_authorized_emails table
**Why**: 
- Simpler to maintain than Microsoft SSO
- No external dependency (Azure)
- Full control over invitations
- Rate limiting easy to implement
**Alternatives**: Microsoft Entra ID (rejected - complexity, cost, dependency)

## ADR-007 : In-memory rate limiting
**Choice**: Python in-memory storage (no Redis)
**Why**: No external dependency, sufficient for Cloud Run scale, simpler
**Implementation**: Dictionary {hash(IP+UA): [timestamps]} with auto cleanup

## ADR-008 : No complex password validation
**Choice**: Min 8 characters only
**Why**: NIST recommends length > complexity
**UX**: Less friction for users

## ADR-009 : Capabilities System
**Choice**: Granular `resource:action` permissions instead of binary roles
**Why**: 
- Flexibility for multi-SMB (construction, cleaning, etc.)
- Specific capabilities per subsidiary company
- Automatic admin bypass
**Format**: `construction:invoicing:read`
**Implementation**: Tables `user_capabilities` + `organization_capabilities`

## ADR-010 : Telegram bot per company
**Choice**: A bot can be linked to a subsidiary company or the global org
**Why**: 
- Separation of concerns
- Custom configuration per business
- Targeted notifications
**Architecture**: Services separated by primitive (button)

## ADR-011 : Complete Telegram audit
**Choice**: `telegram_audit` table logs all interactions
**Why**: 
- Workflow debugging
- Error monitoring
- Business traceability
**Data**: Payload, result, timing, errors

## ADR-012 : Agentic OCR - Shell
**Choice**: Workflow structure ready but OCR not implemented
**Why**: 
- Extensible architecture
- Contracts defined first
- AI implementation in a second phase
**Structure**: `app/agents/invoice_ocr/workflow.py` + `contracts.py`

## ADR-013 : Multi-status invoices
**Choice**: Workflow with 6 statuses and full history
**Status**: draft → pending_validation → [validated/rejected] → accountant_processing → archived
**Why**: Full life cycle traceability
**Table**: `invoice_status_history` logs all changes

## ADR-014 : Telegram Webhook Security
**Choice**: Double security on webhooks
**Mechanisms**:
1. Token hash in the URL (not the token in clear text)
2. Header `X-Telegram-Bot-Api-Secret-Token` verified
**Why**: Security even if the URL leaks

## ADR-015 : Admin Space - User and permission management
**Choice**: Dedicated admin interface to manage access
**Features**:
1. **Email pre-authorization**: Admin adds/removes emails authorized to join the org
2. **Granular capabilities**: Assign `resource:action` permissions per user
3. **Per-resource scope**: Global capabilities or limited to a subsidiary company
**API Routes**: `/admin/*` (OpenAPI contract-first)
**Architecture**: 
- Service layer `app/services/admin_service.py` calls the Supabase REST API
- Frontend pages under `/dashboard/settings/admin/`
- Guard component `AdminGuard.tsx` for route protection
**Why**:
- Full control over who can join the organization
- Fine-grained permissions suited to multi-SMB
- Clear separation between admin and standard user
