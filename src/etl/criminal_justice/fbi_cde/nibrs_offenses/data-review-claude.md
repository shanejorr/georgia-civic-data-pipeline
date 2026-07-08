# Data Review: nibrs_offenses

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Every bronze-to-gold count reproduces exactly (state offense_count totals equal the
raw bronze offense-row counts for all 7 years; extreme, era-1, and ordinary traces
match to the row), the pinned Group A offense vocabulary is a 100% match against the
FBI's own GA-2024 lookup (all 72 entries — offense_type, offense_category,
crime_against), and validation is 20/20 with no warnings. The prior review's one HIGH
finding — multi-county agencies attributed to the alphabetically-first county rather
than their primary county (Atlanta PD wholly in DeKalb) — has been **fixed and
re-run**: the crosswalk now resolves the primary county from the ORI county ordinal
plus a small override table, a full 2024 per-county recompute from bronze matches gold
with **0 mismatches** across all counties, and Atlanta PD's 31,983 offenses now land in
Fulton (Fulton 2024 = 66,155 > DeKalb 54,340, correcting the prior inversion). Both
prior LOW judgment items are now documented in the artifacts. v1 parity: **no v1
baseline** — `docs/rebuild/v1-baseline.yaml` has no `criminal_justice` entries (topic is
post-v1).

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| offense_type | 72 | 51 (+`23*` guard, unseen) | 0 | PASS — all 72 verified vs 2024 bronze lookup |
| offense_category | 72 | 51 | 0 | PASS — same verification (24 produced) |
| crime_against | 72 | 51 | 0 | PASS — same verification (person/property/society) |
| attempt_status | 2 (C/A) | 2 | 0 | PASS |
| coverage | 7 (year-derived) | 7 | 0 | PASS |
| county_fips | 434 ORIs | 434 | 0 | PASS — multi-county now maps to primary county |

**Offense vocabulary — 100% verified programmatically (Step 2b).** All 72
`GROUP_A_OFFENSE_VOCAB` entries were compared against `GA-2024.zip:NIBRS_OFFENSE_TYPE.csv`
(offense_name → snake_case offense_type, offense_category_name → snake_case
offense_category, crime_against lowercased): **0 mismatches**. Spot-confirmed
surprising-but-correct FBI classifications, each quoted from the 2024 bronze lookup:
`26H` "Money Laundering" → `other_offenses` / `society` (not fraud);
`510` "Bribery" crime_against = `Property`; `23*` "Not Specified" →
`larceny_theft_not_specified`; `101`/`103` Treason/Espionage → `other_offenses`/`society`.
The `11D` label is the 2024 wording "Criminal Sexual Contact" → `criminal_sexual_contact`
(earlier lookups' "Fondling"), exactly as the docstring pins. The 20 map codes never seen
in GA data (immigration 30A–30D, federal 58A/61A, `26H`, `521`/`522`, etc.) are correctly
held as guards; none of them map to `other_offenses` in the produced set, so the emitted
`offense_category` enum (24 values, no `other_offenses`) equals the manifest's
`gold_values_produced` exactly (2c PASS).

**attempt_status**: `C → completed`, `A → attempted` — matches the structure doc's NIBRS
`attempt_complete_flag` definition ("`C` completed / `A` attempted").

**coverage**: 2018/2019 → `partial_adoption`, 2020–2024 → `full_participation` — matches
the documented Oct-2019 SRS→NIBRS transition and the `coverage_matches_transition_year`
quality check.

**county_fips (ORI → primary county)**: verified below — see Value-Level Spot Checks and
Transform Logic Risks. The multi-county attribution defect from the prior review is
resolved.

### Row-count reconciliation

| Year | Bronze offense rows | Gold rows | Gold state offense_count sum | Verdict |
|---|---|---|---|---|
| 2018 | 879 | 202 | 879 | MATCH (12 duplicate roster rows dropped, recorded `filtered_explicit`) |
| 2019 | 84,895 | 2,686 | 84,895 | MATCH |
| 2020 | 332,191 | 4,145 | 332,191 | MATCH |
| 2021 | 402,368 | 4,343 | 402,368 | MATCH |
| 2022 | 434,291 | 4,416 | 434,291 | MATCH |
| 2023 | 442,508 | 4,390 | 442,508 | MATCH |
| 2024 | 432,444 | 4,275 | 432,444 | MATCH |

Gold parquet total = **24,457** = manifest `total_gold` ✓ (3b). "Filtered" counts are
aggregation compression (offense rows → county×offense cells), not row loss: state-row
offense_count sums reproduce bronze exactly in every year, so zero offense rows were
lost. Read-loss events: 0. The SRS estimates sidecar is recorded on the manifest as
`srs_estimates_EXCLUDED` with a documented incompatible-methodology rationale (estimated,
hierarchy-ruled SRS index crimes vs unestimated NIBRS counts) — exclusion appropriate.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| data_year | year | MAPPED (asserted == filename year, hard-fail) |
| agencies.ori → crosswalk | county_fips | MAPPED (primary-county attribution; fix verified) |
| OFFENSE.offense_code (era 1 via OFFENSE_TYPE_ID join) | offense_type | MAPPED (descriptive names, no-source-codes convention) |
| OFFENSE_TYPE.offense_category_name / crime_against | offense_category, crime_against | MAPPED (denormalized, FD-checked) |
| OFFENSE rows (counted) | offense_count | MAPPED |
| incident_id (distinct) | incident_count | MAPPED (degenerate at this grain — documented, see Notes) |
| attempt_complete_flag | completed_count / attempted_count | MAPPED (pivoted; doc offered this) |
| agencies (roster count) | agencies_reporting | MAPPED |
| cleared_except_id | — | CORRECTLY EXCLUDED (incident-grain; exclusion now documented in docstring) |
| location_id / NIBRS_LOCATION_TYPE | — | CORRECTLY EXCLUDED (doc: include only if gold keeps location breakdown) |
| agencies names/types/population | — | CORRECTLY EXCLUDED (dimension attributes) |
| incident_hour/dates/cargo_theft/report_date_flag | — | CORRECTLY EXCLUDED (below gold grain) |
| incident_status/data_home/orig_format/did | — | CORRECTLY EXCLUDED (FBI internal) |
| NIBRS_month.* | — | CORRECTLY EXCLUDED (grain flip; trustworthy only 2018–2020) |
| num_premises_entered/method_entry_code | — | CORRECTLY EXCLUDED (burglary-only, 95%+ null) |
| srs_estimates columns | — | CORRECTLY EXCLUDED (separate-topic rationale on manifest) |
| victim/offender/arrestee segments | — | CORRECTLY EXCLUDED (sibling topics) |

No gold column lacks bronze provenance (no fabrication). Era rename handling is by
column signature (`offense_type_id` vs `offense_code`), mutually exclusive — no typo
risk surface. Contract prose audited against the structure doc (Step 6): no
contradictions on year range, coverage counts, suppression scheme, percentage scale, or
demographic convention. (The contract's "37 in 2018" is the correct post-dedup distinct-
agency count; the structure doc's "49" is the raw roster row count including the 12
exact duplicates — precision, not a contradiction.)

## Value-Level Spot Checks

All recounts computed independently from the bronze zips (NIBRS_OFFENSE → NIBRS_incident
→ agencies → ori_to_county crosswalk primary county), executed 2026-07-06:

| Trace | Bronze recount | Gold | Verdict |
|---|---|---|---|
| **Extreme global max**: 2021 DeKalb (13089) simple_assault (13B) | 11,422 rows / 11,422 C / 0 A / 11,422 incidents; 14 roster agencies primary→13089 | 11,422 / completed 11,422 / attempted 0 / incident 11,422 / agencies_reporting 14 | MATCH |
| **Extreme global min**: 2018 Coweta (13077) theft_from_building (23D) | 1 row / 1 C / 0 A / 1 incident | offense 1 / completed 1 / attempted 0 / incident 1 | MATCH |
| **Ordinary era 1** (uppercase + surrogate-id join): 2019 Chatham (13051) burglary (220) | 91 rows / 87 C / 4 A / 91 incidents | 91 / 87 / 4 / 91 | MATCH |
| **Full 2024 per-county reconciliation** (all counties): bronze recompute vs gold offense_count | 0 counties differ | — | MATCH |
| 2024 statewide attempt partition | C 416,887 / A 15,557 (structure doc categorical table, quoted) | state completed sum 416,887 / attempted sum 15,557 | MATCH |
| 2018 roster dedup | 49 roster rows → 37 distinct agencies | 2018 state agencies_reporting = 37; 12 drops recorded on manifest | MATCH |
| Multi-county fix: Atlanta PD (GAAPD0000) 2024 | 31,983 offenses → county 13121 (Fulton) | gold Fulton 66,155 > DeKalb 54,340 (prior inversion corrected) | MATCH |

- **4a extreme traces**: both global extremes traced to bronze — no unit/scale/column-
  swap error.
- **4c sentinel year-attribution**: N/A — no year-bearing string parsing; `year` comes
  from `GA-{year}.zip` and `assert_data_year` hard-fails unless every segment row's
  `data_year` equals it.
- **4d aggregate reconciliation**: state rollup offense_count = sum of county rows =
  bronze offense rows in every year (zero statewide/NULL-county submissions), and the
  full 2024 per-county recompute matches gold exactly (0 mismatches).
- **4e dedup tie-break**: N/A — one zip per data year, no overlap years;
  `assert_no_natural_key_collisions` runs before the dedup safety net.
- **4f suppression**: N/A — NIBRS master extracts are unsuppressed
  (`suppressed_to_null: false`); validator confirms no suppression markers.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 0 warning** (2026-07-02T22:05:43Z), including
  `contract_parquet_schema` (14 files), `contract_quality_sql` (17 checks),
  `grain_uniqueness`, `foreign_keys` (county_fips → counties: all 154 keys resolve), and
  geography nulling for both detail levels.
- `schema_hash`: `1f12d58680f14f7739375f851676dd2e0aed49acfa7f8c54bf23d84a3043d593`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no
  `masked_values` section (zero events); consistent with the docstring's "No §4b masks"
  rationale — every metric is a derived row count, so impossible values cannot occur.
  PASS.
- **§15b coverage judgment**: strong — 8 authored checks cover the attempt partition,
  count floors, incident ≤ offense bounds, state ≥ county sum, roster constancy per
  (year, county), coverage-year consistency, and the offense_type → category/crime_against
  functional dependency. No missing obvious invariant.
- **incident_count degeneracy (prior Judgment 1) — resolved**: `incident_count !=
  offense_count` on **0 of 24,457** rows (structural: a NIBRS incident reports each
  offense code at most once, so at this grain "distinct incidents" always equals the
  offense-row count). The contract description now explicitly documents this ("in the GA
  extracts an offense type appears at most once per incident, so incident_count equals
  offense_count within a row; the column is kept for grouped rollups, where the two
  diverge"), addressing the prior communication concern. Values are accurate.
- **cleared_except_id exclusion (prior Judgment 2) — resolved**: the transform docstring
  now carries an explicit design-decision bullet ("`cleared_except_id` excluded …
  exceptional clearance is an incident-grain attribute … not cleared-by-arrest"), so the
  omission is documented.
- **v1 parity (5d)**: **no v1 baseline** — `docs/rebuild/v1-baseline.yaml` contains no
  `criminal_justice/*` topics (verified); this is a post-v1 topic with no v1 gold to
  compare against. Not a divergence.

## Cross-Era Consistency

- **Format-era boundary (2020 zip → 2021 zip)** is a *format* change (uppercase +
  surrogate-id join vs lowercase + native code); state totals move smoothly across it
  (×1.21 into 2021, then ×1.08, ×1.02, ×0.98) and the era-1 surrogate join was verified
  value-for-value by the 2019 Chatham trace.
- **Methodology boundary (adoption ramp)**: 2018→2019 ×96.6, 2019→2020 ×3.91 — the
  documented NIBRS adoption ramp, correctly versioned by the `coverage` flag and
  `agencies_reporting` companion (37 → 276 → 401+ agencies) rather than pooled or
  estimated. No unexplained >10x jump exists anywhere in the full-participation era
  (2020+).
- **Cross-year NULL sweep (3c)**: no metric column is ≥95% NULL in any year (only
  `county_fips` on state rows, by design). No era-localized rename signature.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| ORI→county primary attribution | PASS (was HIGH) | Prior defect fixed: crosswalk resolves primary via ORI county ordinal (708/710 single-county agencies agree; 2 exceptions are single-county where the roster county wins anyway) + `ORI_PRIMARY_OVERRIDES` (Atlanta PD→Fulton). All 41 multi-county ORIs resolve to a county in their own listed set (0 not-listed); full 2024 per-county reconciliation is exact. |
| Silent column drops | PASS | `require_columns` guards every member read; missing columns hard-fail |
| Era routing | PASS | Signature-based (`offense_type_id` vs `offense_code`), mutually exclusive, unmatched raises; era-1 lookup read from the same zip (per-extract id spaces respected) |
| Filter logic | PASS | Only filters: 12 exact-duplicate 2018 roster rows (logged + manifest) and the non-Group-A guard (0 rows today; unknown codes hard-fail) |
| Normalization map completeness | PASS | 72/72 Group A codes; 100% verified vs the 2024 bronze lookup |
| `strict=False` casts | PASS | None — all recodes use `replace_strict`; metrics are constructed Int64 |
| Dedup keys + tie-break | PASS | Collision guard raises before dedup; one zip per year makes duplicates impossible today |
| Year extraction | PASS | Filename year hard-asserted against `data_year` on every segment |
| §4b masks | PASS | None needed; none claimed; manifest agrees |

## Notes

- `schema_hash`: `1f12d58680f14f7739375f851676dd2e0aed49acfa7f8c54bf23d84a3043d593`;
  validation 20 pass / 0 fail / 0 warning; read_loss events 0; masked_values none;
  unmapped 0 across all 6 recorded categoricals. Gold total 24,457 rows.
- **Prior review superseded.** The 2026-07-02 report was `NEEDS FIXES` on the multi-county
  attribution defect (Fix 1); the crosswalk was rebuilt (`build_ori_to_county.py` now
  ORI-ordinal + override) and this transform re-run. Gold row counts changed accordingly
  (per-county cell counts redistributed; total 24,412 → 24,457). This review independently
  re-verified the corrected gold.
- Risk-hypothesis sweep: (1) Asian/PI conflation — N/A, no demographic column (offense
  segment carries no person attributes). (2) Era rename typo — PASS (NULL sweep clean).
  (3) Sentinel year attribution — N/A/PASS (hard-asserted). (4) Derived aggregation —
  PASS (state = county sum = bronze every year; full 2024 per-county recompute exact).
  (5) Dedup inversion — N/A (no overlap years). (6) Mutual exclusivity — N/A. (7)
  Wrong-meaning mapping — PASS for all offense vocab (72/72) and for county_fips
  (multi-county primary attribution now correct).
- Minor, non-blocking observation (not a finding): the served contract `limitations`
  documents the SRS and demographics exclusions but not the clearance exclusion; a
  future minor version could surface the (now docstring-documented) clearance rationale
  in the served limitations. No contradiction and no data-accuracy impact.
