# Data Review: english_learners_el_exit_rate

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

The gold data itself is accurate: **v1 parity MATCH (byte-identical with v1 gold)**, 1,336 bronze rows → 1,336 gold rows with zero filtering and zero read loss, all 11 value-level traces match, the FY2024 mask (130 cells) is correctly sized and recorded, and validation is 20/20. Two **documentation-accuracy** defects require fixing: (1) the contract/README/docstring State Schools provenance is wrong on both the codes (actual 7991893–7991895, not 7991891–7991893) and the years (FY2019 only — FY2020 bronze contains **zero** State Schools rows), which would send consumers querying nonexistent keys; (2) the FY2024-quirk prose misstates the masked-row composition ("65 with both counts TFS reading 0" — actually 65 of the 130 read 0 but only 46 of those have both counts TFS; and the published rates are not just "0 or 100" — 64 rows carry other numeric values). Neither defect touches the parquet, so the fix is prose-only and parity-safe.

## Manifest Verification

### Categorical mappings

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| _(none)_ | — | — | — | N/A — `categorical_mappings: {}` by design |

The transform applies **no categorical recodings at all** (no demographic, subject, or grade column exists in any era — verified: gold columns are `year`, `district_code`, `school_code` + 3 metrics only). The empty manifest section is correct, matching the docstring claim and the structure doc ("No demographic breakdown"). Steps 2a–2d, 2e (Asian/PI), and 2f (mutual exclusivity) are all **N/A**: no `demographic` column, no `pct_asian` column, and `NO_NHPI_LABEL_IN_BRONZE` (grep executed). Every row is the all-EL-students total.

### Row-count reconciliation

| Year | Bronze (manifest) | Gold (manifest) | Gold (parquet, measured) | Filtered | Expansion | Composition |
|---|---|---|---|---|---|---|
| 2019 | 214 | 214 | 214 | 0 | 1.0 | 213 district + 1 state |
| 2020 | 211 | 211 | 211 | 0 | 1.0 | 210 district + 1 state |
| 2021 | 223 | 223 | 223 | 0 | 1.0 | 222 district + 1 state |
| 2022 | 224 | 224 | 224 | 0 | 1.0 | 223 district + 1 state |
| 2023 | 228 | 228 | 228 | 0 | 1.0 | 227 district + 1 state |
| 2024 | 236 | 236 | 236 | 0 | 1.0 | 235 district + 1 state |
| **Total** | **1,336** | **1,336** | **1,336** | **0** | 1.0 | |

Parquet row counts measured directly and equal to manifest `total_gold`. Per-year district counts match the structure doc's district-file row counts exactly (213/210/222/223/227/235), each state file contributes exactly 1 row. All 6 expected years present. `read_loss`: zero events (12/12 files, raw == parsed). All 12 files routed to the expected era in `files_processed` (district: 5× era 1 + FY2023 era 2; state: 2019–2021 era 1, 2022/2024 era 2, 2023 era 3).

### Metric stats spot-verified against bronze

- 2024 `el_exit_count` max 15,519 and `el_student_count` max 155,372 = the state_FY2024.csv row (traced below).
- Non-null counts tie out with the structure doc's per-file non-null tallies + 1 state row in every year (e.g. 2023 rate non-null 106 = 105 district + 1 state; 2024 student non-null 179 = 178 + 1). No silent cast loss from `strict=False`.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `FISCAL_YEAR` (both groups) | `year` | MAPPED (Int32; single value per file, cross-checked vs filename) |
| `SYSTEM_ID` (district files) | `district_code` | MAPPED (Utf8 zfill(3); bronze lengths verified {3,7} in all 6 files — zfill is a no-op, no truncation) |
| `SYSTEM_ID` (state 2023) | — | CORRECTLY EXCLUDED (constant `"State of Georgia"`; state role = NULL keys + filename) |
| `SYSTEM_NAME` (district) | — | CORRECTLY EXCLUDED (dimension attribute, §2) |
| `SYSTEM_NAME` (state 2023) | — | CORRECTLY EXCLUDED (constant sentinel) |
| `#RPT_NAME` (district 2023, state 2023) | — | CORRECTLY EXCLUDED (constant report-name string) |
| `EL_EXIT_COUNT` / `STATE_EL_EXIT_COUNT` | `el_exit_count` | MAPPED (Int64, TFS→NULL; STATE_ prefix renamed) |
| `EL_STUDENT_COUNT` / `STATE_EL_STUDENT_COUNT` | `el_student_count` | MAPPED (Int64, TFS→NULL) |
| `EL_EXIT_RATE` / `STATE_EL_EXIT_RATE` | `el_exit_rate` | MAPPED (Float64, /100 to 0–1; FY2024 mask applied) |
| — (synthesized) | `school_code` | Always-NULL key per education CLAUDE.md; pinned by `school_code_always_null` |
| — (synthesized, transient) | `detail_level` | Dropped by `export_to_parquet`; encoded in filename — matches the structure doc's amended classification ("transient pipeline column", not persisted) |

No fabricated columns; every gold column traces to bronze or a documented synthesis. `_to_gold` raises on missing required columns and warns loudly on unexpected extras — no silent-drop path.

## Value-Level Spot Checks

All bronze quotes are from the raw CSVs (read with `infer_schema_length=0`, before suppression nulling).

### Extreme-row traces (per-metric global max/min)

| Trace | Bronze (file, row, values) | Expected | Gold | Verdict |
|---|---|---|---|---|
| `el_exit_count` global max | state_FY2024.csv: `2024,15519,155372,9.99` | 15519 | 2024 state row: `el_exit_count=15519` | MATCH |
| `el_student_count` global max | same row | 155372, rate 0.0999 | `el_student_count=155372`, `el_exit_rate=0.0999` | MATCH |
| `el_exit_count` global min (10) | district_FY2019.csv, SYSTEM_ID 606 Banks County: `"10","95","10.5"` (also 618/697/713) | 10 / 95 / 0.105 | 2019 d=606: `10, 95, 0.105` (618: `10,35,0.286`; 697: `10,45,0.222`; 713: `10,108,0.093`) | MATCH ×4 |
| `el_student_count` global min (10) | district_FY2019.csv, SYSTEM_ID 674 Heard County: `"TFS","10","TFS"`; 7820618 Coastal Plains: `"TFS","10","TFS"` | exit NULL, student 10, rate NULL | 2019 d=674: `None, 10, None`; d=7820618: `None, 10, None` | MATCH ×2 (also the §4f suppression trace) |
| `el_exit_rate` global max (0.467) | district_FY2023.csv, SYSTEM_ID 7830623 Academy For Classical Education: `"14","30","46.7"` | 0.467 (14/30 = 0.4667, dev 0.0003 < 0.0006) | 2023 d=7830623: `14, 30, 0.467` | MATCH |
| `el_exit_rate` global min (0.015) | district_FY2021.csv, SYSTEM_ID 631 Clayton County: `"79","5328","1.5"` | 0.015 (79/5328 = 0.01483, dev 0.00017) | 2021 d=631: `79, 5328, 0.015` | MATCH |

### Ordinary traces (one per era)

| Era | Bronze | Gold | Verdict |
|---|---|---|---|
| District Era 1 | district_FY2019.csv: `2019,"601","Appling County","37","274","13.5"` | 2019 d=601: `37, 274, 0.135` | MATCH |
| District Era 2 (#RPT_NAME) | district_FY2023.csv: `"EL_EXIT_RATES_DISTRICT_LEVEL","2023","601","Appling County","40","288","13.9"` | 2023 d=601: `40, 288, 0.139` | MATCH |
| State Era 1 (STATE_ prefix) | state_FY2019.csv: `2019,12125,121921,9.94` | 2019 state: `12125, 121921, 0.0994` | MATCH |
| State Era 2 (no prefix) | state_FY2022.csv: `2022,14348,136295,10.53` | 2022 state: `14348, 136295, 0.1053` | MATCH |
| State Era 3 (#RPT_NAME + sentinels) | state_FY2023.csv: `"EL_EXIT_RATES_STATE_LEVEL","2023","State of Georgia","State of Georgia","14215","143070","9.94"` | 2023 state: `14215, 143070, 0.0994`, `district_code=NULL` | MATCH (sentinel correctly dropped, not emitted as a district code) |

### Mask-boundary traces (FY2024 quirk)

- **Masked**: district_FY2024.csv, SYSTEM_ID 7820612 `'State Charter Schools-Ivy Preparatory Academy, Inc'`: `EL_EXIT_COUNT='TFS', EL_STUDENT_COUNT='TFS', EL_EXIT_RATE='100'` → gold 2024 d=7820612: `None, None, None`. **MATCH** — the unverifiable bronze rate 100 is NULLed.
- **Kept (same year)**: district_FY2024.csv, SYSTEM_ID 601: `"46","307",15` → gold `46, 307, 0.15` (46/307 = 0.14984, dev 0.00016). **MATCH** — published-count rows keep their rate.
- **Kept (prior year, co-suppressed regime)**: district_FY2023.csv, SYSTEM_ID 602 Atkinson: `"16","185","8.6"` → gold `16, 185, 0.086`. **MATCH**; and 2019–2023 bronze has **zero** rows with a numeric rate next to a TFS count (measured `rate_wo_counts=0` in all five years), so the mask is verifiably a no-op outside 2024.
- **Mask accounting**: FY2024 exit-TFS rows = 130 (manifest masked count = 130 ✓); gold 2024 rate non-null = 106 = 235 − 130 district + 1 state ✓; 73 rows retain `el_student_count` with rate NULL (exit-only-TFS) ✓.

### Other Step-4 items

- **4c sentinel year-attribution**: N/A in the risky sense — the only year-bearing source is `FISCAL_YEAR`, required single-valued and cross-checked against the filename (raises on mismatch). State Era 3 trace above confirms 2023 attribution.
- **4d aggregate feasibility screen** (state rows come from bronze; district-only variant, suppression-heavy → impossibly-low direction): for every year, state total ≥ visible district sum and ≥ max district, executed output:
  `2019: state_exit=12125 dist_visible_sum=11920 (98.3%) … state_stud=121921 dist_visible_sum=121921 (100.0%) state>=sum: True state>=max: True` — and likewise True/True for 2020–2024 (visible exit sums 97.4–98.7% of state; student sums 99.9–100.0%). No impossible aggregate; the transform's decision to skip a state-vs-district-sum quality check is justified (54–62% of district exit counts suppressed), and the screen confirms the lenient direction holds anyway.
- **4e dedup tie-break**: N/A — no year is covered by two eras within a routing group (one file per group-year), and measured `dupIDs=0` in every district file. The explicit `sort_col="el_exit_count"` is an inert, documented safety net.
- **4f suppression semantics**: Heard County trace above (TFS → NULL, row + valid `el_student_count` preserved). The only marker is `TFS`; validator confirms no leftover markers.

## Validation Cross-Read

- `_validation.json`: **passed=true, 20 pass / 0 fail / 0 warning** (2026-06-11T22:24:07Z, FRESH vs manifest and transform mtime). `contract_parquet_schema` (12/12 files), `contract_quality_sql` (12/12 checks), `grain_uniqueness` (year, district_code, school_code), and `foreign_keys` (all 241 district codes resolve; school_code has no populated keys) all pass.
- **schema_hash**: `17460628cb5370c6bec17717e50e6af3dd0a8413ee6f9a5ccaf25b89cd2af10b`
- **§4b masking audit**: `_null_unverifiable_rates` is the single `_null_*` helper. Manifest `masked_values`: `el_exit_rate`, count 130, years [2024], reason recorded — count independently re-derived from bronze (130 exit-TFS FY2024 rows, all with numeric rates). Documented in the contract `el_exit_rate` description. Range guard present (`unit: proportion` → `el_exit_rate_within_unit_interval`), and the mask is pinned bidirectionally by `el_exit_rate_requires_counts` + `el_exit_rate_present_when_counts_present`. The biconditional's bronze basis verified in all 12 files: `rate_wo_counts=0` and `counts_wo_rate=0` for 2019–2023 district files and all state files; 2024 `rate_wo_counts=130` (the masked set), `counts_wo_rate=0`. Mechanically sound — but the prose describing the masked set is inaccurate (Fix 2).
- **§15b coverage judgment**: adequate. 8 authored checks + 4 derived = 12. Co-null in both directions, count-subset (`exit_count ≤ student_count` — bronze verified 0 violations in all 6 district files), suppression hierarchy (`student NULL ⇒ exit NULL` — bronze verified 0 violations), structural facts (`school_code_always_null`, `one_state_row_per_year`, `state_metrics_never_null`), and component reconciliation with a justified 0.0006 tolerance (district bronze rounds to 1 decimal on 0–100 → 0.0005 bound after /100; measured gold max deviation **0.0005000000000000004** over 576 published triples — the tolerance is tight but correct, float epsilon included). Partition-sums: N/A (no proportion family).
- **v1 parity** (verbatim): `MATCH — byte-identical with v1 gold`

## Cross-Era Consistency

- **Overlap years**: none — each (group, year) has exactly one file. Era-boundary continuity is clean: state rates 9.94 / 9.29 / 7.71 / 10.53 / 9.94 / 9.99 across the State Era 1→2→3→2 transitions (no scale break at any boundary; the 2021 dip is the COVID-era testing year, ~19% below trend, nowhere near a 10x or 2x anomaly). District Era 1→2→1 (2022→2023→2024) means are continuous (exit-rate means 0.1334 / 0.1304 / 0.1234).
- **Cross-year NULL sweep** (executed): `OK el_exit_count`, `OK el_student_count`, `OK el_exit_rate` — no ~100%-NULL year for any column; the STATE_-prefix rename (Risk 2) demonstrably landed (2019–2021 state rows fully populated).
- **Null rates track suppression**, not era: exit-count null pct 0.535–0.619 across years; the FY2024 mask brings `el_exit_rate` (0.5508) exactly in line with `el_exit_count` (0.5508) — uniform invariant achieved, no spike (validator: 0 warnings).
- **Filename-prefix routing is genuinely mandatory** (claim verified): manifest `bronze_columns` for district_FY2023 and state_FY2023 are identical 7-column sets (`#RPT_NAME, FISCAL_YEAR, SYSTEM_ID, SYSTEM_NAME, EL_EXIT_COUNT, EL_STUDENT_COUNT, EL_EXIT_RATE`) — column-only routing would be ambiguous; the transform raises on any unprefixed filename.
- **State Schools representation**: gold 2019 = `['7991893','7991894','7991895']`, 2020 = `[]`, 2021–2024 = `['799']` — faithfully preserves bronze (verified directly), but contradicts the documentation in three places (Fix 1).

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — `_to_gold` raises on missing required columns, warns on unexpected extras; `_prepare_for_era` drops only documented constants |
| Era routing correctness | — | PASS — prefix routing raises on unknown prefixes; `detect_era_by_columns` is first-match-wins and both signature dicts are ordered most-specific-first (superset signatures lead); all 12 manifest era assignments correct |
| Filter logic | — | PASS — zero filters, zero filtered rows |
| Normalization map completeness | — | PASS — `STATE_PREFIX_RENAMES` covers all 3 STATE_ columns; rename-coverage guard enforces post-rename presence |
| `strict=False` casts | — | PASS — defensive only; non-null gold counts reconcile exactly with structure-doc bronze non-null tallies (no silent NULLing) |
| Dedup keys + tie-break | — | PASS — collision guard before dedup; explicit documented `sort_col`; zero duplicates measured |
| Year extraction | — | PASS — single-valued FISCAL_YEAR + filename cross-check, raises on mismatch |
| §5b mask recording | LOW | Mask correctly sized/recorded/pinned; describing prose inaccurate (Fix 2) |
| Risk 1 Asian/PI conflation | — | N/A — no demographic axis (grep: NO_NHPI_LABEL_IN_BRONZE) |
| Risk 2 column-rename typo | — | PASS — NULL sweep clean in every year |
| Risk 3 sentinel year-attribution | — | N/A — no year-bearing strings beyond FISCAL_YEAR |
| Risk 4 derived-row aggregation | — | N/A (aggregates from bronze); feasibility screen PASS all 6 years |
| Risk 5 dedup tie-break inversion | — | N/A — no overlap years |
| Risk 6 mutual exclusivity | — | N/A — no demographic column |
| Risk 7 semantically wrong mapping | — | N/A — no categorical recodings exist |

## Required Fixes

### Fix 1: State Schools provenance in contract/README/docstring cites wrong codes and wrong years
- **Severity**: MEDIUM
- **Issue**: The contract `district_code` description and `limitations`, the README notes, and the transform module docstring all state that individual State Schools rows are "7991891-7991893 in FY2019-2020". Both halves are wrong: the actual FY2019 codes are **7991893, 7991894, 7991895** (Atlanta Area School for the Deaf, Georgia Academy for the Blind, Georgia School for the Deaf), and they appear in **FY2019 only** — the FY2020 district file contains zero State Schools rows (no 799-prefix code, no "State Schools" name; 210 rows vs 213 in 2019, exactly the three missing rows). A consumer following the contract would query `district_code IN ('7991891','7991892')` (nonexistent keys, zero rows) and would expect FY2020 coverage that does not exist. The gold parquet itself is correct — this is metadata-only.
- **Evidence**: Bronze district_FY2019.csv: `'7991893','State Schools-Atlanta Area School for the Deaf'`, `'7991894','State Schools-Georgia Academy for the Blind'`, `'7991895','State Schools- Georgia School for the Deaf'` (all metrics TFS). Bronze district_FY2020.csv: zero rows matching `(?i)state school` or 7-digit non-782/783 codes. Gold 799-prefix codes by year (measured): 2019 `['7991893','7991894','7991895']`, 2020 `[]`, 2021–2024 `['799']`. Contract lines: "individual State Schools rows 7991891-7991893 in FY2019-2020" (district_code description), "individual 7-digit rows (7991891-7991893) in FY2019-2020" (limitations), README note "FY2019-2020 publish individual 'State Schools-…' rows (7991891-7991893)".
- **Location**: `_emit_contract_and_readme()` in transform.py — `district_code` column description, `limitations=`, and the "State Schools representation" entry in `notes=`; also the module docstring ("the individual ``State Schools-…`` rows (FY2019-2020)"). The same errors exist in `bronze-data-structure.md` (FY2019 row-count note "All five `STATE_`-style state schools" — actually three; FY2020 note "Same individual `State Schools-…` rows as 2019" — actually none) and should be amended there too.
- **Suggested fix**: Replace with: individual State Schools rows **7991893–7991895 in FY2019 only**; **no State Schools representation at all in FY2020**; one combined `799` row from FY2021. Re-run the transform to re-emit contract + README (description-only change — schema_hash and parquet unchanged, v1 parity preserved).

### Fix 2: FY2024-quirk prose misstates the masked-row composition ("65 with both counts TFS reading 0"; rates "(0 or 100)")
- **Severity**: LOW
- **Issue**: The transform docstring, `_null_unverifiable_rates` docstring, contract notes, and bronze-data-structure.md describe the FY2024 masked set as "130 rows where EL_EXIT_COUNT is TFS (65 of them with both counts TFS and the rate reading 0, plus Ivy Preparatory Academy … with both counts TFS and the rate reading 100)", and the contract `el_exit_rate` description says "GOSA published numeric rates (0 or 100) even for the 130 district rows with suppressed counts". The measured composition differs: both-counts-TFS rows total **57** (46 reading 0, 1 reading 100, 10 reading other values); **65** is the count of rate-0 rows across all 130 exit-TFS rows (46 both-TFS + 19 exit-only-TFS); and the 130 masked rates span many values (12.5, 16.7, 4.8, 0.9, 44.4, …), not just 0 or 100. The mask itself (130 cells) and its rationale are correct — only the descriptive prose is wrong.
- **Evidence**: Executed against district_FY2024.csv: `exit-TFS rows: 130`; `rate==0 among exit-TFS rows: 65`; `rows with both TFS: 57`; both-TFS rate distribution `0→46, 100→1, 12.5→3, 16.7→1, 22.2→2, 25→1, 37.5→1, 40→1, 44.4→1`; exit-only-TFS rows = 73 with rates `['0','0.9','1.3','1.6','10','10.3','11.1','12.5','12.8','13.3', …]`.
- **Location**: transform.py module docstring (lines ~46–49), `_null_unverifiable_rates()` docstring, the `el_exit_rate` column description ("(0 or 100)") and the FY2024-anomaly entry in `notes=` inside `_emit_contract_and_readme()`; same claim in `bronze-data-structure.md` ETL Considerations ("65 rows where both count columns are TFS and the rate reads 0").
- **Suggested fix**: Restate as: "130 FY2024 district rows have TFS-suppressed EL_EXIT_COUNT yet a published numeric EL_EXIT_RATE (values 0–100; 65 read 0, including Ivy Preparatory Academy / 7820612 with both counts TFS and a rate of 100); 57 of the 130 also suppress EL_STUDENT_COUNT." Drop the "(0 or 100)" parenthetical from the el_exit_rate description (e.g. "published numeric rates" suffices). Re-run the transform to re-emit (prose-only; parquet unchanged).

## NEEDS_JUDGMENT

None — no unresolved suspicions. (The FY2020 absence of State Schools rows is a property of the published bronze, faithfully preserved; the decision to mask all 130 FY2024 unverifiable rates — including the 73 rows where the denominator is published — is documented, uniform, quality-check-pinned, and byte-identical with the approved v1 gold.)

## Notes

- schema_hash: `17460628cb5370c6bec17717e50e6af3dd0a8413ee6f9a5ccaf25b89cd2af10b`; validation 20 pass / 0 fail / 0 warning; contract quality SQL 12/12.
- v1 parity: `MATCH — byte-identical with v1 gold` — both fixes are prose-only and must not change the parquet; re-verify parity after the fix run.
- Bronze claim verifications (all 6 district files): zero duplicate SYSTEM_IDs; zero `exit > student` violations; zero suppression-hierarchy violations; rate↔counts biconditional exact in 2019–2023 (and in 2024 after the mask); min published exit count 10 (11 in 2021). SYSTEM_ID lengths are {3,7} everywhere, so `zfill(3)` is provably non-destructive.
- The contract claim "published values are always 10 or more" for the counts is bronze-verified but not pinned by a quality check. Optional hardening (not required): a `published_counts_at_least_10` check would catch a future suppression-threshold regime change, in the same spirit as `state_metrics_never_null`.
- Rate-reconciliation tolerance 0.0006 is tight and justified: measured gold max deviation 0.0005000000000000004 across 576 published triples (district bronze rounds to 1 decimal on the 0–100 scale).
- District 890 FY2023 (NULL SYSTEM_NAME, all TFS in bronze) is correctly emitted with NULL metrics; the districts dimension resolves the name (FK check passes for all 241 codes).
