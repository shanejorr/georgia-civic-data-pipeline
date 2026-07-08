# Data Review: enrollment_by_grade_level

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Value-level accuracy is verified: every bronze→gold trace (global max, true-zero min, ordinary rows in both eras, TFS suppression, the 52-row twin drop) MATCHes, the 52-row drop replay confirms all of the transform's claims exactly, and **v1 parity is MATCH — byte-identical with v1 gold**. One MEDIUM contract-hardening fix is required: the suppression-era floor (no published `student_count` < 10 from 2021 on) is documented in the structure doc and holds in gold but is not authored as a quality check, so it is unenforced. One LOW judgment item: GOSA's published state/district aggregates do not tie exactly to component sums (a source characteristic, faithfully preserved), which may deserve a limitations caveat.

## Manifest Verification

Preconditions: FRESH (transform mtime 22:26:14 < manifest 22:26:21 ≤ validation 22:26:21), `passed: true`, `read_loss` events: 0.

### Categorical mappings

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `enrollment_period` | 2 | 2 (`Fall`, `Spring`) | 0 | PASS |
| `grade_level` | 13 | 13 (`K`, `1st`–`12th`) | 0 | PASS |

Full map review (every entry):

| Bronze | Gold | Correct? |
|---|---|---|
| `Fall` | `fall` | Yes — fall snapshot (GaDOE October FTE collection) |
| `Spring` | `spring` | Yes — spring snapshot (March collection) |
| `K` | `k` | Yes — kindergarten, canonical §16 code |
| `1ST` | `01` | Yes |
| `2ND` | `02` | Yes |
| `3RD` | `03` | Yes |
| `4TH` | `04` | Yes |
| `5TH` | `05` | Yes |
| `6TH` | `06` | Yes |
| `7TH` | `07` | Yes |
| `8TH` | `08` | Yes |
| `9TH` | `09` | Yes |
| `10TH` | `10` | Yes |
| `11TH` | `11` | Yes |
| `12TH` | `12` | Yes |

Mapping is via the shared `normalize_grade_column` / `GRADE_LEVEL_MAP` (§10a), with the manifest recording the observed-spellings slice. `gold_values_produced` equals the contract `enum` for both columns (`fall`/`spring`; `01`–`12` + `k`). Verified directly in bronze that `PK` and `ALL` never appear in `GRADE_LEVEL` (checked 2011, 2016, 2022, 2024) — the contract's "no `pk`/`all`" claim holds. `unmapped_count` = 0 for both.

- **2e Asian/PI conflation**: N/A — gold has no `demographic` column and no `pct_asian` column (bronze publishes no demographic breakdown; every row is a total count).
- **2f Mutual exclusivity**: N/A — no demographic column.

### Row-count reconciliation

| Year | Bronze | Filtered | Gold (manifest) | Gold (parquet, counted) | Match |
|---|---|---|---|---|---|
| 2011 | 64,428 | 0 | 64,428 | 64,428 | ✓ |
| 2012 | 64,610 | 0 | 64,610 | 64,610 | ✓ |
| 2013 | 64,194 | 0 | 64,194 | 64,194 | ✓ |
| 2014 | 63,947 | 0 | 63,947 | 63,947 | ✓ |
| 2015 | 64,038 | 0 | 64,038 | 64,038 | ✓ |
| 2016 | 64,311 | 0 | 64,311 | 64,311 | ✓ |
| 2017 | 64,441 | 0 | 64,441 | 64,441 | ✓ |
| 2018 | 64,636 | 0 | 64,636 | 64,636 | ✓ |
| 2019 | 64,753 | 0 | 64,753 | 64,753 | ✓ |
| 2020 | 64,818 | 0 | 64,818 | 64,818 | ✓ |
| 2021 | 65,130 | 0 | 65,130 | 65,130 | ✓ |
| 2022 | 65,312 | 52 | 65,260 | 65,260 | ✓ |
| 2023 | 28,250 | 0 | 28,250 | 28,250 | ✓ |
| 2024 | 28,501 | 0 | 28,501 | 28,501 | ✓ |
| **Total** | **831,369** | **52** | **831,317** | **831,317** | ✓ |

Bronze counts equal the structure doc's per-year tables exactly, and `wc -l` over the 14 CSVs gives 831,383 raw lines = 831,369 data rows + 14 headers — so the 2023–2024 drop to ~28.5k rows/year is **genuinely in the source** (Era 1 sparse emission), not read loss. The only filtered rows are the 52 explicit 2022 twin drops (`school_all_sentinel_twin_of_school_coded_row`); dedup removed 0 rows (no `duplicate_rows_deduped` reason in the manifest). Expansion factor 1.0 everywhere except 2022 (0.9992).

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `#RPT_NAME` (Era 1 only) | — | CORRECTLY EXCLUDED — constant `"Enrollment_by_Grade"`, no information |
| `LONG_SCHOOL_YEAR` | `year` | MAPPED — ending year parsed, cross-checked against filename (raises on mismatch) |
| `DETAIL_LVL_DESC` | — (drives `detail_level` → filename) | CORRECTLY EXCLUDED — encoded as `schools`/`districts`/`states.parquet` |
| `SCHOOL_DSTRCT_CD` | `district_code` | MAPPED — `ALL` → NULL, else zfill(3) |
| `SCHOOL_DSTRCT_NM` | — | CORRECTLY EXCLUDED — dimension attribute |
| `INSTN_NUMBER` | `school_code` | MAPPED — `ALL` → NULL, else zfill(4) |
| `INSTN_NAME` | — | CORRECTLY EXCLUDED — dimension attribute |
| `GRADES_SERVED_DESC` | — | CORRECTLY EXCLUDED — institution metadata; row's own `GRADE_LEVEL` pins the grade |
| `ENROLLMENT_PERIOD` | `enrollment_period` | MAPPED |
| `GRADE_LEVEL` | `grade_level` | MAPPED via shared normalizer |
| `ENROLLMENT_COUNT` | `student_count` | MAPPED — TFS → NULL, cast Int64; §16-canonical name (doc's `enrollment_count` suggestion superseded, noted in the doc itself) |

No gold column lacks a bronze source (no fabrication). The 2012 casing quirk is real — raw header quoted: `..."GRADE_LEVEL","Enrollment_Count"` — and absorbed by the post-read uppercase rename (manifest's 2012 `bronze_columns` show `ENROLLMENT_COUNT`).

## Value-Level Spot Checks

All bronze values quoted from the raw CSVs (read as strings, columns uppercased only).

1. **Global max (extreme)** — 2022 bronze: `State, SCHOOL_DSTRCT_CD='ALL', INSTN_NUMBER='ALL', Fall, 9th, ENROLLMENT_COUNT='159821'` → gold `(2022, NULL, NULL, fall, 09) = 159821`. **MATCH** (sentinels correctly resolved to NULL; this is the manifest's global max).
2. **Global min / true zero (extreme)** — 2011 bronze: `School, 743, 0207 (Twiggs Middle), Fall, 1st, ENROLLMENT_COUNT='0'` → gold `(2011, '743', '0207', fall, 01) = 0`. **MATCH**. Gold 2011 has exactly 37,413 zeros — equals the structure doc's zero count. True zeros preserved, never NULLed.
3. **TFS-era min (extreme)** — 2024 bronze: `School, 612, 0115, Fall, 8th, ENROLLMENT_COUNT='10'` → gold `= 10`. **MATCH**. Global min for 2021–2024 is 10 with **zero** rows at 0 < count < 10 (the suppression floor — see Fix 1).
4. **Ordinary, Era 2 + structure-doc correction** — 2011 bronze: `District, 601 (Appling County), INSTN_NUMBER='ALL', Fall, K, ENROLLMENT_COUNT='313'` → gold `(2011, '601', NULL, fall, k) = 313`. **MATCH** — confirms the doc's corrected sample value 313 (was 279 in an earlier doc revision).
5. **Ordinary, Era 1** — 2024 bronze: `School, 748 (Ware), 3052 (Waresboro Elementary), Fall, 2nd, ENROLLMENT_COUNT='80'` → gold `= 80`. **MATCH**.
6. **Suppression (4f)** — 2022 bronze: `School, 758 (Wilkinson), 0175, Spring, 8th, ENROLLMENT_COUNT='TFS'` → gold `student_count = None`. **MATCH**. 2024 bronze TFS count 1,178 = gold 2024 NULL count 1,178 exactly.
7. **Drop-boundary trace (the 52 twins)** — full replay against 2022 bronze: exactly 52 rows with `DETAIL_LVL_DESC='School'` AND `INSTN_NUMBER='ALL'`, exactly 26 each for districts `7830627` and `7830636`; joining each twin to its school-coded sibling on (district, period, grade) gives 52 join rows (no fan-out) and **52/52 exact count matches** including `TFS`=`TFS` pairs (e.g. `7830627` Fall K: twin `'TFS'` vs school-coded `0627` `'TFS'`; `7830636` Fall K: twin `'75'` vs school-coded `0636` `'75'`). Bronze 2022 has **0** District-level rows for these districts, and **no other year** contains any School+ALL row. Gold keeps exactly 52 school-coded rows for these districts in 2022 (0 with NULL school_code), e.g. `(2022, '7830636', '0636', fall, k) = 75`. **MATCH — drop fully justified and correctly executed.**
8. **Year attribution (4c)** — `LONG_SCHOOL_YEAR` distinct per file: 2011→`'2010-11'`, 2012→`'2011-12'`, 2022→`'2021-22'`, 2024→`'2023-24'`; gold `year` equals the embedded ending year in every trace above. The transform raises on filename/in-file mismatch. **PASS**.
9. **Aggregate feasibility (4d, aggregates COME FROM BRONZE)** —
   - District vs sum-of-schools, 2011–2020 (no suppression): 52,689 cells, 52,597 exact, **0 cells where district < school sum** (the impossible direction), max gap +138. The 71 cells off by >2% are 67× district `891` (Dept. of Juvenile Justice, grade 09 — district counts students not attributed to a facility) plus 4 tiny cells (≤10 students) in 612/701/601 — all in the feasible direction, all bronze-published.
   - TFS years: 0 districts below max visible school, 0 below visible school sum. **PASS**.
   - State vs sum-of-districts: pre-2021 diffs are small and **bidirectional** (62 negative, min −254; 46 positive, max +294; on ~1.6–1.7M totals = ≤0.02%) — so GOSA's state row is independently computed, not a sum of district rows. The 21 TFS-era cells where state < visible district sum (max −175, all grades 07–12) match this pre-existing pattern in magnitude and direction and are therefore a source characteristic, not garbling. See Judgment Call 1.
10. **Dedup tie-break (4e)** — N/A: each file covers exactly one school year (manifest `files_processed`), no overlap years; dedup removed 0 rows.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning**. `contract_parquet_schema` (42 files), `contract_quality_sql` (10 checks), `grain_uniqueness`, and `foreign_keys` (245 district keys, 2,604 school keys, all resolve) all pass.
- The single warning is the expected `null_rate_spikes`: `student_count` 2021 = 58.2%, 2022 = 58.1% vs 0.0% median — the documented TFS suppression-regime change (dense rows + blanket <10 suppression). Explained; not escalated.
- `schema_hash`: `530491b07bc53621ba83aed23c6031b4a7e6bc607c3d2b98ecaaeeacab0351cd`.
- **§4b masking audit**: transform has no `_null_*` helpers; manifest has no `masked_values` section; contract declares `unit: count` (≥ 0 derived check). Consistent — the metric is a non-negative integer count and bronze contains only digit strings or TFS, so there is nothing to mask. PASS.
- **§15b coverage judgment**: the six authored checks (26 state rows/year, 13 grades/period, dense-era full grade set, never-NULL before 2021, ID-length facts ×2) pin the right structural facts, use single-scan GROUP BY subqueries (no self-joins), and all pass. **One obvious invariant is missing**: the suppression-era floor — from 2021 on, every non-NULL `student_count` must be ≥ 10 (the structure doc states the Era-1 minimum is 10 and TFS replaces everything below 10; verified to hold: gold min for 2021–2024 is 10 with zero values in 1–9). This is the enforcement complement of `student_count_never_null_before_2021` and would catch a cast/scale regression in exactly the years that check cannot see. → Fix 1.
- **v1 parity** (verbatim output):

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **No overlap years** — 12 files routed to `era_2_2011_2022_dense`, 2 to `era_1_2023_2024_rpt_name_sparse` (manifest), matching the structure doc exactly; era detection is by column signature with the more-specific Era 1 signature checked first.
- **Era boundary continuity (3d)** — state-level totals per period are smooth across all 13 adjacent year pairs including the 2022→2023 era boundary (fall: 1,694,450 → 1,702,352; spring: 1,685,643 → 1,692,481); no >10x jumps, no 1.5–2x one-year level shifts. The 2021 COVID dip (1,719,069 → 1,686,890 fall) is real-world, not pipeline.
- **Cross-year NULL sweep (3c)** — no column ~100% NULL in any year subset; no column NULL in every year. The 2021/2022 ~58% `student_count` NULL rate is the TFS regime, below the sweep's 95% threshold and fully explained.
- **Dense-era rectangle** — verified for 2011: all 4,956 (entity, period) groups carry exactly 13 grade rows; 2,475 fall vs 2,481 spring entity-periods — exactly the structure doc's corrected per-(entity, period) scoping of the "perfect rectangle" claim.
- **2022 detail-level split** — gold: 26 state / 5,720 district / 59,514 school = bronze 59,566 school rows − 52 twins. Matches.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | Explicit `.select(STANDARD_COLUMNS)` plus a required-columns guard that raises on missing bronze columns |
| Era routing | PASS | Signature-based (`detect_era_by_columns`), most-specific first; manifest era assignments correct for all 14 files |
| Filter logic logged + justified | PASS | Only filter is the 2022 twin drop: hard-fail exact-duplicate guard, `manifest.record_filtered`, logged with district codes |
| Normalization map completeness | PASS | 2 period + 13 grade spellings cover everything observed; `replace_strict` + sentinel; unmapped = 0 |
| `strict=False` casts | PASS | Only on `ENROLLMENT_COUNT` after TFS→NULL; bronze verified all-digit; `student_count_never_null_before_2021` pins against regressions pre-2021 (2021+ unpinned → Fix 1) |
| Dedup keys + tie-break | PASS | Collision guard runs first; dedup purely defensive (0 rows removed); `sort_col="student_count"` documented |
| Year extraction | PASS | Anchored filename regex, cross-checked against `LONG_SCHOOL_YEAR` (raises on mismatch) |
| §4b masking | PASS | No masks needed or applied; manifest consistent |
| Risk 1 Asian/PI | N/A | No demographic axis in this source |
| Risk 2 rename typo | PASS | NULL sweep clean; 2012 casing quirk absorbed by uppercase rename (header quoted above) |
| Risk 3 sentinel year | PASS | Trace 8 |
| Risk 4 derived aggregates | PASS | Nothing derived; bronze-published aggregates pass the feasibility screen (Trace 9) |
| Risk 5 dedup inversion | N/A | No overlap years |
| Risk 6 mutual exclusivity | N/A | No demographic column |
| Risk 7 semantic mapping | PASS | All 15 entries reviewed individually |

## Required Fixes

### Fix 1: Author the suppression-era floor quality check (student_count ≥ 10 from 2021 on)
- **Severity**: MEDIUM
- **Issue**: The structure doc documents that from 2021 on, every published `ENROLLMENT_COUNT` below 10 is suppressed to TFS ("integer ≥10"; Era-1 minimum is 10). The invariant holds in gold (min over 2021–2024 is exactly 10; zero rows with 0 < count < 10) but no contract quality check enforces it, so a future cast/parse/scale regression in the suppression years is unguarded — `student_count_never_null_before_2021` only covers ≤ 2020, and `student_count_non_negative` would not catch a value of 1–9.
- **Evidence**: Executed: `global min student_count 2021-2024 in gold: 10` and `rows with 0 < count < 10 in 2021-2024: 0`. Manifest `metric_stats.student_count` min_val = 10.0 for 2021, 2022, 2023, 2024. Bronze structure doc: "`ENROLLMENT_COUNT` … integer ≥10 (the cell-size threshold)".
- **Location**: `_emit_contract_and_readme()` in `src/etl/education/gosa/enrollment_by_grade_level/transform.py` — `quality_checks=` list.
- **Suggested fix**: Add a check, e.g. `student_count_suppression_floor_from_2021`: `SELECT COUNT(*) FROM {object} WHERE year >= 2021 AND student_count IS NOT NULL AND student_count < 10`, `mustBe: 0`, dimension `accuracy`, with a description tying it to the TFS <10 threshold. Re-run the transform. Contract-only change — gold parquet bytes are untouched, so v1 parity remains MATCH (`schema_hash` is also unaffected: quality checks are not hashed).

## NEEDS_JUDGMENT

### Judgment Call 1: GOSA aggregates do not tie exactly to component sums — consider a limitations caveat
- **Severity if confirmed**: LOW
- **Suspicion**: State rows differ slightly from the sum of district rows (and DJJ district 891 exceeds its school sums by up to 138 students in grade 09), which an API consumer summing components might misread as pipeline data loss.
- **Evidence available**: Pre-2021 (no suppression): 108 of 260 state cells differ from the district sum, bidirectionally (−254 to +294 on ~1.6–1.7M totals, ≤0.02%) — proving the state figure is computed independently by GOSA (likely deduplicating students enrolled in multiple districts; the deficit concentrates in grades 07–12, consistent with dual enrollment). The 21 TFS-era cells where state < even the *visible* district sum (max −175) match this pattern in direction, magnitude, and grade range. District-vs-school sums show 0 impossibly-low cells anywhere. All values trace byte-exact to bronze, and v1 parity is MATCH, so this is unambiguously a source characteristic, not a transform defect.
- **Why uncertain**: Whether this warrants contract prose is a documentation-taste call: the discrepancy is tiny, entirely bronze-faithful, and standard for independently published aggregates — but the auto-derived `limitations` only mention suppression NULLs, so a consumer reconciling levels has no warning.
- **Location**: `_emit_contract_and_readme()` — `limitations` override or a `notes` entry.
- **If confirmed, suggested fix**: Add one sentence to the contract limitations/README notes: "State and district rows are independently published GOSA aggregates and may differ from the sum of their component rows by up to ~0.02% (e.g., students enrolled in more than one district); do not treat component sums as exact reconciliations." My recommendation: add the sentence (cheap, prevents a predictable consumer misreading); no data change of any kind.

## Notes

- `schema_hash`: `530491b07bc53621ba83aed23c6031b4a7e6bc607c3d2b98ecaaeeacab0351cd`; contract `version: 1.0.0`.
- Validation: 20 pass / 0 fail / 1 warning (expected TFS null-rate spike, 2021–2022).
- v1 parity: **MATCH — byte-identical with v1 gold** (computed via `compute_gold_sha256` vs `docs/rebuild/v1-baseline.yaml`). Fix 1 does not disturb parity (contract-only).
- Read loss: 0 events; independently confirmed via raw line counts (831,383 lines = 831,369 data rows + 14 headers). The 2023–2024 row-count halving is Era-1 source sparsity, verified in the raw CSVs.
- FK coverage: all 245 district codes and 2,604 (district, school) pairs resolve in the dimensions (validator), including the 7-char charter codes present in every year.
- No `masked_values`, no `reclassified` sections in the manifest — consistent with a no-mask, no-reclassification transform (the 52 twins are recorded as explicit filtered rows, not reclassifications).
