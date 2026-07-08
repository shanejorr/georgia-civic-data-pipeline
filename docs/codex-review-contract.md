# Codex Review Report Contract

This document specifies the **required markdown structure** for `data-review-codex.md` files produced by the Codex agent in Step 4b of `/full-pipeline`. The pipeline automation (the Step 4b structural validation, the Step 5 fix-loop gating, `/fix-from-reviews` ingestion) depends on these structural conventions. A file that deviates from this contract will either be silently ignored or will break the gating logic.

## File location

`src/etl/{main_topic}/{sub_topic}/{topic}/data-review-codex.md`

The Codex agent overwrites this file on each review. A missing file means the Codex invocation failed — `/full-pipeline` treats that as a non-fatal warning and continues with Claude's review as authoritative.

## Required sections (in order)

Every report must contain the following top-level headings, **in this order**, spelled exactly as shown:

1. `# Data Review: {topic}` — top-level title
2. `## Verdict` — overall status block (see schema below)
3. `## Required Fixes` — **only when verdict is `NEEDS FIXES`**; omitted when verdict is `PASS` or `BLOCKED`

Additional sections (`## Summary`, `## Manifest Verification`, `## Notes`, etc.) may appear between these required sections. The automation only keys off the three headings above.

## Verdict schema

The `## Verdict` section must contain:

- A **Status** line that reads exactly one of:
  - `**Status**: PASS` — no must-fix items; reviewer believes the transform is accurate.
  - `**Status**: NEEDS FIXES` — at least one must-fix item; `## Required Fixes` must follow.
  - `**Status**: BLOCKED` — reviewer could not complete the review (e.g., missing manifest, transform did not run). No `## Required Fixes` section; instead, the Verdict block must include a `**Blocker**:` line describing what prevented the review.
- A **Must-fix count** line of the form `**Must-fix count**: N` where N is a non-negative integer. For `BLOCKED`, use `0`.

Example Verdict block (NEEDS FIXES case):

```markdown
## Verdict

**Status**: NEEDS FIXES
**Must-fix count**: 3

Summary: three categorical mapping issues in the 2019-2022 era plus one metric-scale regression in 2021.
```

Example Verdict block (PASS case):

```markdown
## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: manifest-driven categorical verification matches gold data; row-count reconciliation within tolerance; no data-loss risks identified.
```

## Required Fixes schema

When `Status` is `NEEDS FIXES`, the `## Required Fixes` section must list each fix as a `### Fix N: {short title}` subsection (starting at N=1, incrementing), with the following fields:

```markdown
### Fix 1: {short title}

- **Severity**: HIGH | MEDIUM | LOW
- **Issue**: {What is wrong — describe the data inaccuracy}
- **Evidence**: {Specific bronze value vs gold value, row count discrepancy, manifest mismatch, etc.}
- **Location**: {Line number or function in transform.py}
- **Suggested fix**: {What should change in transform.py to fix the data}
```

Rules:

- `### Fix N:` headings are numbered consecutively starting at 1. Do not skip numbers.
- The five bold fields (`Severity`, `Issue`, `Evidence`, `Location`, `Suggested fix`) are **required** on every fix. Omitting any field will cause `/fix-from-reviews` to skip the fix.
- Severity must be one of `HIGH`, `MEDIUM`, `LOW` (uppercase, no variants).
- Fixes should be ordered HIGH → MEDIUM → LOW within the section.

## Non-goals

This contract does **not** prescribe the review methodology or the exhaustive schema — it only formalizes the parts the pipeline automation reads. The Codex agent may include additional sections (summaries, tables, notes, etc.) as long as they do not precede `## Verdict` or `## Required Fixes`.

## Validation

`/full-pipeline` Step 4b runs a structural validation after the `codex exec` command returns. A malformed report (missing required headings, missing Status/Must-fix count lines, malformed Fix subsections) is reported as `MALFORMED` in the pipeline summary and does not contribute fixes to the fix loop. Claude's review remains authoritative in that case.

## Parity with Claude's review

The Required-Fixes schema mirrors `data-review-claude.md` Step 10 format exactly so that `/fix-from-reviews` can deduplicate across both reports without per-reviewer special-casing. If Claude's format changes, this contract must change in lockstep.
