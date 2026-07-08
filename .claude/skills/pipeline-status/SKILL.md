---
name: pipeline-status
description: Scan all topic directories and report which pipeline steps have been completed for each topic, plus drift and referential-integrity status.
argument-hint: "[main_topic] or leave blank for all"
allowed-tools: ["Bash", "Glob", "Read"]
---

# Pipeline Status Report

Scan all topic directories and report a matrix of which pipeline artifacts
exist for each topic, then run the standing repo-health checks (approved-gold
drift incl. dimension baselines, and referential integrity).

## Input

Arguments: `$ARGUMENTS` (optional `main_topic` filter; blank scans all).

## Steps

### 1. Run the status matrix

```bash
uv run python -c "
import json, sys
from pathlib import Path
import yaml

main_topic_filter = '$ARGUMENTS'.strip() or None
bronze_root, gold_root, etl_root = Path('data/bronze'), Path('data/gold'), Path('src/etl')
status_file = Path('topic-status.yaml')
approval_map = (yaml.safe_load(status_file.read_text()) or {}).get('topics', {}) if status_file.exists() else {}

topics = []
for mt in sorted(p for p in bronze_root.iterdir() if p.is_dir() and not p.name.startswith(('.', '_'))):
    if main_topic_filter and mt.name != main_topic_filter:
        continue
    for st in sorted(p for p in mt.iterdir() if p.is_dir() and not p.name.startswith(('.', '_'))):
        for tp in sorted(p for p in st.iterdir() if p.is_dir() and not p.name.startswith(('.', '_'))):
            topics.append((mt.name, st.name, tp.name))
if not topics:
    print('No topics found.'); sys.exit(0)

def validation_state(gold_dir):
    '''Return '+' passed+fresh, 'x' failing, 'o' stale, '-' absent.'''
    vp, mp = gold_dir / '_validation.json', gold_dir / '_transform_manifest.json'
    if not vp.exists():
        return '-'
    try:
        val = json.loads(vp.read_text())
    except Exception:
        return 'x'
    if not val.get('passed'):
        return 'x'
    if mp.exists():
        try:
            gen = json.loads(mp.read_text()).get('generated_at', '')
            if str(val.get('timestamp', '')) < str(gen):
                return 'o'
        except Exception:
            pass
    return '+'

rows = []
for main, sub, topic in topics:
    bronze_dir = bronze_root / main / sub / topic
    gold_dir = gold_root / main / topic
    etl_dir = etl_root / main / sub / topic
    rows.append({
        'group': f'{main}/{sub}', 'topic': topic, 'main': main, 'sub': sub,
        'bronze': any(bronze_dir.glob(p) for p in ('*.xlsx', '*.csv', '*.xls')),
        'structure': (bronze_dir / 'bronze-data-structure.md').exists(),
        'transform': (etl_dir / 'transform.py').exists(),
        'gold': gold_dir.exists() and any(gold_dir.glob('year=*/')),
        'validation': validation_state(gold_dir) if gold_dir.exists() else '-',
        'review_c': (etl_dir / 'data-review-claude.md').exists(),
        'review_x': (etl_dir / 'data-review-codex.md').exists(),
        'approved': bool((approval_map.get(f'{main}/{sub}/{topic}') or {}).get('approved')),
    })

mark = lambda v: '✓' if v is True else ('-' if v is False else v)
print('=== PIPELINE STATUS ===')
print('(Validation: + passed/fresh, x failing, o stale, - absent)')
group = None
for r in rows:
    if r['group'] != group:
        group = r['group']
        print(f'\n{group}:')
        hdr = f\"{'Topic':<58}| {'Brz':^4}| {'Doc':^4}| {'Xform':^6}| {'Gold':^5}| {'Valid':^6}| {'Rev-C':^6}| {'Rev-X':^6}| {'Appr':^5}\"
        print(hdr); print('-' * len(hdr))
    print(f\"{r['topic']:<58}| {mark(r['bronze']):^4}| {mark(r['structure']):^4}| {mark(r['transform']):^6}| {mark(r['gold']):^5}| {r['validation']:^6}| {mark(r['review_c']):^6}| {mark(r['review_x']):^6}| {mark(r['approved']):^5}\")

print('\n=== SUMMARY ===')
total = len(rows)
done = sum(1 for r in rows if r['transform'] and r['gold'] and r['validation'] == '+' and r['review_c'])
print(f'Total topics: {total}')
print(f'Approved: {sum(1 for r in rows if r[\"approved\"])}')
print(f'Processed (gold + passing validation + Claude review): {done}')
print(f'Awaiting approval: {sum(1 for r in rows if r[\"transform\"] and r[\"gold\"] and not r[\"approved\"])}')
print(f'Pending (structure doc, no transform): {sum(1 for r in rows if r[\"structure\"] and not r[\"transform\"])}')
print(f'Need structure doc: {sum(1 for r in rows if r[\"bronze\"] and not r[\"structure\"])}')

print('\n=== NEXT ACTIONS ===')
for r in rows:
    args = f\"{r['main']} {r['sub']} {r['topic']}\"
    if r['validation'] in ('x', 'o') :
        print(f\"  {r['topic']}: validation {('failing','stale')[r['validation']=='o']} — re-run: uv run python -m src.etl.{r['main']}.{r['sub']}.{r['topic']}.transform\")
    elif r['transform'] and r['gold'] and not r['review_c']:
        print(f\"  {r['topic']}: needs data review — /data-review-claude {args}\")
    elif r['transform'] and r['gold'] and r['review_c'] and not r['approved']:
        print(f\"  {r['topic']}: awaiting your approval — /approve-topic {args}\")
    elif r['structure'] and not r['transform'] and not r['approved']:
        print(f\"  {r['topic']}: needs pipeline — /full-pipeline {args}\")
    elif r['bronze'] and not r['structure']:
        print(f\"  {r['topic']}: needs structure doc — /bronze-data-structure {args}\")
"
```

### 2. Standing repo-health checks

```bash
uv run python scripts/check_approved_topics.py
uv run python scripts/check_referential_integrity.py
```

Drift (topic gold or dimension baselines) and FK violations are not fatal
here — surface the output so the user decides whether to investigate,
re-run, or re-approve. During a rebuild window with nothing approved, both
print their no-scope messages; add `--all` to the integrity check to sweep
unapproved topics too.

### 3. Review results

Read-only — this skill creates and modifies nothing.

## Important Rules

- This skill is **read-only**.
- If the `main_topic` filter doesn't exist, list available main topics.
