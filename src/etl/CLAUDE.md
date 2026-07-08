# ETL (Data Cleaning) — Agent Instructions

> `AGENTS.md` is a symlink to this file — edit `CLAUDE.md` only.
> This is the top-level guide for `src/etl/`. Domain-specific conventions live
> in `src/etl/education/CLAUDE.md`. The authoritative gold-cleaning rules live
> in the **`data-cleaning-standards`** skill — read it before writing or
> reviewing a `transform.py`.

## What this is

The bronze→gold pipeline: Python (polars) scripts that read raw source files
from **bronze** and emit cleaned, contract-described **gold** Parquet in a star
schema. Each topic has its own `transform.py`; the heavy lifting is shared via
`src/utils/`.

**Cardinal rule: never edit gold data directly.** All changes go through the
topic's `transform.py`; re-run it (it re-emits the contract and self-validates)
after every edit. **Data quality > code quality.**

## Directory layout

```
src/etl/
├── build_demographics_dimension.py     # global demographics dim
├── build_counties_dimension.py         # global counties dim (county FIPS)
├── crosswalks/                          # crosswalk build scripts
│   ├── build_facility_to_county.py     # ICE/HIFLD facility -> county FIPS
│   └── build_ori_to_county.py          # FBI ORI -> county FIPS
├── criminal_justice/                    # main_topic (county grain)
│   ├── CLAUDE.md                        # ← domain conventions
│   └── {sub_topic}/{topic}/            # download.py + transform.py per topic
└── education/                           # main_topic
    ├── CLAUDE.md                        # ← domain conventions (read this)
    ├── build_dimensions.py             # districts + schools dims
    ├── gosa/                           # sub_topic (46 topics)
    │   ├── _educator_lookups.py        # shared helpers (underscore-prefixed)
    │   ├── _enrollment_subgroup_programs_shared.py
    │   └── {topic}/transform.py        # one per topic
    └── georgiainsights/                # sub_topic (21 topics)
        ├── _charter_district_promotion.py
        ├── _enrollment_race_lookups.py
        └── {topic}/transform.py
```

Path convention (matches bronze/gold/contracts):
`src/etl/{main_topic}/{sub_topic}/{topic}/transform.py`. A topic dir also
collects its review artifacts (`data-review-claude.md`, `data-review-codex.md`).
**Underscore-prefixed modules** (`_*.py`) are shared bronze/lookup logic for a
family of related topics — add shared logic there, not duplicated per topic.

## Run a transform

```bash
uv run python -m src.etl.education.gosa.act_scores.transform   # run one topic (self-validates)
uv run python scripts/validate_topic.py education act_scores   # re-run the generic validator only
uv run python -m src.etl.education.build_dimensions            # rebuild districts + schools dims
uv run python -m src.etl.build_demographics_dimension         # rebuild the global demographics dim
uv run python -m src.etl.build_counties_dimension             # rebuild the global counties dim
```

A transform exits **non-zero** on any validation failure. Most topic work is
driven by the pipeline skills (`/full-pipeline`, `/transform-topic`,
`/fix-from-reviews`, `/batch-pipeline`) — see the repo-root `CLAUDE.md`
workflow table.

## Anatomy of a `transform.py`

`main()` is the standard pipeline (see `gosa/act_scores/transform.py` for a
fully-worked example). The shape:

1. **Declare config** — `TOPIC`, `BRONZE_DIR`, `GOLD_DIR`, `STANDARD_COLUMNS` (gold column order), `TARGET_TYPES`, `METRIC_COLUMNS`, `NATURAL_KEYS`, and any recode maps. A `TransformManifest` is created up front.
2. **Read + transform each bronze file** — `read_bronze_file()` (with read-loss tracking), often era-detected via `detect_era_by_columns()`. Per-file functions reshape to gold columns. Record categoricals + filtered rows on the manifest.
3. **Harmonize + concat** — `harmonize_columns(dfs, STANDARD_COLUMNS, TARGET_TYPES)` then `pl.concat`.
4. **Collision guard → dedup** — `assert_no_natural_key_collisions()` raises on duplicate keys with divergent metrics (an alias/aggregation bug, never silently deduped); then `deduplicate_by_detail_level()`.
5. **Geography nulling + §4b masks** — `null_aggregate_geography()` (state/district rows get NULL geography keys); NULL provably-impossible values (rows + counts preserved, masked counts recorded on the manifest).
6. **Manifest stats + export** — `record_gold_from_dataframe()`, `compute_metric_stats()`, `export_to_parquet()` (year-partitioned, splits by detail level, drops `detail_level`), `manifest.write()`.
7. **Emit the contract** — `write_data_dictionary()` projects the in-code column declaration into the ODCS contract. Per metric column author `unit` (+ optional `value_min`/`value_max`/`null_meaning`), the single `key_metric`, and `metric_component` on numerator/denominator counts. Everything else (grain, foreign keys, schema_hash, limitations, example queries) is auto-derived. The column declaration order **must** match `STANDARD_COLUMNS` minus `detail_level`.
8. **ALWAYS LAST: `run_topic_validation(GOLD_DIR)`** — validates the gold just written against the contract just emitted; raises `GoldValidationError` → non-zero exit.

## Shared utilities (`src/utils/`)

Transforms should reuse these rather than re-implement. Key modules:

| Module | What it gives you |
|--------|-------------------|
| `readers.py` | `read_bronze_file` (CSV/XLS/XLSX, read-loss accounting), `list_bronze_files`, `extract_year_from_filename`, `parse_school_year` / `format_school_year`. |
| `transformers.py` | The transform toolkit: `TransformManifest` (+ `RowCountTracker`, `MetricStats`, `CategoricalMapping`), `harmonize_columns`, `validate_output`, `export_to_parquet`, `assert_no_natural_key_collisions`, `deduplicate_by_detail_level`, `aggregate_demographic_collisions`, `null_aggregate_geography`, `detect_era_by_columns`, `title_case_name`. |
| `metadata.py` | `write_data_dictionary()` — the contract-emission entry point transforms call. |
| `contract_emitter.py` | Projects the column declaration → ODCS contract (roles, units, range checks, grain, key-metric, foreign keys, `schema_hash`). Don't call directly — go through `write_data_dictionary`. |
| `contract_reader.py` | Reads a contract back into validator/API config (`derive_type_spec`, `derive_topic_config`, `grain_columns`, `quality_sql_entries`). The validator derives **everything** from the contract — no per-topic `validate.py`. |
| `validators.py` | `run_topic_validation` + the `ValidationRunner` and the individual checks (schema↔contract↔parquet, types, percentage scale, geography nulling, ID formatting, grain uniqueness, contract quality SQL, FK integrity, vocabulary, null-rate spikes). `GoldValidationError` is the non-zero-exit signal. |
| `crosswalks.py` | `add_census_district_code()` (district → 5-digit Census ID), `DISTRICT_NAME_OVERRIDES`; `add_county_fips()` (county name → 5-digit FIPS), `COUNTY_NAME_OVERRIDES`; name normalization. |
| `demographics.py` / `grades.py` / `subjects.py` / `vocabulary.py` | Canonical vocabularies + normalization expressions (`normalize_demographic_column`, `normalize_grade_column`, `apply_subject_normalization`, `vocabulary_violations`). |
| `dimension_contract_emitter.py` | Builds/emits the 4 dimension contracts (districts/schools/demographics/counties). |
| `bronze.py` / `s3.py` | Bronze fetch/upload + the R2 (S3-compatible) client used for object-store writes. |
| `result_cache.py` | Shared LRU used by the API/MCP result caches (not ETL — lives here as common infra). |

## The transform manifest

Every transform emits `_transform_manifest.json` via `TransformManifest`:
categorical recode maps (bronze→gold, with unmapped detection), per-year row
counts, read-loss events, filtered/masked-row events, and metric summaries.
`/data-review-claude` reads it for 100% categorical verification, so **record
every recode, filter, and mask** on the manifest as you go.

## Blocking integrity gates

These **halt** (non-zero exit / hard error), they don't warn:

- Stale bronze checksums or **unanalyzed bronze files** (`scripts/check_bronze_freshness.py`).
- Any categorical with `unmapped_count > 0` in the manifest.
- Any failing validation check — `run_topic_validation` exits non-zero.
- A missing expected bronze column (an unmatched source column silently NULLs in gold — the most common data-loss bug; guard with an explicit `_require_columns`-style check).
- Natural-key collisions with divergent metrics.

## Gold data model (recap — full spec in `data-cleaning-standards`)

- **Fact tables:** `year` + geography FKs (`district_code`/`school_code`) + `demographic` (if applicable) + categoricals + metrics. **No names, labels, or census IDs** — those live in dimensions. Natural keys only (no surrogate ints).
- **Dimension tables:** single non-partitioned Parquet under `data/gold/_dimensions/` (global) and `data/gold/{main_topic}/_dimensions/` (domain).
- **Demographics are mutually exclusive within a category;** the `all` row is the only overlap. Publish the split pair OR the combined rollup, never both.
- Year-partitioned fact Parquet under `data/gold/{main_topic}/{topic}/year=YYYY/`. No empty Parquet files.

## Known-bad vs extreme-but-conceivable

Impossible values (e.g. ACT > 36, proportion outside `[0,1]`) → **NULL the cell,
preserve the row, record the masked count** on the manifest. Extreme-but-real
values are preserved and documented in the contract. See
`data-cleaning-standards` §4b.

## Working in here

- **New topic:** create the `{topic}/transform.py`, follow the pipeline shape above and the `data-cleaning-standards` skill, run it (self-validates), then `/data-review-claude` + `data-review-codex`, then `/approve-topic`. The API + MCP pick it up on restart.
- **Schema change:** edit `transform.py` (units / quality checks), re-run (rewrites gold, re-emits contract, re-validates), bump contract `version` if breaking, check API impact (`src/api/`).
- **Adding a column:** verify it exists in bronze; add to `STANDARD_COLUMNS` + `TARGET_TYPES`. **Renaming a column:** update any API endpoint referencing the old name.
- **Dimension change:** edit `build_dimensions.py` / `build_demographics_dimension.py`, rebuild, verify fact FK columns still match dim PKs, re-emit dimension contracts (`scripts/generate_dimension_contracts.py`), run `scripts/check_referential_integrity.py`.
- **Geography crosswalk fix:** add the name to `DISTRICT_NAME_OVERRIDES` in `src/utils/crosswalks.py`, then rebuild dimensions. The crosswalk data itself (`data/gold/crosswalks/ga_census_crosswalk.parquet`) is a maintained artifact — there is no build script.
- **Education domain specifics** (fact key columns, detail levels + geography nulling, ID formatting, pseudo-district codes, cross-topic naming, percentage-scale exceptions): `src/etl/education/CLAUDE.md`.
