# Frontend Architecture

## Stack

- React + TypeScript, built with Vite.
- `oxlint` for linting (replaces ESLint in this project — see "Linting"
  below).
- TanStack Query v5 for all server state.
- Tailwind CSS v4 + a hand-maintained Mechanicum design-system CSS layer for
  theming (see "Styling").
- Vitest + React Testing Library + MSW for testing — see
  `08-frontend-testing.md`.

The frontend talks to the FastAPI backend over REST only. Per
`01-architecture.md`, it must never import Python domain code or reimplement
rule-engine logic client-side — colony math, thresholds, and stat derivation
belong entirely to the backend. The frontend's job is to display what the
API returns and to send GM-entered inputs (roll results, upgrade
installs, custom modifiers) back to it.

## Layering

Actual layout — the FE is a root-level Vite SPA (no `frontend/` subdir); the
Python backend sits beside it under `src/colony_manager/`:

```text
src/
  components/     # presentational UI + feature-scoped containers
  lib/            # shared request/error layer (api.ts, error.ts) + calculators
  types/          # API types (colony.ts, generated api.d.ts)
  data/           # static FE config (rulesData.ts, seedData.ts) — NOT game
                    # rule tables; those stay server-side
  assets/         # mechanicum-design-system.css, fonts
```

There is no separate `features/`, `api/`, or `hooks/` directory yet — those
belong to the aspirational layout, not the current tree. TanStack Query hooks
live in `lib/api.ts`; feature-scoped containers live in `components/`. Follow
the established pattern and flag (don't silently restructure) if a real
`features/` split starts to emerge: this section should be corrected to match
the actual layout rather than imposed from here.

## API Contract & Type Safety

**Confirmed: `openapi-typescript`, types only — no runtime client
generation.** Rationale: request-sending behavior (credentials, CSRF header,
error-normalizer) stays hand-written and auditable; only the *types* are
generated, so FE↔BE drift from hand-maintained interfaces is eliminated.

- Backend FastAPI app exposes its OpenAPI schema (`/openapi.json`) as usual
  — no extra work required there.
- Generation runs via the `generate:types` npm script — already wired in the
  root `package.json` to `openapi-typescript docs/api/openapi.json -o
  src/types/api.d.ts`. Run it manually or in CI when the backend schema
  changes — not on every dev save; a live schema URL can substitute for the
  static `openapi.json` path.
- The generated `src/types/api.d.ts` is a checked-in file produced by the
  `generate:types` script above. Regenerate and commit it when the backend
  schema changes, not on every dev save — and check the generated output
  once before wiring MSW handlers to it (see the near-duplicate warning
  below and `08-frontend-testing.md`).
- `api/` hooks (TanStack Query) import from the generated types for request
  and response shapes. Do not hand-write a parallel interface for a
  request/response body that already has a generated type.
- Do **not** introduce a full runtime client generator (e.g. `orval`
  generating the hooks themselves) at this stage — that's a second
  abstraction layer on top of TanStack Query and duplicates work already
  done by hand in `api/`. Revisit only if hand-writing hooks becomes actual
  duplication pain across many resources (same two-or-more-uses test as
  `01-architecture.md`).
- If the generated types and a hand-written hook's assumptions diverge
  (e.g. a field the FE expects isn't in the schema), that's a signal to
  fix the mismatch, not to widen the hook's types with an `any`/cast.
- **Check the generated output once, before wiring hooks to it.** FastAPI
  disambiguates same-named Pydantic models from different modules by their
  full module path, which can surface as multiple long, near-identical
  generated type names for what's conceptually one resource (this project
  currently has two distinct `UserResponse` schemas — one from the auth
  module (`/auth/me`, no `created_at`/`updated_at`) and one from the user
  module (adds `created_at`/`updated_at`) — near-identical otherwise). If the
  generated types file has near-duplicate types like this, raise it with
  whoever owns the backend schema (consolidate to one model) rather than
  picking one of the duplicates silently and hand-waving the other, since
  a future backend change could easily update only one of them.

## Error Handling Contract

Standardize on FastAPI's default error shapes rather than inventing a
custom envelope:

- Simple errors: `{"detail": "<message>"}`.
- Validation errors (422): `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`.

Frontend rule: all mutations pass their error through **one** shared
error-normalizing function (e.g. `normalizeApiError`), not a per-feature
`try/catch` pattern. That function maps status code to UI treatment:

| Status | Meaning | UI treatment |
| --- | --- | --- |
| 422 | Field-level validation failure | Map `loc` to the offending form field, show inline |
| 409 / domain-rule rejection | Backend rejected a valid-shaped request for a business reason (e.g. "prerequisite upgrade missing") | Inline message near the action, not a generic toast |
| 401 | Not authenticated | See "Auth & Session" below |
| 500 / network failure | Unexpected server/connection error | Generic toast, do not attempt to interpret `detail` as structured |

Do not build a bespoke error-handling pattern per feature — if the shared
function doesn't cover a new case, extend it and say so, rather than
working around it locally.

## Data Fetching Conventions

### Query defaults

Set `staleTime` and retry behavior once at the `QueryClient` level, not
per-query. Given the ~5–15 minute backend data refresh cadence, a
`staleTime` on that order (a few minutes) is a reasonable default;
`retry: 1–2` with default exponential backoff. Override per-query only
with a stated reason (e.g. a resource known to change far more or less
often than the norm).

**Prefer the real-time channel over polling where it covers the resource.**
`GET /api/v1/notifications/stream` (SSE) pushes colony, event,
development-plan, and colony-membership changes as they happen:

- Subscribe once (e.g. in a top-level provider); on a relevant notification,
  call `queryClient.invalidateQueries` for the affected query key — the same
  invalidate-and-refetch pattern used after mutations, now server-triggered
  instead of local.
- Don't also poll that resource with `refetchInterval` — redundant network
  traffic and a second source of "when does this update," fighting the
  stream instead of relying on it.
- `staleTime`/interval refetching stays the right default for anything the
  stream doesn't cover (config/reference data) — this narrows polling, it
  doesn't remove it everywhere.
- The stream needs the auth cookie like any other request (see "Auth &
  Session" below) — implement reconnection with backoff (the API documents
  that clients should auto-reconnect), and treat a dropped/reconnecting
  stream as a reason to one-off refetch affected queries, not a silent
  freshness gap.

### Loading vs. background refetch

Distinguish initial load from a background refetch of already-cached data:

- `isPending` → initial load, show a skeleton/loading state.
- `isFetching && !isPending` → background refetch, show a small unobtrusive
  indicator (if any) — never re-show a full skeleton over existing data.

This distinction should be a shared convention (e.g. a small shared hook or
UI pattern), not reinvented per component.

### Query key rules (race conditions / stale responses)

**Hard rule: a query key must include every parameter that affects the
response** — filters, pagination, colony ID, sort order, all of it. No
exceptions "because it's simple right now." Getting this wrong is how
stale responses silently overwrite newer state or unrelated views share a
cache entry they shouldn't. This is cheap to get right up front and
expensive to retrofit once cache collisions start producing what look like
random UI bugs.

### Mutations and cache updates

Per the existing rule: invalidate affected query keys on success rather
than manually patching cached data, unless a specific optimistic-update
need is identified and confirmed (see below).

### Optimistic updates

Default is **invalidate-and-refetch**, everywhere. Reserve optimistic
updates for a named exception, not a general technique to reach for:

- Good candidate: high-frequency, low-conflict-risk actions where perceived
  latency genuinely matters at the table (e.g. toggling an infrastructure
  item working/faulty).
- Bad candidate: anything destructive, anything where a rejected mutation
  would be confusing to visually roll back, or anything low-frequency
  enough that the round-trip latency doesn't matter.

Keep an explicit, short list of confirmed optimistic-update cases in this
file as they're agreed on — don't let "optimistic updates" become an
ambient default someone reaches for because it feels more polished.

### Pagination

**Open item — not yet needed.** Infrastructure/modifier lists per colony
are expected to be small (tens, not thousands, of rows), so full-fetch is
likely fine for now. Do not build `useInfiniteQuery`/cursor-pagination
scaffolding speculatively — this fails the "used in ≥2 places, real harm"
test from `01-architecture.md` today. Revisit if/when a specific list
screen's row count becomes an actual problem, and flag it explicitly when
that happens rather than silently picking a pagination strategy then.

## Forms & Validation

Domain validation (e.g. `Order`/`Complacency` can't go below 0,
conditional-required fields tied to Representative personality) lives in
the backend, per `02-domain.md`. The frontend does not reimplement
those rules in a client-side schema (Zod/Yup/etc.) — that would create the
same drift risk described in "API Contract & Type Safety," at the form
layer instead.

- Client-side validation is limited to **cheap, non-domain** checks:
  required-field-present, numeric format, string length/format.
- Domain-rule violations are surfaced from the backend's 422 response (see
  "Error Handling Contract") and rendered inline against the relevant
  field.
- Trades a slightly less instant validation UX for a single source of truth
  on business rules; if that UX gap becomes a real problem for a specific
  form, raise it explicitly rather than quietly duplicating the rule
  client-side.

## Auth & Session

**Confirmed: cookie-based authentication (HttpOnly cookies) only. Bearer
auth is being removed entirely, not gradually phased out.** Do not write
any FE code that reads, stores, or attaches a Bearer token — no
`Authorization: Bearer ...` header anywhere in the frontend, including in
one-off scripts, debug tooling, or Swagger-style manual testing helpers
committed to the repo.

**Backend follow-up — RESOLVED as of 2026-09-18 (do not re-flag without new
evidence).** The legacy Bearer surface is fully gone from the current source:
Bearer-only auth helpers were deleted from `adapters/api/middleware/auth.py`;
the OpenAPI schema (checked-in snapshot included) declares no `HTTPBearer`
scheme, guarded by a regression test in `tests/adapters/api/test_auth.py`;
and `/auth/login`/`/auth/refresh` set tokens exclusively as HttpOnly cookies,
never in the response body.

Standing rule: never reintroduce a Bearer token path in the backend (header or
body), and keep the `HTTPBearer`-absent OpenAPI test in place.

### Why cookie-based is the safer choice here

An HttpOnly cookie is never readable by JavaScript, so an XSS payload has no
token value to steal — unlike a Bearer token held anywhere JS can reach
(`localStorage`, `sessionStorage`, a JS variable), which is exfiltratable
the moment an XSS vector exists anywhere in the app. The trade-off cost is
explicit CSRF handling (below), a well-understood problem.

### Frontend rules

- **Never store tokens in FE-reachable storage.** No `localStorage`, no
  `sessionStorage`, no module-level JS variable holding an access or
  refresh token. The browser handles the cookie; the FE never touches the
  token value directly.
- **Never decode the JWT client-side.** Don't parse the access token's
  payload to read user info or roles "since it's right there" — with
  HttpOnly cookies the FE can't read it anyway, but the rule holds
  regardless: user/session info comes from `GET /api/v1/auth/me`, not from
  decoding a token. This also means the FE doesn't need to know or care
  about token internals (claims, expiry format) at all.
- **Every request includes credentials.** `fetch`/axios calls must set
  `credentials: 'include'` (fetch) or `withCredentials: true` (axios) —
  otherwise the browser won't attach the auth cookie even same-site.
- **Session is server state.** Current user (`/auth/me`) is a TanStack
  Query (e.g. `useSession()`), and is the confirmed second exception —
  alongside theme — to "no global state library," only if something
  outside TanStack Query is genuinely needed (e.g. a small "am I
  authenticated at all" flag read before the router decides what to
  render).
- **401 handling:** a shared response interceptor/wrapper (not per-feature
  try/catch) attempts exactly one silent call to `/api/v1/auth/refresh` on
  a 401, then retries the original request once. If refresh also fails,
  clear the session query and redirect to login.
- **Concurrent-401 refresh race — known pitfall, guard against it
  explicitly.** The backend rotates refresh tokens (old one invalidated
  when a new one issues). If several requests 401 at once (common when a
  page fires multiple queries on mount), each naively calling `/refresh`
  independently will race: the first refresh succeeds and rotates the
  token, the second refresh then fails because it's using an
  already-invalidated token. Fix: share a single in-flight refresh
  `Promise` across all concurrent 401s (a simple module-level mutex is
  enough) so only one refresh call is ever made per expiry, and all
  waiting requests retry once it resolves.
- **Logout** calls `/api/v1/auth/revoke` (or `/revoke-all` for "log out
  everywhere"), then invalidates the session query — don't just clear FE
  state and assume the server-side session is gone.

### CSRF — required because cookies auto-attach, and now implemented

Moving to cookies reintroduces CSRF, which Bearer-in-header doesn't have
(a forged cross-site request can't set a custom header, but it can trigger
a cookie-bearing request). The backend now exposes
`GET /api/v1/auth/csrf-token`, confirmed to implement the double-submit
pattern: it sets a non-HttpOnly, JS-readable cookie containing the CSRF
token. Frontend rule:

1. On session start (or before the first mutating request if no session
   exists yet), call `/auth/csrf-token` once so the CSRF cookie is set.
2. Read the CSRF cookie's value and echo it as an `X-CSRF-Token` header on
   every state-changing request (`POST`/`PUT`/`PATCH`/`DELETE`) — this
   should live in the same shared request layer that already attaches
   `credentials: 'include'`, not be added per-feature.
3. `SameSite=Lax` or `Strict`, `Secure`, `HttpOnly` on the actual
   session/refresh cookies, and explicit non-wildcard CORS with
   `allow_credentials=True` (per "Environment & Configuration" below),
   remain required alongside this — the CSRF token is one layer, not a
   replacement for the others.
4. If a mutating request 403s specifically due to a missing/invalid CSRF
   token (should be distinguishable from a plain 401), the shared error
   handler should re-fetch `/auth/csrf-token` once and retry, the same
   pattern as the 401-refresh flow — don't require every feature to
   reimplement this.

### Two separate role concepts — don't conflate them

The system role vs. colony role distinction is a domain concept, defined
once in `02-domain.md` — this
section doesn't restate the definitions, only the FE-specific
consequence: name the two distinctly in FE code (e.g. `systemRole` vs.
`colonyRole`) rather than a single ambiguous `role` variable that could be
either, and fetch each from where it actually lives (`User.role` from
`/auth/me` for system role; the relevant `ColonyUserRoleEnum` value from
colony-membership endpoints for colony role) rather than assuming one
implies the other.

**Known schema gap:** `User.role` is typed as a bare `string` in the
generated API types, not an enum — the backend enforces the hierarchy but
doesn't expose it as a typed enum in the OpenAPI schema. Generated types
won't give exhaustive-match safety here. The FE may declare a local
literal-union type mirroring the known values purely as a type-checking
aid (not a duplicated business rule — it doesn't decide anything, it just
names the values), but must still handle an unrecognized role value
defensively (e.g. treat as least-privileged) rather than assuming the
union is exhaustive. Worth raising with whoever owns the backend schema as
a fix (proper `Enum` on the Pydantic model) rather than permanently
working around it FE-side.

## Environment & Configuration

- API base URL is read from a Vite env var (`VITE_API_BASE_URL`), never
  hardcoded (e.g. no `localhost:8000` baked into `api/` modules).
- A `.env.example` is committed showing the expected variable(s).
- FastAPI CORS configuration explicitly allows the Vite dev origin; do not
  use `allow_origins=["*"]` even for local development, to avoid carrying
  that habit into a later deployment.

## State: server state vs. UI state

- **Server state** (anything that originates from the API — colony stats,
  Representatives, infrastructure, modifiers) lives in TanStack Query and
  nowhere else. Do not copy query data into `useState`/`useReducer` "for
  convenience" — that creates a second source of truth that can drift from
  what the backend actually holds.
- **UI-only state** (dialog open/closed, selected tab, form draft values
  before submit, local sort/filter of an already-fetched table) is local
  component state (`useState`/`useReducer`) or lifted to the nearest common
  parent. Don't reach for a global store for this.
- **Mutations** (installing an upgrade, entering a GM roll, adding a custom
  modifier) go through TanStack Query mutations, invalidating the affected
  query keys on success rather than manually patching cached data, unless a
  specific optimistic-update need is identified and confirmed (see "Data
  Fetching Conventions" above).
- No separate global state library (Redux/Zustand/Context-as-store) unless a
  concrete cross-cutting need emerges that server state + local state can't
  cover (e.g. active theme, current user session) — ask before introducing
  one. Theme selection and the current-user session are the two confirmed
  exceptions (see "Auth & Session" above).

## Styling

Two layers, used deliberately rather than interchangeably:

| Layer | Purpose | Example |
|---|---|---|
| Tailwind v4 | Layout, spacing, responsive utilities | `flex gap-4 p-6 rounded-lg` |
| Mechanicum design-system CSS | Theme variables, WH40k-styled components, fonts | `--mech-amber`, `.data-slate`, `.ornament-border` |

Rules:

- New theme-able values (colors, fonts, decorative treatments) are added to
  `assets/mechanicum-design-system.css` as CSS variables, not hardcoded
  Tailwind color classes or inline styles — otherwise the 7-theme swap
  breaks silently for that element.
- Per the confirmed UI direction: **Cult Mechanicus / data-slate ornamentation
  is confined to chrome (headers, borders, decorative framing) — data
  surfaces themselves (tables, stat values, numbers a GM needs to read
  quickly) stay accessibility-first and legible first.** If a component
  puts ornamental styling directly on a data-bearing element, that's a
  violation of this rule, not a style preference to negotiate per-component.
- No CSS-in-JS. This was a deliberate choice (zero runtime cost, SSR
  compatibility if ever needed) — don't introduce styled-components/
  emotion/vanilla-extract for a "one-off" component.

## Linting — oxlint

- `oxlint` is the linter of record; there is no ESLint config to keep in
  sync with it.
- Same principle as `05-style.md`'s stance on
  ruff/mypy: don't silently add or change lint rule configuration
  (`.oxlintrc.json` or equivalent) without confirmation — propose the
  change and wait.
- Don't add inline disable comments to suppress a rule without a comment
  explaining why (mirrors the backend's "comments explain why" rule in
  `05-style.md`).

## When to introduce an abstraction (React-specific application of `01-architecture.md`)

Before extracting a custom hook, a shared component, or a generic
"data table" component, apply the same test as the backend:

1. Is this used in at least two places right now?
2. Is the duplication it removes actually causing a maintenance problem?
3. Does it make the code easier or harder to follow for someone new to it?

Concretely: don't build a generic `<DataSlateTable>` abstracting over every
table in the app before there are at least two tables revealing what's
actually shared vs. incidentally similar. A `useColony(id)` query hook used
by two-plus components is fine; a hook wrapping a single one-off fetch
isn't earning its abstraction yet.

## Do not invent UI/UX behavior

If a screen's behavior isn't explicitly specified by the GM/Erebus (in a
shared spec, a prior conversation, or an existing reference screen), don't
guess a plausible-looking interaction, validation rule, or copy string —
this is the same principle as `02-domain.md`'s "do not invent
game rules," applied to the UI layer. Ask, or flag the gap explicitly,
rather than filling it in silently.

## What NOT to do

- Don't recompute derived stats, thresholds, or Profit Factor client-side —
  even for a "quick preview" before the API responds. If a perceived-latency
  problem justifies this later, it's a decision to make explicitly, not a
  default.
- Don't let a component both fetch its own data via TanStack Query *and*
  receive the same data as a prop from a parent that also fetched it —
  pick one owner per query.
- Don't hardcode theme colors as Tailwind utility classes (`bg-orange-500`)
  where a `--mech-*` variable already exists for that purpose.
- Don't hand-write TypeScript types for API request/response bodies that
  already have a generated type from the OpenAPI schema.
- Don't reimplement backend domain-validation rules in a client-side form
  schema — surface them from the 422 response instead.
- Don't build a query key that omits a parameter affecting the response,
  and don't reach for optimistic updates outside the confirmed exception
  list.
- Don't hardcode the API base URL or loosen CORS to `*`, even locally —
  doubly true now that cookies are in play, since browsers reject
  credentialed requests against a wildcard origin.
- Don't store an access or refresh token anywhere JS-reachable
  (`localStorage`, `sessionStorage`, a held JS variable) and don't decode
  a JWT client-side to read user info or roles — use `/auth/me`.
- Don't let more than one concurrent 401 trigger its own independent
  `/auth/refresh` call — share a single in-flight refresh promise.
- Don't conflate system role (`viewer`/`colony_manager`/`admin`) with
  colony membership role (`owner`/`editor`/`viewer`) — they answer
  different questions.
