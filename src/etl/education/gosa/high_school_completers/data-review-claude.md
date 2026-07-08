# Data Review: high_school_completers

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

PASS — no required fixes, no judgment calls. v1 parity: **MATCH — byte-identical with v1 gold** (`compute_gold_sha256` vs `docs/rebuild/v1-baseline.yaml`). All 478,980 bronze rows land in gold 1:1 (zero filtered, zero read loss); all three categorical maps (9 demographic, 6 credential_type, 2 completer_type entries) are semantically correct with `unmapped_count: 0`; the §5b combined Asian/Pacific Islander convention is proven exactly (2024 state general_education_diplomas race sum 119,764 = Total 119,764, ratio 1.0000, and `grep -li pacific` over all 14 bronze CSVs returns nothing); 18/18 value-level bronze→gold traces MATCH, including the global max (119,764), real zeros, every suppression-marker form, and the 2011 pct=0.0-on-TFS quirk; the four-direction aggregate feasibility screen has 0 violations.

## Manifest Verification

### Categorical maps

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `demographic` | 9 | 9 (matches structure-doc list exactly) | 0 | PASS |
| `credential_type` | 6 | 6 (2011 carries only 5 — documented) | 0 | PASS |
| `completer_type` | 2 | 2 | 0 | PASS |

### Full map review — `demographic` (all 9 entries)

| Bronze (upper) | Gold | Correct? |
|---|---|---|
| `TOTAL` | `all` | YES — the unfiltered total lane |
| `ASIAN` | `asian_pacific_islander` | YES — topic-local pre-normalize remap to the combined bucket, proven by the exact math test (see Risk 1 below); `DEMOGRAPHIC_ALIASES['ASIAN/PACIFIC ISLANDER'] = asian_pacific_islander` confirmed |
| `BLACK` | `black` | YES |
| `HISPANIC` | `hispanic` | YES |
| `WHITE` | `white` | YES |
| `MULTI` | `multiracial` | YES — GOSA's "Multi" race bucket |
| `NATIVE AMERICAN/ ALASKAN NATIVE` | `native_american` | YES — irregular space after the slash matched verbatim via the shared alias |
| `MALE` | `male` | YES |
| `FEMALE` | `female` | YES |

### Full map review — `credential_type` (all 6 entries)

| Bronze | Gold | Correct? |
|---|---|---|
| `Certificates Of Attendance` | `certificates_of_attendance` | YES |
| `Diplomas with Both College Prep. & Voc.` | `diplomas_college_prep_and_vocational` | YES — punctuation (periods, ampersand) resolved explicitly |
| `Diplomas with College Prep Endorsements` | `diplomas_college_prep` | YES |
| `Diplomas with Vocational Endorsements` | `diplomas_vocational` | YES |
| `General Education Diplomas` | `general_education_diplomas` | YES — absent from 2011 bronze (credential did not exist yet); gold 2011 confirmed to carry only the other 5 |
| `Special Education Diplomas` | `special_education_diplomas` | YES |

### Full map review — `completer_type` (both entries)

| Bronze | Gold | Correct? |
|---|---|---|
| `Graduates` | `graduates` | YES — the four diploma credentials |
| `Other Completers` | `other_completers` | YES — Special Education Diplomas + Certificates of Attendance |

Contract cross-check (2c): `gold_values_produced` equals the contract `enum` for all three columns, and the gold parquet's distinct values match both exactly. Unmapped (2d): 0 for all three.

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Factor |
|---|---|---|---|---|
| 2011 | 27,540 | 27,540 | 0 | 1.0 |
| 2012 | 33,318 | 33,318 | 0 | 1.0 |
| 2013 | 33,372 | 33,372 | 0 | 1.0 |
| 2014 | 33,534 | 33,534 | 0 | 1.0 |
| 2015 | 34,236 | 34,236 | 0 | 1.0 |
| 2016 | 34,398 | 34,398 | 0 | 1.0 |
| 2017 | 34,722 | 34,722 | 0 | 1.0 |
| 2018 | 34,992 | 34,992 | 0 | 1.0 |
| 2019 | 35,046 | 35,046 | 0 | 1.0 |
| 2020 | 35,316 | 35,316 | 0 | 1.0 |
| 2021 | 35,478 | 35,478 | 0 | 1.0 |
| 2022 | 35,856 | 35,856 | 0 | 1.0 |
| 2023 | 35,478 | 35,478 | 0 | 1.0 |
| 2024 | 35,694 | 35,694 | 0 | 1.0 |
| **Total** | **478,980** | **478,980** | **0** | **1.0** |

Per-year bronze counts match the structure doc verbatim. Actual parquet rows (3b): 478,980 = manifest `total_gold` (states 747 + districts 141,066 + schools 337,167). 2011 has 45 state rows (5 credentials × 9 demographics — `general_education_diplomas` absent, as documented); 2012–2024 have 54. Suppression accounting reconciles exactly against the structure doc's per-file blank/TFS table, e.g. 2011 count nulls 19,412 = 9,073 blanks + 10,339 TFS; 2011 pct nulls = 9,073 blanks; 2023 pct-published-on-TFS-count rows = 31,661 − 29,708 = 1,953; 2024 = 31,852 − 29,992 = 1,860.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| LONG_SCHOOL_YEAR | `year` (ending year, filename cross-checked) | MAPPED |
| SCHOOL_DSTRCT_CD | `district_code` (`ALL` sentinel → NULL; zfill(3)) | MAPPED |
| SCHOOL_DSTRCT_NM | — (districts dimension attribute) | CORRECTLY EXCLUDED |
| INSTN_NUMBER | `school_code` (`ALL` sentinel → NULL; zfill(4)) | MAPPED |
| INSTN_NAME | — (schools dimension attribute) | CORRECTLY EXCLUDED |
| LABEL_SORT_ORDER | — (presentation sort key, one-to-one with credential) | CORRECTLY EXCLUDED |
| COMPLETER_TYPE | `completer_type` | MAPPED |
| LABEL_LVL_1_DESC | `credential_type` | MAPPED |
| LABEL_LVL_5_CD | `demographic` | MAPPED |
| PROGRAM_TOTAL | `completer_count` | MAPPED |
| PROGRAM_PERCENT | `pct_of_credential_type` (÷100 → 0–1) | MAPPED |
| #RPT_NAME (Era 2 only) | — (constant, guarded by `_validate_era2_constants`) | CORRECTLY EXCLUDED |

Every gold column traces to bronze — no fabrication. `_require_columns` + `_reject_unexpected_columns` make both silent drops and silent new-column passthrough impossible.

## Value-Level Spot Checks

All 18 traces MATCH. Bronze quoted verbatim (Era 1 2011/2018–2020 unquoted CSV; 2012–2017/2021–2022 quoted; Era 2 quoted with leading `#RPT_NAME`).

**Extreme rows (4a):**

| # | Bronze (file, row, value) | Expected | Gold | Verdict |
|---|---|---|---|---|
| T1 | 2024: `"2023-24","ALL",...,"General Education Diplomas","Total","119764","100"` | global max count 119,764; pct 1.0 | 119764, 1.0 | MATCH |
| T4 | 2011: `2010-11,ALL,...,Diplomas with College Prep Endorsements,Total,51605,100` | 2011 max 51,605; pct 1.0 | 51605, 1.0 | MATCH |
| T3c | 2022: `"2021-22","ALL",...,"Special Education Diplomas","Native American/ Alaskan Native","0","0"` | global min count, real published 0 | 0, 0.0 | MATCH |
| T6 | 2012: `"2011-12","601",...,"0103",...,"General Education Diplomas","Native American/ Alaskan Native",0,0` | real 0 at school level | 0, 0.0 | MATCH |
| T5c | 2011: `2010-11,601,Appling County,103,...,Diplomas with College Prep Endorsements,Asian,TFS,0` | pct global min 0.0 published on a TFS count; school code 103 → `0103`; Asian → combined bucket | NULL count, pct 0.0 at (601, 0103, asian_pacific_islander) | MATCH |

**pct semantics proof (the amended structure-doc claim):**

| # | Bronze | Expected | Gold | Verdict |
|---|---|---|---|---|
| T2 | 2022: `"2021-22","ALL",...,"General Education Diplomas","Male","55853","48.8"` (Total row: `"114359","100"`) | 55,853 / 114,359 = 48.84% → 0.488 (share of the credential's total) | 55853, 0.488 | MATCH |
| T3a/T3b | 2022 state Other Completers: `"Special Education Diplomas","Total","189","100"` AND `"Certificates Of Attendance","Total","18","100"` | BOTH credentials carry pct=1.0 — disproves the old "share within completer_type" reading (which would give 0.913/0.087) | 189, 1.0 and 18, 1.0 | MATCH |

**Ordinary entity traces (4b), one per era/suppression regime:**

| # | Bronze | Gold | Verdict |
|---|---|---|---|
| T5a | 2011 (unquoted, 3-char codes): `2010-11,601,Appling County,103,...,College Prep Endorsements,Male,39,38.2` | (2011, 601, 0103, male): 39, 0.382 | MATCH |
| T7 | 2022 (quoted Era 1): `"2021-22","651","Effingham County","0390",...,"Special Education Diplomas","Male","4","50"` | (2022, 651, 0390, male): 4, 0.5 | MATCH |
| T10a/c | 2024 (Era 2): Appling district `"General Education Diplomas","Black","59","25"`, `"Total","236","100"` | (2024, 601, NULL): black 59, 0.25; all 236, 1.0 | MATCH |
| T1b/T1c | 2024 state: `"Native American/ Alaskan Native","225",".2"`, `"Asian","6232","5.2"` | native_american 225, 0.002; asian_pacific_islander 6232, 0.052 | MATCH |

**Suppression traces (4f), one per marker form:**

| # | Marker form | Bronze | Gold | Verdict |
|---|---|---|---|---|
| T9 | blank both (2012–2017/2021 regime) | 2015: `"2014-15","601",...,"0103",...,"Both College Prep. & Voc.","Male",,` | NULL, NULL | MATCH |
| T8 | TFS both (2022 regime) | 2022: `"2021-22","748","Ware County","ALL",...,"Diplomas with Vocational Endorsements","Multi","TFS","TFS"` | district row: NULL, NULL | MATCH |
| T5b | TFS count + published pct (2011/2018–2020/2023–2024 regime) | 2011: `...,103,...,College Prep Endorsements,Hispanic,TFS,6.9` | NULL, 0.069 | MATCH |
| T10b | TFS count + published pct, Era 2 | 2024: Appling district `"General Education Diplomas","Asian","TFS","1.3"` | NULL, 0.013 | MATCH |

**Sentinel year-attribution (4c):** PASS — gold `year` is parsed from `LONG_SCHOOL_YEAR` ("2023-24" → 2024) and the transform raises on disagreement with the filename year; every 2024-file trace above lands at `year=2024`.

**Aggregate feasibility screen (4d):** aggregates come from bronze, so the impossibly-low screen was run on gold: district < max school **0 violations**, district < visible school sum **0 violations** (26,421 screened groups); state < max district **0**, state < visible district sum **0** (419 screened groups).

**Dedup tie-break (4e):** N/A — 14 files, 14 distinct years (manifest `files_processed`), no overlap; per-file grain verified unique by the transform's collision guard.

## Validation Cross-Read

- `_validation.json`: **passed, 21 pass / 0 fail / 0 warnings** (2026-06-12T01:31:09Z, fresh against the manifest). `contract_parquet_schema` (42 files), `contract_quality_sql` (all 13 checks), `grain_uniqueness`, and `foreign_keys` (201 districts, 575 schools, 9 demographics all resolve) all pass.
- `schema_hash`: `e03ad04843c6291927e3edf4b7d40cfb933203a5f5af7423d8dd41e8ba466a8e`
- **§4b masking audit (5b):** No `_null_*` helpers in transform.py and no `masked_values` section in the manifest — consistent. The module docstring documents the full-scan basis (counts 0–119,764, PROGRAM_PERCENT within [0, 100]): no impossible values exist, so no masks. Manifest metric stats confirm (count min ≥ 0 every year; pct within [0, 1] every year). PASS.
- **§15b coverage judgment (5c):** Strong. The 7 authored checks cover the topic's real cross-column invariants: the credential→completer_type functional dependency, the count⇒pct co-null direction, all-demographic share ≡ 1.0, EXACT gender and race count partitions, and rounding-tolerant gender (0.002) and race (0.004) pct partitions — all written as single-scan conditional-aggregation pivots (no self-joins). Tolerances are tight against observed maxima (0.001/0.002). No missing obvious invariant.
- **v1 parity (5d):** executed output verbatim: `MATCH — byte-identical with v1 gold`

## Cross-Era Consistency

- **Overlap years:** none (each file is one school year).
- **Era boundary 2022→2023 (Era 1 → Era 2):** state-level all-demographic count sums are smooth across all 13 adjacent year pairs (98,823 in 2011 → 119,967 in 2024, no jump > 1.5x, no >10x anywhere). The pct mean rises 0.34 → 0.43 at 2023 — a suppression-composition effect (2023–2024 publish no 0.0 shares; min pct becomes 0.001), not a scale shift; traced Era 2 values divide by 100 correctly.
- **Cross-year NULL sweep (3c):** no column is ~100% NULL in any year subset — no era-localized rename signature. Metric NULL rates (65–89%) are bronze-real suppression, reconciled per file above; validator `null_rate_spikes` passes.
- **§5b consistency across eras:** race sums are exact in 2011 (e.g. Both-Prep-&-Voc: 8,803+10,660+1,624+462+435+57 = 22,041 = Total) and 2024 (6,232+42,883+21,389+4,414+225+44,621 = 119,764 = Total) — the combined-bucket convention holds at both ends.
- **ID formatting across eras:** gold district_code lengths {3, 7} only; school_code uniformly 4 chars — the 2011/2018–2020 3-char bronze codes (e.g. `103`) were padded to `0103` (traced).

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Risk 1 Asian/PI conflation | PASS | Topic-local remap Asian → "Asian/Pacific Islander" before `normalize_demographic_column()`; math test exact (ratio 1.0000); `NO_NHPI_LABEL_IN_BRONZE` across all 14 files |
| Risk 2 column-rename typo | PASS | NULL sweep clean; `_require_columns` guard |
| Risk 3 sentinel year-attribution | PASS | LONG_SCHOOL_YEAR ending year, filename cross-check raises on mismatch |
| Risk 4 derived-row aggregation | N/A / PASS | No derived rows; feasibility screen 0 violations ×4 directions |
| Risk 5 dedup tie-break inversion | N/A | No overlap years; `sort_col="completer_count"` documented safety net only |
| Risk 6 mutual exclusivity | PASS | Single convention — only `asian_pacific_islander`; split keys never emitted |
| Risk 7 semantically wrong mapping | PASS | All 17 map entries reviewed above |
| Silent column drops | PASS | `_reject_unexpected_columns` raises on untriaged bronze columns |
| Era routing | PASS | `detect_era_by_columns`, most-specific signature first; Era 2 `#RPT_NAME` constant guarded |
| Filter logic | PASS | Zero filters — bronze = gold row-for-row |
| Normalization completeness | PASS | Maps cover every documented bronze value; `replace_strict` default `"99999999"` routes strays to the manifest guard |
| `strict=False` casts | PASS | Reader nulls TFS/blanks; suppression accounting reconciles exactly, so no silent residue was nulled; counts cast via exact Float64→Int64 hop |
| Year extraction | PASS | Single LONG_SCHOOL_YEAR per file enforced |
| §4b masking (5b) | PASS | No masks needed; documented basis in docstring |

## Notes

- `schema_hash`: `e03ad04843c6291927e3edf4b7d40cfb933203a5f5af7423d8dd41e8ba466a8e`; validation 21 pass / 0 fail / 0 warnings; contract `version: 1.0.0`.
- **2011 pct=0.0-on-TFS rows (4,459 of the 10,339 TFS-count rows):** at school level a 1-decimal share of 0.0 implies the masked count is exactly 0 (e.g. Appling HS College Prep Asian: total 102, any count ≥ 1 would print ≥ 1.0). The transform preserves bronze faithfully (count NULL, pct 0.0) rather than imputing 0 — the correct preserve-bronze default; the contract `null_meaning` documents the pattern.
- The manifest's `demographic.map_used` is the effective slice of `DEMOGRAPHIC_ALIASES` with the `ASIAN` entry overridden to record the topic-local remap actually applied — it accurately reflects pipeline behavior (verified against gold values).
- State-level suppression is real and increases over time: 27 suppressed state count cells in 2022 (the three endorsement-diploma credentials, all 9 demographics each), 34 in 2023 and 2024 — matching the contract's limitations prose.
- CSV quoting varies by file (2011/2018–2020 unquoted; others quoted; Era 2 adds `#RPT_NAME`) — handled uniformly by the all-string read; no read loss recorded in any file.
