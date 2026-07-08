# Data Review: placements

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Gold faithfully reproduces the bronze placement-level file. An independent
full recompute of the placement-tuple pipeline (clean → sentinel-NULL →
year-window-drop → tuple-reduce → aggregate) matched **all 48 state-level cells
(16 years × 3 metrics) exactly** (every `d_new/d_plc/d_yth` delta = 0), a county
trace matched to the unit, the DERIVED state rollup reconciles to
`Σcounty + OUT OF STATE` in every tested year, and all categorical mappings
(8 demographic, 2 facility, 160 county incl. OUT OF STATE) are 0-unmapped and
semantically correct. Validation is clean (**20 pass / 0 fail / 0 warning**,
fresh). The prior review's one LOW fix (contract said "10 placements" for the
unknown-admission cells; it is 10 bronze rows = 5 placement tuples) has been
**applied** — the current contract and docstring read "5 placements (from 10
bronze rows...)", which I re-verified against bronze. No Required Fixes remain.
**v1 parity: no v1 baseline (topic is post-v1)** — `docs/rebuild/v1-baseline.yaml`
has no `criminal_justice/*` entry. One judgment item persists — the transform's
own flagged ~5% gap between gold's `num_new_placements` and the structure doc's
illustrative official-measure figures — with a no-data-change recommendation.

## Manifest Verification

| Column | Map entries | Bronze seen | Unmapped | Status |
|--------|------------|-------------|----------|--------|
| `demographic` | 8 | 8 (AmInd, Asian, Black, FEMALE, Hispanic, MALE, Other, White) | 0 | PASS |
| `facility_type` | 2 | 2 (RYDC, YDC) | 0 | PASS |
| `county_fips` | 160 | 160 (159 GA counties + OUT OF STATE) | 0 | PASS |

**Demographic map (every entry reviewed against `src/utils/demographics.py`):**

| Bronze | Gold | Correct? |
|--------|------|----------|
| `MALE` | `male` | Yes |
| `FEMALE` | `female` | Yes |
| `White` | `white` | Yes |
| `Black` | `black` | Yes |
| `Hispanic` | `hispanic` | Yes — source codes Hispanic as a mutually exclusive race-level bucket (Race Code 7); `DEMOGRAPHIC_CATEGORIES['hispanic'] = 'race'` |
| `AmInd` | `native_american` | Yes — `DEMOGRAPHIC_ALIASES['AMIND'] = 'native_american'` (American Indian, Race Code 3) |
| `Asian` | `asian` | Yes — decided judgment, see §2e |
| `Other` | `other` | Yes — explicit source catch-all (Race Code 6) |

**Facility map:** `RYDC` → `rydc`, `YDC` → `ydc` — correct, after stripping the
source's 10-char right-padding. The `all` value is a transform-synthesized
rollup, so its absence from the manifest's row-grain `gold_values_produced` is
expected; contract `enum` = {all, rydc, ydc} equals gold's actual distinct
values.

**County map:** all 159 uppercase GA county names resolved via `add_county_fips`
against the global counties dimension (FK check: "county_fips -> counties: all
159 keys resolve"). Spot-verified `FULTON → 13121`, `DEKALB → 13089`,
`MUSCOGEE → 13215`, `MACON → 13193`. **MACON → 13193 (Macon County) confirmed
deliberate**: the source's 160-name residence list is exactly the 159 GA
counties + OUT OF STATE, so MACON can only be Macon County (else Macon-County
youths would have no label); the transform docstring and `crosswalks.py` note
the global crosswalk deliberately carries no `macon → bibb` override.
`OUT OF STATE` maps to the explicit marker `state_rollup_only_no_county_fips`
(deliberate handling — county-excluded, state-kept — not a real recode).

**§2e Asian/Pacific Islander (Risk 1):** grep for `pacific islander|native
hawaiian|nhpi` in the structure doc returns only meta-commentary ("**no
separate Pacific Islander bucket**", "no combined Asian/Pacific Islander
label") — there is **no NHPI data label anywhere in the source**. Math test
executed on the latest state row: `state 2025 facility=all: num_placements
all=6081 race_sum=6081 ratio=1.0000`. The ratio is 1.0000 **by construction** —
this is individual-level data with exactly one mutually-exclusive race bucket
per row plus an explicit `Other` catch-all, so the 6 buckets are exhaustive and
the math test cannot discriminate conflation from an exhaustive partition; the
education-domain "bare Asian = pre-1997 combined bucket" structural argument does
not transfer to a 2010–2025 microdata source. **Verdict: PASS — keep `asian`**,
matching the reviewed `decision_points` sibling (same source, same 6-bucket
scheme): (a) explicit `Other` catch-all where unlisted races land, (b) unused
Race Code 5 suggests a reserved separate bucket, not a combined one, (c) modern
data, (d) tiny affected share (835 Asian rows = 0.19%). Remapping to
`asian_pacific_islander` would positively assert PI inclusion the source does
not support; the contract documents the caveat verbatim.

**§2f mutual exclusivity (Risk 6):** PASS — single convention. Gold
demographics = {all, asian, black, female, hispanic, male, native_american,
other, white}; `has asian_pacific_islander? False | has pacific_islander?
False | has asian? True` — no rollup key coexists with split keys. The three
overlapping axes (all / race / gender) packed into one column are the
documented project convention; the partition quality checks (below) prove
within-axis exclusivity numerically.

**Row-count reconciliation:** All 16 years (2010–2025) present, matching the
structure doc. `total_bronze` 433,844 = structure-doc row count; `total_gold`
32,656 = **actual parquet rows (verified: 32,656; state rows 406, county rows
32,250)**. `filtered_explicit` = 16 year-window-violation rows + 3,934 OUT OF
STATE **placement tuples** (bronze OOS residence rows are 10,660 — the manifest
records the exclusion at placement grain, the grain actually excluded). The
remaining "filtered" is aggregation compression (offense-level rows →
county/year/demo/facility cells); expansion factors drift smoothly 0.058→0.093
as bronze volume falls against a bounded cell count — consistent, no outliers.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| Year | year | MAPPED |
| County of Residence | county_fips | MAPPED (name→FIPS; OUT OF STATE → state rollup only) |
| Race Value / Gender | demographic | MAPPED (two axes + synthesized `all`) |
| Site Type | facility_type | MAPPED (padding-stripped; + synthesized `all` rollup) |
| newjuvenileid | — (consumed) | CORRECTLY EXCLUDED — PII; drives `num_youth`/`num_placements` only |
| Admitted Date / Date Terminated | — (consumed) | CORRECTLY EXCLUDED — drive `is_new` flag + year-window guard |
| Site Name | — (consumed) | CORRECTLY EXCLUDED — placement-identity key component; below county grain |
| Arrest County / Facility County / Offense County | — | CORRECTLY EXCLUDED — alternate geography concepts (doc ETL #9) |
| Offense Date / Offense Description / Other offenses | — | CORRECTLY EXCLUDED — needs curated category map (ETL #14); `Other offenses` derivable (ETL #12) |
| Placement Count | — | CORRECTLY EXCLUDED — unreliable (ETL #6) |
| Gender Code / Race Code | — | CORRECTLY EXCLUDED — 1:1 redundant, re-proven at runtime by `_assert_code_label_bijection` |
| DBL Placements / Duplicate Offense Record | — | CORRECTLY EXCLUDED — dedup bookkeeping, broken for 2014 (ETL #5); counts derived from tuples instead |

Derived gold metrics (`num_new_placements`, `num_placements`, `num_youth`) all
trace to bronze via the documented tuple recipe — no fabricated columns.

**Contract prose fidelity:** audited served text (`purpose` / `usage` /
`limitations` / `null_semantics` + per-column descriptions) against
`bronze-data-structure.md` for contradictions — **none found**. Year range
2010–2025 ✓; suppression "source publishes no suppression" ✓ (bronze:
"None"); RYDC ~96% ✓ (418,168/433,844 = 96.4%); OUT OF STATE ~2.5% ✓
(10,660/433,844 = 2.46%); demographic convention (hispanic as race bucket, no
PI bucket, asian→asian) ✓; "214 placements (~0.15%)" mixed-type ✓ (verified
below). The doc's suggested key-metric candidate was `placement_count`; the
transform instead sets `num_new_placements` as `key_metric` — a defensible
choice (it aligns with the Clearinghouse's official "new instances" headline
measure), not a contradiction.

## Value-Level Spot Checks

Independent recompute (separate implementation) against gold — bronze values
quoted before each verdict:

| Trace | Bronze (recomputed) | Gold | Verdict |
|-------|--------------------|------|---------|
| **State all/all, ALL 16 years × 3 metrics** | e.g. 2010: new=10,512, plc=16,296, youth=11,900; 2025: 3,752/6,081/4,854 | identical (all deltas 0) | **MATCH (48/48 cells)** |
| **Raw doc reproduction (pre-drop)** | distinct `(jid, Admitted-Date, Site)` per Year: 2010: 16,299; 2014: 10,343; 2025: 6,081 — distinct youth 2010: 11,901; 2025: 4,854 | matches structure-doc table exactly | MATCH |
| County trace: FULTON 13121, 2025, all/all | 485 distinct placement tuples, 376 distinct youth; new (adm-year==2025) = 378 | new=378, plc=485, youth=376 | MATCH |
| **§4b sentinel/null-admission**: 7 bronze rows `Admitted Date=01-01-1900` (`Year=2017/2018`) + 3 NULL-admission rows = 10 rows → 5 placement tuples | 7 sentinel + 3 null = 10 rows → **5 tuples** | counted in `num_placements`, excluded from `num_new_placements` | MATCH (contract: "5 placements from 10 bronze rows") |
| **Mixed-site modal resolution** | 214 of 147,474 placement tuples span both site types = **0.145%** (only at MACON/AUGUSTA/EASTMAN dual-type campuses) | 214, ties → rydc | MATCH (contract: "214 (~0.15%)") |

- **4a extreme-row traces**: global max `num_placements` = 16,296 (state 2010
  all/all) traces to 16,299 raw tuples minus 3 year-window drops in 2010;
  global max `num_youth` 11,900 = 11,901 raw minus 1 youth whose only 2010
  appearance was a dropped year-window row. Both explained by the sanctioned
  drop (structure doc ETL #7). Min cells (`num_placements = 1`) are enforced
  non-zero by the `cells_exist_only_where_activity` quality check (passing).
- **4c sentinel year-attribution (Risk 3)**: N/A for embedded-string years —
  `year` comes from the `Year` column, `is_new` from the parsed admission
  date. Verified via FULTON 2025 (new=378 from adm-year==2025) and the
  multi-year-stay semantics (a stay active in N years appears once per year;
  `is_new` true only in its admission year).
- **4d aggregate reconciliation (Risk 4)**: state rows are DERIVED —
  `state − Σcounty` for `num_placements` all/all equals OUT OF STATE tuples in
  every tested year (2010: 16,296 − 15,780 = 516 = OOS; 2025: 6,081 − 5,982 =
  99 = OOS). Race/gender/facility partitions of `num_placements` and the
  facility partition of `num_new_placements` are contract quality checks (all
  passing). No `.mean()` on percentages (all metrics are counts).
- **4e dedup tie-break (Risk 5)**: N/A — single cumulative file, one era; every
  cell produced by one `group_by`; the collision guard runs before the
  safety-net `deduplicate_by_levels`.
- **4f suppression semantics**: N/A — source publishes no suppression markers
  (`suppressed_to_null: false`); zeros in `num_new_placements` are real
  (carried-over-only cells).

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 0 warning** (timestamp
  2026-07-02T21:01:21Z, fresh vs manifest `generated_at` 21:01:21Z).
  `contract_parquet_schema` (32 files), `contract_quality_sql` (all 14 checks),
  `grain_uniqueness` (`['year','county_fips','demographic','facility_type']`),
  `foreign_keys` (159 county + 9 demographic keys resolve), both
  `geography_nulling` checks — all pass.
- `schema_hash`: `3985a0e412e2f7b7d5c9af19d788d53c64299b731999313555f5d3eb4a0d56bc`;
  contract `version: 1.0.0`.
- **§4b masking audit**: one mask — `admitted_date`, count 7, years [2017, 2018],
  with reason — verified against bronze (exactly 7 rows carry `01-01-1900`).
  Handling is documented in the `num_new_placements` contract description; the
  metric is `unit: count` with an auto non-negative check, so the mask stays
  enforceable. The 16 year-window rows are drops recorded via `record_filtered`
  (recomputed per year: 2010: 3, 2011: 7, 2013: 1, 2015: 3, 2016: 2 = 16), which
  exactly explain the structure-doc pre-drop tuple counts (e.g. 2010: 16,299 →
  gold 16,296). No unrecorded or undocumented mask.
- **§15b coverage judgment**: strong — 8 authored cross-column checks
  (new ⊆ placements, youth ⊆ placements, ≥1 completeness, facility partition ×2
  metrics, race partition, gender partition, county ≤ state) plus auto
  range/enum checks. `num_youth` is correctly NOT partition-checked (it is
  non-additive by design). No missing obvious invariant.
- **v1 parity**: **no v1 baseline (topic is post-v1)**. Script output verbatim:
  `DIFFERS from v1 / v1: None / now:
  8303f6b87eee29931b395d6ed2a4baf48e1f0cb33fe7ad746033add0d77b61da`;
  `any criminal_justice keys in v1 baseline?: False`. Per the review brief this
  is not a divergence — the baseline has no `criminal_justice/*` entries.

## Cross-Era Consistency

Single era (one cumulative file, one schema) — no overlap years, no era
boundaries. Cross-year NULL sweep: **clean** — no metric column ≥95% NULL in any
year; all three metrics 0% NULL in every year (manifest `null_pct: 0.0`
throughout). Year-over-year continuity: max adjacent-year ratio of state all/all
metrics = 1.72 (`num_new_placements`), 1.63 (`num_placements`), 1.46
(`num_youth`) — no >10x jumps, no cumulative-publication (~2x-then-revert)
signature. The 2019→2020 dip is the documented COVID trough.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|------|----------|-------------------|
| Silent column drops | — | PASS — `_require_columns` guards all 11 used columns; deliberate exclusions documented |
| Era routing | — | PASS — single-era signature; unmatched schema hard-fails |
| Filter logic logged + justified | — | PASS — year-window drops (16) and OOS exclusions (3,934 tuples) both `record_filtered` with reasons |
| Normalization map completeness | — | PASS — all maps 0-unmapped vs structure doc; an unmapped label blocks the run |
| `strict=False` casts | — | PASS — date parses use `strict=False` but a new-NULL guard raises if the parse introduces any NULL; `Year` cast is `strict=True` |
| Dedup keys + tie-break | — | PASS — collision guard before `deduplicate_by_levels` safety net; duplicates impossible by construction |
| Year extraction | — | PASS — from the `Year` column; filename upload-month correctly ignored |
| §4b mask recording | — | PASS — manifest mask (7) + filter reasons (16 + 3,934) all recorded; contract prose now accurate |

## NEEDS_JUDGMENT

### Judgment Call 1: `num_new_placements` sits ~1–5% above the structure doc's illustrative official-measure figures
- **Severity if confirmed**: LOW
- **Suspicion**: The transform docstring itself flags this for data review. Gold
  `num_new_placements` (2010: 10,512; 2025: 3,752) exceeds the structure doc
  ETL #7's illustrative new-admission figures (2010: 9,955; 2025: 3,706) by
  ~5.3% (2010) / ~1.2% (2025). If the doc's figures reflect the Clearinghouse's
  published headline, gold overstates it.
- **Evidence available**: My independent recompute of the transform's recipe —
  distinct `(year, jid, admitted_date, site)` tuples with `admitted_year ==
  Year` — reproduces gold's 10,512 / 3,752 **exactly** (all 16-year deltas = 0),
  confirming the recipe is faithfully implemented. The structure doc labels its
  9,955 / 3,706 figures "illustrative" and states no reproducible recipe, and
  they do not match any tuple recipe. The gap's documented cause — the official
  measure excludes same-type-facility transfers, which appear as new tuples and
  are not detectable in the source — is already stated in both the contract
  `limitations` and the `num_new_placements` description.
- **Why uncertain**: The doc's figures may be the doc author's own computation
  under an unstated key rather than the Clearinghouse's published numbers; the
  live dashboard cannot be checked headlessly here. Meanwhile the transform's
  recipe is internally the strongest choice — it uses the identical placement
  identity for both measures, preserving `new ⊆ placements` and the exact
  facility/race/gender partitions (all verified passing).
- **Location**: `_reduce_to_placements()` (`is_new` flag) in `transform.py`;
  structure doc ETL #7.
- **If confirmed, suggested fix**: **None to the data — keep the tuple recipe.**
  The current contract caveat ("slightly OVERSTATES the official measure") is
  accurate and adequate. If the official dashboard figures are ever compared and
  the gap exceeds "slight", strengthen the caveat with the measured delta
  (e.g. "~1–5% above the official measure") and record the doc figures'
  provenance in `bronze-data-structure.md`.

## Notes

- `schema_hash`: `3985a0e412e2f7b7d5c9af19d788d53c64299b731999313555f5d3eb4a0d56bc`;
  validation 20 pass / 0 fail / 0 warning; `read_loss`: 0 events; 1 mask
  (`admitted_date`, 7 values, years 2017/2018); 2 filter reasons (16 year-window
  + 3,934 OOS tuples).
- **PII gate (explicit)**: gold parquet columns are exactly `year, county_fips,
  demographic, facility_type, num_new_placements, num_placements, num_youth` —
  `newjuvenileid`, dates, site names, and offense text never leave the transform;
  the youth ID is consumed by `n_unique`/flag-sums inside
  `_transform_placement_level`.
- **No small-cell suppression (decided convention)**: gold publishes cells down
  to `num_youth = 1`, following the `decision_points` sibling and the documented
  rationale that the source itself publishes the pseudonymized placement-level
  file publicly, making county/year aggregates strictly less disclosive than
  bronze. Noted for the approver; no change recommended.
- The manifest's OOS `filtered_explicit` (3,934) counts placement **tuples**;
  the structure doc's 10,660 counts bronze rows — both correct at their own grain.
- Prior review's Fix 1 (contract "10 placements" → "5 placements from 10 bronze
  rows") is **applied and verified**; no Required Fixes remain in this review.
