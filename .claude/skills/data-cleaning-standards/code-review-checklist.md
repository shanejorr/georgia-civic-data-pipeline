# Code Review Checklist for `transform.py`

Canonical checklist for reviewing a `transform.py` script. Both `/transform-topic` (post-authoring self-review) and `/review-transform` use this list, so a transform that passes one must pass the other. Do not duplicate or fork it — update this file if a check changes.

For each check below, record **PASS / FAIL / N/A**. When marking FAIL, include the file/line location and a concrete suggested fix. N/A is reserved for checks that genuinely do not apply to the topic (see "Scope notes" at the end).

---

## Shared Utilities

- [ ] Uses `TransformManifest` from `src.utils.transformers` (not bare `RowCountTracker`)
- [ ] Uses `DEMOGRAPHIC_ALIASES` from `src.utils.demographics` (not hardcoded demographic mappings)
- [ ] Uses `harmonize_columns` from `src.utils.transformers`
- [ ] Uses `validate_output` from `src.utils.transformers`
- [ ] Uses `export_to_parquet` from `src.utils.transformers`
- [ ] Uses `deduplicate_by_detail_level` from `src.utils.transformers` with an **explicit `sort_col`** (the tie-break is a documented decision, never the default), preceded by `assert_no_natural_key_collisions()` so alias-collapse fails loudly instead of being resolved silently by dedup
- [ ] Uses `write_data_dictionary` from `src.utils.metadata`
- [ ] Uses `read_bronze_file(..., return_loss=True)` from `src.utils.readers` (not raw polars/pandas reads) and records the loss via `manifest.record_read_loss()`
- [ ] `main()` ends with `run_topic_validation(GOLD_DIR)` from `src.utils.validators`, placed after `write_data_dictionary()` (validates against the contract the run just emitted; raises on failure)
- [ ] **Grade columns** — if the transform produces a `grade_level` column, it uses `normalize_grade_column` / `GRADE_LEVEL_MAP` from `src.utils.grades` (not a topic-local map)
- [ ] **Subject columns** — if the transform produces a `subject` column, it passes values through `apply_subject_normalization` / `SUBJECT_NORMALIZATION_MAP` from `src.utils.subjects` after the topic-local map
- [ ] Calls `manifest.record_categorical()` for each categorical recoding applied (including the shared grade/subject normalizers)
- [ ] Calls `manifest.compute_metric_stats()` before export
- [ ] Calls `manifest.write()` to emit `_transform_manifest.json`

## Code Quality

- [ ] Era detection uses column inspection (`detect_era_by_columns`), not hardcoded year ranges
- [ ] All filters log removed count + sample values
- [ ] Numeric casts use `strict=False` (so suppressed values become null)
- [ ] **Known-bad / out-of-range values are NULLed and documented (§4b).** Values that are *impossible* on the metric's defined scale (e.g., an ACT score > 36, a bounded proportion outside [0,1] that isn't a `ratio`, a star rating off its scale, a negative count) are set to NULL — same convention as suppression, row and other valid columns preserved — before validate/manifest/export, with the masked count logged and the handling documented in the contract column `description`. The column keeps its `value_min`/`value_max` (or `unit` bounds) so the range check stays enforceable. *Extreme-but-conceivable* values (within the possible domain, e.g. `participation_rate` slightly > 1 from transfers-in) are instead preserved + documented. Silently keeping an impossible value, or dropping the whole row, is a FAIL.
- [ ] Column rename coverage verification exists (logs unmatched columns)
- [ ] Uses native Polars operations (no `map_elements()` UDFs)
- [ ] Includes two-line comments (what + why) for non-obvious logic
- [ ] **Asian / Pacific Islander mapping is correct for this source.** If bronze has only 6 race buckets (no separate Pacific Islander column/row), the bare label "Asian" likely represents the pre-1997 OMB combined Asian + Pacific Islander bucket — the transform must remap to `asian_pacific_islander`, not `asian`. Verify by inspecting the bronze structure report and (for count metrics) running the math test: race-bucket sum at a state row should equal the cohort total. See `data-cleaning-standards` skill §5b.

## Pipeline Standards

- [ ] `STANDARD_COLUMNS` list defines output column order
- [ ] `main()` follows the standard pipeline: list files → transform → harmonize → deduplicate → validate → export → metadata
- [ ] Emits the ODCS contract (`contracts/{main}/{topic}.odcs.yaml`) and `README.md` via `write_data_dictionary`; each metric column dict sets a `"unit"` key (`count | proportion | ratio | score | rating | currency | percentile`; unclassifiable columns none)
- [ ] NULL rate spike check runs via `check_null_rate_spikes()` from `src/utils/validators.py` (do not reimplement inline)
- [ ] **Cross-topic column names match the canonical vocabulary (§16):** `subject` (not `content_area`) for assessed academic content; `test_component` only for SAT/ACT-style test sections; `grade_level` (not `grade`) for academic grade with zero-padded 2-char string values; `ccrpi_flag` with descriptive values (`green` / `green_star` / `yellow` / `red`); `target` (not `ccrpi_target`) inside CCRPI topics; `num_received_sgp` (not `n_received_sgp` / `number_received_sgp`); FESR sibling schemas use `fte_enrollment`, `per_pupil_expenditure`, `federal_per_pupil_expenditure`, `state_local_per_pupil_expenditure`, `ccrpi_single_score`, `fesr_star_rating`; proficiency-threshold metrics use `_or_above` (not `_and_above`); rate metrics drop redundant `_pct` suffix (e.g., `dropout_rate`, not `dropout_rate_pct`).
- [ ] **Each metric column carries the right `unit` marker** (§4a): in `write_data_dictionary`, set `"unit": "proportion"` for percentage columns that must be 0–1, or `"unit": "ratio"` for columns divided by 100 from a 0–100 source that may legitimately exceed 1; use `count` / `score` / `rating` / `currency` / `percentile` for non-percentage metrics; unclassifiable columns omit the key. Optional `value_min` / `value_max` pin a bounded range (ACT 1–36, star ratings 1–5, percentile 0–100 are the safe bounded cases; variable-range scores omit bounds). The emitter writes this to the contract's `unit` custom property and the generic validator derives the entire validation config — types, metric/categorical lists, bounded/ratio split, exemptions — back from the contract (§15a). There are no per-topic validate.py files.
- [ ] **The key metric and its components are declared** (§4c): exactly one column in `write_data_dictionary` sets `"key_metric": True` — the single metric most users want given the description (a score/proportion over a count, the most granular over a category derived from it; a count only when the topic *is* a headcount). The count column(s) composing a rate/average key metric carry `"metric_component": "numerator"` / `"denominator"` (and are `unit: count`): a rate flags numerator + denominator, an average flags only its N as denominator, a count/currency headline flags none. The emitter **raises** if a metric table declares ≠1 `key_metric`; `key_metric_grain_contributor` is auto-derived — do not author it.
- [ ] **Cross-column invariants are authored as `quality_checks=`** (§15b): every partition-sums-to-one family, co-null relationship (flag ⇒ metric NULL), component-reconciles-to-total, and structural fact (e.g. always-NULL school_code) the reviewer would otherwise verify by hand. Checks are NULL-guarded and self-scope by geography NULL-ness when level-specific. A topic with none of these shapes records why in the transform docstring.
- [ ] **Proficiency band columns use the canonical pair** (§16): `pct_<level>_learner` / `num_<level>_learner` for the four-level Beginning / Developing / Proficient / Distinguished breakdown. Topics emitting the bands also emit cumulative `pct_developing_learner_or_above` and `pct_proficient_learner_or_above`. No `<level>_pct`, `<level>_learner_pct`, or `level_<n>_<level>_<…>` variants.
- [ ] **`subject` is academic content only** (§16 "Assessment subject"). Metric-family blocks like `sgp_*`, `reading_status`, or Lexile are folded into the parent academic-subject row at transform time, not emitted as separate `subject` values.
- [ ] **Racial demographics are mutually exclusive within a topic** (§5a). Split-convention topics emit only `asian` and `pacific_islander` rows; combined-convention topics emit only `asian_pacific_islander` rows. Never synthesize a rollup row alongside the split sources — that double-counts the Pacific Islander population. Cross-topic comparability between the two conventions is the analyst's responsibility at query time.
- [ ] **Education fact tables include the standard key shape**: `year`, `district_code`, `school_code` (in that order, even when `school_code` is always NULL for district-only topics like `salaries_and_benefits`). Don't omit `school_code` just because the topic has no school-level data.
- [ ] **The `write_data_dictionary` `columns=[...]` order matches the Parquet column order.** It must iterate `STANDARD_COLUMNS` (minus `detail_level`) in order — the contract `schema[0].properties[]` is emitted from it and the validator's `contract_parquet_schema` check compares parquet against it. Any rearrangement breaks API consumers that pair columns by index.

## Optimization

- [ ] **Vectorized operations**: All row-level transformations use Polars expressions (`.with_columns()`, `.select()`, `pl.when().then().otherwise()`) rather than Python-level loops, `.iter_rows()`, `.apply()`, or `map_elements()`
- [ ] **Expression chaining**: Multiple column transformations on the same DataFrame are batched in a single `.with_columns()` call rather than chained as separate `.with_columns()` calls (allows Polars to parallelize)
- [ ] **Function decomposition**: Transform logic is broken into well-named functions (one per era at minimum). No single function exceeds ~80 lines. Helper functions are used for repeated patterns (e.g., a shared normalization step used across eras)
- [ ] **No redundant scans**: The same bronze file is not read multiple times. The same gold DataFrame is not filtered repeatedly when a single `group_by` or `partition_by` would suffice
- [ ] **Efficient filtering**: Filters that reduce row count significantly are applied early in the pipeline (before expensive operations like joins or unpivots)
- [ ] **Lazy evaluation where beneficial**: For large or complex transforms, uses `scan_parquet()` / `.lazy()` with a single `.collect()` at the end rather than multiple eager operations on large intermediate DataFrames
- [ ] **No unnecessary copies**: Avoids patterns like `df = df.clone()` or converting to/from pandas for operations that Polars handles natively
- [ ] **String operations**: Uses Polars `.str` namespace methods (`.str.replace()`, `.str.to_lowercase()`, `.str.strip_chars()`) rather than Python string methods via `map_elements()`
- [ ] **Mapping dictionaries**: Uses `pl.col().replace()` or `replace_strict()` for value mapping rather than chained `pl.when()` expressions when there are more than 3-4 cases
- [ ] **DRY across eras**: Shared logic between era functions is extracted into helper functions rather than copy-pasted. Era-specific differences are isolated to config dicts or small conditional blocks

## Scope notes — when a check is N/A

- If the topic has no demographics → skip the `DEMOGRAPHIC_ALIASES` check
- If the topic has only one era → skip the era detection check
- If the topic has no overlapping source files → `deduplicate_by_detail_level` may not be needed, but should still be present as a safety net
- Lazy evaluation is only recommended when DataFrames exceed ~100K rows or the pipeline has many intermediate steps
