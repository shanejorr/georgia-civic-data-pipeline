# Data Review: free_reduced_lunch

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Gold is a faithful, lossless 1:1 projection of bronze: an independent cell-by-cell census of all 28 bronze CSVs reproduces the gold `reporting_status` totals exactly (26,561 numeric → `reported`; 7,952 `*` → `suppressed_privacy_band`; 622 `#` + 6 `NA` = 628 → `not_participating`), every one of 18 value-level traces MATCHes, and the aggregate feasibility screen (1,456 fully-published district groups) found zero violations. **v1 parity: MATCH — byte-identical with v1 gold** (`f24b85108b73abad743b0f345c4aae7db649d04af14bc34abe0c92bbf1428a1c`), independently recomputed. No required fixes; no judgment items.

## Manifest Verification

**Preconditions**: transform mtime 17:36:07 ≤ manifest generated_at 17:36:16 ≤ validation ts 17:36:16; `passed: true` (21 pass / 0 fail / 0 warning); manifest has **no** `read_loss` / `masked_values` / `reclassified` sections (absent = zero events; the transform measures raw-vs-parsed for all 28 files). FRESH.

| Column | Map entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| `reporting_status` | 3 (`*`, `#`, `NA`) | `#`, `*`, `NA` — all 3 in map | 0 | PASS |

**Full map review (every entry, against the source's own footer Notice — identical in all 28 files):**

> `-"*" indicates Free and Reduced Lunch (FRL) percentage is either greater than 95% or less than 5%.`
> `-"NA" indicates school does not participate in the FRL program.`

| Bronze → Gold | Correct? |
|---|---|
| `*` → `suppressed_privacy_band` | CORRECT — the footer defines `*` as a dual-ended >95%/<5% privacy band, exactly what the gold value and contract prose say. Not a small-cell suppression. |
| `#` → `not_participating` | CORRECT — `#` is the de-facto non-participation marker (622 cells across all 14 years). The footer literally defines only `NA` for non-participation, but `#` occupies the same cell role, flags the same entity types (e.g. SAIL Charter Academy, Dept-style specialty systems, virtual academies), and the structure doc's ETL notes record that "in practice the data uses `#` for this". Both markers coexist only in FY2016 and both map to the same gold value, so no information is lost either way. |
| `NA` → `not_participating` | CORRECT — verbatim the source's own Notice definition. Occurs only in FY2016 (2 District + 4 School cells — all six traced below). |
| numeric → `reported` (derivation, not map entry) | CORRECT — `strict=False` cast succeeds ⇒ `reported`; recorded outside the map so the unmapped guard fires only on genuinely new markers. |

`gold_values_produced` = {`not_participating`, `reported`, `suppressed_privacy_band`} = contract `enum` exactly (2c PASS). `unmapped_count` = 0 (2d PASS). My independent bronze census found **no** marker outside {numeric, `*`, `#`, `NA`} and **zero empty rate cells** in any of the 28 files — the closed-vocabulary claim (structure-doc Correction 6) holds.

**Row-count reconciliation** (manifest `by_year` vs my census vs parquet):

| Year | Bronze | Gold | Factor | | Year | Bronze | Gold | Factor |
|---|---|---|---|---|---|---|---|---|
| 2013 | 2,472 | 2,472 | 1.0 | | 2020 | 2,512 | 2,512 | 1.0 |
| 2014 | 2,459 | 2,459 | 1.0 | | 2021 | 2,524 | 2,524 | 1.0 |
| 2015 | 2,463 | 2,463 | 1.0 | | 2022 | 2,531 | 2,531 | 1.0 |
| 2016 | 2,466 | 2,466 | 1.0 | | 2023 | 2,537 | 2,537 | 1.0 |
| 2017 | 2,498 | 2,498 | 1.0 | | 2024 | 2,553 | 2,553 | 1.0 |
| 2018 | 2,511 | 2,511 | 1.0 | | 2025 | 2,554 | 2,554 | 1.0 |
| 2019 | 2,512 | 2,512 | 1.0 | | 2026 | 2,549 | 2,549 | 1.0 |

Total 35,141 bronze = 35,141 gold = actual parquet row sum (3b PASS). `total_filtered` = 0 every year — zero drops, matching the docstring's 1:1 claim. All 14 expected years present; per-file bronze rows match the structure doc's corrected counts (FY2013 District 199, FY2024 District 235, FY2024 School 2,318, FY2026 School 2,312).

**Per-year status counts tie out exactly** — e.g. 2013: D(5*)+S(194*)=199 suppressed, 193+2058=2251 reported, 1+21=22 not_participating; 2016: 39+545=584 / 162+1688=1850 / 1+2+25+4=32 (incl. all 6 NA); 2025: 81+896=977 / 146+1411=1557 / 8+12=20; 2026: 89+966=1055 / 140+1336=1476 / 8+10=18. Gold per-year pivot matches the census for all 14 years. The FY2025 split confirms structure-doc Correction 4 (81 `*` / 8 `#` District; 896 `*` / 12 `#` School).

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `System ID` | `district_code` | MAPPED — zfill(3); whitespace state sentinel → NULL **before** zfill (traced: FY2013 state row `System ID=' '` → NULL, not `'000'`); 3-or-7-digit shape enforced by a loud guard |
| ` System Name` | — | CORRECTLY EXCLUDED — dimension attribute (districts dim); used only to detect the `State-Wide Total` row |
| `School ID - School Name` | `school_code` | MAPPED — anchored `^\s*(\d{4}) - ` extract, 100% conformance enforced (unparseable raises); name half correctly excluded to schools dim |
| `KK-12 % FRL` | `free_reduced_lunch_rate` + `reporting_status` | MAPPED — ÷100 to 0-1 proportion; markers → NULL rate + status. Gold name follows the `…_rate` convention (the doc's suggested `pct_frl` would violate §16 — correctly overridden) |
| (filename year) | `year` | MAPPED — filename regex, cross-checked against the preamble (I re-verified all 28 files agree) |
| (derived) | `detail_level` | MAPPED — partition-file split (schools/districts/states.parquet), dropped from columns per domain convention |

No gold column lacks a bronze ancestor — no fabrication.

## Value-Level Spot Checks

All 18 traces MATCH (bronze quoted verbatim; gold from parquet):

**Extremes first (4a)** — global min and max of the only metric:

| Trace | Bronze (file, row) | Gold | Verdict |
|---|---|---|---|
| Global min | FY2017 School: `633, Cobb County, " 0281 - Dickerson Middle School", 5` | 2017/633/0281 `reported` 0.05 | MATCH |
| Global min | FY2017 School: `644, DeKalb, " 0314 - GLOBE Academy Charter School I", 5` | 2017/644/0314 `reported` 0.05 | MATCH |
| Global min | FY2022 School: `656, Fayette, " 0199 - Peeples Elementary School", 5` | 2022/656/0199 `reported` 0.05 | MATCH |
| Global max | FY2026 School: `601, Appling, " 5050 - Fourth District Elementary", 95` | 2026/601/5050 `reported` 0.95 | MATCH |
| Global max | FY2026 School: `699, Meriwether, " 4050 - Manchester High School", 95` | 2026/699/4050 `reported` 0.95 | MATCH |

Min/max file locations confirm structure-doc Correction 5 (min 5.0 in FY2017+FY2022 School; max 95.0 incl. FY2026 School).

**Ordinary traces (4b)** — first year, mid, last year, every detail level:

| Trace | Bronze | Gold | Verdict |
|---|---|---|---|
| FY2013 district | `761, Atlanta Public Schools, 75.31` | 2013/761/NULL `reported` 0.7531 | MATCH |
| FY2024 district | `620, Camden County, 53.31` | 2024/620/NULL `reported` 0.5331 | MATCH |
| FY2024 school | `715, Polk, " 0102 - Rockmart High School", 61.01` | 2024/715/0102 `reported` 0.6101 | MATCH |
| FY2026 7-digit charter district | `7830616, Genesis Innovation Academy for Girls, *` | 2026/7830616/NULL `suppressed_privacy_band` NULL | MATCH (7-digit code passes zfill(3) untruncated) |
| FY2013 state | `' ', State-Wide Total, 59.59` | 2013/NULL/NULL `reported` 0.5959 | MATCH |
| FY2024 state | `' ', State-Wide Total, 63.69` | 2024/NULL/NULL `reported` 0.6369 | MATCH |
| FY2026 state | `' ', State-Wide Total, 68.6` | 2026/NULL/NULL `reported` 0.686 | MATCH |

**Suppression semantics (4f)** — one trace per marker type, plus ALL six `NA` cells:

| Trace | Bronze | Gold | Verdict |
|---|---|---|---|
| `*` | FY2024 School: `706, Muscogee, " 4070 - Wynnton Elementary", *` | 2024/706/4070 `suppressed_privacy_band` NULL | MATCH |
| `#` | FY2024 District: `7830618, SAIL Charter Academy, #` | 2024/7830618/NULL `not_participating` NULL | MATCH |
| `NA` ×6 | FY2016 District `7820613` Foothills Regional, `7820616` GA School for Innovation; FY2016 School `658/0219` Forsyth Virtual Academy, `703/0114` Montgomery Academy, `7820613/0613`, `7820616/0616` — all `NA` | all six: `not_participating`, rate NULL | MATCH (confirms Correction 1: NA is FY2016-only, 2+4 cells) |

**Sentinel year-attribution (4c)**: N/A as a risk — no year exists in any data row; year is filename-only. I re-verified the preamble year == filename year for all 28 files (the transform also raises on mismatch).

**Aggregate feasibility screen (4d)** — aggregates COME FROM BRONZE (state row published in District files; district rows published, never derived). For a rate metric, a published district rate must lie within [min, max] of its school rates when every school row is published: **1,456 (year, district) groups with ≥2 schools and zero suppressed/non-participating school rows → 0 violations** (±0.005 rounding tolerance). State-level screen: the state rate lies within the published district min/max in all 14 years. No impossibly-low/high aggregates anywhere.

**Dedup tie-break (4e)**: N/A — single era, no overlap years; entity-grain duplicate groups = 0 (verified directly on gold).

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning** — `contract_parquet_schema` (42 files), `contract_quality_sql` (9/9), `grain_uniqueness`, `foreign_keys` (district_code → districts: all 250 keys; school_code → schools: all 2,568 keys), geography nulling ×3 all pass. No warnings to explain (the anticipated FY2025/FY2026 null-spike warning did not trigger at threshold).
- **schema_hash**: `3a1e4394f33288dc91c72a06d9977bce94215412ce53a5277dab6094a4047f42`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no `masked_values` section — consistent, since the bronze published range is exactly [5.0, 95.0] (re-verified globally) and nothing is impossible. PASS.
- **§15b coverage judgment**: the contract's 6 authored checks pin the topic's real invariants — the full 3-way co-null lattice (`reported_status_has_rate`, `suppressed_privacy_band_has_null_rate`, `not_participating_has_null_rate`), `reporting_status_never_null` (closed bronze vocabulary), the [0.05, 0.95] publication band (±1e-6), and `one_state_row_per_year`. I independently re-derived the lattice from parquet: exactly {reported→26,561 non-NULL, suppressed→7,952 NULL, not_participating→628 NULL} with zero off-lattice rows. No missing obvious invariant. PASS.
- **v1 parity (5d)**, executed output verbatim:

  ```
  MATCH — byte-identical with v1 gold
  hash: f24b85108b73abad743b0f345c4aae7db649d04af14bc34abe0c92bbf1428a1c
  ```

## Cross-Era Consistency

Single era (one layout, FY2013-FY2026) — no overlap years, no era boundaries. Cross-year NULL sweep: **no era-localized NULL columns** (Risk 2 ruled out). Year-over-year continuity: state rate moves smoothly (0.596 → 0.62-0.62 plateau → 0.4534 in FY2022 → 0.5931 → 0.686), with one real dip — **FY2022 state 0.4534 is the source's own value** (bronze FY2022 District line 228: `" ,State-Wide Total,45.34"`), the SY2021-22 USDA universal-meal-waiver year when FRL applications collapsed; the dip appears coherently at all three detail levels (district mean 0.493, school mean 0.4246) and reverts in FY2023, so it is publication reality, not a transform artifact. FY2022 also shows the `#` spike (144 school cells, vs 10-64 in other years) — same CEP/waiver mechanism, all correctly traced to `not_participating`. Elevated FY2025/FY2026 `*` suppression (977/1,055 rows) matches the bronze census exactly — real, per expanded CEP coverage.

## Transform Logic Risks

| Risk (Step 7 / 5b) | Severity | Verdict — details |
|---|---|---|
| Silent column drops | none | PASS — only ` System Name` (dimension attribute) excluded; `_require_columns` raises on missing bronze columns |
| Era routing | none | PASS — single era; strict filename regex raises on unknown files; District/School dispatch on the filename group |
| Filter logic | none | PASS — zero filters, `total_filtered=0`, 1:1 bronze→gold |
| Normalization map completeness | none | PASS — map covers the verified-closed marker space {`*`,`#`,`NA`}; unknown marker → NULL status, which fails BOTH the unmapped guard and `validate_output(required_non_null=...)` |
| `strict=False` casts | none | PASS — the single `strict=False` cast is the marker-detection mechanism; every non-numeric outcome is explicitly routed to a status, with two loud backstops |
| Dedup keys + tie-break | none | PASS — `assert_no_natural_key_collisions` runs BEFORE dedup with `reporting_status` as a divergence metric; dedup is a verified no-op (0 duplicate entity keys in gold) |
| Year extraction | none | PASS — filename regex + preamble cross-check (all 28 verified in this review); footer shape pinned exactly so the slice can never eat data rows |
| §4b masks | none | PASS — none exist; none needed (bronze range exactly [5.0, 95.0]) |

Risk hypotheses 1 (Asian/PI) and 6 (mutual exclusivity): **N/A — no demographic column** (source publishes a single overall K-12 rate; column correctly omitted per §5). Risks 2, 3, 4, 5, 7: ruled out above with executed evidence.

## Notes

- schema_hash `3a1e4394f33288dc91c72a06d9977bce94215412ce53a5277dab6094a4047f42`; validation 21/21 pass, 0 warnings; v1 parity MATCH (hash `f24b8510…1428a1c`).
- The contract grain (`year, district_code, school_code, reporting_status`) includes the categorical per the emitter's standard auto-derivation. The true entity grain (`year, district_code, school_code`) is strictly tighter and is enforced at build time by `assert_no_natural_key_collisions`; I verified 0 duplicate entity-key groups directly on gold. Standard pattern across topics — no action.
- The footer Notice literally defines only `*` and `NA`; `#` (622 of the 628 non-participation cells) is undefined in-file. Its `not_participating` reading rests on the structure doc's source-legend note, the entity types it flags, and FY2016's NA/`#` equivalence — and is the same call v1 shipped (byte-identical). Recorded here for provenance; not a fix.
- Detail-level row totals: 32,109 school / 3,018 district / 14 state (one state row per year, all from District files' `State-Wide Total`; School files verified to carry none).
- Known environment issue (not topic-related): AWS profile `georgia-data-admin` is broken — S3 was not touched in this review.
