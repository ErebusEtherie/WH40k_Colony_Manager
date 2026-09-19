# Task State — EXAMPLE (completed)

> This is a completed example of `tasks/TEMPLATE.md`. For real work, copy
> the *template*, not this file, to `tasks/<YYYY-MM-DD>-<topic>/task.md`.
> Scenario, file paths, and commands are illustrative but modeled on this
> repo's conventions (uv + taskipy on the backend, `npm run lint:md` for
> docs); verify against the current tree before treating anything here as
> real.

## 0. Task Definition

**Request:** Add an endpoint that lists a colony's audit-log entries,
filterable by actor user id, newest entries first.

**In scope:**

- New read-only endpoint + use case + repository query
- Filter parameter (actor id) and ordering
- Tests for filter and ordering

**Out of scope:**

- Pagination (open item — the audit view is small for now)
- Writing/editing audit entries (recording already exists)

**References (docs first — check `docs/.manifest.yaml` for the right doc):**

- `docs/architecture.md` — layering (adapters → application → domain)
- `docs/api.md` — endpoint map and conventions
- `.clinerules/contexts/new-endpoint.md` — endpoint-adding checklist
- `.clinerules/02-domain.md` — no business logic in route handlers

## 1. Analysis

**Findings** (distinguish facts from assumptions):

- (fact) Repositories live in `src/colony_manager/adapters/persistence/`
  with `to_domain()`/`to_row()` mappers.
- (fact) Audit entries are append-only; no update path exists.
- (assumption) Filtering by actor belongs in the repository query, not a
  Python-side filter — confirm against the existing repository pattern
  before implementing.

## 2. Plan

Independently verifiable steps:

| Step | Target files | Status |
|------|--------------|--------|
| 1 | `application/` — use case for listing filtered entries | [x] |
| 2 | `adapters/persistence/` — repository query: actor filter, newest-first | [x] |
| 3 | `adapters/api/` — route + request/response schemas | [x] |
| 4 | `tests/` — use-case + repository + API tests | [x] |

## 3. Step Log

### Step 1: use case

**Changes:** `application/audit.py` → added
`list_audit_entries(colony_id, actor_id=None)`, raising a domain error for
an unknown colony.
**Verification:** `uv run task lint && uv run task typecheck` — clean.

### Step 2: repository query

**Changes:** `adapters/persistence/audit_repository.py` → added actor
filter and `ORDER BY created_at DESC`; mapped rows via `to_domain()`.
**Verification:** `uv run task test -k audit` — all pass.

### Step 3: API route

**Changes:** `adapters/api/` → `GET /api/v1/colonies/{colony_id}/audit`
with optional `actor_id` query param; response schema reused, not
redefined.
**Verification:** `uv run task test -k audit_api` — pass; checked the new
path in the OpenAPI schema.

### Step 4: tests

**Changes:** `tests/` → filter returns only matching actor; ordering is
newest-first; unknown colony 404s.
**Verification:** `uv run task quality` — lint, typecheck, and full suite
pass.

## 4. Review

**Result:** Steps 1–4 done; diff inspected; full `uv run task quality`
green.
**Open items / follow-ups:**

- Pagination for the audit view (revisit when row count is a real problem).
- Frontend consumption is a separate task — this change is API-only.
