# Data Review: ccrpi_climate_star_rating

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold data is value-accurate: every spot check (extremes, one entity per era, year
attribution, suppression, the 2015 duplicate) matched bronze exactly, row counts
reconcile to the row (15,893 bronze − 1 byte-identical duplicate = 15,892 gold), and
**v1 parity is MATCH** (independently re-verified, `f0647a7d…`). One documentation
fix is required: raw-cell inspection shows **every metric NULL in every year
originates from a literal `NA` text marker** — there are zero blank cells in either
metric column in any of the 7 files — contradicting the structure doc's "true nulls
(blank cells)" claims (Era 1, 2024), the transform docstring, and the contract's
`null_meaning`/notes, which attribute `NA` markers to the 2019 CCRPI column only.
The gold values and null counts are unaffected (the shared reader nulls `NA` at
read in all columns), so the fix is prose-only and cannot change parquet bytes or
parity.

## Manifest Verification

### Categorical mappings

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| — | 0 | — | — | N/A — `categorical_mappings` is `{}`; the topic has no demographic column and no topic-specific categoricals (nothing is recoded), matching the structure doc's Gold Schema Classification |

Steps 2a–2d are trivially satisfied. Step 2e (Asian/PI conflation): **N/A** — no
`demographic` column, no `pct_asian` column in gold. Step 2f (mutual exclusivity):
**N/A** — no demographic axis exists.

### Row-count reconciliation (manifest vs parquet)

| Year | Bronze | Filtered | Gold (manifest) | Gold (parquet, re-counted) | Expansion | Verdict |
|------|--------|----------|-----------------|---------------------------|-----------|---------|
| 2014 | 2,261 | 0 | 2,261 | 2,261 | 1.0 | PASS |
| 2015 | 2,271 | 1 | 2,270 | 2,270 | 0.9996 | PASS — the byte-identical Murray Co. duplicate, ledgered via `record_filtered` |
| 2016 | 2,269 | 0 | 2,269 | 2,269 | 1.0 | PASS |
| 2017 | 2,235 | 0 | 2,235 | 2,235 | 1.0 | PASS |
| 2018 | 2,278 | 0 | 2,278 | 2,278 | 1.0 | PASS |
| 2019 | 2,279 | 0 | 2,279 | 2,279 | 1.0 | PASS |
| 2024 | 2,300 | 0 | 2,300 | 2,300 | 1.0 | PASS |
| **Total** | **15,893** | **1** | **15,892** | **15,892** | | **PASS** |

All 7 expected years present (2014–2019 + 2024; 2020–2023 absent per the COVID
CCRPI pause — documented, not synthesized). `filtered_explicit_by_reason` carries
exactly one entry: `"byte-identical duplicate row in bronze (dedup keep-first)": 1`.
Era assignments in `files_processed` match the structure doc (2014–2018 → era_1,
2019 → era_2, 2024 → era_3); the 2014 data correctly attributes to the
`...04.14.15.xlsx` publication-dated file.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|------------|--------|
| Year / School Year | `year` (Int32) | MAPPED (normalized per era, in-file value authoritative) |
| System ID | `district_code` (Utf8, zfill 3) | MAPPED |
| System Name | — | CORRECTLY EXCLUDED — dimension attribute (districts dimension; FK check passes for all 242 keys) |
| School ID | `school_code` (Utf8, zfill 4) | MAPPED |
| School Name | — | CORRECTLY EXCLUDED — dimension attribute (schools dimension; FK check passes for all 2,480 keys) |
| CCRPI Single Score | `ccrpi_single_score` (Float64) | MAPPED (NULL-filled for 2024 where the bronze column is absent) |
| School Climate Star Rating | `school_climate_star_rating` (Float64) | MAPPED |

No fabricated gold columns — gold carries exactly the 5 columns above. One
intentional deviation from the structure doc: the doc recommends `pl.Int8` for the
star rating; the transform uses Float64 with an explicit rationale (one star-rating
type across the API; FESR ratings take half-steps) plus a whole-star quality check
so nothing fractional can slip in. Justified — not a fix.

## Value-Level Spot Checks

All traces read bronze directly (shared reader, plus raw pandas/openpyxl where the
literal cell content mattered). Every trace **MATCH**.

**Extreme rows (4a) — global max/min of each metric:**

1. **Global max `ccrpi_single_score` = 110.3 (2016 file)**: bronze `667 / 1019`
   "Gwinnett School of Mathematics…", `CCRPI Single Score = "110.3"`, star `"5"` →
   gold `{2016, '667', '1019', 110.3, 5.0}`. MATCH — bonus-point-era >100 value
   preserved per §4b extreme-but-conceivable, documented in the contract.
2. **Global min `ccrpi_single_score` = 16.4 (2017 file)**: bronze `7991895 / 1895`
   "Georgia School for the Deaf", score `"16.4"`, star `"3"` → gold
   `{2017, '7991895', '1895', 16.4, 3.0}`. MATCH — 7-digit state-school code
   preserved untruncated.
3. **Star rating min = 1**: 2018 bronze `729 / 0190` "Sumter County Middle School"
   star `"1"` → gold `1.0`; 2024 bronze `7820618 / 618` "Coastal Plains High
   School" star `"1"` → gold `{'7820618', '0618', 1.0}`. MATCH.
4. **Star rating max = 5**: 2018 bronze `722 / 0378` "Edwards Middle School" star
   `"5"` → gold `5.0`; 2019 bronze `785 / 0275` "East Central Elementary School"
   star `"5"` → gold `5.0`. MATCH.
5. **Per-year extremes**: 2014 max `773/0505` Clairemont Elementary `"101.2"` →
   gold `101.2`; 2014 min `761/0207` Hillside Conant `"21.3"` → gold `21.3`
   (star NULL); 2019 max `633/0491` Timber Ridge Elementary `"99.3"` → gold
   `99.3`; 2019 min `721/0391` Alternative Education Center at Lamar `"18.6"` →
   gold `18.6`. All MATCH and equal the manifest `metric_stats` per-year min/max.

**Ordinary traces (4b) — one entity per era, all columns:**

- **Era 1 (2018)**: bronze `644 / 2061` "McLendon Elementary School", score
  `"80.9"`, star `"3"` → gold `{2018, '644', '2061', 80.9, 3.0}`. MATCH. Also
  `891 / 0104` "Atlanta Youth Detention Center" (DJJ), score `"28.4"`, star NULL →
  gold `{28.4, None}`. MATCH (state-agency district code preserved).
- **Era 2 (2019)**: bronze `706 / 1066` "Reese Road Leadership Academy", score
  `"67.3"`, star `"4"` → gold `{2019, '706', '1066', 67.3, 4.0}`. MATCH.
- **Era 3 (2024)**: bronze `734 / 201` "Telfair County High School", star `"4"` →
  gold `{2024, '734', '0201', None, 4.0}` — bare-integer school code zfilled to
  `'0201'`, `ccrpi_single_score` NULL-filled (column absent from the release).
  MATCH. Shortest 2024 School ID `'103'` (Appling County High School, sys 601) →
  gold `'0103'`, star 3.0. MATCH. `726 / 103` "Moreland Road Elementary" star
  NULL → gold NULL. MATCH.

**Year attribution (4c)**: the 2014 file
`CCRPI Score and School Climate Star Rating 04.14.15.xlsx` carries exactly one
distinct in-file `Year` value, `['2014']`, across its 2,261 rows; first bronze row
(`601 / 0103` "Appling County High School", score `"69.1"`, star `"4"`) lands in
gold at `year=2014` with `{69.1, 4.0}`; the same school's gold 2015 row is the
*different* `{73.6, 4.0}` sourced from the 2015 file. Filename year (None — no
parseable 20XX) correctly defers to the in-file year; gold 2014 row count (2,261)
equals this file's row count exactly. MATCH.

**Aggregate reconciliation (4d)**: N/A — bronze publishes no district/state rows
and the transform derives none (school-only; enforced by the `all_rows_school_level`
quality check and the raise-on-sentinel guard).

**Dedup tie-break (4e)**: N/A for cross-era overlap — each year comes from exactly
one file (`files_processed`). The single within-file duplicate was traced: 2015
bronze has two rows for `705 / 1052` "Spring Place Elementary School", verified
byte-identical (`unique().height == 1`; both `{score "68.6", star "5"}`); gold has
exactly one row `{2015, '705', '1052', 68.6, 5.0}`. Gold-wide duplicate natural
keys: 0. MATCH.

**Suppression semantics (4f)**: raw 2019 read (no NA filtering) finds exactly 35
literal `'NA'` strings in `CCRPI Single Score`; first marker row `611 / 0307`
"Price Academy" (Bibb County, score `'NA'`, star `'NA'`) → gold
`{None, None}`. All 35 NA-keyed gold rows have NULL `ccrpi_single_score`
(0 non-null). MATCH. See Required Fix 1 for the full-file marker census this
trace uncovered.

## Validation Cross-Read

- `_validation.json`: **18 pass / 0 fail / 1 warning**, `passed: true`
  (2026-06-12T15:45:54Z, fresher than the manifest; transform mtime older —
  FRESH). `contract_parquet_schema`, `contract_quality_sql` (all 5),
  `grain_uniqueness` (`['year','district_code','school_code']`), and
  `foreign_keys` (242 district + 2,480 school keys all resolve) all pass.
- The single warning is `null_rate_spikes`:
  `ccrpi_single_score year=2024: null_rate=100.0% (median=4.0%, delta=96.0%)` —
  explained: GaDOE dropped the column from the 2024 release (verified: the 2024
  bronze file has no `CCRPI Single Score` column); pinned by the
  `ccrpi_single_score_absent_in_2024` quality check and documented in the
  contract notes. Not a transform bug.
- `schema_hash`: `bc142f2c78285b736f27e0abc563fed627ae258a4970a46c15dab76da11ad6bd`
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no
  `masked_values` section (correct — nothing is range-masked). The >100 CCRPI
  scores (max 110.3) are preserved-and-documented extreme-but-conceivable values;
  the column intentionally declares no bounds, with the rationale in its contract
  description. Suppression nulling happens at read via the shared reader's
  `SUPPRESSION_VALUES` — outcome correct, but its documentation is inaccurate
  (Required Fix 1).
- **§15b coverage judgment**: PASS — the authored checks pin the topic's real
  invariants: whole-star-only (the derived [1,5] range alone would admit 2.5),
  2024 all-NULL composite (structural fact), and both geography keys non-NULL on
  every row (school-only shape). No obvious cross-column invariant is missing
  (two independent metrics, no partition/co-null relationships to enforce).
- **v1 parity** (re-run independently):

  ```
  current: f0647a7d59c28b46ede82517041aa53b928f8a3a77fdc8d9fb3465454245cdf7
  v1     : f0647a7d59c28b46ede82517041aa53b928f8a3a77fdc8d9fb3465454245cdf7
  MATCH — byte-identical with v1 gold
  ```

## Cross-Era Consistency

- **Overlap years**: none — one file per year; era boundaries are 2018→2019
  (`Year` → `School Year`) and 2019→2024 (composite score dropped).
- **Cross-year NULL sweep**: exactly one flag —
  `FLAG ccrpi_single_score: ~100% NULL only in [2024]` — the documented,
  check-pinned release change. No other column has a ≥95%-NULL year (rules out
  the era-localized rename-typo signature; the era_2/era_3 signature-subset
  ordering hazard is correctly handled by putting era_2 first).
- **Level continuity (3d)**: per-year means from the manifest —
  `ccrpi_single_score`: 74.01 / 72.08 / 72.48 / 74.28 / 71.94 / 74.15
  (2014–2019); `school_climate_star_rating`: 3.50 / 3.50 / 3.52 / 3.66 / 3.87 /
  3.93 / 3.66 (2014–2024). No >10x jumps, no transient 1.5–2x level shifts.
  PASS.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Rename-coverage guard raises on any missing expected bronze column before `.select(STANDARD_COLUMNS)` |
| Era routing | PASS | Ordered first-match signatures with era_2 before its subset era_3; unmatched schema raises (no silent year drops) |
| Filter logic logged + justified | PASS | Only 1 row filtered (byte-identical 2015 duplicate), ledgered via `record_filtered` with reason |
| Normalization map completeness | PASS | No categorical recoding exists or is needed; renames cover every fact column in every era |
| `strict=False` casts | PASS | Metric casts: `NA` residue → NULL (belt-and-suspenders; the reader already nulls at read). Year cast is protected by the exactly-one-distinct-in-file-year guard + validator `year_non_null` (passes) |
| Dedup keys + tie-break | PASS | Collision guard (raises on metric-divergent duplicates) runs before dedup; explicit `sort_col="ccrpi_single_score"` keeps the data-bearing row; moot today (lone pair byte-identical) |
| Year extraction | PASS | In-file year authoritative; parseable-filename disagreement raises; 04.14.15 file traced to year=2014 |
| Suppression documentation | MEDIUM | `NA` markers exist in both metric columns in ALL years, not only 2019 CCRPI — docs/contract prose mischaracterize the mechanism (Required Fix 1) |

Risk hypotheses 1, 4, 5, 6 (Asian/PI, derived aggregates, dedup inversion,
mutual exclusivity): N/A for this topic with the evidence above; 2 (rename typo)
and 3 (year attribution): ruled out by the NULL sweep and the 2014 trace; 7
(wrong mapping): no recodings exist, and all column renames verified semantically.

## Required Fixes

### Fix 1: Document the true suppression mechanism — literal `NA` markers in both metric columns in every year, not only 2019 CCRPI

- **Severity**: MEDIUM
- **Issue**: Documentation inaccuracy (gold values are unaffected). The structure
  doc claims Era 1 and 2024 metrics "use true nulls (blank cells) rather than
  text suppression markers", the transform docstring claims "All other metric
  NULLs are true blanks", and the contract's `ccrpi_single_score.null_meaning` +
  notes single out "35 bronze `NA` markers in 2019" — implying 2019 NULLs are
  suppression while other years' NULLs are blank no-score cells. Raw-cell
  inspection (pandas `keep_default_na=False`, confirmed at cell level with
  openpyxl) shows **every** metric NULL in **every** year is a literal `NA`
  string and there are **zero** blank metric cells anywhere. The 2019-only
  "suppressed cells" framing is therefore an artifact of 2019's column being the
  only one the structure-doc profiling saw as String-typed; there is no evidence
  the 2019 `NA`s differ in meaning from any other year's (e.g., the 2018 DJJ
  Atlanta Youth Detention Center star `NA` is a not-rated facility, not a
  privacy suppression).
- **Evidence**: Raw text-marker census (blanks / `NA` literals per file, both
  metric columns): 2014 CCRPI `NA`×25, star `NA`×17; 2015 `NA`×123 / `NA`×28;
  2016 `NA`×127 / `NA`×35; 2017 `NA`×89 / `NA`×11; 2018 `NA`×33 / `NA`×42; 2019
  `NA`×35 / `NA`×42; 2024 (no CCRPI column) star `NA`×60 — **blanks=0 in every
  file/column**, and every count equals the corresponding gold null count in the
  manifest's `metric_stats` exactly. openpyxl cell-level confirmation (2018):
  CCRPI cells `{float: 2007, int: 238, 'NA': 33}`, star cells
  `{int: 2236, 'NA': 42}`. The 2019 NA-key sets are not nested
  (35 CCRPI-NA vs 42 star-NA, intersection 28), consistent with independent
  per-metric "not available" marking.
- **Location**: `_emit_contract_and_readme()` in transform.py (the
  `ccrpi_single_score` `null_meaning`, the `school_climate_star_rating`
  `null_meaning`, and the "Bronze `NA` suppression markers (35 cells…)" note);
  the module docstring "Suppression" bullet; plus a new entry in
  `bronze-data-structure.md` § Corrections (its per-era "Suppression Markers"
  sections say "None … true nulls (blank cells)" for Era 1 and 2024).
- **Suggested fix**: Prose-only. State that all metric NULLs in all years
  originate from literal `NA` text markers nulled at read via the shared
  reader's `SUPPRESSION_VALUES` (counts per year as in the evidence), and
  describe them neutrally as "no score/rating published (`NA` in bronze)"
  rather than splitting 2019 off as "suppressed cells". No parquet value
  changes — gold bytes and v1 parity (`f0647a7d…`) must remain identical after
  the re-run.

## Notes

- `schema_hash`: `bc142f2c78285b736f27e0abc563fed627ae258a4970a46c15dab76da11ad6bd`
- Validation: 18 pass / 0 fail / 1 warning (the documented 2024
  `ccrpi_single_score` 100%-NULL spike).
- v1 parity: MATCH (`f0647a7d59c28b46ede82517041aa53b928f8a3a77fdc8d9fb3465454245cdf7`),
  independently re-computed by this review.
- Manifest sections `read_loss` / `masked_values` / `reclassified` are absent —
  zero events by construction (whole-sheet Excel reads; no §4b masks; no
  recodings). `record_read_loss` is invoked per file as a structural no-op for
  auditability.
- Freshness verified: transform mtime 15:45:29Z < manifest 15:45:54.085Z ≤
  validation 15:45:54.120Z.
- The Float64-vs-Int8 star-rating type is a documented, justified deviation from
  the structure doc's recommendation (cross-topic API star-rating type), guarded
  by the whole-star quality check.
- S3 not touched (broken `georgia-data-admin` profile noted in the run context);
  parity used the local baseline per `docs/rebuild/v1-baseline.yaml`.
