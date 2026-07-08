# Data Review: detention_population

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Value-level accuracy is excellent and every spot check reproduced gold from bronze **exactly**:
Stewart FY2026 (all 14 ADP metrics, with all three partitions summing to 2025.803), the FY2019
Folkston ADP-omission edge case, Stewart FY2024 month=07 monthly means, the Dec-2023→FY2024
fiscal-year attribution, the Irwin FY2021 mid-year-drop recovery, and both global extremes.
The three Required Fixes from the prior (2026-07-02) review are all **landed and re-verified**:
the `monthly_rows_start_fy2023` quality check now exists, the facility-count prose reads
"6-9 in Georgia" (matches the true per-FY code counts 6-9), and the two-source reconciliation
prose reads "within about 2 percent" in both places. **No Required Fixes remain.** v1 parity is
**no baseline (post-v1)**: `docs/rebuild/v1-baseline.yaml` has zero `criminal_justice` entries, so
the parity script prints `DIFFERS` with `v1: None` — not a real divergence. Two LOW judgment calls
remain (one carried forward, one new), neither blocking.

## Manifest Verification

### Categorical mappings

| Column | Map entries | Bronze values seen | Unmapped | Status |
|--------|------------|--------------------|----------|--------|
| `facility_code` | 18 (name → DETLOC) | 18 — all map keys encountered | 0 | PASS |
| `county_fips` | 23 (DETLOC → FIPS) | 20 (3 hospital codes never appear in either feed) | 0 | PASS |
| `month` | 13 (identity) | 13 | 0 | PASS |

### Full map review — `facility_code` (name → DETLOC), every entry

| Bronze name (normalized) | Gold code | Correct? |
|---|---|---|
| ANNEX - FOLKSTON IPC / FOLKSTON ANNEX IPC | FIPCAGA | ✓ rename pair, same annex |
| MAIN - FOLKSTON IPC (D RAY JAMES) / FOLKSTON MAIN IPC | FIPCMGA | ✓ rename pair, same main center (the "(D RAY JAMES)" tag is the former campus name, not the prison) |
| FOLKSTON D RAY ICE PROCES / FOLKSTON D RAY ICE PROCESSING CTR | FIPCDGA | ✓ truncation variant; correctly NOT conflated with the prison |
| D. RAY JAMES PRISON | GADRYJM | ✓ the BOP-contract prison (closed 2021), its own code so its FY series stays separate from FIPCDGA |
| STEWART DETENTION CENTER | STWRTGA | ✓ |
| IRWIN COUNTY DETENTION CENTER | IRWINGA | ✓ |
| ROBERT A DEYTON DETENTION / …FAC / …FACILITY / ROBERT A. DEYTON… (4 variants) | RADDFGA | ✓ punctuation/truncation variants of one facility |
| COBB COUNTY JAIL | COBBJGA | ✓ |
| FLOYD COUNTY JAIL | FLOYDGA | ✓ |
| WHITFIELD COUNTY JAIL | WHITFGA | ✓ |
| ATLANTA US PEN / FCI ATLANTA | BOPATL | ✓ same BOP Atlanta facility, renamed across years |

### Full map review — `county_fips` (DETLOC → FIPS), every entry

Verified two ways: against the counties dimension name and against the crosswalk's own facility city (executed join):

| Code | FIPS | County | Facility city | Correct? |
|---|---|---|---|---|
| ATLANGA, ATLHOLD, BOPATL, GMHATGA | 13121 | Fulton | Atlanta | ✓ |
| BARTOGA | 13015 | Bartow | Cartersville | ✓ |
| BOPRAE | 13271 | Telfair | Mcrae-Helena | ✓ (McRae Correctional Facility) |
| BRYANGA | 13029 | Bryan | Pembroke | ✓ |
| CHTHMGA, SAVHOLD | 13051 | Chatham | Savannah | ✓ |
| COBBJGA | 13067 | Cobb | Marietta | ✓ |
| DEKABGA | 13089 | DeKalb | Decatur | ✓ |
| FIPCAGA, FIPCDGA, FIPCMGA, GADRYJM | 13049 | Charlton | Folkston | ✓ |
| FLOYDGA | 13115 | Floyd | Rome | ✓ |
| HALLJGA | 13139 | Hall | Gainesville | ✓ |
| IRWINGA | 13155 | Irwin | Ocilla | ✓ |
| PCRMMGA | 13215 | Muscogee | Columbus | ✓ (hospital, not in panel) |
| PHPMHGA | 13095 | Dougherty | Albany | ✓ (hospital, not in panel) |
| RADDFGA | 13063 | Clayton | Lovejoy | ✓ |
| STWRTGA | 13259 | Stewart | Lumpkin | ✓ |
| WHITFGA | 13313 | Whitfield | Dalton | ✓ |

The 3 crosswalk codes never seen in bronze (GMHATGA, PCRMMGA, PHPMHGA) are hospital facilities that appear in neither the collation nor the daily panel — not a routing bug. Their counties 13215/13095 correctly never reach gold; gold's 14-county set was verified exact and every FK resolves.

### Row-count reconciliation

Executed: actual gold parquet rows = **671 = manifest `total_gold`**. Per-year gold matches the manifest by_year (2019:7, 2020:7, 2021:8, 2022:8, 2023:187, 2024:186, 2025:186, 2026:82). The large per-year bronze counts (7,4xx in 2023-25) are dominated by the daily-panel facility-days that collapse to monthly means (expansion factor ~0.025) — expected for a daily→monthly aggregation, not silent loss. Explicit filtered = 856 = 656 superseded intra-FY snapshots + 200 partial-March-2026 rows. Excluded files (2 PII parquets, 3 codebooks, 1 byte-identical FY2025 workbook) all recorded with reasons.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| detention_facility_code / name (via crosswalk + name map) | county_fips (aggregated) | MAPPED — county grain per domain convention (facility identifiers stay out of gold); facility-grain candidate consciously not taken, documented |
| fiscal_year (collation) | year | MAPPED |
| date (panel) | year + month | MAPPED (federal-FY +1 logic verified) |
| level_a…level_d | adp_security_level_a…d | MAPPED |
| male_crim / male_non_crim / female_crim / female_non_crim | adp_male_criminal / adp_male_noncriminal / adp_female_criminal / adp_female_noncriminal | MAPPED |
| ice_threat_level_1/2/3, no_ice_threat_level | adp_threat_level_1/2/3, adp_no_threat_level | MAPPED |
| mandatory | adp_mandatory_detention | MAPPED |
| guaranteed_minimum | guaranteed_minimum_beds | MAPPED (placeholders → NULL) |
| n_detained, n_detained_male/_female, n_detained_convicted_criminal, n_detained_possibly_under_18 | avg_daily_population, avg_daily_male/_female, avg_daily_convicted_criminal, avg_daily_possibly_under_18 | MAPPED (monthly means of county-day sums) |
| n_detained_at_midnight | — | CORRECTLY EXCLUDED (redundant near-duplicate of n_detained, ~2% lower; documented) |
| FY{yy} ALOS / Facility ALOS sheet | — | CORRECTLY EXCLUDED (ALOS cannot aggregate to county without stay-level weights; documented) |
| Address/City/State/Zip/AOR/Type Detailed/Male-Female | — | CORRECTLY EXCLUDED (dimension attributes; crosswalk holds location) |
| Inspection-tail columns (all 5 eras) | — | CORRECTLY EXCLUDED (era-inconsistent compliance data, future topic) |
| file_date / pull_date | — | CORRECTLY EXCLUDED (snapshot-selection keys only) |
| stints/stays parquets | — | CORRECTLY EXCLUDED (PII gate; recorded in manifest) |
| Other workbook sheets (ATD, Detention, ICLOS, Bond, Segregation, …) | — | CORRECTLY EXCLUDED (national/AOR aggregates, out of scope) |

No gold column lacks a bronze ancestor. `avg_daily_population` on FY rows is the sum of the four gender×criminality components — an ICE-published partition identity verified below.

**Contract prose fidelity** (audited against `bronze-data-structure.md` for contradictions): year range FY2019-FY2026 ✓; "No values are suppressed" ✓ (bronze: no suppression in either source); "6-9 in Georgia" ✓ (executed per-FY code counts = 7,7,9,8,7,6,7,8); "14 counties" ✓ (executed min=max=14); FY2019 omits ADP for the two Folkston IPCs ✓ (traced); monthly rows FY2023 onward, panel starts 2022-10-01 ✓; three Folkston processing centers + old prison ✓. **No contradictions found.**

## Value-Level Spot Checks

**Extreme rows first (4a):**

1. **Global max monthly `avg_daily_population` = 4660.806451612903** (year=2026, month='01', state row). Rebuilt from bronze: mean over Jan-2026's 31 panel days of the GA-facility `n_detained` sum → **MATCH** (exact). Plausible (recent detention surge).
2. **Global min `avg_daily_population` (non-null) = 0.0** (year=2023, month='01', county 13015 Bartow). Bartow County Jail is a dormant IGSA — all panel days = 0 → **MATCH** (real zero, per contract `zero_is_real`).

**Ordinary traces (4b):**

3. **Stewart FY2026, all 14 FY metrics** (county 13259, sole facility). Latest FY2026 STWRTGA collation snapshot (file_date 2026-04-09): level_a 1022.382514, b 427.071038, c 286.169399, d 290.180328; male_crim 539.420765, male_non_crim 1161.273224, female_crim 57.36612, female_non_crim 267.743169; threat 1/2/3/none 316.20765/192.852459/235.590164/1281.153005; mandatory 1345.721311; GM 1600 — **every value matches gold exactly**. All three partitions (gender×crim, security A-D, threat 1-3+none) sum to **2025.803278** = `avg_daily_population` → **MATCH**.
4. **FY2019 Folkston ADP-omission** (Charlton 13049). Bronze FY2019 snapshot (file_date 2019-10-07): both IPCs (ANNEX 'null', MAIN 'null') have NULL ADP components with GM 338/544. Gold 13049: `avg_daily_population = NULL` (both null → `_null_aware_sum` yields NULL, not 0) and `guaranteed_minimum_beds = 882` = 338+544 → **MATCH**. Stewart FY2019 = 1910.542466 (882.98+1027.43+0.13+0), state row = 2838.684932 = Σ non-null counties → **MATCH**.
5. **Stewart FY2024, month='07' monthly, all 5 metrics**. Panel July-2024 (31 days) means: n_detained 1531.4516129, male 1371.4838710, female 159.5483871, convicted 650.9677419, under_18 0.0 — gold row identical → **MATCH**.
6. **Irwin FY2021 recovery** (the transform's distinctive selection rule). Irwin has 25 FY2021 snapshots; the latest (file_date 2021-10-01) is its final published fiscal-YTD value. Gold 13155 FY2021 = 287.3192488262914 = sum of that snapshot's four components → **MATCH** (facility present in FY2021 despite mid-year drop; Cobb/Floyd/Whitfield likewise present in their drop years).

**4c — fiscal-year attribution (Risk 3)**: PASS. Panel Dec-2023 rows carry FY label 2024, month='12' (Oct-Dec → next FY); the earliest panel date 2022-10-01 lands at (year=2023, month='10'); zero monthly rows exist below year=2023 (matches the `monthly_rows_start_fy2023` quality check). The only filename-year parsing feeds verification-only.

**4d — aggregate reconciliation (Risk 4)**: PASS. State = Σ counties enforced by the passing `state_adp_equals_sum_of_counties` check for `avg_daily_population`, and **independently verified for other metrics**: avg_daily_male (2025 m=07) state=3370.129 = county_sum; avg_daily_convicted_criminal (2024 m=05) state=957.097 = county_sum; adp_security_level_c (2022 m='all') state=311.265 = county_sum (all diff <1e-6). County = Σ facilities verified in traces 3-4. Monthly means are means of daily *counts* (correct); no `.mean()` over percentages exists (there are no percentage columns).

**4e — dedup tie-break (Risk 5)**: N/A by construction — the four sub-frames are disjoint on (month, detail_level) lanes, `assert_no_natural_key_collisions` runs before dedup, and grain uniqueness passed. The `sort_col='avg_daily_population'` tie-break is an unexercised safety net.

**4f — suppression/placeholder semantics**: PASS. 16 GA collation rows carry non-numeric `guaranteed_minimum` placeholders (`'*'`, `'\xa0'` NBSP); these cast to NULL via `strict=False` (logged), correctly meaning "no contractual floor", never 0. See Judgment Call 1. No suppression markers in either source (`suppressed_to_null: false`).

## Validation Cross-Read

- `_validation.json`: **passed=true, 19 pass / 0 fail / 1 warning**. `contract_parquet_schema` (16 files), `contract_quality_sql` (**all 31**), `grain_uniqueness` (year, county_fips, month), and `foreign_keys` (county_fips → counties, all 14 keys) all pass.
- The one **warning** (`tidy_format`: `avg_daily_male`/`avg_daily_female` "wide format?") is a benign false positive: long demographic format is wrong here — the FY lanes carry three *overlapping* ADP breakdown families that would double-count as rows, and the monthly gender counts don't partition the total (gender occasionally unrecorded; capped by `monthly_gender_split_within_total`). Structure-doc §12 anticipated either choice.
- **§4b masking audit**: no impossible-value masks; the manifest has no `masked_values` section (zero events), consistent with the docstring's "No S4b masks apply". The only `_null_*` helpers are `_null_aware_sum` (aggregation, yields NULL not fake 0 when all inputs NULL) and the shared `null_aggregate_geography` (state rows). The GM placeholder→NULL is a type-cast of a "no floor" placeholder, logged, documented in the column `null_meaning`, and range-guarded by `guaranteed_minimum_beds_non_negative` — see Judgment Call 1.
- **§15b coverage judgment**: strong quality set (3 partition-sum checks, 2 lane-exclusivity checks, monthly subset caps, mandatory-within-total, state=Σcounties, non-negativity ×15, month-enum, monthly_rows_start_fy2023). Covers every real cross-column invariant; `guaranteed_minimum_beds` has no cross-column relationship to author.
- **v1 parity** (verbatim):
  ```
  DIFFERS from v1
    v1:  None
    now: fd86c122e9d54e4f838924eadeafd6020d839e99ab0e4cf12c2532bc18b3206d
  ```
  Explanation: `docs/rebuild/v1-baseline.yaml` has **no criminal_justice entries at all** — this is a post-v1 topic with no baseline. Not a data change; parity is N/A.
- Contract `schema_hash`: `1fa3b1218a4c4b01a7f5d927f390ba85882880e935fd2eb29b4edd50ada546e4`.

## Cross-Era Consistency

- **No overlap years between feeds within a lane**: FY lanes (month='all') come only from the collation; monthly lanes only from the panel. The five Feed-1 workbook eras are verification-only (era detected per file, all matched; byte-identical FY2025 excluded by hash).
- **Cross-year NULL sweep**: every FLAG is the documented two-family structure — monthly metrics ≥95% NULL in 2019-2022 (panel starts 2022-10-01); FY metrics ≥95% NULL in 2023-2025 only because those years are dominated by 180 monthly rows vs 6-7 FY rows (2026 sits at 91.5%, below the flag line, confirming the same ratio); `guaranteed_minimum_beds` additionally sparse (only 2-3 counties ever have a floor). Matches manifest per-year `non_null_count`s exactly. No era-localized rename-bug signature.
- **Era-boundary continuity**: state FY ADP 2838.7 → 2652.0 → 1450.7 → 2525.9 → 1763.7 → 2408.3 → 3022.3 → 4383.1 (executed); all adjacent ratios 0.55-1.74, no >10x jumps; the FY2021 trough is the real COVID/Irwin-closure dip; ADP averages carry no cumulative-publication signature.
- **County universe**: every monthly (year, month) has exactly 14 county rows (executed min=max=14), matching the contract's "always include all 14 counties" claim.
- **Daily-panel GA universe**: 20 distinct GA facility codes in the panel, all 20 resolve in the crosswalk; heuristic scan found no GA-suffix/BOP code outside the crosswalk — no detectable silent drop (see Judgment Call 2 on the guard asymmetry).

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | All served columns traced; midnight/ALOS/book-in exclusions deliberate + documented |
| Era routing | PASS | Feed-1 eras verification-only; signature detection per file; all 8 workbooks matched an era; byte-identical FY2025 excluded |
| Filter logic | PASS | GA scope, superseded snapshots, partial months all logged + `record_filtered`; accounting reconciles (671=671) |
| Normalization map completeness | PASS | 18/18 name variants seen; unmapped collation names hard-fail; crosswalk membership hard-checked at load |
| `strict=False` casts | PASS | All-string reads cast strict=False; ADP columns have 0 nulls in every era; workbook-vs-collation hard-fail verification would catch parse corruption; GM placeholders the only non-numeric values (traced) |
| Dedup keys + tie-break | PASS | Collision guard before dedup; lanes disjoint by construction |
| Year extraction | PASS | `fiscal_year` column (collation) + date-derived federal FY (panel, traced Dec-2023→FY2024); filename FY verification-only |
| Daily-feed GA-membership guard | LOW | Inner join to crosswalk is unguarded vs the collation feed's hard-fail; see Judgment Call 2 |
| GM placeholder recording | LOW | Log-only; see Judgment Call 1 |

## NEEDS_JUDGMENT

### Judgment Call 1: GM placeholder→NULL conversions are log-only, not manifest-recorded
- **Severity if confirmed**: LOW
- **Suspicion**: The domain convention ("Suppression → NULL … record masked counts on the manifest") could be read to want the 16 `'*'`/`'\xa0'` `guaranteed_minimum` conversions recorded on the manifest, not only in the run log. The manifest has no `masked_values` section.
- **Evidence available**: 16 GA snapshot rows carry the placeholders (executed: distinct values `['*', '\xa0']`); the strict=False cast NULLs them; the conversion is logged, documented in the column's `null_meaning`, and range-guarded. Gold values verified correct (no fake zeros).
- **Why uncertain**: The transform's documented position — the placeholders mean "no contractual floor exists" (a real absence, not suppression of a real value), supported by the bronze doc and `suppressed_to_null: false` — makes the manifest correct as-is; recording them as "masked" could itself mislead (it would imply suppression of a real value).
- **Location**: `transform_collation()` in `transform.py`
- **If confirmed, suggested fix**: Record the placeholder-conversion count on the manifest (a `record_filtered`-style entry with reason `no_contractual_floor_placeholder`) purely for audit completeness; keep `suppressed_to_null: false`.

### Judgment Call 2: daily-feed GA membership is an unguarded inner join (asymmetric with the collation feed)
- **Severity if confirmed**: LOW
- **Suspicion**: `transform_daily` establishes GA membership solely by an **inner join** to the crosswalk (the panel has no state column). Any GA facility present in a future daily-panel refresh but not yet in `facility_to_county.parquet` would be **silently dropped** — with no error, unlike the collation feed, which hard-fails on any unmapped GA name.
- **Evidence available**: Executed — the panel has 20 distinct GA codes, all 20 resolve in the crosswalk; a heuristic scan for GA-suffix/BOP codes outside the crosswalk found **none**. So there is **no detectable current drop**. The residual risk is a new GA facility appearing at a refresh boundary before the crosswalk is updated.
- **Why uncertain**: The crosswalk (built from the stints file's state column) is, by design, the authoritative definition of GA membership for the panel; a facility "missing from the crosswalk" is definitionally "not GA" from the transform's viewpoint. The real completeness guarantee lives in the crosswalk build script (`build_facility_to_county.py`), not this transform. No drop is happening today.
- **Location**: `transform_daily()` inner join in `transform.py`
- **If confirmed, suggested fix**: Add a cheap defensive assertion — e.g., flag any panel `detention_facility_code` matching a GA naming heuristic (suffix `GA`, or a stints-derived GA code list) that is absent from the crosswalk — so a future un-crosswalked GA facility fails loudly instead of dropping silently.

## Notes

- Contract `schema_hash`: `1fa3b1218a4c4b01a7f5d927f390ba85882880e935fd2eb29b4edd50ada546e4`; validation 19 pass / 0 fail / 1 warning (tidy_format, explained); gold rows 671 = manifest; grain (year, county_fips, month) unique; FKs resolve (14 counties). Current gold sha256 `fd86c122…`.
- **Prior-review fixes verified landed**: (1) `monthly_rows_start_fy2023` quality check present (grep count 1); (2) limitations reads "(6-9 in Georgia)", matching executed per-FY code counts (6-9); (3) usage + `avg_daily_population` description read "within about 2 percent" (2 occurrences).
- Risk-hypothesis triage: (1) Asian/PI conflation — **N/A**, no demographic column and no race buckets in either feed (bronze doc §12 confirms only gender exists, served as wide metric columns); (6) mutual exclusivity — **N/A** likewise (male+female ≤ total enforced by `monthly_gender_split_within_total`, not a demographic partition); (2)(3)(4)(5)(7) — PASS with evidence above.
- Bronze structure-doc imprecision (doc-only, no gold defect): it says "All 14 GA facility codes present" in the daily panel; the panel actually contains **20** GA crosswalk codes (each with full 1,257-day coverage) that roll up to **14 counties** — the "14" the contract cites is counties, verified exact.
- `avg_daily_population` deliberately carries two definitions on one column (fiscal-YTD ADP on `month='all'` rows; monthly mean of daily `n_detained` on monthly rows). This is a documented design choice — the contract `usage` instructs filtering `month = 'all'` vs `month != 'all'` separately and states the two families reconcile within ~2 percent. Endorsed as-is.
- ALOS and book-ins deliberately not served (documented judgment calls; both endorsed — ALOS does not aggregate by population weights, and the stints file carries DDP-flagged reliability caveats + PII).
