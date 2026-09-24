# Frontend Decisions

## ADR-001 : App Router vs Pages Router
**Choice**: App Router (Next.js 14)
**Why**: Native Server Components, simplified layout, dynamic [org] routing

## ADR-002 : Magic Link + Password Auth
**Choice**: Email+password system via Supabase, with pre-authorization
**Why**: Simpler than Microsoft SSO, no Azure dependency, smooth UX
**Alternatives**: Microsoft Entra ID (rejected - too complex)

## ADR-003 : Images unoptimized
**Choice**: `images: { unoptimized: true }`
**Why**: Cloud Run does not support Next.js image optimization
**Impact**: Manual management of image sizes

## ADR-004 : shadcn/ui
**Choice**: shadcn/ui + Tailwind
**Why**: Copyable components, no lib dependency, customizable
**Alternatives**: MUI, Chakra (rejected - too heavy)

## ADR-005 : Dynamic CSS theme
**Choice**: CSS variables injected server-side
**Why**: No white theme flash, SSR compatible
**Storage**: theme_config JSONB in organizations

## ADR-006 : No React Hook Form
**Choice**: Native React forms with state
**Why**: Simple forms (login), no need for a complex lib
**Validation**: Native HTML5 + Yup if needed

## ADR-007 : Deep Link + Redirect
**Choice**: Middleware intercepts protected routes, stores redirect URL in query parameter
**Why**: Smooth UX when user clicks a direct link without being logged in
**Security**: Internal hostname validation only, no localStorage (React state)
**UX**: After login, automatic redirect to the requested page

## ADR-008 : No Supabase Frontend Client
**Choice**: All Supabase calls go through the Python backend
**Why**: Security - no keys exposed to the frontend, full backend control
**Drawback**: Latency +1 hop, manual cookie management
**Alternatives**: Direct Supabase Auth (rejected - exposed keys)
