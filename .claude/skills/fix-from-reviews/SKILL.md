---
name: fix-from-reviews
description: Apply fixes from data-review-claude.md and data-review-codex.md to transform.py, re-run the transform (which re-validates), and verify each fix landed in gold. Supports --no-prompt for batch runs (judgment items deferred, never asked).
argument-hint: "[main_topic] [sub_topic] [topic] [--no-prompt]"
allowed-tools: ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]
---

# Fix From Reviews

Consolidates the `Required Fixes` sections from `data-review-claude.md` and
`data-review-codex.md`, applies the mechanical fixes to `transform.py`,
re-runs the transform (which re-validates as its last step), and verifies
each fix landed in the regenerated gold. Verification is part of this skill —
there is no separate verify step.

## Arguments

`$ARGUMENTS` format: `[main_topic] [sub_topic] [topic] [--no-prompt]`

- `--no-prompt` — batch mode: NEEDS_JUDGMENT fixes are **deferred and
  reported**, never asked. Required when this skill runs inside a sub-agent
  (prompts would be swallowed).

**Derived paths:**
- Reviews: `src/etl/$0/$1/$2/data-review-{claude,codex}.md`
- Transform: `src/etl/$0/$1/$2/transform.py`
- Gold: `data/gold/$0/$2/`

## Step 1: Prerequisites

1. At least one review report exists (halt otherwise — run the reviews first).
2. `transform.py` exists and gold contains parquet.
3. `git status --porcelain src/etl/$0/$1/$2/transform.py` is clean — if not,
   warn that applied fixes will mix with in-progress edits (in `--no-prompt`
   mode: proceed and note it in the summary; interactively: ask).

## Step 2: Parse and Consolidate

From each report's `## Required Fixes`, extract every `### Fix N:` with its
five bold fields (Severity / Issue / Evidence / Location / Suggested fix) and
its source. **Deduplicate across reports** on `(evidence + location)` — not
title — merging sources and keeping the clearer evidence. Sort: severity
(HIGH→LOW), then location (group related edits).

If neither report has Required Fixes: skip to Step 5 (re-run validation only).

## Step 3: Classify

- **AUTO** — mechanical, evidence specifies exactly what changes, confined to
  this topic's own `transform.py` (or its own `__init__`/local helpers):
  add a missing map entry, divide by 100, sentinel→NULL, missing rename,
  `strict=False`, zero-pad an ID, add a `_null_*` mask the contract already
  range-guards, author a missing `quality_checks` entry the review specified
  verbatim.
- **NEEDS_JUDGMENT** — interpretation, schema redesign (add/remove/retype
  column, change grain), report disagreement, ambiguous evidence,
  "investigate why X", or **any edit touching a file outside this topic**
  (shared utils, dimension builds, another topic) — those are applied once,
  centrally, by the user.
- **SKIP** — stale references, evidence too vague to act on.

## Step 4: Apply

Print the plan (AUTO / NEEDS_JUDGMENT / SKIP with one-line reasons), then:

- **AUTO**: locate code **by content** (never line numbers), Edit, log
  `APPLIED [Fix N]`. Edit failure ("not found"/"multiple matches") → demote
  to NEEDS_JUDGMENT, never force.
- **NEEDS_JUDGMENT**: interactively — show the fix and ask; with
  `--no-prompt` — record it as a **deferred judgment item** (title, severity,
  evidence, recommendation) for the final summary and move on.
- **SKIP**: record the reason.

## Step 5: Re-run Transform (re-validates automatically)

```bash
uv run python -m src.etl.$0.$1.$2.transform
```

The transform ends with `run_topic_validation(GOLD_DIR)`, so exit 0 means the
regenerated gold passed the full check suite. If it **fails**: print the
error and the applied-edit list, suggest `git diff` / `git checkout` of the
transform, and halt — in `--no-prompt` mode, revert the edits
(`git checkout -- src/etl/$0/$1/$2/transform.py`), mark every attempted AUTO
fix as a deferred judgment item ("auto-fix broke the transform; reverted"),
and continue to the summary.

## Step 6: Verify Each Fix

For every applied fix, design ONE targeted check against the regenerated
gold/manifest proving the specific flagged condition is resolved — use the
fix's own evidence (entity, year, column, value). Patterns:

- unmapped value → manifest `categorical_mappings[col].unmapped_count == 0`
  and the value now in `map_used`
- scale fix → the flagged column's max/median now in range *for the flagged
  year* (query gold, not just the manifest)
- sentinel/suppression → zero rows with the flagged marker
- value mismatch → re-trace the exact entity bronze → gold
- §4b mask → the flagged out-of-range rows now NULL, others intact

Statuses: `VERIFIED` / `STILL FAILING` / `VERIFIED (with caveats)` (explain).
Do not re-run the whole review — only the flagged conditions.

## Step 7: Summary

```
=== FIX FROM REVIEWS: $2 ===
Parsed:        N fixes (claude: X, codex: Y, after dedup: Z)
AUTO applied:  N  (VERIFIED: a, STILL FAILING: b, with caveats: c)
DEFERRED:      N judgment item(s) — listed below
SKIPPED:       N
Transform:     SUCCESS (validation passed) / FAILED (reverted)

{deferred judgment items: title, severity, evidence, recommendation}

Next: git diff src/etl/$0/$1/$2/transform.py to review the edits.
```

## Important Rules

- **Only `transform.py` is edited.** All gold changes flow through the
  re-run. The only file written besides that is nothing — the git diff is
  the audit trail.
- **Single-pass.** Never loop apply→transform→review automatically; if fixes
  are STILL FAILING, surface them and stop.
- **`--no-prompt` never asks anything** — every uncertainty becomes a
  deferred judgment item with a recommendation.
- Dedup across sources: one issue in both reports = one fix, two sources.
