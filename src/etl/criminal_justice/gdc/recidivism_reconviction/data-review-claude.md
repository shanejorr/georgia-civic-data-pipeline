# Data Review: recidivism_reconviction

**Date**: 2026-07-07
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Every one of the 192 bronze matrix cells (2 editions x 8 rows x 12 cohort years) was independently re-parsed from the source PDFs and matches its gold row exactly after the /100 proportion conversion — zero value mismatches, zero missing or extra rows. All categorical recodes (11 raw facility-type stubs, 2 sex labels, 2 report titles) are semantically correct and fully covered by the manifest. v1 parity is N/A: `docs/rebuild/v1-baseline.yaml` contains no `criminal_justice` entries (new domain, first build), so the parity script's `DIFFERS from v1 / v1: None` output means "no baseline", not a divergence. No required fixes and no judgment calls.

## Manifest Verification

Preconditions: FRESH (transform mtime 04:06:26 < manifest 04:17:18 < validation 04:17:18 UTC, 2026-07-07), `passed: true`, 0 read-loss events (raw==parsed parity no-ops per file; the exact-shape parse guards are the read-loss protection).

| Column | Map entries | Bronze values seen | Unmapped | Status |
|--------|------------|--------------------|----------|--------|
| demographic | 2 | 2 (`All`, `Female`) | 0 | PASS |
| facility_type | 11 | 11 | 0 | PASS |
| reporting_period | 2 | 2 (report titles) | 0 | PASS |

**demographic** (via `normalize_demographic_column` / `DEMOGRAPHIC_ALIASES` — no hardcoded map):

| Bronze | Gold | Correct? |
|--------|------|----------|
| `All` | `all` | Yes — non-female rows cover the full cohort (both sexes) |
| `Female` | `female` | Yes — the female-only block |

**facility_type** (raw stubs, `**` stripped + casing normalized before recode):

| Bronze | Gold | Correct? |
|--------|------|----------|
| `All inmate facilities **` | `all` | Yes — rollup row → aggregation lane |
| `All Female Facilities **` | `all` | Yes — female rollup → aggregation lane (sex carried by `demographic`) |
| `All female facilities **` | `all` | Yes — FY lowercase variant of the same stub |
| `Private prisons` | `private_prison` | Yes |
| `State prison, IBCs` | `state_prison_ibc` | Yes — IBC = Inmate Boot Camp per the structure doc |
| `Female State prison, IBCs` | `state_prison_ibc` | Yes — female block, same facility type |
| `Female state prison, IBCs` | `state_prison_ibc` | Yes — FY casing variant |
| `County CI` | `county_ci` | Yes — CI = County Correctional Institution |
| `Transition centers` | `transition_center` | Yes |
| `Female Transition centers` | `transition_center` | Yes |
| `Female transition centers` | `transition_center` | Yes — FY casing variant |

**reporting_period** (bronze value = printed report title; edition detection is content-based, cross-checked against the axis caption):

| Bronze | Gold | Correct? |
|--------|------|----------|
| `CY Recidivism Rates (Felony Reconviction)` | `calendar_year` | Yes |
| `FY Recidivism Rates (Felony Reconviction)` | `fiscal_year` | Yes |

- **2a Completeness**: all 8 canonical row stubs from the structure doc's row-label table appear in `bronze_values_seen` (11 raw variants = 8 CY forms + 3 FY lowercase variants, exactly the casing drift the structure doc documents). No documented value went unencountered.
- **2c Contract cross-check**: `gold_values_produced` = contract enums exactly — `demographic` {all, female}, `facility_type` {all, county_ci, private_prison, state_prison_ibc, transition_center}, `reporting_period` {calendar_year, fiscal_year}.
- **2d Unmapped**: 0 for all three columns; the transform additionally uses `replace_strict` (raises on unmapped) plus an exact-label-set assertion.
- **2e Asian/PI conflation**: **N/A** — `gold_values_produced` for `demographic` is {all, female}; the source has a sex axis only (no race buckets, no `pct_asian` column).
- **2f Mutual exclusivity**: **PASS — single convention.** Only `all` and `female`; `all` is the permitted total-overlap row and no male rows are published or synthesized (verified: bronze prints no male-only stubs).

**Row-count reconciliation**:

| Year | Bronze | Gold | Filtered | Expansion |
|------|--------|------|----------|-----------|
| 2011 | 8 | 8 | 0 | 1.00x |
| 2012–2022 (each) | 16 | 16 | 0 | 1.00x |
| 2023 | 8 | 8 | 0 | 1.00x |
| **Total** | **192** | **192** | **0** | — |

2011 appears only in the CY edition and 2023 only in the FY edition (8 rows each); overlap years 2012–2022 carry 8+8=16. Actual parquet row sum = 192 = manifest `total_gold`. Year floor (>= 2000) dropped 0 rows, consistent with published cohorts 2011–2023.

## Column Coverage

| Bronze element | Gold column | Status |
|----------------|-------------|--------|
| column header year | `year` | MAPPED (Int32, from in-table headers) |
| CY vs FY edition (report title) | `reporting_period` | MAPPED |
| row stub — facility part | `facility_type` | MAPPED |
| row stub — female block | `demographic` | MAPPED (structure doc's "sex / demographic" option — demographic chosen, giving the dimension FK) |
| cell value (0–100 percent) | `reconviction_rate_3yr` | MAPPED (÷100, `unit: proportion`, key_metric) |
| geography | — | CORRECTLY EXCLUDED (statewide-only source; no `county_fips` column at all, per structure doc "county_fips = NULL / statewide only") |
| header date stamp (`Date: 01/06/2026` / `Date: 07/01/2026`) | — | CORRECTLY EXCLUDED (report print date, not data) |

Note: the structure doc suggested gold values `calendar` / `fiscal`; the transform serves `calendar_year` / `fiscal_year`, documented in-code as prescribed for sibling-topic consistency — a deliberate, clearer refinement, not a mismatch.

## Value-Level Spot Checks

**Exhaustive reconciliation (supersedes sampling).** All 192 cells were independently re-parsed from both PDFs (pdfplumber with an independent regex + label map written for this review) and compared to gold at 1e-9 tolerance: **ALL 192 CELLS MATCH**, zero gold rows without a bronze cell, zero bronze cells missing from gold.

Extreme and ordinary traces, individually evidenced:

| Trace | Bronze (quoted) | Expected | Gold | Verdict |
|-------|------------------|----------|------|---------|
| Global max | FY row `State prison, IBCs 27.70 ... 33.70 33.90` — last column FY 2023 = **33.90** | 0.339 | (2023, all, fiscal_year, state_prison_ibc) = 0.339 | MATCH |
| Global min | FY row `Female transition centers 12.90 ... 9.70 14.00` — 11th column FY 2022 = **9.70** | 0.097 | (2022, female, fiscal_year, transition_center) = 0.097 | MATCH |
| Ordinary, CY edition | CY row `All inmate facilities ** 26.90 ...` — first column CY 2011 = **26.90** | 0.269 | (2011, all, calendar_year, all) = 0.269 | MATCH |
| Ordinary, FY edition | FY row `All female facilities ** 19.30 ...` — first column FY 2012 = **19.30** | 0.193 | (2012, female, fiscal_year, all) = 0.193 | MATCH |
| Contract example | CY row `All inmate facilities ** ... 31.10` — last column CY 2022 = **31.10** | 0.311 | (2022, all, calendar_year, all) = 0.311 | MATCH (matches the contract's `example: 0.311`) |
| Female-rollup anomaly cited in contract | CY 2012: `All Female Facilities ** ... 20.80`, members `Female State prison, IBCs ... 20.60`, `Female Transition centers ... 19.80` | rollup 0.208 > both members | gold 0.208 / 0.206 / 0.198 | MATCH — the contract's non-exhaustiveness evidence is faithful to bronze |

- **4c Sentinel year-attribution**: PASS. Years come from the in-table column headers, never the filename or file year (filenames carry no year). Proof: cohort 2011 exists only under `calendar_year` and 2023 only under `fiscal_year`, exactly matching each file's header row; the manifest's per-file `year` (2022/2023) is only the max-cohort label for bookkeeping.
- **4d Aggregate-row reconciliation**: aggregates COME FROM BRONZE (the `**` rollup rows). Feasibility screen = the contract's `full_cohort_rollup_within_member_range` quality check (rollup within [member_min, member_max] ± 0.001 for all 24 full-cohort groups) — passing in `_validation.json`. The female rollup is correctly excluded from the bracket (CY 2012 counter-example above) and the exclusion is documented in the contract instead. No derived aggregation exists (no `.mean()` on percentages anywhere).
- **4e Dedup tie-break**: **N/A** — the two files' rows are disjoint on `reporting_period` by construction; no natural-key overlap exists. The collision guard (`assert_no_natural_key_collisions`) runs before the safety-net dedup and would raise on divergence.
- **4f Suppression semantics**: **N/A** — every cell in both matrices is populated (verified by the 192/192 reconciliation); `suppressed_to_null: false`; the `reconviction_rate_present` quality check enforces zero NULLs.

## Validation Cross-Read

- `_validation.json` (2026-07-07T04:17:18Z): **19 pass / 0 fail / 0 warnings**, `passed: true`. `contract_parquet_schema`, `contract_quality_sql` (all 10), `grain_uniqueness` (year, demographic, reporting_period, facility_type), and `foreign_keys` (demographic → demographics, 2/2 keys) all pass.
- `schema_hash`: `a6ed7bbae00fe7481f49c9830e33ec6bdf51e727869e34ccef85edf96c523ae2`
- **§4b masking audit**: no `_null_*` helpers in transform.py, no `masked_values` section in the manifest — consistent. The transform deliberately replaces defensive masking with parse-time hard-fails (out-of-range value ⇒ ValueError, since misalignment is likelier than a GDC publication error on a fixed layout) — the right call for this source; documented in the module docstring and contract.
- **§15b coverage judgment**: ADEQUATE. The 5 authored checks (year floor, no-NULL rate, exactly 8 rows per cohort-edition, full-cohort rollup within member range, female rows only under published facility types) plus the 5 auto-derived checks cover this topic's real invariants: shape, completeness, the only bracketable aggregate relationship, and the label-recode failure mode. No obvious missing invariant (rates are non-summable, so no partition-sum check is possible).
- **v1 parity** (verbatim): `DIFFERS from v1` / `v1:  None` / `now: 76ea640ec07e12e266be94155048cbe703990bf1dc7825918f2864052df6f1b7` — `docs/rebuild/v1-baseline.yaml` has **no entry** for this topic (no `criminal_justice` keys at all), so parity is **N/A — new topic/domain**, not a regression.
- **Contract prose fidelity**: checked against `bronze-data-structure.md` — year ranges (CY 2011–2022, FY 2012–2023), no-suppression claim, proportion scale, sex-only demographic convention, `**`-marker-undefined note, reconviction-vs-re-arrest caveat, and the CY 2012 female-rollup figures (20.8 vs 20.6/19.8) all agree with bronze. No contradictions.

## Cross-Era Consistency

- **Overlap years**: 2012–2022 appear in both editions but under disjoint `reporting_period` values — both series correctly co-exist (e.g., 2012 all/all: CY 0.266 vs FY 0.270, each matching its own bronze cell).
- **Cross-year NULL sweep**: no column ≥95% NULL in any year (no columns have NULLs at all).
- **Year-over-year continuity**: per-edition mean rate moves smoothly (calendar_year 0.20–0.26; fiscal_year 0.20–0.27); no >10x jumps, no revert-style level shifts. The 2018–2019 dip and post-2020 rise are consistent across both editions (coherent with the source, not a parse artifact).

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Exact-shape guards: 1 page, single known title + axis-caption cross-check, 12 consecutive year columns, exact 8-label set, 12 values per row — any deviation raises |
| Era routing correctness | PASS | Edition detected from printed title, cross-checked against the axis caption; never filename-based; one-of-each-edition assertion in `main()` |
| Filter logic logged + justified | PASS | Only the year >= 2000 floor; 0 rows dropped (logged); drops would be manifest-recorded via `record_filtered` |
| Normalization map completeness | PASS | 11 observed raw stubs ↔ 8 canonical keys, all in the structure doc incl. FY casing drift; label-set assertion catches any new/renamed stub |
| `strict=False` casts | PASS | None; `replace_strict` used for both recodes (raises on unmapped) and the unmatched-demographic sentinel check raises |
| Dedup keys + tie-break | PASS | Duplicates impossible by construction; collision guard raises first; `deduplicate_by_levels(sort_col="reconviction_rate_3yr")` is a documented safety net only |
| Year extraction | PASS | From in-table column headers with consecutive-run assertion; verified by edition-specific year coverage (2011 CY-only, 2023 FY-only) |
| §4b masks (5b) | PASS | None used; parse-time hard-fail is the documented, appropriate alternative for a fixed-layout born-digital PDF |

## Notes

- schema_hash: `a6ed7bbae00fe7481f49c9830e33ec6bdf51e727869e34ccef85edf96c523ae2`
- Validation: 19 pass / 0 fail / 0 warnings (2026-07-07); manifest and validation fresh relative to transform.py mtime; 0 read-loss events.
- The exhaustive 192-cell reconciliation used an independently written parser (separate regex + label map from the transform's) — agreement is therefore evidence about the data, not a tautology of the transform's own code path.
- Caveat for consumers (already in the contract): rates only, no cohort sizes — nothing here can be summed, weighted, or converted to counts; never pool `calendar_year` with `fiscal_year`.
