# Data Review: georgia_milestones_end_of_grade_eog_lexile_scores

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is byte-identical with the v1 baseline (**v1 parity MATCH**, verified via `compute_gold_sha256`). All 60,908 bronze rows land in gold 1:1 (zero filtered, zero read-loss, zero masks), all 10 categorical map entries are semantically correct, and every extreme-row and ordinary trace matched bronze byte-for-byte — including the headline `avg_lexile_score` max 1435.0 (2023 Elite Scholars Academy, 631/0114, g08) and min 300.0 (2022 State Schools district 799, g03). One required fix, documentation-only with zero data impact: the contract/docstring claim that pre-2021 empty metric fields exist "in the 2019 file" only is provably false — 2015–2018 each carry 126–136 fully-empty metric rows in raw bronze (the structure doc's Null Counts table of "0" for 2015–2018 is also wrong). The transform handles those rows correctly (empty → NULL); only the prose misattributes them.

## Manifest Verification

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| `detail_level` | 3 | 3 (State/District/School Level) | 0 | PASS |
| `grade_level` | 6 | 6 ("03"–"08") | 0 | PASS |
| `subject` | 1 | 1 (synthetic "English Language Arts") | 0 | PASS |

Full map review (every entry):

| Bronze | Gold | Correct? |
|---|---|---|
| `State Level` | `state` | YES — drives states.parquet + both-geo NULLing |
| `District Level` | `district` | YES — drives districts.parquet + school_code NULL |
| `School Level` | `school` | YES — both geography keys populated |
| `03`…`08` (6 entries) | `03`…`08` | YES — identity through `normalize_grade_column`; raw CSV bytes confirmed quoted zero-padded 2-char (e.g. 2017 line 1195: `..."03",208,207,98,1,634.8`); EOG covers grades 3–8 only |
| `English Language Arts` | `english_language_arts` | YES — constant; bronze has no subject column, Lexile exists only for EOG ELA; emitted for §16 sibling-topic filter parity |

- **2a Completeness**: every bronze value documented in the structure doc appears in `bronze_values_seen`; no documented value missing (no skipped era — all 9 files routed to `era_1_2015_2024`). PASS.
- **2b Correctness**: 100% of entries verified above. PASS.
- **2c Contract cross-check**: contract `grade_level` enum = `['03','04','05','06','07','08']` = `gold_values_produced`; `subject` enum = `['english_language_arts']` = produced. `detail_level` is dropped at export (filename-encoded) so it correctly has no contract property. PASS.
- **2d Unmapped**: 0 for all three. PASS.
- **2e Asian/PI conflation**: **N/A** — gold has no `demographic` column and no `pct_asian`-style column; bronze publishes no subgroup axis (grade-by-geography only).
- **2f Mutual exclusivity**: **N/A** — no demographic column; PASS by construction.

Row-count reconciliation (manifest `row_counts` vs structure doc vs parquet):

| Year | Bronze (doc) | Bronze (manifest) | Gold | Filtered | Factor |
|---|---|---|---|---|---|
| 2015 | 6,641 | 6,641 | 6,641 | 0 | 1.0 |
| 2016 | 6,664 | 6,664 | 6,664 | 0 | 1.0 |
| 2017 | 6,692 | 6,692 | 6,692 | 0 | 1.0 |
| 2018 | 6,741 | 6,741 | 6,741 | 0 | 1.0 |
| 2019 | 6,758 | 6,758 | 6,758 | 0 | 1.0 |
| 2021 | 6,768 | 6,768 | 6,768 | 0 | 1.0 |
| 2022 | 6,846 | 6,846 | 6,846 | 0 | 1.0 |
| 2023 | 6,881 | 6,881 | 6,881 | 0 | 1.0 |
| 2024 | 6,917 | 6,917 | 6,917 | 0 | 1.0 |
| **Total** | **60,908** | **60,908** | **60,908** | **0** | 1.0 |

Actual parquet row count (executed): **60,908** across 27 files (9 years × 3 detail levels), per-year counts identical to the table. 2020 absent as documented (COVID EOG suspension). Expansion factor uniformly 1.0 — no unpivot, no derived rows. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| SCHOOL_YEAR | `year` | MAPPED (filename year cross-checked against file content; mismatch raises) |
| DETAIL_LEVEL | — | CORRECTLY EXCLUDED (drives detail-level file split + geography nulling; dropped by `export_to_parquet`) |
| SCHOOL_DSTRCT_CD | `district_code` | MAPPED ("All" → NULL before zfill(3); 7-digit charter codes pass through) |
| SCHOOL_DSTRCT_NM | — | CORRECTLY EXCLUDED (dimension attribute) |
| INSTN_NUMBER | `school_code` | MAPPED ("All" → NULL before zfill(4)) |
| INSTN_NAME | — | CORRECTLY EXCLUDED (dimension attribute) |
| ACDMC_LVL_CD | `grade_level` | MAPPED (shared `normalize_grade_column`) |
| TOTAL_STUDENTS_TESTED | `num_tested` | MAPPED (canonical §16 name; structure doc's draft `students_tested` superseded) |
| STUDENTS_WITH_LEXILE | `num_with_lexile` | MAPPED (explicitly listed in §16 vocabulary) |
| LEXILE_ON_OR_ABOVE_MIDPOINT | `num_at_or_above_lexile_midpoint` | MAPPED (`_or_above` suffix per §16) |
| NO_LEXILE_SCORE | `num_without_lexile` | MAPPED (explicitly listed in §16 vocabulary) |
| AVG_LEXILE_SCORE | `avg_lexile_score` | MAPPED (`avg_` prefix per §16) |
| — | `subject` | Gold-only constant (`english_language_arts`), documented and justified per §16 sibling parity; not fabricated data |

No gold column lacks a bronze (or documented-constant) source; no fact_metric/fact_key from the structure doc is missing. The doc's draft gold names (`students_tested`, etc.) were correctly replaced by the canonical §16 vocabulary — `canonical_vocabulary` validation check passes.

## Value-Level Spot Checks

Extreme rows first (global max/min of every metric, located from manifest stats; bronze quoted verbatim):

| Trace | Bronze (file:line, quoted) | Gold | Verdict |
|---|---|---|---|
| `avg_lexile_score` global max 1435.0 | 2023.csv:2147 `2023,"School Level","631","Clayton County","0114","Elite Scholars Academy School","08","103","103","103","TFS","1435"` | 2023/631/0114/g08: tested=103, with=103, above=103, without=NULL, avg=1435.0 | MATCH (TFS→NULL; "1435"→1435.0) |
| `avg_lexile_score` global min 300.0 | 2022.csv:1254 `2022,"District Level","799","State Schools","All","All","03","11","11","TFS","TFS","300"` | 2022/799/school_code=NULL/g03: tested=11, with=11, above=NULL, without=NULL, avg=300.0 | MATCH (district-level "All"→NULL school_code) |
| `num_tested` global max 148,592 | 2023.csv:6882 `2023,"State Level","All","All","All","All","08","148592","133196","77933","555","1150.1"` | 2023/NULL/NULL/g08: 148592, 133196, 77933, 555, 1150.1 | MATCH (state sentinels→NULL) |
| `num_tested` global min 10 | 2015.csv:1150 `2015,"District Level","7991893","State Schools- Atlanta Area School for the Deaf","All","All","07",10,10,1,0,801.5` | 2015/7991893/NULL/g07: 10, 10, 1, 0, 801.5 | MATCH (7-digit code passes zfill unchanged) |
| `num_with_lexile` global max 137,222 | 2018.csv:6739 `2018,"State Level","All","All","All","All","05",137312,137222,75096,91,959` | 2018/NULL/NULL/g05: 137312, 137222, 75096, 91, 959.0 | MATCH (unquoted pre-2021 numerics) |
| `num_at_or_above…` global max 82,633 | 2019.csv:6759 `2019,"State Level","All","All","All","All","08",130838,124136,82633,6697,1185` | 2019/NULL/NULL/g08: with=124136, above=82633, without=6697, avg=1185.0 | MATCH (also matches structure-doc 2019 stats maxima) |
| `num_at_or_above…` global min 0 | 2015.csv:1421 `2015,"School Level","611","Bibb County","5054","Burghard Elementary School","04",40,40,0,0,576.6` | 2015/611/5054/g04: 40, 40, 0, 0, 576.6 | MATCH (zero preserved as real, not NULLed) |
| `num_without_lexile` global max 14,245 | 2021.csv:6769 `2021,"State Level","All","All","All","All","08","96991","82740","46410","14245","1136.2"` | 2021/NULL/NULL/g08: 96991, 82740, 46410, 14245, 1136.2 | MATCH |
| 2021 per-year `num_tested` max 97,390 (manifest) | 2021.csv:6764 `2021,"State Level","All","All","All","All","03","97390","96945","42256","605","629.3"` | 2021/NULL/NULL/g03: 97390, 96945, 42256, 605, 629.3 | MATCH |

Ordinary traces (single era; one from each suppression regime):

| Trace | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| 2017 Appling Co Elementary (pre-TFS regime) | 2017.csv:1195 `2017,"School Level","601","Appling County","0177","Appling County Elementary School","03",208,207,98,1,634.8` | 2017/601/0177/g03: 208, 207, 98, 1, 634.8 | MATCH (all 5 metrics) |
| 2024 Roberta T. Smith Elementary (TFS regime; structure-doc sample row) | 2024.csv:2206 `2024,"School Level","631","Clayton County","0200","Roberta T. Smith Elementary School","04","132","132","19","TFS","607"` | 2024/631/0200/g04: 132, 132, 19, NULL, 607.0 | MATCH |

Suppression / missing-value traces (4f):

| Trace | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| TFS marker (two columns in one row) | 2024.csv:5631 `…"721","Richmond County","3050","Bayvale Elementary School","04","57","57","TFS","TFS","611.3"` | 2024/721/3050/g04: 57, 57, NULL, NULL, 611.3 | MATCH — only the TFS cells are NULL, row preserved |
| Genuinely empty metric fields (pre-2021) | 2019.csv:782 `2019,"District Level","731","Taliaferro County","All","All","03",,,,,` | 2019/731/NULL/g03: all 5 metrics NULL, row preserved | MATCH |

Other Step 4 items:

- **4c Sentinel year-attribution**: N/A in the risky sense — no year-bearing data strings. `_resolve_year` cross-checks filename year against the file's single `SCHOOL_YEAR` value and raises on mismatch; every traced row's gold `year` equals the bronze `SCHOOL_YEAR` field. PASS.
- **4d Aggregates COME FROM BRONZE → feasibility screen (executed)**: per (year, grade), district `num_tested` sums cover 99.96–100.0% of the published state row in every year (suppression accounts for the deficit); **0 rows** where district sum exceeds state by >0.5% or state < max district; **0 districts** impossibly low vs their own schools (district < max school, or visible school sum >0.5% over district). No act_scores-style swap/garble signature. PASS.
- **4e Dedup tie-break**: N/A — one file per year, no overlap years (`files_processed` shows 9 distinct years), `grain_uniqueness` passes, and the collision guard runs before dedup.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning**, `passed: true`, timestamp fresh (2026-06-12T00:04:24Z, after manifest generation; transform mtime older). `contract_parquet_schema` (27 files), `contract_quality_sql` (all 10), `grain_uniqueness` (year, district_code, school_code, grade_level, subject), and `foreign_keys` (236 district keys, 1,968 school keys all resolve) all pass.
- The one warning is `null_rate_spikes` on `num_without_lexile` 2021–2024 (94.4%–99.4% vs 2.1% median) — explained: GOSA TFS suppression hits nearly every `NO_LEXILE_SCORE` cell from 2021 onward (bronze 2024: 6,870/6,917 cells are the literal `TFS`). Documented in the contract description, README notes, and the transform docstring. Not a defect.
- `schema_hash`: `971f8f1c82d6b245c78083940fd83a5c5f13c30c86c1051d6cc24a1426f20420`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no `masked_values` section (zero events — consistent); observed `avg_lexile_score` range 300.0–1435.0 sits inside the contract's enforceable [0, 2000] guard, and no negative counts exist. Intentionally-empty masked ledger is correct. PASS.
- **§15b coverage judgment**: authored checks cover the topic's real invariants — `lexile_counts_subset_chain` (above ≤ with ≤ tested) and `num_without_lexile_never_exceeds_num_tested`, both NULL-guarded, plus auto-derived non-negativity and the [0, 2000] score range. The obvious remaining candidate, the sum identity `with + without = tested`, is **correctly not authored**: I verified it fails in every year (2015: 403 violating rows, diffs −1…+326; … 2023: 20 rows, min diff **−15,807** on the state g05 row `TESTED=142160, WITH=126259, NO=94`; 2024: 26 rows, min −12,724) — matching the transform docstring's and contract caveat's exact figures. Authoring it would hard-fail valid published data. Coverage adequate. PASS.
- **v1 parity** (executed verbatim): `MATCH — byte-identical with v1 gold`.

## Cross-Era Consistency

- Single era (all 9 files share the identical 12-column header; manifest confirms identical `bronze_columns` per file). No overlap years; no era boundary.
- Cross-year NULL sweep (executed): only `FLAG num_without_lexile: ~100% NULL only in [2022, 2023, 2024]` (2021 sits at 94.4%, just under the 95% sweep cutoff but flagged by the validator) — the documented TFS regime, not a rename bug; all other columns populated in every year.
- YoY state-level continuity (executed): no >10x jumps and no revert-style level shift. 2021 participation dip (sum tested 571,111 vs ~780–800k in adjacent years) is the real COVID-recovery participation drop; mean state Lexile stable (918–958) across all years. The 2015–2019 raw lines are unquoted numerics, 2021+ quoted strings — the all-Utf8 read + `strict=False` cast absorbs both regimes, confirmed by the traces above.
- Sentinel convention verified in raw bytes: `grep -c '"ALL"'` = 0 in **all 9 files**; title-case `"All"` present in all 9 (1,170–1,304 occurrences/file). The transform's `BRONZE_ALL_SENTINEL = "All"` claim holds, and the NULLing happens before zfill (transform.py lines 299–307), so a padded sentinel cannot masquerade as a code.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_transform_era1` raises if any required bronze column is missing (rename-coverage guard) |
| Era routing | PASS | Single signature via `detect_era_by_columns`; unmatched header raises; all 9 files routed to `era_1_2015_2024` |
| Filter logic | PASS | No filters exist; bronze = gold = 60,908 (nothing to log) |
| Normalization map completeness | PASS | All 3 DETAIL_LEVEL literals, all 6 grades, 1 subject constant; unmapped → sentinel → manifest guard |
| `strict=False` casts | PASS | Applied only to the 5 metric columns after all-Utf8 read; converts TFS + empty fields to NULL; verified by traces |
| Dedup keys + tie-break | PASS | Collision guard before dedup; explicit `sort_col="num_tested"` documented as safety net (no duplicates exist; grain_uniqueness passes) |
| Year extraction | PASS | Filename year cross-checked against single in-file SCHOOL_YEAR; mismatch raises |
| §5b mask recording | PASS (N/A) | No masks; manifest ledger correctly absent |
| Risk 1 Asian/PI | N/A | No demographic axis in bronze or gold |
| Risk 2 rename-typo NULL year | PASS | Sweep flags only documented `num_without_lexile` suppression years |
| Risk 3 year attribution | PASS | See 4c |
| Risk 4 derived aggregation | N/A | All aggregate rows published by bronze; feasibility screen 0 violations |
| Risk 5 dedup inversion | N/A | No overlap years |
| Risk 6 mutual exclusivity | N/A | No demographic column |
| Risk 7 wrong mapping | PASS | 100% of map entries verified semantically (Step 2b) |

## Required Fixes

### Fix 1: Pre-2021 empty-field NULLs are misattributed to "the 2019 file" in contract prose and docstring
- **Severity**: LOW
- **Issue**: The contract and transform docstring claim genuinely-empty metric fields exist only in the 2019 bronze file, but every pre-TFS file (2015–2018) has them too. Executed raw-bronze count (`grep -c ',,,,,$'`): 2015 = 129, 2016 = 126, 2017 = 128, 2018 = 136, 2019 = 141 fully-empty metric rows — exactly matching the manifest's per-year null counts (e.g., 2015 `num_tested` null_count = 129; ~1.9–2.1% NULL in *every* pre-2021 year). Example: 2015.csv:1146 `2015,"District Level","7991893","State Schools- Atlanta Area School for the Deaf","All","All","03",,,,,`. The gold data is **correct** (empty → NULL, rows preserved); only the provenance prose is wrong. Affected prose: (a) contract `num_tested` description "NULL when suppressed (TFS, 2021+) or missing in the 2019 file"; (b) contract/README note "The 2019 file additionally has 141-143 genuinely empty metric fields"; (c) transform docstring "2015-2019 metric fields are pure numerics (2019 has 141-143 genuinely empty fields)"; (d) the per-column `null_meaning` ("Suppressed by GOSA (TFS…2021+)") which misattributes pre-2021 NULLs to suppression; (e) the structure doc's Null Counts table showing 0 nulls for 2015–2018.
- **Evidence**: `grep -c ',,,,,$'` per file (above) vs manifest `metric_stats` null counts: 2015: 129/131, 2016: 126/127, 2017: 128, 2018: 136/137, 2019: 141/143 — versus bronze-data-structure.md's Null Counts table claiming 0 for 2015–2018 and the contract's "missing in the 2019 file".
- **Location**: `_emit_contract_and_readme()` in transform.py (the `num_tested` description, the `notes` entry on suppression, and the `null_meaning` strings); module docstring; `bronze-data-structure.md` Null Counts section.
- **Suggested fix**: Reword to "missing/empty in the source in 2015–2019 (126–143 rows per year, ~2%)" in the `num_tested` description and the suppression note; extend `null_meaning` to "Suppressed by GOSA (TFS, 2021+) or empty in the pre-2021 source"; correct the structure doc's Null Counts table for 2015–2018. Description-only change — gold parquet is untouched, so v1 parity and the schema_hash-relevant fields are preserved (descriptions do not enter the schema_hash).

## Notes

- schema_hash: `971f8f1c82d6b245c78083940fd83a5c5f13c30c86c1051d6cc24a1426f20420`; validation 20 pass / 0 fail / 1 explained warning; manifest fresh (generated 2026-06-12T00:04:24Z), read_loss 0 events, masked_values absent.
- v1 parity: `MATCH — byte-identical with v1 gold` — the required fix above is prose-only and cannot perturb parity.
- The transform-agent's structure-doc corrections both check out: (1) the "one 3-digit school code in 2024" claim was indeed the `"All"` placeholder (doc note 6 now documents the awk field-length verification; raw bytes show only 4-char codes + the 3-char sentinel); (2) the sum-identity violation is correctly widened from "2019 only" to every year — my executed table: 2015: 403, 2016: 241, 2017: 149, 2018: 223, 2019: 160, 2021: 34, 2022: 31, 2023: 20 (min diff −15,807), 2024: 26 (min diff −12,724); largest overshoot +326 (2015 state g03).
- `num_without_lexile` retention despite ~99% post-2020 suppression is a sound, documented decision (pre-2020 comparability); structure-doc consideration #3 ("consider dropping") was resolved deliberately.
- 89 rows share the `num_tested` global min of 10 — consistent with GOSA suppressing cells below 10 (TFS era) and 10 being the smallest publishable count; min is 10 in every year for tested/with-lexile, while 0 remains a real (preserved) value for the two subset counts.
