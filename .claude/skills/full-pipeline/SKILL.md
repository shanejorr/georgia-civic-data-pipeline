---
name: full-pipeline
description: Run the complete bronze-to-gold pipeline for a topic — freshness gate, transform authoring (self-validating), parallel Claude + Codex data reviews, and fix-from-reviews when either review flags issues.
argument-hint: "[main_topic] [sub_topic] [topic] [--allow-stale-bronze] [--no-prompt]"
allowed-tools: ["Read", "Glob", "Grep", "Bash", "Agent", "Skill"]
---

# Full pipeline: transform, validate, review, fix

Five steps:

1. **Freshness gate** — bronze checksums + no unanalyzed files (script)
2. **Transform** — author + run `transform.py` (emits gold, contract,
   manifest, and validates itself)
3. **Validation gate** — independent re-run of the generic validator
4. **Reviews** — Claude review (Agent) + Codex review (Bash) **in parallel**
5. **Fix loop** — `/fix-from-reviews` when either review flags Required Fixes

## Arguments

`$ARGUMENTS` format: `[main_topic] [sub_topic] [topic] [--allow-stale-bronze] [--no-prompt]`

- `--allow-stale-bronze` — forward to the freshness gate (CHANGED/MISSING
  downgrade to warnings; UNANALYZED files always block).
- `--no-prompt` — batch mode: pass through to `/fix-from-reviews` so
  NEEDS_JUDGMENT items are deferred, never asked. Use whenever this skill
  runs inside a sub-agent.

## Step 1: Freshness gate

```bash
uv run python scripts/check_bronze_freshness.py $0 $1 $2{ --allow-stale when --allow-stale-bronze}
```

Non-zero exit → stop with `Overall: FAILED (stale bronze)` (or `FAILED
(unanalyzed bronze)`) and tell the user to run `/bronze-data-structure $0 $1 $2`.

## Step 2: Transform (Agent)

Spawn a general-purpose agent:

> Invoke the transform-topic skill by running: `/transform-topic $0 $1 $2{ --allow-stale-bronze when passed}`
>
> Follow all skill instructions completely, including the post-run
> self-review against the code-review checklist. When finished, report:
> 1. Whether transform.py was created and ran to exit 0 (exit 0 includes a
>    passing validation — the transform validates itself)
> 2. Years and row counts produced
> 3. The dedup tie-break decision and any §4b masks applied
> 4. The quality_checks authored (or why none apply)
> 5. Any warnings from the run (read-loss events, null-rate spikes)

If the agent reports failure, stop and relay details. Do not proceed.

## Step 3: Validation gate

Independent confirmation (cheap — the transform already validated):

```bash
uv run python scripts/validate_topic.py $0 $2
```

Non-zero → stop with `FAILED (validation)`. This catches the case where the
transform agent claimed success it didn't have.

## Step 4: Parallel reviews — Claude + Codex

> **Issue both tool calls in a single message** so they run concurrently.

**4a — Claude review (Agent):**

> Invoke the data-review-claude skill by running: `/data-review-claude $0 $1 $2`
>
> Follow all skill instructions completely. When finished, report:
> 1. Status (PASS / NEEDS FIXES / NEEDS_JUDGMENT)
> 2. Required-fix count and severity breakdown
> 3. The v1 parity verdict (MATCH / DIFFERS + the explanation)

**4b — Codex review (Bash, timeout 600000 ms):**

```bash
codex exec 'Use $data-review-codex for $0 $1 $2'
```

When it returns, verify `src/etl/$0/$1/$2/data-review-codex.md` exists and
run the structural validation below (full contract:
[docs/codex-review-contract.md](../../../docs/codex-review-contract.md)).
A missing/malformed report or a failed `codex` invocation is reported as
`MALFORMED`/`FAILED` but never stops the pipeline — the Claude review is
authoritative; a MALFORMED Codex report contributes zero fixes.

```bash
uv run python -c "
import re, sys
from pathlib import Path
p = Path('src/etl/$0/$1/$2/data-review-codex.md')
if not p.exists():
    print('MALFORMED: data-review-codex.md was not written'); sys.exit(2)
text = p.read_text()
errors = []
if not re.search(r'^# Data Review:', text, re.MULTILINE):
    errors.append('missing top-level heading')
m = re.search(r'^\*\*Status\*\*:\s*(PASS|NEEDS FIXES|BLOCKED)\s*\$', text, re.MULTILINE)
status = m.group(1) if m else None
if not m: errors.append('missing/malformed **Status** line')
c = re.search(r'^\*\*Must-fix count\*\*:\s*(\d+)\s*\$', text, re.MULTILINE)
count = int(c.group(1)) if c else None
if not c: errors.append('missing **Must-fix count** line')
has_fixes = bool(re.search(r'^## Required Fixes\s*\$', text, re.MULTILINE))
if status == 'NEEDS FIXES' and not has_fixes: errors.append('NEEDS FIXES without ## Required Fixes')
if status in ('PASS', 'BLOCKED') and has_fixes: errors.append(f'{status} with ## Required Fixes present')
if status == 'BLOCKED' and not re.search(r'^\*\*Blocker\*\*:', text, re.MULTILINE):
    errors.append('BLOCKED without **Blocker** line')
if has_fixes:
    for i, block in enumerate(re.split(r'^### Fix \d+:', text.split('## Required Fixes',1)[1], flags=re.MULTILINE)[1:], 1):
        for f in ['Severity', 'Issue', 'Evidence', 'Location', 'Suggested fix']:
            if f'**{f}**:' not in block: errors.append(f'Fix {i} missing **{f}**')
if errors:
    print('MALFORMED:'); [print(' -', e) for e in errors]; sys.exit(2)
print(f'PASS: Status={status}, Must-fix count={count}')
"
```

Wait for both before Step 5.

## Step 5: Fix loop (conditional, inline)

```bash
grep -l '^## Required Fixes' src/etl/$0/$1/$2/data-review-claude.md src/etl/$0/$1/$2/data-review-codex.md 2>/dev/null
```

- Neither file has `## Required Fixes` → record `SKIPPED (both reviews passed)`.
- Either does → invoke inline via the Skill tool (a sub-Agent would swallow
  interactive prompts):

```
Skill(skill: "fix-from-reviews", args: "$0 $1 $2{ --no-prompt when batch}")
```

`/fix-from-reviews` applies AUTO fixes, re-runs the transform (which
re-validates), verifies each fix against the regenerated gold, and defers
judgment items in `--no-prompt` mode. **Single-pass** — do not re-run the
reviews afterwards; remaining items surface in the summary.

## Final Output

```
=== FULL PIPELINE SUMMARY: $2 ===

Step 1 - Freshness:      {PASS/FAIL}
Step 2 - Transform:      {PASS/FAIL} — {years, rows; tie-break; §4b masks; quality_checks}
Step 3 - Validation:     {PASS/FAIL} — {N checks passed}
Step 4a - Claude Review: {PASS/NEEDS FIXES/NEEDS_JUDGMENT} — {fix counts; v1 parity}
Step 4b - Codex Review:  {PASS/NEEDS FIXES/BLOCKED/MALFORMED/FAILED} — {must-fix count}
Step 5  - Fixes:         {SKIPPED/APPLIED/PARTIAL/FAILED} — {applied/verified/deferred counts}

Overall: {PASS / FIXED / NEEDS FIXES / FAILED}
Deferred judgment items: {list or none}
```

`Overall`: `PASS` (both reviews clean) · `FIXED` (fixes applied, all
VERIFIED, validation passing) · `NEEDS FIXES` (items still failing or
deferred) · `FAILED` (fatal step).

## Important Rules

- Step 2 (transform) and Step 4a (Claude review) each run in their own
  **Agent** (fresh context). Step 5 runs **inline**.
- Codex failure of any kind never stops the pipeline.
- A fatal step (freshness, transform, validation) stops the pipeline.
- This skill never approves topics — approval is the user's, after review.
