# Data Review: overdose_deaths

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

All categorical mappings, the full row-count reconciliation, and every value-level trace reconcile exactly between bronze and gold; the 15 contract quality checks (including exact county→state, race-partition, sex-partition sums, and opioid containment) pass, 20/20 in `_validation.json`. No Required Fixes. One LOW judgment call: the manifest `masked_values` count (8,001 per rate column) exceeds the surviving gold NULL count (7,985) by exactly 16, because the sentinel mask is counted pre-dedup and 8 suppressed statewide-`all` heroin cells are each triplicated across the county/race/sex layouts then collapsed by dedup — gold is correct, the count is a faithful record of the masking operation, so I recommend accept-as-is. v1 parity: **no v1 baseline (topic is post-v1)** — `docs/rebuild/v1-baseline.yaml` has no `criminal_justice` entry. Race correctly preserves the post-1997 OMB split pair (`asian`/`pacific_islander`), confirmed by exact partition (ratio 1.0000) and distinct bronze values (2023: Asian 21 vs NHPI 5).

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| demographic | 11 | 11 | 0 | PASS |
| drug_category | 6 (identity) | 6 | 0 | PASS |

**demographic — full map review (all 11 entries, 2b):**

| Bronze | Gold | Correct? |
|---|---|---|
| All Races | all | Yes — race-layout total row |
| All Sexes | all | Yes — sex-layout total row |
| American Indian or Alaska Native | native_american | Yes |
| Asian | asian | Yes — bronze publishes the SPLIT pair (separate NHPI bucket exists), so bare `asian` is correct, not the pre-1997 combined bucket |
| Black or African-American | black | Yes |
| Female | female | Yes |
| Male | male | Yes |
| Multiracial | multiracial | Yes |
| Native Hawaiian or Other Pacific Islander | pacific_islander | Yes |
| Unknown | race_unknown | Yes — appears only in race-layout files (mapped to the `race`-category key `race_unknown`; ethnicity files, whose `Unknown` means unknown *ethnicity*, are not ingested) |
| White | white | Yes |

Completeness (2a): the structure doc lists 9 race values and 4 sex values; the two `Selected … Total` labels are dropped by `drop_selected_total_rows` *before* mapping (correct — derived duplicates), leaving 8 + 3 = 11 = `bronze_values_seen` exactly. No documented value went unencountered. (Age/ethnicity documented values are absent because those layouts are deliberately deferred — see Column Coverage.)

**drug_category (2b):** identity map of the 6 filename slugs; all 6 seen, all 6 produced, already canonical snake_case. Semantically correct — slugs match the OASIS cause labels in the structure doc.

Contract cross-check (2c): contract `enum` for `demographic` (10 values) and `drug_category` (6 values) each equal `gold_values_produced` exactly. Unmapped (2d): 0 for both.

### Asian / Pacific Islander (Risk 1, Step 2e)

Bronze grep confirms the NHPI label exists as a distinct bucket alongside `Asian` (`Native Hawaiian or Other Pacific Islander`) — the split pair, no combined bucket. Math test (positive evidence for the split convention), executed:

```
deaths: year=2024 cat=all_drug_overdoses total=1990 race_sum=1990 ratio=1.0000
```

The 7 race buckets partition the `all` total exactly, and `asian` / `pacific_islander` carry distinct values (2023: Asian 21, NHPI 5 — traced below). **PASS — split convention, not conflated.** The contract check `race_deaths_partition_to_state_total` enforces this for every (year, drug_category) and passes.

### Mutual exclusivity (Risk 6, Step 2f)

`asian_pacific_islander` present in gold: **False**. Only the split pair is served, no rollup — **PASS, single convention** (no split+rollup double-count possible).

### Row-count reconciliation (3a/3b)

| Slice | Bronze | Gold | Filtered | Explanation |
|---|---|---|---|---|
| Each year 1999–2023 | 1,044 | 1,014 | 30 | 1,044 = 6×161 (county) + 6×9 (race) + 6×4 (sex); filtered = 18 explicit (6 County Summary + 6 Selected Races Total + 6 Selected Sexes Total) + 12 dedup (2 duplicate statewide `all` × 6 causes); gold 1,014 = 159 counties × 6 + 10 state rows × 6 |
| 2024 | 2,088 | 1,014 | 1,074 | Adds the 1,044 `selected_years_total` rows (161×6 + 9×6 + 4×6), lumped into 2024 by `_record_bronze_accounting` and immediately filtered |
| **Total** | **28,188** | **26,364** | **1,824** | 28,188 = 6×4,347 + 6×243 + 6×108 (18 ingested files, exactly the raw row counts) |

Arithmetic verified end-to-end (executed): explicit filtered 1,512 (`selected_years_total` 1,044; County Summary / Selected Races Total / Selected Sexes Total 156 each) **+** dedup 312 (2 triplicate statewide-`all` surplus × 26 years × 6 causes) **= 1,824** = manifest `total_filtered`. Gold decomposition: county 24,804 + state-all 156 + race 1,092 + sex 312 **= 26,364** = actual parquet row count = manifest `total_gold`. All 26 expected years present; expansion factor uniform (0.9713) across 1999–2023, no per-year anomaly.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| geography | — | CORRECTLY EXCLUDED (county name lives in the counties dimension; used only to route Georgia/County Summary rows) |
| county_fips | county_fips | MAPPED (bare `13xxx` → 5-digit string, format asserted; Georgia `13` → NULL state row) |
| race / sex | demographic | MAPPED (two axes folded into the single FK column) |
| age / ethnicity | — | CORRECTLY EXCLUDED (deferred to v2: age needs a demographics-dimension expansion; ethnicity overlaps the race axis and would break §5a — 12 files skipped by layout signature, documented in contract limitations) |
| year | year | MAPPED (Int32 after dropping `selected_years_total`) |
| deaths | deaths | MAPPED (null → 0 true zero, per OASIS + exact reconciliation) |
| death_rate | death_rate_per_100k | MAPPED (renamed; negative sentinels → NULL) |
| age_adjusted_death_rate | age_adjusted_death_rate_per_100k | MAPPED (renamed; negative sentinels → NULL) |
| *(filename slug)* | drug_category | MAPPED (identity) |

No gold column lacks a bronze source (no fabrication). Deliberate, defensible deviation from the structure doc's classification table: the doc suggested gold names `death_rate` / `age_adjusted_death_rate` with `unit: ratio`; the transform instead ships `*_per_100k` with **no** unit + authored non-negativity checks. This is the better call — `ratio` means "divided by 100 from a 0-100 source" and the validator fails a ratio column whose median exceeds 1.5, which would misfire on per-100k rates. Documented in the module docstring and contract descriptions.

**Contract prose fidelity (Step 6):** audited the served text (`purpose` / `usage` / `limitations` / `null_semantics` + each column `description`) against `bronze-data-structure.md` for contradictions — none found. Year range (1999–2024), suppression scheme (<5 deaths → NULL rate; deaths never suppressed; 0 is a true zero), no-percentage/per-100k scale, the split-race convention, the deferred age/ethnicity claim, and the overlap/non-additivity warning all agree with the bronze doc. Contract-quoted figures (2023 subtype sum 3,609 vs all_opioids 1,838; 2,521 all-races) independently reproduced from gold below.

## Value-Level Spot Checks

Extreme rows first (Step 4a), all bronze lines quoted from the CSVs:

| Trace | Bronze (file, quoted) | Gold | Verdict |
|---|---|---|---|
| Global max deaths (4a) | `Georgia,13,2022,2678,24.50139030293892,25.000693100000003` (all_drug_overdoses__county_year.csv) | 2022, county_fips NULL, demographic all: deaths 2678, rate 24.501390, aadr 25.000693 | MATCH |
| Global max crude rate + max aadr (4a) | `Crisp,13081,2023,15,76.42922653622746,86.2323748` (all_drug_overdoses__county_year.csv) | 13081/2023: deaths 15, rate 76.429227, aadr 86.232375 | MATCH |
| Global min (zero-death row, empty deaths + empty aadr) (4a) | `Talbot,13263,1999,<empty>,0,<empty>` (heroin__county_year.csv) | 13263/1999/heroin: deaths 0, rate 0.0, aadr 0.0 | MATCH (null→0 true zero; inconsistent empty aadr normalized to 0.0) |
| Suppression, county (4f) | `Effingham,13103,2006,4,-5,-5`; `Wilkinson,13319,2008,1,-5,-5`; `Stephens,13257,2019,2,-5,-5` (all_drug_overdoses__county_year.csv) | 13103/2006: 4/NULL/NULL; 13319/2008: 1/NULL/NULL; 13257/2019: 2/NULL/NULL | MATCH (−5 sentinel → NULL, exact deaths preserved) |
| Race layout, ordinary + suppressed (4b) | 2023 all_drug_overdoses race file: AIAN `4,-5,-5`; NHPI `5,43.211476968282774,39.1076142`; Asian `21,3.757434352254103,3.491917`; Unknown `<empty>,0,0` | native_american 4/NULL/NULL; pacific_islander 5/43.211477/39.107614; asian 21/3.757434/3.491917; race_unknown 0/0.0/0.0 | MATCH (all four) |
| Sex layout, ordinary (4b) | 2023 all_drug_overdoses sex file: `Male,1674,31.295352789670364,31.9635073`; `Female,847,14.821601810930257,15.048451499999999` | male 1674/31.295353/31.963507; female 847/14.821602/15.048451 | MATCH |
| Another era/layout ordinary (4b) | 2020 all_opioids: race `Black or African-American,289,8.365458817917249,8.281152700000002`; sex `Female,443,8.00851831564409,8.084393600000002` | black 289/8.365459/8.281153; female 443/8.008518/8.084394 | MATCH |
| Triplicate dedup (4e analogue) | Statewide 2022 all_drug_overdoses published identically in 3 files: county `Georgia,13,2022,2678,24.50139030293892,25.000693100000003`, race `All Races,2678,…`, sex `All Sexes,2678,…` — byte-identical metrics | one gold row: 2678/24.50139/25.000693 | MATCH (collision guard asserted equality before dedup; removed count asserted = triplicate surplus) |

- **4c sentinel year-attribution**: N/A — `year` always comes from the bronze `year` column; year-bearing literals in transform.py appear only in docstrings/contract prose, never as a parse source. The manifest's file-level `year: 2024` is bookkeeping (max data year), not attribution. `selected_years_total` rows are dropped, never attributed to a calendar year.
- **4d aggregate reconciliation**: aggregates COME FROM BRONZE (Georgia / All Races / All Sexes rows), not derived. The contract quality checks perform the feasibility screen exactly and exhaustively — `county_deaths_sum_to_state_total`, `race_deaths_partition_to_state_total`, `sex_deaths_partition_to_state_total` require EXACT equality for every (year, drug_category); all pass. No `.mean()` on percentages. Independently reproduced from gold: 2023 statewide `all_drug_overdoses` = 2,521; `all_opioids` = 1,838; subtypes (heroin 103 + methadone 58 + nss 1,809 + synthetic 1,639) sum to 3,609 — matches the served contract text verbatim.

## Validation Cross-Read

- `_validation.json`: **passed = true, 20 pass / 0 fail / 0 warning** — including `contract_parquet_schema` (52 files), `contract_quality_sql` (15 checks), `grain_uniqueness` (year, county_fips, demographic, drug_category), `foreign_keys` (county_fips → counties: all 159 resolve; demographic → demographics: all 10 resolve), and both geography-nulling checks. No warnings to explain.
- `schema_hash`: `3f7052554c1a444e5950eb97b79d73cf6d0128b2c5daee29e47647327233d0f1`
- **§4b masking audit (5b)**: one mask family — `null_sentinel_rates` (negative OASIS sentinels → NULL). Recorded in manifest `masked_values`: 8,001 cells per rate column, reason `oasis_rate_suppression_sentinel (negative sentinel values [-5.0]; …)`, all 26 years. Only `-5.0` observed (consistent — `-2` occurs only in ethnicity files, which are not ingested). Documented in both rate columns' contract `description` + `null_meaning`. Range guard: authored `*_non_negative` quality checks stand in for unit bounds (columns are unit-exempt per-100k rates), so the mask stays enforceable. **Discrepancy (see NEEDS_JUDGMENT #1):** gold carries 7,985 NULLs per rate column, 16 fewer than the recorded 8,001 — the mask is counted pre-dedup and 8 suppressed statewide-`all` heroin cells are triplicated then collapsed. The zero-death rate normalization (`normalize_zero_death_rates`, a fill not a mask) is correctly not in `masked_values`; it is logged, documented in both descriptions, and enforced by `zero_deaths_implies_zero_rates` (positive-rate-on-zero-death contradictions hard-fail; none exist).
- **§15b coverage judgment (5c)**: strong. 11 authored checks cover every real cross-column invariant: both partition sums (race, sex), county→state sum, opioid containment hierarchy, suppression semantics both directions (`rates_null_only_when_deaths_1_to_4`, `zero_deaths_implies_zero_rates`), and the structural grid facts (159-county grid, 10-row state demographic grid, breakdowns state-only), plus rate non-negativity. Nothing obvious is missing.
- **v1 parity (5d)**: executed check returns `DIFFERS` with `v1: None` — expected: `docs/rebuild/v1-baseline.yaml` has **no `criminal_justice` entry** (confirmed: zero keys with that prefix). **No v1 baseline — topic is post-v1; not a divergence, no finding.**

## Cross-Era Consistency

Single era: all 30 files exported in one scripted download (2026-07-02); the 5 layouts are column signatures, not eras — no overlap years, no era boundaries. Cross-year NULL sweep (executed): **no FLAG, no INVESTIGATE** — no column is ~100% NULL in any year (rate NULLs from suppression are spread across all 26 years, as expected). Year-over-year continuity (executed, statewide all_drug_overdoses + all categories): no >10x jumps; the series rises smoothly 274 (1999) → 2,678 (2022 peak) → 2,521 (2023) → 1,990 (2024), matching the known epidemic curve. The 2024 decline (×0.79) is consistent with the contract's documented late-certificate revision caveat, not a cumulative-publication level-shift artifact.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | 18 ingested files carry the full expected column set (manifest `bronze_columns`); age/ethnicity skips are explicit, logged, and layout-signature-routed |
| Era/layout routing | PASS | `detect_oasis_layout` by column signature, never filename; unknown signature raises; unknown cause slug raises |
| Filter logic logged + justified | PASS | All three derived-row drops assert equality against the surviving row before dropping and are recorded per-year on the manifest |
| Normalization map completeness | PASS | 11/11 demographic labels via shared `DEMOGRAPHIC_ALIASES`; unmatched labels hard-fail (`SENTINEL_UNMATCHED_DEMOGRAPHIC` guard) |
| `strict=False` casts | PASS | None — rates cast STRICTLY with a loud-failure guard for new suppression markers; deaths cast then `fill_null(0)` with documented true-zero semantics |
| Dedup keys + tie-break | PASS | Collision guard (`assert_no_natural_key_collisions`) runs first and hard-fails on any metric divergence, so the `sort_col="deaths"` tie-break is immaterial; removed count asserted == expected triplicate surplus |
| Year extraction | PASS | From the bronze `year` column only; `selected_years_total` dropped before Int32 cast |
| §4b masking (5b) | PASS (data) | Sentinel mask correct in gold, documented in contract, guarded by authored quality SQL; manifest count nuance in NEEDS_JUDGMENT #1 |

## NEEDS_JUDGMENT

### Judgment Call 1: manifest mask count (8,001) is measured pre-dedup, 16 above surviving gold NULLs (7,985)

- **Severity if confirmed**: LOW
- **Suspicion**: `masked_values` records 8,001 nulled cells per rate column, but gold contains only 7,985 NULLs per rate column — a 16-cell overstatement in the manifest's documentation of the suppression mask.
- **Evidence available**: Executed — `df['death_rate_per_100k'].null_count()` = 7,985 and `age_adjusted_death_rate_per_100k` = 7,985 in gold, vs `masked_values` count 8,001 (both). Root cause pinned exactly: `null_sentinel_rates` runs on the pre-dedup concatenated frame, then dedup removes the 2-of-3 duplicate statewide-`all` rows. There are exactly 8 statewide-`all` cells with deaths 1–4 (all `heroin`, years 1999/2000/2001/2002/2004/2005/2006/2010) whose rate is suppressed; each is triplicated across the county/race/sex layouts (masked 3×) but survives once → 8 × 2 = 16 duplicate masks removed. 8,001 − 16 = 7,985 (exact).
- **Why uncertain**: This is a documentation-accuracy question, not a data defect — the gold is correct (all 7,985 NULLs sit on deaths-1–4 rows, `rates_null_only_when_deaths_1_to_4` passes), and 8,001 is a truthful count of the masking *operation* as performed (before the later dedup). It is genuinely defensible either way; the approver should knowingly accept which count the manifest should report.
- **Location**: `main()` in `transform.py` — `null_sentinel_rates` / `manifest.record_masked` run before `deduplicate_by_levels`.
- **If confirmed, suggested fix**: Optional, non-blocking — either accept as-is (the pre-dedup count faithfully records the masking operation; my recommendation), or move `record_masked` after dedup (or re-measure NULL counts on the final frame) so the manifest count matches surviving gold NULLs exactly. No gold-data change; no re-approval needed under the metadata-only drift rule.

## Notes

- `schema_hash` `3f7052554c1a444e5950eb97b79d73cf6d0128b2c5daee29e47647327233d0f1`; validation 20 pass / 0 fail / 0 warning; `read_loss`: 0 events (acknowledged section absent = zero).
- Cosmetic only (not a data issue, no fix): the module docstring says "max state count (2,687 in 2022)" — the actual value is 2,678 (digit transposition). Gold, manifest, and contract all carry the correct 2,678; the typo exists only in transform.py prose, which is not a served surface.
- `race_unknown` has 0 deaths in every year (bronze `Unknown` rows are empty = true zero), matching the contract description's explicit claim.
- The 12 deferred age/ethnicity bronze files remain checksummed and analyzed in bronze; deferral rationale (dimension expansion / §5a race-axis overlap) is documented in the module docstring and contract limitations, and re-serving them later is additive (new demographic values, no schema change).
