---
name: review-team
description: Use when the user asks for a code review by a fleet of specialized reviewer agents, wants multiple independent reviewer perspectives, or asks to run reviewers in single-pass or iterative fix-until-clean mode. Launches focused subagents for correctness, security, architecture, conventions, simplicity, UX, reliability, telemetry, testing, compatibility, and documentation review.
---

# Review Team

Run a fleet of specialized reviewer subagents against the same change. Each reviewer is intentionally unaware of the others and must stay within its assigned focus area.

Reviewer prompts live alongside this file. Read only the reviewer files you plan to launch.

## Modes

- **single**: Default. Launch reviewers once, aggregate findings, deduplicate, and report the final review.
- **iterate**: Launch reviewers, fix accepted findings, rerun relevant reviewers, and repeat until the review is clean or the remaining findings are intentionally deferred.

If the user does not specify a mode, use **single**. Use **iterate** only when the user explicitly asks to keep fixing, make reviewers happy, or run until clean.

## Reviewer Loading Protocol

Read reviewers at launch time only — never pre-load the whole set.

1. Read this SKILL.md.
2. Pick the reviewers that match the change:
   - Backend logic → correctness, security-abuse, architecture (add testing-strategy if tests changed)
   - Frontend → correctness, product-ux-accessibility, architecture
   - API changes → api-compatibility, architecture, security-abuse
   - Config/infrastructure → security-abuse, architecture, telemetry-observability
3. Read only the reviewer files you plan to launch (the files below live in
   this directory next to SKILL.md — there is no `reviewers/` subdirectory).
4. Cap at 5 reviewers per review. If more than 5 are relevant, launch the
   highest-risk ones and note the ones skipped.

For an unspecified request, use the default set: correctness,
security-abuse, architecture. Launch specialist reviewers only when the
change touches their area. "Full team" means the default set plus every
specialist relevant to this change — still subject to the 5-reviewer cap.

## Reviewer Set

Core (default):

- `correctness-reviewer.md`
- `security-abuse-reviewer.md`
- `architecture-reviewer.md`

Specialist (on-demand):

- `code-quality-conventions-reviewer.md`
- `simplicity-scope-reviewer.md`
- `product-ux-accessibility-reviewer.md`
- `performance-reliability-reviewer.md`
- `telemetry-observability-reviewer.md`
- `testing-strategy-reviewer.md`
- `api-compatibility-reviewer.md`
- `documentation-dx-reviewer.md`

## Launch Pattern

For each reviewer subagent, provide:

1. The exact reviewer prompt from its Markdown file.
2. The task description, PR/issue context, or user request.
3. The diff or changed files to review.
4. Any test results, logs, screenshots, or relevant repository context.

Add this wrapper to every reviewer prompt:

```text
You are one reviewer in a fleet of independent code review agents. You cannot see the other reviewers. Stay strictly within your assigned role. Return only concrete, actionable findings with file and line references. If you find no issues in your area, say so clearly. Do not provide general commentary, praise, summaries, or duplicate concerns outside your mandate.
```

Prefer running independent reviewers in parallel. Do not ask multiple reviewers to solve the same broad task in the same way; their reviewer prompt is their boundary.

## Aggregation

After reviewers finish:

1. Merge duplicate findings.
2. Drop findings that lack a concrete failure mode, user impact, security risk, or maintenance cost.
3. Resolve conflicts using the codebase, tests, and stated requirements as evidence.
4. Rank findings by severity and practical importance.
5. Present findings first, with file and line references.

The final review should not expose raw reviewer transcripts unless the user asks for them.

## Iterate Mode

In **iterate** mode:

1. Run the initial reviewer set.
2. Decide which findings are valid and should be fixed.
3. Implement fixes directly.
4. Run tests or checks appropriate to the changes.
5. Rerun only the reviewers relevant to the changed areas or unresolved findings.
6. Continue until no actionable findings remain, or until any remaining findings are explicitly documented as out of scope, false positives, or accepted tradeoffs.

Keep the user informed between iterations. Do not loop indefinitely; stop when additional iterations are not producing material new findings.

## Final Response

For **single** mode, return the aggregated review.

For **iterate** mode, return:

- What was fixed.
- What verification ran.
- Which reviewers were rerun.
- Any remaining findings or accepted tradeoffs.
