---
name: review-transform
description: Lightweight code review of a transform.py for shared utility usage, code quality, pipeline standards, and optimization. Does not run validation or check data.
argument-hint: "[main_topic] [sub_topic] [topic]"
allowed-tools: ["Read", "Glob", "Grep"]
---

# Review Transform Code Quality

A focused code review of `transform.py` that checks shared utility usage, code quality patterns, pipeline standards, and optimization. This is a **read-only** skill — it does not run any scripts, create files, or modify code.

Use this skill:
- After fixing issues identified by `/data-review-claude`
- As a standalone code-quality pass on an existing transform
- When you want code feedback without re-running the transform

For data accuracy checks, use `/data-review-claude`. To re-run validation,
use `uv run python scripts/validate_topic.py {main} {topic}`.

## Input

Arguments: `$ARGUMENTS` (format: `[main_topic] [sub_topic] [topic]`)

**Derived paths:**
- Transform: `src/etl/$0/$1/$2/transform.py`
- Domain conventions: `src/etl/$0/CLAUDE.md`

## Step 1: Read Context

Read:
1. `src/etl/$0/$1/$2/transform.py` — halt if missing
2. `src/etl/$0/CLAUDE.md` — domain conventions
3. `.claude/skills/data-cleaning-standards/SKILL.md` — cleaning standards
4. `.claude/skills/data-cleaning-standards/code-review-checklist.md` — the canonical code-review checklist

## Step 2: Review Checklist

Review `transform.py` against every check in `.claude/skills/data-cleaning-standards/code-review-checklist.md`. Record **PASS / FAIL / N/A** for each. The checklist covers Shared Utilities, Code Quality, Pipeline Standards, and Optimization — plus scope notes describing when a check is legitimately N/A.

The checklist is shared with `/transform-topic`'s post-authoring self-review, so a transform that passed authoring must pass this skill. Do not fork or paraphrase the checks here — if something seems missing, update the shared checklist file instead.

## Step 3: Output Report

Print a structured report:

```
=== CODE REVIEW: $2 ===

--- Shared Utilities ---
[For each check: PASS / FAIL / N/A with brief note]

--- Code Quality ---
[For each check: PASS / FAIL / N/A with brief note]

--- Pipeline Standards ---
[For each check: PASS / FAIL / N/A with brief note]

--- Optimization ---
[For each check: PASS / FAIL / N/A with brief note]
[For FAIL items: specific line numbers and suggested fix]

--- Summary ---
{X} passed, {Y} failed, {Z} N/A
{If any FAIL: prioritized list of issues to fix}
```

## Important Rules

- **Read-only** — do not create, edit, or run any files.
- For FAIL items, include the specific line number(s) and a concrete suggested fix.
- Focus on patterns that affect correctness or performance, not style preferences.
