# Data Review: hate_crimes

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Gold is accurate at every level checked. An independent bronze re-aggregation
(zip → GA filter → ORI crosswalk → multi-bias explode → county/state grain)
reproduces the shipped extremes, aggregates, and NULL propagation exactly; all
three categorical maps (bias_motivation, bias_category, ORI→county_fips) are
semantically correct with `unmapped_count == 0`; and every state rollup equals
its county sum for all (year, bias_motivation) pairs. The prior review's single
MEDIUM (missing `victim_count` cross-level check) has been **resolved** — the
contract now carries `state_victim_total_covers_county_sum` and validation
reports all 14 quality checks passing. v1 parity is **no v1 baseline (post-v1
topic)**: `docs/rebuild/v1-baseline.yaml` has zero `criminal_justice/*` entries.
No Required Fixes; no open judgment calls.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|--------|------------|--------------------|----------|--------|
| bias_motivation | 35 (full national vocab) | 32 (all GA values) | 0 | PASS |
| bias_category | 35 (same keys) | 32 | 0 | PASS |
| county_fips (ORI→FIPS) | 224 (observed slice) | 224 | 0 | PASS |

**2a Completeness.** The structure doc's `bias_desc` atomic table lists 32 GA
values; all 32 appear verbatim in `bronze_values_seen` for both bias columns.
The 3 map keys with no GA rows (`Anti-Hindu`, `Anti-Jehovah's Witness`,
`Unknown (offender's motivation not known)`) are exactly the structure doc's
"national-only, not yet in GA" list — refresh headroom, not a routing gap.

**2b Correctness — 100% semantic review of every map entry.**
- Race/ethnicity/ancestry (9): `Anti-American Indian or Alaska Native`, `Anti-Arab`,
  `Anti-Asian`, `Anti-Black or African American`, `Anti-Hispanic or Latino`,
  `Anti-Multiple Races, Group`, `Anti-Native Hawaiian or Other Pacific Islander`,
  `Anti-Other Race/Ethnicity/Ancestry`, `Anti-White` → snake_case preserving full
  meaning; all → `race_ethnicity_ancestry`. Matches the FBI's own category scheme
  (Anti-Arab / Anti-Hispanic are ancestry/ethnicity biases there). ✓
- Religion (14): every `Anti-{faith}` → `religion`. Pure-gloss parentheticals
  dropped without loss (`Anti-Islamic (Muslim)`→`anti_islamic`,
  `Anti-Eastern Orthodox (Russian, Greek, Other)`→`anti_eastern_orthodox`). ✓
- Sexual orientation (5): `Anti-Gay (Male)`→`anti_gay_male`,
  `Anti-Lesbian (Female)`→`anti_lesbian_female`,
  `Anti-Lesbian, Gay, Bisexual, or Transgender (Mixed Group)`→`anti_lgbt_mixed_group`
  keep disambiguating parentheticals; Anti-Bisexual/Anti-Heterosexual straightforward.
  All → `sexual_orientation`. ✓
- Disability (2)→`disability`; Gender (Anti-Female/Anti-Male)→`gender`; Gender
  identity (Anti-Gender Non-Conforming/Anti-Transgender)→`gender_identity`. Matches
  the CDE split of Gender vs Gender Identity. ✓
- `Unknown (offender's motivation not known)`→`unknown_motivation`/`unknown`. ✓

**county_fips (ORI→county).** Verified samples against the counties dimension,
including the three structure-doc judgment cases: `GAAPD0000` Atlanta PD → `13121`
Fulton (multi-county, primary-county convention documented in contract
limitations), `GA0331100` Southern Polytechnic State University → `13067` Cobb,
`GA1080100` Watkinsville → `13219` Oconee (the two crosswalk-gap overrides).
Gwinnett `GA0670200` → `13135`, Camden `GA0200000` → `13039`, Bibb `GA0110000` →
`13021`, Cobb County PD `GA0330200` → `13067` all confirmed. FK check: all 108
county keys resolve.

**Row-count reconciliation.** Manifest `total_bronze` 265,834 = national rows;
`filtered_explicit_by_reason.non_georgia_state_row` 263,851 = 265,834 − 1,983 GA
rows (independently confirmed: GA rows = 1,983, distinct `incident_id` = 1,983).
1,983 GA incidents → 1,999 incident-bias pairs (+16 from 15 multi-bias incidents,
one carrying 3 biases) → 1,299 gold rows (952 county + 347 state). Gold parquet
sum = 1,299 = manifest `total_gold`. Tiny expansion factors (~0.002–0.016)
reflect aggregating the national file down to GA county×bias cells; the 2019+
step-up (gold 35→116 rows) tracks the documented 11→71 agency participation jump.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|------------|--------|
| data_year | year | MAPPED (Int32; `year(incident_date)==data_year` asserted) |
| ori | county_fips | MAPPED (shared crosswalk; hard-fail on unmatched) |
| bias_desc | bias_motivation + bias_category | MAPPED (explode on `;`, pinned vocab, hard-fail on unknown) |
| incident_id | incident_count | MAPPED (`n_unique` per cell; global uniqueness asserted) |
| total_individual_victims | victim_count | MAPPED (sum with NULL propagation) |
| total_offender_count | known_offender_count | MAPPED (sum; 0 = unknown offenders; never-null asserted) |
| ori (distinct) | agencies_reporting | DERIVED (distinct reporting ORIs per geography-year) |
| adult/juvenile victim & offender counts | — | CORRECTLY EXCLUDED (NIBRS-only null pattern, ETL #5) |
| victim_count (bronze) | — | CORRECTLY EXCLUDED (entity-type count, misleading, ETL #7) |
| offense_name, location_name, victim_types | — | CORRECTLY EXCLUDED (sparse at bias grain; docstring justifies) |
| offender_race / offender_ethnicity | — | CORRECTLY EXCLUDED (offender demographics ≠ demographics-dimension semantics) |
| pug_agency_name, agency_type_name, pub_agency_unit, state_*/division/region, population_group_*, incident_date, multiple_offense, multiple_bias | — | CORRECTLY EXCLUDED (constants after GA filter / redundant flags / agency attrs live with crosswalk) |

No gold column lacks a bronze ancestry; no `fact_key`/`fact_metric` from the
structure doc's Gold Schema Classification is missing.

**Contract prose fidelity** (audited against `bronze-data-structure.md` for
contradictions): year range 1991–2024, "32 observed atomic bias motivations",
11→71 agencies in 2019, decline to 45 by 2024, "224 reporting agencies", 16
multi-county agencies covering ~30% dominated by Atlanta PD→Fulton, "15 Georgia
incidents, 2017-2019" NULL victims, "about a third" of incidents with unknown
offenders (655/1,983 = 33%), unsuppressed source — **every assertion matches the
bronze doc**. No contradictions found.

## Value-Level Spot Checks

Bronze values quoted from the zip CSV (`hate_crime/hate_crime.csv`), GA filter.

- **4a incident_count global MAX = 105** (2021 state, `anti_black_or_african_american`):
  bronze has exactly **105** distinct GA 2021 incidents whose `bias_desc` contains
  `Anti-Black or African American`. MATCH.
- **4a victim_count global MAX = 115** (2021 state, `anti_black_or_african_american`):
  sum of `total_individual_victims` over those 105 incidents = **115**. MATCH.
- **4a victim_count 2017 MAX = 101** (state, `anti_multiple_races_group`): bronze
  incident `190211` (`ori=GA0670200` Gwinnett → 13135,
  `bias_desc='Anti-Islamic (Muslim);Anti-Multiple Races, Group'`,
  `total_individual_victims=100`, `offense_name='Intimidation;Simple Assault'`)
  explodes into both bias cells; 2017 Anti-Multiple-Races has 2 incidents summing to
  **101** victims. This is the structure-doc §Statistics extreme, preserved as
  documented (not masked). MATCH.
- **4a known_offender_count global MAX = 91** (1992 state, `anti_white`): 22 distinct
  GA 1992 Anti-White incidents, `sum(total_offender_count)` = **91**. MATCH.
- **4a agencies_reporting global MAX = 82** (2020 state): distinct GA ORIs in 2020 =
  **82**. MATCH.
- **4a global MINs**: `incident_count` min = 1 (grain floor, quality-checked);
  `victim_count`/`known_offender_count` min = 0 (real — entity-only victims /
  unidentified offenders, `zero_is_real`). ✓
- **4b ordinary traces (single era):** `1467690` (2022, Camden `GA0200000`,
  Anti-White, iv=1, off=1) → gold (2022, 13039, anti_white) = 1/1/1 MATCH;
  `1458630` (2021, Cobb PD `GA0330200`, Anti-Black, iv=1, off=1) → cell (2021,
  13067, anti_black) present with incident_count 13 (this incident among them) MATCH;
  `1547665` (2024, Bibb `GA0110000`, Anti-White, iv=1, off=2) → gold (2024, 13021,
  anti_white) = 1/1/2 MATCH.
- **4c sentinel year-attribution: N/A** — year is the `data_year` column; the
  transform asserts `year(incident_date) == data_year` on every GA row (hard fail).
  No year is parsed out of any string for attribution.
- **4d aggregate reconciliation:** DERIVED state rows re-aggregate all incidents.
  Executed full sweep: for **every** (year, bias_motivation), state
  `incident_count` == sum of county `incident_count` (0 mismatches) — a clean
  rollup, no statewide-only agencies today. No `.mean()` on any percentage (all
  metrics are counts). Verified Atlanta PD attribution: `GAAPD0000` 2021 Anti-Black
  = 4 incidents, folded into Fulton (13121) county cell of 11. ✓
- **4e dedup tie-break: N/A** — single national file, `incident_id` global
  uniqueness asserted; `deduplicate_by_levels(sort_col='incident_count')` is a
  documented no-op safety net.
- **4f suppression / NULL provenance:** no FBI suppression markers. Literal `NULL`
  `total_individual_victims` in **15** GA incidents (2017: 5, 2018: 4, 2019: 6 —
  matches contract "15 Georgia incidents, 2017-2019"). Traced `190205`
  (`GA0290200` → 13059 Dougherty, Anti-Black, iv=NULL) → gold (2017, 13059,
  anti_black) `victim_count` is **NULL** (incident_count=2, known_offender_count=2)
  — NULL propagation, never an understated sum. MATCH.

## Validation Cross-Read

- `_validation.json`: **passed=true**, 19 pass / 0 fail / 1 warning.
  `contract_parquet_schema` (68 files), `contract_quality_sql` (**14** checks),
  `grain_uniqueness` (`['year','county_fips','bias_motivation','bias_category']`),
  `foreign_keys` (`county_fips -> counties: all 108 keys resolve`) all pass.
  Independently confirmed grain uniqueness (0 duplicate natural-key groups) and the
  bias_motivation→bias_category functional dependency (0 violations, 32 motivations
  over 6 GA categories).
- **Warning explained:** `victim_count year=2017: null_rate=41.7%` — the 15
  NULL-victim incidents of 2017–2019 propagate to whole cells; 2017 has the highest
  concentration. Correct, documented behavior (`null_meaning`), not a defect.
- `schema_hash`: `e296e679430a7aa5e2d66cead62d4c863e487bdecd4316a0acef08ed693c1a5a`.
- **§5b masking audit:** no `_null_*` helpers in the transform; no `masked_values`
  section in the manifest (absent = zero); the one extreme-but-conceivable value
  (2017 Gwinnett, 100 victims) is preserved and documented in the contract, not
  masked. PASS.
- **§5c coverage judgment:** 8 authored checks cover the real invariants —
  incident floor (`incident_count_at_least_one`), all three summable metrics'
  state≥county-sum consistency (incident, known_offender, **and now victim**,
  NULL-aware), the bias_motivation→bias_category functional dependency, and
  agencies_reporting constancy/floor/ceiling — plus the 6 auto-derived
  enum/non-negative checks. No missing obvious invariant. The prior review's gap is
  closed.
- **v1 parity (executed output, verbatim):**

  ```
  v1 entry present? False
  current gold sha256: dcbe399f7d28f5dc72d25998a87870ce964b63bf3d21fe8faaefb5cf8d5f5ff0
  v1 baseline sha256 : None
  DIFFERS (v1: None)
  ```

  `v1: None` means **no baseline entry exists** — `docs/rebuild/v1-baseline.yaml`
  has zero `criminal_justice/*` topics. This topic is post-v1, so this is **not** a
  divergence to explain.

## Cross-Era Consistency

- Single era (`hate_crime_master_v1`, uniform 28-column schema 1991–2024,
  signature-detected). No overlap years, no era boundaries.
- Cross-year NULL sweep: **clean** — no column ~100% NULL in any subset of years;
  only `victim_count` has year-localized NULLs (2017–2019, documented).
- 3d level continuity: no >10x jumps in state-level sums for incident or offender
  counts. The victim-sum blip at 2017 (driven by the 100-victim Gwinnett incident
  counted under both its biases) reverts the next year with no matching
  incident-count jump — an extreme value, not a scale error. The 2019 ~3x row
  step-up is the documented NIBRS reporting-coverage effect.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `require_columns` guards 8 load-bearing bronze columns; all-string read prevents inference loss |
| Era routing | PASS | Single signature-detected era; no year-range routing |
| Filter logic logged + justified | PASS | Only filter `state_abbr=='GA'`, recorded per-year as `non_georgia_state_row` (263,851) |
| Normalization map completeness | PASS | Pinned 35-value national vocab; unknown labels hard-fail (`replace_strict` + explicit guard) |
| `strict=False` casts | PASS | `total_individual_victims` (literal-NULL, 15 rows, propagated) + `total_offender_count` (post-cast null hard-fails — documented never-null) |
| Dedup keys + tie-break | PASS | Collision guard before a structurally no-op dedup (unique incident_id asserted) |
| Year extraction | PASS | `data_year` column; `incident_date` year equality asserted on all rows |
| §5b masks | PASS | No masks; extreme value documented, not masked |

## Notes

- schema_hash `e296e679430a7aa5e2d66cead62d4c863e487bdecd4316a0acef08ed693c1a5a`;
  validation 19 pass / 0 fail / 1 warning (explained); manifest fresh; read_loss 0.
- **Step 2e (Asian/PI): N/A** — gold has no `demographic` column; offender race is
  deliberately excluded. The bias vocabulary keeps `anti_asian` and
  `anti_native_hawaiian_or_other_pacific_islander` separate, exactly as bronze does
  (post-1997 OMB buckets, structure doc §Asian/Pacific Islander) — no conflation
  surface. **Step 2f: N/A** — no rollup/split demographic keys; `bias_category` is
  mutually exclusive by construction (functional dependency, authored check).
- **2c note:** `bias_category` contract enum (7 values incl. `unknown`) is a
  deliberate superset of `gold_values_produced` (6) — `unknown` has no GA incidents
  yet; documented as refresh headroom. `bias_motivation` intentionally carries no
  contract enum, so new national values don't force a contract bump (the transform
  hard-fails on unmapped labels instead).
- Multi-bias explode convention (incident counted once per bias; NOT additive
  across bias motivations) is consistently documented across the contract
  description, usage, limitations, and both affected metric descriptions.
- v1 parity: **no v1 baseline (post-v1 topic)**.
