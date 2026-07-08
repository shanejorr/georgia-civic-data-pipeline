# Data Review: wida_access

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Bronze-to-gold accuracy is verified end-to-end with zero findings. **v1 parity: MATCH — byte-identical with v1 gold** (re-verified independently in this review). All 31 categorical map entries across 3 columns are semantically correct and 100% covered; all 12 extreme-row traces and 2 ordinary per-era traces match bronze exactly; per-year statewide tested totals reproduce the structure doc's table to the student; and every claim in the structure doc's Corrections section was independently re-verified against raw bronze (2021's 8 non-grade rows, max pct-sum deviation 2e-06, 2021 published denominators equal to level-count sums with 0 mismatches).

## Manifest Verification

Preconditions: artifacts FRESH (transform mtime 20:06:24 < manifest 20:06:40 = validation 20:06:40), `_validation.json` `passed: true` (19 pass / 0 fail / 0 warning). No `read_loss`, `masked_values`, or `reclassified` sections in the manifest (absent = zero events).

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `domain` | 12 | 12 (8 Era-1 base + 4 Era-2 footnote variants) | 0 | PASS |
| `grade_level` | 13 | 13 (`K`, `1`..`12`) | 0 | PASS |
| `proficiency_level` | 6 | 6 | 0 | PASS |

**Full map review — every entry verified semantically:**

- `domain` (12 → 8): `Listening Domain → listening`, `Speaking Domain → speaking`, `Reading Domain → reading`, `Writing Domain → writing` — correct (the four individually tested WIDA language domains). `Oral Language Composite`/`Oral Language CompositeA → oral_language_composite`, `Literacy Composite`/`Literacy CompositeB → literacy_composite`, `Comprehension Composite`/`Comprehension CompositeC → comprehension_composite`, `Overall Score Composite`/`Overall Score CompositeD → overall_score_composite` — correct; the trailing A–D letters are footnote references unique to the 2021 file. Verified against the 2021 footnote rows read directly from bronze: `'AOral Language = 50% Listening + 50% Speaking'`, `'BLiteracy = 50% Reading + 50% Writing'`, `'CComprehension = 70% Reading + 30% Listening'`, `'DOverall Score = 35% Reading + 35% Writing + 15% Listening + 15% Speaking'` — these also confirm the composite-weighting prose in the contract's `domain` description verbatim.
- `grade_level` (13 → 13): `K → k`, `1 → 01` … `12 → 12` via the shared `GRADE_LEVEL_MAP`. Correct canonical codes per §16; matches the contract enum exactly.
- `proficiency_level` (6 → 6): `Level 1 Entering → level_1_entering` … `Level 6 Reaching → level_6_reaching`. The fixed WIDA six-level scale, in order; correct.
- 2a completeness: every distinct bronze value documented in `bronze-data-structure.md` appears in `bronze_values_seen` (all 12 domain labels including all 4 footnote variants, all 13 grades, all 6 levels). No documented-but-unseen values.
- 2c contract cross-check: `gold_values_produced` equals the contract `enum` for all three columns (8 domains, 13 grades, 6 levels).
- 2d: `unmapped_count` = 0 for all three columns.
- 2e Asian/PI conflation: **N/A** — no `demographic` column (grade-primary topic) and no `pct_asian` column.
- 2f mutual exclusivity: **N/A** — no demographic column; `grade_level` values are inherently disjoint single grades (no `all` rollup published).

**Row-count reconciliation:**

| Year | Bronze rows | Filtered (explicit) | Gold rows | Expansion | Assessment |
|---|---|---|---|---|---|
| 2017–2020, 2022–2024 (each) | 13 | 0 | 624 | 48.0 | 13 grades × 8 domains × 6 levels = 624 exactly |
| 2021 | 21 | 8 (`non_grade_footnote_or_blank_rows`) | 624 | 29.7 | (21 − 8) × 48 = 624 exactly |

Manifest `total_gold` = 4,992 = actual parquet rows (8 × 624, re-counted from disk). The 2021 filter ledger is exact: my independent openpyxl read of the 2021 data region found precisely 8 non-grade rows (2 blanks, 4 composite-weighting footnotes A–D, 1 note, 1 URL) and 0 in every other file — confirming the Corrections-section claim.

## Column Coverage

| Bronze column (group) | Gold column | Status |
|---|---|---|
| `Grade` (row axis) | `grade_level` | MAPPED (grade-in-demographic policy: grade is the primary row axis, no `demographic` column — per Corrections note and education CLAUDE.md) |
| `Total Number of Students Tested` (Era 1) / `…Tested in At Least One Domain` (Era 2) | `num_tested` | MAPPED (same semantic, era-specific header handled by `TOTAL_TESTED_HEADER`) |
| `{Domain} \| {Level} \| # of Students at Level` (48 cols) | `num_at_proficiency_level` | MAPPED (unpivoted) |
| `{Domain} \| {Level} \| % of Total Tested` (48 cols) | `pct_at_proficiency_level` | MAPPED (unpivoted, ÷100) |
| `{Domain} \| Total Tested in Domain` (Era 2 only, 8 cols) | `num_tested_in_domain` | MAPPED (Era 2 published value; Era 1 reconstructed as six-level count sum — see Spot Checks) |
| `Percentage of Enrolled Students Tested in At Least One Domain` (Era 2 only) | `enrollment_tested_rate` | MAPPED (÷100; NULL outside 2021) |
| `{Domain} \| Percentage of Enrolled Students Tested in Domain/Both Domains/All Four Domains` (Era 2 only, 8 cols) | `enrollment_tested_in_domain_rate` | MAPPED (÷100; prefix-matched with exactly-one guard; NULL outside 2021) |
| Row-1 title string | — | CORRECTLY EXCLUDED (redundant with filename year; used only for the year cross-check) |
| 2021 footnote/blank/URL rows | — | CORRECTLY EXCLUDED (filtered + ledgered, 8 rows) |
| (filename) | `year` | MAPPED |
| (implicit, state-only) | `district_code`, `school_code` | MAPPED (always NULL) |

Column arithmetic confirms no silent drops: Era 1 = 1 + 1 + 96 = 98 columns, all consumed; Era 2 = 1 + 1 + 1 + 8×(1 + 1 + 12) = 115 columns, all consumed. No gold column lacks a bronze source (no fabrication).

## Value-Level Spot Checks

All traces use an independent openpyxl reader (separate implementation from the transform). Every check below quotes the actual bronze cell values.

**Extreme-row traces (global max and min of every metric — 12 traces, all columns checked per trace):**

| Metric | Extreme | Entity | Bronze | Gold | Verdict |
|---|---|---|---|---|---|
| `num_at_proficiency_level` | max 11,790 | 2023 K reading L1 | count=11790, pct=76.93311582381729, denom(sum)=15325, total=15342 | 11790 / 0.7693311582381729 / 15325 / 15342 | MATCH |
| `num_at_proficiency_level` | min 0 | 2017 g01 writing L6 | count=0, pct=0, denom=17068, total=17153 | 0 / 0.0 / 17068 / 17153 | MATCH (real zero, no suppression) |
| `pct_at_proficiency_level` | max 0.80810581411798 | 2024 K reading L1 | pct=80.810581411798, count=11425, denom=14138, total=14148 | all match | MATCH |
| `pct_at_proficiency_level` | min 0.0 | 2017 g01 writing L6 | pct=0 | 0.0 | MATCH |
| `num_tested_in_domain` | max 17,526 | 2024 g02 listening | level-count sum=17526, total=17527 | 17526 | MATCH (Era-1 reconstruction) |
| `num_tested_in_domain` | min 1,102 | 2017 g12 overall_score_composite | sum=1102, total=1121 | 1102 | MATCH |
| `num_tested` | max 17,527 | 2024 g02 | `Total Number of Students Tested`=17527 | 17527 | MATCH |
| `num_tested` | min 1,121 | 2017 g12 | total=1121 | 1121 | MATCH |
| `enrollment_tested_rate` | max 0.9545115 | 2021 K | `Percentage of Enrolled…At Least One Domain`=95.45115 | 0.9545115 | MATCH |
| `enrollment_tested_rate` | min 0.66647382 | 2021 g12 | 66.647382 | 0.66647382 | MATCH |
| `enrollment_tested_in_domain_rate` | max 0.95413803 | 2021 K listening | 95.413803 | 0.9541380300000001 | MATCH |
| `enrollment_tested_in_domain_rate` | min 0.64420017 | 2021 g12 overall_score_composite (`…All Four Domains`) | 64.420017 | 0.6442001700000001 | MATCH |

The 2021 extreme traces additionally verified the Era-2 published denominator path: e.g. 2021 K listening `Total Tested in Domain`=12774 → gold `num_tested_in_domain`=12774, with `num_tested`=12779 from `Total Number of Students Tested in At Least One Domain`.

**Ordinary traces (one per era, all columns):**

- Era 1 — 2019 grade 07, speaking/level_3_developing: bronze count=2213, pct=39.175075, six-level sum=5649, total=5658 → gold 2213 / 0.39175075 / 5649 / 5658, both participation rates NULL, both geography codes NULL. **MATCH**.
- Era 2 — 2021 grade 05, writing/level_4_expanding: bronze count=4463, pct=43.494786, published `Total Tested in Domain`=10261 (equals level sum 10261), total=10351, overall participation=93.143166, domain participation=92.333303 → gold 4463 / 0.43494786 / 10261 / 10351 / 0.93143166 / 0.92333303. **MATCH**.

**Other Step-4 items:**

- 4c sentinel year-attribution: the only year-bearing parsing is the filename regex plus the `_check_title_year` cross-check. Verified all 8 title rows directly from bronze — each embeds exactly the filename's year (e.g. `'Spring 2021 ACCESS for ELLs State Results'`, `'Spring 2024 WIDA ACCESS State Results'`; the `ACCESS for ELLs 2.0` substring in 2019/2020/2022/2023 titles cannot false-match the `20\d{2}` pattern). PASS.
- 4d aggregate-row reconciliation: N/A for derivation — the transform derives no district/state rows (all rows COME FROM bronze state aggregates; there is no finer level to reconcile against). The feasibility screen's analog here is the count-subset structure, verified directly in bronze: across all 8 files, every per-domain six-level count sum is ≤ the overall tested total (0 violations), and in 2021 the published `Total Tested in Domain` equals the level-count sum in every cell (0 mismatches). The contract's `count_ordering_chain` and `level_counts_sum_to_domain_denominator` checks enforce the same on gold and pass.
- 4e dedup tie-break: N/A — exactly one file per year (`files_processed`), no overlap years; collision guard runs before the defensive dedup.
- 4f suppression semantics: N/A — zero suppression markers in bronze (structure doc; validator `no_suppression_markers` pass). My independent reader summed every count/pct cell across all 8 files without encountering a single non-numeric or NULL cell — full-coverage positive evidence that the data is fully populated and a 0 is a real zero.

## Validation Cross-Read

- `_validation.json`: 19 pass / 0 fail / 0 warning, including `contract_parquet_schema`, `contract_quality_sql` (all 15 checks), `grain_uniqueness` on (`year`, `district_code`, `school_code`, `grade_level`, `domain`, `proficiency_level`), and `foreign_keys` (both geography FKs structurally NULL — "no populated keys").
- Contract `schema_hash`: `1942277f42b93ba7e255a2484148b54f5376553c1644ad09ba57f66b77f965c3`.
- §4b masking audit: transform declares no `_null_*` helpers (grep confirms none); manifest has no `masked_values` section; contract `limitations` and `null_meaning` properties document the only NULLs as structural (geography + 2021-only participation rates). Consistent — nothing unrecorded.
- §15b coverage judgment: the 5 authored quality checks cover this topic's real invariants well — level-count partition sum to the domain denominator, level shares summing to 1.0, the `num_at_proficiency_level ≤ num_tested_in_domain ≤ num_tested` ordering chain, the 2021-only co-presence of both participation rates, and the structural geography-NULL fact. A missing level row would be caught by the two partition-sum checks (unless its count were 0), and the transform's unpivot height assertion guarantees the full 13×8×6 cube at build time. No missing obvious invariant.
- v1 parity (executed this review):

```
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- Overlap years: none (one file per year) — dedup tie-break never engages.
- Cross-year NULL sweep: only `enrollment_tested_rate` and `enrollment_tested_in_domain_rate` flagged (~100% NULL in 2017–2020, 2022–2024) — exactly the documented Era-2-only metrics, enforced by the `participation_rates_2021_only` contract check. No era-localized rename signature on any other column (Risk 2 ruled out).
- Era-boundary continuity: per-year statewide tested totals from gold (summing unique per-grade `num_tested`) reproduce the structure doc's table exactly — 2017: 104,876; 2018: 115,639; 2019: 122,062; 2020: 129,551; 2022: 136,399; 2023: 144,036; 2024: 155,894 — all OK to the student. 2021 = 114,466 (consistent with the doc's Era-2 mean 8,805.1 × 13 grades), the expected COVID participation dip. Adjacent-year mean ratios for all count metrics sit between 0.88 and 1.20 — no >10x jumps, no cumulative-publication signature.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_require_column` raises for every expected flattened column; `_resolve_domain_labels` raises on zero/multiple matches per gold domain; duplicate-flattened-header guard; column arithmetic shows all 98/115 bronze columns consumed. |
| Era routing correctness | PASS | `detect_era_by_columns` keyed on the Era-2-only `Listening Domain \| Total Tested in Domain` signature; manifest shows 2021 → era_2, all others → era_1; verified that only the 2021 file carries those columns. |
| Filter logic logged + justified | PASS | 8 rows filtered, 2021 only, reason `non_grade_footnote_or_blank_rows`; verified row-by-row against raw bronze (footnotes/blanks/URL, zero data rows lost). |
| Normalization map completeness | PASS | 12/13/6 entries exactly match the structure doc's documented values; `bronze_values_seen` covers all; unmapped = 0 everywhere. |
| `strict=False` casts | PASS | Counts hop Float64→Int64 with `strict=False`; benign here — independent read confirms every metric cell in all 8 files is numeric (no strings/NULLs to silently null), and the contract marks the four core metrics `required: true` (validator would catch any null). |
| Dedup keys + tie-break | PASS (N/A in practice) | Collision guard (`assert_no_natural_key_collisions`) runs before dedup; one file per year makes duplicates impossible; documented defensive `sort_col`. |
| Year extraction | PASS | Filename `20\d{2}` token + title-row cross-check; all 8 titles verified to embed the matching year. |
| §5b unrecorded masks | PASS | No masks exist; none claimed; manifest and contract consistent. |

## Notes

- `schema_hash`: `1942277f42b93ba7e255a2484148b54f5376553c1644ad09ba57f66b77f965c3`; validation 19/19 pass, 0 warnings; manifest rows 4,992 = parquet rows; only `states.parquet` emitted per year (no empty district/school files), matching the structure doc's empty-file rule.
- The Corrections section's three claims were each independently re-verified: (1) 2021 has 8 non-data rows below the grade rows (not 4); (2) grade-in-demographic policy supersedes the doc's original `demographic` recommendation — gold uses `grade_level` (`k`, `01`..`12`), matching v1; (3) max six-level pct-sum deviation from 100.0 is 2.0e-06 (2017–2022 files; 2.84e-14 in 2023/2024) and 2021 published denominators equal level-count sums in every cell.
- Risk hypotheses 1, 4, 5, 6 are N/A for this topic (no demographic column, no derived aggregates, no overlap years); 2, 3, 7 affirmatively ruled out with executed evidence above.
- This topic's grain includes both always-NULL geography keys; the parquet NULL-key grain check and FK checks pass trivially but correctly.
