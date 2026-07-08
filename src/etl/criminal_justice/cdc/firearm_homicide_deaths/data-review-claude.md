# Data Review: firearm_homicide_deaths

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Zero required fixes, zero open judgment calls. Both categorical maps are identity on
canonical values and semantically verified against the source cause definitions; row
counts reconcile exactly (18,444 bronze − 1,908 overlap-drop = 16,536 gold); every
value-level trace I ran (six extreme rows, one ordinary row per era, both suppression
markers, and the 2018-2020 vintage-overlap stitch) MATCHes bronze verbatim; manifest mask
counts reconcile against gold NULL counts; and the contract's served prose contains no
contradiction with the bronze doc. **v1 parity: no baseline — this topic is post-v1**
(`docs/rebuild/v1-baseline.yaml` has zero `criminal_justice/*` keys), so its `DIFFERS
(v1: None)` is expected and not a finding.

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| cause_category | 4 (identity) | 4 | 0 | PASS |
| dataset_vintage | 2 (identity) | 2 | 0 | PASS |

**cause_category — full map review.** The four values are filename slugs mapped to
themselves, so the semantic question is whether each slug names the cause actually
queried. The bronze structure doc records each file's footer Query Parameters:
`firearm_deaths` = UCD Injury Mechanism = Firearm (all intents); `homicide` = UCD Injury
Intent = Homicide (all mechanisms); `firearm_homicide` = Homicide intent AND Firearm
mechanism (subset of both); `legal_intervention` = Injury Intent = Legal Intervention /
Operations of War. Each slug→code is meaningfully correct, not merely snake-cased. An
unknown slug hard-fails in `_parse_cause_slug` (never guessed). `gold_values_produced`
= `[firearm_deaths, firearm_homicide, homicide, legal_intervention]` equals the contract
`enum`. `unmapped_count = 0`.

**dataset_vintage — full map review.** Era-derived, not read from a bronze cell:
`d77_bridged_race → bridged_race`, `d157_single_race → single_race`. Era is detected by
column signature (only D157 carries `Crude Rate Upper 95% Confidence Interval`; only D77
carries `Age Adjusted Rate`), with the full 4-cause × 2-era matrix asserted present.
Both entries semantically correct; `gold_values_produced` = `[bridged_race, single_race]`
equals the contract `enum`; `unmapped_count = 0`.

### Row-count reconciliation

| Segment | Bronze | Filtered | Gold | Check |
|---------|-------:|---------:|-----:|-------|
| 1999-2017 (19 years) | 636/yr | 0 | 636/yr | 159 counties × 4 causes ✓ |
| 2018-2020 (3 years) | 1,272/yr | 636/yr | 636/yr | D77 overlap dropped (159/cause/year asserted) ✓ |
| 2021-2024 (4 years) | 636/yr | 0 | 636/yr | ✓ |
| **Total** | **18,444** | **1,908** | **16,536** | 18,444 = 4×(3,498+1,113); 1,908 = 3×636; 16,536 = 26×636 ✓ |

Actual parquet row count = **16,536** = manifest `total_gold` ✓. Every year has exactly
636 rows and 159 counties (verified in parquet). Read loss: 0 events. Sole filter reason
`d77_overlap_year_served_from_d157_vintage` (1,908 rows) matches the documented stitch.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| County Code | county_fips | MAPPED (5-char zero-padded string; `^13\d{3}$` hard-fail guard) |
| Year Code | year | MAPPED (Int32; `Year` avoided per the `'2024 '` trailing-space defect) |
| *(filename slug)* | cause_category | MAPPED (verified against footer cause definitions) |
| *(era signature)* | dataset_vintage | MAPPED (transform-modeled methodology flag) |
| Deaths | deaths | MAPPED (`Suppressed` → NULL) |
| Population | population | MAPPED (never suppressed; hard-fail guard on NULL) |
| Crude Rate | crude_rate_per_100k | MAPPED (`Suppressed`/`Unreliable` → NULL) |
| Age Adjusted Rate | age_adjusted_rate_per_100k | MAPPED (D77 only; typed-NULL emitted for D157 files, logged) |
| Crude Rate Lower/Upper 95% CI | — | CORRECTLY EXCLUDED — deliberate, and consistent with the bronze doc's own conditional framing ("If gold keeps CI columns, they'll be NULL for 1999-2017"): no platform interval-estimate vocabulary; documented in the module docstring AND contract `limitations` ("The source's crude-rate 95% confidence-interval bounds … are not served"); bronze retains them for a future additive change |
| County | — | CORRECTLY EXCLUDED (county_name lives in the counties dimension) |
| Notes | — | CORRECTLY EXCLUDED (100% null on data rows; footer discriminator only) |
| Year | — | CORRECTLY EXCLUDED (duplicate of Year Code with the trailing-space defect) |

No gold column lacks a bronze provenance (no fabrication; `dataset_vintage` is a
documented era-derived methodology flag).

## Value-Level Spot Checks

All bronze quotes are verbatim grep output (tab-separated; `<CountyName>` `<FIPS>`
`<Year>` `<YearCode>` `<Deaths>` `<Population>` `<CrudeRate>` `<AAR or CI…>`). All traces MATCH.

**Extreme rows (4a):**

| Trace | Bronze (file, quoted) | Gold | Verdict |
|---|---|---|---|
| Global max deaths | fd_2018_2024: `"Fulton County, GA" "13121" "2021" "2021" 258 1065334 24.2 21.3 27.2` | 2021/13121/firearm_deaths: deaths=258, pop=1065334, crude=24.2, aar=NULL, single_race | MATCH (258/1065334×100k = 24.22 → 24.2; CIs dropped as documented) |
| Global max crude rate | fd_2018_2024: `"Jefferson County, GA" "13163" "2022" "2022" 10 15314 65.3 31.3 120.1` | 2022/13163/firearm_deaths: deaths=10, crude=65.3, single_race | MATCH (10/15314×100k = 65.30; extreme-but-real small county; <20 deaths but single_race so rate published, correct) |
| Global max age-adjusted rate | fd_1999_2020: `"Muscogee County, GA" "13215" "2017" "2017" 59 194058 30.4 29.6` | 2017/13215/firearm_deaths: deaths=59, crude=30.4, aar=29.6, bridged_race | MATCH |
| Global min (nonzero) AAR | fh_1999_2020: `"Gwinnett County, GA" "13135" "2012" "2012" 22 842046 2.6 2.5` | 2012/13135/firearm_homicide: deaths=22, crude=2.6, aar=2.5, bridged_race | MATCH |
| Global max population | 2024/13121 pop=1090354 (identical across all four cause rows) | population constant per county-year (`population_consistent_across_causes` passes) | MATCH |
| Global min deaths (true zero) | fd_1999_2020: `"Clay County, GA" "13061" "2007" "2007" 0 3262 Unreliable Unreliable` | 2007/13061/firearm_deaths: deaths=0, crude=NULL, aar=NULL, bridged_race | MATCH — true zero preserved as 0; D77 zero-death rate masked |

Global min crude rate = 0.0: 1,697 gold rows carry crude=0.0, **all** `single_race` with
`deaths=0` — exactly the D157 zero-death convention (D77 zero-death rows are `Unreliable`
→ NULL instead). No stray zero-crude rows elsewhere.

**Ordinary trace, per era:**

| Trace | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| D157: Bulloch 2024 firearm_deaths | `"Bulloch County, GA" "13031" "2024 " "2024" 15 85454 17.6 9.8 29.0` | year=2024, deaths=15, pop=85454, crude=17.6, aar=NULL, single_race | MATCH — also proves `Year Code` was used, bypassing the `'2024 '` trailing-space `Year` cell |
| D77: Clay 2007 firearm_deaths | (quoted above) | deaths=0, pop=3262, rates NULL, bridged_race | MATCH |

**Suppression semantics (4f):**

| Marker | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| `Suppressed` | fd_2018_2024: `"Sumter County, GA" "13261" "2022" "2022" Suppressed 28877 Suppressed Suppressed Suppressed` | deaths=NULL, pop=28877, crude=NULL, aar=NULL | MATCH — count AND rates NULLed, population kept |
| `Unreliable` | fd_1999_2020: Clay 2007 `0 3262 Unreliable Unreliable` | deaths=**0** (kept), crude=NULL, aar=NULL | MATCH — rate-only mask, count survives |

**Dedup / stitch winner (4e)** — 2018-2020 is covered by both vintages; documented
winner is D157. Overlap-identity spot check, Fulton homicide (raw D77 vs raw D157):

| Year | D77 (Deaths/Pop/Crude) | D157 (Deaths/Pop/Crude) | Gold |
|---|---|---|---|
| 2018 | 116 / 1050114 / 11.0 | 116 / 1050114 / 11.0 | single_race |
| 2019 | 145 / 1063937 / 13.6 | 145 / 1063937 / 13.6 | single_race |
| 2020 | 201 / 1077402 / 18.7 | 201 / 1077402 / 18.7 | single_race |

Raw values identical across vintages; gold serves only `single_race` for 2018-2020
(verified — one vintage per year). No blend.

**Sentinel year-attribution (4c):** N/A as a sentinel-string risk — gold `year` comes
from the per-row `Year Code` column, never from a filename or an embedded string. The
transform's only year literals (`D157_START_YEAR = 2018`, `OVERLAP_YEARS`) are stitch
constants, checked by the `vintage_year_alignment` quality check and the Bulloch-2024
trailing-space trace.

**Aggregate-row reconciliation (4d):** N/A — the transform derives no aggregate rows, and
bronze has none (`Show Totals: Disabled`; WONDER withheld state totals). County detail
only. The relevant cross-row invariant is cross-cause containment: Fulton 2021
firearm_homicide=169 ≤ homicide=195 ≤ firearm_deaths=258 (spot-checked); enforced for all
county-years by `firearm_homicide_contained_in_parents` (passing).

## Validation Cross-Read

- `_validation.json`: **passed=true, 19 pass / 0 fail / 0 warning** (timestamp
  2026-07-02T23:51:53Z, fresh vs manifest 23:50:29Z). `contract_parquet_schema`,
  `contract_quality_sql` (17 checks), `grain_uniqueness`
  (`year, county_fips, cause_category, dataset_vintage`), and `foreign_keys`
  (`county_fips → counties`: all 159 keys resolve) all pass.
- **schema_hash**: `239bee9385ad012f1e3d883f5760f71aabb3154cbb9f0429eed65d2a01b89f7c`
- **§4b masking audit**: no `_null_*` helpers and no §4b impossible-value masks (the
  maxima 65.3 per 100k and 258 deaths are extreme-but-conceivable published values,
  preserved per the module docstring). The only masks are source suppression markers
  (§8), fully recorded in the manifest `masked_values` and independently reconciled
  against gold NULL counts — e.g. firearm_deaths: single_race deaths NULL = **698**
  (manifest 698); bridged_race deaths NULL = **2,084** (manifest 2,084; = bronze-doc
  1999-2020 total 2,384 minus the 300 dropped 2018-2020 overlap cells, since the mask runs
  after the stitch drop). Handling documented per column via `null_meaning` + descriptions;
  enforceability guarded by authored non-negativity checks (the per-100k rate columns carry
  no `unit`, per the sanctioned overdose_deaths precedent). Independent invariant probes:
  0 rows with NULL deaths but a non-NULL rate; 0 single_race rows with a non-NULL AAR.
- **§15b coverage judgment**: the authored quality set is unusually thorough and covers
  every real cross-column invariant I could identify — rate↔count reconciliation (±0.051
  rounding), suppression implication (NULL deaths ⇒ NULL rates), both vintage rate
  conventions (D77 <20-death mask; D157 full coverage + true-0.0), AAR bridged-only,
  vintage-year alignment, category containment (fh ≤ fd, fh ≤ hom), population consistency
  across causes, 159-county grid, and all-4-causes-per-year. No obvious missing invariant
  (legal_intervention is NOT strictly ⊆ firearm_deaths, so a containment check there would
  be wrong — correctly not authored).
- **v1 parity**: `compute_gold_sha256` returns
  `0e8ac7fe1e81a6afa684d2fc234972776ee1c398112976304f55ae5fb5073697`; the baseline has no
  `criminal_justice/cdc/firearm_homicide_deaths` entry (`old = None`), so the script prints
  `DIFFERS (v1: None)`. **No v1 baseline — topic is post-v1**; not a divergence, not a finding.

## Cross-Era Consistency

- **Overlap years**: 2018-2020 exist in both bronze vintages; gold serves them exclusively
  from `single_race` (verified). The transform hard-asserts raw-string identity of
  Deaths/Population and numeric crude-rate equality across vintages for all 159 × 3
  county-years × 4 causes before stitching, then asserts the drop shape is exactly 159 rows
  per overlap year per cause. Independent spot check (Fulton homicide, above) confirms
  identity.
- **Era-boundary continuity (3d)**: population and visible-deaths sums move smoothly across
  the 2017→2018 stitch; the largest adjacent-year move is the real 2020→2021 national
  homicide rise, not a stitch artifact. No >10× adjacent-year jumps in any metric; no
  cumulative-publication revert pattern (metric ranges are contract-enforced and not
  re-verified here).
- **Cross-year NULL sweep (3c)**: two flags, both explained by source masking conventions,
  neither a rename bug —
  - `crude_rate_per_100k` ≥95% NULL in 1999-2016 (2017 = 94.3%, just under threshold):
    D77 masks all <20-death rates `Unreliable` (incl. every zero-death row) and the D77
    legal_intervention file has zero numeric rates, so only 19-36 rates/year survive —
    exactly the manifest per-year `non_null_count`. Values ARE present in-era, so this is
    not the Risk-2 signature. NULL density then drops to ~49% from 2018 (D157 convention).
  - `age_adjusted_rate_per_100k` ≥95% NULL in 1999-2016 (same D77 masking) and 100% NULL
    2018-2024 (WONDER forbids AAR at county grain in D157; enforced by
    `age_adjusted_rate_bridged_race_only` and documented in `null_meaning`).
  `deaths` and `population` have no ≥95%-null years.

## Transform Logic Risks

| Risk (Step 7 item) | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `select(STANDARD_COLUMNS)` drops County/Notes/Year/CI columns — every exclusion documented (Column Coverage) |
| Era routing correctness | PASS | Column-signature detection (CI vs AAR, most-specific first) + hard assertion the full 4-cause × 2-era matrix is present |
| Filter logic logged + justified | PASS | Sole filter is the overlap drop: exact-count asserted (159 × {2018,2019,2020} per cause), recorded as `filtered_explicit` with reason, logged |
| Normalization map completeness | PASS | Identity maps; all 4 slugs match footer cause definitions; unknown slug hard-fails |
| `strict=False` casts | PASS | Guarded: bronze true-null count must be 0; post-cast null count must equal marker count; any non-marker non-numeric value hard-fails (`junk` check) — nothing slips to NULL unrecorded |
| Dedup keys + tie-break | PASS | Stitch makes cross-vintage duplicates structurally impossible; collision guard runs on keys EXCLUDING `dataset_vintage` (a stitch bug would collide loudly); `deduplicate_by_levels` asserted to remove exactly 0 rows; winner traced (Fulton overlap) |
| Year extraction | PASS | Per-row `Year Code` (clean); unparseable years hard-fail; traced through Bulloch 2024 (`'2024 '` defect bypassed) |
| §5b mask recording | PASS | `masked_values` entries reconcile with gold NULL counts (698 / 2,084 verified); `null_meaning` documented on all maskable columns |

Risk-hypothesis closure: (1) Asian/PI conflation — **N/A**, no demographic column (bronze
doc: "No demographic columns"; validator: "No demographic column (skipped)"). (2)
Column-rename typo — PASS, both NULL-sweep flags explained by in-era source masking with
values present. (3) Sentinel year-attribution — N/A (year from `Year Code`). (4)
Derived-row aggregation — N/A, nothing derived. (5) Dedup tie-break inversion — PASS,
traced. (6) Mutual exclusivity — N/A, no demographic; `cause_category` non-additivity is
documented and containment-enforced. (7) Semantically wrong mapping — PASS, all 4 causes +
2 vintages verified.

## Notes

- schema_hash `239bee9385ad012f1e3d883f5760f71aabb3154cbb9f0429eed65d2a01b89f7c`; contract
  version 1.0.0; validation 19 pass / 0 fail / 0 warning. Grain
  `(year, county_fips, cause_category, dataset_vintage)`; `dataset_vintage` is functionally
  derived from `year`, so the reduced key `(year, county_fips, cause_category)` is also
  unique.
- Gold = 16,536 rows (26 years × 636), county detail only, no state rows (matches WONDER's
  withheld totals; `usage` warns against summing counties into a state total, and against
  summing across the overlapping `cause_category` values).
- The 95% CI columns (D157) remain in bronze only; serving them later would be an additive
  change (new columns, minor version bump). Their exclusion is consistent with the bronze
  doc's own conditional classification and is documented in the contract `limitations`, so
  it is not treated as a missing gold column.
