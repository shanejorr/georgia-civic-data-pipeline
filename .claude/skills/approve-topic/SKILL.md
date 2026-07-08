---
name: approve-topic
description: Mark a topic as approved in topic-status.yaml after the user has reviewed its gold output. Requires a fresh passing validation; captures gold + dimension hash baselines.
argument-hint: "<main_topic> <sub_topic> <topic> (blank to list pending; --approve-all-pending for the batch mode)"
allowed-tools: ["Bash"]
---

# Approve Topic

Mark a topic as reviewed-and-approved by the user. Approval is **post-hoc** —
the pipeline must already have run (transform.py + gold + a fresh, passing
`_validation.json`; the script refuses otherwise) and warns when either
review report is missing.

Approval captures the drift baselines: `approved_gold_sha256` for the topic
and the top-level `dimensions:` hash map (districts/schools/demographics), so
both gold edits and dimension rebuilds after approval are detectable by
`scripts/check_approved_topics.py`.

## Input

Arguments: `$ARGUMENTS`

- `<main_topic> <sub_topic> <topic>` — approve one topic.
- Blank — list topics awaiting approval.
- The user may also run the batch mode themselves after reviewing everything:
  `uv run python scripts/approve_topic.py --approve-all-pending`
  (per-topic gates still enforced for each).

## Steps

### 1. Run the approval script

```bash
uv run python scripts/approve_topic.py $ARGUMENTS
```

### 2. Confirm the contract is committed

The ODCS contract is emitted by the transform, so an approved topic's
`contracts/{main}/{topic}.odcs.yaml` is already current from its last run.
Tell the user to commit the contract alongside the `topic-status.yaml`
change. If the contract is somehow missing, re-run the transform (it
re-emits everything and re-validates).

### 3. Report back

Echo the script output. On success, mention the topic is now live for the
API/MCP registry on next restart, and suggest `/pipeline-status` for what's
next.

## Important Rules

- **Only the user approves. Never run this skill unprompted.**
- Do not overwrite `approved: true` entries unless the user explicitly
  re-approves.
- If the script refuses (no transform / no gold / failing or stale
  validation), do not work around it — fix the topic first.
