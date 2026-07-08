# Data Review: decision_points

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Gold faithfully reproduces the bronze youth-level file: an independent re-aggregation
matched gold **exactly** at the state level for all 11 metrics × 16 years, and at the
county level for every year and demographic slice of three spot-check counties
(Fulton, Chatham, Echols). The synthesized state rollup reconciles to the county sums
plus the OUT OF STATE contribution to the unit, every categorical mapping is
semantically correct, and all contract prose figures (2025 multi-race/gender youths,
funnel invariants, secure-placement collapse) verify. **No Required Fixes** — the prior
review's LOW contract-caveat fix has been applied (the `demographic` description now
correctly scopes the race/gender inconsistency to 2025). One LOW NEEDS_JUDGMENT: the
`num_youth` served description asserts "county rows sum above the state row," which is
true in 15 of 16 years but reverses in 2025 (county sum 12,287 < state 12,361) because
out-of-state youths outweigh the multi-county double-count. **v1 parity: no baseline**
(`docs/rebuild/v1-baseline.yaml` has zero `criminal_justice` entries — post-v1 topic).

## Manifest Verification

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| `demographic` | 8 | 8 (AmInd, Asian, Black, FEMALE, Hispanic, MALE, Other, White) | 0 | PASS |
| `county_fips` | 160 | 160 (159 GA counties + OUT OF STATE) | 0 | PASS |

**Demographic map — every entry reviewed:**

| Bronze | Gold | Correct? |
|--------|------|----------|
| `AmInd` | `native_american` | Yes — shared alias `AMIND → native_american` (`src/utils/demographics.py:110`); canonical for American Indian/Alaska Native |
| `Asian` | `asian` | Yes, as a judgment call — see §2e (kept as published) |
| `Black` | `black` | Yes |
| `Hispanic` | `hispanic` | Yes — source treats Hispanic as a mutually exclusive race bucket ("All races except Hispanic are populations not considered Hispanic"), so the 6 race values partition |
| `Other` | `other` | Yes — explicit source catch-all (code 6) |
| `White` | `white` | Yes |
| `MALE` | `male` | Yes |
| `FEMALE` | `female` | Yes |

Bronze `Race Value`×`Race Code` confirmed: White=1, Black=2, AmInd=3, Asian=4, Other=6,
Hispanic=7 (code 5 never appears). Race/Gender codes are dropped as redundant.

**County map:** all 159 uppercase names resolve via `add_county_fips` against the global
counties dimension (FK check: "all 159 keys resolve"); `OUT OF STATE` is deliberately
mapped to the non-FIPS marker `state_rollup_only_no_county_fips` (excluded from county
rows, kept in the state rollup) — handled, not a real recode. Contract `enum` for
`demographic` (9 values incl. `all`) = `gold_values_produced` ∪ {`all`}; `all` is
transform-synthesized so its absence from the bronze-observed map is expected.

**§2e Asian/Pacific Islander (Risk 1):** `NO_NHPI_LABEL_IN_BRONZE` — no PI/NHPI label
anywhere in either bronze file (bronze doc ETL #5: "No Pacific Islander bucket exists in
either file"). Math test executed:
`num_offenses: year=2025 total=29008 race_sum=29008 ratio=1.0000`. The ratio is 1.0000
**by construction** — the source's 6 race buckets (with an explicit `Other` catch-all)
exhaustively partition the transform-synthesized `all` row — so the math test cannot
discriminate here, and the education-domain structural argument ("bare Asian = pre-1997
combined bucket") does not transfer. **Verdict: PASS — keep `asian`**: (a) the source
carries an explicit `Other` catch-all where unlisted races land, (b) the race-code scheme
1,2,3,4,6,7 leaves code 5 unused (a reserved separate bucket, not a combined one), (c) the
data is modern (2010+), (d) the affected population is 748 youth-rows (0.24%). Remapping to
`asian_pacific_islander` would falsely assert PI inclusion the source does not support and
would corrupt the dimension's combined-vs-split convention. The contract documents the
caveat verbatim.

**§2f mutual exclusivity (Risk 6):** PASS — single convention. Gold demographics =
{all, asian, black, female, hispanic, male, native_american, other, white}; no rollup key
(`asian_pacific_islander`/`pacific_islander`) coexists with its splits. The three
overlapping axes (all / race / gender) packed into one column are the documented project
convention; within each axis values are mutually exclusive per bronze row.

**Row-count reconciliation:**

| Year | Bronze | Gold | Filtered-explicit | Expansion |
|------|--------|------|-------------------|-----------|
| 2010 | 26,784 | 1,050 | 223 | 0.039 |
| 2015 | 21,826 | 1,034 | 314 | 0.047 |
| 2020 | 12,435 | 1,010 | 184 | 0.081 |
| 2025 | 12,990 | 973 | 120 | 0.075 |
| **Total** | **309,637** | **16,551** | **3,338** | — |

All 16 years 2010–2025 present (matches structure doc). Filtered-explicit = 38
byte-identical duplicates + 3,300 OUT OF STATE youth-years (both match the structure doc
exactly). The remaining "filtered" is aggregation compression (youth-level →
county/year/demographic cells); expansion factors 0.039–0.081 drift smoothly upward as
youth volume falls against a bounded cell count (~160 geos × 9 demos) — consistent, no
outliers. Actual parquet total = **16,551** = manifest `total_gold`; grain dup rows = 0.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| NEWJUVID | consumed → `num_youth`, secure-placement counts | CORRECTLY EXCLUDED (PII; never exported) |
| Period Year | `year` | MAPPED |
| County Name | `county_fips` | MAPPED |
| Court Type | summed over | CORRECTLY EXCLUDED (D/I/S undocumented at source; ETL #3 sanctions summing over) |
| Gender | `demographic` (gender axis) | MAPPED |
| Gender Code | — | CORRECTLY EXCLUDED (redundant with Gender) |
| Race Value | `demographic` (race axis) | MAPPED |
| Race Code | — | CORRECTLY EXCLUDED (redundant with Race Value) |
| Number of offenses | `num_offenses` | MAPPED |
| Diversions (all types) | `num_diversions` | MAPPED |
| Delinquent Adjudications (Misd. And Felony) | `num_delinquent_adjudications` | MAPPED |
| Unique Adjudication Date Count | `num_adjudication_dates` | MAPPED |
| Probation orders | `num_probation_orders` | MAPPED |
| Commitments orders | `num_commitment_orders` | MAPPED |
| Petitions | `num_petitions` | MAPPED |
| Superior Court Sentenced | `num_superior_court_sentences` | MAPPED |
| Secure Detention (RYDC) | `num_secure_detention_youth` | MAPPED (n_unique of flagged youths — stricter than the doc's sum-of-flags: a youth flagged in two court-type segments counts once) |
| Secure Confinement (YDC) | `num_secure_confinement_youth` | MAPPED (same) |
| (1)ACTIVE JUVENILE - (0)TERMINATED JUVENILE | — | CORRECTLY EXCLUDED (publication-time case status, not a fact about the data year; exclusion loses no event counts) |
| *Raw Data 2 (all 12 columns)* | — | CORRECTLY EXCLUDED (different universe/grain — 65 self-reporting counties, county/month case flow; ETL #1 forbids union; recorded on manifest as `raw_data_2_case_flow_EXCLUDED`, 92,656 rows; documented in contract limitations; candidate sibling topic) |

Gold names use the `num_*` prefix rather than the structure doc's suggested `*_count`
working names — canonical-vocabulary check passed, so this is a naming convention, not
drift. No gold column lacks a bronze ancestor (no fabrication).

**Contract prose fidelity:** audited the served `purpose`/`usage`/`limitations`/
`null_semantics` and every column `description` against `bronze-data-structure.md`. Year
range 2010–2025, suppression scheme (none; zeros real), no-percentage-scale, 6-bucket race
convention with mutually-exclusive Hispanic and no PI bucket, court-type/active-flag/Raw
Data 2 exclusions, and the 2023–2025 secure-placement incompleteness (62/81/72 flagged
rows) all **agree** with the bronze doc. One derived-prose imprecision found (not a bronze
contradiction) — see NEEDS_JUDGMENT.

## Value-Level Spot Checks

All traces recomputed independently from bronze Raw Data 1 with the transform's dedup
applied (309,637 raw → 309,599 after dropping the 38 byte-identical duplicates).

| Trace | Bronze-recompute evidence | Gold | Verdict |
|-------|---------------------------|------|---------|
| **State `all`, all 11 metrics × all 16 years** | full independent re-aggregation | identical | MATCH (0 mismatches) |
| Global max `num_offenses` (2012, state, all) | Σ `Number of offenses` over 2012 = **63,649** | 63,649 | MATCH |
| Global max `num_youth` (2010, state, all) | `n_unique(NEWJUVID)` 2010 = **25,843** | 25,843 | MATCH |
| Global max `num_secure_confinement_youth` (2018, state, all) | distinct NEWJUVID with YDC=1 in 2018 = **121** | 121 | MATCH |
| Global max `num_superior_court_sentences` (2013, state, all) | Σ = **1,106** | 1,106 | MATCH |
| **Fulton (13121), Chatham (13051), Echols (13101)** — every year × slice (all/race/gender), all 11 metrics | full re-aggregation (326 cell-metrics) | identical | MATCH (0 mismatches) |
| Global min cells (`num_youth`=1) | single-youth county cells (e.g. Echols small-county slices) | num_youth=1, num_offenses≥1 | MATCH |
| 2023 secure-confinement collapse | bronze 2023 YDC-flagged rows = **0** | all-zero YDC 2023 | MATCH — real source coverage collapse, documented |

**OUT OF STATE reconciliation** (state rows are DERIVED, include OOS; county rows exclude
it): `state_all num_offenses − Σ county_all num_offenses = OOS bronze offense sum`, exact
in every checked year — 2010: 58,967−58,424=543 (OOS=543); 2018: 49,084−48,554=530
(OOS=530); 2025: 29,008−28,883=125 (OOS=125).

**Funnel invariants (bronze row-wise):** rows with adjudications>offenses = **0**, rows
with petitions>offenses = **0**, rows with offenses<1 = **0**, negative event values = 0
— the contract's consistency checks rest on verified-clean bronze. RYDC/YDC are strictly
0/1, mutually exclusive (rows with both=1 → **0**; RYDC=1: 3,413, YDC=1: 857).

- **4c sentinel year-attribution**: N/A — `year` comes solely from the `Period Year`
  integer column; no year-bearing string literals are parsed (only docstring prose /
  contract example).
- **4d aggregate reconciliation** (DERIVED state rows): reconciled exactly (above); no
  `.mean()` on any percentage (all metrics are sums / distinct-counts). PASS.
- **4e dedup tie-break**: N/A — one bronze file, one `group_by` per cell; the collision
  guard runs before the safety-net `deduplicate_by_levels`.
- **4f suppression semantics**: N/A — no suppression markers (`suppressed_to_null: false`);
  zeros verified real.

## Validation Cross-Read

`_validation.json`: **20 pass / 0 fail / 0 warning** (2026-07-02T13:40:24Z, fresh vs
transform mtime). `contract_parquet_schema` (32 files), `contract_quality_sql` (19 checks),
`grain_uniqueness` (`['year','county_fips','demographic']`), and `foreign_keys`
(county_fips → counties: 159; demographic → demographics: 9) all pass.

- `schema_hash`: `09e4b9320e0df5a0e33d73774ae2acbab749fde198422379ed9071101a93d642`
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no
  `masked_values` / `read_loss` sections (zero events); docstring documents why no masks
  apply (all metrics are sums/distinct-counts over verified-clean bronze integers). PASS.
- **§15b coverage judgment**: quality list covers the real invariants — race & gender
  partition of `num_offenses` (both levels via the NULL-group trick; verified 0 mismatches
  across all years), funnel bounds (`adjudications ≤ offenses`, `petitions ≤ offenses`),
  `num_offenses ≥ num_youth`, secure-placement ⊆ youth, plus per-metric non-negativity.
  Partition checks are correctly authored on the event count `num_offenses` (partitions
  exactly) rather than `num_youth` (approximate in 2025). Adequate; no missing obvious
  invariant.
- **v1 parity**: `DIFFERS from v1 / v1: None / now: 4429cfec…` — `docs/rebuild/
  v1-baseline.yaml` has **zero `criminal_justice` entries**. This is **not** a divergence:
  the topic is new since v1 (no baseline hash exists), reported as "no v1 baseline
  (post-v1)" per the run instructions.

## Cross-Era Consistency

Single era feeds gold (Raw Data 1; Raw Data 2 deliberately excluded) — no overlap years or
era boundaries. Cross-year NULL sweep: **no flags** (metric columns fully non-null in all
16 years; `county_fips` NULL only on the 144 state rows = 16 yr × 9 demos). Adjacent-year
continuity: **no >10x jumps** on any state-level metric. The only near-zero transition is
`num_secure_confinement_youth` (2022→2025), tracing to the documented bronze
indicator-coverage collapse. The 2020 COVID dip is visible and consistent across metrics.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `_require_columns` hard-stops on any missing expected bronze column |
| Era routing correctness | PASS | Disjoint column signatures; Raw Data 2 excluded with manifest record + logged rationale |
| Filter logic logged + justified | PASS | 38 exact duplicates + 3,300 OOS rows recorded via `record_filtered` with reasons; OOS kept in state rollup (verified numerically) |
| Normalization map completeness | PASS | Shared `DEMOGRAPHIC_ALIASES` (never topic-local); effective slice recorded on manifest; unmapped guard blocks unknown labels |
| `strict=False` casts | PASS | `_assert_clean_casts` raises if any NULL appears (bronze verified zero-null); `_assert_binary_flags` guards the 0/1 indicators |
| Dedup keys + tie-break | PASS | Collision guard runs before `deduplicate_by_levels`; duplicates impossible by construction (one group_by per cell) |
| Year extraction | PASS | From `Period Year` column only; filename carries no data year (upload month only) |
| §4b masking | PASS | None needed; none applied; documented |

## NEEDS_JUDGMENT

### Judgment Call 1: `num_youth` description says "county rows sum above the state row," which reverses in 2025
- **Severity if confirmed**: LOW
- **Suspicion**: The served `num_youth` column `description` states: "a youth with contact
  in two counties counts once in each county but once statewide, **so county rows sum above
  the state row**." This illustrative conclusion omits the out-of-state effect (OOS youths
  are in the state row but no county row), so its direction is not universal.
- **Evidence available**: At the state level, summing county `num_youth` for
  `demographic = 'all'` vs the state `all` row: 2010 → county 26,561 ≥ state 25,843
  (claim holds); **2025 → county 12,287 < state 12,361 (claim reversed by −74)**. The
  reversal is real: in 2025 the OOS contribution (present only statewide) outweighs the
  multi-county double-count. The load-bearing guidance ("NOT additive; never sum across
  counties; use state rows") remains correct, and the OOS caveat is separately documented
  in `limitations`.
- **Why uncertain**: The clause is directionally correct in 15 of 16 years and is only an
  explanatory aside; the actionable advice (do not sum county rows) holds either way. Worth
  a one-clause softening for the served text (MCP `describe_dataset` / DataTalk grounding),
  but no data change is warranted — gold faithfully reflects bronze.
- **Location**: `_emit_contract()` in
  `src/etl/criminal_justice/juvenile_clearinghouse/decision_points/transform.py` — the
  `num_youth` column `description`.
- **If confirmed, suggested fix**: Soften to e.g. "…so county rows **generally** sum above
  the state row, though out-of-state youths (counted only statewide) can reverse this in
  low-multi-county years." Bump the contract minor version.

## Notes

- schema_hash: `09e4b9320e0df5a0e33d73774ae2acbab749fde198422379ed9071101a93d642`;
  validation 20 pass / 0 fail / 0 warning; manifest fresh relative to transform.py; zero
  read-loss, zero masked values.
- **Prior Required Fix resolved**: the earlier review's LOW fix (contract caveat
  mis-scoping the race/gender inconsistency) has been applied — the current `demographic`
  description reads "entirely confined to 2025 in the current publication (228 multi-race
  and 247 multi-gender youths, ~1.8% of 2025 youths; zero in 2010-2024)…sums ~2% above it,"
  which I independently verified exactly (per-year multi-race youths: 0 for 2010–2024, 228
  for 2025; multi-gender: 0, then 247; state 2025 race-sum 12,596 vs all 12,361 = +1.90%).
- **Asian mapping (decided, not deferred)**: bronze `Asian → asian` accepted (§2e). If the
  Clearinghouse ever documents that its Asian bucket includes Pacific Islanders, remap to
  `asian_pacific_islander` and bump the contract minor version.
- Raw Data 2 (92,656 rows) remains unserved — a deliberate exclusion and candidate sibling
  topic; nothing in this review blocks that plan.
- v1 parity: no baseline (new criminal_justice-domain topic; post-v1).
