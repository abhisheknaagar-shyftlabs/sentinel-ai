# Sentinel AI — Frontend

**AI Engineering Control Center.** Sentinel AI watches every pull request, every container, and every dollar of infrastructure spend — then tells your team exactly what needs attention next, before it turns into an incident, a missed deadline, or a budget surprise.

This is the production-grade frontend: React + TypeScript + Tailwind, built feature-first with a mock data layer that swaps cleanly to a real FastAPI backend.

## Quick start

```bash
npm install
npm run dev        # http://localhost:5173 (or the port Vite prints)
```

The app boots on the **landing page**. Click **Get started** / **Sign in** and enter any email + a 6+ character password to enter the authenticated app (auth is mocked for the demo).

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start the Vite dev server with HMR |
| `npm run build` | Type-check (`tsc -b`) and build for production |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |
| `npm run format` | Format with Prettier |

## Pages

Public: **Landing**, **Login**.
Authenticated (inside the AppShell): **Dashboard**, **Development Intelligence**, **Production Intelligence**, **Executive Intelligence**, **Integrations**, **Settings**.

## Tech stack

- **React 19 + TypeScript** (strict, no `any`)
- **Vite** build tooling
- **TailwindCSS v4** with a dark, token-driven design system (no hardcoded colors)
- **shadcn/ui** for base components
- **TanStack Query** for server state (loading / error / retry / cache)
- **Zustand** for UI state (sidebar, mobile nav, auth session)
- **React Hook Form + Zod** for type-safe forms (login, settings)
- **Recharts** for charts, **motion** for landing animations

## Architecture

Feature-first. Each feature owns its own slice:

```
src/
├── app/            # providers, query client
├── components/
│   ├── ui/         # shadcn primitives
│   ├── shared/     # reusable app components (StatCard, DataTable, badges, states…)
│   └── brand/      # logo
├── features/       # dashboard, development-intelligence, production-intelligence,
│   │               # executive-intelligence, integrations, settings, auth, landing
│   └── <feature>/  # components / api / hooks / types / mock / utils
├── layouts/        # AppShell, Sidebar, Topbar
├── pages/          # one file per route (lazy-loaded)
├── routes/         # route table, ProtectedRoute, paths
├── services/       # http-client, mock utilities
├── stores/         # Zustand stores
├── types/          # shared domain types
└── utils/          # cn, formatters
```

### Data layer

No component calls `fetch` directly. Every endpoint flows through
`feature/api/*.api.ts` → `feature/hooks/*.ts` (React Query) → component.

Every `*.api.ts` calls the real backend directly - the mock-data toggle and
`feature/mock/*.mock.ts` fixtures have been removed now that the backend is
integrated end to end, so there's no fallback path that could silently show
stale/fake data. Point at the backend via:

```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000/api
```
