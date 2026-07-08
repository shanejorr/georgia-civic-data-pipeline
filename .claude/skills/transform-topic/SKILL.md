---
name: transform-topic
description: Author transform.py for a data topic from bronze-data-structure.md and the data-cleaning standards, run it, and self-review against the shared checklist. The transform emits gold parquet, the ODCS contract, the manifest, and validates itself.
argument-hint: "[main_topic] [sub_topic] [topic]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
---

# Transform a data topic from bronze to gold

The purpose of the transform code is two-fold:

1. Data Quality — the gold data must accurately reflect the bronze data
2. Clean Code — the transformation code should be clean and run efficiently

Purpose number 1 (data quality) is the most important.

A successful run of `transform.py` produces, in one pass: the gold parquet,
the ODCS contract, the human README, `_transform_manifest.json`, and a passing
`_validation.json` — the transform validates itself as its last act and exits
non-zero on any failure.

## Input

Arguments: `$ARGUMENTS` (format: `[main_topic] [sub_topic] [topic] [--allow-stale-bronze]`)

Example: `education gosa act_scores`

**Derived paths:**
- Bronze: `data/bronze/$0/$1/$2/`
- Gold: `data/gold/$0/$2/`
- Script: `src/etl/$0/$1/$2/transform.py`
- Contract (emitted): `contracts/$0/$2.odcs.yaml`

---

## Prerequisite: bronze freshness gate

```bash
uv run python scripts/check_bronze_freshness.py $0 $1 $2
```

- Exit 0 → proceed.
- Exit 2 (no structure doc) → **stop**: tell the user to run `/bronze-data-structure $0 $1 $2` first.
- Exit 1 with CHANGED/MISSING → **stop** unless the user passed `--allow-stale-bronze` (then re-run the script with `--allow-stale` and proceed with its warning visible).
- Exit 1 with UNANALYZED files → **always stop**: new bronze files must go through `/bronze-data-structure` before any transform ingests them. There is no override.

---

## Step 1: Read Context

Read in order:

1. **`data/bronze/$0/$1/$2/bronze-data-structure.md`** (required) — eras, columns, sample data, categorical inventories, suppression markers, detail levels, year representation. This replaces manual bronze exploration; do not re-explore bronze from scratch. (Spot-reading a bronze file to resolve a specific ambiguity is fine.)
2. **`src/etl/$0/CLAUDE.md`** — domain conventions: fact key columns, detail levels, ID formatting, output filenames, excluded columns.
3. **`.claude/skills/data-cleaning-standards/SKILL.md`** — universal rules. Pay particular attention to §4a (units), §4b (known-bad NULLing), §4c (key metric + numerator/denominator), §5a/§5b (demographic exclusivity, Asian/PI), §15b (required quality checks), §16 (canonical vocabulary).
4. **Reference implementation** — the most similar completed transform: same sub_topic first (`src/etl/$0/$1/*/transform.py`), then same main_topic. Prefer consistency with existing transforms. If none exists yet (early in a rebuild), skip this — the v1-consult rules below are the fallback.
5. **Shared utilities** — `src/utils/readers.py`, `src/utils/transformers.py`, `src/utils/demographics.py`, `src/utils/grades.py`, `src/utils/subjects.py`, `src/utils/metadata.py`, `src/utils/validators.py` (the `run_topic_validation` entry point).

### Consulting the v1 transform (reference only)

A previous-generation transform for this topic exists in git history at the
`v1-pipeline` tag. **Author this transform fresh from the structure doc and
standards — never copy the v1 file wholesale.** Consult it only when stuck on
a *source quirk* the structure doc leaves ambiguous — an era-routing edge
case, a known Asian/PI determination, a documented §4b mask, a dedup
tie-break rationale:

```bash
git show v1-pipeline:src/etl/$0/$1/$2/transform.py | less
```

When you adopt a v1 decision, re-verify it against bronze (don't trust it
blindly) and document the decision in your own words.

---

## Step 2: Design the Pipeline

- **Single pipeline with conditional logic** when era differences are minor (column renaming only); **separate functions per era** when formats differ fundamentally (wide vs. long, compound IDs).
- **Era detection by column signature** (`detect_era_by_columns`), most-specific signature first. Year ranges only as fallback.
- **Decide the dedup tie-break now**: which row wins when overlapping bronze files cover the same key, and why. This becomes the explicit `sort_col` argument and a code comment.
- **List the topic's cross-column invariants** (§15b shapes: partition sums, co-null rules, component totals, structural facts). These become `quality_checks=` entries in Step 5.

---

## Step 3: Script Structure

Create `src/etl/$0/$1/$2/transform.py` and `__init__.py`.

```python
# 1. Configuration: TOPIC, BRONZE_DIR, GOLD_DIR
# 2. Normalization maps (topic-specific categoricals)
# 3. STANDARD_COLUMNS (output order), TARGET_TYPES, METRIC_COLUMNS, NATURAL_KEYS
# 4. Era-specific transform functions (receive manifest)
# 5. transform_file() — detect era, route, record to manifest
# 6. main() — full pipeline (Step 5 skeleton), ending in run_topic_validation
```

Required imports follow the reference implementation plus:

```python
from src.utils.transformers import assert_no_natural_key_collisions
from src.utils.validators import run_topic_validation
```

Column naming priority: shared-utility names (`demographic`) → domain CLAUDE.md → §16 canonical vocabulary → descriptive snake_case. Output order: `year`, geography keys, `demographic` (if applicable), categoricals, metrics.

---

## Step 4: Transformation Rules

Apply all rules from **data-cleaning-standards** and the **domain CLAUDE.md**. Topic-specific decision areas:

### 4.1 Column rename coverage verification

After building a rename mapping, verify all expected metric columns were matched — unmatched source columns silently become NULL in gold (the most common data-loss bug). Log an error listing missing + unmatched columns per year.

### 4.2 Optional columns

When a metric may be absent in some years: if present, cast; else `pl.lit(None).cast(...)` **with a log line** — the fallback firing can indicate a rename bug, not a genuinely absent column.

### 4.3 Read-loss accounting

Every bronze read uses `read_bronze_file(path, return_loss=True)`; pass the loss dict to `manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])`. If a real loss shows up, **investigate before proceeding** — a truncated file is a data problem, not a logging problem. A legitimate cause (quoted multi-line CSV fields) is recorded with a `note=`.

### 4.3a Recording the demographic categorical

`record_categorical()` needs a map dict, but demographics use the shared
`DEMOGRAPHIC_ALIASES` (never a topic-local map). Record the **effective
slice**: `{label: DEMOGRAPHIC_ALIASES[label.upper()] for label in observed}`
— keeps `map_used` reviewable (the aliases actually hit, not all ~200) while
preserving the unmapped guard.

### 4.3b All-string bronze reads

For CSV bronze with sentinel strings (`ALL`, `TFS`) and zero-padded codes,
read with `read_bronze_file(..., infer_schema_length=0)` (all columns Utf8)
and cast explicitly — schema inference on such files mis-types columns and
strips leading zeros.

### 4.3c Reclassified rows

When a row's detail level or identity is repaired in place (e.g. a bronze
aggregate mislabeled as a school row), record it via
`manifest.record_reclassified(year, count, reason)` so the repair is a
manifest artifact the review can verify, and document the evidence in the
docstring.

### 4.4 Demographic subgroup collisions

When multiple raw labels normalize to one canonical value, aggregate explicitly with `aggregate_demographic_collisions()` **before** dedup — sum counts, weighted-average rates/scores. Never let dedup resolve semantically distinct rows.

### 4.5 Asian / Pacific Islander conflation

Bare bronze `"Asian"` does NOT automatically mean Asian-only (§5b). If bronze has only 6 race buckets with no separate Pacific Islander row anywhere, run the math test (state-level race-bucket sum vs cohort total; equality ⇒ combined bucket). Fix pattern: topic-local remap of the label to `"Asian/Pacific Islander"` **before** `normalize_demographic_column()`. Never edit `DEMOGRAPHIC_ALIASES` globally; never emit a rollup row alongside split rows (§5a).

### 4.6 Deduplication with overlapping bronze files

Call `assert_no_natural_key_collisions(combined, natural_keys=..., metric_cols=...)` first — it raises when duplicate keys carry *divergent* metrics (alias collapse, unaggregated collisions). Then `deduplicate_by_detail_level(..., sort_col=<explicit choice>)` with a two-line comment stating the tie-break rule and why (e.g. "newer era wins via _source_year; older files republish identical rows").

**All-null placeholder twins.** The guard counts NULL as a divergent value, so the common bronze pattern of a renamed entity carrying a second, all-null-metrics row under the same key will hard-fail the guard even though dedup's `sort_col` would resolve it. The sanctioned fix: drop the all-null twin **explicitly before the guard** — filter rows where every metric is NULL AND a same-key row with data exists, log the count, and record it via `manifest.record_filtered(year, n, "all_null_placeholder_twin")`. Never widen the guard or skip it.

### 4.7 Known-bad values (§4b)

Impossible values (outside the metric's defined scale) → NULL via a `_null_*` helper in `main()` — after harmonize/dedup/geography-nulling, **before** manifest stats and export — with the mask recorded via `manifest.record_masked(column, count, reason, years=[...])`, logged, and documented in the column's contract `description`. Keep the contract range guard so the check stays enforceable. Extreme-but-conceivable values are preserved + documented instead.

### 4.8 Manifest recording

`transform_file()` records file info + bronze counts; era functions call `manifest.record_categorical()` after every `replace_strict()` (including demographics, grades, subjects). Do NOT call `record_gold` per file — gold counts come from the final DataFrame in `main()`. `manifest.write()` raises on any unmapped categorical.

### 4.9 Key-metric designation (§4c)

Decide the topic's **headline metric** and mark it in the `columns=[...]` declaration (the emitter raises unless exactly one is set):

- `"key_metric": True` on the single metric most users want given the description — a score/proportion over a count, the most granular over a category derived from it; a count only when the topic *is* a headcount (e.g. enrollment). For a categorical headline with no underlying numeric, also set `"key_metric_categorical": True`.
- `"metric_component": "numerator"`/`"denominator"` on the **count** columns composing the key metric when it is a rate/average: a rate (`proportion`/`ratio`) flags both numerator + denominator counts; an average (`score`/`rating`/`percentile`) flags only the N it averages over as `denominator`; a `count`/`currency` headline flags none.
- `key_metric_grain_contributor` is auto-derived from the grain — never author it.

---

## Step 5: Pipeline Orchestration (`main()`)

```python
def main() -> None:
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)
    all_dfs = []

    # 1. Read + transform each bronze file (read-loss accounted)
    for path in list_bronze_files(BRONZE_DIR):
        year = ...  # per the structure doc's year-representation rules
        df = transform_file(path, year, manifest)
        if df is not None and df.height > 0:
            all_dfs.append(df)

    # 2. Harmonize + concat across eras
    all_dfs = harmonize_columns(all_dfs, STANDARD_COLUMNS, TARGET_TYPES)
    combined = pl.concat(all_dfs)

    # 3. Collision guard, THEN dedup with an explicit, documented tie-break
    assert_no_natural_key_collisions(combined, NATURAL_KEYS, METRIC_COLUMNS)
    combined = deduplicate_by_detail_level(
        combined, school_keys, district_keys, state_keys, sort_col="<explicit>"
    )

    # 4. Geography nulling (shared rules), §4b masks, pre-export sanity
    combined = null_aggregate_geography(combined, "detail_level",
        EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"])
    combined = _null_<topic_specific_masks>(combined)   # §4b, if any
    validate_output(combined, required_non_null=["year"])

    # 5. Manifest stats on the FINAL DataFrame, then export
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, STANDARD_COLUMNS)
    manifest.write(GOLD_DIR)

    # 6. Emit the contract + README. Each metric column carries "unit"
    #    (+ value_min/value_max where bounded). EXACTLY ONE column carries
    #    "key_metric": True — the single headline metric (§4c); the count
    #    columns composing a rate/average key metric carry
    #    "metric_component": "numerator"/"denominator". quality_checks=
    #    carries the topic's cross-column invariants (§15b) — REQUIRED
    #    wherever the shapes apply; a topic with genuinely none documents
    #    why in the module docstring. For a source with NO suppression, pass
    #    suppressed_to_null=False so the contract doesn't claim NULL means
    #    "suppressed".
    write_data_dictionary(
        output_dir=GOLD_DIR, name=TOPIC, description=...,
        columns=[
            # ...key columns...
            {"name": "num_tested", "type": "int64", "unit": "count",
             "metric_component": "denominator", "description": ...},
            {"name": "avg_score", "type": "float64", "unit": "score",
             "value_min": 1, "value_max": 36, "key_metric": True,
             "description": ...},
        ],
        source=..., year_range=(min_year, max_year),
        quality_checks=[
            # e.g. partition-sums-to-one, co-null rules, component totals,
            # school_code_always_null for district-only topics, ...
        ],
    )

    # 7. ALWAYS LAST: validate against the contract just emitted.
    #    Raises GoldValidationError -> transform exits non-zero.
    run_topic_validation(GOLD_DIR)
```

---

## Step 6: Run and Verify

```bash
rm -rf data/gold/$0/$2          # transform owns its gold dir; no stale partitions
uv run python -m src.etl.$0.$1.$2.transform
```

**Exit 0 means**: gold written, manifest written with zero unmapped
categoricals, contract emitted, and **all validation checks passed**
(schema↔contract↔parquet conformance, units/scale, grain uniqueness, the
topic's own quality SQL, FK integrity against dimensions, vocabulary,
geography nulling). If it exits non-zero, read the error: fix the transform
(or, for an FK failure, check whether the dimension build is stale) and
re-run. Never weaken a check to make it pass.

Then sanity-check beyond what code enforces:

1. Row counts and expansion factors are explainable from the structure doc
2. Per-year NULL-rate spikes (warnings in the validation report) have a documented cause
3. Spot-compare 2–3 rows against the bronze source
4. The dedup log line ("Deduplicated N rows") matches expectations from overlap analysis

## Step 7: Self-review against the checklist

Read `.claude/skills/data-cleaning-standards/code-review-checklist.md` and
verify the new transform against every item (PASS/FAIL/N/A). Fix FAILs before
declaring the step complete. This is the code-quality gate; data accuracy is
the data review's job.

---

## Vectorized Operations

Always prefer native Polars expressions (`replace_strict`, `pl.when/then`,
`.str` namespace, casts with `strict=False`) over `map_elements()` UDFs.
`map_elements()` is acceptable only for multi-column logic inexpressible with
`pl.when().then()`.

## Code Comments

Two-line comments (what + why) for: column mapping logic, detail-level
detection, ID formatting, era quirks, filtering decisions, demographic
handling, the dedup tie-break, and every §4b mask.

## Common Pitfalls

- Hardcoded year ranges for era detection — use column inspection
- Silent NULL from unmatched renames — log fallback paths
- Dedup tie-break discarding non-NULL data from the losing row — prefer the most complete row or merge
- Demographic collisions resolved by dedup instead of aggregation
- `replace_strict(MAP, default=None)` + `coalesce` producing uncontrolled values — log fallback hits
- Not validating after joins (joins can drop or duplicate rows)
- Forgetting that `export_to_parquet()` drops `detail_level` — never carry it in STANDARD_COLUMNS-minus-export expectations

## Ask Questions

If unsure whether a transformation should occur or how, ask (or in
non-interactive batch mode: record the question as a judgment item and choose
the conservative option — preserve bronze granularity). Do not guess.
