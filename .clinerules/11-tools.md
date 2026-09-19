# Tool Use Priority

When several tools can get the same result, use the purpose-built one — it
is faster, cheaper on context, and behaves consistently. Shell commands via
`run_commands` are for what the dedicated tools do not cover, not a
fallback that re-implements them. (Precedent: the archived
`docs/archive/old_rules.clinerules/00-overview.md` tool-use section
established the same principle.)

## Tool ladder (highest first)

| Intent | Prefer | Instead of |
| --- | --- | --- |
| Read known-path files (batch several in one call) | `read_files` | shell cat/Get-Content |
| Search the codebase (regex, parallel) | `search_codebase` | grep/Select-String across the tree |
| Directory listing / tree / file metadata | `filesystem` MCP | shell ls/Get-ChildItem |
| File edits / creation | `editor` | shell redirection |
| Git status / diff / log / branches | `git` MCP | shell git |
| Structured multi-step analysis | `sequential-thinking` | reasoning buried in a long reply |
| Library/framework documentation (semantic) | context7 (resolve → query) | guessing API shapes from memory |
| External knowledge / current information | `ddg-search` + web fetch | inventing facts |
| Skill execution | `skills` | hand-reimplementing a skill's flow inline |
| Genuine execution: builds, tests, linters, installs, exploring an unknown tree | `run_commands` | — this is its purpose, see below |

`run_commands` remains the right tool for anything the others cannot do:
running builds/tests/linters, booting servers, one-off scripting, and
listing an unknown directory tree to learn its shape. The rule is "don't
shell out to reproduce what a purpose-built tool already gives you", not
"never shell".

## Knowledge-retrieval decision

1. Specific file known → read it directly (`read_files`, batching several).
2. Topic search → `search_codebase` for repo code; context7 for library
   behavior; `docs/.manifest.yaml` + targeted reads for repo knowledge.
3. Current state / recent changes → `git` (status, log, diff).
4. External knowledge / current events → `ddg-search` (then fetch content).

How much to read once the source is known (manifest → summary → section,
never whole docs up front) is `10-context-budget.md`; this file decides
which tool fetches. Audit/investigation narrowing lives in
`contexts/investigation-audit.md`.
