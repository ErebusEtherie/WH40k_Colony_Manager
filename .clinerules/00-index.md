# Rule Set Index

Quick routing for "which `.clinerules/` file do I need right now?" The
numbered files below form one binding rule set (they are not alternatives);
`contexts/`, `workflows/`, and `skills/` layer additional detail on top for
specific situations. The index loads right after `00-core.md` in filename
order — keep it lean: every file adds to the always-loaded token budget
(`10-context-budget.md` and `00-core.md`'s Context Contract).

## Numbered rules — which one when

| File | Covers | Reach for |
| --- | --- | --- |
| `00-core.md` | Scope, planning, execution, stop conditions, context contract | Anchor for every task; completion contract |
| `01-architecture.md` | Dependency direction, API boundary, abstraction test | Architecture, layering, where logic lives |
| `02-domain.md` | Domain vs API vs persistence models, rule tables | Domain/model work, game-rule decisions |
| `03-persistence.md` | Repository vs Importer/Exporter, schema mapping | Storage, migrations, import/export |
| `04-testing.md` | Risk-based test priority, anti-abstraction fixtures | Any test writing/planning |
| `05-style.md` | Type hints, strict mypy, ruff, docstrings, naming | Any backend code change |
| `06-collaboration.md` | Ask-don't-guess, conflict handling, ambiguity | Requirements that are unclear or conflicting |
| `07-frontend-architecture.md` | FE stack, API contract, auth/CSRF/SSE, styling, state | Any frontend work |
| `08-frontend-testing.md` | RTL/MSW/E2E priorities | Any frontend test work |
| `09-workflow.md` | Change classification, required skills, resumption | Before starting: which gates apply to this change |
| `10-context-budget.md` | Token economy, retrieval strategy | Long/context-heavy or investigative tasks |
| `11-tools.md` | Tool priority: which read/search/fetch tool to use | Deciding how to fetch or inspect something |

## Situational rules — layered on top

| Where | Covers |
| --- | --- |
| `contexts/new-endpoint.md` | Adding an API endpoint |
| `contexts/database-migration.md` | Schema migrations |
| `contexts/investigation-audit.md` | Audits, drift checks, investigation |
| `workflows/implement-phase.md` | Multi-step implementation workflow |
| `skills/` | Installed skills — `00-core.md` + `09-workflow.md` decide which apply |

## Not in `.clinerules/`

- Game rules and implemented-system knowledge: `docs/`, routed via
  `docs/.manifest.yaml` (never read a doc blind — see `10-context-budget.md`).
- Per-screen UI specs: `docs/UI_REQ/SUMMARY.md`.
- Source code is inspected on demand, in targeted slices only
  (`10-context-budget.md`).
