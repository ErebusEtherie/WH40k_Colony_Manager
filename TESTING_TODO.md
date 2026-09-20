# Testing ToDo List

**Last Updated:** 2026-09-20
**Current Status:**

- Backend: 843 collected, 839 passed + 4 skipped (100% pass rate)
- Frontend: 87 tests passing, 0 skipped (11 test files)
- E2E (Playwright): 1 scenario (`e2e/not-logged-in.spec.ts`) — run on demand via `npm run test:e2e`, separate from `npm test`

This document tracks testing priorities and progress for the WH40k Colony Manager project.
It complements .clinerules/04-testing-strategy.md with specific implementation tasks.

---

## Current Test Coverage Summary

### ✅ Backend Tests (52+ files, 843 tests)

| Category | Files | Tests | Status |
|----------|-------|-------|--------|
| **Domain Models** | 10 files | 100+ | ✅ Complete |
| **Domain Rules** | 9 files | 80+ | ✅ Complete (includes Hypothesis) |
| **Application Services** | 8 files | 50+ | ✅ Complete |
| **Persistence Repositories** | 9 files | 60+ | ✅ Complete |
| **API Routers** | 14 files | 200+ | ✅ Complete |
| **Security** | 4 files | 40+ | ✅ Complete |
| **Integration** | 3 files | 26+ | ✅ Complete (Phase 3 added 6 permission tests) |
| **CLI/Config/IO** | 4 files | 30+ | ✅ Complete |
| **Total** | **52+ files** | **843 tests** | ✅ **100% passing** |

### Test Patterns in Use

#### Backend

1. **Hypothesis property-based testing** for domain rules (stat calculator, profit factor, size, state effects)
2. **pytest fixtures** for shared test data and mock repositories
3. **Example-based tests** for boundary conditions and specific scenarios
4. **Round-trip tests** for persistence (save → load → verify)
5. **API integration tests** using FastAPI TestClient with SQLite in-memory DB
6. **Permission/authorization tests** for role-based access control (Phase 3)
7. **Cross-feature workflow tests** using `auth_client` fixture (Phase 3)

---

## End-to-End (Playwright)

First scenario added 2026-09-20: `e2e/not-logged-in.spec.ts` — an anonymous
visitor entering the page sees the login screen (and a 401 from `/auth/me`),
never the dashboard.

The E2E suite runs **on demand** (or in CI for large changes), by design **not**
part of `npm test`. It targets the self-contained mock stack (`npm run dev:mock`,
`server.ts` on `:3000`); no Python backend, database, or seeded users needed.

```bash
npm run test:e2e            # run all specs (starts the mock server)
npm run test:e2e:install    # one-time Chromium install
npm run typecheck:e2e       # type-check specs without running them
```

---

## Phase 3 Implementation Summary (2026-09-01)

### Completed Tasks

#### 1. Permission/Authorization Tests (6 tests) ✅

**File:** `tests/integration/test_auth_flow.py::TestAuthorizationPermissions`

Tests added:

- `test_viewer_cannot_edit_colony` - Verifies VIEWER role cannot edit colonies
- `test_editor_can_edit_colony` - Verifies EDITOR role can edit colonies
- `test_admin_can_access_any_colony` - Verifies ADMIN bypass for colony access
- `test_user_cannot_access_unowned_colony` - Verifies non-members cannot access colonies
- `test_colony_manager_cannot_delete_users` - Verifies colony_manager cannot access admin endpoints
- `test_admin_can_delete_users` - Verifies ADMIN can access admin-only endpoints

**Key patterns:**

- Uses `integration_client` fixture with proper auth header management
- Tests both colony-level permissions (viewer/editor/owner) and global roles (admin/colony_manager/viewer)
- Verifies 403 responses with appropriate error messages

#### 2. Hypothesis Tests for Rule Engine ✅

**Files:** `tests/domain/rules/test_security_invariants.py`, `tests/domain/rules/test_state_effects_hypothesis.py`

Existing hypothesis tests cover:

- Stats never go negative regardless of modifier combinations
- Order == 0 always forces Profit Factor to 0 (Anarchy rule)
- Locked stats ignore positive modifiers
- Profit Factor never goes negative
- State effect properties (Orderly, Pious, Anarchy decay, etc.)

#### 3. Service Workflow Tests ✅

**File:** `tests/integration/test_cross_feature_workflows.py`

Existing workflow tests cover:

- Colony lifecycle with infrastructure, modifiers, and age advancement
- Representative assignment and stat changes
- Infrastructure state transitions (working/not_working)
- Modifier stacking from all sources
- Colony state transitions (Anarchy, Placated, etc.)
- Error handling and transaction rollback

### Test Count Summary

| Phase | Tests Added | Files Modified/Created |
|-------|-------------|------------------------|
| Phase 1 | ~777 | 52+ files |
| Phase 3 | 6 | 1 file (test_auth_flow.py) |
| **Total** | **843** | **52+ files** |

> Test count measured via `uv run pytest --collect-only -q` on 2026-09-20
> (843 collected nodes; includes parametrized tests). Category rows above are
> approximate — verified totals are in the table's Total row.

### Notes

- All tests pass (803 passed, 4 skipped)
- Permission tests use the existing `integration_client` fixture (not a new `auth_client` fixture) per architectural decision
- Hypothesis tests and workflow tests were already complete from Phase 1
- Phase 3 focused on filling the permission/authorization gap identified in the Phase 3 plan
