# Data Review: enrollment_program_participation

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review — conducted in the main session; the review
subagent hit the account session limit, so the verification was executed inline with
the same skill obligations)
**Status**: PASS

## Summary

Gold is **byte-identical with the v1 approved baseline (parity MATCH)**, re-verified
independently by this review. All 314,190 rows (= 34,910 wide bronze entity rows ×
9 programs, 2011–2024) reconcile against the shared
`enrollment_by_subgroup_programs` bronze. Both §4b mask groups were replayed from
raw bronze and confirmed exactly; the mask boundaries are surgical (era-precise);
the categorical map is 100% verified; an ordinary entity trace and both extreme
traces match bronze after the documented ÷100 scaling.

## Verdict

- **Required fixes: 0**
- **Judgment items: 0 new** (the transform agent's two LOW deferrals — `student_count`
  naming vs `num_*`, and the structure-doc sample-table correction scope — are
  recorded in `docs/rebuild/rebuild-report.md`; this review found nothing to add)
- **Parity: MATCH** — `compute_gold_sha256('education','enrollment_program_participation')`
  equals the baseline in `docs/rebuild/v1-baseline.yaml`

## Artifact freshness

- `_transform_manifest.json` is newer than `transform.py` (mtime-verified); 
  `_validation.json` fresh and `passed: true` — 20 passed / 0 failed / 1 warning.
- The single warning is the documented null-rate spike at the TFS rollout boundaries
  (2021+ count suppression, 2023+ pct suppression) — expected and documented in the
  contract.
- Bronze freshness gate: PASS 21/21 at batch start; this topic consumes 2011–2024
  only (`min_year=2011` per the shared-module handoff).

## Manifest verification

- **Row counts**: `total_gold` 314,190; per-year counts match the structure doc's
  wide-row counts × 9 exactly. Detail levels: schools 287,955 / districts 26,109 /
  states 126 (one state row per program-year, all 14 years).
- **Categorical map**: `program` — 9 values (alt_programs, eip_k_5, esol, gifted,
  remedial_gr_6_8, remedial_gr_9_12, special_ed_k_12, special_ed_pk,
  vocation_9_12), `unmapped_count` 0. Distinct gold values re-queried: exactly
  those 9. No AYP categoricals recorded (correct for `min_year=2011`).
- **Mask ledger** (both replayed from bronze, see below):
  - `participation_rate`: 5,012 NULLed, years [2011, 2012], reason
    `pre_2013_special_ed_pk_denominator_drift` — counts preserved.
  - `student_count`: 4,938 NULLed, alt_programs 2011/2019 publishing error —
    rates preserved.
- **Filtered**: 0 (zero duplicate keys 2011–2024; collision guard + defensive dedup
  with `sort_col="student_count"` retained). **Reclassified**: 2 (the 2022 charter
  aggregates 7830627/7830636 → district, recorded by the shared module).
  **Read loss**: 0.

## Bronze replay of the two §4b mask groups

| Claim | Bronze evidence (re-read raw via `read_bronze_file`) | Result |
|---|---|---|
| 2011 special_ed_pk pct impossible as share | max `ENROLL_PERCENT_SPECIAL_ED_PK` = **644.1** | CONFIRMED |
| 2012 special_ed_pk pct impossible as share | max = **759.4** | CONFIRMED |
| 2013+ clean (mask must stop) | 2013 max = **100.0** | CONFIRMED |
| alt_programs 2011 corrupted | max `ENROLL_COUNT_ALT_PROGRAMS` = **1,533,435** (state row) | CONFIRMED |
| alt_programs 2019 corrupted | max = **1,602,163** | CONFIRMED |
| Adjacent years sane | 2012 max 32,145; 2013 max 31,560 | CONFIRMED |

**Mask-boundary traces (gold)**:
- special_ed_pk 2012: **2,488 of 2,488** `participation_rate` NULL (full-year mask),
  only 3 `student_count` NULL (counts preserved). 2013: **3 of 2,472** rate NULLs
  (no mask — the 3 are genuine bronze gaps). The boundary is exactly at 2013 as
  documented.
- alt_programs 2011: **2,460** rows count-NULL-with-rate-present (the masked set —
  matches the manifest's 2,460 for 2011); **20** rows kept, minimum kept rate
  **0.966** (consistent with the documented `rate >= 0.95` keep-threshold; the
  kept rows are the genuine all-alternative entities).

## Value traces

- **Extreme — max `student_count`**: 307,995 = 2024 state row, vocation_9_12,
  rate 0.559 — internally consistent state aggregate.
- **Extreme — max `participation_rate`**: exactly **1.0** (post-mask; `unit:
  proportion` bound holds with zero violations — enforced by the derived range
  check).
- **Ordinary — district 601 (Appling County), 2018**: bronze
  `ENROLL_COUNT_ESOL=235 / ENROLL_PCT_ESOL=6.9` and
  `ENROLL_COUNT_GIFTED=193 / ENROLL_PCT_GIFTED=5.7` → gold
  `esol 235 / 0.069` and `gifted 193 / 0.057`, `school_code` NULL on the district
  rows. MATCH (÷100 scaling correct).

## Validation cross-read

- 20 passed / 0 failed / 1 warning (documented TFS-boundary null spikes).
- Authored quality checks present in the contract and passing inside
  `contract_quality_sql`: `special_ed_pk_rate_null_pre_2013`,
  `alt_programs_count_kept_only_for_all_alt_entities_2011_2019`,
  `count_rate_co_null_outside_known_asymmetries`,
  `nine_program_rows_per_entity_year` — plus the auto-derived range guards.
  All pivot-style; no `{object}` self-joins (§15b compliant).
- FK integrity, grain uniqueness, vocabulary: pass per `_validation.json`.

## Shared-module boundary

`_enrollment_subgroup_programs_shared.py` consumed read-only (git-verified
unmodified); scaling/typing/geography/reclassification handled in the module and
already parity-proven through the sibling topic. This transform performs no further
arithmetic on metric values (float-bit parity preserved).

## NEEDS_JUDGMENT

None.

## Notes

- The Codex review (independent) reached PASS / 0 must-fix on the same artifacts.
- v1 parity MATCH means every preserved anomaly above also describes the approved
  v1 gold; the two §4b mask groups reproduce v1's masks exactly.
