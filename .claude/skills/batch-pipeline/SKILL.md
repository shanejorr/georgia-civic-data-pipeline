---
name: batch-pipeline
description: Run the full pipeline for all eligible topics in a sub_topic, in parallel batches of non-prompting agents (default 2 at a time). Judgment items are deferred to an aggregate report, never asked.
argument-hint: "[main_topic] [sub_topic] [--batch-size N]"
allowed-tools: ["Read", "Write", "Bash", "Glob", "Agent"]
---

# Batch Pipeline

Runs `/full-pipeline` across every eligible topic in a sub_topic, in
**parallel batches** (default 2; never raise above 4 on this machine — each
topic runs transforms, two reviews, and a possible fix loop concurrently).

**Non-prompting by construction.** Every per-topic agent runs the pipeline
with `--no-prompt`: NEEDS_JUDGMENT fixes are deferred and collected into the
aggregate report, never asked. The user works the judgment items afterwards.

## Arguments

`$ARGUMENTS` format: `[main_topic] [sub_topic] [--batch-size N]`

## Step 1: Discover eligible topics

Eligible = has `bronze-data-structure.md`, has **no** `transform.py`, and is
not approved in `topic-status.yaml`. Topics with a transform but no approval
are "awaiting review" — list them separately, do not re-run them.

```bash
uv run python -c "
from pathlib import Path
import yaml
status = yaml.safe_load(Path('topic-status.yaml').read_text())['topics']
eligible, awaiting, no_doc = [], [], []
for key in sorted(status):
    if status[key].get('approved'):
        continue
    main, sub, topic = key.split('/')
    if main != '$0' or sub != '$1':
        continue
    doc = Path(f'data/bronze/{main}/{sub}/{topic}/bronze-data-structure.md')
    tf = Path(f'src/etl/{main}/{sub}/{topic}/transform.py')
    if not doc.exists():
        no_doc.append(topic)
    elif tf.exists():
        awaiting.append(topic)
    else:
        eligible.append(topic)
print('ELIGIBLE:', *eligible, sep='\n  ')
print('AWAITING REVIEW (skip):', *awaiting, sep='\n  ')
print('NEED /bronze-data-structure:', *no_doc, sep='\n  ')
"
```

If nothing is eligible, stop and report.

## Step 2: Plan the batches

Group eligible topics into batches of `--batch-size` (default 2),
**pairing sibling topics in the same batch** so shared naming and helper
decisions are made once: district/school variants, recent/highest variants,
c11/c12 reports, EOC/EOG pairs, march/october enrollment pairs, topics
sharing a bronze directory or a `_shared` helper module. Within a sibling
group larger than the batch size, schedule the group in consecutive batches
— the first topic authors any shared helper module; later siblings reuse it.
Otherwise alphabetical. Print the batch plan before starting.

## Step 3: Run batches

For each batch, spawn one **Agent** per topic **in a single message** (they
run concurrently), each with this prompt:

> Run the full bronze-to-gold pipeline for one topic, non-interactively.
> You must never ask the user a question — defer every uncertainty as a
> judgment item in your final report.
>
> Invoke the full-pipeline skill by running:
> `/full-pipeline $0 $1 {topic} --no-prompt`
>
> Follow all skill instructions completely. End your final message with this
> exact block:
>
> ```
> === TOPIC RESULT ===
> topic: $1/{topic}
> overall: PASS | FIXED | NEEDS FIXES | FAILED
> transform: {years} years, {rows} rows
> validation: PASS | FAIL
> claude_review: {status} ({fix counts})
> codex_review: {status} ({must-fix count})
> fixes: {applied}/{verified} applied/verified, {deferred} deferred
> v1_parity: MATCH | DIFFERS — {one-line why} | N/A
> JUDGMENT_ITEMS:
> - [SEVERITY] {title} :: {evidence} :: {recommendation}
> (or "none")
> ===
> ```

Wait for the whole batch before dispatching the next. Print
`[batch K/N] complete: {topic}: {overall}, {topic}: {overall}` after each.
An agent that errors without a result block → record `FAILED_OTHER` and
continue; never let one topic abort the sweep.

## Step 4: Aggregate report

After all batches, append per-topic results and ALL deferred judgment items
(grouped by topic, HIGH first, each with its recommendation) to
`docs/rebuild/rebuild-report.md` (create with a header if absent). Print a
console summary:

```
=== BATCH PIPELINE: $0/$1 ===
Processed: N topics in B batches
  PASS: n   FIXED: n   NEEDS FIXES: n   FAILED: n
  v1 parity: n MATCH / n DIFFERS / n N/A
  Deferred judgment items: n (see docs/rebuild/rebuild-report.md)
Next: review judgment items, then approve via
  uv run python scripts/approve_topic.py --list-pending
```

## Important Rules

- **Agents never prompt** — `--no-prompt` end to end; judgment items are the
  escape hatch.
- One topic per agent, batches dispatched in a single message, wait between
  batches.
- Failures are logged and skipped, not retried automatically.
- This skill never approves topics.
