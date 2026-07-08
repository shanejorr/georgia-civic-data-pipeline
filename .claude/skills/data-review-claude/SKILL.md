---
name: data-review-claude
description: Conduct a manifest-driven data accuracy review of a single topic by comparing bronze inputs to gold outputs, then write a data-review-claude.md report listing required fixes.
argument-hint: "[main_topic] [sub_topic] [topic]"
allowed-tools: ["Read", "Write", "Bash", "Glob", "Grep"]
---

# Data Review — Bronze-to-Gold Accuracy Audit (judgment layer)

This skill is the **judgment layer** of validation: it verifies the things
deterministic code cannot — whether categorical mappings are *semantically*
correct, whether values survived the bronze→gold journey intact, whether the
transform's interpretive decisions (eras, dedup, year attribution,
demographics conventions) were right.

It does **not** re-run structural checks. The generic validator already
enforced — on this same gold, in the transform run that produced it — schema↔
contract↔parquet conformance, types, percentage scale by `unit`, grain
uniqueness, the contract's own quality SQL, FK integrity against dimensions,
canonical vocabulary, ID formatting, geography nulling, and suppression
markers. The review **reads** `_validation.json` and builds on it. If you
find yourself re-implementing a validator check inline, stop — read the
report instead.

<core_principle>
**Derive from artifacts, never hardcode.** Metric ranges/units → the
contract. Demographic vocabulary → `src/utils/demographics.py` + the
demographics dimension. FK targets/grain → the contract. File→year/era
mapping → the manifest. When a check needs a fact, the first move is "which
artifact already states this?"
</core_principle>

## Input

Arguments: `$ARGUMENTS` (format: `[main_topic] [sub_topic] [topic]`)

**Derived paths:**
- Bronze: `data/bronze/$0/$1/$2/` (+ `bronze-data-structure.md`)
- Gold: `data/gold/$0/$2/`
- Transform: `src/etl/$0/$1/$2/transform.py`
- Contract: `contracts/$0/$2.odcs.yaml`
- Manifest: `data/gold/$0/$2/_transform_manifest.json`
- Validation report: `data/gold/$0/$2/_validation.json`
- Output report: `src/etl/$0/$1/$2/data-review-claude.md`

---

## Preconditions — halt if any fails

1. `transform.py`, `bronze-data-structure.md`, gold parquet, the contract,
   `_transform_manifest.json`, and `_validation.json` all exist.
2. **Freshness**: `transform.py`'s mtime is not newer than the manifest's
   `generated_at`, and `_validation.json`'s `timestamp` is not older than the
   manifest's `generated_at`. Stale artifacts → halt with
   `FAILED (stale gold/manifest)`: re-run
   `uv run python -m src.etl.$0.$1.$2.transform` and re-invoke.
3. **Validation passed**: `_validation.json` has `"passed": true`. If not,
   halt with `FAILED (validation failing)` — the transform must be fixed
   before a review is meaningful.
4. **Read loss**: if the manifest has a `read_loss` section, every event must
   carry a `note` explaining why the loss is legitimate. Unacknowledged loss
   → this review's FIRST Required Fix (HIGH), and continue reviewing.
   (`read_loss` / `masked_values` / `reclassified` sections are omitted
   entirely when empty — an absent section means zero events, not
   "not recorded".)

```bash
uv run python -c "
import json, datetime as dt
from pathlib import Path
tp = Path('src/etl/$0/$1/$2/transform.py')
gold = Path('data/gold/$0/$2')
manifest = json.loads((gold / '_transform_manifest.json').read_text())
val = json.loads((gold / '_validation.json').read_text())
gen = manifest['generated_at']
tp_m = dt.datetime.fromtimestamp(tp.stat().st_mtime, dt.timezone.utc).isoformat()
print('transform mtime :', tp_m)
print('manifest gen    :', gen)
print('validation ts   :', val['timestamp'])
print('validation pass :', val['passed'])
stale = tp_m > gen or val['timestamp'] < gen
print('STALE' if stale else 'FRESH')
loss = manifest.get('read_loss', [])
bad = [e for e in loss if not e.get('note')]
print(f'read_loss events: {len(loss)} ({len(bad)} unacknowledged)')
"
```

---

## Risk Hypotheses — what has actually shipped wrong before

Rule each in or out for this topic. Step 8 re-checks that you did.

<risk_hypotheses>
1. **Asian/PI conflation** — bronze "Asian" is the combined pre-1997 bucket but gold says `asian`. Silent: counts tie out. (Step 2e)
2. **Column-rename typo** — one era's gold column is ~100% NULL while other years are populated. (Step 3c)
3. **Sentinel year-attribution** — a year embedded in a bronze string attached to the file's year instead. (Step 4c)
4. **Derived-row aggregation error** — district/state rows derived by summing use the wrong grouping or average percentages. (Step 4d)
5. **Dedup tie-break inversion** — the wrong era's row survives dedup on overlap years. (Step 4e)
6. **Demographic mutual-exclusivity violation** — split rows AND a rollup row in the same category, double-counting. (Step 2f)
7. **Semantically wrong mapping** — a map entry that is mechanically applied but means the wrong thing. (Step 2b — the core of this review)
</risk_hypotheses>

---

## Step 1: Read Context

Read: `transform.py`, `bronze-data-structure.md`, `src/etl/$0/CLAUDE.md`,
the contract (note each metric's `unit`/bounds, the `key_metric` +
`metric_component` markers, the grain, the `foreign_keys` block,
`null_semantics`, the quality checks), the manifest,
and **`_validation.json`** (note every check's status; warnings — null-rate
spikes, tidy heuristics — are YOUR work items to explain or escalate).

## Step 2: Manifest-Driven Categorical Verification

From the manifest's `categorical_mappings`, for each column:

- **2a Completeness** — every distinct bronze value documented in
  `bronze-data-structure.md` appears in `bronze_values_seen`; flag documented
  values the transform never encountered (file-routing bug or skipped era).
- **2b Correctness — verify EVERY map entry semantically.** Is
  `(bronze_key → gold_value)` *meaningfully* right (not just snake_cased)?
  This is 100% coverage of all recodings and the highest-value step of the
  review. ("Science Reasoning" → `science` is right; → `reading` would be
  wrong; "Economically Disadvantaged Flag = N" → `economically_disadvantaged`
  would be wrong.)
- **2c Contract cross-check** — `gold_values_produced` equals the contract's
  `enum` for the column.
- **2d Unmapped** — `unmapped_count` is 0 (the manifest writer enforces this;
  a nonzero here means a bypass — HIGH fix).

### 2e: Asian / Pacific Islander conflation (Risk 1)

Executable, not narrative. Triage: if `gold_values_produced` for
`demographic` has no `asian` and gold has no `pct_asian` column, record
`N/A` — except when gold emits `asian_pacific_islander` from an explicit
combined bronze label: record PASS and run the math test anyway as the
*positive* evidence for the convention. Otherwise:

1. `grep -iE 'pacific[ _-]?islander|native[ _-]?hawaiian|nhpi' data/bronze/$0/$1/$2/bronze-data-structure.md || echo NO_NHPI_LABEL_IN_BRONZE`
2. **Math test** (count metrics): at the latest state-level row, sum the race
   buckets (from `DEMOGRAPHIC_CATEGORIES`, race category — total row is
   `all`) and compare to the cohort total. ratio ≈ 1.00 → CONFLATED.
3. Average-style metrics (SAT/ACT): structural test — if bronze never
   publishes a separate Pacific Islander row anywhere in any era, treat bare
   "Asian" as combined; cite a sibling topic from the same vendor.
4. **Decision**: CONFLATED math test, or NO_NHPI_LABEL + structural argument
   → HIGH Required Fix "Remap bronze 'Asian' → asian_pacific_islander",
   quoting the printed math-test line verbatim. Else record PASS with the
   ratio as evidence.

```bash
uv run python -c "
import polars as pl
from src.utils.demographics import DEMOGRAPHIC_CATEGORIES
gold = pl.read_parquet('data/gold/$0/$2/**/*.parquet', hive_partitioning=True)
if 'demographic' not in gold.columns:
    print('SKIP: no demographic column'); raise SystemExit
year = sorted(gold['year'].unique().to_list())[-1]
state = gold.filter(pl.col('year') == year)
for c in ('district_code', 'school_code'):
    if c in state.columns:
        state = state.filter(pl.col(c).is_null())
total_row = state.filter(pl.col('demographic') == 'all')
if total_row.height == 0:
    print('GUARD: no demographic==all state row — confirm the total key'); raise SystemExit
race_buckets = [k for k, v in DEMOGRAPHIC_CATEGORIES.items() if v == 'race']
races = state.filter(pl.col('demographic').is_in(race_buckets))
print('Race buckets present:', sorted(races['demographic'].unique().to_list()))
for m in [c for c in state.columns if state[c].dtype.is_numeric() and c != 'year']:
    if any(s in m for s in ['pct_', '_rate', '_percent']):
        continue
    total, race_sum = total_row[m].sum(), races[m].sum()
    if total and race_sum and total > 0:
        r = race_sum / total
        verdict = 'CONFLATED' if 0.98 <= r <= 1.02 else 'OK'
        print(f'{m}: year={year} total={total} race_sum={race_sum} ratio={r:.4f} -> {verdict}')
        break
else:
    print('SKIP: no summable count metric — use the structural test')
"
```

### 2f: Demographic mutual exclusivity (Risk 6)

If `gold_values_produced` contains a rollup key alongside its split keys
(`asian_pacific_islander` with `asian`/`pacific_islander` — same logic for
any category), check per-natural-key overlap; any group containing both →
HIGH Required Fix (drop the convention bronze does not publish). Use
`DEMOGRAPHIC_CATEGORIES` to identify same-category keys. Otherwise record
`PASS — single convention`.

### Early termination

More than 5 critical categorical failures → write the report with Steps 1–2
findings, status `NEEDS FIXES (EARLY TERMINATION)`, skip the rest.

## Step 3: Row Counts and Metric Plausibility

- **3a Reconciliation** — manifest `row_counts`: bronze − filtered ≈ gold per
  year (expansion factors consistent across years; explain outliers from the
  structure doc — unpivots, placeholder filtering, folds). All expected years
  present per the structure doc.
- **3b Actual parquet count** — sum gold parquet rows; must equal manifest
  `total_gold`.
- **3c Cross-year column completeness (Risk 2)** — per column, per year, flag
  ~100% NULL years when other years are populated (era-localized rename bug
  signature); a column NULL in *every* year → NEEDS_JUDGMENT.

```bash
uv run python -c "
import polars as pl
df = pl.read_parquet('data/gold/$0/$2/**/*.parquet', hive_partitioning=True)
key_cols = {'year', 'district_code', 'school_code', 'demographic'}
for col in [c for c in df.columns if c not in key_cols]:
    by = (df.group_by('year').agg(pl.col(col).null_count().alias('n'), pl.len().alias('t'))
            .with_columns((pl.col('n')/pl.col('t')).alias('p')).sort('year'))
    bad = by.filter(pl.col('p') >= 0.95)
    if 0 < bad.height < by.height:
        print(f'FLAG {col}: ~100% NULL only in {bad[\"year\"].to_list()}')
    elif bad.height == by.height:
        print(f'INVESTIGATE {col}: 100% NULL in every year')
"
```

- **3d Year-over-year level continuity** — compare state-level metric
  means/sums across ALL adjacent year pairs (not just era boundaries): flag
  >10x jumps anywhere (scale inconsistency signature) and, for currency and
  count metrics, sustained ~1.5–2x single-year level shifts that revert the
  following year (the cumulative-publication signature — found the
  salaries 2021 ~2x anomaly). Metric *ranges* are already enforced by the
  contract quality checks — do not re-verify bounds here.

## Step 4: Value-Level Spot Checks

The manifest verified the mappings; the validator verified the structure.
Spot checks verify **values**. Resolve all placeholders from the manifest
(`files_processed` maps file→year/era) before running anything.

<investigate_before_answering>
Read the bronze, quote the specific values, then state the verdict. A
verdict without a quoted bronze line is not acceptable.
</investigate_before_answering>

- **4a Extreme-row traces (NEW, do these first).** For each metric column,
  take the manifest's per-year max and min rows, locate those entities in
  bronze, and trace bronze → expected transformation → gold. Extremes are
  where unit, scale, and column-swap errors live. At minimum: the global max
  row and global min row of every metric. (Gotcha: bronze geography
  sentinels like `INSTN_NUMBER='ALL'` become NULL in gold — resolve
  sentinels before building the gold lookup filter.)
- **4b Ordinary traces** — one entity per era, all columns, bronze → gold.
- **4c Sentinel year-attribution (Risk 3)** — grep transform.py for
  year-bearing literals/parsing (`20[0-2][0-9]|FY[0-2][0-9]`); if present,
  trace one sentinel row: gold `year` must match the year inside the string,
  not the file's year. Else `N/A`.
- **4d Aggregate-row reconciliation (Risk 4)** — when the transform DERIVES
  district/state rows: reconcile one (year, district): sum of school rows vs
  the district row for each count metric (diff >2% → fix); any `.mean()` on a
  percentage during derived aggregation → MEDIUM fix. When aggregates COME
  FROM BRONZE, run the **feasibility screen** instead: for each year, a
  published district mean must lie within the bounds implied by its school
  rows (`[(S + e·domain_min)/n, (S + e·domain_max)/n]` where S = sum of
  school score×count, e = students not covered by school rows, n = district
  count); a published district count must be ≥ the max school count and
  plausibly ≈ the school sum. For district-only topics, the variant is:
  reconcile the state rollup against the sum of district rows per
  category-year (tolerate composition drift; flag swaps/garbling). For
  suppression-heavy topics, the useful direction is impossibly-LOW
  aggregates (district < max school, district < visible school sum).
  (polars note: `is_between('850','888')` parses bare strings as column
  names — wrap literals in `pl.lit()`.) Provable violations → Required Fix
  (pinned repair or §4b mask); systematic-but-unprovable patterns →
  NEEDS_JUDGMENT with a contract-caveat recommendation. This screen found real shipped
  defects (act_scores 2007 swap, 2009 Atlanta) that row counts and ranges
  cannot see.
- **4e Dedup tie-break (Risk 5)** — from `files_processed`, find a year
  covered by two eras; trace one entity present in both: gold must equal the
  documented winner's bronze. No overlap years → `N/A`.
- **4f Suppression semantics** — trace one suppressed bronze cell per marker
  type to a NULL gold cell (and, where the topic encodes suppression in a
  status column, the right status value).

## Step 5: Contract & Validation Cross-Read

- **5a** Confirm `_validation.json` shows `contract_parquet_schema`,
  `contract_quality_sql`, `grain_uniqueness`, and `foreign_keys` all passing
  (they must — precondition 3). Record the contract `schema_hash` in Notes.
- **5b §4b masking audit** — for every `_null_*` helper in transform.py:
  mask recorded in the manifest's `masked_values` section (count + reason +
  years — verify the counts there, not from logs)? handling documented in the
  column's contract `description`? range guard (`value_min`/`value_max`/unit
  bounds) present so the mask stays enforceable? An unrecorded or
  undocumented mask is a MEDIUM fix.
- **5c §15b coverage judgment** — does the contract's `quality` list cover
  the topic's real cross-column invariants (partition sums, co-null,
  component totals, structural facts)? A missing obvious invariant is a
  MEDIUM Required Fix ("author quality_check X"), because un-authored
  invariants are unenforced forever.
- **5d v1 parity** — if `docs/rebuild/v1-baseline.yaml` has an entry for this
  topic, compare:

```bash
uv run python -c "
import sys, yaml
sys.path.insert(0, 'scripts')
from approve_topic import compute_gold_sha256
from pathlib import Path
base = yaml.safe_load(Path('docs/rebuild/v1-baseline.yaml').read_text())['topics']
key = '$0/$1/$2'
cur = compute_gold_sha256('$0', '$2')
old = (base.get(key) or {}).get('approved_gold_sha256')
print('MATCH — byte-identical with v1 gold' if cur == old else f'DIFFERS from v1\\n  v1:  {old}\\n  now: {cur}')
"
```

  Caution: `git show v1-pipeline:` docs (reviews, gold-data-structure) can
  predate v1's own fix loop — the approved hash reflects the post-fix
  transform. Trust v1's transform.py + the baseline hash, not tag-era prose.

  `MATCH` is strong evidence and goes in the Summary. `DIFFERS` is **not**
  a failure — but the review must *explain why* (new §4b mask, a fix, an
  intentional convention change, different dedup winner...). An unexplained
  DIFFERS is a NEEDS_JUDGMENT item. Compare row counts and per-year metric
  stats against `git show v1-pipeline:` artifacts when hunting the cause.

## Step 6: Column Coverage vs the Structure Doc

From `bronze-data-structure.md`'s Gold Schema Classification: every
`fact_key`/`fact_metric`/`fact_categorical` column lands in gold (under its
gold name); every `dimension_attribute`/`not_in_gold` exclusion's reason
holds; every gold column traces back to bronze (no fabrication). Then read
transform.py's rename maps per era for typos and unhandled conditional
columns.

**Contract prose fidelity.** The contract's *served* text — `purpose` /
`limitations` / `null_semantics` and each column's `description` — is grounding
context for the REST schema endpoint, MCP `describe_dataset`, and Data Talk, so a
description that drifts from the source ships a grounded-but-wrong answer with a
citation on it. Audit it against `bronze-data-structure.md` for **contradictions
only** (not prose style): year range/coverage, suppression scheme + markers,
percentage scale, demographic convention (combined vs split race buckets), and
every `not_in_gold` claim. Any assertion the bronze doc refutes is a MEDIUM
Required Fix, quoting the contradicting bronze line. Agreement is not a finding —
surface only contradictions.

## Step 7: Transform Logic Review (data-accuracy only)

One-line verdict each (PASS/FLAG/N/A): silent column drops · era routing
correctness · filter logic logged+justified · normalization map completeness
vs the structure doc · `strict=False` casts · dedup keys + tie-break ·
year extraction. (Code quality is the checklist's job, not this review's.)

## Step 8: Self-Critique

Every risk hypothesis and every step above has a verdict (PASS with
evidence / Required Fix / NEEDS_JUDGMENT / documented N/A) before you write
the report. Each verdict must cite executed output or quoted values — never
intuition.

## Step 9: Write the Report

Write to `src/etl/$0/$1/$2/data-review-claude.md`. **This format is a
compatibility surface** (fix-from-reviews and the Codex contract parse it) —
do not alter the heading names or the five bold fix fields.

```markdown
# Data Review: $2

**Date**: {date}
**Reviewer**: Claude (automated data review)
**Status**: {PASS | NEEDS FIXES | NEEDS_JUDGMENT}

## Summary

{2-3 sentences: verdict, v1 parity (MATCH / DIFFERS+why), anything load-bearing}

## Manifest Verification

{categorical map table: column | entries | bronze seen | unmapped | status}
{full map review per column: bronze → gold | correct? — for every entry}
{row-count reconciliation table + assessment}

## Column Coverage

{bronze column | gold column | MAPPED / CORRECTLY EXCLUDED / MISSING}

## Value-Level Spot Checks

{per trace: bronze file+row+value, expected transform, gold value, MATCH/MISMATCH
 — extreme rows first, then one ordinary entity per era}

## Validation Cross-Read

{_validation.json summary line; schema_hash; §4b masking audit; §15b
 coverage judgment; v1 parity output verbatim}

## Cross-Era Consistency

{overlap years, era-boundary continuity, cross-year NULL sweep results}

## Transform Logic Risks

{table: risk | severity | details — one row per Step 7 item + Step 5b}

## Required Fixes

### Fix {N}: {title}
- **Severity**: HIGH / MEDIUM / LOW
- **Issue**: {the data inaccuracy}
- **Evidence**: {specific bronze vs gold values / executed output, quoted}
- **Location**: {function in transform.py}
- **Suggested fix**: {what to change}

## NEEDS_JUDGMENT

### Judgment Call {N}: {title}
- **Severity if confirmed**: HIGH / MEDIUM / LOW
- **Suspicion**: ...
- **Evidence available**: ...
- **Why uncertain**: ...
- **Location**: ...
- **If confirmed, suggested fix**: ...

## Notes

{schema_hash, validation summary counts, caveats}
```

Status rules: `NEEDS FIXES` if ≥1 Required Fix; `NEEDS_JUDGMENT` if only
judgment calls; `PASS` only when both sections are empty (omit empty
sections).

---

## Important Rules

- **Do NOT edit any file other than `data-review-claude.md`.** Not the
  transform, not gold, not the contract, not the manifest.
- **Be specific** — every finding cites files, rows, and values.
- **Quote bronze before concluding** — every spot-check verdict carries the
  bronze evidence it rests on.
- **Route uncertainty to NEEDS_JUDGMENT**, never silently drop a suspicion.
- **Check ALL eras** — data-loss bugs cluster at era boundaries.
- **Don't re-run the validator's checks by hand** — read `_validation.json`;
  your job is what code can't see.
- The Codex review (`data-review-codex.md`) follows the contract in
  `docs/codex-review-contract.md` and has no NEEDS_JUDGMENT section; both
  reports' `## Required Fixes` schemas are identical so the fix loop can
  dedupe across them.
