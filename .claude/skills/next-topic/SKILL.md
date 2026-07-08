---
name: next-topic
description: Resolve the next topic to process by walking topic-status.yaml alphabetically, skipping approved topics and topics that already have a transform.py, and invoking /full-pipeline on the first eligible candidate.
argument-hint: "[--dry-run] [--allow-stale-bronze]"
allowed-tools: ["Read", "Bash", "Skill"]
---

# Pick and run the next eligible topic

This skill implements the "next topic" resolution algorithm defined in root `CLAUDE.md` so the user can say "run the next one" without naming it explicitly.

## Arguments

`$ARGUMENTS` may include optional flags:

- `--dry-run` — print the picked topic and exit without invoking `/full-pipeline`
- `--allow-stale-bronze` — forward to `/full-pipeline` when the picked topic has stale checksums you already vetted

Any other argument is rejected — this skill does not take topic names. Use `/full-pipeline` directly when you want to target a specific topic.

## Step 1: Resolve the candidate

Run this Python script to pick the next topic. It reads `topic-status.yaml`, walks entries alphabetically, and returns the first topic where **all** of these hold:

1. `approved: false`
2. `data/bronze/{main}/{sub}/{topic}/bronze-data-structure.md` exists
3. `src/etl/{main}/{sub}/{topic}/transform.py` does **not** exist yet

```bash
uv run python -c "
import yaml, sys
from pathlib import Path

status = yaml.safe_load(Path('topic-status.yaml').read_text())
topics = status.get('topics', {}) or {}

picked = None
awaiting_review = []

for full_path in sorted(topics.keys()):
    entry = topics[full_path] or {}
    if entry.get('approved', False):
        continue
    parts = full_path.split('/')
    if len(parts) != 3:
        continue
    main, sub, topic = parts
    bronze_doc = Path(f'data/bronze/{main}/{sub}/{topic}/bronze-data-structure.md')
    transform_py = Path(f'src/etl/{main}/{sub}/{topic}/transform.py')

    if not bronze_doc.exists():
        continue
    if transform_py.exists():
        awaiting_review.append(full_path)
        continue

    picked = (main, sub, topic)
    break

if picked is None:
    print('NONE: no eligible topic found')
    if awaiting_review:
        print('')
        print('Topics awaiting user review (not candidates for /full-pipeline):')
        for p in awaiting_review:
            print(f'  - {p}')
        print('')
        print('Run /approve-topic on these when satisfied with their gold output.')
    sys.exit(1)

main, sub, topic = picked
print(f'PICKED: {main} {sub} {topic}')
"
```

If the script exits non-zero (no candidate), stop and relay its output to the user. Do not invoke `/full-pipeline`.

## Step 2: Dry-run gate

If the user passed `--dry-run`, stop here and print the picked topic. Do not invoke `/full-pipeline`.

## Step 3: Invoke `/full-pipeline`

When a candidate was picked and `--dry-run` was not passed, invoke the full pipeline via the Skill tool (inline, not via Agent — `/full-pipeline` orchestrates its own sub-Agents):

```
Skill(skill: "full-pipeline", args: "{main} {sub} {topic}{append ' --allow-stale-bronze' when the user passed that flag}")
```

Pass through `--allow-stale-bronze` verbatim when the user included it.

## Step 4: Post-pipeline reminder

After `/full-pipeline` returns (regardless of Overall status), print:

> Review the gold output and the two data-review reports for `{main}/{sub}/{topic}`, then run `/approve-topic {main} {sub} {topic}` when satisfied.

This mirrors the "next topic" workflow note in root `CLAUDE.md` so the user is never left guessing what to do next.

## Important rules

- This skill never picks a topic that already has `transform.py` — those are "awaiting review," not candidates for a fresh pipeline run.
- This skill never picks an approved topic.
- Alphabetical ordering is by the full `main/sub/topic` path, matching the algorithm defined in root `CLAUDE.md`.
- If no candidate exists, surface the "awaiting review" list so the user knows which approvals are pending.
