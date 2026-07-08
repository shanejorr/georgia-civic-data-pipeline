# Data Review: educator_qualifications_inexperienced_teachers_leaders

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

No required fixes. All 19 documented drops replayed exactly from bronze; both categorical maps are 100% verified; every extreme and ordinary trace matches bronze byte-for-byte; validation is 21/21 with zero warnings. v1 parity is **DIFFERS — explained**: the full-row null-safe anti-join decomposes into exactly four 2023–2024 entity-attribution decisions (Coweta Charter 7830601→7830610, Coastal Middle 0198→0311, Oakhurst 0103→0105, Barrow Arts 2023 dropped as a genuine cert-personnel ambiguity), metric tuples byte-identical on both sides, net −3 rows; all four new attributions are better-evidenced than v1's (verified against cert_personnel 2023/2024 and the dimensions). Two judgment items: GOSA's `inexperienced_fte` is **non-additive up the hierarchy for Teachers** (district sums exceed the state row by 1.38–1.49x in every year while `total_fte` reconciles to ≈1.000 — bronze-native, undocumented in the contract), and the 2018–2019 source era carries level anomalies (2019 statewide Teachers FTE ≈1.4x adjacent years; 149 districts in 2018 where school FTE sums exceed the district row).

## Manifest Verification

Preconditions: FRESH (transform mtime 17:31:12 < manifest 17:31:38 ≤ validation 17:31:38); `passed: true`; read_loss events: 0.

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| role | 2 | 2/2 | 0 | PASS |
| poverty_subgroup | 5 | 5/5 | 0 | PASS |

Full map review (every entry):

| Bronze | Gold | Correct? |
|---|---|---|
| Teachers | teachers | YES — LABEL_LVL_3_DESC workforce role, snake_case |
| Leaders | leaders | YES — principals/assistant principals per structure doc |
| Total | total | YES — all schools in entity |
| High Poverty | high_poverty | YES — highest-poverty quartile stratum |
| Low Poverty | low_poverty | YES — lowest-poverty quartile stratum |
| Not Applicable | not_applicable | YES — Leaders-only stratum, faithfully preserved (not coerced to NULL or dropped) |
| Unknown | unknown | YES — Leaders-only, chiefly Dept. of Juvenile Justice facilities |

- **2a completeness**: structure doc documents exactly `Teachers`/`Leaders` and the 5 poverty labels; `bronze_values_seen` covers all of them, no documented value unseen.
- **2c contract cross-check**: `gold_values_produced` == contract `enum` for both columns == distinct values in gold parquet (verified by query).
- **2d**: `unmapped_count` 0 for both.
- **2e Asian/PI conflation**: **N/A** — no `demographic` column and no `pct_asian`-style column; `poverty_subgroup` is a school-poverty stratum, not a student demographic.
- **2f mutual exclusivity**: **N/A** for demographics. The `total` stratum overlaps its sub-strata by design; this is documented in the contract and bounded by the `aggregate_poverty_strata_within_total` and `school_role_single_poverty_stratum` quality checks.

Row-count reconciliation (manifest `by_year` vs gold parquet — parquet re-counted: 45,093 == manifest `total_gold`):

| Year | Bronze | Filtered | Gold | Parquet | Check |
|---|---|---|---|---|---|
| 2018 | 6,395 | 0 | 6,395 | 6,395 | ✓ 1:1 |
| 2019 | 6,427 | 0 | 6,427 | 6,427 | ✓ 1:1 |
| 2020 | 6,435 | 0 | 6,435 | 6,435 | ✓ 1:1 |
| 2021 | 6,448 | 0 | 6,448 | 6,448 | ✓ 1:1 |
| 2022 | 6,460 | 0 | 6,460 | 6,460 | ✓ 1:1 |
| 2023 | 6,485 | 15 | 6,470 | 6,470 | ✓ |
| 2024 | 6,462 | 4 | 6,458 | 6,458 | ✓ |

**Drop-ledger replay (19 drops, re-derived from bronze through the transform's own functions; every class matches the manifest):**

- `source_gap_district` (4, all 2023): Foothills Charter High School truncated aggregate ×2 (`TFS/TFS/TFS` Leaders + `TFS/TFS/54` Teachers) and Ivy Prep Kirkwood truncated aggregate ×2 (`TFS/TFS/80` Leaders + `29/16/55` Teachers). **Neither drop loses unique signal**: the kept school rows mirror the dropped aggregates — Foothills 7820613/0613 Teachers Total rate 0.54 (= dropped aggregate's 0.54) and Ivy Prep 7820612/0612 Teachers Total `29.0/16.0/0.55` (= dropped aggregate's values; bronze `"State Charter Schools-","Ivy Preparatory Academy, Inc","Teachers","Total","29","16","55"` resolves year-aware via cert_personnel 2023 `"7820612","0612"`).
- `force_drop_ambiguous_truncated_district_aggregate` (7: 4 in 2023, 3 in 2024): all under the 52-char `"State Charter Schools II- Genesis Innovation Academy"` label whose Boys/Girls distinguisher was erased; replay confirms it resolves arbitrarily to 7830615 and the 2023 Teachers pair carries DIVERGENT tuples (`31.1/23.1/0.74` vs `29.6/17.6/0.6` — two different campuses), so keeping a winner would mis-attribute one campus's data. The bare Genesis Boys/Girls school rows are present in gold.
- `source_gap_school` (7, all 2023): Barrow Arts and Sciences Academy ×3 (cert_personnel 2023 publishes BOTH `607/0300` and `607/0309` under that name — genuinely ambiguous; 2021, 2022, 2024 rows resolve to 0300 and are kept in gold), Lindley 6th Grade Academy ×2 and Lumpkin County Elementary School ×2 (both names absent from cert_personnel 2023, present and resolved in 2018–2022 — unresolved-only predicate semantics verified).
- `duplicate_rows_deduped` (1, 2024): the truncated Utopian Academy Leaders/Total pair — two campuses (7820121 + Trilith 7820619) collapsed onto the pinned 7820121 with IDENTICAL tuples `(NULL, NULL, 1.0)`; dedup removes 1 redundant row. Verified the only surviving-duplicate group post-force-drop.

Per-detail-level reconciliation against the structure doc's table: 2023 districts 637 + 138 reclassified − 8 dropped = 767 ✓; schools 5,842 − 138 − 7 = 5,697 ✓; 2024 districts 744 + 60 − 3 − 1 = 800 ✓; schools 5,712 − 60 = 5,652 ✓. Reclassified events re-derived from bronze: 2023 = 38 suffix-restore + 100 hybrid (manifest: 38/100 ✓); 2024 = 20 + 40 ✓.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| #CATEGORY_DESC (Era 1) | — | CORRECTLY EXCLUDED — constant `Inexperienced`, asserted before drop |
| LONG_SCHOOL_YEAR | year | MAPPED (ending year via parse_school_year) |
| SCHOOL_DSTRCT_NM | district_code | MAPPED (name→code via shared resolver); name itself is a dimension attribute |
| INSTN_NAME | school_code | MAPPED (name→code, composite); name itself is a dimension attribute |
| LABEL_LVL_3_DESC | role | MAPPED |
| LABEL_LVL_2_DESC | poverty_subgroup | MAPPED |
| FTE | total_fte | MAPPED (Float64, strict=False) |
| INEXPERIENCED_FTE / CATEGORY_FTE | inexperienced_fte | MAPPED (both eras harmonized) |
| INEXPERIENCED_FTE_PCT / CATEGORY_FTE_PCT | inexperienced_fte_rate | MAPPED (÷100 to 0-1). Structure doc suggested `inexperienced_fte_pct`; the transform's `_rate` name follows canonical vocabulary §16 (no `_pct` on a 0-1 rate) — deliberate improvement, validator vocabulary check passes |

No gold column lacks a bronze source (no fabrication). No unhandled conditional columns; the missing-metric-column guard in `_transform_era` raises rather than NULLing a year.

## Value-Level Spot Checks

Extreme rows first (per-metric global max/min from manifest stats):

| Trace | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| total_fte global max (2019 state Teachers Total) | `"2018-19","State of Georgia","All Georgia Schools","Teachers","Total",162256.2,46940,29` | (2019, NULL, NULL, teachers, total, 162256.2, 46940.0, 0.29) | MATCH (also inexperienced_fte global max) |
| total_fte / inexperienced_fte / rate global min — true zero (2018 Marietta City, Hartmann Center) | `"2017-18","Marietta City","George W. Hartmann Center","Leaders","Low Poverty",0,0,0` | (2018, 781, 0207, leaders, low_poverty, 0.0, 0.0, 0.0) | MATCH — true zero preserved, not nulled |
| rate global max 1.0 + the +0.1 rounding artifact (2018 Randolph County, Randolph Clay HS) | `"2017-18","Randolph County","Randolph Clay High School","Leaders","High Poverty",1.9,2,100` | (2018, 720, 0201, leaders, high_poverty, 1.9, 2.0, 1.0) | MATCH — numerator > denominator by exactly 0.1, preserved per §4b |
| 2021+ floor min 10.0 | bronze 2021–2024 publish no numeric below 10 (TFS below floor; structure doc) | manifest min_val = 10.0 for all metrics 2021+ | MATCH — consistent with TFS reporting floor |

`inexperienced_fte > total_fte` count in gold = **6** (2018: 720/0201; 2019: 7830612 district + 7830612/0612; 2020: 615/0502, 629/3058, 706/0502), all Leaders, all +0.1 exactly — matches the contract's documented six rows and the 0.15 quality-check tolerance.

Ordinary traces (one per era, all columns):

- **Era 1, 2024** — Holsenbeck Elementary School (Barrow County 607/4050): bronze `"Teachers","Total","58.2","28.1","48"` → gold (58.2, 28.1, 0.48) MATCH; bronze `"Leaders","Not Applicable","TFS","TFS","48"` → gold (NULL, NULL, 0.48) MATCH (independent per-cell suppression preserved).
- **Era 2, 2022** — Jones-Wheat Elementary School (Decatur County 643/4052; dim name "Jones-Wheat Primary School"): bronze `"Teachers","Total","39.6","15.6","39"` and `"Teachers","High Poverty","39.6","15.6","39"` → gold (39.6, 15.6, 0.39) ×2 MATCH (school stratum mirrors total, per quality check); `"Leaders","High Poverty","TFS","TFS","TFS"` → (NULL, NULL, NULL) MATCH.
- **Truncation-repair resolution spot checks (2023)**: hybrid-rescued `"State Charter Schools II- Atlanta Heights Charter Sc"` → district aggregate 7830410 (school_code NULL), values identical to its single school row 7830410/0410 (31.3/13.3/0.42) — exactly the single-school-district equivalence the resolver rationale predicts; cert_personnel 2023 confirms `"7830410","0410"`. The 52-char school-name rows matching neither repair branch (SAIL ×3 2023, ×1 2024; Foothills Central Office ×2 2023) resolved as school rows — SAIL → 7830618/0618 (bronze Teachers 37 FTE → gold 37.0; cert_personnel `"7830618","0618"`), Foothills Central Office → 7820613/0613 (TFS rows → NULLs, rate 0.54 preserved).

Other Step 4 items:

- **4c sentinel year-attribution**: `LONG_SCHOOL_YEAR` is authoritative; 2023 file carries `2022-23` → gold year 2023; all six 2023 state rows match the 2023 file's bronze values (e.g. Leaders Total 6653.5/2242/0.34). PASS.
- **4d feasibility screen** (aggregates come from bronze): state `total_fte` vs sum of district rows reconciles at 0.999–1.001 in every Teachers year and 1.000–1.002 for Leaders pre-suppression (2021+ Leaders visible-sum ratios 0.71–0.76 are explained by TFS suppression of small district Leaders rows — state ≥ visible sum, the legitimate direction). The impossibly-LOW screen on `inexperienced_fte` fired broadly → bronze-native non-additivity, see Judgment Call 1. district `total_fte` < school-row sum in 166 role-district-years, 149 of them in 2018 → see Judgment Call 2.
- **4e dedup tie-break**: no year is covered by two eras (each year = one file) → cross-era N/A. The single within-year dedup event verified above (identical tuples; collision guard ran per detail level before dedup, so a divergent pair could not be silently collapsed).
- **4f suppression semantics**: TFS → NULL traced (Paulding County HS 2022, `"Leaders","Not Applicable","TFS","TFS","17"` → NULL/NULL/0.17); true zero preserved (Hartmann Center above). Only one marker type (`TFS`) exists in this topic.

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning** — `contract_parquet_schema`, `contract_quality_sql` (13 checks), `grain_uniqueness`, `foreign_keys` (241 district keys, 2,396 school keys) all pass.
- `schema_hash`: `97f942f22b6bb4ed8c400d5006fa87998929f352b6c65529faec9cd00e51b4dc`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; no `masked_values` section in the manifest — consistent (zero masks claimed, zero applied). The bronze percent range 0–100 and non-negative FTEs were re-verified by the contract's range checks. The six +0.1 rows are preserve-and-document, with the contract range guard (`inexperienced_fte_within_total_fte`, +0.15 tolerance) keeping the invariant enforceable. PASS.
- **§15b coverage judgment**: 7 authored cross-column checks (numerator-within-denominator, rate reconciliation scoped ≥10 FTE, school stratum mirrors total, single non-total stratum per school-role, Teachers never not_applicable/unknown, HP+LP within total +0.55, exactly 6 state rows/year) — covers the real invariants. A hierarchy-additivity check is correctly NOT authored: the data does not satisfy it (Judgment Call 1). Adequate.
- **v1 parity output (verbatim)**:

  ```
  DIFFERS from v1
    v1:  b8212c9fd819f87366b26294c9db805d93e312bb1b112ebfffcabff99c743724
    now: b47e0ac6839a42ae7a1d8a52636cb9509a74be1e1c6972674cc9a0932060ee9e
  ```

  The read-only S3 snapshot at `/tmp/v1gold_s3/` re-hashes to `b8212c9f…` — exactly the baseline. Null-safe full-row anti-join (NULL keys/metrics filled with sentinels before joining): v1 45,096 rows, new 45,093 (net −3); **20 rows only-in-v1, 17 only-in-new**, decomposing into exactly four clusters with metric tuples byte-identical across the re-keyed pairs:

  1. **Coweta Charter Academy truncated district aggregate** (6 rows, 2023+2024): v1 → 7830601, new → 7830610. The districts dim carries name-twin rows for both codes; only 7830610 has a school (0610), and cert_personnel 2023+2024 publish ONLY `"7830610","0610"` — v1's 7830601 is a school-less twin. New attribution sound.
  2. **Coastal Middle School** (5 rows, 625): v1 → 0198, new → 0311. Schools dim has both; cert_personnel 2023 and 2024 publish uniquely `"625","0311","Coastal Middle School"`. Sound.
  3. **Oakhurst Elementary School** (6 rows, 773): v1 → 0103, new → 0105. cert_personnel 2023+2024 publish uniquely `"773","0105"`. Sound.
  4. **Barrow Arts and Sciences Academy 2023** (3 rows): v1 → 607/0300, new → dropped as `source_gap_school`. cert_personnel 2023 publishes BOTH `607/0300` and `607/0309` under the same name — v1's 0300 bind was arbitrary. 2021/2022/2024 rows (where cert_personnel is unambiguous) remain at 0300 in gold. Sound, at the cost of a documented 1-year coverage gap. This is the same predicate the PASS-reviewed emergency sibling uses.

  Verdict: **DIFFERS — explained and justified**; the divergences are year-aware-resolution improvements over v1's static binds, with zero metric-value changes.

## Cross-Era Consistency

- No overlap years between eras (Era 1 = 2023–2024 files, Era 2 = 2018–2022 files; one file per year; manifest `files_processed` confirms routing).
- Cross-year NULL sweep: no era-localized ~100%-NULL columns; no column NULL in every year. The per-year NULL-rate step change at 2021 (0% → ~40–53% on FTE metrics) is the documented suppression-policy boundary, not a rename bug — null counts match the structure doc's TFS counts exactly (e.g. 2022: 2,597/3,415/957).
- Era-boundary continuity at 2022→2023 (Era 2→Era 1) is smooth (state Teachers Total 104,530 → 113,417 → 113,555; Leaders 6,574 → 6,654 → 6,866); the metric-pair rename (`INEXPERIENCED_FTE` → `CATEGORY_FTE`) harmonized correctly.
- The notable discontinuities are *within* Era 2 at the source level (2019 level shift; 2018 school-sum excess) — see Judgment Call 2.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `#CATEGORY_DESC` asserted constant before drop; missing metric columns raise |
| Era routing | PASS | Column-signature detection; manifest confirms 5×Era 2 + 2×Era 1 |
| Filter logic logged + justified | PASS | All 19 drops logged, manifest-recorded, replayed exactly; residual-unresolved guard RAISES on anything outside documented predicates (replay confirmed zero residuals) |
| Normalization map completeness | PASS | Both maps cover all bronze values; sentinel default would fail manifest.write() on new values |
| `strict=False` casts | PASS | All-string read; only non-numeric is TFS (per structure doc); true zeros survive |
| Dedup keys + tie-break | PASS | Per-detail-level collision guard before dedup (NULL-safe by construction); `sort_col="inexperienced_fte"` documented; only identical-tuple duplicates reached dedup |
| Year extraction | PASS | `LONG_SCHOOL_YEAR` ending year authoritative, filename cross-checked |
| §5b masking audit | PASS | No masks; none needed (bronze ranges verified) |
| Risk 1 Asian/PI | N/A | No demographic column |
| Risk 2 rename-NULL | PASS | NULL sweep clean |
| Risk 3 year attribution | PASS | Traced 2023 |
| Risk 4 aggregation | NEEDS_JUDGMENT | Aggregates are bronze-published, transform derives none; bronze hierarchy is non-additive for Teachers `inexperienced_fte` (Judgment Call 1) |
| Risk 5 dedup inversion | PASS / N/A | No overlap years; single dedup event identical-tuple |
| Risk 6 mutual exclusivity | N/A | No demographic column |
| Risk 7 wrong mapping | PASS | All 7 entries semantically verified |

## NEEDS_JUDGMENT

### Judgment Call 1: Teachers `inexperienced_fte` is non-additive across hierarchy levels — undocumented interpretive trap
- **Severity if confirmed**: MEDIUM
- **Suspicion**: GOSA computes "inexperienced" relative to the reporting unit (new-to-school vs new-to-district vs new-to-profession), so district rows cannot be derived by summing school rows, and the state row cannot be derived by summing district rows — but the contract does not say so, and the `poverty_subgroup` description ("district/state rows aggregate only the schools in that stratum") implies additivity.
- **Evidence available**: Bronze-native, not transform-induced — 2020 bronze (no drops, 1:1 bronze→gold): Teachers/Total state `INEXPERIENCED_FTE` = 25,767 vs district-row sum = 37,747.1 vs school-row sum = 47,470.7, while `FTE` is 110,800.8 / 110,798.7 / 110,806.3 (identical to ±6). The district/state ratio is 1.38–1.49 in **every** year (2018: 50,362/33,781=1.49 … 2024: 41,473/29,986=1.38). Leaders reconcile to 1.000–1.002 pre-suppression, so the pattern is Teachers-specific. 102–175 districts per year have school `inexperienced_fte` sums exceeding the district row.
- **Why uncertain**: GOSA does not document the computation; the unit-relative-experience hypothesis fits the monotone school>district>state direction and the plausible state rate (~23% ≈ new-to-profession share) but cannot be proven from the CSVs. The data is faithfully preserved either way; the open question is only how loudly to caveat it.
- **Location**: `_emit_contract_and_readme()` in transform.py (contract `limitations` + `inexperienced_fte` description).
- **If confirmed, suggested fix**: add a contract caveat to `inexperienced_fte`/`inexperienced_fte_rate` and `limitations`: "inexperienced FTE does not aggregate across hierarchy levels for Teachers — school-row sums exceed the district row and district-row sums exceed the state row by ~1.4x (consistent with experience being measured relative to the reporting unit); never derive aggregates by summing lower-level rows." No data change.

### Judgment Call 2: 2018–2019 source-era level anomalies (2019 statewide Teachers FTE ≈1.4x; 2018 school-sum excess)
- **Severity if confirmed**: LOW
- **Suspicion**: the 2018 and especially 2019 files measure a broader Teachers workforce than 2020+ (2019 statewide Teachers Total FTE 162,256.2 vs 118,009.1 in 2018 and 110,800.8 in 2020 — implausibly high for classroom teachers, suggesting all certificated staff), making 2018→2020 year-over-year comparisons misleading.
- **Evidence available**: bronze line quoted verbatim (`"2018-19",…,"Teachers","Total",162256.2,46940,29`) — gold matches exactly, so no transform defect. The shift is broad-based: median district Teachers/Total ratio is 1.06 (2019/2018) and 1.20 (2019/2020); 38 of 205 districts jump >1.2x into 2019. Separately, 149 of the 166 district-total-below-school-sum `total_fte` violations are concentrated in 2018 (e.g. Bibb County 611: district 1,718.0 vs school sum 2,342.9), dropping to ≤9/year afterwards — an early-era FTE allocation quirk (multi-school assignment double-counting at school level).
- **Why uncertain**: below the skill's hard 1.5–2x cumulative-publication threshold; internally consistent (published rates reconcile with published components); could be a genuine definitional change GOSA never documented. Preserve-and-document is the standards-mandated default; v1 shipped the same values approved without a caveat.
- **Location**: `_emit_contract_and_readme()` in transform.py (contract `limitations` / README note).
- **If confirmed, suggested fix**: add a documentation caveat: "the 2019 file's Teachers FTE levels run ~40%% above adjacent years statewide and the 2018 file's school-level FTEs can sum above the district row — treat 2018–2019 levels as a distinct measurement basis when trending." No data change.

## Notes

- schema_hash `97f942f22b6bb4ed8c400d5006fa87998929f352b6c65529faec9cd00e51b4dc`; validation 21 pass / 0 fail / 0 warning; manifest generated 2026-06-11T17:31:38Z.
- Gold 45,093 rows = bronze 45,112 − 19 documented drops; per-year and per-detail-level counts reconcile exactly against the structure doc (including the 138/60 truncation-repair reclassifications, re-derived from bronze at 38+100 / 20+40).
- Known attribution caveat (already in the contract, verified): the two surviving 2024 truncated Utopian rows are bound to pinned 7820121 though the Leaders/Low Poverty row likely describes Trilith 7820619 — matches v1-approved handling.
- The structure doc's drop-class `state_charter_placeholder_district` recorded zero events this run (all placeholder-district rows were repaired, school-name-resolved, or dropped under the more specific predicates) — consistent with the manifest listing only 4 reasons.
- This review is the judgment layer over `_validation.json`; structural checks were not re-run by hand.
