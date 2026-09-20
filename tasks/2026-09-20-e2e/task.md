# Task State — E2E (Playwright) suite

> State file for the Playwright E2E effort, per `tasks/TEMPLATE.md`. Created
> once the suite grew to multiple scenarios (auth setup + anonymous +
> logged-in). Anyone resuming can read this file instead of re-exploring.

## 0. Task Definition

**Request:** Add Playwright E2E testing to WH40k Colony Manager, wired to run
on demand (not part of the default test flow), with type-checking and docs
for the specs. Later pass ("resolve open items"): add a logged-in dashboard
scenario backed by a storage-state auth flow, and create this state file.

**In scope:**

- `playwright.config.ts` — hermetic mock-stack target + three projects
  (setup / authenticated / anonymous)
- `package.json` — `test:e2e*` scripts, `typecheck:e2e`
- `tsconfig.e2e.json` — isolate E2E type-checking from the base check
- `e2e/auth.setup.ts`, `e2e/not-logged-in.spec.ts`, `e2e/dashboard.spec.ts`
- README.md / TESTING_TODO.md — on-demand E2E docs + mock-port correction
- `tasks/2026-09-20-e2e/task.md` — this file

**Out of scope:**

- Running E2E in CI/default `npm test`/`lint`/`typecheck` (deliberately
  on-demand)
- More scenarios (navigation, mutations, logout) — future work
- Real-backend E2E, network auth (SSE, refresh-race) — E2E targets the mock

## 1. Analysis

**Findings** (distinguish facts from assumptions):

- (fact) `npm run dev` = `tsx server.ts`: an Express server on :3000 serving
  both the Vite SPA and a cookie-authenticated mock of the FastAPI backend
  (`/api/v1/*`), mirroring the real backend's auth/CSRF behavior.
- (fact) Mock auth is cookie-based: `POST /auth/login` sets
  `rt_access_token`/`rt_refresh_token` (HttpOnly, SameSite=Lax) and, via the
  FE's `loginApi`, also fetches `csrf-token` (HttpOnly). Login is CSRF-exempt.
- (fact) `e2e/.auth/` is gitignored; `vitest.config.ts` already excludes
  `e2e/**` from the unit run.
- (fact) Dashboard selectors are stable: `#header-logout-button`,
  `#nav-tab-overview`, and the identity chip renders `userName`/role label.
- (assumption) Playwright's storageState snapshots HttpOnly cookies, so a
  real login in `auth.setup.ts` is sufficient — no manual cookie seeding.

## 2. Plan

| Step | Target files | Status |
|------|--------------|--------|
| 1 | `playwright.config.ts` + `package.json` (test:e2e scripts) | [x] |
| 2 | `e2e/not-logged-in.spec.ts` (anonymous scenario) | [x] |
| 3 | `tsconfig.e2e.json` + `typecheck:e2e` + README/TESTING_TODO docs | [x] |
| 4 | `e2e/auth.setup.ts` + storage-state project split in config | [x] |
| 5 | `e2e/dashboard.spec.ts` (logged-in scenario) | [x] |
| 6 | `tasks/2026-09-20-e2e/task.md` (this file) | [x] |

## 3. Step Log

### Step 1: config + scripts

**Changes:** `playwright.config.ts` → mock-stack target with
`webServer` (dev on :3000, forced `VITE_API_BASE_URL`); `package.json` →
`test:e2e`, `test:e2e:headed`, `test:e2e:install`.
**Verification:** `npx playwright test` — ran (server boot included).

### Step 2: anonymous scenario

**Changes:** `e2e/not-logged-in.spec.ts` → fresh-context visitor sees the
login screen; `/auth/me` must 401.
**Verification:** passing in the suite run.

### Step 3: type-check + docs

**Changes:** `tsconfig.e2e.json` (extends base, covers only `e2e/**` +
`playwright.config.ts`, `noEmit`); `package.json` → `typecheck:e2e`;
README.md → E2E section + mock-port fix (`:8001` → same `:3000` origin,
verified `server.ts:122` binds `PORT = 3000`); TESTING_TODO.md → E2E status +
"on-demand by design" note.
**Verification:** `tsc -p tsconfig.e2e.json` and `npm run typecheck` exit 0;
`oxlint e2e playwright.config.ts tsconfig.e2e.json` clean; `markdownlint-cli2`
on both docs clean.

### Step 4: auth setup + project split

**Changes:** `playwright.config.ts` → export `STORAGE_STATE`
(`e2e/.auth/user.json`) and split into `setup` (runs `auth.setup.ts`),
`chromium-authenticated` (matches `dashboard.spec.ts`, rehydrates snapshot,
depends on setup), `chromium-anonymous` (matches `not-logged-in.spec.ts`,
fresh context); `e2e/auth.setup.ts` → logs in as `LordCaptain` via the real
form, waits for `#header-logout-button`, snapshots storage state.
**Verification:** covered by step 5's full run (setup must pass first).

### Step 5: logged-in scenario

**Changes:** `e2e/dashboard.spec.ts` → with a rehydrated session: `/auth/me`
returns 200, app shell renders, login screen is absent, `LordCaptain` /
`LORD CAPTAIN` identity is shown, Overview has loaded seed colony data.
**Verification:** full `npx playwright test` below.

### Step 6: state file

**Changes:** this `task.md`.
**Verification:** `npm run lint:md` clean.

## 4. Review

**Result:** Full suite `npx playwright test` passes (setup + anonymous +
logged-in); `npm run typecheck:e2e` and `npm run typecheck` exit 0; oxlint and
markdownlint clean; `git status` shows only intended files.
**Open items / follow-ups:**

- More E2E scenarios: nav-tab interaction, a mutation flow (needs the CSRF
  token path), and logout (returns to login screen).
- Revisit auto-running E2E in CI for large changes — currently on-demand only.
- Document any new mock auth behavior changes here before altering specs.
