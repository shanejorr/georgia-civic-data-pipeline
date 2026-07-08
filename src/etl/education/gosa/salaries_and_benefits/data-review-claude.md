# Data Review: salaries_and_benefits

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

The transform reproduces bronze faithfully: all 12 value-level traces MATCH exactly
(dollars verbatim, percentages ÷100, negatives preserved), both categorical maps are
complete and semantically correct, and **v1 parity is MATCH — byte-identical with v1
gold** (`f4b80fd9…`). Two required fixes: a missing `state_rows_present_every_year`
quality check (MEDIUM — the symmetric RESA-presence check exists but state-rollup
presence is unpinned) and a false docstring claim about comma-grouped bronze values
(LOW — zero exist in all 14 files). One judgment call: the 2021 file is ~2× across
**all** metrics — dollars included (94.2% of districts at ≈2× their 2020/2022
average) — so the contract's "pandemic-year base effect" narrative for the >1.0
ratios likely understates a source-side two-year-cumulative publication anomaly.

## Manifest Verification

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| `detail_level` (Era 2 only) | 3 | 3 (`DOE OTHER`, `District`, `State`) | 0 | PASS |
| `staff_category` | 3 | 3 | 0 | PASS |

Full map review — every entry:

| Bronze → Gold | Correct? |
|---------------|----------|
| `State` → `state` | YES — Era 2 explicit state rollup; matches Era 1's `SCHOOL_DSTRCT_CD='ALL'` derivation |
| `District` → `district` | YES |
| `DOE OTHER` → `district` | YES — verified the DOE OTHER code set in 2023+2024 is exactly the 16 RESA codes `850 852 854 856 858 860 862 864 866 868 872 876 880 884 886 888`, and **zero** 85x–88x codes appear under the `District` label; routing to district detail matches the documented cross-topic convention (districts dimension types all 16 as `resa`, census ID NULL — verified) |
| `General Administration` → `general_administration` | YES |
| `School Administration` → `school_administration` | YES |
| `Teachers and Paraprofessionals` → `teachers_and_paraprofessionals` | YES |

- 2a completeness: every distinct bronze value documented in `bronze-data-structure.md`
  appears in `bronze_values_seen`; no documented value went unencountered.
- 2c contract cross-check: `staff_category` `gold_values_produced` == contract `enum`
  (3 values). `detail_level` is not a contract column (dropped at export; encoded as
  `districts`/`states` files — matches the contract's `detail_levels` property).
- 2d: `unmapped_count` = 0 for both columns.
- 2e Asian/PI conflation: **N/A** — gold has no `demographic` column and no `pct_asian`
  column (triage rule).
- 2f mutual exclusivity: **N/A** — no demographic column; PASS — single convention.

Row-count reconciliation:

| Year | Bronze | Gold | Filtered | Expansion |
|------|--------|------|----------|-----------|
| 2011 | 618 | 618 | 0 | 1.0 |
| 2012 | 627 | 627 | 0 | 1.0 |
| 2013 | 636 | 636 | 0 | 1.0 |
| 2014 | 630 | 630 | 0 | 1.0 |
| 2015 | 627 | 627 | 0 | 1.0 |
| 2016 | 651 | 651 | 0 | 1.0 |
| 2017 | 657 | 657 | 0 | 1.0 |
| 2018 | 657 | 657 | 0 | 1.0 |
| 2019 | 672 | 672 | 0 | 1.0 |
| 2020 | 678 | 678 | 0 | 1.0 |
| 2021 | 678 | 678 | 0 | 1.0 |
| 2022 | 711 | 711 | 0 | 1.0 |
| 2023 | 723 | 723 | 0 | 1.0 |
| 2024 | 747 | 747 | 0 | 1.0 |

Assessment: 1:1 bronze→gold in every year, zero filtering, zero read loss
(manifest has no `read_loss` events). Total gold parquet rows counted directly:
**9,312 = manifest `total_gold` = manifest `total_bronze`**. Counts match the
structure doc's stated ranges (Era 1: 618–711; Era 2 adds 48 RESA rows). All 14
expected years present, no gaps.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|------------|--------|
| LONG_SCHOOL_YEAR | `year` | MAPPED (ending year, cross-checked vs filename) |
| SCHOOL_DSTRCT_CD | `district_code` | MAPPED (`ALL` → NULL state rows; zfill(3); RESAs kept at district detail) |
| SCHOOL_DSTRCT_NM | — | CORRECTLY EXCLUDED (districts dimension) |
| INSTN_NUMBER | — | CORRECTLY EXCLUDED (constant `ALL`; verified by doc) |
| INSTN_NAME | — | CORRECTLY EXCLUDED (constant `All Column Values`) |
| #RPT_NAME (Era 2) | — | CORRECTLY EXCLUDED (constant; guarded by `_validate_era2_constants`) |
| DETAIL_LVL_DESC (Era 2) | — | CORRECTLY EXCLUDED (routing only; detail level encoded in file split) |
| GRADES_SERVED_DESC (Era 2) | — | CORRECTLY EXCLUDED (near-constant institution metadata; NULL for RESAs) |
| CATEGORY | `staff_category` | MAPPED |
| SALARIES | `salaries_dollars` | MAPPED |
| BENEFITS | `benefits_dollars` | MAPPED |
| SALARIES_AND_BENEFITS | `salaries_and_benefits_dollars` | MAPPED |
| % Rev- GF/Title/Lottery / REV__GF/TITLE/LOTTERY | `pct_revenue_gf_title_lottery` | MAPPED (÷100, era-routed) |
| % Rev- Total K-12 / REV__TOTAL_K_12 | `pct_revenue_total_k12` | MAPPED (÷100, era-routed) |
| % Exp- GF/Title/Lottery / EXP__GF/TITLE/LOTTERY | `pct_expense_gf_title_lottery` | MAPPED (÷100, era-routed) |
| % Exp-Total K-12 / EXP_TOTAL_K_12 | `pct_expense_total_k12` | MAPPED (÷100, era-routed) |

No gold column lacks a bronze source (`school_code` is the convention-mandated
always-NULL key column, pinned by `school_code_always_null`). Note: the structure
doc's classification suggested *dropping* state and RESA rows; the transform keeps
both (state → `states.parquet`, RESA → district detail), which the doc itself
acknowledges as the current cross-topic convention — deviation justified and
documented in contract `limitations`.

## Value-Level Spot Checks

All traces: bronze line quoted → expected transform → gold value. **12/12 MATCH.**

Extreme rows first:

1. **Global max all dollar metrics — 2021 state Teachers** (`salaries_and_benefits_2021.csv`):
   `"2020-21","ALL",…,"Teachers and Paraprofessionals",14132075066.24,6844371451.55,20976446517.79,100.52,82.86,107.98,89.34`
   → gold year=2021, district NULL: `14132075066.24 / 6844371451.55 / 20976446517.79`,
   pct `1.0052 / 0.8286 / 1.0798 / 0.8934`. **MATCH** (see Judgment Call 1 on the level itself).
2. **Global min benefits — 2022 Cherokee Charter** (line 534, 2022 file):
   `"7820212",…,"School Administration",322236.65,-191629.6,130607.05` → gold
   `-191629.6`, total `130607.05` (reconciles: 322236.65 − 191629.6). **MATCH**.
3. **2011 negative benefits — Baker 604** (line 12): `167441.17,-46332.52,121108.65` → gold exact. **MATCH**.
4. **2012 negative benefits — Toombs 738** (line 413): `50454.01,-43127.9,7326.11` → gold exact. **MATCH**.
5. **Global min salaries — 2024 charter 7830619** (line 602, Era 2 quoted format):
   `"-2000","25409.58","23409.58",".44",".43",".4",".39"` → gold `-2000.0 / 25409.58 / 23409.58`,
   pct `0.0044 / 0.0043 / 0.004 / 0.0039` — leading-dot decimal strings cast correctly. **MATCH**.
6. **Global max pct — 2021 Forsyth 658** (line 175): `…,122.53,101.23,127.31,90.44`
   → gold `1.2253 / 1.0123 / 1.2731 / 0.9044`. **MATCH** (manifest 2021 max 1.2731 ✓).
7. **2017 outlier pct — Cartersville 767** (line 496): `…,54.73,44.14,90.7,72.6` →
   gold `0.5473 / 0.4414 / 0.907 / 0.726`. **MATCH** — the 2017 max 0.907 is in-bronze, preserved.

Ordinary traces (one per era + RESA in both eras):

8. **Era 1, 2022 — Charlton 624 Teachers**: bronze `6204434.85,3059444.6,9263879.45,41.83,37.27,45.58,40.58` → gold exact (pct ÷100). **MATCH**.
9. **Era 1, 2011 — Appling 601, all 3 categories**: e.g. General Administration
   `195022.05,91043.77,286065.82,0.88,0.76,0.99,0.91` → gold exact. **MATCH** (3/3 rows).
10. **Era 2, 2024 — Savannah-Chatham 625 Teachers**: bronze `"187068750.62","100872639.23","287941389.85","41.26","33","46.77","35.9"` → gold exact. **MATCH**.
11. **Era 2, 2024 — Metro RESA 856 (DOE OTHER), all 3 categories**: e.g. Teachers
    `"1024979.9","587756.72","1612736.62","10.57","10.57","10.36","10.36"` → gold at
    district detail, exact. **MATCH** (3/3 rows).
12. **Era 1, 2011 — RESA 854 (Pioneer, bare code)**: General Administration
    `375146.71,121094.94,496241.65,7.62,7.62,7.41,7.41` → gold exact, incl. the
    all-zero School Administration row preserved as real zeros. **MATCH** (3/3 rows).

- **4c sentinel year-attribution**: gold `year` derives from the in-string
  `LONG_SCHOOL_YEAR` ending year (`parse_school_year`), hard-cross-checked against the
  filename year (raises on disagreement). Trace: 2011 file rows carry `"2010-11"` →
  gold `year=2011`. **PASS**.
- **4d aggregates come from bronze — feasibility screen**: per (year, staff_category),
  sum of non-RESA district `salaries_and_benefits_dollars` vs the published state row:
  ratio range **[0.9772, 1.0308]**; 10 of 42 category-years deviate >2% (max 3.1%, all
  in general/school administration). In 2011–2013 the state row equals the sum
  *including* RESAs exactly (9/9 category-years), in later years it sits between the
  incl/excl sums — the source's rollup composition drifted. No entity-level swap or
  garble signature; the contract `limitations` already warns against summing district
  rows to reproduce the state rollup. **PASS with caveat** (see Notes).
- **4e dedup tie-break**: **N/A** — 14 files, 14 distinct years (manifest
  `files_processed`), no overlap; `assert_no_natural_key_collisions` runs before dedup.
- **4f suppression**: **N/A** — no suppression markers anywhere (structure doc +
  zero NULLs in all 7 metrics in all years, pinned by `metrics_never_null`).

## Validation Cross-Read

- `_validation.json` 2026-06-10T17:08:26Z: **20 pass / 0 fail / 0 warning**, including
  `contract_parquet_schema` (28 files), `contract_quality_sql` (11 checks),
  `grain_uniqueness` (year, district_code, school_code, staff_category), and
  `foreign_keys` (all 254 district keys resolve; school_code never populated).
- `schema_hash`: `9382b972c0107d427932df1c149dd4585fa8a0e96a310849bedb7a92b95c937f`
- **§4b masking audit**: no `_null_*` helpers in transform.py, no `masked_values`
  manifest section — consistent. Negatives are preserved (not masked) and documented
  in both the contract column descriptions and `notes`; verified counts match the
  documentation exactly: `salaries_dollars < 0` → {2024: 1}; `benefits_dollars < 0`
  → {2011: 1, 2012: 1, 2022: 1}; total never negative. `unit: currency` correctly
  derives no range check. **PASS**.
- **§15b coverage judgment**: authored checks pin component reconciliation,
  school_code-always-NULL, metrics-never-null, 3-categories-per-entity, and
  RESA-presence-every-year — good coverage of the real invariants, **except** the
  symmetric state-rollup presence (see Fix 1). `staff_category_complete_per_entity`
  cannot catch a wholly missing state group (its `HAVING` only evaluates groups that
  exist).
- **v1 parity (verbatim)**: `MATCH — byte-identical with v1 gold`
  (baseline `approved_gold_sha256: f4b80fd9feaa46d18f932ee4a076b8385a86c15e861d58a679fd71bbbd3a4621`, approved 2026-05-30).

## Cross-Era Consistency

- **Overlap years**: none (each file one school year; filename ↔ LONG_SCHOOL_YEAR enforced).
- **Era boundary (2022→2023)**: state-level means continuous (e.g. S&B mean 4.06B →
  4.43B; pct_expense_gf 0.187 → 0.192). No magnitude jumps at the boundary; the
  era-routed pct renames land in populated columns on both sides.
- **Cross-year NULL sweep**: **0 flags** — no column is ≥95% NULL in any year (all 7
  metrics 100% populated in all 14 years).
- **2021 anomaly (within Era 1, not an era artifact)**: all dollar AND ratio levels
  ≈2× adjacent years — escalated to Judgment Call 1.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `_require_columns` guards shared + era-specific pct headers per file; excluded columns verified constant/metadata |
| Era routing correctness | PASS | Signatures most-specific-first; manifest shows 12× era_1 (2011–2022), 2× era_2 (2023–2024) as documented |
| Filter logic | PASS | No filters; `total_filtered=0`, bronze==gold 1:1 |
| Normalization map completeness | PASS | All documented bronze values mapped; unmapped_count 0 (both maps) |
| `strict=False` casts | PASS | Residue would NULL silently, but `metrics_never_null` contract check makes any residue a hard validation failure |
| Dedup keys + tie-break | PASS | No-op by construction (no overlap years); collision guard raises before dedup can hide divergent duplicates |
| Year extraction | PASS | Single LONG_SCHOOL_YEAR per file enforced; filename cross-check raises on mismatch |
| §4b masking | PASS | No masks; negatives preserved and documented with verified counts |

## Required Fixes

### Fix 1: Author a `state_rows_present_every_year` quality check
- **Severity**: MEDIUM
- **Issue**: The contract pins RESA presence per year (`resa_rows_present_every_year`)
  but not the state rollup's presence. If a future bronze year omitted the `ALL` rows,
  nothing would fail: `staff_category_complete_per_entity` only evaluates groups that
  exist (`HAVING` on existing groups), and the validator passes with whatever detail
  files are present. The invariant "every year has exactly 3 state rows" is real,
  verified in all 14 current years, and currently unenforced.
- **Evidence**: Contract quality list (11 checks) has presence checks for RESAs but
  none for state rows; gold currently has exactly 3 NULL-district rows per year
  (verified via the feasibility screen joins, 42/42 category-years present).
- **Location**: `quality_checks` list in `_emit_contract_and_readme()` in `transform.py`
- **Suggested fix**: Add a quality check, e.g.
  `SELECT COUNT(*) FROM (SELECT year FROM {object} WHERE district_code IS NULL GROUP BY year HAVING COUNT(*) <> 3) AS bad_years`
  with `mustBe: 0` (additive contract change; parquet bytes unchanged).

### Fix 2: Correct the false comma-grouped-values claim in the transform docstring
- **Severity**: LOW
- **Issue**: The module docstring ("Era 1 dollar columns mix plain floats with quoted
  comma-grouped values (\"6,204,400\")") and `_to_float_expr`'s docstring assert a
  bronze format that does not exist. The claim appears inherited from the structure
  doc's *rounded display* sample (`6,204,400` vs actual bronze `6204434.85`).
- **Evidence**: `grep -cE '"[0-9]{1,3}(,[0-9]{3})+(\.[0-9]+)?"'` returns **0 for all
  14 bronze files**. Actual bronze: Era 1 numerics unquoted plain floats
  (`6204434.85,3059444.6,9263879.45`), Era 2 quoted plain floats (`"187068750.62"`).
- **Location**: module docstring (Design decisions, "All-string bronze read" bullet)
  and `_to_float_expr` docstring in `transform.py`
- **Suggested fix**: Reword to state no comma-grouped values were observed; keep
  `str.replace_all(",", "")` as an explicitly-labelled defensive no-op (or remove it —
  either way the docstring must match bronze reality). Doc-only change; gold bytes
  unaffected.

## NEEDS_JUDGMENT

### Judgment Call 1: 2021 file is ~2× across ALL metrics — "base effect" narrative likely understates a source publication anomaly
- **Severity if confirmed**: MEDIUM
- **Suspicion**: The contract and docstring explain the 2021 `pct_* > 1.0` values as a
  "systematic pandemic-year base effect" (spending exceeded the revenue/expenditure
  bases). But the **dollar columns double too**, which a denominator/base effect cannot
  cause. The far more plausible reading is that GOSA's 2021 file publishes two-year
  cumulative (or otherwise doubled) values; the >1.0 ratios are then a 2-year numerator
  over a 1-year base. Consumers reading only the current caveat would treat 2021 dollar
  levels as single-year actuals and 2021 trends as real.
- **Evidence available**: Bronze 2021 state Teachers row (quoted in trace 1):
  S&B `20,976,446,517.79` vs `10,527,043,552.44` (2020) and `10,894,197,190.41` (2022).
  State-level mean S&B by year: 3.92B (2020) → **7.80B (2021)** → 4.06B (2022).
  District-level: of 225 districts present 2020–2022, **94.2% have 2021 ≈ 2× their
  2020/2022 average (median ratio 1.962)** for Teachers S&B (DeKalb: 679M → 1.343B →
  641M). All four pct means double (e.g. pct_expense_gf 0.195 → 0.375 → 0.176). The
  144 over-100 rows and max 127.31 are verified in bronze. Row count is normal (678 =
  2020), so it is the values, not duplicated rows.
- **Why uncertain**: Bronze alone cannot prove GOSA's intent (no external source
  consulted). A genuine one-year doubling of statewide salary spending followed by
  reversion is implausible but not strictly impossible. Preserving bronze as published
  is correct either way (v1 byte-identical), so this is a documentation-accuracy
  question, not a data-change question.
- **Location**: `limitations` kwarg, `notes` list, and the four pct_* column
  descriptions in `_emit_contract_and_readme()` in `transform.py`
- **If confirmed, suggested fix**: Rewrite the 2021 caveat to state that **all 2021
  metrics — dollar levels included — run ≈2× adjacent years** (94% of districts at
  ≈2× their 2020/2022 average), consistent with a two-year cumulative publication;
  advise excluding 2021 from cross-year level/trend analysis. Drop or qualify the
  "category spending exceeded the bases that pandemic year" wording. Doc/contract-only
  change; gold bytes unchanged.

## Notes

- `schema_hash`: `9382b972c0107d427932df1c149dd4585fa8a0e96a310849bedb7a92b95c937f`;
  validation 20 pass / 0 fail / 0 warning; gold rows 9,312 across 28 parquet files
  (14 years × districts/states).
- **v1 parity: MATCH (byte-identical)** — the strongest single piece of evidence that
  the rebuild reproduces approved v1 gold.
- Contract descriptions' specific claims all verified against data: pct maxima
  1.2346 / 1.0413 / 1.2731 (+ state rollup 1.0798) / 1.2103; 144 over-100 rows in
  2021; negative-row counts and minima; component reconciliation within $1 (contract
  check passes).
- Structure-doc errata (do not block; doc not editable by this review): (1) RESA
  example pairings are wrong — actual bronze has 850=Northwest Georgia RESA,
  854=Pioneer RESA, 856=Metro RESA, 886=Coastal Plains RESA (doc claims 850=Pioneer,
  854=Metro, 860=Coastal Plains); code→name sets are otherwise identical in 2011 and
  2024. (2) Sample-data tables show rounded, comma-grouped display values that do not
  match raw bronze (source of Fix 2's false claim).
- State-rollup composition drift (informational): in 2011–2013 the state row equals
  the sum of all district rows including RESAs exactly; from 2020 on it deviates up to
  ~3–5% in the administration categories. The existing `limitations` warning covers
  this; a reconciliation quality check would be too brittle to author.
- Sibling-convention note: `revenues_and_expenditures` (cited for the RESA convention)
  has no rebuilt contract yet — only act_scores, dropout_rate_7_12, and this topic
  exist under `contracts/education/`. The convention reference is to v1.
