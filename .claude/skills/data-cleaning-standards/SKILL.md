---
name: data-cleaning-standards
description: Standards for cleaning bronze data into gold data. Use when writing or reviewing transform.py files to ensure consistent data quality across all topics.
user-invocable: true
---

# Data Cleaning Standards

Standards that all `transform.py` scripts must follow when converting bronze data to gold. These ensure consistent, queryable gold data across all topics.

Domain-specific conventions (geography columns, detail levels, ID formatting, output filenames, crosswalks) are defined in each domain's `CLAUDE.md` (e.g., `src/etl/education/CLAUDE.md`).

---

## 1. Column Naming

All column names must be **snake_case**.

**Fact table column order**: `year` first, then geography key columns (domain-specific FKs, defined in domain `CLAUDE.md`), then `demographic` (if applicable), then topic-specific categorical columns, then metric columns.

---

## 2. Star Schema: Fact vs Dimension Tables

Gold data uses a star schema. Each topic's `transform.py` produces **fact tables only**. Dimension tables are built by standalone scripts:
- Global demographics: `uv run python -m src.etl.build_demographics_dimension`
- Education districts + schools: `uv run python -m src.etl.education.build_dimensions`

### What goes in fact tables

- `year` (partition key)
- Geography key columns (foreign keys to domain dimension tables) — defined in domain `CLAUDE.md`
- `demographic` (FK to global demographics dimension) — only if topic has demographic breakdowns
- Topic-specific categorical columns (e.g., `subject`, `test_component`) — normalized to snake_case
- Topic-specific metric columns (counts, scores, rates)

### What does NOT go in fact tables

- Name columns (`district_name`, `school_name`, etc.) — dimension attributes
- Census/crosswalk IDs (`district_census_id`, etc.) — dimension attributes
- Any descriptive/label column that can be looked up from a key

### Dimension table conventions

- Stored as single Parquet files (not year-partitioned)
- Use natural keys as primary keys (no surrogate integer IDs)
- Store the latest/current name only (no historical versions)
- Name columns in title case
- Global dimensions: `data/gold/_dimensions/`
- Domain dimensions: `data/gold/{main_topic}/_dimensions/`
- Domain-specific dimension schemas are defined in the domain `CLAUDE.md`

### Global demographics dimension schema

| Column | Type | Description |
|--------|------|-------------|
| `demographic` | `pl.Utf8` | PK — canonical key from `demographics.py` |
| `demographic_label` | `pl.Utf8` | Human-readable display name |
| `demographic_category` | `pl.Utf8` | Grouping (from `DEMOGRAPHIC_CATEGORIES` in `demographics.py`): `aggregate` (the `all` total), `race`, `gender`, `economic_status`, `grade`, and the special-population splits `sped`, `esol`, `migrant_status`, `homeless_status`, `foster_care`, `military`. Exposed as the `demographic_category` fact-query filter (REST + MCP). |

---

## 3. Data Types

| Category | Type | Examples |
|----------|------|---------|
| ID columns | `pl.Utf8` (string) | codes, IDs — preserve leading zeros |
| Count columns | `pl.Int64` | totals, counts |
| Rate/percentage columns | `pl.Float64` | rates, percentages, proportions |
| Score columns | `pl.Float64` | test scores, indicator scores |
| Star rating columns | `pl.Float64` | FESR 1–5 (half-steps), CCRPI climate 1–5 — uniform `Float64` so the API exposes one star-rating type |
| Calendar year | `pl.Int32` | `year` |
| Categorical columns | `pl.Utf8` | `demographic`, `subject` |
| Name columns | `pl.Utf8` | proper names |

Cast metric columns with `strict=False` so non-numeric strings (suppressed values) become null:

```python
pl.col("value_raw").cast(pl.Int64, strict=False).alias("value")
```

**All ID columns must be strings.** Integer types lose leading zeros. Domain-specific ID formatting rules (e.g., zero-padding width) are in the domain's `CLAUDE.md`.

---

## 4. Percentages and Rates: 0-1 Decimal Scale

All percentage, rate, and proportion columns must use a **0-1 decimal scale** (e.g., 0.95 = 95%).

**Applies to**: Any column with `pct_`, `_rate`, or `_percent` in its name, plus any column representing a rate, percentage, or proportion.

**If bronze source uses 0-100 scale**: Divide by 100.

```python
(pl.col("RATE_RAW").cast(pl.Float64, strict=False) / 100.0).alias("some_rate")
```

**Does NOT apply to**:

- Score columns -- preserve natural scale
- Star ratings -- preserve natural scale
- Count columns -- preserve as integers
- Percentile ranks (0-100 ordinal) -- preserve as 0-100 integers

**Scale consistency across eras**: When combining data from multiple eras, verify metric columns use the same scale by comparing summary statistics (mean, min, max) per era. If magnitude differs by ~100x, normalize all eras to 0-1.

### 4a. Bounded proportions vs decimal ratios

Two kinds of "percentage" columns exist on the 0-1 scale, and they need
different validator behavior:

- **Bounded proportion** — must satisfy `0 ≤ value ≤ 1`. Anything above 1 is
  a bug. Examples: graduation rate (a cohort can't graduate more than once),
  any pct_demographic share of a fixed cohort.
- **Decimal ratio** — divided by 100 from a 0-100 bronze source, but may
  legitimately exceed 1 when the real-world numerator can exceed the
  denominator. Examples: mobility rate at a high-churn school, participation
  rate in early years where the source overcounts test administrations,
  salary/expense as a fraction of a chosen base when the base excludes
  some categories.

The classification is **authored in the transform**, on each metric column's
dict in the `write_data_dictionary` `columns=[...]` declaration, via a `unit`
key. The full vocabulary is:

`count | proportion | ratio | score | rating | currency | percentile`

The two percentage cases are:

- `unit: "proportion"` — the **bounded** case: must satisfy `0 ≤ value ≤ 1`.
  Anything above 1 is a bug (graduation rate, any pct_demographic share of a
  fixed cohort).
- `unit: "ratio"` — divided by 100 from a 0-100 source, may legitimately exceed
  1 when the real-world numerator can exceed the denominator (mobility rate at a
  high-churn school, participation rate when the source overcounts).

The remaining values cover non-percentage metrics: `count` (non-negative
integers), `score` (e.g. ACT), `rating` (e.g. star ratings), `currency`
(dollars), `percentile` (0-100 ordinal rank). Omit the `unit` key only for a
genuinely unclassifiable column.

```python
{"name": "graduation_rate", "type": "float64", "unit": "proportion", ...},
{"name": "mobility_rate",   "type": "float64", "unit": "ratio",      ...},
{"name": "student_count",   "type": "int64",   "unit": "count",      ...},
{"name": "avg_act_score",   "type": "float64", "unit": "score",
 "value_min": 1, "value_max": 36, ...},
{"name": "star_rating",     "type": "float64", "unit": "rating",
 "value_min": 1, "value_max": 5, ...},
{"name": "mystery_metric",  "type": "float64", ...},  # unclassifiable — NO unit key
```

Optional `value_min` / `value_max` keys pin a bounded range. ACT scores (1-36),
star ratings (1-5), and percentile ranks (0-100) are the safe bounded cases — a
`score`/`rating` with both bounds gets a `[value_min, value_max]` range check,
and `percentile` defaults to `[0, 100]` when bounds are omitted. Scores with
variable or open-ended ranges should omit `value_min`/`value_max` (they then get
no derived range check).

The emitter writes the `unit` to the contract as a per-property `unit` custom
property (plus `value_min`/`value_max` when given) and derives the range-check
quality SQL from it (`proportion` → `[0, 1]`; `ratio`/`count` → `>= 0`;
bounded `score`/`rating`/`percentile` → `[value_min, value_max]`).

The validator reads the bounded/ratio classification **back from the contract's
`unit`** (`proportion` → bounded, `ratio` → ratio); the rest of the
validation config (types, metric/categorical lists, exemptions) is likewise
derived from the contract — nothing is declared per topic (§15a). Default new
percentage columns to
`proportion`; promote to `ratio` only when the bronze data demonstrates a
legitimate real-world reason to exceed 1.0. Both percentage buckets still
trigger a `median > 1.5` warning ("looks like it was never divided by 100"). The
check lives in `check_percentage_scale()` in `src/utils/validators.py`.

### 4b. Known source defects

The cardinal rule (data quality takes priority over code quality) and the
"preserve bronze granularity" principle pull in opposite directions when a
specific source value is documented as defective — e.g., a clearly impossible
value published by the upstream agency. The decision turns on whether the value
is **impossible** or merely **extreme-but-conceivable**:

**Impossible / out-of-range → NULL + document.** A value that cannot exist on
the metric's defined scale or domain is a publication error, not data — do not
serve it. Examples: an ACT scaled score above 36 or below 1, a bounded
proportion outside `[0, 1]` (one that is *not* a `ratio`), a star rating outside
its published scale, a negative count. Set it to **NULL** — the same NULL
convention used for suppression (§8) — rather than preserving or dropping it.
Mechanics:

- **NULL the offending metric only, not the row.** Keep the row and every other
  valid column (e.g., null a bad `avg_score` but keep its `num_tested`), so the
  grain and the rest of the observation survive.
- **Apply the masking before validate / manifest / export** so the manifest
  metric stats and the exported parquet reflect the cleaned values.
- **Encapsulate the masking in a `_null_*` helper** applied in `main()` at one
  clear seam — after harmonize / dedup / geography-nulling, before
  `validate_output()` / `manifest.record_gold_from_dataframe()` / export. This is
  the established convention: `_null_invalid_act_scores` (the canonical
  out-of-range reference), plus the sibling masks `_null_id_sentinels`
  (`ccrpi_graduation_rate`, `ccrpi_scoring_by_component`),
  `_null_placeholder_zero_amounts` (`financial_efficiency_star_rating_fesr_school`),
  and `_null_if_all` (`georgia_alternate_assessment_gaa`).
- **Keep (or restore) the column's contract range guard** — the per-column
  `value_min` / `value_max` (or `unit` bounds, §4a). Because the impossible
  values are now NULL, the `{col}_within_range` quality check passes and stays a
  real, enforceable invariant that prevents the bad value from silently
  returning.
- **Never mask silently.** Record every mask via
  `manifest.record_masked(column, count, reason, years=[...])` (the data
  review verifies masked counts from the manifest, not from logs), log a
  warning with the affected years/identifiers, and document the handling in
  the column's contract `description`: the bronze value(s), the gold row
  identifier(s), why the value is impossible, and that this revises the
  preserve-default for that column.
- Changing already-approved gold this way will trip drift detection
  (`check_approved_topics.py`); re-run `/approve-topic` after you and the user
  confirm the cleaned gold.

**Extreme-but-conceivable → preserve + document.** A value that is within the
metric's *possible* domain but suspiciously large/atypical is not provably wrong
— default to **preserve + document**:

- Keep the raw value in gold (after the topic's standard scaling/casting).
- Surface it via the topic's existing sanity-threshold warning in `transform.py`
  so re-runs continue to flag the row.
- Document the value, the bronze source value, the gold row identifiers, and why
  it is suspect in the topic's README / contract column `description`.

When you are unsure which bucket a value falls in, the test is "is this value
*physically possible* for this metric?" — `participation_rate` slightly above
1.0 from transfers-in is conceivable (preserve, mark the column `unit: ratio`);
an ACT score of 41.5 is not (NULL).

References:
- **Impossible → NULL**: `act_scores.avg_score` — 2006 bronze published 10 rows
  at 36.9–41.5 (above the ACT 1–36 scale) for two real schools; the transform
  NULLs any `avg_score` outside `[1, 36]` via `_null_invalid_act_scores`, keeps
  `num_tested`, and the contract enforces `value_min: 1` / `value_max: 36`.
- **Extreme-but-conceivable → preserve**: `student_mobility_rates_school` 2020
  row at sys_sch=701298 (mobility_rate=115.0 from bronze 11500.0) — preserved and
  documented in the topic README / contract column description.

### 4c. Key metric, its components, and its grain

Three contract properties make a fact table's **headline metric**
machine-readable for API / MCP / LLM consumers. The first two are authored on the
column dicts in `write_data_dictionary` (alongside `unit`); the third is
auto-derived.

- **`"key_metric": True`** — set on **exactly one** column: the single metric a
  consumer is most likely to want given the dataset description. Prefer a
  score/proportion over a count, and the most granular over a category derived
  from it (a `score` over a `proficient`/`not_proficient` category); a count is
  rarely the key metric (only when the topic *is* a headcount, e.g. enrollment).
  The emitter **raises** unless exactly one is set on a table that has metric
  columns, and it also emits a schema-object `key_metric: <colname>` pointer. A
  categorical key metric (rare — a category with no underlying numeric) needs an
  explicit `"key_metric_categorical": True` opt-in.
- **`"metric_component": "numerator" | "denominator"`** — set on the **count**
  column(s) that compose the key metric, when the key metric is a rate or average
  (the column must be `unit: count`). Decide by the key metric's `unit`:
  `proportion` / `ratio` → flag its numerator + denominator counts (e.g.
  `graduation_rate` → `graduate_count` numerator + `cohort_size` denominator);
  `score` / `rating` / `percentile` (an average) → flag only the N it averages
  over, as `denominator` (e.g. `avg_score` → `num_tested`; `sgp_median` →
  `num_received_sgp`); a `count` or `currency` key metric has no components.
- **`key_metric_grain_contributor`** (auto-derived, no authoring) — the grain
  columns that disaggregate the key metric: grain minus `year` minus the
  geography columns, so `demographic` and every categorical (`test_component`,
  `grade_level`, `subject`, …) are flagged while `year` / `district_code` /
  `school_code` are not. Take the distinct values of these columns and no key
  metric value is collapsed.

---

## 5. Demographics

Use `normalize_demographic_column()` from `src/utils/demographics.py` for all demographic normalization. Never hardcode demographic mappings in `transform.py`.

**Canonical values**: `all`, `asian`, `black`, `hispanic`, `white`, `multiracial`, `native_american`, `pacific_islander`, `male`, `female`, `economically_disadvantaged`, `students_with_disabilities`, `english_learners`, `homeless`, `migrant`, `foster_care`, `military`, and others defined in `CANONICAL_DEMOGRAPHICS`.

**Pattern**:

```python
from src.utils.demographics import normalize_demographic_column

df = df.with_columns(
    normalize_demographic_column("demographic_raw").alias("demographic")
)
```

`normalize_demographic_column()` is the single canonical path: it casts to string, strips whitespace, uppercases, maps via `DEMOGRAPHIC_ALIASES`, and emits `SENTINEL_UNMATCHED_DEMOGRAPHIC` (`"99999999"`) for unmatched values. Never reimplement these steps inline.

**Rules**:

- Sentinel `"99999999"` for unmatched values -- add mappings to `demographics.py`, do not discard rows. See the module docstring in `src/utils/demographics.py` for the full steps when adding new demographics.
- **Omit the `demographic` column entirely** if all rows would be `"all"` (topic has no demographic breakdowns)
- NULL demographics in bronze stay NULL in gold
- Never remove rows due to demographic issues
- **Subgroup collisions**: When multiple raw labels normalize to the same canonical value (e.g., two Hispanic subgroups both → `"hispanic"`), call `aggregate_demographic_collisions()` from `src/utils/transformers.py` **before** `deduplicate_by_detail_level()`. It sums count metrics and weighted-averages rate/score metrics across colliding rows, so dedup never silently discards data.

  ```python
  from src.utils.transformers import aggregate_demographic_collisions

  df = aggregate_demographic_collisions(
      df,
      natural_key_cols=["year", "district_code", "school_code",
                        "demographic", "test_component"],
      sum_cols=["num_tested"],
      weighted_avg_cols={"avg_score": "num_tested"},
  )
  ```

### 5a. Demographic categories must be mutually exclusive

**Principle**: within any single demographic category (race, gender, English-learner status, disability status, etc.), the canonical values are mutually exclusive. **A student belongs to exactly one value within a category** and therefore appears in exactly one row per natural-key group on that axis. Two rows from the same category for the same student would double-count them when consumers sum across the demographic axis.

Specific category rules:

- **Race** (`asian`, `pacific_islander`, `black`, `hispanic`, `white`, `multiracial`, `native_american`, `asian_pacific_islander`): a student is in exactly one race row. The combined-bucket key `asian_pacific_islander` is **mutually exclusive with** the split keys `asian` and `pacific_islander` — never emit both for the same topic/year/geography. See §5b for the canonical Asian / Pacific Islander example.
- **Gender** (`male`, `female`): exactly one row per student.
- **English-learner status** (`english_learners`, `not_english_learners`): exactly one row per student. (The negated key uses the `not_` prefix, matching `not_economically_disadvantaged` and `not_migrant` and the canonical demographics dimension; there is no `non_english_learners` key.)
- **Disability status** (`students_with_disabilities`, `students_without_disabilities`): exactly one row per student.
- **Economic disadvantage** (`economically_disadvantaged`, `not_economically_disadvantaged`): exactly one row per student.

**Aggregation lane (`all`) is the exception, not a counterexample.** The `all` value is not a category member; it is the unfiltered total. It is expected to overlap with every category-specific row — a student appears in the `all` row AND in their race row AND in their gender row, etc. Consumers must filter `demographic != 'all'` when summing within a category, and must filter to a single category when comparing across topics.

**Across-category overlap is by design.** A student appears in one row per category they belong to: one race row, one gender row, one EL row, one SWD row, one economic-status row, etc. These are separate axes packed into a single `demographic` column for tidy storage. Consumers querying across categories must group by category and filter to one category at a time.

**Bronze sometimes publishes overlapping rollup labels** (e.g., a separate `"Asian/Pacific Islander"` row alongside `"Asian"` and `"Pacific Islander"` rows). Do not pass both through to gold. Pick the convention used by the bronze for that topic — if the bronze publishes the split rows, gold keeps the split rows; if the bronze publishes only the combined row, gold keeps the combined row. Never synthesize a rollup row at transform time when bronze already provides the split rows.

### 5b. The Asian / Pacific Islander conflation pitfall

Three canonical race keys are intentionally distinct: `asian` (post-1997 OMB Asian-only), `pacific_islander` (post-1997 OMB Native Hawaiian / Other Pacific Islander only), and `asian_pacific_islander` (the pre-1997 OMB combined bucket). They are **not additive** — a source publishing the combined bucket must map to `asian_pacific_islander`, never silently into `asian` or `pacific_islander`.

**Mutual exclusivity rule**: racial demographics in gold are mutually exclusive within a topic. A student appears in exactly one race row per natural-key group. Do NOT emit a synthesized `asian_pacific_islander` row alongside the split `asian` + `pacific_islander` rows — that double-counts the Pacific Islander population. Pass bronze granularity through; do not invent rollup rows in gold.

**The trap**: a bronze column or label of bare `"Asian"` / `"Asians"` does NOT automatically mean Asian-only. Many sources (notably GOSA) report a 6-bucket race scheme (American Indian, Asian, Black, Hispanic, Multiracial, White) where the small Pacific Islander population is folded into "Asian" under pre-1997 OMB convention. `DEMOGRAPHIC_ALIASES["ASIAN"]` maps to `asian` because that is correct for sources that publish Asian-only — but the alias is wrong for combined-bucket sources, and `normalize_demographic_column()` cannot tell the difference from the label alone.

**The math test (apply when bronze has only 6 race buckets)**: at the state-level row in a representative year, sum the race-bucket counts and compare to the cohort total (or sum the race-bucket percentages and check that they reach 100%).

- Race sum equals total exactly → Pacific Islanders are folded in → "Asian" is the combined bucket → map to `asian_pacific_islander`.
- Race sum is less than total (by approximately the expected NHPI share, ~0.1-0.2% of Georgia students) → Pacific Islanders are dropped → "Asian" is genuinely Asian-only → map to `asian`. Flag the dropped rows.
- For average-style metrics where the math test is inapplicable (SAT/ACT scores), use the structural argument: if the bronze never publishes a separate Pacific Islander row/column anywhere in any era, treat bare "Asian" as the combined bucket. Cross-check with sibling reports from the same vendor — they often use the explicit `"Asian/Pacific Islander"` label for the same concept.

**The fix pattern**: do NOT change `DEMOGRAPHIC_ALIASES` globally — that would break topics where "Asian" really is Asian-only. Add a topic-local override in `transform.py` that remaps the bronze label to `"Asian/Pacific Islander"` BEFORE `normalize_demographic_column()` runs (which then canonicalizes to `asian_pacific_islander` via the existing alias). The override is typically a small helper:

```python
def _raw_demographic_label(bronze_label: str) -> str:
    """Remap bare 'Asian' to the combined OMB bucket for this topic.

    Bronze has only 6 race buckets and race-bucket sums equal the cohort
    total -- Pacific Islanders are folded in, not dropped. See section 5b
    of the data-cleaning-standards skill.
    """
    if bronze_label in {"Asian", "ASIAN", "Asians"}:
        return "Asian/Pacific Islander"
    return bronze_label
```

Apply at the `pl.lit(...)` emission site before normalize, and update the topic's `demographic` column description in `write_data_dictionary()` to list `asian_pacific_islander` (not `asian`) in the race-bucket enumeration. For topics with no `demographic` column (wide-format metric columns like `pct_asian`), rename the column to `pct_asian_pacific_islander` in the transform's column declaration (the validator derives its expectations from the re-emitted contract).

**Known to use the combined bucket** (as of 2026-05): GOSA `dropout_rate_7_12`, `dropout_rate_9_12`, `retained_students`, `attendance`, `high_school_completers`, `certified_personnel`, `sat_scores_recent` (Eras 1-3), `sat_scores_highest` (Eras 1-3), `enrollment_by_subgroup_programs`. **Known to use the split convention** (Asian and Pacific Islander as separate rows): `postsecondary_c11_report`, `postsecondary_c12_report`, `georgia_alternate_assessment_gaa`, the Georgia Milestones by-grade EOC/EOG topics, and the Georgia Insights `enrollment_*_gender_race_ethnicity` topics.

**Cross-topic comparability is the analyst's responsibility, not the pipeline's.** Split-convention topics keep their separate `asian` and `pacific_islander` rows; combined-convention topics keep their `asian_pacific_islander` rows. Each topic faithfully preserves its bronze granularity. An analyst joining a split-convention topic with a combined-convention topic must aggregate `asian + pacific_islander` themselves at query time — the pipeline does NOT pre-compute a rollup row, because that would double-count when summing across all race demographics within a single topic.

---

## 6. Detail Levels and Geography Nulling

Datasets may contain multiple detail levels (e.g., individual + aggregate rows). Higher-level aggregate rows must have their geography columns nulled so they are not confused with specific entities.

**General principle**: When a row represents an aggregate level, all geography key columns below that level must be NULL. Sentinel strings from bronze (e.g., `"ALL"`, `"Statewide"`) must become NULL in gold.

Use `null_aggregate_geography()` from `src/utils/transformers.py` together with the domain's geography rules dict (e.g., `EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"]` from `src/utils/validators.py`). Transform and validator then share one rule source so they cannot disagree.

```python
from src.utils.transformers import null_aggregate_geography
from src.utils.validators import EDUCATION_DOMAIN_CONFIG

df = null_aggregate_geography(
    df,
    detail_level_col="detail_level",
    geography_rules=EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"],
)
```

Domain-specific detail levels, geography columns, sentinel strings, and nulling rules are defined in the domain's `CLAUDE.md`.

---

## 7. Name Columns: Title Case

All proper name columns must be in **title case**.

Use the `title_case_name` utility:

```python
from src.utils.transformers import title_case_name

pl.col("NAME_RAW").pipe(title_case_name).alias("name")
```

**Note**: Name columns appear only in dimension tables, not in fact tables. Use `title_case_name` when building dimension tables. The helper:

- Handles proper-noun overrides (e.g., `DeKalb`, `STEAM`) that polars's `to_titlecase` would corrupt.
- Lowercases the letter following an apostrophe so possessives and contractions read correctly (`Eagle's Landing`, not `Eagle'S Landing`; `they'll`, not `They'Ll`).

---

## 8. Suppression Handling

All suppressed values must become NULL in gold.

- `read_bronze_file()` handles common markers: `TFS`, `N/A`, `*`, `**`, `***`, `-`, etc.
- Cast metric columns with `strict=False` to convert remaining non-numeric strings to null
- Topic-specific suppression markers should be added to a local list if `read_bronze_file()` misses them

**Known-bad values use the same NULL convention.** A value that is *impossible*
on the metric's defined scale (e.g., an ACT score > 36) is treated exactly like
a suppressed value — set to NULL (via a small `_null_*` helper in `main()`), row
preserved — and documented. See §4b "Known source defects" for the full
impossible-vs-extreme decision, the NULLing mechanics, and the `_null_*` helper
family.

---

## 9. Tidy Data Format

All gold data must be in **tidy long format**:

- Each row = one observation
- No demographics, years, test components, or other categories as column names
- Wide format bronze data must be unpivoted

**Unpivot approaches**:

| Approach | When to Use |
|----------|-------------|
| Build sub-DataFrames per group, then `pl.concat()` | Multiple metrics per category (e.g., count + rate per demographic) |
| `df.unpivot()` | Single metric embedded in column names |
| No unpivot needed | Bronze data is already long format |

---

## 10. Categorical Normalization

Topic-specific categorical columns (e.g., `subject`, `data_category`, `employee_type`) must be normalized to **snake_case**.

Define normalization dictionaries as module-level constants:

```python
SUBJECT_MAP = {
    "ENGLISH LANGUAGE ARTS": "english_language_arts",
    "MATHEMATICS": "mathematics",
    "SCIENCE": "science",
}
```

Use `replace_strict()` with a sentinel or default for unmapped values. Always log values that fall through to a fallback.

### 10a. Shared categorical utilities

When two or more topics need to normalize the same categorical vocabulary,
the mapping lives in `src/utils/` rather than being duplicated in each
transform.

| Utility | Module | Purpose |
| --- | --- | --- |
| `normalize_demographic_column`, `DEMOGRAPHIC_ALIASES` | `src/utils/demographics.py` | Canonical demographic keys (`white`, `economically_disadvantaged`, etc.) — see §5 |
| `normalize_grade_column`, `GRADE_LEVEL_MAP` | `src/utils/grades.py` | Canonical `grade_level` values (`'01'`–`'12'`, `'k'`, `'pk'`, `'all'`) — see §16 |
| `apply_subject_normalization`, `SUBJECT_NORMALIZATION_MAP` | `src/utils/subjects.py` | Canonical `subject` values for assessment topics (resolves spelling variants like `us_history` / `united_states_history`) — see §16 |

After running the topic-local map, pass `subject` and `grade_level` through
the shared normalizer so spelling variants resolve consistently. Record the
result via `manifest.record_categorical()` exactly like any other mapping;
the manifest's `unmapped_count` guard still applies.

---

## 11. Columns NOT Stored in Gold Fact Tables

| Column | Reason |
|--------|--------|
| `topic` | Implicit in folder path (`data/gold/{main_topic}/{topic}/`) |
| Name columns (e.g., `district_name`, `school_name`) | Stored in dimension tables, not fact tables |
| Crosswalk IDs (e.g., `district_census_id`) | Stored in dimension tables, not fact tables |

Domain-specific excluded columns are defined in the domain's `CLAUDE.md`.

---

## 12. Output Format

Gold data is exported as year-partitioned Parquet:

```
data/gold/{main_topic}/{topic}/
├── year=2024/
│   └── {detail_level_files}.parquet
└── README.md
```

The machine-readable schema is the git-tracked ODCS contract at
`contracts/{main_topic}/{topic}.odcs.yaml`, emitted directly by the transform —
there is no `_metadata.json`. See §12a for the column-declaration authoring
surface and the contract fields the emitter auto-derives.

Only create files for detail levels that have data. No empty parquet files. Domain-specific file naming conventions are defined in the domain's `CLAUDE.md`.

The `detail_level` column is dropped during export because the filename encodes it. `export_to_parquet()` from `src/utils/transformers.py` handles this automatically — do not carry `detail_level` through to gold parquet files.

**Gold directory ownership.** `transform.py` owns its gold directory. Starting a run wipes prior output — the `/transform-topic` skill runs `rm -rf data/gold/{main_topic}/{topic}` before invoking the transform, so a re-run that produces fewer year partitions does not silently inherit stale partitions from a previous run.

---

## 12a. The Data Contract Is the Metadata

The git-tracked **ODCS v3.1 contract** at `contracts/{main_topic}/{topic}.odcs.yaml`
is the dataset's machine-readable metadata — the schema artifact the REST API,
the validator, and (in future) the MCP server consume. There is **no
`_metadata.json`**. The contract is **emitted directly by the transform** as a
byproduct of the same run that writes the gold parquet, so the two cannot drift.
This section documents the authoring surface; for the full emit mechanism see
[`docs/contract-creation.md`](../../../docs/contract-creation.md).

### The `write_data_dictionary()` call

Emit the contract (and the human `README.md`) by calling
`write_data_dictionary()` from `src/utils/metadata.py` once in `main()`, after
`export_to_parquet()` and `manifest.write()`, and before
`run_topic_validation()` (which reads the contract this call emits). It returns
`(contract_path, readme_path)`. Parameters group as:

| Group | Parameters |
| --- | --- |
| **Required** | `output_dir` (the gold topic dir), `name` (must equal `output_dir.name`), `description` (becomes the contract `purpose`), `columns=[...]` (the in-code schema), `source` |
| **Optional metadata** | `source_url`, `update_frequency` (default `"annual"`), `year_range=(min, max)` |
| **README-only** | `partitioned_by`, `notes` (do not affect the contract) |
| **Contract overrides** | `limitations`, `usage`, `example_queries` — pass verbatim **only** when the emitter's auto-derived prose is insufficient |

The emitter resolves the rest from what the transform just produced: it reads the
topic identity from `output_dir`, the **detail levels** from the gold parquet
basenames under `output_dir` (`year=*/*.parquet`), and the `sub_topic` from
`topic-status.yaml` / the ETL tree.

### The `columns=[...]` declaration — the single schema source

`columns` is a list of dicts authored **in the same order as the gold parquet
columns** (`STANDARD_COLUMNS` minus `detail_level`). It is projected directly
into `schema[0].properties[]` in the contract. Recognized keys (any other key is
silently dropped):

| Key | Required | Purpose |
| --- | --- | --- |
| `name` | yes | snake_case column name. **List order = parquet column order** (enforced by the `contract_parquet_schema` check — see §15a) |
| `type` | yes | logical type: `int32` / `int64` / `float64` / `float32` / `string` / `bool` / `date` |
| `description` | recommended | prose (whitespace collapsed; write `%%` to emit a literal `%`) |
| `nullable` | optional (default `True`) | per-property required/optional flag |
| `example` | optional | sample value (also seeds `example_queries`) |
| `validValues` | optional | enum for a categorical. **Auto-filled from the gold parquet** when omitted (`_fill_categorical_valid_values`); hand-author it only when the vocabulary is small + fixed (e.g. `test_component`) |
| `unit` | metrics only | `count \| proportion \| ratio \| score \| rating \| currency \| percentile` — drives the range-check quality SQL; **omit for exempt columns**. Full rules in §4a |
| `value_min` / `value_max` | optional | pin a bounded range for a `score` / `rating` / `percentile` column |
| `null_meaning` | optional | per-column custom property describing what NULL means in that column |
| `key_metric` | exactly one metric | `True` on the single headline metric column. Emitter **raises** if a table with metric columns has ≠1. Also emits a schema-object `key_metric: <colname>` pointer. Full rules in §4c |
| `key_metric_categorical` | rare | `True` to opt in a *categorical* key metric (a category with no underlying numeric); required when `key_metric` is set on a non-metric column |
| `metric_component` | optional | `numerator` / `denominator` on the count column(s) composing the key metric (must be `unit: count`). §4c |

```python
columns=[
    {"name": "year", "type": "int32", "nullable": False, "example": 2024,
     "description": "Spring calendar year."},
    {"name": "test_component", "type": "string", "nullable": False,
     "validValues": sorted(set(TEST_COMPONENT_MAP.values())),
     "description": "ACT section."},
    {"name": "num_tested", "type": "int64", "unit": "count",
     "metric_component": "denominator",
     "description": "Count of students tested."},
    {"name": "avg_score", "type": "float64", "unit": "score",
     "value_min": 1, "value_max": 36, "key_metric": True,
     "description": "Average ACT scaled score (1-36)."},
],
```

### What the emitter auto-derives — do NOT hand-author these

The transform authors only column identity + `description` + (for metrics)
`unit` / `value_min` / `value_max` / `null_meaning` + the key-metric markers
`key_metric` / `metric_component` (§4c). Everything below is derived by
`src/utils/contract_emitter.py`, so there is no authoring burden:

- **Row grain** → native `primaryKey` / `primaryKeyPosition` on `year` + present
  FK columns (`district_code`, `school_code`, `demographic`) + every categorical
  column, in declared order, plus a human `dataGranularityDescription` and a
  `grain` custom property. FK columns stay `required: false` — the primary key is
  the logical cross-detail-level key, **not** a not-null constraint (FK columns
  are NULL at higher aggregation levels).
- **`key_metric_grain_contributor`** → flagged on each grain column that
  disaggregates the key metric (grain minus `year` minus geography = `demographic`
  + categoricals). Pure function of the grain, so it never drifts (§4c).
- **Range-check quality SQL** from each metric's `unit` (§4a): `proportion` →
  `{col}_within_unit_interval` (`[0, 1]`); `ratio` / `count` → `{col}_non_negative`
  (`>= 0`); `score` / `rating` / `percentile` → `{col}_within_range`
  (`[value_min, value_max]`, percentile defaults `[0, 100]`); `currency` → none.
  Every SQL check is emitted with `type: sql` (an ODCS `quality` SQL check with no
  `type` is silently skipped, so the emitter always sets it).
- **`limitations` + `null_semantics`** — `limitations` prose derived from the
  detail levels present; a `null_semantics` custom property of
  `{suppressed_to_null: true, zero_is_real: true}`, plus optional per-column
  `null_meaning`.
- **Layout** — `partition_columns` (`["year"]`), a `path_template`, and a second
  `local_gold` server entry alongside `s3_gold`.
- **`schema_hash`** — a deterministic top-level sha256 over each property's
  `name` / `logicalType` / `physicalType` / `required` / role / `unit` /
  sorted-enum + the grain. A rename or retype changes the hash; a
  description-only change does not. Regenerating twice yields a byte-identical
  contract (empty `git diff`).
- **`example_queries`** — 2-3 deterministic DuckDB queries derived from the shape.
- **`foreign_keys`** — one descriptor per present FK column for non-API
  consumers: `district_code` → `districts`, `school_code` → `schools` (the
  **composite** `(district_code, school_code)` key, because school codes are not
  globally unique), `demographic` → `demographics`.

### `version` / `schema_hash` policy

Contracts stay at `version: 1.0.0` / `status: active`. Bump the **minor** version
for additive backward-compatible changes (new column/metric) and the **major**
version for breaking changes (renamed/removed/retyped column, changed grain). A
regeneration that changes `schema_hash` means the schema changed and the version
should reflect it.

### Regenerating contracts

- **One topic** — re-run the transform: `uv run python -m
  src.etl.{main_topic}.{sub_topic}.{topic}.transform` (writes gold **and**
  re-emits the contract). Commit the updated `contracts/{main}/{topic}.odcs.yaml`.
- **All approved topics** — `uv run python scripts/generate_contracts.py` (a thin
  batch wrapper that re-runs every approved topic's transform).
- **The 3 dimension contracts** — `uv run python
  scripts/generate_dimension_contracts.py`.
- **CI gate** — `scripts/check_contracts.py` lints every contract and guards the
  quality-`type` rule on each push; an opt-in nightly `contracts-s3` job runs
  `datacontract test` against R2 gold via the S3-compatible API (schema +
  quality checks + check-count assertion).

---

## 13. Cross-Topic Consistency

Beyond single-topic correctness, gold data across topics should be consistent so the API can join facts from different topics reliably.

### Dimension key consistency

- **All topics that use `district_code` must produce values that exist in the domain districts dimension** (`data/gold/{main_topic}/_dimensions/districts.parquet`). Unmatched keys cause silent data loss at query time when DuckDB joins fact → dimension.
- **Same rule for `school_code`** — fact rows with school codes not in the schools dimension will be dropped by API joins.
- **Same rule for `demographic`** — all topic demographics must appear in the global demographics dimension (`data/gold/_dimensions/demographics.parquet`).

### Scale consistency across topics

- Percentage/rate columns with the same semantic meaning across topics (e.g., `graduation_rate` in multiple topics) should use the same scale (0-1 decimal, per §4).
- Count columns representing the same entity (e.g., `num_students`) should use the same unit (per-student, per-enrollment, etc.) — document any differences in the topic's README / contract column description.

### Year coverage consistency

- When a topic reports data for a year that an adjacent topic does not, investigate why: is the data genuinely missing, or was there a bronze file gap?
- Log year coverage per topic in the topic's `_transform_manifest.json` and compare across related topics during data review.

### Verifying cross-topic consistency

Dimension key coverage is enforced per topic by the validator's `foreign_keys`
check (§15a check 18, driven by the contract's FK block). Repo-wide — and
after any dimension rebuild — run
`uv run python scripts/check_referential_integrity.py [--all]` to re-verify
every topic's FKs against the current dimensions.

---

## 14. Transform Manifest

Every `transform.py` must produce a `_transform_manifest.json` alongside its gold data via the `TransformManifest` class from `src/utils/transformers.py`. The manifest is the contract the audit, data-review, and verify-fixes skills depend on — without it, those skills fall back to spot-checking and lose 100% coverage guarantees on categorical recodings, row counts, and metric scales.

What the manifest captures:

- Files read (path, year, era, row count, column list)
- Per-year bronze and gold row counts (and derived expansion factors)
- Every categorical mapping applied — both the bronze values seen and the gold values produced
- Per-year summary stats (min, max, mean, null-pct) for every metric column

### Required calls in every transform

Match the pattern prescribed by `/transform-topic`:

```python
from src.utils.transformers import (
    TransformManifest,
    assert_no_natural_key_collisions,
    deduplicate_by_detail_level,
)
from src.utils.validators import run_topic_validation

def main():
    manifest = TransformManifest(topic=TOPIC, bronze_dir=BRONZE_DIR, gold_dir=GOLD_DIR)

    for path, year, era in bronze_files:
        df, loss = read_bronze_file(path, return_loss=True)
        manifest.record_read_loss(year, path.name, loss["raw_rows"], loss["parsed_rows"])
        manifest.record_file(path, year, era, df.height, df.columns)
        manifest.record_bronze(year, df.height)
        result = transform_era(df, year, era, manifest)

    combined = pl.concat(frames)
    # MANDATORY before dedup: surface alias-collapse / divergent duplicates
    # instead of letting dedup silently pick a winner.
    assert_no_natural_key_collisions(
        combined, natural_keys=NATURAL_KEYS, metric_cols=METRIC_COLUMNS
    )
    # Dedup tie-break is an explicit, documented decision — never rely on the
    # default sort_col.
    combined = deduplicate_by_detail_level(combined, ..., sort_col="num_tested")
    # Record gold counts from the *final* DataFrame so the manifest matches
    # what actually lands in parquet (post-dedup / post-collision aggregation).
    manifest.record_gold_from_dataframe(combined)
    manifest.compute_metric_stats(combined, METRIC_COLUMNS)
    export_to_parquet(combined, GOLD_DIR, ...)
    manifest.write(GOLD_DIR)
    write_data_dictionary(...)            # emits the ODCS contract + README
    run_topic_validation(GOLD_DIR)        # ALWAYS LAST — validates against the
                                          # contract just emitted; raises on failure
```

**Read-loss accounting.** `read_bronze_file(..., return_loss=True)` returns a
`(df, loss)` pair; pass the loss to `manifest.record_read_loss()`. A recorded
loss (parsed < raw) means the parser dropped rows (malformed lines,
truncation) — it is a **blocking finding at data-review time** unless the
event carries a `note` explaining why it is legitimate (e.g. quoted
multi-line fields inflating the raw CSV line count).

After every `replace_strict()` mapping of a categorical column, call:

```python
manifest.record_categorical(column="subject", bronze=df["subject_raw"], gold=df["subject"])
```

To explain *why* rows dropped, optionally record explicit removals with
`manifest.record_filtered(year, count, reason)`. These are additive provenance
for the manifest only — they do not alter the derived bronze-minus-gold counts
that `record_gold_from_dataframe()` computes.

### Rules

- **`unmapped_count` must be 0** for every recorded categorical. `TransformManifest.write()` raises `ValueError` when any mapping has unmapped bronze values (the manifest is still written so you can inspect it), causing the transform to exit non-zero. Fix the map and re-run. In rare inspection/debugging contexts only, you may pass `strict_unmapped=False` to `write()`.
- **Compute metric stats on the final combined DataFrame** (after all filtering, demographic collision aggregation, and deduplication) so the stats match what actually lands in gold.
- **Call `manifest.write()` last**, after `export_to_parquet()`, so the manifest's row counts are final.

See `/transform-topic` for the full `main()` skeleton.

### Shared utilities quick reference

Canonical pipeline utilities. Use these rather than reimplementing the logic inline.

| Utility | Module | Purpose |
| --- | --- | --- |
| `TransformManifest`, `RowCountTracker` | `src/utils/transformers.py` | Runtime manifest + row tracking |
| `harmonize_columns` | `src/utils/transformers.py` | Unify column names across eras |
| `detect_era_by_columns` | `src/utils/transformers.py` | Column-based era detection (not hardcoded years) |
| `deduplicate_by_detail_level` | `src/utils/transformers.py` | Dedup per detail-level natural key |
| `aggregate_demographic_collisions` | `src/utils/transformers.py` | Aggregate colliding demo rows before dedup |
| `null_aggregate_geography` | `src/utils/transformers.py` | Domain-driven geography nulling |
| `validate_output` | `src/utils/transformers.py` | Pre-export sanity check |
| `export_to_parquet` | `src/utils/transformers.py` | Year-partitioned export; drops `detail_level` |
| `title_case_name` | `src/utils/transformers.py` | Dimension name formatting |
| `normalize_demographic_column`, `DEMOGRAPHIC_ALIASES` | `src/utils/demographics.py` | Demographic normalization |
| `read_bronze_file` | `src/utils/readers.py` | Suppression-aware bronze reader |
| `check_null_rate_spikes` | `src/utils/validators.py` | Year-over-year null-rate guard |
| `write_data_dictionary` | `src/utils/metadata.py` | Emits the ODCS contract (via `src/utils/contract_emitter.py`) + `README.md` from the in-code column declaration |

---

## 15. Logging and Validation

- **Every filter must log** what is being removed (count and sample values)
- **Unmatched categorical values** must be logged (demographics, subjects, categories)
- **Row count tracking** via `RowCountTracker` (bronze in, gold out, filtered with reasons) — accessible as `manifest.tracker` once a `TransformManifest` is instantiated
- **Per-year NULL rate check** on metric columns — call `check_null_rate_spikes()` from `src/utils/validators.py`, which flags any year >20pp above the median. Do not reimplement this loop inside `transform.py`.
- **Pre-export validation** — call `validate_output()` from `src/utils/transformers.py` on the final DataFrame before `export_to_parquet()`.
- **Contract and README** — emit the ODCS contract (`contracts/{main}/{topic}.odcs.yaml`) and `README.md` via `write_data_dictionary()` from `src/utils/metadata.py`. Set a `"unit"` key (`count | proportion | ratio | score | rating | currency | percentile`) on each metric column dict (omit for unclassifiable columns) so the contract carries the classification and the validator can read it back. Author cross-column invariants via `quality_checks=` (§15b). There is no `_metadata.json`.
- **Post-emit validation** — `main()` ends with `run_topic_validation(GOLD_DIR)` (§15a). The transform exits non-zero when gold fails any check.
- **Column rename coverage verification** -- ensure all expected metric columns were matched

---

## 15a. Validation: the generic, contract-driven validator

**There are no per-topic `validate.py` files.** The entire validation config
derives from the topic's ODCS contract (`src/utils/contract_reader.py`):
`type_spec` from the properties' physical types, `metric_columns` /
`categorical_columns` from each property's `column_role`, percentage
exemptions and the bounded-vs-ratio split from the per-column `unit` markers.
The transform authors the contract; the validator reads it back. Nothing is
declared twice.

Validation runs in two ways — both execute the identical suite:

1. **Automatically, inside every transform run.** `main()` ends with
   `run_topic_validation(GOLD_DIR)` (from `src/utils/validators.py`), placed
   AFTER `write_data_dictionary()` so the contract on disk is the one this
   run just emitted. It writes `_validation.json` next to the gold and
   **raises** on any failure, so a transform that produces invalid gold exits
   non-zero. A stale `_validation.json` cannot exist — regenerating gold
   regenerates the verdict.
2. **Standalone**: `uv run python scripts/validate_topic.py {main} {topic}`
   (exit 0/1). Use it to re-check without re-transforming (e.g., after a
   dimension rebuild).

### The check suite (`run_all()`, in order)

1. **No empty files** — no 0-row parquet under the gold dir.
2. **`contract_parquet_schema`** — every gold parquet's column names + order
   match the contract (`schema[0].properties[]`). Closes the
   transform↔contract↔parquet loop.
3. **Column naming** — all columns snake_case.
4. **Column order** — columns begin with the expected key prefix (`year`,
   `district_code`, `school_code`).
5. **Star-schema compliance** — no forbidden name/crosswalk columns
   (`district_name`, `school_name`, `district_census_id`, `school_year`, `topic`,
   `detail_level`) in the fact table.
6. **Data types** — every contract column exists in gold and matches its
   contract-declared dtype.
7. **Percentage scale** — bounded/ratio buckets read from the contract `unit`;
   bounded must be `<= 1.001`, and either bucket warns on `median > 1.5` ("looks
   like it was never divided by 100").
8. **Demographics** — the `demographic` column (if present) holds only canonical
   values; flags the `"99999999"` sentinel.
9. **Suppression markers** — no leftover `TFS` / `*` / `N/A`-style markers in
   string columns.
10. **Tidy format** — no year-keyed or demographic-keyed column names (heuristic).
11. **Year non-null** — `year` exists and has no NULLs.
12. **Null-rate spikes** — per-year NULL rate for each metric column is not
    `> 20pp` above the across-years median (warning).
13. **Categorical normalization** — every categorical column value is snake_case.
14. **ID formatting** — `district_code` / `school_code` are zero-padded strings.
15. **Canonical vocabulary** — no column name uses a forbidden variant from
    the `src/utils/vocabulary.py` registry (the machine-readable half of §16).
16. **Grain uniqueness** — exactly one gold row per contract-declared grain
    tuple (duplicates mean dedup/aggregation produced multiple rows per key).
17. **Contract quality SQL** — every `type: sql` check in the contract
    (`schema[0].quality`) executes against the local gold via DuckDB and its
    `mustBe` / `mustBeGreaterThan` / `mustBeLessThan` assertion must hold.
    This is what makes the §15b invariants *enforced*, not decorative.
18. **Foreign keys** — every populated FK resolves in its dimension table,
    driven by the contract's `foreign_keys` block (composite-aware: schools
    join on `(district_code, school_code)`). Repo-wide re-check:
    `uv run python scripts/check_referential_integrity.py` (run it after any
    dimension rebuild).
19. **Geography nulling** — per detail level (`states` / `districts` /
    `schools`, inferred from each parquet's filename), geography columns are
    NULL/not-NULL per `EDUCATION_DOMAIN_CONFIG["detail_level_geography_rules"]`.

Each check returns pass / fail / warning; `_validation.json` records all of
them. A failing check fails the transform run.

### When the schema changes

Nothing to mirror — the validator derives everything from the contract the
same run emits. Author the change in the transform's column declaration
(`unit`, types, `quality_checks`), re-run the transform, and the validator
checks the new shape automatically. See the root `CLAUDE.md` "Schema
Evolution" section.

---

## 15b. Required per-topic quality checks (`quality_checks=`)

The auto-derived contract checks (range-by-`unit`, enum membership,
non-empty) cover single-column invariants. **Cross-column invariants must be
authored by the transform** via the `quality_checks=` parameter of
`write_data_dictionary()` — they become contract `quality` SQL and are
executed on every validation run (§15a check 17).

**Authoring rule: every invariant a careful reviewer would verify by hand
must be authored as a quality check.** The minimum set, wherever the shape
applies:

- **Partition-sums-to-one** — a family of proportion columns that partitions
  a population must sum to ~1.0 (tolerance for rounding, typically ±0.02).
  E.g. the four Milestones achievement bands; a below/at-or-above Lexile pair;
  absentee tiers.
- **Co-null relationships** — a flag or status that implies a metric is NULL
  (e.g. `is_non_compliant = true ⇒ fesr_star_rating IS NULL`;
  `reporting_status = 'suppressed' ⇒ rate IS NULL`).
- **Component reconciliation** — a published total that must equal the sum of
  its published components (e.g. `salaries + benefits = salaries_and_benefits`,
  within $1).
- **Structural facts** — invariants of the topic's shape (e.g.
  `school_code_always_null` for a district-only topic; half-step star ratings
  via `value * 2 = round(value * 2)`).

Each entry is a dict with `name`, `description`, `dimension`
(consistency/accuracy/completeness), `query` (DuckDB SQL over `{object}`,
counting violations), and `mustBe: 0` (or another assertion key).

**Quality SQL has no `detail_level` axis** — the validator's view unions all
detail levels. An invariant that only holds at one level must self-scope via
geography NULL-ness (e.g. `... AND school_code IS NOT NULL` for school-level
rules), and every check should be NULL-guarded (`col IS NOT NULL AND ...`)
because suppression NULLs appear at every level.

**Never self-join `{object}` to compare rows of a long-format table — pivot
with conditional aggregation instead.** A reconciliation across categorical
rows (e.g. `total = component_a + component_b` where each lives on its own
row) written as `{object} t JOIN {object} a ON ... JOIN {object} b ON ...`
can OOM-kill the whole transform process: with `IS NOT DISTINCT FROM`
conditions on nullable geography keys, DuckDB hoists those conditions to the
top join and runs the inner joins keyed on the remaining low-cardinality
columns alone — a near-cartesian intermediate (observed: a 4-way self-join on
~176k rows allocating ~10 GB before the kernel killed it; the validator now
caps its connection at 4 GB so this fails as a check, but the check is still
wrong). Write it as one scan:

```sql
SELECT COUNT(*) FROM (
  SELECT year, district_code, school_code, demographic,
         MAX(CASE WHEN category = 'total' THEN metric END) AS total,
         MAX(CASE WHEN category = 'a' THEN metric END) AS a,
         MAX(CASE WHEN category = 'b' THEN metric END) AS b
  FROM {object} WHERE category IN ('total', 'a', 'b')
  GROUP BY year, district_code, school_code, demographic
) WHERE total IS NOT NULL AND a IS NOT NULL AND b IS NOT NULL
  AND ABS(total - (a + b)) > <tolerance>
```

`GROUP BY` treats NULL keys as equal, which is exactly the
`IS NOT DISTINCT FROM` semantics the join needed; grain uniqueness (§15a)
guarantees `MAX(CASE ...)` picks the single row per cell. Same-row
reconciliations across *columns* (the `salaries + benefits` example above)
don't involve a join and are unaffected.

---

## 16. Canonical Column Vocabulary

§1 mandates snake_case and column order. Two topics with the same semantic concept can still pick different snake_case names and pass §1 — `number_tested` vs `num_students_tested` vs `n_tested` are all valid snake_case for "count of distinct students tested", but the API can only join cleanly if every topic agrees on one. This section holds the **rationale** for each canonical name; the **enforceable registry** is `src/utils/vocabulary.py` (forbidden variants, suffix rules, sanctioned exemptions), which the validator runs against every gold table (§15a check 15). When this section gains an entry, add the matching variants to the registry in the same change.

### Count of distinct students tested → `num_tested`

For the count of distinct students who took an assessment, use **`num_tested`** (`pl.Int64`). Do NOT use `number_tested`, `num_students_tested`, `total_students_tested`, `n_tested`, or similar.

When a topic publishes a related but distinct count, derive the name from `num_tested`:

- `num_tests_taken` — total tests administered (one student can take multiple tests; AP)
- `num_tests_3_or_higher` — subset count (AP score ≥ 3)
- `num_tested_in_domain` — students tested in a specific sub-domain (WIDA listening, speaking, etc.)

Counts of OTHER entities (enrolled students, completers, dropouts, retained students, etc.) follow the canonical names below — they describe different populations from test-takers.

### Count of students in an enrollment / cohort slice → `student_count`

For the count of distinct students in an enrollment, attendance, or cohort slice (the per-row denominator for rates), use **`student_count`** (`pl.Int64`). Applies to October-1 enrollment, March enrollment, attendance-period enrollment, retention cohorts, and similar. Do NOT use `num_students`, `total_students`, `enrollment_count`, `enrolled_count`, or other variants.

This is distinct from `num_tested` (reserved for assessment-test-taker counts; see above).

**Tiebreaker — `student_count` vs `num_*`.** When a count column names a sub-population *condition* rather than the row's defining denominator, prefer **`num_*`**. Use `student_count` only for the row's headline denominator (enrollment, cohort, attendance period). Examples:

- `num_received_sgp` — subset of test-takers who received an SGP (condition on the sub-population)
- `num_at_proficiency_level` — count at a specific WIDA level (condition)
- `num_with_lexile` / `num_without_lexile` — condition on lexile availability
- `num_<level>_learner` — count at a Milestones proficiency band (condition)

vs.

- `student_count` — the row's enrollment/cohort denominator itself

**Exception — graduation adjusted-cohort denominators keep `cohort_size`.** `graduation_rate_4_year_cohort.cohort_size` and `ccrpi_graduation_rate.cohort_size` retain the name `cohort_size`, not `student_count`. The federal *adjusted four-year cohort* (first-time 9th-graders four years prior, plus transfers in, minus transfers out) is a distinct, federally-defined statistical construct — not a plain enrollment/attendance headcount — and no other topic shares that population, so renaming it to `student_count` would lose the signal without enabling any cross-topic join. The two graduation topics are consistent with each other under `cohort_size`; that is the canonical name for this concept.

### Count of high-school graduates → `graduate_count`

For the count of high-school graduates in the row, use **`graduate_count`** (`pl.Int64`). Do NOT use `graduates` or `total_graduated`.

Distinct from **`completer_count`** (used by `high_school_completers`), which counts graduates plus non-diploma credential completers — different populations, different name.

**Documented exception — SAT `num_tested` is `pl.Float64`**: `sat_scores_recent` and `sat_scores_highest` store `num_tested` as `Float64` rather than `Int64`. Era 5-6 GOSA bronze publishes fractional `INSTN_NUM_TESTED_CNT` on the `Combined Test Score` component because it is computed as a weighted average of per-section test-taker counts (e.g., Math=47 + Reading=37 + WritLang=37 → Combined=40.3). Rounding would silently lose precision on every Composite row from 2020 onward. The column still semantically represents the count of test-takers, so the canonical name is retained — the Float64 type is the schema signal that fractional values are possible. Document this exception explicitly in any new SAT-style topic that inherits the same bronze structure.

### Average of a score-like value → `avg_<thing>`

For the arithmetic mean of a score or score-like value, use the **`avg_`** prefix: `avg_score` (`act_scores`, `sat_scores_recent`, `sat_scores_highest`), `avg_scale_score` (`georgia_milestones_end_of_course`, `georgia_milestones_end_of_grade`), `avg_lexile_score` (the EOC/EOG Lexile topics). Do NOT use `mean_*` or `average_*` for this concept.

Distinct statistics keep their own names: `scale_score_std_dev` (a standard deviation, not an average) and `sgp_median` (a median, not a mean) are correct as-is.

**Sanctioned named-metric exception — `average_daily_*`.** `attendance_dashboard.average_daily_attendance_rate` and `average_daily_absenteeism_rate` keep the spelled-out `average_daily_` prefix. "Average Daily Attendance" (ADA) is a fixed term of art in school finance/reporting; abbreviating it to `avg_daily_*` would obscure a recognized metric name. This is the one sanctioned exception to the `avg_` rule — do not "correct" it.

### Grade level → `grade_level` VARCHAR zero-padded

For the academic grade a student is in, use **`grade_level`** (`pl.Utf8`) with values as **zero-padded 2-char strings**: `'03'`, `'04'`, …, `'12'`. Special values: `'k'` for kindergarten, `'pk'` for pre-kindergarten.

Do NOT use `grade` as the column name, do NOT use `pl.Int32` (loses ability to encode K/PK), do NOT mix padded and unpadded forms across topics.

Distinct concepts that DO keep their own names:

- `grade_cluster` (`elementary`/`middle`/`high`) — a cluster of grades, not a single grade (used by CCRPI topics).
- `grade_configuration` — the comma-separated list of grades a school serves; a school attribute that belongs in the schools dimension, not in fact tables.

For cross-grade aggregate rows (e.g., a published AllGrades SGP median that cannot be reconstructed from per-grade medians), use the canonical aggregate value `'all'`, mirroring the `demographic='all'` pattern.

### CCRPI sub-indicator score → `indicator_score`

For the CCRPI sub-component score column, use **`indicator_score`** (`pl.Float64`) on the natural **0-100 scale** (score columns are exempt from the 0-1 percentage convention per §4 + education CLAUDE.md). Do NOT add a `_pct` suffix — the column is a score, not a rate, and the `_pct` reads as if it were on the 0-1 percentage scale.

Reserved for canonical names elsewhere in education gold:

- `unbenchmarked_rate` — the participation-rate companion to CCRPI score columns. It IS a rate, so it follows the 0-1 decimal scale per §4. Do not write `unbenchmarked_rate_pct`.

### Assessment subject → `subject`

For the academic content area being assessed in a row (Milestones EOC/EOG, GAA, SGM, AP, CCRPI content mastery, Lexile), use **`subject`** (`pl.Utf8`). Do NOT use `content_area` or `test_component` for academic content.

Reserve **`test_component`** strictly for **non-academic test sections** (SAT/ACT math, reading, evidence_based_reading_and_writing, etc.) where the column describes a sub-section of a single composite assessment rather than a subject area.

**`subject` is academic content only — fold metric-family blocks into the parent subject.** When bronze ships a metric block keyed by something like `"SGP English Language Arts"`, `"Reading Status"`, or `"Lexile"`, the metrics in that block describe a sub-population of the parent academic subject's test-takers (e.g., SGP ELA is computed for students who took the ELA EOG). Do NOT emit those rows as separate `subject` values like `sgp_english_language_arts` or `reading_status` — the resulting gold is non-orthogonal (cross-topic queries on `subject = 'english_language_arts'` silently miss the SGP / Lexile data) and inflates row count. Instead, after the per-block unpivot, left-join the metric-family rows onto the parent academic-subject rows by the rest of the natural key (year, geography, grade_level, assessment_type) and drop the metric-family rows. Orphan metric-family rows (no matching parent) should be relabeled to the parent academic content rather than carried as a fake subject. See `georgia_milestones_end_of_grade` for the reference implementation.

Canonical spelling-variant resolutions inside `subject` (resolved by `apply_subject_normalization` in `src/utils/subjects.py`):

| Canonical | Merged variants |
| --- | --- |
| `us_history` | `united_states_history` |
| `9th_grade_literature_and_composition` | `9th_grade_literature`, `ninth_grade_literature`, `ninth_grade_literature_and_composition` |
| `american_literature_and_composition` | `american_literature` |
| `economics_business_free_enterprise` | `economics` |

**Kept distinct on purpose** (these reflect actual Georgia curriculum-era differences, not naming inconsistencies):

- `algebra_i` / `coordinate_algebra` / `algebra_concepts_and_connections` / `algebra_i_coordinate_algebra`
- `geometry` / `analytic_geometry` / `geometry_analytic_geometry`
- `mathematics_1`, `mathematics_2` (CCRPI groupings)

Add new merges only when topics already publish equivalent spellings under different names.

### CCRPI color flag → `ccrpi_flag` with descriptive values

For the CCRPI color flag column, use **`ccrpi_flag`** (`pl.Utf8`) with values **`green`**, **`green_star`**, **`yellow`**, **`red`**. Do NOT keep source codes (`G`, `G*`, `Y`, `R`) — the API exposes descriptive labels, and snake_case categorical normalization applies. Do NOT use the bare column name `flag` because multiple CCRPI topics carry the same concept.

### CCRPI improvement target → `target`

For the CCRPI improvement target on the same scale as an indicator/rate, use **`target`** within CCRPI topics. The topic name already provides the CCRPI context, so do not prefix with `ccrpi_`.

**Scale follows the companion metric — not cross-topic comparable.** `target` inherits the scale of its topic's primary indicator: `ccrpi_content_mastery.target` and `ccrpi_progress.target` are 0-100 (matching `indicator_score`), while `ccrpi_graduation_rate.target` is 0-1 (matching `graduation_rate`). This is correct as a within-topic invariant — `achieved` and `target` must be on the same scale for `achieved >= target` to be meaningful — but it means `target` is NOT cross-topic comparable on raw values. Each topic's contract description for `target` must state the scale explicitly. Analysts comparing across CCRPI topics must always join `target` against the same row's companion metric, never against another topic's `target`.

### Student-Growth-Percentile count → `num_received_sgp`

For the count of students with a Student Growth Percentile in the row, use **`num_received_sgp`** (`pl.Int64`). Do NOT use `n_received_sgp` or `number_received_sgp`.

### Proficiency band columns → `pct_<level>_learner` / `num_<level>_learner`

For Georgia Milestones-style four-level achievement breakdowns, use the canonical pair:

- Percentage: **`pct_<level>_learner`** (`pl.Float64`, 0-1 scale). Levels: `beginning`, `developing`, `proficient`, `distinguished`.
- Count: **`num_<level>_learner`** (`pl.Int64`).
- Cumulative variants: **`pct_<level>_learner_or_above`** (see "Proficiency threshold suffix" below).

Do NOT use `<level>_pct` / `<level>_count` (drops the `_learner` semantic), `<level>_learner_pct` (wrong word order), or `level_<n>_<level>_<…>` (the level index is encoded by the canonical level name — `beginning`=1, `developing`=2, etc.).

Every assessment topic that emits this four-level breakdown should also emit `pct_developing_learner_or_above` and `pct_proficient_learner_or_above` cumulative columns — derive them at transform time so consumers don't have to handle suppression-aware addition in SQL.

### Proficiency threshold suffix → `_or_above`

When a metric describes the share of students at or beyond a learner level, use the suffix **`_or_above`** (not `_and_above`). Examples: `pct_developing_learner_or_above`, `pct_proficient_learner_or_above`.

### Rate names: drop redundant `_pct` / `_rate_pct`

When a metric is conceptually a rate AND already on the 0-1 decimal scale per §4, name it `…_rate` only. Do NOT double-suffix with `_pct`. Examples: `dropout_rate` (not `dropout_rate_pct`), `graduation_rate` (not `graduation_rate_pct`), `mobility_rate`.

### Share-of-denominator metric → `pct_*` prefix

For any column expressing the share of a denominator (share of enrollment, share of cohort, share of credential earners, share of district enrollment) on the 0-1 decimal scale, use the **`pct_*` prefix**. Do NOT use `*_share`, `*_share_of_*_pct`, or any other double-`_pct` variant.

Pick a name that names the denominator: `pct_of_enrollment`, `pct_of_district_enrollment`, `pct_of_retained_cohort`, `pct_of_credential_type`. The companion-count column for the same denominator follows the `num_*` rule below (e.g., `num_retained` ↔ `pct_of_retained_cohort`).

This rule is distinct from the proficiency-band `pct_<level>_learner` pattern (which encodes a level name) and from `…_rate` rates (which describe an event-rate metric like `graduation_rate`); use `pct_of_<denominator>` when the metric is "this row's share of a named total."

### When to extend this list

Add a new canonical entry only when **two or more** topics have already published the same concept under different names. Do not pre-register names speculatively — the vocabulary is meant to encode resolved conflicts, not anticipate them.

---

## Code Review Checklist

For reviewing an existing `transform.py` against shared-utility usage, code quality, pipeline standards, and optimization, see the dedicated [code-review-checklist.md](code-review-checklist.md) in this skill directory. Both `/transform-topic` (the post-authoring self-review step) and `/review-transform` use that file verbatim, so it is the single source of truth — update it there rather than duplicating checks in either skill.

---

## Quick Reference Checklist

When writing or reviewing a `transform.py`, verify:

- [ ] Fact tables contain only keys + metrics (no names, no census IDs, no descriptive attributes)
- [ ] All column names are snake_case
- [ ] Cross-topic concepts use the canonical names from §16 (`num_tested`, `grade_level` VARCHAR zero-padded, `indicator_score` with no `_pct` suffix, proficiency bands as `pct_<level>_learner` / `num_<level>_learner` + `_or_above` cumulatives)
- [ ] `subject` contains only academic content (metric-family blocks like SGP, Reading Status, Lexile are folded into the parent subject row, not emitted as separate subjects) — see §16 "Assessment subject"
- [ ] Racial demographics are mutually exclusive — no synthesized rollup rows alongside split source rows (§5a). Split-convention topics keep `asian` and `pacific_islander` separate; combined-convention topics keep `asian_pacific_islander`; never both within one topic.
- [ ] The `write_data_dictionary` column declaration order matches the Parquet column order (the contract `schema[0].properties[]` is emitted from it and the validator checks parquet against it)
- [ ] Each metric column dict carries a `"unit"` key (`count | proportion | ratio | score | rating | currency | percentile`; unclassifiable columns carry none) — `proportion`/`ratio` are the two percentage cases — so the contract emits the marker and the validator reads the bounded/ratio classification back
- [ ] Fact table column order: year, geography keys, demographic, categoricals, metrics
- [ ] ID columns are strings with leading zeros preserved
- [ ] Percentages/rates are on 0-1 scale (scores and ratings are NOT)
- [ ] Demographics normalized via `normalize_demographic_column()` (or column is omitted if always "all")
- [ ] Aggregate rows have NULL geography key columns (not sentinel strings)
- [ ] Suppressed values are NULL
- [ ] Data is in tidy long format
- [ ] Topic-specific categories are normalized to snake_case
- [ ] `topic` is not in gold parquet files
- [ ] `detail_level` is not in gold parquet files (dropped by `export_to_parquet()`)
- [ ] Geography key columns match domain CLAUDE.md fact table key spec
- [ ] Domain-specific excluded columns are dropped (see domain CLAUDE.md)
- [ ] Demographic subgroup collisions are aggregated, not silently deduped
- [ ] `assert_no_natural_key_collisions()` called before dedup; dedup `sort_col` passed explicitly with the tie-break decision documented
- [ ] Filters log removed rows with sample values
- [ ] Era detection uses column inspection (`detect_era_by_columns`) rather than hardcoded year ranges
- [ ] `TransformManifest` instantiated; `record_bronze` / `record_categorical` / `record_read_loss` called per-file; `record_gold_from_dataframe` / `compute_metric_stats` / `write()` called in `main()` on the final post-dedup DataFrame
- [ ] `unmapped_count == 0` for every recorded categorical; zero unacknowledged read loss
- [ ] `validate_output()` called before export
- [ ] ODCS contract (`contracts/{main}/{topic}.odcs.yaml`) and `README.md` emitted via `write_data_dictionary()` (`src/utils/metadata.py`); metric columns carry `unit` markers
- [ ] Cross-column invariants authored as `quality_checks=` per §15b (partition sums, co-null rules, component reconciliation, structural facts)
- [ ] `main()` ends with `run_topic_validation(GOLD_DIR)` and the run exits 0
