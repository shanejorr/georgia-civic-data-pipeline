# Data Review: attendance_dashboard

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Gold output is byte-identical with the approved v1 baseline (**v1 parity: MATCH**, sha256 `690a98e3133cf90eae81413ac781d8e9f719e5ddc2044aa074043f8c212be65c`, recomputed independently). All 28 demographic map entries are semantically correct, bronze−gold row counts reconcile exactly (386,836 = 386,836, 1.00x every year, 0 filtered), all 12 value-level spot traces MATCH (extremes first), and the aggregate feasibility screen is clean. Validation: 21/21 PASS, 0 warnings. No required fixes, no judgment items.

## Manifest Verification

**Preconditions**: FRESH (transform mtime 12:17:24 < manifest 12:18:02 ≤ validation 12:18:02), `passed: true`, read_loss events: 0 (Excel reads load whole sheets; raw == parsed by construction).

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|--------:|------------:|---------:|--------|
| demographic | 28 | 28 | 0 | PASS |

**2a Completeness**: the manifest's 28 `bronze_values_seen` exactly equal the 28 distinct `Subgroup` values documented in bronze-data-structure.md (lexicon identical across all 8 years per the doc; confirmed — no documented value is unseen, no seen value is undocumented).

**2b Full map review (every entry)** — all 28 verified semantically correct:

| Bronze (upper-cased key) | Gold | Correct? |
|--------------------------|------|----------|
| ALL | all | Yes — unfiltered total |
| AMERICAN INDIAN/ALASKAN NATIVE | native_american | Yes — canonical race key |
| ASIAN/PACIFIC ISLANDER | asian_pacific_islander | Yes — explicit combined bucket → combined key (§5b); NOT `asian` |
| BLACK | black | Yes |
| HISPANIC | hispanic | Yes |
| MULTI-RACIAL | multiracial | Yes |
| WHITE | white | Yes |
| MALE / FEMALE | male / female | Yes |
| ECONOMICALLY DISADVANTAGED | economically_disadvantaged | Yes |
| ENGLISH LEARNER | english_learners | Yes — singular bronze → canonical plural |
| HOMELESS | homeless | Yes |
| MIGRANT | migrant | Yes |
| KINDERGARTEN | kindergarten | Yes — grade-in-demographic policy (long-form key) |
| GRADE 1 … GRADE 12 | grade_1 … grade_12 | Yes — all 13 grade entries checked individually; no off-by-one (GRADE 10→grade_10, GRADE 11→grade_11, GRADE 12→grade_12) |
| STUDENT WITH DISABILITIES | students_with_disabilities | Yes — singular → canonical plural |
| STUDENT WITHOUT DISABILITIES | students_without_disabilities | Yes — complement key, not conflated with the "with" key |

**2c Contract cross-check**: `gold_values_produced` == contract `enum` == distinct values in gold parquet (executed: `gold parquet == contract enum: True`, `manifest produced == contract enum: True`, n=28).

**2d Unmapped**: 0.

**2e Asian/PI (Risk 1)**: PASS — gold emits `asian_pacific_islander` from the explicit combined bronze label `Asian/Pacific Islander` (bronze never publishes a separate Asian or Pacific Islander row in any year, per the structure doc's dedicated check). Math test run as positive evidence:

```
Race buckets present: ['asian_pacific_islander', 'black', 'hispanic', 'multiracial', 'native_american', 'white']
student_count: year=2025 total=1749935 race_sum=1749935 ratio=1.0000 -> TIES_OUT
```

The six race buckets (with the combined bucket included) sum exactly to the `all` total — the combined-bucket convention is complete and correct.

**2f Mutual exclusivity (Risk 6)**: PASS — single convention. `gold_values_produced` contains `asian_pacific_islander` only; the split `asian` / `pacific_islander` keys are never emitted.

**Row-count reconciliation (3a/3b)**:

| Year | Bronze (doc) | Manifest bronze | Gold parquet | Factor |
|-----:|-------------:|----------------:|-------------:|-------:|
| 2018 | 47,870 | 47,870 | 47,870 | 1.00 |
| 2019 | 47,953 | 47,953 | 47,953 | 1.00 |
| 2020 | 47,970 | 47,970 | 47,970 | 1.00 |
| 2021 | 48,073 | 48,073 | 48,073 | 1.00 |
| 2022 | 48,398 | 48,398 | 48,398 | 1.00 |
| 2023 | 48,623 | 48,623 | 48,623 | 1.00 |
| 2024 | 48,948 | 48,948 | 48,948 | 1.00 |
| 2025 | 49,001 | 49,001 | 49,001 | 1.00 |
| **Total** | **386,836** | **386,836** | **386,836** | **1.00** |

Per-file totals in the manifest match the structure doc's per-sheet sums exactly; 0 filtered rows, no expansion. Detail-level splits also reconcile against the doc's per-sheet detail counts (e.g., 2025: districts 6,025 = 234+2,755+3,036; schools 42,948 = 2,301+11,375+29,272; states 28 = 1+13+14). States parquet has exactly 28 rows in every year (1 `all` + 13 grade + 14 subgroup).

## Column Coverage

| Bronze Column | Gold Column | Status |
|---------------|------------|--------|
| `School \nYear` | `year` (Int32) | MAPPED — cross-checked against filename year with hard raise |
| `System \nID` | `district_code` | MAPPED — "All"→NULL, zfill(3), 7-digit charter codes preserved |
| `System Name` | — | CORRECTLY EXCLUDED — dimension attribute (districts.parquet) |
| `School \nID` | `school_code` | MAPPED — "All"→NULL, zfill(4) |
| `School Name` | — | CORRECTLY EXCLUDED — dimension attribute (schools.parquet) |
| `Group` | — | CORRECTLY EXCLUDED — redundant after Subgroup→demographic mapping |
| `Subgroup` | `demographic` | MAPPED — shared canonical aliases, 28→28 |
| `Total \nStudents` | `student_count` | MAPPED — canonical §16 name (`total_students` is the forbidden variant; doc Corrections section records the amendment) |
| `Chronically Absent \n(10% or more)` | `chronically_absent_rate` | MAPPED — 0-1 scale preserved |
| `Average Daily Absenteeism Rate` | `average_daily_absenteeism_rate` | MAPPED — 0-1 scale preserved |
| `Average Daily Attendance Rate` | `average_daily_attendance_rate` | MAPPED — 0-1 scale preserved |

All 11 bronze columns accounted for; no gold column lacks a bronze source (no fabrication). The five embedded-`\n` headers are mapped by exact full-name keys in `COLUMN_RENAME`, and `_require_columns` raises if any expected header is absent (rename-typo guard). `detail_level` is derived from the documented "All" sentinel quadrants and dropped at export.

## Value-Level Spot Checks

All traces quote bronze read directly from the xlsx (pandas `dtype=str`, same path as the transform). 12/12 MATCH.

**Extreme rows (4a):**

| # | Trace | Bronze (file, sheet, row) | Gold | Verdict |
|---|-------|---------------------------|------|---------|
| T1 | Global ADAR max / ADAtt min | 2019 Subgroups: `654` Evans County / `197` Second Chance / Hispanic / Total=15 / CA=0.933 / ADAR=**0.763** / ADAtt=**0.237** | year=2019, `654`/`0197`, hispanic, 15, 0.933, 0.763, 0.237 | MATCH |
| T2 | Global student_count max | 2018 All Students: System ID=All / School ID=All / Subgroup=All / Total=**1777720** / 0.12 / 0.049 / 0.951 | year=2018, NULL/NULL, all, 1777720, 0.12, 0.049, 0.951 | MATCH (sentinels → NULL) |
| T9 | Global student_count min (=1) | 2018 Grade Level: `761`/`306` / Grade 10 / Total=**1** / TFS / TFS / TFS | year=2018, `761`/`0306`, grade_10, 1, NULL, NULL, NULL | MATCH |
| T8 | chronically_absent max 2018 (0.97) + 7-digit district | 2018 Subgroups: `7820108` Mountain Education Charter / School ID=All / Multi-Racial / 67 / **0.97** / 0.543 / 0.457 | year=2018, `7820108`/NULL, multiracial, 67, 0.97, 0.543, 0.457 | MATCH (7-digit code passes zfill(3) untouched) |
| T11 | chronically_absent global max (1.0) | 2025 Subgroups: `7820108` / All / American Indian/Alaskan Native / 20 / **1** / 0.606 / 0.394 | year=2025, `7820108`/NULL, native_american, 20, 1.0, 0.606, 0.394 | MATCH |
| T12 | ADAtt max (1.0) / ADAR min (0.0) / chronic min (0.0) | 2025 All Students: `611`/`1311` / All / 468 / **0** / **0** / **1** | year=2025, `611`/`1311`, all, 468, 0.0, 0.0, 1.0 | MATCH (perfect attendance, plausible) |

**Ordinary traces (4b — one per sheet, latest year):**

| # | Trace | Bronze | Gold | Verdict |
|---|-------|--------|------|---------|
| T3 | All Students sheet | 2025: `721` Richmond County / `399` Richmond Hill ES / All / 913 / 0.284 / 0.081 / 0.919 | `721`/`0399`, all, 913, 0.284, 0.081, 0.919 | MATCH (zfill `399`→`0399`) |
| T4 | All Students, 4-digit school | 2025: `644` DeKalb / `2055` Druid Hills HS / All / 1568 / 0.393 / 0.108 / 0.892 | `644`/`2055`, all, 1568, 0.393, 0.108, 0.892 | MATCH (4-digit unchanged) |
| T5 | Grade Level sheet, district row | 2025: `755` Whitfield / School ID=All / Grade 3 / 960 / 0.107 / 0.048 / 0.952 | `755`/NULL, grade_3, 960, 0.107, 0.048, 0.952 | MATCH |
| T6 | Subgroups sheet, gender | 2025: `781` Marietta City / `101` Marietta HS / Female / 1330 / 0.379 / 0.110 / 0.890 | `781`/`0101`, female, 1330, 0.379, 0.11, 0.89 | MATCH |

**Suppression traces (4f):**

| # | Trace | Bronze | Gold | Verdict |
|---|-------|--------|------|---------|
| T7 | TFS in Subgroups sheet | 2025: `755` Whitfield / `206` Beaverdale ES / Black / Total=5 / TFS / TFS / TFS | `755`/`0206`, black, **5**, NULL, NULL, NULL | MATCH — all-or-nothing, count preserved |
| T10 | Suppression in All Students sheet | 2025: `604` Baker County / `183` Baker County Learning Academy / All / Total=11 / TFS | `604`/`0183`, all, 11, NULL, NULL, NULL | MATCH — gold 2025 `demographic='all'` null-rate rows = exactly 4, matching the doc's count |

**4c Sentinel year-attribution (Risk 3)**: N/A — no year-bearing data strings; the only year literals in transform.py are docstrings and the era label. Year comes from `extract_year_from_filename` and is hard-cross-checked against the in-sheet `School \nYear` values (`raise` on mismatch) — stronger than the typical pattern.

**4d Aggregate feasibility screen (Risk 4)**: aggregates COME FROM BRONZE (state/district rows published per sheet) — screen executed:
- State vs sum-of-districts (`demographic='all'`): ratio 1.027–1.038 across all 8 years (district sums slightly exceed state — consistent with within-year student mobility double-counting; stable, no swaps or garbling).
- District vs schools, 2025: 234 districts, **0** impossible-low cases (district < max school), school_sum/district ratio quantiles p01=1.000 / median=1.0003 / p99=1.062, **0** outliers outside [0.95, 1.10].

**4e Dedup tie-break (Risk 5)**: N/A — single era, one file per year, bronze grain unique per file (collision guard ran before dedup; bronze=gold row counts at 1.00x confirm zero rows were deduped away).

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning** — `contract_parquet_schema` (24 files), `contract_quality_sql` (9 checks), `grain_uniqueness` (year, district_code, school_code, demographic), `foreign_keys` (district_code → districts: 243 keys; school_code → schools: 2,409 keys; demographic → demographics: 28 keys — all resolve), `geography_nulling` ×3 all pass.
- Contract `schema_hash`: `a6612a3cbb342e862ca44104b12973b872cf3265e86fae6b63408667f9bb740d`; version 1.0.0.
- **§4b masking audit (5b)**: no `_null_*` helpers in transform.py; manifest has no `masked_values` section (zero events). Consistent — no masks exist or are needed (manifest min/max confirm every metric within its unit bounds; max ADAR 0.763, max chronic 1.0, all ≤ 1).
- **§15b coverage judgment (5c)**: adequate. The three authored checks capture this topic's real cross-column invariants — `attendance_absenteeism_complement` (|ADA+ADAR−1| ≤ 0.005), `rate_suppression_all_or_nothing`, `student_count_never_null` — on top of the auto-derived proportion/count range checks and the demographic enum check. No obvious invariant is missing (district=Σschools is not an exact source invariant due to mobility double-counting, so it correctly lives in this review's feasibility screen rather than enforced SQL).
- **v1 parity (5d)** — executed output, verbatim:

```
MATCH — byte-identical with v1 gold
v1 : 690a98e3133cf90eae81413ac781d8e9f719e5ddc2044aa074043f8c212be65c
now: 690a98e3133cf90eae81413ac781d8e9f719e5ddc2044aa074043f8c212be65c
```

## Cross-Era Consistency

- Single era (2018–2025, identical 11-column 3-sheet layout); no overlap years, no era boundaries.
- Cross-year NULL sweep (3c): **clean** — "NULL sweep: clean — no era-localized NULL columns". No column is ≥95% NULL in any year.
- Year-over-year continuity (3d): state `all` row is smooth — student_count 1.74M–1.78M (no jumps); chronically_absent_rate 0.12/0.121/0.081/0.201/0.239/0.226/0.213/0.195. The 2020 dip and the 2021–22 surge are the well-documented COVID-era attendance pattern (2020 measured largely pre-closure; chronic absenteeism roughly doubled statewide post-pandemic), not a scale artifact — complements stay exact (ADA+ADAR=1.0) throughout. No >10x jumps; no cumulative-publication signature.
- Per-year rate null counts in gold exactly match the manifest (2018: 6,962 … 2025: 6,750), and 2025's 6,750 decomposes as 4 (All Students) + 309 (Grade Level) + 6,437 (Subgroups) per the structure doc.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|------|----------|-------------------|
| Silent column drops | none | PASS — `_require_columns` raises on any missing expected header; the 3 unselected columns are documented dimension/redundant attributes |
| Era routing correctness | none | PASS/N-A — single era; local `_read_data_sheets` reads exactly the 3 named data sheets (Read Me never ingested); `pl.concat(how="vertical")` raises on schema mismatch |
| Filter logic logged + justified | none | PASS — no row filters; `total_filtered: 0`; empty-file skip is logged |
| Normalization map completeness | none | PASS — shared `DEMOGRAPHIC_ALIASES` via `normalize_demographic_column`; effective slice recorded in manifest; unmapped guard active (0) |
| `strict=False` casts | none | PASS — used only to coerce residual suppression strings to NULL; student_count's Float64→Int64 hop produced 0 NULLs in all years (manifest), so nothing was silently lost |
| Dedup keys + tie-break | none | PASS — `assert_no_natural_key_collisions` runs BEFORE dedup; `sort_col="student_count"` is a documented defensive tie-break that never fired (1.00x row parity) |
| Year extraction | none | PASS — filename year hard-cross-checked against in-sheet `School \nYear` (raise on mismatch); bad-quadrant guard (System=All + concrete school) also raises |
| §4b masks (5b) | none | N/A — no masks; none needed |

## Notes

- schema_hash `a6612a3cbb342e862ca44104b12973b872cf3265e86fae6b63408667f9bb740d`; validation 21/21 pass, 0 warnings; manifest read_loss 0 events.
- Documentation nuance (no data impact): the structure doc's Null Counts / Suppression Markers tables describe the All Students sheet's suppressed cells as "numeric null", but in the raw 2025 xlsx those 4 cells are the literal string `TFS` (pandas `dtype=str` read shows `TFS`, `isna=0`; likely a polars-inference artifact at doc-generation time). The transform's `na_values=SUPPRESSION_VALUES` handles both representations identically, and the gold result is verified correct (T10; exactly 4 null-rate `all` rows in 2025). No fix needed; recording for future doc readers.
- District sums exceed the state total by ~3% in every year (mobility double-counting in the source). Expected source behavior — stable across years; analysts summing district rows should be aware. The contract's grain/usage prose already directs users to the published state rows.
- `deduplicate_by_detail_level` and the geography-nulling step are shared utilities operating on the same `detail_level` the validator re-derives — verified consistent (geography_nulling ×3 pass).
