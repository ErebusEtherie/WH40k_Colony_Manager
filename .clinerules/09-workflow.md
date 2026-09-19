# Task Execution Workflow

## Rule Priority

1. User request
2. Project rule files
3. Project configuration files
4. Installed skills
5. General model knowledge

Skills must never override project rules. If conflict detected: follow
project rules, report conflict.

## Change Classification

**Small Bugfix**: typo fixes, documentation fixes, import corrections,
missing types, linting fixes, isolated straightforward fixes.

**Standard Change**: new features, behavior changes, API modifications,
database changes, approved refactorings, multi-module changes.

**Security Sensitive**: auth, authorization, JWT, cookies, CSRF,
permissions, roles, ownership transfer, audit logging, session management.

When uncertain between Small Bugfix and Standard: treat as Standard.

## Required Skills

| Change Type | codex-grade-coding | code-reviewer | review-team | security-first |
|-------------|-------------------|--------------|-------------|----------------|
| Small Bugfix | Optional | Optional (short path) | No | Only if security-related |
| Standard | Required (up-front gate) | Required (via implement-phase) | Only if medium+/architectural/public API/multi-module | No |
| Security Sensitive | Required (risky mode) | Required (via implement-phase) | Required | Required |

`code-reviewer` runs for implemented changes inside the implement-phase
workflow (steps 7 and 10) — this column is where that gate shows up in the
per-change-type matrix.

## Invocation Defaults

**Security Sensitive (Option A - full pipeline)**:

1. Inspect existing code
2. codex-grade-coding (risky): surface assumptions, minimize change surface
3. Implement
4. Run validation tools
5. review-team
6. security-first
7. Report with evidence boundaries

**Standard (Option B - lean gate)**:

1. Inspect existing code
2. codex-grade-coding (standard): smallest correct change
3. Implement
4. Run validation tools
5. Report concisely
6. review-team only if triggers apply

**Small Bugfix**: Short path, codex optional.

## Existing Code First

Before creating new files, search for similar functionality. Prefer
extending existing code over parallel implementations. Creating a new file
is not automatically preferable to modifying an existing one.

## Respect Existing Patterns

When multiple valid implementations exist, prefer the pattern already
used. Consistency > theoretical perfection. Don't replace patterns simply
because another approach is cleaner.

## Minimal Scope

Modify only what was explicitly requested. Examples of NOT doing:

- Adding a feature doesn't justify refactoring nearby code
- Fixing a bug doesn't justify renaming unrelated classes
- Adding a test doesn't justify restructuring the test suite

## Report, Don't Fix

When discovering additional problems (duplication, inconsistent naming,
missing tests, technical debt): report them, explain impact, do not fix
unless explicitly requested. Skill findings are not automatically
authorized.

## No Opportunistic Refactoring

Refactoring requires explicit approval. Suggestions encouraged;
implementation requires approval.

## No Architectural Migrations

Do not introduce new architectural styles, frameworks, DI systems,
state-management approaches, plugin architectures, or generic abstraction
layers without explicit approval.

## One Concept, One Implementation

Avoid parallel implementations. Prefer single implementation of a
concept: one domain model, one repository, one source of truth, one query
hook.

## Tool Configuration Is Authoritative

If documentation and configuration disagree: report inconsistency, follow
actual configuration, do not silently change either.

## Dependency Approval

Do not introduce new dependencies without approval. Before proposing:
explain problem, why current dependencies are insufficient, alternatives
considered. Default preference: avoid adding dependencies.

## Evidence Boundaries

Distinguish between:

- Verified facts
- Reasonable inferences
- Unknown information

Do not present assumptions as verified facts. Explicitly state what was
not verified.

"Resolved"/"verified" markers in rules and docs are claims, not facts.
Spot-check them cheaply when you pass through, and report drift rather
than silently believing or silently fixing it.

## Task State Markers

For long or multi-session work, keep a lightweight task-state file under
`tasks/` (see `tasks/TEMPLATE.md`): task definition, plan with checkboxes,
and per-step verification, at `tasks/<YYYY-MM-DD>-<topic>/task.md` (a
completed example lives in `tasks/examples/`). Optional — use for multi-step
work where losing context is expensive, not for small fixes.

## Task Resumption

When resuming a task:

1. Find its task file under `tasks/`; when only the topic is known,
   newest-first match wins.
2. Read the task file (definition, plan table, step log) instead of
   re-exploring the repo.
3. Verify which steps are marked done `[x]` versus open `[ ]`.
4. Continue from the next uncompleted step — and re-confirm the last
   completed step still holds, since state may have drifted since it was
   written.
5. Do not re-plan from scratch unless the task file is missing, the plan no
   longer matches reality, or the user asks.

## Definition of Done

**Backend**:

- Requested change implemented
- Ruff passes
- Mypy passes
- Relevant tests pass
- No unrelated changes introduced

**Frontend**:

- Requested change implemented
- Oxlint passes
- TypeScript checks pass
- Relevant tests pass
- No unrelated changes introduced

**Reporting** (all change types):

- Final summaries note any docs/rule files that should change but were out
  of scope, with `file:line` anchors so the follow-up is actionable in one
  pass.
