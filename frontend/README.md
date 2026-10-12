# DocMind AI — Frontend

Next.js 14 (App Router) + React 18 + TypeScript + Tailwind CSS + shadcn/ui-pattern components.

## Setup

```bash
npm install
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE_URL at your backend
npm run dev
```

Requires the backend (Step 5) running at the URL configured in `.env.local` — `next.config.mjs`
rewrites `/api/*` to it, so the browser only ever talks same-origin.

## Structure

- `src/app/` — routes (App Router). `(dashboard)` is a route group sharing the authenticated
  sidebar shell; routes outside it (`/`, `/login`, `/register`) are public.
- `src/components/ui/` — shadcn/ui-pattern primitives, themed to the design tokens below.
- `src/components/{documentation,chat,tasks,layout,upload}/` — feature components.
- `src/hooks/` — TanStack Query hooks, one file per backend resource, mirroring the API
  surface from Step 3.
- `src/lib/types.ts` — hand-written TypeScript mirror of the backend's Pydantic schemas.
  **Known drift risk**: flagged in Step 6 as a candidate for OpenAPI-schema codegen in Step 11.

## Design tokens

Blueprint/schematic aesthetic — see `tailwind.config.ts` for the full token list.
Ink navy background, cyan ("blueprint") for structural/static elements, amber
("annotation") for AI-generated content — a deliberate visual distinction between
"the code as it is" and "what the AI added."

## Known trade-offs (see inline comments for full reasoning)

- **Auth tokens**: access token in memory, refresh token in `localStorage`. The more secure
  design (backend-set httpOnly cookie) requires changing the Step 3 auth contract — flagged
  as a Step 11 hardening item, not silently shipped as the "done" version.
- **Route protection**: enforced client-side (`(dashboard)/layout.tsx`), not via Next.js
  middleware, because middleware can't read the in-memory/localStorage token. Same fix
  (httpOnly cookies) would resolve this too.
