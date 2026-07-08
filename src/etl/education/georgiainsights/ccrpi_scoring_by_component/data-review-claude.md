# Data Review: ccrpi_scoring_by_component

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is value-faithful to bronze across all four eras: every trace executed (26 extreme rows, 6 full-row entity traces, all 9 RTC rows, 5 suppression-marker traces) matched exactly, row counts reconcile 37,279 = 37,279 with an empty filter ledger, and per-detail-level counts match the corrected structure doc in all 12 years. **v1 parity DIFFERS — deliberately, and the +9-row accounting is independently CONFIRMED on all four prongs**: bronze 2015-2017 ships literal `SYSTEM ID == 'RTC'` district rows with real values; the 9 gold RTC rows match bronze cell-for-cell; the delta vs the v1 reconstruction is exactly those 9 rows (0 v1-only rows, 33 of 36 parquet files byte-identical, and the reconstruction re-hashes to the v1 baseline byte-identically); and `RTC` resolves in the districts dimension (`state_special`). Two fixes are required, both metadata-level (no parquet bytes change): the contract's "blank cells in 2023-2025" closing-gaps suppression claim is a type-inference artifact (bronze ships literal `NA` markers — 196/228/207, zero blank cells), and the verified single-score cross-cluster constancy invariant (0 violations over 19,303 entity-years) should be authored as a quality check.

## Manifest Verification

### Categorical mappings

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| grade_cluster | 3 | E, H, M | 0 | PASS |

Full map review — every entry:

| Bronze | Gold | Correct? |
|---|---|---|
| `E` | `elementary` | YES — CCRPI Elementary cluster |
| `M` | `middle` | YES — CCRPI Middle cluster |
| `H` | `high` | YES — CCRPI High cluster |

- **2a Completeness**: structure doc documents exactly E/M/H in every year; `bronze_values_seen` = [E, H, M]. No documented value unseen. PASS.
- **2c Contract cross-check**: contract `enum` = [elementary, high, middle] = `gold_values_produced`. PASS.
- **2d Unmapped**: 0. PASS.
- **2e Asian/PI conflation**: N/A — no `demographic` column (validator: "No demographic column (skipped)"), no `pct_asian` column. This topic has no demographic axis.
- **2f Mutual exclusivity**: N/A — no demographic column.

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Factor |
|---|---|---|---|---|
| 2012 | 2,991 | 2,991 | 0 | 1.0 |
| 2013 | 2,968 | 2,968 | 0 | 1.0 |
| 2014 | 2,978 | 2,978 | 0 | 1.0 |
| 2015 | 3,060 | 3,060 | 0 | 1.0 |
| 2016 | 3,079 | 3,079 | 0 | 1.0 |
| 2017 | 3,069 | 3,069 | 0 | 1.0 |
| 2018 | 3,099 | 3,099 | 0 | 1.0 |
| 2019 | 3,138 | 3,138 | 0 | 1.0 |
| 2022 | 3,200 | 3,200 | 0 | 1.0 |
| 2023 | 3,212 | 3,212 | 0 | 1.0 |
| 2024 | 3,247 | 3,247 | 0 | 1.0 |
| 2025 | 3,238 | 3,238 | 0 | 1.0 |

Total 37,279 = 37,279; actual parquet row sum independently re-counted = 37,279 = manifest `total_gold`. All 12 expected years present (2020/2021 correctly absent — COVID pause). No read-loss, masked-values, or reclassified sections in the manifest (all genuinely zero — whole-sheet Excel reads). Per-detail-level counts match the structure doc's *Corrections* values in all 12 years, including 2015 = 3/586/2,471, 2016 = 3/592/2,484, 2017 = 3/594/2,472 (district counts inclusive of the 3 RTC rows): executed check printed `ALL LEVEL COUNTS MATCH`.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| SCHOOL YEAR / School Year | `year` (derived; in-file assert vs filename) | MAPPED |
| SYSTEM ID / Id variants | `district_code` (zfill 3; `ALL`→NULL; `RTC` kept) | MAPPED |
| SYSTEM NAME | — (districts dimension; used for detail-level cross-check) | CORRECTLY EXCLUDED |
| SCHOOL ID (incl. 2013 trailing space) | `school_code` (zfill 4; `ALL`→NULL) | MAPPED |
| SCHOOL NAME | — (schools dimension; used for cross-check) | CORRECTLY EXCLUDED |
| Grade Configuration (Era 2-4) | — (school attribute, not a fact) | CORRECTLY EXCLUDED |
| GRADE CLUSTER | `grade_cluster` | MAPPED |
| ACHIEVEMENT POINTS | `achievement_points` | MAPPED |
| PROGRESS POINTS | `progress_points` | MAPPED |
| ACHIEVEMENT GAP POINTS | `achievement_gap_points` | MAPPED |
| ED/EL/SWD PERFORMANCE | `ed_el_swd_performance` | MAPPED |
| ETB POINTS | `etb_points` | MAPPED |
| CHALLENGE POINTS | `challenge_points` | MAPPED |
| Content Mastery (incl. 2018 newline) | `content_mastery` | MAPPED |
| Progress | `progress` | MAPPED |
| Closing Gaps (incl. 2018 newline) | `closing_gaps` | MAPPED |
| Readiness | `readiness` | MAPPED |
| Graduation Rate | `graduation_rate` (÷100 → proportion) | MAPPED |
| CCRPI SCORE (incl. 2018 newline) | `ccrpi_score` | MAPPED |
| SINGLE SCORE (incl. 2018 newline) | `ccrpi_single_score` | MAPPED |

The structure doc's Gold Schema Classification proposed `single_score`; the transform emits `ccrpi_single_score` — the canonical cross-topic name (education CLAUDE.md, FESR convention), an improvement, and the validator's canonical-vocabulary check passes. No gold column lacks a bronze ancestor (no fabrication). All renames are exact-match on canonicalized headers with a `_require_columns` guard, so an unmatched bronze column raises rather than silently nulling.

## Value-Level Spot Checks

### 4a Extreme-row traces — global MAX and MIN of all 13 metrics (26 traces)

All 26 MATCH, 0 mismatches. Highlights (bronze quoted from string-typed reads):

| Metric | Kind | Entity | Bronze | Gold |
|---|---|---|---|---|
| achievement_points | MAX | 2012 d=644 s=0288 E | `'59.9'` | 59.9 MATCH |
| achievement_points | MIN | 2015 d=644 s=1100 M | `'2.6'` | 2.6 MATCH |
| progress_points | MAX | 2015 d=604 district M | `'40'` | 40.0 MATCH |
| achievement_gap_points | MAX | 2012 d=618 district H | `'15'` | 15.0 MATCH |
| etb_points | MAX | 2014 d=705 s=5050 E | `'3'` | 3.0 MATCH |
| content_mastery | MIN | 2023 d=799 s=1893 M | `'0'` | 0.0 MATCH |
| graduation_rate | MAX | 2018 d=7830103 district H | `'100'` | 1.0 MATCH (÷100) |
| graduation_rate | MIN | 2018 d=648 s=0507 H | `'0'` | 0.0 MATCH |
| ccrpi_score | MAX | 2016 d=667 s=1019 H | `'110.3'` | 110.3 MATCH (bonus overshoot preserved per §4b) |
| ccrpi_single_score | MIN | 2013 d=7991895 district E | `'8'` | 8.0 MATCH |

Geography sentinels (`SYSTEM ID`/`SCHOOL ID == 'ALL'`) were resolved to NULL before the gold lookups; 7-digit charter codes (7830103, 7991895) and unpadded bronze school codes traced correctly through zfill.

### RTC pseudo-district — all 9 rows traced (parity scrutiny target)

Bronze 2015/2016/2017 each ship exactly 3 rows with literal `SYSTEM ID='RTC'`, `SYSTEM NAME='Residential Treatment Center'`, `SCHOOL ID='ALL'`, `SCHOOL NAME='All RTC Schools'`. Example bronze line (2015 H): `RTC | Residential Treatment Center | ALL | All RTC Schools | H | 11.3 | 27.7 | 3.3 | <blank> | 0 | 0 | 42.3 | 40.8` → gold `year=2015, district_code='RTC', school_code=NULL, grade_cluster='high', achievement=11.3, progress=27.7, gap=3.3, ed_el_swd=NULL, etb=0.0, challenge=0.0, ccrpi_score=42.3, single_score=40.8`. All 9 rows match cell-for-cell, land as district-level rows (school_code NULL), and satisfy the points-era reconciliation where applicable (2015 H: 11.3+27.7+3.3+0 = 42.3 exact; 2016 H: 12+30.1+5.6+0 = 47.7 exact; 2017 M: 16+28.6+3.3+0 = 47.9 exact).

### 4b Ordinary traces — one entity per era, all 13 columns

- **Era 1**: 2013 Glynn Academy (663/4752/H) — all 13 columns MATCH (47.2/16.1/13.8/3.4/0/3.4/80.5/80.5; score-era columns absent→NULL).
- **Era 2**: 2017 Grovetown Middle (636, bronze `'103'` → gold `0103`, M) — all 13 MATCH (29.8/31.4/5/0.5/1/1.5/67.7/67.7).
- **Era 3**: 2019 Cherokee High (628/5050/H) — all 13 MATCH incl. `Graduation Rate '81.3'` → 0.813.
- **Era 4**: 2024 Greenville High (699, bronze `'300'` → gold `0300`, H) — all 13 MATCH incl. `'85'` → 0.85; aggregate columns absent→NULL.
- **State rows**: 2019 E state (`SYSTEM ID='ALL'`) — all MATCH incl. `Graduation Rate 'NA'` → NULL; 2022 H state — Content Mastery `'64.7'` → 64.7, Readiness `'73.2'` → 73.2, Graduation Rate `'84.7'` → 0.847, and Progress/Closing Gaps/CCRPI Score/Single Score all literal `'NA'` → NULL (COVID blackout, rows retained).

### 4c Sentinel year-attribution

Year comes from the filename's first 4-digit token and is asserted equal to the single-valued in-file `SCHOOL YEAR` in every file (`_assert_in_file_year` — a disagreement raises). The 2014 file, whose name embeds the 03.10.2016 publication date, lands at year=2014 (manifest: 2,978 rows = the 2014 file). PASS.

### 4d Aggregate feasibility screen (aggregates come from bronze)

District values vs their school rows' [min, max] per (year, district, cluster): small out-of-range deviations exist (e.g., ccrpi_score 1,350/4,661 district rows outside, mostly by tenths of a point; worst case 2019 d=891 Dept. of Juvenile Justice H content_mastery 9.4 vs school range [2.2, 5.3]). Both worst-case rows were traced to bronze and match exactly: 2012 d=607 H district `CCRPI SCORE='73.7'` = gold 73.7; 2019 d=891 H `CONTENT MASTERY='9.4'` = gold 9.4. These deviations are source methodology — GaDOE computes each aggregation level's CCRPI independently from student-level indicator attainment (with caps/ETB earned at the aggregate level), and suppressed school rows remove range coverage — not transform garbling. State rollups lie inside the district [min, max] for all years tested (0/24 ccrpi_score, 0/18 content_mastery outside). No impossibly-low aggregates pattern. PASS.

### 4e Dedup tie-break

N/A — 12 files map to 12 distinct years (no overlap years); natural key unique within every file (0 duplicates, re-verified by the transform's collision guard + the no-op assertion that dedup removed 0 rows).

### 4f Suppression semantics — one trace per marker type

| Marker | Bronze cell | Gold | Verdict |
|---|---|---|---|
| `NA` | 2019 state E `Graduation Rate='NA'`; 2022 state H `Progress='NA'` | NULL | MATCH |
| `TFS` | 2019 Price Academy (611/0307/E) `CONTENT MASTERY='TFS'` | NULL | MATCH |
| `Too Few Students` | 2018 Price Academy (611/0307/E) `CONTENT MASTERY='Too Few Students'` | NULL | MATCH |
| blank cell | 2013 Appling County Primary (601/0277/E) `ED/EL/SWD=''` (one of 82) | NULL | MATCH |
| `NA` (Era 4 Closing Gaps) | 2024 Baker County Learning Academy (604/0183/H) `CLOSING GAPS='NA'` | NULL | MATCH |

2018 `Too Few Students` confirmed in THREE columns (CM=68, RD=21, GR=28 — matching the structure doc's Corrections item 3). Suppression-count reconciliation: 2019 graduation_rate gold null_count 2,500 = bronze `NA` 2,475 + `TFS` 25 exactly; Era 4 closing_gaps gold null counts 196/228/207 = bronze `NA` counts 196/228/207 exactly.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning**; `contract_parquet_schema` (36 files), `contract_quality_sql` (14 checks), `grain_uniqueness`, `foreign_keys` (district_code → districts: all 246 keys resolve, incl. `RTC`; school_code → schools: all 2,576 resolve), and geography_nulling ×3 all pass. The single warning is the 8 NULL-rate spikes on ccrpi_score/ccrpi_single_score 2022-2025 — fully explained by documented bronze structure (2022 COVID blackout `NA`, 2023+ columns dropped at source) and pinned by the `aggregate_scores_null_from_2022` quality check.
- Contract `schema_hash`: `f645754de4375353548b0277aa3d05a986ea906620d6d72ded655ddfe07739f0`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest carries no `masked_values` / `read_loss` / `reclassified` sections (verified zero occurrences). Consistent with the claim that every observed bronze value is in-domain — extreme traces corroborate (Era 3-4 scores within [0,100]; >100 values only on the unbounded Era 1-2 aggregates, preserved + documented). PASS.
- **§15b coverage judgment**: 7 authored checks (era-scoped NULL structure ×3, 2022 blackout, exact points-era component reconciliation, co-null trio, graduation-rate-high-only) + 6 auto-derived range checks + enum. Strong coverage — with one gap: the verified single-score cross-cluster constancy invariant is stated in the contract description but unenforced (Fix 2).
- **v1 parity** (executed output, verbatim):

```
DIFFERS from v1
  v1:  f9fd2660901fb92bb9477a10cbca5da4b9d5b35714198f3ac249628a8b95d75b
  now: e7652fb48c392dda31e796a3b2be4a0ca38d5580e87b433a5c37742b390c1d25
```

**DIFFERS accounting — independently verified, CONFIRMED:**

1. **Control re-hash**: `/tmp/v1_scoring_by_component.py` is byte-identical to `git show v1-pipeline:src/etl/.../transform.py` (diff clean); its patched run (`/tmp/v1_csc_patched.py`, only GOLD_DIR redirect + contract-emit stub) produced `/tmp/v1_gold_csc`, which re-hashes to `f9fd2660…` — **exactly the v1 baseline**. The reconstruction is faithful.
2. **File-level delta**: 36 vs 36 parquet files, none added/removed; **33 byte-identical**; only `year=2015/districts.parquet`, `year=2016/districts.parquet`, `year=2017/districts.parquet` differ.
3. **Row-level delta**: anti-joins both directions → **0 v1-only rows; exactly 3 current-only rows per year = 9 total**, all `district_code='RTC'`, one per grade cluster.
4. **Bronze ground truth**: bronze 2015/2016/2017 each ship 3 literal `SYSTEM ID='RTC'` rows with real metric values (quoted above) — refuting v1's drop premise (that the rows had no district code and appeared only in 2017; that premise was a polars Int64-inference artifact, now corrected in the structure doc's Corrections section). RTC is allowlisted in the districts dimension (`state_special`) and the FK resolves; sibling topics publish the same entity (verified in gold: ccrpi_content_mastery RTC years 2015-2017, ccrpi_graduation_rate RTC years 2015-2018).

The deliberate parity break **recovers 9 previously-dropped published bronze rows** and is correct. The accompanying `src/etl/education/CLAUDE.md` edit (adding `ccrpi_scoring_by_component` (2015-2017) to the RTC source-topics cell) is accurate per the gold verification above.

## Cross-Era Consistency

- **Overlap years**: none (one file per year).
- **Cross-year NULL sweep**: 13 FLAGs, every one the documented era structure — six points metrics 100% NULL 2018+; five score metrics 100% NULL 2012-2017; progress/closing_gaps additionally 2022 (COVID); aggregates 100% NULL 2022+; graduation_rate also ~80% NULL within score-era years (non-high clusters, quality-checked). No column 100% NULL in every year; no era-localized rename-bug signature (each column fully populated in its source era).
- **Era-boundary continuity (state level)**: no >10x jumps. Level shifts only at documented framework changes — progress_points 2014→2015 ratio 2.14 (component redesign, max 22→40) and achievement_points 2014→2015 ratio 0.65 (same redesign); ed_el_swd/challenge drift 2013→2014 and 2016→2017 (small absolute values, points-era rubric drift). Score-era columns are stable across the 2019→2022→2023 boundary. State-level challenge = ed_el_swd + etb in every points year, consistent with the contract description.
- **Single-score structure**: `ccrpi_single_score` is constant across an entity's cluster rows in all years it is published — 0 violations over 17,664 school-, 1,631 district-, and 8 state-entity-years.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_require_columns` guard fails loudly; only names/Grade Configuration deliberately unselected (dimension concerns) |
| Era routing correctness | PASS | Signature detection on canonicalized headers, specificity-ordered (Era 3 before 4, Era 2 before 1); manifest eras match the structure doc 12/12 |
| Filter logic | PASS | No filters; ledger empty; expansion factor 1.0 all years; 37,279 in = 37,279 out |
| Normalization map completeness | PASS | GRADE_CLUSTER_MAP covers all bronze values; `replace_strict(default=None)` + manifest unmapped gate |
| `strict=False` casts | PASS | Residual-non-numeric net only; suppression handled at read (`na_values=SUPPRESSION_VALUES`); gold null counts reconcile with bronze marker counts exactly (2019 grad rate 2,500 = 2,475 NA + 25 TFS) |
| Dedup keys + tie-break | PASS | Collision guard before dedup; dedup asserted no-op (raises on any removal) |
| Year extraction | PASS | Filename token + in-file `SCHOOL YEAR` assert; publication-date filenames immune |
| §4b masking (5b) | PASS | No masks; no manifest mask sections; in-domain extremes verified |
| Contract prose accuracy | FLAG | "Blank cells in 2023-2025" closing-gaps suppression claim is wrong (Fix 1) |
| Quality-check coverage (5c) | FLAG | Single-score constancy invariant unenforced (Fix 2) |

## Required Fixes

### Fix 1: Correct the closing_gaps "blank cells in 2023-2025" suppression prose (contract notes + null_meaning)
- **Severity**: LOW
- **Issue**: The contract's notes claim "2023-2025 ship Closing Gaps suppression as blank cells rather than markers" and the `closing_gaps` `null_meaning` says "Suppressed at source (`NA`, or blank cells in 2023-2025)". Both are wrong: Era 4 bronze ships the literal string `NA` in Closing Gaps — there are no blank cells. Gold data is unaffected (the `NA` strings become NULL via `na_values=SUPPRESSION_VALUES` at read), but the contract misdescribes the source. The structure doc's Era 4 note ("no `NA`/`TFS` strings appear in the actual cells, so polars infers Float64 with true nulls") carries the same polars type-inference artifact the doc's own Corrections section fixed for three sibling claims but missed here.
- **Evidence**: String-typed reads (`dtype=str, keep_default_na=False`): 2023 CLOSING GAPS non-numeric values = `{'NA': 196}`, 2024 = `{'NA': 228}`, 2025 = `{'NA': 207}`; NaN = 0 and empty-string = 0 in all three. Gold closing_gaps null counts are 196/228/207 — the `NA` counts exactly. Trace: 2024 Baker County Learning Academy (604/0183/H) `CLOSING GAPS='NA'` → gold NULL.
- **Location**: `_emit_contract_and_readme()` in transform.py — the suppression-markers `notes` entry and the `closing_gaps` column's `null_meaning`; optionally amend the bronze-data-structure.md Era 4 note as a sixth Corrections item.
- **Suggested fix**: Reword to state that 2023-2025 Closing Gaps suppression uses the literal `NA` marker like the other score columns (the doc's Float64/true-null reading was a polars inference artifact). Re-run the transform to re-emit the contract; parquet bytes are unchanged so parity evidence stands.

### Fix 2: Author the single-score cross-cluster constancy quality check
- **Severity**: MEDIUM
- **Issue**: The contract's `ccrpi_single_score` description asserts the column is "the cross-cluster rollup, so an entity spanning multiple clusters repeats one value across its rows" — a real, verified structural invariant that is not enforced by any quality check, so a future republish that garbles it (e.g., a cluster-score/single-score column swap) would pass validation.
- **Evidence**: Executed check on gold: 0 of 17,664 school-entity-years, 0 of 1,631 district-entity-years, and 0 of 8 state years have more than one distinct non-NULL `ccrpi_single_score` within (year, district_code, school_code).
- **Location**: `quality_checks=` list in `_emit_contract_and_readme()` in transform.py.
- **Suggested fix**: Add a check like `single_score_constant_per_entity_year`: `SELECT COUNT(*) FROM (SELECT year, district_code, school_code FROM {object} WHERE ccrpi_single_score IS NOT NULL GROUP BY year, district_code, school_code HAVING COUNT(DISTINCT ccrpi_single_score) > 1)` with `mustBe: 0`. Re-run the transform (contract-only change; parquet unchanged).

## Notes

- schema_hash: `f645754de4375353548b0277aa3d05a986ea906620d6d72ded655ddfe07739f0`
- Validation: 20 pass / 0 fail / 1 warning (warning = documented 2022-2025 aggregate blackout NULL spikes).
- Both fixes are metadata/contract-level: applying them re-emits the contract without touching parquet bytes, so the verified +9-row parity accounting remains valid afterward (drift hashes only cover `.parquet`).
- No NEEDS_JUDGMENT items: the only borderline observation — district aggregates falling outside their school rows' [min, max] — was resolved with bronze evidence (flagged rows match bronze exactly; GaDOE computes each aggregation level independently, so derivability is not a contract claim).
- S3 not touched (known-broken AWS profile); review conducted entirely against local bronze/gold and the /tmp v1 reconstruction.
