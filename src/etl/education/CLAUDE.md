# Education ETL — Domain Conventions

Education-specific conventions for `transform.py` scripts. These supplement the universal standards in the `data-cleaning-standards` skill.

---

## Fact Table Key Columns

Education fact tables use these key columns (always in this order, before any topic-specific columns):

| Column | Type | Description |
|--------|------|-------------|
| `year` | `pl.Int32` | Ending calendar year (e.g., 2024 for "2023-2024") |
| `district_code` | `pl.Utf8` | GOSA district code (FK to districts dimension) |
| `school_code` | `pl.Utf8` | GOSA school code (FK to schools dimension) |

The `demographic` column (FK to global demographics dimension) follows geography keys when the topic has demographic breakdowns. See `data-cleaning-standards` skill for demographic rules.

**District-only topics still include `school_code`.** When bronze publishes only district and state-level rows (e.g., `salaries_and_benefits`), the fact table still emits a `school_code` column — always NULL — so every education fact table shares the same key-column shape. Add it via `pl.lit(None).cast(pl.Utf8).alias("school_code")` in each per-file transform before the final `.select(STANDARD_COLUMNS)`. Do not drop the column just because the topic has no school-level data.

---

## Detail Levels and Geography Nulling

Three detail levels: `"school"`, `"district"`, `"state"`.

| Detail Level | `district_code` | `school_code` |
|-------------|-----------------|----------------|
| `state` | NULL | NULL |
| `district` | value | NULL |
| `school` | value | value |

Sentinel strings from bronze (`"ALL"`, `"State of Georgia"`, `"Statewide"`, `"All Systems"`) must become NULL in gold.

```python
df = df.with_columns(
    pl.when(pl.col("detail_level") == "state").then(None)
    .otherwise(pl.col("district_code")).alias("district_code"),
    pl.when(pl.col("detail_level") != "school").then(None)
    .otherwise(pl.col("school_code")).alias("school_code"),
)
```

---

## ID Column Formatting

- **District codes**: `.cast(pl.Utf8).str.zfill(3)` — pads 3-digit standard codes while preserving 7-digit charter codes, and also preserves the small allowlisted set of non-numeric pseudo-district codes (see below). **Never truncate** with `.str.slice(0, 3)`.
- **School codes**: `.cast(pl.Utf8).str.zfill(4)`

### Pseudo-district codes

A small set of non-numeric, non-3/7-digit district codes is allowlisted in `src/etl/education/build_dimensions.py` (`PSEUDO_DISTRICT_CODES`). Each must also have an entry in `HARDCODED_DISTRICTS` with an explicit `district_type`. Current members:

| Code | Name | `district_type` | Source topics |
| --- | --- | --- | --- |
| `RTC` | Residential Treatment Center | `state_special` | `ccrpi_content_mastery` (2015-2017), `ccrpi_graduation_rate` (2015-2018), `ccrpi_scoring_by_component` (2015-2017) |

The `state_special` type is reserved for these aggregated state-managed pseudo-districts.

---

## Dimension Tables

Education dimension tables are stored at `data/gold/education/_dimensions/`. These are built and maintained separately from topic fact tables.

### districts.parquet

| Column | Type | Description |
|--------|------|-------------|
| `district_code` | `pl.Utf8` | PK — 3-digit standard or 7-digit charter, zfill(3) |
| `district_name` | `pl.Utf8` | Title case |
| `district_census_id` | `pl.Utf8` | 5-digit Census school district code for cross-dataset linking (e.g., `00060`). Sourced via `src/utils/crosswalks.py`. NOT the 7-digit NCES LEA ID. |
| `district_type` | `pl.Utf8` | `standard`, `state_charter`, `commission_charter`, `state_school` (the 799-prefix Georgia state schools — Deaf/Blind), `state_agency` (state agencies that report education programs under a district code but are not schools — Depts. of Corrections `890`, Juvenile Justice `891`, Human Resources `892`, Labor `896`; no Census ID), `state_special` (pseudo-districts — see "Pseudo-district codes" above), `resa` (Regional Educational Service Agencies — service agencies in the 850–888 range; not Census-matchable districts, so `district_census_id` is NULL) |

Census ID matching uses `add_census_district_code()` from `src/utils/crosswalks.py`. Match rate should be >95%. Charter schools (7-digit codes) typically get null census IDs. Add unmatched districts to `DISTRICT_NAME_OVERRIDES` in `src/utils/crosswalks.py`.

### schools.parquet

| Column | Type | Description |
|--------|------|-------------|
| `district_code` | `pl.Utf8` | Composite PK part 1 / FK to districts dimension |
| `school_code` | `pl.Utf8` | Composite PK part 2 — 4-digit, zfill(4) |
| `school_name` | `pl.Utf8` | Title case |

**Note**: School codes are NOT globally unique — the same code (e.g., `0101`) can appear in multiple districts. The primary key is the `(district_code, school_code)` pair (district_code first — matches the dimension contract's `primaryKeyPosition` order and the on-disk parquet column order).

### Building dimensions

Run `uv run python -m src.etl.education.build_dimensions` to rebuild both tables from bronze data. The script scans all GOSA Era 3+ files (2011 onward), keeps the latest name per entity, applies title case, and adds census IDs for districts.

### Notes

- Dimension tables store the **latest name only** (no year versioning, no slowly-changing dimensions).
- The global demographics dimension (`data/gold/_dimensions/demographics.parquet`) is defined in the root `CLAUDE.md` and built via `uv run python -m src.etl.build_demographics_dimension`.

---

## Gold Output Format

Education gold data is split by `detail_level` into separate fact files per year:

```
data/gold/education/
├── _dimensions/
│   ├── districts.parquet       # District dimension table
│   └── schools.parquet         # School dimension table
├── {topic}/
│   └── year=2024/
│       ├── schools.parquet     # School-level fact rows
│       ├── districts.parquet   # District aggregate fact rows
│       └── states.parquet      # State aggregate fact rows
```

The topic's documentation and machine-readable schema is the single git-tracked
ODCS contract at `contracts/education/{topic}.odcs.yaml` — emitted directly by
the transform (see **Data Contracts** below). It carries both the schema and the
human-facing fields (`title`/`summary` at the topic level, `label`/
`short_description` per column). There is no `_metadata.json` and no per-topic
gold `README.md` (retired — the contract is the one documentation artifact).

Note: The `_dimensions/` directory name uses a leading underscore to distinguish it from topic directories.

---

## Data Contracts

Each approved education topic has a git-tracked ODCS v3.1.0 data contract at `contracts/education/{topic}.odcs.yaml`. **The contract is emitted directly by the transform** — `write_data_dictionary()` projects the transform's in-code column declaration into the contract via `src/utils/contract_emitter.py`. There is no `_metadata.json` intermediary and no separate generate step. Each metric column's semantics are authored in the transform's column declaration via a per-column `"unit"` key (vocabulary: `count | proportion | ratio | score | rating | currency | percentile`, with optional `value_min`/`value_max`; omit for unitless/exempt columns); the emitter projects it to a contract `unit` custom property and derives the range-check quality SQL from it (`proportion` → `[0, 1]`; `ratio`/`count` → `>= 0`; `score`/`rating`/`percentile` → `[value_min, value_max]` when bounds are given, percentile defaults 0–100; `currency` → no range check). The generic validator derives its entire per-topic config back from the contract (`src/utils/contract_reader.py`) — there are no per-topic `validate.py` files. Re-running the transform re-emits the contract; `scripts/generate_contracts.py` is a thin batch wrapper that re-runs every approved topic's transform. `scripts/check_contracts.py` is the CI gate: a fast lint + quality-`type` guard on every push (fact **and** dimension contracts), plus an opt-in nightly `contracts-s3` job that runs `datacontract test` against R2 gold via the S3-compatible API (schema + quality checks + check-count assertion).

The transform authors per column: `unit` (and optional `value_min`/`value_max`/`null_meaning`), plus the **key-metric** keys below. Everything else is **auto-derived** by the emitter — the row grain (native `primaryKey`/`primaryKeyPosition` + `dataGranularityDescription`), `limitations`/`null_semantics`, layout metadata, a deterministic `schema_hash`, `example_queries`, and the per-FK-column `foreign_keys` block — so there is no authoring burden for those. (`limitations`/`usage`/`example_queries` are overridable via `write_data_dictionary` kwargs only if the derived prose is insufficient.)

**Key-metric properties (per fact table).** Three properties make a table's headline metric machine-readable (full rules in `data-cleaning-standards` §4c):

- `"key_metric": True` — authored on **exactly one** column: the single metric most users want given the topic description (prefer a score/proportion over a count, the most granular over a derived category; rarely a count). The emitter **raises** unless exactly one is set on a table with metric columns, and also emits a schema-object `key_metric: <colname>` pointer. A categorical key metric (rare) needs `"key_metric_categorical": True`.
- `"metric_component": "numerator" | "denominator"` — authored on the count column(s) that compose the key metric when it is a rate/average (must be `unit: count`). Education conventions: an average's denominator is its N (`avg_score` → `num_tested`; `avg_scale_score` → `num_tested`; `sgp_median` → `num_received_sgp`); a rate's pair is its numerator + denominator (`graduation_rate` → `graduate_count` + `cohort_size`; `*_fte_rate` → `*_fte` + `total_fte`). A count, currency, or rating headline has no `metric_component`.
- `key_metric_grain_contributor` — **auto-derived** (no authoring): the grain columns that disaggregate the key metric (`demographic`, `test_component`, `grade_level`, `subject`, …) — i.e. grain minus `year` minus geography (`district_code`/`school_code`).

**Dimension contracts.** The dimension tables now have contracts too, emitted by the dimension build scripts (same pattern): `contracts/education/_dimensions/{districts,schools}.odcs.yaml` and the global `contracts/_dimensions/demographics.odcs.yaml` (re-emit with `uv run python scripts/generate_dimension_contracts.py`). The **districts** dim declares the cross-dataset link key — `district_census_id` carries a `link_key` custom property (target `census.county_fips` via the Census crosswalk; NULL for charters/RESAs/state agencies). The **schools** dim declares the composite primary key `(district_code, school_code)`. The REST API (and MCP) derive their fact→dimension joins from these contracts (composite-aware) and expose every categorical column as an independent filter — no join keys or filter lists are hardcoded in the API. **A joined dimension's enum attributes are also filterable** (`demographic_category`, `district_type`): an enum attribute on a dim contract auto-becomes a fact-query filter on every topic that joins it (resolved as a semi-join on the FK code column — see the root `CLAUDE.md` "Dimension-attribute filters"). So declaring an `enum` on a new dimension attribute is the only step needed to make it filterable.

---

## Columns NOT Stored in Fact Tables

| Column | Reason |
|--------|--------|
| `school_year` | Derivable from `year` (year 2024 → "2023-2024") |
| `detail_level` | Implicit in filename (`schools.parquet`, `districts.parquet`, `states.parquet`) |
| `district_name` | Stored in districts dimension table |
| `school_name` | Stored in schools dimension table |
| `district_census_id` | Stored in districts dimension table |

---

## Geography Identifier

School districts use **GOSA district codes** (3-digit standard like `601`, or 7-digit for charters) as the natural key (`district_code`) in fact tables. The districts dimension table additionally carries the 5-digit Census school district code (`district_census_id`, e.g., `00060`) for cross-dataset linking. The NCES 7-digit LEA ID format (e.g., `1300120`) is not currently stored — add a separate column if it becomes needed.

---

## Percentage Scale Exceptions

These education-specific columns are NOT converted to 0-1 scale — they keep their natural scale and are annotated with the matching non-percentage `unit`:

- Score columns (SAT, ACT 1–36, CCRPI indicator scores 0–100) → `unit: score` (with `value_min`/`value_max` where known)
- Star ratings (FESR 1–5, CCRPI climate 1–5) → `unit: rating` (`value_min: 1`, `value_max: 5`)
- Percentile ranks (0–100 integers) → `unit: percentile` (defaults to 0–100)
- Money columns (salaries, revenue, expenditure) → `unit: currency` (no derived range check)
- Plain integer counts → `unit: count` (`>= 0`)

Per data-cleaning-standards §4a, percentage columns split into **bounded → `unit: proportion`** (must be 0–1, e.g. `graduation_rate`) and **ratio → `unit: ratio`** (divided by 100 but may exceed 1, e.g. `mobility_rate`, `participation_rate` in early years, `salaries_and_benefits.pct_*` against a chosen base). The transform authors this per column via a `"unit"` key in the column declaration (omit for exempt columns); the emitter writes it to the contract's `unit` custom property, and the generic validator reads it back from the contract to apply the right rule (`proportion`→bounded, `ratio`→ratio). There are no per-topic validator files.

---

## Cross-Topic Naming Conventions

Beyond the universal canonical vocabulary in `data-cleaning-standards` §16, these education-specific conventions apply across topics. The full rationale and the spelling-variant resolutions live in §16 — this list is a quick reference for education contributors.

| Concept | Canonical column / value | Notes |
| --- | --- | --- |
| Academic assessed content | `subject` | Used by Milestones EOC/EOG, GAA, SGM, AP, CCRPI content mastery, Lexile. Spelling variants (e.g., `us_history` vs `united_states_history`) resolve via `src/utils/subjects.py`. Curriculum-era distinctions (`algebra_i` vs `coordinate_algebra`; `geometry` vs `analytic_geometry`) stay distinct. |
| Non-academic test section | `test_component` | Reserved for SAT/ACT-style sections (`math`, `reading`, `evidence_based_reading_and_writing`, etc.). |
| Georgia state assessment program | `assessment_type` | Values: `crct`, `eoct`, `eog`, `eoc`, `eog_and_eoc_combined`. CRCT/EOCT are the pre-2015 program; EOG/EOC are the Milestones-era program. `eog_and_eoc_combined` is a 2016-2021 transitional reporting bucket. Each topic emits only the subset its bronze reports (e.g., `ccrpi_content_mastery` uses `{crct, eoct, eoc, eog}`; `georgia_milestones_end_of_grade` uses `{eoc, eog, eog_and_eoc_combined}`). |
| Academic grade | `grade_level` | String, zero-padded 2-char (`'01'`–`'12'`, `'k'`, `'pk'`). Aggregate row uses `'all'`. Normalize via `src/utils/grades.py`. Move grade out of `demographic` when the topic is grade-primary. |
| Race × gender cross-classification | `race` + `gender` columns | When a topic's bronze publishes a true cross-classification of race × gender (currently `enrollment_march_gender_race_ethnicity`, `enrollment_october_gender_race_ethnicity`), each axis becomes its own fact-table column rather than collapsing into `demographic`. `race` takes the canonical race demographic keys; `gender` takes `male` / `female`. The two-column shape is preserved because flattening would force fabrication of cells the source does not measure (e.g., race=asian × gender=female × economic=disadvantaged). Topics that publish a single demographic axis must continue to use only `demographic`. |
| CCRPI color flag | `ccrpi_flag` | Values `green`, `green_star`, `yellow`, `red`. No source-code values. Not every CCRPI topic emits `green_star`; each topic's contract `enum` enumerates the values it can publish. |
| CCRPI improvement target | `target` | Inside CCRPI topics only; no `ccrpi_` prefix. |
| SGP count | `num_received_sgp` | Not `n_received_sgp` or `number_received_sgp`. |
| Proficiency threshold suffix | `_or_above` | Not `_and_above`. |
| Rate metric suffix | `…_rate` only | No `_rate_pct` / `_pct` on a column already on 0–1 scale (e.g. `dropout_rate`, `graduation_rate`, `mobility_rate`). |
| Share-of-denominator prefix | `pct_of_<denominator>` | For share-of-denominator metrics on 0-1 scale (`pct_of_enrollment`, `pct_of_district_enrollment`, `pct_of_retained_cohort`, `pct_of_credential_type`). Not `*_share`. See data-cleaning-standards §16 "Share-of-denominator metric". |
| FESR FTE enrollment | `fte_enrollment` | Used by both district and school FESR topics. |
| FESR per-pupil expenditure | `per_pupil_expenditure` | Plus `federal_per_pupil_expenditure`, `state_local_per_pupil_expenditure`. |
| FESR CCRPI single score | `ccrpi_single_score` | Both district and school FESR topics. |
| FESR star rating | `fesr_star_rating` | Both district and school FESR topics. |

### Grade-in-demographic policy

When grade is the **primary row axis** for a topic (one row per grade × geography × year), put grade in `grade_level` and drop `demographic` if all surviving rows would be `'all'`. When grade is **one slice among race/gender/economic demographic breakouts**, grade values may live in the `demographic` column — but the topic's transform docstring must explicitly state that decision and the rationale.

**Value-format note.** The two columns intentionally use different value vocabularies:

- `grade_level` uses canonical zero-padded codes per data-cleaning-standards §16: `'01'`–`'12'`, `'k'`, `'pk'`, `'all'`.
- The grade values inside `demographic` use the demographics dimension's long-form labels: `grade_1`–`grade_12`, `kindergarten`, `pre_kindergarten` (see `src/utils/demographics.py`).

This is intentional. The two columns belong to different conceptual axes — `grade_level` is the grade as a row partition; `demographic` is the demographic axis a row is keyed on. Analysts joining a grade-primary topic to a grade-in-demographic topic must translate between the two encodings explicitly (e.g., `grade_1` ↔ `'01'`, `kindergarten` ↔ `'k'`).
