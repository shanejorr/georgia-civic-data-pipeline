# Data Review: fatal_crashes

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

The bronze-to-gold pipeline for NHTSA FARS fatal crashes is accurate. Independent re-verification this session — reading the zip members directly (never extracted) and reconstructing the Georgia aggregates — matched gold exactly on all three global-extreme county rows and a cross-era trace set (1975/1980/1981/2000/2020/2021/2022/2024), and all 50 statewide gold rows equal the structure doc's independent per-year crash/fatality table (0 mismatches). Every quantitative contract claim (126 unknown-county crashes across 1975-2006, worst gap 27 in 1980, DRUNK_DR dropped after 2020) is verified against bronze. **v1 parity: no v1 baseline — this topic is post-v1** (`docs/rebuild/v1-baseline.yaml` has zero criminal_justice entries). No required fixes and no judgment calls.

## Manifest Verification

Freshness: transform mtime `2026-07-02T22:51:24Z` ≤ manifest `2026-07-02T22:51:42Z` ≤ validation `2026-07-02T22:52:39Z` → FRESH. `read_loss`: section absent from the manifest = 0 events (transform verifies raw-line vs parsed-row equality for all 50 files).

### Categorical map (the topic's single recode: county code → FIPS)

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| county_fips | 194 | 194 | 0 | PASS |

Full map review (100% coverage, verified programmatically this session):

- **159 valid codes → FIPS**: every non-None entry equals `"13" + zfill(3)` of the GSA code; the 159 gold values exactly equal the counties-dimension GA PK set (validator FK check: "county_fips -> counties: all 159 keys resolve"). The GSA-code ≡ 3-digit-FIPS-suffix premise was re-verified this review against the `COUNTYNAME` label twins in **2016 (155 distinct codes) and 2024 (151 distinct codes): 0 name/mapping mismatches** — every mapped code's dimension name matches the FARS county-name label. The dimension-membership guard makes a wrong-county map impossible to ship silently.
- **Invalid codes → None (state-only)**: codes not resolving to a valid GA FIPS become NULL (999/0 = unknown; 510/520/507 in 1976-1981; scattered even/out-of-range codes 1986-1994; single 0-code rows 2001-2006). Re-verified this review: **126 such crashes total across exactly 21 years, last in 2006** — matching the contract verbatim. Per-year examples confirmed: 1980 = 27 (codes 124/262/507/510), 1991 = 10 (codes 0/20/28/80/90/130/190/296/471/950 — the structure doc's documented peak), 2001 = 1 (code 0). Crashes are kept at state level, never dropped.
- `bronze_values_seen` == map keys (map built from observed codes; the real guard is dimension membership, as the transform documents).

**2a Completeness**: every documented code family was encountered; no documented value missing from `bronze_values_seen`. PASS.
**2b Correctness**: every entry semantically right — the `"13"+zfill(3)` construction plus the label-twin verification admits no wrong-county mapping. PASS.
**2c Contract cross-check**: `county_fips` is an FK, not an enum categorical — gold values validated against the counties dimension (validator FK check pass), so no contract `enum` to equate. PASS.
**2d Unmapped**: 0. PASS.
**2e Asian/PI conflation**: N/A — no `demographic` column and no `pct_asian` column (county-year count table; person-level demographics deliberately out of v1 scope per structure doc ETL #13).
**2f Mutual exclusivity**: N/A — no demographic column.

### Row-count reconciliation

| Quantity | Value | Assessment |
|----------|-------|------------|
| total_bronze (GA crash rows) | 66,916 | re-summed this review across all 50 zips = 66,916 — exact ✓ |
| total_filtered | 58,916 | per-file `filtered_explicit` = non-GA national rows (e.g. 1975: 39,161 − 1,170 = 37,991) ✓ |
| total_gold | 8,000 | = 50 years × (159 county rows + 1 state row) — exact ✓ |
| Actual parquet rows | 8,000 | equals manifest total_gold; 160 rows/year, 159 county + 1 state, no year deviates ✓ |
| Years | 50 (1975–2024), no gaps, no duplicate files | ✓ |

Per-year bronze GA counts match the structure doc's independent sweep table for **all 50 years**. The bronze→gold "contraction" (~0.11–0.15) is crash-level → county-year aggregation plus densification — uniform by construction (gold is always 160 rows/year).

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| STATE | — (filter == 13) | CORRECTLY EXCLUDED |
| COUNTY | county_fips | MAPPED |
| YEAR (+ filename) | year | MAPPED (2-digit years normalized 1900+YY; hard-fail guard verified all 50 files) |
| (row count) | fatal_crashes | MAPPED |
| FATALS | traffic_fatalities | MAPPED (sum) |
| DRUNK_DR | crashes_with_drunk_driver | MAPPED (count of rows ≥1; NULL 2021+) |
| PEDS (optional in structure doc) | — | CORRECTLY EXCLUDED — deliberate v1 scope (1991+ only, era-gapped); documented in transform docstring |
| VE_FORMS/VE_TOTAL (optional) | — | CORRECTLY EXCLUDED — 2005 definition change (ETL #4); documented v1 scope |
| RUR_URB / LAND_USE / ROAD_FNC (optional) | — | CORRECTLY EXCLUDED — 3-era recode not worth it per structure doc |
| MONTH/DAY/HOUR…, CITY/lat/long, crash-attribute codes, ST_CASE, COUNTYNAME twins, all others | — | CORRECTLY EXCLUDED — sub-grain / sub-county / era-shifting code lists / verification-only, reasons hold |

No gold column lacks a bronze ancestor (`fatal_crashes` is the crash-row count — a legitimate derivation). No fabrication.

## Value-Level Spot Checks

All bronze values were read directly from the zip members (`accident.csv`, `STATE=13`) this session, never extracted to disk. **Every trace: MATCH.**

Extreme rows first (gold global extremes traced back to bronze):

| Trace | Bronze evidence (read this review) | Gold | Verdict |
|-------|-----------------|------|---------|
| Global max fatal_crashes | FARS2021: Fulton (COUNTY=121) = 149 GA crash rows | 2021/13121 fatal_crashes = 149 | MATCH |
| Global max traffic_fatalities | FARS2022: Fulton = 145 rows, sum FATALS = 160 | 2022/13121 traffic_fatalities = 160 | MATCH |
| Global max crashes_with_drunk_driver (county) | FARS1981: Fulton rows with DRUNK_DR≥1 = 48 | 1981/13121 = 48 | MATCH |
| Global min (true zero) | Densified county-years with 0 crash rows → 0/0 | 361 county-years at 0 crashes ⇒ 0 fatalities (quality check enforced) | MATCH |

Ordinary cross-era traces (Fulton COUNTY=121 + statewide, spanning both transform eras and all five analytic bronze eras):

| Year (era) | Bronze Fulton (crashes / FATALS-sum / DRUNK_DR≥1) | Bronze state (GA rows / FATALS / DRUNK_DR≥1) | Gold | Verdict |
|------------|------------------|----------------|------|---------|
| 1975 (A) | 95 / 100 / 13 | 1170 / 1360 / 247 | same | MATCH |
| 1980 (A) | 130 / 138 / 38 | 1348 / 1508 / 564 | same | MATCH |
| 1981 (A) | 138 / 151 / 48 | 1256 / 1418 / 543 | same | MATCH |
| 2000 (C) | 107 / 123 / 32 | 1380 / 1541 / 414 | same | MATCH |
| 2020 (E) | 119 / 145 / 23 | 1517 / 1658 / 364 | same | MATCH |
| 2021 (E, post-DRUNK_DR) | 149 / 153 / (DRUNK_DR absent) | 1681 / 1809 / — | drunk = NULL, counts match | MATCH |
| 2022 (E, post) | 145 / 160 / (absent) | 1677 / 1796 / — | drunk = NULL, counts match | MATCH |
| 2024 (E, post) | 91 / 95 / (absent) | 1312 / 1403 / — | drunk = NULL, counts match | MATCH |

`has_DRUNK_DR` read from bronze directly: True for 1975/1980/1981/2000/2020, **False for 2021/2022/2024** — confirming the era boundary is source-real, not a rename bug.

- **4a Extreme-row traces**: all three global maxima and the true-zero minimum trace cleanly (above). PASS.
- **4b Ordinary traces**: one large entity (Fulton) + statewide across all eras — all MATCH (above). PASS.
- **4c Sentinel year-attribution**: PASS — `year` comes from the filename regex; the transform normalizes bronze `YEAR` (1900+YY for 2-digit 1975-1997) and **hard-fails** if the GA slice's year ≠ filename year. All 50 files passed at transform time (no exception). The YEAR=99 unknown-date sentinel exists only on non-GA rows (transform checks the GA slice — correct).
- **4d Aggregate reconciliation**: state rows are DERIVED (group_by over the same crash rows). Reconciled this review per year for all 3 metrics: **0 violations of state ≥ county-sum**; positive gaps occur in exactly the 21 unknown-county years, totaling 126 crashes (worst: 1980 gap = 27 = the 27 invalid-code rows). No `.mean()` on any percentage (all metrics are counts).
- **4e Dedup tie-break**: N/A — one file per year, 50 unique years, no era-overlap years. Collision guard runs before the documented `sort_col="traffic_fatalities"` safety net.
- **4f Suppression**: N/A — FARS is unsuppressed public-domain microdata; `suppressed_to_null=false`; validator found no suppression markers.

## Validation Cross-Read

- `_validation.json`: **passed=true — 19 pass / 0 fail / 1 warning** (2026-07-02T22:52:39Z). `contract_parquet_schema` (100 files), `contract_quality_sql` (13/13), `grain_uniqueness` (['year','county_fips']), `foreign_keys` (159/159 resolve), and geography nulling (counties + states) all pass.
- The single warning — `crashes_with_drunk_driver` 100% NULL in 2021/2022/2023/2024 — is the documented NHTSA drop of DRUNK_DR after data year 2020. It is enforced (not merely narrated) by the authored `drunk_driver_metric_era_coverage` quality check and documented in the column's `null_meaning`. Explained; no action.
- `schema_hash`: `ff74843cd70be4c3f61b4b8dbf5691ef2520065098bd90c74d018353d232942e`.
- **§4b masking audit**: no `_null_*` masking helpers in transform.py (the only null-related util is `check_null_rate_spikes`, a pre-export sanity log, not a mask); no `masked_values` manifest section — consistent. The no-mask claim is empirically grounded (FATALS 1-7, DRUNK_DR 0-4, no impossible values), and the `unit: count` (≥0) range guards remain enforceable. PASS.
- **§15b coverage judgment**: the 13 quality checks cover the topic's real cross-column invariants well — fatalities ≥ crashes, zero-crashes ⇒ zero-fatalities, drunk-subset ≤ crashes, the DRUNK_DR era boundary (both directions), exactly 159 county rows + exactly 1 state row per year, and state ≥ county-sum for all three metrics (the correct enforceable form given unknown-county crashes live only in state rows). No missing obvious invariant.
- **v1 parity**: **no v1 baseline — topic is post-v1.** `docs/rebuild/v1-baseline.yaml` has no `criminal_justice/traffic_safety/fatal_crashes` key (zero criminal_justice keys among its topics). Executed check output: `DIFFERS from v1  v1:None  now:50fa46d55c7d8969ab3edb1b49c1486a52a6717eff4b8d373174d2d3f1701660` — the `None` baseline confirms absence of a predecessor, not a divergence. Not a finding.

## Cross-Era Consistency

- **Overlap years**: none (one national zip per year; era split is 1975–2020 `fars_with_drunk_dr` / 2021–2024 `fars_post_drunk_dr`, confirmed from `files_processed` — a 46/4 file split).
- **Era boundary (2020→2021)**: crashes 1517→1681 and fatalities 1658→1809 are continuous (~+11%, consistent with the national 2021 fatality surge); only `crashes_with_drunk_driver` changes state (364 → NULL), by design.
- **Cross-year NULL sweep (Step 3c)**: single flag — `crashes_with_drunk_driver` ≥95% NULL in [2021, 2022, 2023, 2024] only. This is the documented era boundary, not an era-localized rename bug (bronze 2021+ genuinely lacks DRUNK_DR, confirmed directly). `fatal_crashes` and `traffic_fatalities` have 0 NULLs in every year; no column is all-NULL.
- **YoY continuity (Step 3d)**: no >10x jumps anywhere in the state series (all metrics range ~1,080–1,809). No sustained cumulative-publication doubling. No action.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Explicit `select` of 4 columns per file; unneeded bronze columns intentionally unread |
| Era routing | PASS | Ordered signatures, most-specific first: DRUNK_DR-bearing signature wins for all files ≤2020; 2021+ matched via VE_TOTAL. Bronze `has_DRUNK_DR` confirms the 46/4 split; unmatched schema raises |
| Filter logic | PASS | Single filter STATE==13, recorded per file as `out_of_scope_non_georgia_states` with explicit counts |
| Normalization map completeness | PASS | County map covers all 194 observed codes; guard is dimension membership, not the map itself (unmapped_count=0 by construction) |
| `strict=False` casts | PASS | None — all casts strict (fail-loud); `infer_schema_length=0` + explicit casts avoids type-inference loss |
| Dedup keys + tie-break | PASS | Duplicates impossible by construction (1 file/year, single group_by per level); collision guard raises before the documented `sort_col` safety net |
| Year extraction | PASS | Filename regex + hard-fail equality check against the GA slice's normalized YEAR (all 50 verified; YEAR=99 sentinel only out-of-scope) |
| §4b masks | PASS | None applied, none needed (empirically grounded) |

## Notes

- schema_hash: `ff74843cd70be4c3f61b4b8dbf5691ef2520065098bd90c74d018353d232942e`
- Validation: 19 pass / 0 fail / 1 warning (documented DRUNK_DR era NULL spike)
- Gold: 8,000 rows = 50 years × (159 counties + 1 state); 361 true-zero county-years (census semantics, correctly densified)
- v1 parity: no v1 baseline (post-v1 topic — no criminal_justice entries in the v1 baseline); current gold sha256 `50fa46d55c7d8969ab3edb1b49c1486a52a6717eff4b8d373174d2d3f1701660`
- Contract prose fidelity (Step 6): no contradictions vs `bronze-data-structure.md` — year range 1975-2024, unsuppressed/zeros-real, no percentage columns, no demographics, DRUNK_DR 1975-2020, the 126 unknown-county crashes, and the 159-counties-are-a-census claim all agree with the bronze doc and were re-verified against bronze
- Deliberate v1 metric scope (PEDS, vehicles, person-level demographics omitted) is documented in the transform docstring and consistent with the structure doc's "optional" designations — a future person-file topic can add demographics without touching this table
- Bronze zips were read as members via `zipfile` (never extracted), honoring the provenance contract
