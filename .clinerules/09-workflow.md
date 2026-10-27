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
| Standard | Optional (use for complex/ambiguous/risky) | Required (via implement-phase) | Only if medium+/architectural/public API/multi-module | No |
| Security Sensitive | Required (risky mode) | Required (via implement-phase) | Required | Required |

`code-reviewer` runs for implemented changes inside the implement-phase
workflow (steps 7 and 10) — this column is where that gate shows up in the
per-change-type matrix.

## Skill Invocation

Base rules (00–11) are always active and cover the majority of tasks on
their own. Invoke a skill only when its trigger applies — a skill is a
loaded enhancement, not ambient ceremony:

| Skill | Invoke when |
| --- | --- |
| `code-reviewer` | Self-review of changed code is wanted (also wired into the implement-phase workflow) |
| `codex-grade-coding` | Task is complex, ambiguous, risky, or benefits from explicit task classification — optional for Standard, required (risky mode) for Security Sensitive |
| `review-team` | A formal multi-perspective review is requested, or the change is medium+/architectural/public API/multi-module |
| `security-first` | Change touches auth, authorization, secrets, untrusted input, config/infrastructure, or sensitive data |
| `frontend-design` | UI/UX work requiring design-system-driven, non-generic interface work |
| `find-skills` | Discovery/installation of agent skills — user asks "is there a skill for X"/"can you do X" or wants capabilities extended (skills.sh / `npx skills`); installing still requires explicit approval |
| `mermaid-diagrams` | Creating any Mermaid diagram (flowchart, sequence, class, state, ER, Gantt) in markdown/doc output |
| `architecture-diagramming` | System architecture diagrams — components, layers, subgraph boundaries, data flows (Mermaid flowcharts) |
| `markdown-formatting` | PR descriptions, issue bodies, documentation, notes, or saved/published artifacts needing consistent Markdown conventions and templates |
| `requirement-elicitation` | Gathering/defining project requirements ("help me define requirements", "figure out what to build") — writes `requirements-<project>.md` to the working directory (aim at `docs/` here) |
| `issue-decomposition` | Breaking a feature/project description into GitHub-style work items (INVEST issues with story-point estimates) — always preview before creating |
| `repairing-project-setup` | Agent-setup drift/repair — audit against this repo's actual scheme (`.clinerules/`, `docs/`); the skill targets `CLAUDE.md`/`AGENTS.md`, which this repo does not use, so project rules win |
| `dependency-mapping` | Mapping task/issue dependencies — "what blocks what", blocking chains, critical path (Mermaid flowcharts; reads `gh`-accessible issues) |
| `estimating-work-items` | Sizing/pointing a work item — powers-of-two 1/2/4/8 for issues, epics = exact sum of children (no rounding) |
| `timeline-planning` | Project timeline / sprint plan / Gantt chart — converts estimates + dependencies into a Mermaid gantt |

**Skill provenance / refresh caveat.** Project skill copies are snapshots. `issue-decomposition`,
`estimating-work-items`, and `timeline-planning` ship *enabled* in this project's copies while their
global sources (`C:\Users\lukas\.agents\skills\`) carry `disabled: true`. A future refresh that
re-copies from the global store would silently re-disable them — re-apply this project's enable
decision after any refresh rather than letting the re-copy reset it.

Before starting any non-trivial task, check the enabled-skill list
(surfaced through the `skills` tool — `11-tools.md`) and match skills to
the actual task by their names and descriptions before assuming the base
rules alone apply. When a skill's trigger applies, activate and follow it
through Cline's skill mechanism; combine skills whose responsibilities
complement each other (e.g. an implementation skill plus `code-reviewer`),
and follow each activated skill while respecting the user's explicit
requirements, project rules, and security constraints — skills never
override project rules (see "Rule Priority" above). Never claim to have
used a skill unless it was actually activated and its instructions were
available. Keep loading to the skill's own SKILL.md (see the loading rule
below); do not invoke irrelevant skills.

Do not invoke skills for trivial tasks (typo fixes, import corrections,
documentation tweaks, isolated simple fixes) — the base rules cover those
with the short path. When a skill is invoked, load only its SKILL.md; for
`review-team`, read only the reviewers actually being launched (see that
skill's Reviewer Loading Protocol), never the whole set.

For Security Sensitive changes, invoke `security-first` before
implementation so trust boundaries and attack surface are framed before
code is written, not as a post-hoc check.

## Skill Discovery

When a task would benefit materially from a capability no enabled skill
covers:

- Search for an existing skill before deciding to create one. Check the
  enabled-skill list first, then trusted sources — the official skill
  registry (https://skills.sh/) and relevant GitHub repositories — using
  web search when available (`ddg-search` + web fetch, `11-tools.md`).
- Search by the task's domain and the intended capability, not only by a
  technology name (e.g. "rule-table review" rather than just "pandas").
- If a dedicated discovery skill (e.g. `find-skills`) appears in the
  enabled-skill list, prefer it for this step.
- Evaluate candidates for relevance, maintenance, Cline compatibility,
  dependencies, required permissions, bundled scripts, and security risk.
  Read the candidate's SKILL.md and any scripts before recommending it.
- Present the best candidate(s), explain why they fit, and provide
  installation instructions. Ask for explicit approval before installing a
  skill, enabling it, executing its scripts, or modifying global agent
  configuration.
- If search tools are unavailable, explain the limitation and suggest a
  practical alternative; do not pretend a search was performed.

Searching for a skill does not authorize installing it, and installing a
skill does not authorize running arbitrary scripts or commands bundled
with it. Do not disable, replace, or remove existing skills without
approval. Prefer the smallest useful change — do not install a whole skill
collection when a single skill suffices.

Keep selection efficient: for trivial tasks proceed directly unless a
clearly relevant skill is already enabled; for complex, unfamiliar, or
specialized tasks make a deliberate skill-selection decision. Do not
search externally when an enabled skill already covers the task, and do
not search repeatedly within the same task unless the current selection
proves inadequate.

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
2. codex-grade-coding only if the change is complex, ambiguous, or risky (optional otherwise)
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
