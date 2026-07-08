# Data Review: georgia_milestones_end_of_course_eoc_lexile_scores

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is a faithful 1:1 projection of bronze — 10,082 bronze rows = 10,082 gold rows, zero filtered, zero read-loss, zero masking — and **v1 parity is MATCH (byte-identical with v1 gold)**. Every transform-agent claim was independently re-verified against all 9 bronze files (sentinel↔DETAIL_LEVEL agreement, the 45-of-140 NO_LEXILE_SCORE complement disagreements with max gap 99 in 2021, the 2 source-exception rows, 9th-grade retirement after 2021) and all held with executed output. One MEDIUM fix: the clean subset invariant `num_without_lexile <= num_tested` (zero violations in all 140 observable bronze rows) was not authored as a quality check while its two sibling subset checks were — an un-authored invariant is unenforced forever (§15b). The fix touches only the contract, not the parquet, so v1 parity survives.

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze seen | Unmapped | Status |
| --- | --- | --- | --- | --- |
| detail_level | 3 | 3 (matches structure doc exactly) | 0 | PASS |
| subject | 2 | 2 (matches structure doc exactly) | 0 | PASS |

### Full map review (every entry)

| Bronze | Gold | Correct? |
| --- | --- | --- |
| `State Level` | `state` | YES — verified against the "All"/"All" sentinel pattern (0 disagreements in 10,082 rows, executed) |
| `District Level` | `district` | YES — district code real, INSTN_NUMBER = "All" (0 disagreements) |
| `School Level` | `school` | YES — both geography codes real (0 disagreements) |
| `9th Grade Literature and Composition` | `9th_grade_literature_and_composition` | YES — the §16 canonical target in `src/utils/subjects.py` (lines 43–45 map the `ninth_grade_…` variants TO this form); same value used by the EOC assessment-by-grade sibling contract |
| `American Literature and Composition` | `american_literature_and_composition` | YES — canonical per `subjects.py` line 46–47 |

Contract cross-check (2c): contract `subject` enum = exactly the 2 values in `gold_values_produced`. `detail_level` is correctly absent from the contract properties (dropped at export; encoded in `schools/districts/states.parquet` filenames, and the contract's `detail_levels` custom property lists all three). Unmapped (2d): 0 for both columns.

Bronze-value re-verification (executed over all 9 files): distinct `DETAIL_LEVEL` = exactly the 3 mapped literals; distinct `SUBJECT_CODE` = exactly the 2 mapped literals; the only non-numeric value in either geography column is title-case `"All"` (no uppercase `"ALL"` anywhere — the transform's `BRONZE_ALL_SENTINEL = "All"` choice is exactly right).

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Expansion |
| --- | --- | --- | --- | --- |
| 2015 | 1,422 | 1,422 | 0 | 1.0 |
| 2016 | 1,442 | 1,442 | 0 | 1.0 |
| 2017 | 1,467 | 1,467 | 0 | 1.0 |
| 2018 | 1,477 | 1,477 | 0 | 1.0 |
| 2019 | 1,489 | 1,489 | 0 | 1.0 |
| 2021 | 747 | 747 | 0 | 1.0 |
| 2022 | 678 | 678 | 0 | 1.0 |
| 2023 | 679 | 679 | 0 | 1.0 |
| 2024 | 681 | 681 | 0 | 1.0 |
| **Total** | **10,082** | **10,082** | **0** | **1.0** |

Actual parquet rows (executed): 10,082, per-year identical to the manifest. Independent bronze re-read (executed, all 9 CSVs): 10,082 rows. Expected years per the structure doc all present; 2020 genuinely absent (COVID — EOC suspended); the 2021 drop to ~50% volume and the 2022+ drop to ~680 rows (9th-grade course retired) reproduce the structure doc's per-file row counts exactly.

## Column Coverage

| Bronze column | Gold column | Status |
| --- | --- | --- |
| SCHOOL_YEAR | `year` (via filename, hard-stop cross-check) | MAPPED — 0 of 10,082 rows disagree with the filename year (executed) |
| DETAIL_LEVEL | (encoded in output filename) | CORRECTLY EXCLUDED per §12 |
| SCHOOL_DSTRCT_CD | `district_code` | MAPPED — "All"→NULL, zfill(3) |
| SCHOOL_DSTRCT_NM | — | CORRECTLY EXCLUDED (dimension attribute) |
| INSTN_NUMBER | `school_code` | MAPPED — "All"→NULL, zfill(4) |
| INSTN_NAME | — | CORRECTLY EXCLUDED (dimension attribute) |
| SUBJECT_CODE | `subject` | MAPPED |
| TOTAL_STUDENTS_TESTED | `num_tested` | MAPPED |
| STUDENTS_WITH_LEXILE | `num_with_lexile` | MAPPED |
| LEXILE_ON_OR_ABOVE_MIDPOINT | `num_at_or_above_lexile_midpoint` | MAPPED |
| NO_LEXILE_SCORE | `num_without_lexile` | MAPPED |
| AVG_LEXILE_SCORE | `avg_lexile_score` | MAPPED |

No fabricated gold columns — every gold column traces to a bronze column or the filename year. No `demographic` column (bronze has no subgroup axis — correct omission per §5) and no `grade_level` (course-based reporting; the row axis is the EOC course — verified, no grade column in any bronze header).

## Value-Level Spot Checks

All verdicts below quote the bronze line, then the gold row. Bronze geography sentinels (`"All"`) resolved to NULL before gold lookup.

**Extreme traces (4a):**

1. **Global max `avg_lexile_score` = 1679.3** — bronze 2016 line 884: `2016,School Level,667,Gwinnett County,1019,"Gwinnett School of Mathematics, Science and Technology",American Literature and Composition,205,205,201,TFS,1679.3` → gold (2016, 667, 1019, american_literature): num_tested=205, num_with_lexile=205, num_at_or_above=201, num_without=NULL, avg=1679.3. **MATCH** (a STEM magnet school — plausible extreme).
2. **Global min `avg_lexile_score` = 707.0** — bronze 2023 line 672: `2023,"School Level","799","State Schools","1893","Atlanta Area School for the Deaf","American Literature and Composition","15","15","TFS","TFS","707"` → gold (2023, 799, 1893): 15/15/NULL/NULL/707.0. **MATCH** (state school for the deaf — plausible low Lexile average; `799` is the documented state-school district prefix).
3. **Global max `num_tested` = 140,677 / `num_with_lexile` = 140,436** — bronze 2017 line 1467: `2017,State Level,All,All,All,All,9th Grade Literature and Composition,140677,140436,95620,241,1242.5` → gold 2017 state row (NULL/NULL geography): 140677/140436/241/95620/1242.5. **MATCH**.
4. **Global max `num_at_or_above_lexile_midpoint` = 96,933** — bronze 2019 line 1489: `...,9th Grade Literature and Composition,136933,136797,96933,135,1286.1` → gold 2019 state row identical. **MATCH**.
5. **Global max `num_without_lexile` = 488** — bronze 2016 line 1442 (state, 9th grade): `140209,139721,88039,488,1225.5` → gold 2016 state 9th-grade row: num_without_lexile=488. **MATCH**.
6. **Count minimum (10)** — bronze 2024 line 539: `"711","Peach County","0392","Peach County Achievement Academy",...,"10","10","TFS","TFS","1062"` → gold (2024, 711, 0392): 10/10/NULL/NULL/1062.0. **MATCH**.

**Ordinary trace (4b, single era):** bronze 2015 lines 1119–1120 (Rockmart High School, district 715, **unpadded** INSTN_NUMBER `102`): 9th grade `239,239,124,TFS,1138.8`; American Lit `194,194,103,TFS,1275.4` → gold (2015, 715, **0102**): both rows match all five metrics, school code correctly zfill(4)-reconciled. Late-era spot: bronze 2024 line 553 (Cross Creek High, 721, pre-padded `0100`): `287,287,65,TFS,1119.9` → gold identical. **MATCH ×2**.

**The two documented source-exception rows** (num_tested reported, num_with_lexile not): executed scan over all 9 files found **exactly 2** such rows, precisely the documented pair:
- bronze 2015 line 1123: `2015,School Level,715,Polk County,207,Harpst Academy,9th Grade Literature and Composition,10,,,TFS,` → gold (2015, 715, 0207, 9th grade): num_tested=10, all four other metrics NULL. **MATCH**.
- bronze 2016 line 433: `2016,School Level,612,Bleckley County,115,Bleckley County Success Academy,9th Grade Literature and Composition,10,,,TFS,` → gold (2016, 612, 0115, 9th grade): num_tested=10, rest NULL. **MATCH**.
- Nuance: in both rows the missing cells are **empty strings**, not `TFS` (see Notes — minor structure-doc inaccuracy, identical NULL outcome).

**Sentinel year-attribution (4c):** N/A in the Risk-3 sense — no year-bearing bronze strings other than SCHOOL_YEAR itself, which the transform hard-stop asserts equals the filename year (re-verified: 0 mismatches in 10,082 rows). The transform's only year literal (`year > 2021`) is the 9th-grade retirement check, verified against bronze (0 9th-grade rows after 2021 in bronze).

**Aggregate feasibility screen (4d, aggregates COME FROM BRONZE):** executed across all years:
- District vs visible school rows (2,732 joined groups): `district num_tested < max school` = **0**; `district num_tested < visible school sum` = **0**.
- District weighted-average reconciliation: in all 2,322 groups where school `num_with_lexile` sums exactly to the district's, the lexile-weighted school average matches the published district `avg_lexile_score` within 1.0L — **0 mismatches**.
- State vs district rollup (15 pairs): coverage ratio 0.9997–0.99996 every year/subject; state `avg_lexile_score` vs district-weighted average agrees to <0.2L everywhere; **0** impossibly-low aggregates.
No swap/garbling signature anywhere.

**Dedup tie-break (4e):** N/A — each bronze file is a distinct year (manifest `files_processed`), so no overlap years exist; `assert_no_natural_key_collisions` + grain-uniqueness (validator check 16, pass) confirm no within-year duplicates survived.

**Suppression semantics (4f):** `TFS` is the sole marker (verified: only non-numeric metric value in any file). Trace: bronze 2016 line 434 (Bleckley Success Academy, American Lit) `17,17,TFS,TFS,1028.5` → gold (2016, 612, 0115, american_literature): num_tested=17, num_with_lexile=17, num_at_or_above=**NULL**, num_without=**NULL**, avg=1028.5. **MATCH** — TFS→NULL per marker, row and valid columns preserved. Validator `no_suppression_markers` passes (no residue).

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning**; `contract_parquet_schema` (27 parquet files), `contract_quality_sql` (13 checks), `grain_uniqueness` (year, district_code, school_code, subject), `foreign_keys` (206 district keys, 763 composite school keys all resolve), and geography nulling ×3 all pass. Fresh: transform mtime 00:06:15 < manifest 00:06:28 ≤ validation 00:06:28 (2026-06-12 UTC).
- `schema_hash`: `91988a21c74436d9a28b26a926ea0b21fb149ac023b7482cdca1d4d78790f691`.
- **§4b masking audit (5b)**: no `_null_*` helpers in transform.py (grep: none); manifest has no `masked_values` / `reclassified` / `read_loss` sections (absent = zero events). Consistent — nothing impossible exists to mask: avg_lexile_score observed 707.0–1679.3 (manifest per-year min/max), inside the contract's [0, 2000] `score` guard; no negative counts. PASS.
- **§15b coverage judgment (5c)**: the 6 authored cross-column checks are individually verified correct against bronze (executed: `with > tested` = 0, `mid > with` = 0, `avg XOR with` = 0, `mid without with` = 0, `with without tested` = 0, 9th-grade-after-2021 = 0). The deliberate **omission of a with+without=tested partition check is correct** — re-verified: 45 of the 140 fully-numeric rows violate the complement identity (40 with `num_without_lexile` above the complement, 5 below; per-year 1–7; max gap 99 at the 2021 state row `65925/65851/173`), so the identity is unenforceable. However, the **subset invariant `num_without_lexile <= num_tested` holds with 0 violations in all 140 observable rows and was not authored** → Fix 1.
- **v1 parity (5d)**, executed output verbatim: `MATCH — byte-identical with v1 gold`.

## Cross-Era Consistency

Single era — all 9 files share the identical 12-column header (manifest `files_processed` confirms per file); era detection by column signature would hard-fail on drift. No overlap years; no era-boundary discontinuities to check. Cross-year NULL sweep (Risk 2): no column is ~100% NULL in a subset of years; `num_without_lexile` is ≥95% NULL in **every** year (97.4–99.9%) — explained, not a rename bug: bronze NO_LEXILE_SCORE is TFS in 677–1,386 of ~679–1,489 rows per year per the structure doc, and the manifest's non-null counts (32/37/18/21/14/8/4/1/5 by year) match the doc's "only 1–37 rows per year" exactly. Year-over-year state-level continuity (3d): no >10x jumps and no revert-pattern level shifts except the documented COVID 2021 dip (9th grade collapses to 81 students tested statewide; American Lit to 65,925) which recovers in 2022 — both documented in the contract and README. The school-code padding era quirk (2015–2019 unpadded vs 2021–2024 padded) is correctly reconciled (Rockmart `102` → `0102` trace above), so entities key identically across years.

## Transform Logic Risks

| Risk | Severity | Details |
| --- | --- | --- |
| Silent column drops | PASS | Only SCHOOL_DSTRCT_NM / INSTN_NAME dropped (dimension attributes, documented); `_require_columns` hard-stops on any missing expected column |
| Era routing | PASS | Single signature; `detect_era_by_columns` + raise on no-match |
| Filter logic | PASS | Zero rows filtered (manifest `total_filtered: 0`); only an empty-file skip path (logged), never triggered |
| Normalization map completeness | PASS | Both maps cover 100% of bronze values seen (executed distinct-value scans); `replace_strict` default `"99999999"` + manifest unmapped guard would raise on drift |
| `strict=False` casts | PASS | Applied to all 5 metrics after all-Utf8 read (`infer_schema_length=0` preserves leading zeros); TFS pre-nulled by `read_bronze_file` |
| Dedup keys + tie-break | PASS | Explicit `sort_col="num_tested"`, collision guard first; pure safety net (no duplicate keys exist) |
| Year extraction | PASS | Filename year hard-stop cross-checked against SCHOOL_YEAR (0/10,082 mismatches, executed) |
| §5b masking (5b) | PASS | No masks; nothing impossible to mask |
| Asian/PI conflation (Risk 1) | N/A | No demographic column in bronze or gold; `NO_NHPI_LABEL_IN_BRONZE` (executed grep) |
| Mutual exclusivity (Risk 6) | N/A | No demographic column — single implicit "All Students" population |
| Sentinel year-attribution (Risk 3) | PASS | See 4c |
| Aggregation error (Risk 4) | PASS | Aggregates from bronze; feasibility screen 0 violations (see 4d) |
| Dedup inversion (Risk 5) | N/A | No overlap years |

## Required Fixes

### Fix 1: Author the missing `num_without_lexile <= num_tested` subset quality check
- **Severity**: MEDIUM
- **Issue**: The contract enforces both sibling subset invariants (`lexile_population_within_tested`: with ≤ tested; `midpoint_count_within_lexile_population`: mid ≤ with) but not the third member of the family: `num_without_lexile` is by its own contract description a "Count of **tested** students who did NOT receive a usable Lexile measure" — a subset of `num_tested`. Per §15b, an invariant a careful reviewer would verify by hand must be authored, else it is unenforced forever. (This is distinct from the correctly-rejected complement identity: the subset bound is not violated by the 45 complement disagreements.)
- **Evidence**: Executed over all 9 bronze files and over gold: `bronze rows where NO_LEXILE_SCORE > TOTAL_STUDENTS_TESTED: 0` (of 140 rows where both are numeric); `gold wo > t violations: 0`. The bound is real, observable, and currently passing — it just isn't pinned. A companion reporting implication also holds with zero exceptions (every one of the 140 numeric `num_without_lexile` rows has `num_tested` AND `num_with_lexile` reported) and may be authored in the same pass.
- **Location**: `_emit_contract_and_readme()` in `transform.py` — `quality_checks=` list.
- **Suggested fix**: Add `{"name": "without_lexile_within_tested", "dimension": "consistency", "query": "SELECT COUNT(*) FROM {object} WHERE num_without_lexile IS NOT NULL AND num_tested IS NOT NULL AND num_without_lexile > num_tested", "mustBe": 0}` (optionally plus `without_lexile_reported_implies_tested_reported`). Re-run the transform; gold parquet bytes are unchanged (contract-only change), so v1 parity is preserved — verify with `compute_gold_sha256`.

## Notes

- `schema_hash`: `91988a21c74436d9a28b26a926ea0b21fb149ac023b7482cdca1d4d78790f691`; validation 21 pass / 0 fail / 0 warning; v1 parity `MATCH — byte-identical with v1 gold`.
- All headline transform-agent claims independently reproduced: 10,082=10,082 with empty ledger; title-case `"All"` sentinel with 0 sentinel↔DETAIL_LEVEL disagreements across all 9 files; 45-of-140 complement disagreements (max gap 99, 2021 state row); exactly 2 tested-without-with exception rows (2015 Polk 715/0207 Harpst Academy, 2016 Bleckley 612/0115 Success Academy); 0 9th-grade rows after 2021 in bronze; 2021 9th-grade = 84 gold rows; avg_lexile observed 707.0–1679.3.
- **Structure-doc inaccuracy (no gold impact)**: the "Null Counts" section claims "No literal null values appear in any column of any file — every cell contains either a numeric string or the literal `All`/`TFS` sentinel." False for at least 2015 (e.g., line 1123 `…,10,,,TFS,` and line 1124 `…,,,,,` — Harpst Academy) and 2016 line 433: the metric cells are **empty**, not `TFS`. The transform handles both identically (empty → NULL on read; strict=False residue), and the validator passes, so this is a documentation nit only — worth a one-line amendment to the structure doc on a future pass. Relatedly, the contract's description of the 2 exception rows as "suppressed" is a benign simplification (the bronze cells are blank, not TFS-marked).
- The structure doc's consideration 3 advises "Zero-padding district codes … would corrupt the 7-digit charter codes, so leave district codes as-is"; the transform uses `zfill(3)`, which is a no-op on 3- and 7-digit codes and matches the domain CLAUDE.md convention — no conflict in effect (verified: only `601`–`793` and 7-digit `7820xxx/7830xxx` codes exist; FK check passes for all 206 districts).
- This topic has **no demographic and no grade_level column** by design (course-based, all-students reporting) — the EOG Lexile sibling is the grade-based one. Consumers should not expect to join this topic on a demographic axis.
