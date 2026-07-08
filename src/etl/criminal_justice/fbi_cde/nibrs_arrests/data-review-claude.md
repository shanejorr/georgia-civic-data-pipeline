# Data Review: nibrs_arrests

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Data content is clean: every categorical map verifies semantically against the same-era
FBI lookups, and every extreme-row / per-era / county / state trace reproduced gold
exactly from the bronze zips (both segments, all six count partitions). The one Required
Fix is a served-prose imprecision, not a data defect — the contract states unknown
ethnicity "runs 23-34% by year", but the tiny 290-arrest 2018 partial-adoption sample is
43.8%, exceeding the stated ceiling. v1 parity: **no v1 baseline (topic is post-v1)** —
`docs/rebuild/v1-baseline.yaml` has no `criminal_justice` entries. The lone validator
warning (`tidy_format` on `hispanic_count`) is the deliberate, contract-documented
count-partition design and is a false positive.

## Manifest Verification

Preconditions: FRESH (transform mtime 22:04:39 < manifest gen 22:04:50 ≤ validation
22:07:28), `passed: true`, `read_loss` section absent (zero events).

| Column | Map entries | Bronze seen | Unmapped | Status |
|--------|------------|-------------|----------|--------|
| offense_type | 86 (pinned superset) | 60 | 0 | PASS |
| offense_category | 86 | 60 | 0 | PASS |
| crime_against | 86 | 60 | 0 | PASS |
| offense_group | 86 | 60 | 0 | PASS |
| arrest_type | 3 | 3 | 0 | PASS |
| race_label | 12 (6/era) | 12 | 0 | PASS |
| sex_label | 2 | 2 | 0 | PASS |
| ethnicity_bucket | 8 (4/era) | 8 | 0 | PASS |
| age_bucket | 101 (effective) | 101 | 0 | PASS |
| demographic | 9 | 9 | 0 | PASS |
| county_fips (ORI map) | ~462 ORIs → 153 FIPS | all seen | 0 | PASS |
| coverage | 7 (year-derived) | 7 | 0 | PASS |

**Full map review (every entry checked):**

- **offense_type / offense_category / crime_against / offense_group** — the 14 Group B
  (`90x`) entries are this topic's own vocabulary; I verified all 14 verbatim against
  `GA-2024.zip:NIBRS_OFFENSE_TYPE.csv`, including every counter-intuitive one:
  `90A Bad Checks → Property`, `90F Family Offenses, Nonviolent → Person`,
  `90H Peeping Tom → Person`, `90G Liquor Law Violations → Society`,
  `90K/90L/90M → Other Offenses / Society`, and
  `90I Runaway → offense_category Other Offenses / crime_against Not a Crime /
  offense_group blank → not_a_crime`. All match the FBI lookup exactly. The Group A codes
  are the shared, pinned `_nibrs_shared.GROUP_A_OFFENSE_VOCAB` (verified in the sibling
  nibrs_offenses); I additionally value-traced 35A, 240, and 13B end-to-end (below). Era-1
  surrogate `offense_type_id` is joined against **the same zip's** lookup, so labels are
  era-correct.
- **race_label** — era-scoped maps verified against each era's REF_RACE ids as documented
  in the structure doc: era 1 `0=Unknown, 1=White, 2=Black, 3=American Indian, 4=Asian,
  8=Pacific Islander`; era 2 `10=White, 20=Black, 30=American Indian, 40=Asian,
  50=Pacific Islander, 98=Unknown`. The renumbering hazard (Black 2↔20; 98=Multiple in
  era 1 vs Unknown in era 2) is handled by the per-era lookup; `replace_strict` hard-fails
  any unmapped code. Correct.
- **demographic aliases** — `ALL→all`, `ASIAN→asian`, `BLACK→black`,
  `AMERICAN INDIAN→native_american`, `PACIFIC ISLANDER→pacific_islander`,
  `UNKNOWN→race_unknown`, `WHITE→white`, `MALE/FEMALE`. Split A/PI convention correct per
  §5b (bronze publishes split codes; no combined bucket appears). No rollup key alongside
  the splits → §5a mutual exclusivity holds.
- **ethnicity_bucket** — era 1 `1=hispanic, 2=not_hispanic, 3/NULL(unreported)→
  ethnicity_unknown`; era 2 `10=hispanic, 20=not_hispanic, 40(Unknown)/50(Not Specified)→
  ethnicity_unknown`. Folding Unknown/Not Specified/unreported into one bucket is
  semantically sound.
- **arrest_type** — `1=on_view, 2=summoned_cited, 3=taken_into_custody` (stable across
  eras). Correct.
- **age_bucket** — threshold logic (<18 juvenile) recorded as an effective map. Sentinels
  verified empirically (see Value-Level Spot Checks trace 6).
- **coverage** — `2018-2019→partial_adoption`, `2020+→full_participation`
  (`FULL_PARTICIPATION_START_YEAR=2020`); authored check enforces it.
- **county_fips (ORI map)** — every observed ORI resolves to a FIPS (153 distinct);
  0 `unassigned_statewide` (no statewide-agency arrest rows occurred 2018-2024); unmatched
  ORIs hard-fail upstream.

**Row-count reconciliation** (manifest `row_counts` + state `all` totals vs bronze):

| Year | Bronze | Explicit filtered | Gold | State 'all' (linked) reconciliation |
|------|--------|-------------------|------|-------------------------------------|
| 2018 | 315 | 37 (25 M + 12 dup roster) | 419 | 290 = 315 − 25 M ✓ |
| 2019 | 20,909 | 683 M | 9,960 | 20,226 = 20,909 − 683 ✓ |
| 2020 | 66,107 | 2,234 M | 18,549 | 63,873 = 66,107 − 2,234 ✓ |
| 2021 | 89,021 | 2,353 M | 21,140 | 86,668 = 89,021 − 2,353 ✓ |
| 2022 | 95,901 + 86,162 | 2,306 M | 22,267 | linked 93,595 ✓; groupB state 86,162 = member rows ✓ |
| 2023 | 92,942 + 92,082 | 1,751 M | 21,770 | linked 91,191 ✓; groupB 92,082 ✓ |
| 2024 | 96,433 + 94,440 | 1,522 M | 21,051 | linked 94,911 ✓; groupB 94,440 ✓ |

Per-year M counts sum to the manifest's 10,874; +12 dup-roster = 10,886 total explicit.
Bronze member counts match the structure doc's table for every year/segment. Gold parquet
rows = 115,156 = manifest `total_gold`. Expansion factors decline (1.33→0.11) because gold
is an aggregate whose row count tracks cell diversity, not arrest volume — expected for a
record→aggregate transform.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| data_year / DATA_YEAR | year | MAPPED (`assert_data_year` = filename year) |
| incident_id → agency_id → ori | county_fips | MAPPED (via ori_to_county crosswalk; Group A only) |
| offense_code / OFFENSE_TYPE_ID (era-1 lookup) | offense_type (+category, crime_against, offense_group) | MAPPED |
| arrest_type_id | arrest_type | MAPPED |
| race_id, sex_code | demographic rows | MAPPED |
| ethnicity_id | hispanic/not_hispanic/ethnicity_unknown_count | MAPPED (count partition — documented) |
| age_num (+ age_id sentinels) | juvenile/adult/age_unknown_count | MAPPED (count partition) |
| (row aggregation) | arrest_count | MAPPED (M segments excluded) |
| agencies.csv roster | agencies_reporting | MAPPED (coverage companion) |
| arrestee_id / groupb_arrestee_id / seq_num | — | CORRECTLY EXCLUDED (row ids) |
| arrest_date | — | CORRECTLY EXCLUDED (spills across calendar years; data_year is grain) |
| multiple_indicator | — | CORRECTLY EXCLUDED (dedup filter only, recorded) |
| resident_code / under_18_disposition_code / clearance_ind | — | CORRECTLY EXCLUDED (26-34% missing / juvenile-only / 100% blank) |
| age_id, age_range_low/high_num | — | CORRECTLY EXCLUDED (redundant/near-empty; age_id consumed for sentinels) |
| weapon child segments | — | CORRECTLY EXCLUDED (child grain, 98% unarmed) |
| lookups / agencies attributes | — | CORRECTLY EXCLUDED (recode sources / crosswalk-side) |

No gold column lacks a bronze provenance; no classified fact column is missing.

## Value-Level Spot Checks

All traces recomputed independently from the bronze zips (era-correct lookups, M-filtered,
ORI→county join replicated):

1. **Global max arrest_count** — gold 2023 state group_b_arrest_report all all_other_offenses
   taken_into_custody = **30,039**. Bronze GA-2023 `NIBRS_ARRESTEE_GROUPB.csv`
   `offense_code='90Z' & arrest_type_id='3'` = 30,039 **MATCH**; ethnicity partition
   hispanic(10)=2,375, not_hispanic(20)=19,131, unknown(40/50)=8,533 — **all MATCH** gold.
2. **Global min arrest_count (=1)** — gold 2018 county 13005 (Bacon) motor_vehicle_theft
   on_view all. Bronze GA-2018 era-1 join (offense-lookup + incident→agency→ORI→county,
   M-filtered), `offense_code='240' & arrest_type_id='1' & county=13005` = 1 **MATCH**.
3. **Era-1 race/sex partition** — gold 2020 state group_a summed over offense/arrest_type:
   all=63,873, white=28,766, black=34,197, asian=345, pacific_islander=23,
   native_american=75, race_unknown=467, male=45,753, female=18,120. Bronze GA-2020 non-M
   race_id counts (0=467,1=28,766,2=34,197,3=75,4=345,8=23) reproduce every value; race sum
   and sex sum each equal 63,873 = all — **all MATCH**.
4. **County reconciliation** — gold 2024 Fulton (13121) group_a all summed = **16,346**;
   bronze GA-2024 non-M arrests attributed to 13121 via the crosswalk = 16,346 **MATCH**.
   GA-2024 Group A: 0 unmatched ORIs, 0 statewide-agency (NULL-county) rows — confirms the
   "no statewide arrests 2018-2024" note.
5. **Era-1 granular w/ partitions** — gold 2019 state group_a drug_narcotic_violations
   black taken_into_custody = arrest 807 / juv 32 / adult 775 / age_unk 0 / hisp 5 /
   not_hisp 298 / eth_unk 504. Bronze GA-2019 non-M `35A(lookup) & arrest_type 3 &
   race_id 2`, age & ethnicity bucketed per the era-1 rules = **every column MATCH**.
6. **Age sentinels (empirical)** — era-2 `age_num=='00'` co-occurs with `age_id=='103'`
   (Unknown) in **every** era-2 year (2021:29, 2022:12, 2023:30, 2024:26 rows, all id 103),
   confirming '00' is the Unknown sentinel, not an infant — and real ages 01-09
   (14/36/23/49 rows/yr) are preserved as juvenile. Era 1 never publishes '00'.
7. **`not_a_crime` (90I runaway)** — appears in gold **only in 2020**, with
   `crime_against=not_a_crime` and `offense_group=not_a_crime`, matching the contract's
   crime_against prose ("a handful ... appear in 2020") and the FBI lookup exactly.
8. **Sentinel year-attribution (Risk 3)** — N/A: `year` = zip filename with
   `assert_data_year` proving `data_year` equality on every member; the only year literals
   (2020/2022) gate coverage/segment logic, not string parsing.
9. **Aggregate-row reconciliation (Risk 4)** — state rows derived by grouping ALL arrests
   (not summing county rows): every year's linked state `all` = bronze non-M total; Group B
   state totals = member counts exactly; state ≥ county-sum enforced by contract SQL
   (PASS). All aggregations are counts; no `.mean()` anywhere.
10. **Dedup tie-break (Risk 5)** — N/A: one zip per data year, no overlap;
    `assert_no_natural_key_collisions` runs before dedup and hard-fails on divergence.
11. **Suppression semantics** — N/A: record-level extracts, no suppression markers in any
    era; `suppressed_to_null=False`.

## Validation Cross-Read

- `_validation.json`: **19 pass / 0 fail / 1 warning**. `contract_parquet_schema`,
  `contract_quality_sql` (**28 checks**), `grain_uniqueness`, and `foreign_keys`
  (153 county keys + 9 demographic keys resolve) all pass.
- **Warning explained**: `tidy_format` flags `hispanic_count` as possibly wide-format.
  This is the deliberate count-partition design — NIBRS race and ethnicity are separate
  fields, and the shared vocabulary registers `hispanic` under the `race` category, so
  emitting hispanic demographic *rows* would break §5a race-partition exclusivity. The
  partition identity is contract-enforced (`hispanic + not_hispanic + ethnicity_unknown =
  arrest_count` on every row). False positive.
- `schema_hash`: `0d53e28110e59527884506812de6de7288f4098f0a064b63e361b60bc54b5c58`.
- **§4b masking audit**: no `_null_*` helpers, no `masked_values` manifest section,
  `suppressed_to_null=False` — consistent; all metrics are derived row counts, so
  impossible values cannot occur. PASS.
- **§15b coverage judgment**: the 12 authored quality checks cover the real invariants —
  both partition identities (age, ethnicity), race- and sex-partition-of-all (§5a),
  `arrest_count ≥ 1`, state ≥ county-sum per cell, Group B state-only + 2022-start (both
  coverage breaks), coverage↔year, offense_type→dependent-attribute functional dependency,
  and agencies_reporting constancy + positivity. No obvious missing invariant. PASS.
- **v1 parity**: no v1 baseline (topic is post-v1) — `docs/rebuild/v1-baseline.yaml` has no
  `criminal_justice` entries, so no hash comparison is possible or expected.
- Contract enums vs gold distinct sets match exactly for `demographic`, `coverage`,
  `reporting_segment`, `offense_category`, `crime_against`, `offense_group`, `arrest_type`
  (offense_type intentionally carries no enum).

## Cross-Era Consistency

- **Overlap years**: none (one zip per data year) — dedup tie-break N/A.
- **Cross-year NULL sweep**: no metric column is ≥95% NULL in any year; only `county_fips`
  is nullable (by design, on state rows). No era-localized rename-bug signature.
- **Level continuity (3d)**: linked-segment state `all` sums 290 → 20,226 → 63,873 →
  86,668 → 93,595 → 91,191 → 94,911. The 2018→2020 ramp is the SRS→NIBRS adoption, versioned
  by `coverage` and quantified by `agencies_reporting` (37→276→401→…); within
  full_participation the series is stable. The Group B series is segment-isolated (2022+),
  so no fabricated 2021→2022 jump reaches any served segment. No scale anomaly, no
  cumulative-publication signature.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `require_columns` guards every member read; all exclusions classified `not_in_gold` |
| Era routing | PASS | `detect_era_by_columns` on offense-column signature; Group B hard-fails if matched to era 1; missing 2022+ Group B member hard-fails |
| Filter logic | PASS | M-segment exclusion (10,874) + 2018 dup-roster (12) recorded via `record_filtered` with reasons |
| Normalization completeness | PASS | Maps era-scoped, `replace_strict` everywhere → unmapped codes hard-fail; Group B vocab verified vs FBI lookup |
| `strict=False` casts | PASS | None; the age cast is `strict=True` |
| Dedup keys + tie-break | PASS | Collision guard before dedup; `deduplicate_by_levels(sort_col="arrest_count")` as documented safety net only |
| Year extraction | PASS | Filename year + `assert_data_year` on arrestee, incident, and agency frames |
| §4b masks | PASS | None needed (count-derived metrics); manifest and contract agree |
| Contract prose fidelity | FLAG | See Required Fix 1 (ethnicity-unknown range understates 2018) |

## Required Fixes

### Fix 1: Contract's "23-34%" unknown-ethnicity range understates the 2018 sample
- **Severity**: LOW
- **Issue**: The served `ethnicity_unknown_count` description and the contract
  `limitations` both assert unknown/unreported ethnicity "runs 23-34% by year". The
  measured share exceeds the 34% ceiling in 2018. The claim is served verbatim to the REST
  schema endpoint, MCP `describe_dataset`, and DataTalk, so a grounded answer about 2018
  would cite a wrong figure.
- **Evidence**: `ethnicity_unknown / arrest_count` at state `demographic='all'` by year:
  2018 = 127/290 = **43.8%**, 2019 = 32.1%, 2020 = 26.2%, 2021 = 23.6%, 2022 = 23.4%,
  2023 = 25.1%, 2024 = 23.2%. The 23% floor holds; the 34% ceiling is exceeded only by the
  290-arrest 2018 partial-adoption sample. (2018 is a tiny, explicitly non-comparable
  early-adopter year, which is why this is LOW.)
- **Location**: `transform.py` → `_emit_contract()` — the `ethnicity_unknown_count`
  column `description` ("23-34% of arrests depending on the year") and the topic
  `limitations` string ("unknown/unreported ethnicity runs 23-34% by year").
- **Suggested fix**: Broaden the range to cover 2018 (e.g. "23-44% by year") or qualify it
  ("~23-32% in the full-participation years, higher in the tiny 2018 early-adopter
  sample"), then re-run the transform to re-emit the contract.

## Notes

- `schema_hash 0d53e28110e59527884506812de6de7288f4098f0a064b63e361b60bc54b5c58`;
  validation 19 pass / 0 fail / 1 warning (explained); manifest has no
  read_loss / masked_values / reclassified sections (zero events).
- **2e Asian/PI test**: bronze REF_RACE publishes split codes (era-1 4/8, era-2 40/50) and
  no combined bucket in any year; gold emits `asian` and `pacific_islander` separately with
  no `asian_pacific_islander` key. At 2020 state level the race buckets sum exactly to the
  `all` total (63,873/63,873) with both split keys present — positive evidence the split
  convention is correct, NOT conflated.
- **Under-10 arrestees preserved as juvenile**: real `age_num` 01-09 rows (≈120+/yr in
  era 2) are kept as juvenile per the structure doc's "preserve unless provably impossible";
  only `age_num=='00'` (verified ⇔ Unknown age_id 103) is bucketed age_unknown. Correct,
  and it disproves the structure doc's infant-artifact hypothesis for '00'.
- The Group A offense vocabulary is the shared, pinned `_nibrs_shared` map (owned/verified
  by the sibling nibrs_offenses); this review verified the 14 Group B entries against the
  FBI lookup and value-traced representative Group A codes (35A, 240, 13B).
