# Data Review: law_enforcement_employees

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

This is a re-review of the post-fix state: the four Required Fixes from the prior
review (2026-07-02) have all been applied — the transform now carries a pinned
`KNOWN_BAD_AGENCY_YEARS` screen with all **7 agency-years** (GDC-IA 1994/1995/1998,
GSP-Valdosta 1993/1994, Bowdon 2016, Cobb Park Rangers 2001), each recorded as an
explicit manifest filter event and documented in the contract `limitations`. An
independent full rebuild of all 26,994 gold rows from bronze — strings→Int64, the 7
known-bad dropped, ORI→primary-county via the manifest map, statewide ORIs to state
rows only, per-sex-slice sums + `pl.len()` — reconciles with **zero mismatches** on
every metric across all 66 state-years and all 8,932 county-years. Validation is 20/20
pass (13/13 contract quality checks); all 159 GA county FIPS + 3 demographics resolve as
FKs. **v1 parity: no baseline** — `docs/rebuild/v1-baseline.yaml` has no
`criminal_justice` entries, so this topic is post-v1 (not a drift signal). No Required
Fixes remain. One LOW judgment call carries forward from the prior review (statewide-
operating agencies attributed to their HQ county), and the prior review's residual-tail
judgment call is now resolved by the contract's added caveat.

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| county_fips (ORI→FIPS) | 817 | 817 | 0 | PASS (verified by full rebuild below) |
| demographic | 3 | 3 | 0 | PASS |

**demographic** (synthesized from the wide sex-split columns, normalized via `DEMOGRAPHIC_ALIASES`):

| Bronze → Gold | Correct? |
|---------------|----------|
| `All` → `all` | ✓ — aggregate lane (`officer_ct`/`civilian_ct`/`total_pe_ct`) |
| `Male` → `male` | ✓ — `male_officer_ct`/`male_cilvilian_ct`/`male_total_ct` |
| `Female` → `female` | ✓ — `female_officer_ct`/`female_cilvilian_ct`/`female_total_ct` |

`gold_values_produced` = `['all','female','male']` = contract `demographic` enum (2c PASS).

**county_fips**: 817 ORI entries — too many for entry-by-entry prose, so verified
*executably* via a full independent aggregation rebuild. Applying the manifest's own
ORI→FIPS map to bronze GA agency-years (after dropping the 7 pins) produced **0 unmatched
ORIs** and reconciled every county-year and state-year exactly (see Value-Level Spot
Checks). `gold_values_produced` is the 159 GA county FIPS (`13001`…`13321`), all of which
resolve in the counties dimension. The `unassigned_statewide` sentinel is applied to the
12 no-county ORIs (GBI HQ/field offices, GSP HQ, Ports Authority admin) and routes them
to state rows only.

### Row-count reconciliation

- Manifest `total_gold` 26,994 = actual parquet rows **26,994** (3b PASS); 66 years
  unbroken (1960–2025), matching the structure doc.
- Bronze 26,180 GA agency-years (26,180 of 785,127 national — a scope filter, logged, not
  recorded as a quality filter); `total_filtered_explicit` = **7** (the known-bad pins),
  matching `filtered_explicit_by_reason`.
- Per-year `filtered` values (e.g. 1998: 258) are the tracker's derived `bronze − gold`
  bookkeeping (gold rows are 3 × (counties + state) per year), not real drops — the real
  drops are the 7 explicit ones. Expansion factors (2.6 → 0.65) track agency density.
- Strongest single reconciliation: **state `agencies_reporting` = bronze GA agency-years −
  known-bad drops**, verified for every year (1998 state=737 = 738 − 1; 1994 state=636 =
  638 − 2 [GDC-IA + GSP-Valdosta]; 1993 state=646 = 647 − 1; 1960 state=76 = 76 − 0).
- `read_loss`: 0 events (`masked_values`/`read_loss`/`reclassified` sections absent = zero,
  per skill convention).

### Asian/Pacific Islander conflation (Risk 1) — N/A

`demographic` is sex only (`all`/`female`/`male`); no race buckets exist anywhere in
bronze (structure doc: "Demographic race buckets: n/a — the only demographic split is
male/female"). No `asian` key, no `pct_asian` column.

### Mutual exclusivity (Risk 6) — PASS

Single convention: `male`/`female` are mutually exclusive and partition `all` exactly
(contract quality check `sex_partition_sums_to_all` passes; also proven by the rebuild and
the Dade 2020 trace below). No rollup-plus-split coexistence.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| data_year | year | MAPPED |
| ori | county_fips (via crosswalk) + agencies_reporting | MAPPED (aggregation key; agency grain intentionally rolled up to county — ORI deferred to a future agencies dimension, per the county-grain domain standard) |
| male_officer_ct / female_officer_ct / officer_ct | officer_count × demographic rows | MAPPED (tidy §5a) |
| male_cilvilian_ct / female_cilvilian_ct / civilian_ct | civilian_count × demographic rows | MAPPED (source typo `cilvilian` corrected via era rename — verified below) |
| male_total_ct / female_total_ct / total_pe_ct | total_employee_count × demographic rows | MAPPED |
| pub_agency_name / pub_agency_unit / agency_type_name / population_group_desc | — | CORRECTLY EXCLUDED (agency-dimension attributes; not county-grain facts) |
| county_name | — | CORRECTLY EXCLUDED (superseded by the crosswalk; comma-joined multi-county + `NOT SPECIFIED` make it a secondary signal only) |
| state_abbr / division_name / region_name | — | CORRECTLY EXCLUDED (constant after GA filter) |
| population | — | EXCLUDED (documented judgment) — overlapping agency jurisdictions make county sums meaningless as a denominator; the structure doc itself endorsed dropping it. Documented in contract `usage`/`limitations`. |
| pe_ct_per_1000 | — | EXCLUDED (derived from `population`; same rationale; verified derivable in the structure doc) |

All gold columns trace to bronze — `agencies_reporting` is `pl.len()` per aggregation cell
(verified in the rebuild), not fabricated. No fabrication.

## Value-Level Spot Checks

**Extreme rows first (4a)** — all quoted against bronze:

- **officer_count global max** — gold `2018 / state / all = 27,244`. Bronze `SUM(officer_ct)`
  over all GA 2018 agency-years = **27,244**. MATCH.
- **total_employee_count global max** — gold `2025 / state / all = 37,623`;
  **civilian_count max** `2024 / state / all = 11,748`; **agencies_reporting max**
  `1998 / state / all = 737` (= 738 bronze − 1 GDC-IA). All state rollups, all reconcile.
- **Largest surviving single-agency filing** — Atlanta PD (GAAPD0000, Fulton) `1,855`
  officers (2013), `1,817` (2025), `1,800` (2014) — plausible for the state's largest
  agency; confirms the prior review's four inflation sources are gone (the ex-maxima
  GDC-IA 9,334 and GSP-Valdosta 844 no longer appear).
- **officer_count global min** — gold `1960 / 13001 (Appling) / female = 0`. Bronze source
  is Baxley PD (`GA0010100`, county_name `APPLING`, 1960): `officer_ct 6`, and the female
  slice `female_officer_ct 0` → female `officer_count = 0`. MATCH (a real zero, not a mask).

**Ordinary trace, single-agency county-year (4b)** — Dade County (13083), 2020, sole
reporting agency Dade PD (`GA0410000`): bronze `male_officer_ct 20`, `female_officer_ct 6`,
`male_cilvilian_ct 1`, `female_cilvilian_ct 2`, `officer_ct 26`, `civilian_ct 3`,
`total_pe_ct 29`. Gold: `all 26/3/29`, `male 20/1/21`, `female 6/2/8`, `agencies_reporting 1`.
Checks: male+female officers 20+6=26=all ✓; male+female civilians 1+2=3=all ✓
(**this confirms the `cilvilian`→`civilian` typo rename mapped the right columns**);
totals 21+8=29=all ✓. MATCH exactly.

**Full-coverage rebuild (subsumes 4a/4b for all eras + both detail levels)** — every gold
row re-derived independently from bronze: **0 of 26,994 rows mismatch** on officer_count,
civilian_count, or agencies_reporting; state-year officer/civilian/count all match too.

- **4c Sentinel year-attribution** — N/A. `data_year` is authoritative; the only year
  literals in transform.py are the `KNOWN_BAD_AGENCY_YEARS` pins (compared against the
  authoritative `year` column), not parsed from strings.
- **4d Aggregate reconciliation** — aggregates are transform-DERIVED; the full rebuild
  reconciles 100% of county and state rows. No `.mean()` on any percentage (no percentage
  columns exist). Contract `state_total_covers_county_sum` / `state_agencies_reporting_
  covers_county_sum` enforce state ≥ county-sum (statewide agencies aren't gold rows, so
  the exact state = county + statewide identity is verified here instead).
- **4e Dedup tie-break** — N/A. Single file, single era, bronze `ori × data_year` unique
  (transform hard-guards this; 0 duplicates); `deduplicate_by_levels` is a documented
  no-op safety net and the collision guard runs first.
- **4f Suppression** — N/A. Source has no suppression (`suppressed_to_null=False`); the two
  literal-`NULL` columns (`pub_agency_unit`, `pe_ct_per_1000`) are excluded from gold and
  read via `null_values={"NULL"}`.
- **Zero-employee rows** — bronze has **238** `total_pe_ct == 0` agency-years (matches the
  structure doc); preserved as reported (extreme-but-conceivable §4b) and still counted in
  `agencies_reporting`.

## Validation Cross-Read

- `_validation.json`: **passed, 20 pass / 0 fail / 0 warning** — `contract_parquet_schema`
  (132 files), `contract_quality_sql` (13/13), `grain_uniqueness` (`year, county_fips,
  demographic`), `foreign_keys` (159 county FIPS + 3 demographics all resolve), geography
  nulling for counties and states.
- `schema_hash`: `85ba94219990141b9b8433a2c7ebd217207bc964f6c786c1e6171783e5e6d868`.
- **§4b masking audit**: no `_null_*` cell-masking helpers exist (the known-bad handling is
  a pre-aggregation **row drop**, not a cell mask, which is the correct choice — an entire
  misfiled agency-year is dropped, its counts never enter any sum). The 7 drops are recorded
  on the manifest (`filtered_explicit_by_reason`, counts verified) and documented in the
  contract `limitations` with correct per-county attributions (see Cross-Era). Consistent
  and enforceable. PASS.
- **§15b coverage judgment**: the 7 authored quality checks (component sum, sex partition,
  3-rows-per-cell, state ≥ county-sum for both officer and roster counts, roster constancy
  across sex slices, roster ≥ 1) cover the real cross-column invariants well. Minor,
  non-blocking observation: `state_total_covers_county_sum` checks only `officer_count`, not
  civilian/total — but the row-level `officer_plus_civilian_equals_total` check ties the
  other metrics to officer within each row, so the invariant is transitively covered; not a
  gap worth a fix. No gold-side SQL can catch source misfilings — that screening correctly
  lives in the transform (`KNOWN_BAD_AGENCY_YEARS`).
- **v1 parity** (verbatim): `DIFFERS from v1` with `v1: None` — i.e. **no baseline entry
  exists** (`criminal_justice` keys in `v1-baseline.yaml`: none). Topic is post-v1; parity
  is N/A, not a drift signal. Current gold sha256:
  `4f9a1f525c07f5dea36c643f0017a252c9b16a14e1d62e64983c42dbf560e539`.

## Cross-Era Consistency

- Single era (`lee_v1_cilvilian_typo_header`) — the second signature
  (`lee_v2_corrected_header`) is a defensive forward-guard for a future typo-fixed release;
  no overlap years. The typo columns (`male_cilvilian_ct`/`female_cilvilian_ct`) are mapped,
  not silently NULLed — `civilian_count` is populated in all 66 years.
- Cross-year NULL sweep (3c / Risk 2): **clean** — no metric column is ~100% NULL in any
  year; all 4 metrics non-null by construction every year. No era-localized rename bug.
- YoY continuity (3d): **no >2x adjacent jumps** in state `all` officer_count. 1970→1971
  (2,962 → 4,219 officers) coincides with the reporting roster jumping 59 → 280 agencies —
  genuine coverage growth, correctly interpretable via `agencies_reporting`; not a scale or
  cumulative-publication artifact. The 1994/95/98 GDC and 1993/94 GSP spikes that the prior
  review flagged are **gone** (dropped by the pins), so the state series is now smooth
  through the 1990s.
- Contract-prose fidelity (Step 6): the contract's known-bad county attributions verified
  against the counties dimension — GDC-IA `GA0603200`→`13121` **Fulton** ✓, GSP-Valdosta
  `GAGSP3100`→`13185` **Lowndes** ✓, Bowdon `GA0220300`→`13045` **Carroll** ✓, Cobb Park
  Rangers `GA0331400`→`13067` **Cobb** ✓. Year range (1960–2025), no-suppression scheme,
  coverage figures (44–76 vs ~350–530), and sex-only demographic convention all agree with
  bronze-data-structure.md. No contradictions.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | explicit `expected`/`missing` guard raises on any absent count column |
| Era routing | PASS | signature-based; typo header is its own era; unmatched signature raises |
| Filter logic | PASS | GA scope filter logged (26,180 of 785,127); zero-GA guard; the only real drops are the 7 documented known-bad |
| Normalization map completeness | PASS | all 9 count columns renamed per era; matches structure doc |
| `strict=False` casts | PASS | all casts strict (`cast(pl.Int64)`) — a source change fails loudly, not silently NULLs |
| Dedup keys + tie-break | PASS | `assert_no_natural_key_collisions` first; dedup is a documented no-op safety net; bronze grain hard-checked unique |
| Year extraction | PASS | `data_year` authoritative; per-year `record_bronze` inside the single file |
| Known-bad screen | PASS | 7 provable misfilings pinned + dropped pre-aggregation; stale-pin logs a warning; no un-pinned provable duplicate remains (0 same-year exact-duplicate filings >200 officers) |

## NEEDS_JUDGMENT

### Judgment Call 1: Statewide-operating agencies attributed to their HQ county
- **Severity if confirmed**: LOW
- **Suspicion**: agencies that operate statewide/regionally but have a primary county in
  the crosswalk are attributed to that county every year, unlike the 12 no-county ORIs
  (GBI/GSP-HQ/Ports) that route to state rows only. Examples (all mapped to Fulton 13121):
  Georgia Department of Transportation police (`GA0602000`, ~262–280 officers 1991–95),
  several Department of Natural Resources offices (`GA0602800` ~253, `GA0690700` ~252 →
  Hall, `GA1020500` ~231 → Upson), and MARTA transit police (`GA0602100`, 244 in 2024).
  A consumer reading a "Fulton County law-enforcement employees" figure gets these
  statewide/transit forces folded in.
- **Evidence available**: 2024 Fulton `officer_count = 4,036`, of which ~272 (~6.7%) are
  state/transit agencies (MARTA 244 dominant; DOT only 4 that year). The effect was larger
  historically — DOT alone contributed ~280 to Fulton in 1991. The contract `limitations`
  names only GBI/State Patrol/Ports as statewide-to-state-only, so DOT/DNR/MARTA/Revenue
  are not disclosed as folded into their HQ county.
- **Why uncertain**: this is a **deliberate, documented primary-county attribution policy**
  (the contract states employees go to the reporting agency's primary county), the values
  are real and stable (not errors), and the largest single component (MARTA) is arguably
  correctly attributed to metro Atlanta. Reclassifying DOT/DNR-style ORIs to
  `unassigned_statewide` is a shared-crosswalk design decision affecting sibling FBI-CDE
  topics, not a defect in this transform. Recent-year magnitude is modest.
- **Location**: `src/etl/crosswalks/build_ori_to_county.py` (crosswalk policy) and/or the
  contract `limitations` — not `transform.py`.
- **If confirmed, suggested fix**: either reclassify genuinely statewide-operating ORIs
  (DOT police, DNR HQ-style offices) to `unassigned_statewide` in the crosswalk and rebuild
  (affects siblings — coordinate), or add one sentence to the contract `limitations` naming
  DOT/DNR/transit police as county-attributed so the disclosure is explicit. Given the low
  magnitude and the documented policy, the contract-disclosure route is the lighter,
  recommended option.

## Notes

- The prior review's four Required Fixes are all applied: `KNOWN_BAD_AGENCY_YEARS` pins 7
  agency-years, verified present in the manifest (`total_filtered_explicit: 7`) and the
  contract `limitations`; the independent rebuild confirms the drops landed with no
  collateral effect (0/26,994 mismatch).
- The prior review's residual-tail judgment call (Statesboro, Clayton Narcotics, DNR
  outliers with no internal smoking gun) is now **resolved by the contract caveat**
  "Occasional implausible single-agency filings may survive in this voluntary as-reported
  source." A fresh scan found no un-pinned filing with a provable signature (no same-year
  exact-duplicate >200 officers; the residual outliers all lack an internal contradiction),
  so no Required Fix.
- `schema_hash`: `85ba94219990141b9b8433a2c7ebd217207bc964f6c786c1e6171783e5e6d868`;
  validation 20 pass / 0 fail / 0 warning; contract quality SQL 13/13.
- Current gold sha256: `4f9a1f525c07f5dea36c643f0017a252c9b16a14e1d62e64983c42dbf560e539`
  (topic not yet approved — no drift baseline to compare against).
- All metrics are `unit: count`; non-negativity checks auto-derived; no percentage/
  proportion columns, so scale checks are trivially N/A.
