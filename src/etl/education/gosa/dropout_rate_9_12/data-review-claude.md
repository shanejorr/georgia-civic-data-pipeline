# Data Review: dropout_rate_9_12

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Gold is **byte-identical with v1** (`compute_gold_sha256` matches `docs/rebuild/v1-baseline.yaml`), all 21 validator checks pass, every categorical mapping is semantically verified against the shared alias module, and every value-level trace (extremes, ordinary rows, both suppression eras, the 28 reclassified 2022 rows) matches bronze exactly. The §5b math test proves the combined Asian/Pacific Islander convention with an EXACT partition (ratio 1.0000) at the state level. The single open item is a documentation typo in `bronze-data-structure.md` (2021 TFS count listed as 7,089; bronze verifiably contains 7,247) — no gold impact, routed to NEEDS_JUDGMENT because this review may not edit that file.

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze values seen | Unmapped | Status |
|--------|---------|--------------------|----------|--------|
| demographic | 15 | 15 (= all 15 labels documented in the structure doc, prefix-stripped) | 0 | PASS |
| detail_level | 3 | 3 (State, District, School) | 0 | PASS |

### Full map review — demographic (every entry checked against `src/utils/demographics.py` `DEMOGRAPHIC_ALIASES`)

| Bronze (post-prefix-strip, upper) | Gold | Correct? |
|---|---|---|
| ALL STUDENTS | all | YES — total row |
| ASIAN/PACIFIC ISLANDER | asian_pacific_islander | YES — explicit combined bronze label → combined key (§5b; math test below) |
| BLACK | black | YES |
| HISPANIC | hispanic | YES |
| WHITE | white | YES |
| MULTI-RACIAL | multiracial | YES |
| AMERICAN INDIAN/ALASKAN | native_american | YES — canonical key for AI/AN |
| MALE | male | YES |
| FEMALE | female | YES |
| ECONOMICALLY DISADVANTAGED | economically_disadvantaged | YES |
| NOT ECONOMICALLY DISADVANTAGED | not_economically_disadvantaged | YES |
| STUDENTS WITH DISABILITY | students_with_disabilities | YES |
| STUDENTS WITHOUT DISABILITY | students_without_disabilities | YES |
| LIMITED ENGLISH PROFICIENT | english_learners | YES — canonical key for LEP |
| MIGRANT | migrant | YES |

All 15 entries equal the shared `DEMOGRAPHIC_ALIASES` values (executed comparison: 15/15 `OK`). detail_level: `State→state`, `District→district`, `School→school` — all correct.

**2c contract cross-check**: `gold_values_produced` (15) == contract `enum` (15) == gold parquet distinct values (executed: `True`). **2d**: `unmapped_count = 0` on both columns.

### §5b Asian/Pacific Islander (Risk 1) — PASS with positive evidence

Bronze publishes the explicit combined label (`9-12 Drop Outs -Asian/Pacific Islander`) and no separate Pacific Islander row anywhere (structure doc grep: only combined-label hits). Math test (executed):

```
year=2024  dropout_count: all=16616 race_sum=16616 ratio=1.0000 -> EXACT PARTITION   (male+female=16616, ratio 1.0000)
year=2011  dropout_count: all=19139 race_sum=19139 ratio=1.0000 -> EXACT PARTITION   (male+female=19139, ratio 1.0000)
```

The six race buckets partition the total exactly — Pacific Islanders are folded in, not dropped. The convention is also pinned for every year by the `state_race_partition_sums_to_all` contract check (passing).

### §2f mutual exclusivity (Risk 6) — PASS, single convention

Gold emits only `asian_pacific_islander`; the split `asian` / `pacific_islander` keys never appear (contract enum + gold distincts confirm). No rollup/split coexistence in any category.

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Factor |
|------|--------|------|----------|--------|
| 2011 | 9,885 | 9,885 | 0 | 1.0 |
| 2012 | 9,960 | 9,960 | 0 | 1.0 |
| 2013 | 9,900 | 9,900 | 0 | 1.0 |
| 2014 | 9,990 | 9,990 | 0 | 1.0 |
| 2015 | 10,230 | 10,230 | 0 | 1.0 |
| 2016 | 10,275 | 10,275 | 0 | 1.0 |
| 2017 | 10,155 | 10,155 | 0 | 1.0 |
| 2018 | 10,500 | 10,500 | 0 | 1.0 |
| 2019 | 10,575 | 10,575 | 0 | 1.0 |
| 2020 | 9,940 | 9,940 | 0 | 1.0 |
| 2021 | 10,052 | 10,052 | 0 | 1.0 |
| 2022 | 10,122 | 10,122 | 0 | 1.0 |
| 2023 | 10,920 | 10,920 | 0 | 1.0 |
| 2024 | 11,130 | 11,130 | 0 | 1.0 |
| **Total** | **143,634** | **143,634** | **0** | |

Assessment: perfect 1:1 row preservation, all 14 expected years present, per-year bronze counts match the structure doc's tables exactly. Actual parquet row count (executed) = **143,634** = manifest `total_gold` = **v1's row count**. Per-year parquet counts == manifest `by_year` (executed: `True`). Gold metric non-null counts tie exactly to bronze suppression counts in 13 of 14 years per the structure doc; the one mismatch (2021) is a doc typo, not a data issue — bronze 2021 verifiably has 7,247 TFS cells and zero blanks/other residue (see NEEDS_JUDGMENT).

## Column Coverage

| Bronze Column | Gold Column | Status |
|---------------|------------|--------|
| #RPT_NAME (Era 1 only) | — | CORRECTLY EXCLUDED — constant `"9-12 Dropouts"`, guarded by `_validate_era1_constants` (raises on any other value) |
| LONG_SCHOOL_YEAR | year | MAPPED — `parse_school_year`, cross-checked vs filename (raises on disagreement) |
| DETAIL_LVL_DESC | — | CORRECTLY EXCLUDED — drives geography nulling + detail-split filenames; dropped by `export_to_parquet` |
| SCHOOL_DSTRCT_CD | district_code | MAPPED — zfill(3), `ALL` sentinel → NULL |
| SCHOOL_DSTRCT_NM | — | CORRECTLY EXCLUDED — dimension attribute (districts dim) |
| INSTN_NUMBER | school_code | MAPPED — zfill(4), `ALL` sentinel → NULL |
| INSTN_NAME | — | CORRECTLY EXCLUDED — dimension attribute (schools dim) |
| GRADES_SERVED_DESC | — | CORRECTLY EXCLUDED — institution metadata, topic already 9-12-scoped |
| LABEL_LVL_1_DESC | demographic | MAPPED — prefix `"9-12 Drop Outs -"` stripped, shared alias normalization |
| PROGRAM_TOTAL | dropout_count | MAPPED — Int64 via exact Float64 hop |
| PROGRAM_PERCENT | dropout_rate | MAPPED — Float64, ÷100 to 0-1 proportion |

Every gold column traces to bronze (no fabrication); both eras carry all `REQUIRED_BRONZE_COLUMNS` (manifest `bronze_columns` per file confirm; the guard raises on absence).

## Value-Level Spot Checks

Extreme rows first (global max/min per metric), all executed against bronze CSVs:

1. **dropout_count global MAX** — 2017 state `ALL Students`: bronze `PROGRAM_TOTAL='21500', PROGRAM_PERCENT='3.8'` (`SCHOOL_DSTRCT_CD='ALL', INSTN_NUMBER='ALL'`) → gold `(2017, NULL, NULL, all, 21500, 0.038)`. **MATCH**.
2. **dropout_rate global MAX** — 2012 `625/0209` Black (Savannah Gateway to College, an alternative school): bronze `'44' / '93.6'` → gold `(44, 0.936)`. **MATCH** — extreme but bronze-real.
3. **dropout_rate global MIN** — 2012 district `706` (Muscogee County, `INSTN_NUMBER='ALL'`) economically_disadvantaged: bronze `'13' / '0.2'` → gold `(13, 0.002)`. **MATCH**.
4. **dropout_count global MIN (=10, the suppression threshold)** — 2011 district `602` (Atkinson County) ALL Students: bronze `'10' / '2.1'` → gold `(10, 0.021)`. **MATCH** (2,273 rows share the min — consistent with an n=10 threshold).
5. **Ordinary, Era 2 (2011)** — Phoenix High `667/0189` economically_disadvantaged: bronze `'152' / '33'` → gold `(152, 0.33)`. **MATCH**.
6. **Ordinary, Era 1 (2024)** — Vidalia City district `793` (INSTN_NUMBER='ALL') students_without_disabilities: bronze `'11' / '1.6'` → gold `(11, NULL school_code, 0.016)`. **MATCH**.
7. **Suppression, blank era (2011)** — Brantley County High `613/1050` Multi-Racial: bronze `PROGRAM_TOTAL=None, PROGRAM_PERCENT=None` → gold both NULL. **MATCH**.
8. **Suppression, TFS era (2022)** — Richmond County `721/0213` Not Economically Disadvantaged: bronze `'TFS' / 'TFS'` → gold both NULL. **MATCH**.

**2022 reclassification trace (manifest `reclassified`: 28 rows):** bronze 2022 has exactly 28 rows with `DETAIL_LVL_DESC='School'` AND `INSTN_NUMBER='ALL'` — 14 for `7830627` (Atlanta SMART Academy) + 14 for `7830636` (Northwest Classical Academy), all `PROGRAM_TOTAL='TFS'`. Bronze 2022 has **zero** genuine District rows for those codes (no collision possible — these districts have no other 2022 rows at all in this topic). 2023 publishes the same codes as `DETAIL_LVL_DESC='District'` with `INSTN_NUMBER='ALL'` (15 rows each — convention restored). Gold 2022 carries all 28 as district rows (`school_code` NULL, both metrics NULL). A full scan of all 14 bronze files finds the School+ALL mislabel **only in 2022 (28 rows)** — the generic repair fires nowhere else. **MATCH — repair verified end to end.**

**Year attribution (4c):** the only year-bearing parsing is `parse_school_year(LONG_SCHOOL_YEAR)`, hard-cross-checked against the filename year (raises on disagreement). `_2011.csv` carries the single value `'2010-11'` → gold `year=2011`. **PASS** — no sentinel-year risk.

**Aggregate-row feasibility screen (4d, suppression-heavy variant):** aggregates COME FROM BRONZE (never derived). Executed the impossibly-LOW screen across all years: of **12,191** (year, district, demographic) groups with a published district count and ≥1 visible school row — `district < max(school)`: **0** violations; `district < sum(visible schools)`: **0** violations. State level (185 (year, demographic) groups): `state < sum(visible districts)`: **0** violations. Visible-sum coverage spans 0.19–0.99 of the aggregate, always ≤ 1 — exactly the undercount signature heavy suppression predicts. **PASS**.

**Dedup tie-break (4e):** N/A — 14 files map to 14 distinct years (manifest `files_processed`), per-file grain unique; dedup removed zero rows (143,634 in = 143,634 out).

## Validation Cross-Read

- `_validation.json`: **passed=true, 21 pass / 0 fail / 0 warning** — includes `contract_parquet_schema` (42 files), `contract_quality_sql` (all 12 checks), `grain_uniqueness` (year, district_code, school_code, demographic), `foreign_keys` (district_code → districts: 241 keys; school_code → schools: 619 keys; demographic → demographics: 15 keys), geography nulling for all three detail levels.
- `schema_hash`: `3fc2466c7ccb0dbe743f50879e78d5cf39c1f6c2494810b608855754f0551466`.
- **§4b masking audit (5b)**: no `_null_*` helpers exist in transform.py and the manifest has no `masked_values` section — consistent, and justified: bronze scan found no impossible values (`PROGRAM_TOTAL` ∈ [10, 21500], `PROGRAM_PERCENT` ∈ [0.2, 93.6] on the 0-100 source scale, confirmed by manifest metric stats ×100). **PASS — N/A masks.**
- **§15b coverage judgment (5c)**: 8 authored checks (co-suppression, state-never-suppressed, count ≥ 10 threshold, four partition-sum checks — race/gender/economic/disability, english_learners 2020-2022 gap) + 4 auto-derived = 12 total. This covers every cross-column invariant the topic actually has (rate has no enrollment denominator column to cross-check; district-level partitions are unverifiable under suppression). **PASS — no missing obvious invariant.**
- **v1 parity (5d)**, executed output verbatim:

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **Overlap years**: none — each file is one school year; era boundary is 2022 (era_2) → 2023 (era_1), detected per file in the manifest (12× era_2, 2× era_1, matching the structure doc).
- **Era-boundary continuity**: state `all` dropout_count 2022→2023: 19,590 → 18,872 (−3.7%) — smooth. Full adjacent-pair sweep 2011-2024: no >1.5x jumps anywhere; the largest move is the COVID dip 2019→2020 (19,306 → 14,500, 0.75x) which reverts upward in 2021 — bronze-real, mirrored in the rate (0.034 → 0.026).
- **Cross-year NULL sweep (3c)**: clean — no column is ~100% NULL in any year subset (executed; no era-localized rename signature). Metric NULL rates drift gradually 63%→75% (suppression growth), matching bronze suppression counts.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `REQUIRED_BRONZE_COLUMNS` guard raises on any missing source column; both eras verified in manifest |
| Era routing | PASS | Most-specific-first signatures (`era_1` requires `#RPT_NAME`); 2023/2024 → era_1, 2011-2022 → era_2 per manifest; `#RPT_NAME` constant guard raises on foreign report rows |
| Filter logic | PASS | No row filters; `filtered=0` every year; bronze total = gold total |
| Normalization map completeness | PASS | 15/15 documented labels mapped via shared `DEMOGRAPHIC_ALIASES`; `unmapped_count=0`; manifest records the effective alias slice |
| `strict=False` casts | PASS | Suppression already NULLed at read time; executed scan of 2021 (the one doc-discrepant year): 7,247 TFS + 2,805 numeric + 0 other non-numeric = 10,052 rows — gold non-null 2,805 ties exactly, so nothing real was silently nulled; ≥10-threshold + co-suppression checks would catch residue |
| Dedup keys + tie-break | PASS | Natural-key collision guard (incl. `detail_level`) runs BEFORE dedup; no overlap years; zero rows removed |
| Year extraction | PASS | Single `LONG_SCHOOL_YEAR` per file enforced; cross-checked against filename year; mismatch raises |
| §4b masking (5b) | PASS | No masks exist; none needed (no impossible values in any bronze file) |

## NEEDS_JUDGMENT

### Judgment Call 1: structure doc's 2021 TFS count is wrong (7,089 vs actual 7,247)
- **Severity if confirmed**: LOW
- **Suspicion**: `bronze-data-structure.md` (Era 2 statistics table, line ~157) states 2021 `PROGRAM_TOTAL` has `TFS (7,089 rows)`; bronze actually contains 7,247. 7,089 is exactly the 2022 value — almost certainly a copy-paste error in the doc.
- **Evidence available**: executed scan of `dropout_rate_9_12_2021.csv`: `PROGRAM_TOTAL: nulls=0 TFS=7247 other_non_numeric=0 numeric=2805` (same for `PROGRAM_PERCENT`); 2022 scan: `TFS=7089` (matches the doc's 2022 row). Gold 2021 `null_count=7247` / `non_null_count=2805` tie exactly to bronze, and bronze checksums are unchanged — so the data and transform are correct; only the doc cell is wrong. All other 13 years' doc counts tie exactly.
- **Why uncertain**: the fact is confirmed; the judgment is disposition — this review may only edit `data-review-claude.md`, and amending a checksummed analysis artifact (`bronze-data-structure.md`, generated 2026-05-22) is the maintainer's call, not a transform fix.
- **Location**: `data/bronze/education/gosa/dropout_rate_9_12/bronze-data-structure.md`, Era 2 statistics table, 2021 row (and the corresponding "TFS (7,089 rows)" suppression-marker note if present).
- **If confirmed, suggested fix**: one-cell doc correction: 2021 `PROGRAM_TOTAL`/`PROGRAM_PERCENT` suppression marker count 7,089 → 7,247. No transform, gold, or contract change — gold is byte-identical with v1.

## Notes

- `schema_hash`: `3fc2466c7ccb0dbe743f50879e78d5cf39c1f6c2494810b608855754f0551466`; validation 21 pass / 0 fail / 0 warning; contract quality checks: 12 (8 authored + 4 auto-derived).
- v1 parity: **MATCH — byte-identical with v1 gold** (and v1 also produced 143,634 rows). Any approval can carry the existing baseline forward.
- Risk hypotheses: 1 PASS (combined-label, exact-partition evidence), 2 PASS (NULL sweep clean), 3 PASS (cross-checked year parse), 4 N/A→screen PASS (aggregates from bronze; 0 feasibility violations), 5 N/A (no overlap years), 6 PASS (single convention), 7 PASS (15/15 semantically verified).
- The dropout_rate global max 0.936 (Savannah Gateway to College, 2012) and 0.813/0.811 (2021/2024) are alternative-school rates — extreme but conceivable and bronze-exact; preserved per §4b, bounded by the contract's `[0,1]` proportion check.
