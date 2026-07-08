# Data Review: ccrpi_progress

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

The transform is value-accurate: every spot check (12 extreme-row traces, ordinary traces in all three Era A label eras + Era B, suppression and sentinel traces) reproduced bronze exactly, all 27 categorical map entries are semantically correct, and row counts reconcile 1.00x in all 8 years (365,558 bronze = 365,558 gold, zero drops). **v1 parity: MATCH — byte-identical with v1 gold** (`bca02cd3…`, independently recomputed). Two minor fixes: (MEDIUM) two verified structural invariants are documented in contract prose but not enforced as quality SQL; (LOW) the contract's "Observed range 3.13-100" claim for `indicator_score` is wrong — the actual observed minimum is 0.0 (2021, bronze-verified). Neither fix touches the parquet, so parity is preserved.

## Manifest Verification

Preconditions: artifacts FRESH (transform mtime 12:53:15 < manifest 12:54:05 ≤ validation 12:54:05), `passed: true` (21/21, 0 warnings), `read_loss` 0 events (Excel whole-sheet reads, raw == parsed by construction). No `masked_values` / `reclassified` sections (absent = zero events).

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `demographic` | 13 (effective alias slice) | 14 labels (13 upper-keys) | 0 | PASS |
| `indicator` | 8 (7 Era A + 1 Era B implicit) | 8 | 0 | PASS |
| `grade_cluster` | 3 | 3 | 0 | PASS |
| `ccrpi_flag` | 3 | 3 | 0 | PASS |

**Full map review — every entry verified semantically:**

`demographic` (vs shared `DEMOGRAPHIC_ALIASES`, `src/utils/demographics.py:40-136`):

| Bronze (upper) | Gold | Correct? |
|---|---|---|
| ALL STUDENTS | all | ✓ unfiltered total |
| ASIAN/PACIFIC ISLANDER | asian_pacific_islander | ✓ explicit combined bucket (§5b — see 2e below) |
| ASIAN / PACIFIC ISLANDER | asian_pacific_islander | ✓ 2019 spacing variant, same bucket |
| AMERICAN INDIAN/ALASKAN | native_american | ✓ 2018 truncated variant (doc-confirmed) |
| AMERICAN INDIAN / ALASKAN NATIVE | native_american | ✓ 2019 spacing variant |
| AMERICAN INDIAN/ALASKAN NATIVE | native_american | ✓ 2023+ label |
| BLACK | black | ✓ |
| HISPANIC | hispanic | ✓ |
| WHITE | white | ✓ |
| MULTI-RACIAL | multiracial | ✓ |
| ECONOMICALLY DISADVANTAGED | economically_disadvantaged | ✓ |
| STUDENTS WITH DISABILITY | students_with_disabilities | ✓ (2019 lowercase-w collapses to same upper key) |
| ENGLISH LEARNERS | english_learners | ✓ |

`indicator` — all three concepts confirmed continuous series per the structure doc's label-drift table:

| Bronze (upper) | Gold | Correct? |
|---|---|---|
| ELA GROWTH | english_language_arts_growth | ✓ 2018 growth-explicit label |
| ENGLISH LANGUAGE ARTS | english_language_arts_growth | ✓ 2019+ label, same growth metric |
| MATHEMATICS GROWTH | mathematics_growth | ✓ 2018 |
| MATHEMATICS | mathematics_growth | ✓ 2019+ |
| ELP PROGRESS | progress_towards_elp | ✓ 2018 |
| PROGRESS TOWARDS LANGUAGE PROFICIENCY | progress_towards_elp | ✓ 2019/2020 |
| PROGRESS TOWARDS ENGLISH LANGUAGE PROFICIENCY | progress_towards_elp | ✓ 2023+ |
| PROGRESS TOWARDS ELP RATE | progress_towards_elp | ✓ Era B implicit (sheet has no Indicator column; composite rate = same ELP concept, structure doc "Era B band-movement metrics" section) |

`grade_cluster`: E→elementary, M→middle, H→high — ✓ all three. `ccrpi_flag`: G→green, Y→yellow, R→red — ✓ (§16 vocabulary; bronze `NA` = no flag → NULL on read; `G*` confirmed absent — gold enum has no green_star, manifest saw only G/R/Y).

- **2a Completeness**: every label in the structure doc's per-year tables (incl. 2018/2019 drift variants and 2025's "by Student Group" file) appears in `bronze_values_seen`; no documented value went unseen (no routing/skipped-era gap).
- **2c Contract cross-check**: `gold_values_produced` == contract `enum` for all four columns (10 demographics, 3 indicators, 3 clusters, 3 flags).
- **2d Unmapped**: 0 everywhere.

### 2e Asian / Pacific Islander conflation — PASS

Bronze ships a single explicit combined label in every year (`Asian/Pacific Islander`, 2019 `Asian / Pacific Islander`); grep of the structure doc confirms no separate Asian or Pacific Islander/NHPI row exists anywhere, and `bronze_values_seen` contains no bare `Asian`. Gold publishes only `asian_pacific_islander` — the correct §5b combined convention. Math test executed as positive evidence: `indicator_score: year=2025 total=509.5 race_sum=3149.82 ratio=6.1822 -> OK` (score metrics are averages, not counts, so the count-ratio test is structurally inapplicable — 6 race buckets of ~equal scores sum to ~6x the `all` score; the structural test governs and passes).

### 2f Demographic mutual exclusivity — PASS (single convention)

Gold enum contains the rollup `asian_pacific_islander` and never the split keys; no rollup/split overlap is possible.

**Row-count reconciliation** (manifest vs parquet, verified by direct count):

| Year | Bronze | Gold | Filtered | Factor |
|---|---|---|---|---|
| 2018 | 87,480 | 87,480 | 0 | 1.00 |
| 2019 | 65,898 | 65,898 | 0 | 1.00 |
| 2020 | 3,148 | 3,148 | 0 | 1.00 |
| 2021 | 2,674 | 2,674 | 0 | 1.00 |
| 2022 | 2,721 | 2,721 | 0 | 1.00 |
| 2023 | 67,452 | 67,452 | 0 | 1.00 |
| 2024 | 68,187 | 68,187 | 0 | 1.00 |
| 2025 | 67,998 | 67,998 | 0 | 1.00 |
| **Total** | **365,558** | **365,558** | 0 | 1.00 |

Actual parquet rows: 365,558 == manifest `total_gold` ✓. All 8 expected years present; tiny 2020-2022 years are the documented ELP-only COVID-era releases, matching bronze file row counts exactly.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| School Year | `year` (partition) | MAPPED — used for the per-file cross-check (`_check_sheet_year`), year itself from filename; verified equal in all 8 files |
| System ID | `district_code` | MAPPED — `ALL`→NULL, zfill(3), 7-digit charters untouched (traced `7830636`) |
| System Name | — | CORRECTLY EXCLUDED — dimension attribute; consumed for detail-level detection |
| School ID | `school_code` | MAPPED — `ALL`→NULL, zfill(4) (traced `103`→`0103` in 2023; pre-padded `0373` in 2021 unchanged) |
| School Name | — | CORRECTLY EXCLUDED — dimension attribute; consumed for detail-level detection |
| Grade Configuration | — | CORRECTLY EXCLUDED — school attribute (presence verified via `_require_columns`, then dropped) |
| Grade Cluster | `grade_cluster` | MAPPED |
| Reporting Label | `demographic` | MAPPED |
| Indicator (Era A) | `indicator` | MAPPED |
| Indicator Score (A) / Progress Towards ELP Rate (B) | `indicator_score` | MAPPED — continuous series across eras |
| Target (Era A) | `target` | MAPPED — typed NULL in Era B (no bronze column) |
| Flag (Era A) | `ccrpi_flag` | MAPPED — gold name `ccrpi_flag` (canonical per education conventions) supersedes the doc's suggested `flag` |
| No Positive Movement (B) | `pct_no_positive_movement` | MAPPED — ÷100; typed NULL in Era A |
| Moved Less Than One Band (B) | `pct_moved_less_than_one_band` | MAPPED — ÷100 |
| Moved One Band (B) | `pct_moved_one_band` | MAPPED — ÷100 |
| Moved More Than One Band (B) | `pct_moved_more_than_one_band` | MAPPED — ÷100 |

No gold column lacks a bronze ancestor (no fabrication). Rename maps are guarded by `_require_columns` per era — a missing bronze column raises instead of silently NULLing.

## Value-Level Spot Checks

All bronze values quoted below were read directly from the named xlsx files (pandas `dtype=str`).

**Extreme-row traces (4a):**

| # | Metric / extreme | Bronze (file, row, value) | Gold | Verdict |
|---|---|---|---|---|
| 1 | `indicator_score` global MIN 0.0 | 2021 file: King Middle School (761/0373, M): `Progress Towards ELP Rate = 0.00`, `No Positive Movement = 100.00` | (2021, 761, 0373, EL, middle): score 0.0, pct_no_pos 1.0, other bands 0.0 | MATCH — genuine bronze zero (100% no positive movement) |
| 2 | `indicator_score` global MAX 100.0 | 2018 file: sys 601, School ID `ALL`/All Schools, ALL Students, E, ELP Progress: `100` | (2018, 601, NULL, all, elementary, elp): 100.0 | MATCH |
| 3 | `target` global MIN 5.74 | 2024 file: Luella Middle (675/603, EL, M, ELP): `Target = 5.74`, `Flag = G`, score `24` | (2024, 675, 0603): target 5.74, flag green, score 24.0 | MATCH |
| 4 | `target` global MAX 90.0 | 2018 file: sys 603 district, EL, E, ELP Progress: `Target = 90`, `Flag = G`, score `100` | (2018, 603, NULL): target 90.0, flag green, score 100.0 | MATCH |
| 5 | `pct_no_positive_movement` MAX 1.0 | same row as #1: `100.00` | 1.0 | MATCH (÷100) |
| 6 | `pct_no_positive_movement` MIN 0.0 | 2021: Nicholls Elementary (634/0291, E): `0.00` | 0.0 | MATCH |
| 7 | `pct_moved_less_than_one_band` MAX 0.5294 | 2021: Glenn Hills Elementary (721/2054, E): `52.94` | 0.5294 | MATCH |
| 8 | `pct_moved_less_than_one_band` MIN 0.0 | 2021: sys 610 district E (School ID `ALL`): `0.00` | 0.0 (district row, school_code NULL) | MATCH |
| 9 | `pct_moved_one_band` MAX 0.55 | 2021: C. B. Watson Primary (676/0102, E): `55.00` | 0.55 | MATCH |
| 10 | `pct_moved_more_than_one_band` MAX 0.9333 | 2021: Parkway Elementary (636/0398, E): `93.33`, ELP Rate `100.00+` | 0.9333, score 100.0 | MATCH (overage → 100) |
| 11 | overage marker arithmetic, 2023 | 2023 file: `100.00+` count = **4,131**; literal-100 count = **251** | gold 2023 score==100 count = **4,382** = 4,131 + 251 | MATCH — exact |
| 12 | overage counts, Era B | 2021: 202 `100.00+`; 2022: 466 (both in ELP Rate) | traced 2021 601/0177 E `100.00+` → 100.0 | MATCH (counts == doc == contract) |

**Ordinary traces (4b), one per label-era:**

- **2018** (growth-explicit labels): rows #2, #4 above — score/target/flag all match, `ALL` School ID → NULL.
- **2019** (mid-era labels, spaced slashes): state `Asian / Pacific Islander` E: bronze ELA `97.18` / Math `98.64` → gold (2019, NULL, NULL, asian_pacific_islander, elementary) 97.18 / 98.64. Haymon-Morris Middle (607/0106, EL, M, `Progress Towards Language Proficiency`): bronze `63.33` / Target `64.51` / Flag `Y` → gold 63.33 / 64.51 / `yellow`. MATCH.
- **2020** (Era A layout, ELP-only): state rows E/H/M bronze `100` / `65.86` / `52.78` → gold 100.0 / 65.86 / 52.78, target & flag NULL (bronze publishes neither — 0 non-null in whole file). MATCH.
- **2022** (Era B): DeKalb 644 district E: bronze `19.63 / 15.86 / 24.87 / 39.64 / 92.26` → gold 0.1963 / 0.1586 / 0.2487 / 0.3964 / 92.26. MATCH.
- **2024** (Era A current): Wilcox County Elementary (756/195, SWD, Math, E): bronze `78.96`, Target `NA`, Flag `NA` → gold 78.96, NULL, NULL. MATCH.

**4c Sentinel year-attribution**: N/A in the risky sense — the only year literals are the `SHEET_NAME_BY_YEAR` config keys. `year` derives from the filename and `_check_sheet_year` raises if the sheet's `School Year` values disagree (verified: 2021's String-typed `School Year` column traced to gold year 2021). PASS.

**4d Aggregate feasibility screen** (aggregates COME FROM BRONZE): state rows vs district ranges — **0 of 327** state rows fall outside their districts' [min, max]. District rows vs school ranges: 3,213 of 38,737 (8.3%) fall outside the *visible* school range, but the rate is a monotone function of suppression — 13.3% where only 1 school row is visible, 3.5% at 2-3, **0.14% at 4+** — the classic suppression signature, not a swap. Provably bronze-faithful at the worst case: 2024 Columbia County (636, EL, H, Math) district `80.2` vs lone visible school Grovetown `31.26` — bronze shows the other four schools (Harlem, Lakeside, Greenbrier, Evans) all `TFS`. The published aggregate covers suppressed students; gold transcribes it exactly. PASS — no fix.

**4e Dedup tie-break**: N/A — one file per year, no overlap years; collision guard (`assert_no_natural_key_collisions`) runs before the defensive dedup and validation confirms grain uniqueness.

**4f Suppression semantics**: 2024 charter 7830636 (district row, Asian/PI, H, Math): bronze `Indicator Score = TFS` → gold NULL. 2022 Brookhaven Innovation Academy (7830613/613, M): all five metrics `TFS` → gold all NULL (and the all-or-nothing pattern is contract-enforced). Bronze `NA` (Target/Flag) → NULL via the suppression-aware read. MATCH.

## Validation Cross-Read

- `_validation.json`: **21/21 pass, 0 fail, 0 warnings** — `contract_parquet_schema` (24 files), `contract_quality_sql` (all 18), `grain_uniqueness` (6-col grain), `foreign_keys` (242 districts, 2,411 schools, 10 demographics all resolve), geography nulling ×3 all pass.
- `schema_hash`: `97f8971a4768c786f30a0f203f97d4c5a4677bce2a4a71dc5d3f4b1939402662`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no `masked_values` section — consistent with the docstring's "No §4b masks" claim. The only value rewrite is `100.00+`→100 (a defined-marker decode, not a mask), recorded in the contract description and verified arithmetically (trace #11). PASS.
- **§15b coverage judgment**: the 7 authored invariants (band partition-to-one, all-or-nothing suppression, Era-B-only bands, target/flag ELP-only, target/flag EL-only, target/flag absent 2020-2022, ELP-only-years EL-only) are real, bronze-verified, and well-formed. Two equally obvious, contract-documented invariants are NOT enforced — see Fix 1.
- **v1 parity** (verbatim):

```
current: bca02cd31bbc80add50c77835a61c87feb9dcc08dae147d9d28b4348c9c6af6c
v1     : bca02cd31bbc80add50c77835a61c87feb9dcc08dae147d9d28b4348c9c6af6c
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **No overlap years** (each year ships exactly one file; eras non-contiguous A|B|A by design).
- **Cross-year NULL sweep**: band `pct_*` columns ~100% NULL in all six Era A years (structural — columns exist only in the 2021-2022 schema; contract-enforced). `target`/`ccrpi_flag` ≥95% NULL in *every* year — resolved as structurally sparse, not a rename bug: per-year non-null counts match bronze exactly (target 1,234 / 1,350 / 0 / 0 / 0 / 1,572 / 1,677 / 1,706; flag 1,201 / 1,293 / 0 / 0 / 0 / 1,516 / 1,599 / 1,649 — 2024 flag split green 1,136 / red 422 / yellow 41 == bronze G/R/Y counts; 2018 flag 1,201 == structure-doc Corrections).
- **Era-boundary continuity** (state ELP series): E 100.0→100.0→100.0→81.05→96.95→98.99→…, H 78.26→…→65.86→60.07→60.61→56.55→…, M 65.47→…→52.78→43.80→56.46→50.47→… — continuous across both A→B (2020→2021) and B→A (2022→2023) boundaries; the 2021 dip is the COVID-era trough, no scale break. No >10x jumps in any adjacent year pair of any metric; means 81.99→81.63→81.74→69.91→79.31→81.61→82.72→82.26 for `indicator_score` (the 2021 dip reflects the ELP-only composition + COVID).
- 2018's 10-demographic ELP coverage vs EL-only from 2019 on matches the structure doc's Corrections section exactly (gold 2018 ELP rows span 10 demographics; 2019+ ELP rows are EL-only — 0 counterexamples).

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_require_columns` guards every expected bronze column per era; excluded columns are deliberate dimension attributes |
| Era routing correctness | PASS | Signature-based (`detect_era_by_columns`), most-specific-first, raises on no-match; manifest shows correct era per file |
| Filter logic | PASS | No filters; 0 rows dropped, ledger empty |
| Normalization map completeness | PASS | All structure-doc label variants covered (manifest `bronze_values_seen` ⊇ doc tables); `replace_strict(default=None)` + manifest unmapped guard backstops drift |
| `strict=False` casts | PASS (note) | Applied only after suppression markers are nulled at read and `100.00+` is decoded; structure doc confirms no other non-numeric values exist; null-rate spike check is the runtime backstop |
| Dedup keys + tie-break | PASS | Defensive only (0 duplicate groups); collision guard raises *before* dedup so divergent duplicates can never be silently averaged away |
| Year extraction | PASS | Filename year cross-checked against the sheet's `School Year` per file; raises on mismatch |
| §4b masks (5b) | PASS | None exist, none needed (all values within scale after overage decode) |

## Required Fixes

### Fix 1: Author quality checks for the two verified-but-unenforced structural invariants
- **Severity**: MEDIUM
- **Issue**: Two invariants stated in the contract's own column descriptions are not enforced by quality SQL, while their exact structural siblings are. (a) The ELP-only releases (2020-2022) contain only the `progress_towards_elp` indicator — the authored `elp_only_years_english_learners_only` enforces the *demographic* scope of those years but not the *indicator* scope, so a 2020 row mislabeled `mathematics_growth` would pass every current check. (b) From 2019 on, ELP-indicator rows exist only for `english_learners` (contract `demographic` description: "ELP rows cover all 10 groups in 2018 but only english_learners from 2019 on") — unenforced.
- **Evidence**: Both invariants verified to hold in current gold: `2020-2022 rows with non-ELP indicator: 0`; `2019+ ELP rows with non-EL demographic: 0` (and 2018 ELP rows span exactly 10 demographics, matching the structure doc's Corrections). Neither condition appears in the contract's `quality` list (18 checks reviewed).
- **Location**: `_emit_contract_and_readme()` → `quality_checks=` list in `src/etl/education/georgiainsights/ccrpi_progress/transform.py`
- **Suggested fix**: Add two checks: `elp_only_years_elp_indicator_only` — `SELECT COUNT(*) FROM {object} WHERE year IN (2020, 2021, 2022) AND indicator <> 'progress_towards_elp'` mustBe 0; and `elp_rows_english_learners_only_post_2018` — `SELECT COUNT(*) FROM {object} WHERE year IN (2019, 2023, 2024, 2025) AND indicator = 'progress_towards_elp' AND demographic <> 'english_learners'` mustBe 0 (year-pinned like the existing `target_flag_absent_2020_through_2022`, so a legitimate future re-expansion of ELP demographic coverage cannot break the pipeline; 2020-2022 are already covered by `elp_only_years_english_learners_only`). Re-run the transform — gold parquet is unchanged, so v1 parity is preserved.

### Fix 2: Correct the `indicator_score` observed-range prose (contract description + docstring)
- **Severity**: LOW
- **Issue**: The contract's `indicator_score` description ends "Observed range 3.13-100." and the transform docstring claims "scores and targets within [3.13, 100] / [5.74, 90]". The actual global observed minimum of `indicator_score` is **0.0**, not 3.13 (3.13 is only the Era A / 2023 minimum; the manifest's own 2021 stats record `min_val: 0.0`). The target range 5.74-90 is correct.
- **Evidence**: Gold (2021, '761', '0373', english_learners, middle): `indicator_score = 0.0`; bronze 2021 file, King Middle School: `Progress Towards ELP Rate = 0.00` with `No Positive Movement = 100.00` — a genuine published zero, well inside the declared [0, 100] bounds.
- **Location**: `_emit_contract_and_readme()` `indicator_score` column description, and the module docstring "No §4b masks" bullet, in `src/etl/education/georgiainsights/ccrpi_progress/transform.py`
- **Suggested fix**: Change the description to "Observed range 0-100 (minimum 0.0 occurs in the 2021 Era B composite rate; Era A minimum 3.13)" and fix the docstring bullet accordingly. Prose-only — parquet bytes and parity unaffected.

## NEEDS_JUDGMENT

None — every suspicion raised during the review was resolved with bronze evidence (the 4d out-of-range district aggregates are bronze-faithful suppression artifacts; the 3c NULL flags are era-structural and count-verified against bronze).

## Notes

- `schema_hash`: `97f8971a4768c786f30a0f203f97d4c5a4677bce2a4a71dc5d3f4b1939402662`; validation 21 pass / 0 fail / 0 warning; contract quality checks: 18 (11 auto-derived + 7 authored).
- v1 parity MATCH (`bca02cd31bbc80add50c77835a61c87feb9dcc08dae147d9d28b4348c9c6af6c`), independently recomputed in this review.
- Structure-doc nuance (gold unaffected): under the transform's pandas `dtype=str` read, the 2019 and 2020 state rows carry the literal `ALL` in `System ID` (and 2019 in `School ID`), whereas the doc's ID-encoding table — written from polars-native reads — records them as null. Both encodings funnel through the same `ALL`→NULL/null path in `_apply_detail_level_and_ids`, and `null_aggregate_geography` + the validator's geography_nulling check guarantee the result either way; all traced state/district rows have correctly NULL geography.
- The `100.00+` ceiling decode is exactly verified: 2023 gold score==100 count (4,382) equals bronze `100.00+` (4,131) + literal-100 (251); Era B overage counts (202 / 466) match the structure doc and contract.
- 2020-2022 are tiny years by design (ELP-only COVID-era releases: 3,148 / 2,674 / 2,721 rows) — counts equal their bronze files exactly.
