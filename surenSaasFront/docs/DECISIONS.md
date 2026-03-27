# Décisions Frontend

## ADR-001 : App Router vs Pages Router
**Choix** : App Router (Next.js 14)
**Pourquoi** : Server Components natifs, layout simplifié, routing dynamique [org]

## ADR-002 : Auth Magic Link + Password
**Choix** : Système email+password via Supabase, avec pré-autorisation
**Pourquoi** : Plus simple que Microsoft SSO, pas de dépendance Azure, UX fluide
**Alternatives** : Microsoft Entra ID (rejeté - trop complexe)

## ADR-003 : Images unoptimized
**Choix** : `images: { unoptimized: true }`
**Pourquoi** : Cloud Run ne supporte pas l'optimisation d'images de Next.js
**Impact** : Gestion manuelle des tailles d'images

## ADR-004 : shadcn/ui
**Choix** : shadcn/ui + Tailwind
**Pourquoi** : Composants copiables, pas de dépendance lib, personnalisable
**Alternatives** : MUI, Chakra (rejetés - trop lourds)

## ADR-005 : Theme dynamique CSS
**Choix** : CSS variables injectées côté serveur
**Pourquoi** : Pas de flash thème blanc, SSR compatible
**Stockage** : theme_config JSONB dans organizations

## ADR-006 : Pas de React Hook Form
**Choix** : Forms natifs React avec state
**Pourquoi** : Formulaires simples (login), pas besoin de lib complexe
**Validation** : HTML5 native + Yup si besoin

## ADR-007 : Deep Link + Redirect
**Choix** : Middleware intercepte routes protégées, stocke redirect URL en paramètre query
**Pourquoi** : UX fluide quand user clique lien direct sans être loggué
**Sécurité** : Validation hostname interne uniquement, pas de localStorage (state React)
**UX** : Après login, redirection automatique vers la page demandée

## ADR-008 : Pas de Supabase Client Frontend
**Choix** : Tous les appels Supabase passent par le backend Python
**Pourquoi** : Sécurité - pas de clés exposées au frontend, contrôle total backend
**Inconvénient** : Latence +1 hop, gestion cookies manuelle
**Alternatives** : Supabase Auth direct (rejeté - clés exposées)
