# Data Review: juvenile_court_cases

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Every executable check and value-level trace passed against the bronze JSON. All 4
categorical maps are semantically correct with zero unmapped values; all 17,114
suppression/unavailability masks re-count directly from bronze and match the manifest
and contract cell counts exactly; all 122 published state rates recompute exactly as
count ÷ reporting-population × 1000; and every extreme, ordinary, and
suppression-marker trace matched bronze verbatim. State/county reconciliation shows 0
violations of all three aggregate invariants across the 156 measure-years. **v1
parity: no v1 baseline (topic is post-v1)** — `criminal_justice/ojjdp/juvenile_court_cases`
has no entry in `docs/rebuild/v1-baseline.yaml`, so the script prints
`DIFFERS / v1: None`; this is the absence of a baseline hash, not a divergence. The
validator's 8 NULL-rate-spike warnings are fully explained by the documented
reporting-coverage collapse (152 → 25 → 41 counties).

## Manifest Verification

### Categorical maps

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| `case_type` | 6 | 6 (all 6 measures) | 0 | PASS |
| `petition_status` | 6 | 6 (all 6 measures) | 0 | PASS |
| `reporting_status` | 5 | 5 (all 5 shape markers) | 0 | PASS |
| `county_fips` | 160 | 160 (`0` + 159 odd fct) | 0 | PASS |

### Full map review (2b — every entry verified semantically)

**`case_type`** — EZACO measure suffixes: `del` = delinquency, `sta` = status offense, `dep` = dependency.

| Bronze | Gold | Correct? |
|--------|------|----------|
| `petdel` | `delinquency` | Yes |
| `nonpetdel` | `delinquency` | Yes |
| `petsta` | `status_offense` | Yes |
| `nonpetsta` | `status_offense` | Yes |
| `petdep` | `dependency` | Yes |
| `nonpetdep` | `dependency` | Yes |

**`petition_status`** — `pet` = petitioned, `nonpet` = non_petitioned.

| Bronze | Gold | Correct? |
|--------|------|----------|
| `petdel` | `petitioned` | Yes |
| `nonpetdel` | `non_petitioned` | Yes |
| `petsta` | `petitioned` | Yes |
| `nonpetsta` | `non_petitioned` | Yes |
| `petdep` | `petitioned` | Yes |
| `nonpetdep` | `non_petitioned` | Yes |

**`reporting_status`** — against the source legend (flag 0 = county did not report; flag 1 + numeric = reported; flag 1 + `*`/`x`/`z` = reported-but-suppressed-at-source).

| Bronze marker | Gold | Correct? |
|---------------|------|----------|
| `flag_0_unavailable` | `not_reported` | Yes |
| `flag_1_numeric` | `reported` | Yes |
| `flag_1_suppressed_star` | `suppressed` | Yes |
| `flag_1_suppressed_x` | `suppressed` | Yes |
| `flag_1_suppressed_z` | `suppressed` | Yes |

**`county_fips`** — 159 entries of the form `fct → "13" + zfill(3)` (spot-verified from the manifest map: `121 → 13121` Fulton, `89 → 13089` DeKalb, `59 → 13059` Clarke, `255 → 13255` Spalding, `1 → 13001`, `321 → 13321`), plus `0 → state_row_no_county_fips` (a deliberate non-FIPS marker for the state row, which is NULLed in gold). FK validation confirms all 159 resolve in the counties dimension.

**Contract cross-check (2c):** `gold_values_produced` equals the contract enum for `case_type` (`delinquency`/`dependency`/`status_offense`), `petition_status` (`non_petitioned`/`petitioned`), and `reporting_status` (`not_reported`/`reported`/`suppressed`). PASS.

**Unmapped (2d):** 0 for all four columns. PASS.

**Asian/PI conflation (2e) & mutual exclusivity (2f):** N/A — no demographic column; the source publishes no race/sex/age breakdowns (confirmed in `bronze-data-structure.md` §"Asian / Pacific Islander Check").

### Row-count reconciliation

| Year(s) | Bronze/file | Gold/year | Expansion | Assessment |
|---------|-------------|-----------|-----------|------------|
| all 26 years | 160 | 960 | exactly 6.0 | PASS — 6-measure unpivot; 0 filtered rows every year |

Manifest `total_bronze` = 4,160 (26 × 160), `total_gold` = 24,960 (26 × 960). **Actual parquet row count = 24,960 — equals manifest `total_gold`.** All 26 expected years present (1997–2023 minus 2014, the documented source gap). Read loss: 0 events.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| `yr` | `year` | MAPPED (verified equal to filename year on every row by `_verify_file_shape`) |
| `fct` (+`fst`) | `county_fips` | MAPPED (`"13"+zfill(3)`; state row → NULL) |
| `petdel`…`nonpetdep` (6) | `case_count` (tidy) | MAPPED (unpivot; markers → NULL) |
| (measure name) | `case_type`, `petition_status` | MAPPED (derived categoricals) |
| `reportingflag_*` (county rows) | `reporting_status` | MAPPED — richer 3-value status (flag + value shape) than the structure doc's suggested 0/1; exhaustively guarded |
| `reportingflag_*` (state row) | `counties_reporting` | MAPPED — structure doc hedged this as `not_in_gold`; transform serves it (justified: the headline coverage caveat; verified equal to the sum of county flags in all 156 measure-years) |
| `*rate` (6) | `case_rate_per_1000` | MAPPED — structure doc hedged `not_in_gold`; transform serves it as-published (state rows only, coverage-dependent denominator prominently documented) |
| `court` | — | CORRECTLY EXCLUDED (county name lives in the counties dimension) |
| `poptot`/`popten`/`popzero` | — | CORRECTLY EXCLUDED (denominators duplicated by the sibling juvenile_population topic) |
| `poptenpetdel`…`popzerononpetdep` (6) | — | CORRECTLY EXCLUDED (state-row rate denominators; documented in prose; used here to verify rates) |
| `state`/`st`/`fst`/`age`/`unit`/`unit_2`/`print_state`/`footnotes` | — | CORRECTLY EXCLUDED (constants/metadata; `age=16` and "cases disposed" carried into contract prose) |

No gold column lacks a bronze ancestor (no fabrication). The two columns the structure doc had hedged as `not_in_gold` (`case_rate_per_1000`, `counties_reporting`) trace to real bronze fields and are heavily caveated in the contract — a defensible enhancement, not a defect.

## Value-Level Spot Checks

All executed against the bronze JSON directly; every trace is a **MATCH**.

**Extreme rows (4a):**

| Trace | Bronze (quoted) | Gold | Verdict |
|-------|-----------------|------|---------|
| Global max `case_count` — 1997 state petdel | `petdel='61,619'`, `reportingflag_petdel=152`, `petdelrate='83.87'` | `case_count=61619`, `counties_reporting=152`, `case_rate_per_1000=83.87`, `reporting_status=None` | MATCH (comma-strip) |
| Global min `case_count`=0 — 1997 Baker (`fct=7`→`13007`) petsta | `petsta='0'`, `reportingflag_petsta='1'` | `case_count=0`, `reporting_status='reported'` | MATCH — real zero preserved, not NULLed |
| Global max rate — 1997 state petdel | `petdelrate='83.87'` | `83.87` (delinquency/petitioned) | MATCH |
| Global min rate — 2020 state nonpetdep | `nonpetdeprate='0.31'` (`nonpetdep='424'`) | `0.31` (dependency/non_petitioned) | MATCH |
| Global max `counties_reporting` — 2011 state petdel | `reportingflag_petdel='155'` (≤159) | `counties_reporting=155` | MATCH |

**Ordinary trace (4b) — one county, all 6 measures:** **Clarke 2023** (`fct='59'` → `13059`): `petdel='212'`→(reported, 212); `nonpetdel='100'`→(reported, 100); `petsta='29'`→(reported, 29); `nonpetsta='51'`→(reported, 51); `petdep='--'` flag `'0'`→(not_reported, NULL); `nonpetdep='--'` flag `'0'`→(not_reported, NULL). All 6 MATCH.

**Sentinel year-attribution (4c):** N/A/PASS — the row year comes from the filename (`path.stem.rsplit('_',1)[-1]`) and `_verify_file_shape` hard-stops if any row's `yr` differs; no year is parsed out of an embedded string. No misattachment surface.

**Aggregate feasibility (4d)** — state rows COME FROM BRONZE. Independent gold reconciliation across all 156 measure-years: `state_count < visible county sum` → **0 violations**; `state != county sum when 0 suppressed` → **0**; `counties_reporting != #reporting county rows` → **0**. Spot 1997 delinquency/petitioned: state `61619` = visible county sum `61612` + gap `7`, with `n_suppressed=3` cells (`*` = 1–4 each, feasible gap [3,12]) — matches the structure doc's "61,619 vs 61,612 visible + 3 suppressed". Spot 2023 delinquency/petitioned: `11708 == 11708`, 0 suppressed, exact.

**Dedup tie-break (4e):** N/A — one bronze file per year, one row per (county, measure) per file; no overlap years. `assert_no_natural_key_collisions` runs before the no-op safety-net dedup.

**Suppression semantics (4f)** — one trace per marker type:

| Marker | Bronze (quoted) | Gold | Verdict |
|--------|-----------------|------|---------|
| `*` | Spalding 2023 (`fct=255`) `petsta='*'` flag `'1'` | (suppressed, NULL) | MATCH |
| `x` | Dawson 2016 (`fct=85`→`13085`) `nonpetsta='x'` flag `'1'` | (suppressed, NULL) | MATCH |
| `z` | Dawson 2016 (`fct=85`→`13085`) `petdep='z'` flag `'1'` (the single `z` in the corpus) | (suppressed, NULL) | MATCH |
| `--` (county) | Putnam 2023 (`fct=237`→`13237`) `petdel='--'` flag `'0'` | (not_reported, NULL) | MATCH |
| `--` (state) | 2019/2021–2023 state dependency `--` flag `'0'` | `case_count=None`, `counties_reporting=0` | MATCH |

**Exhaustive rate verification:** all **122 published state-row rates** across all 26 files recompute as count ÷ measure-specific reporting population × 1000 (`popten<measure>` for delinquency/status offense, `popzero<measure>` for dependency): `122/122 within 0.05, 0 mismatches`. Confirms both the contract's "verified equal" claim and the coverage-dependent denominator semantics.

## Validation Cross-Read

- `_validation.json`: **passed** — 19 pass, 0 fail, 1 warning; `contract_parquet_schema` (52 files), `contract_quality_sql` (all 20 checks), `grain_uniqueness`, and `foreign_keys` (`county_fips -> counties: all 159 keys resolve`) all pass.
- `schema_hash`: `0e0036f7ce4fb3de8f7a72a1742fd9359de3fc305224d00bacdfe9495a4e39e7`.
- **Warning explained:** `null_rate_spikes` flags 8 years (2009, 2015–2017, 2019, 2021–2023) with `case_count` null rates 84–91% vs 61% median — the documented reporting-coverage collapse, not a defect: `counties_reporting` = 25 in 2009, 21–41 in 2015–2023 (vs 152 in 1997). Total gold `case_count` NULLs (17,114) equal the masked-value total exactly.
- **§4b masking audit (5b):** No `_null_*` §4b impossible-value masks exist (correct — after marker handling every value casts cleanly, hard-guarded by `_guard_value_vocabulary`). All 5 suppression/unavailability mask events are recorded in `masked_values`, and I re-counted every marker in bronze: `star=671, x=16, z=1, county--=16392, state--=34, total=17114` — **exact match** with the manifest and with the cell counts quoted in the contract's `reporting_status` description (671 / 16 / 1). Handling documented in `case_count.null_meaning` and the `reporting_status` description; range guards present (`unit: count` → ≥0 auto-check; authored `case_rate_per_1000_non_negative` for the unit-exempt rate).
- **§15b coverage judgment (5c):** Excellent — 14 authored consistency/completeness checks cover every real cross-column invariant: reporting_status↔NULL co-occurrence (3), state/county column partitioning (2), `counties_reporting` = sum of county flags, state-count↔zero-coverage iff, state ≥ visible county sum, state = county sum when unsuppressed, rate state-only, rate↔count co-null, rate ≥ 0, all-159-counties completeness, counties_reporting ≤ 159. No missing obvious invariant.
- **v1 parity (5d)** — output verbatim:

  ```
  DIFFERS from v1
    v1:  None
    now: ed8730cae531c3bc213ae949e3380cdcd04fecf995d04146742a401f41784f9b
  ```

  **No v1 baseline (topic is post-v1)** — the key is absent from `docs/rebuild/v1-baseline.yaml` (`v1: None`). Not a divergence.

## Cross-Era Consistency

- **Single era** (`ezaco_v1`): identical 38-key schema in all 26 files (manifest per-file `bronze_columns` all identical; per-row schema-drift guard in `_read_ezaco_json`). No era boundaries, no overlap years.
- **Cross-year NULL sweep (3c):** `case_count` — no ≥95%-NULL years (max 90.5% in 2015, coverage-explained). `case_rate_per_1000` and `counties_reporting` — ≥95% NULL in *every* year, which is **by design, not a rename bug**: both are state-row-only (6 of 960 rows/year ≈ 99.4% NULL), enforced by contract checks `rate_on_state_rows_only` / `counties_reporting_on_state_rows_only` and documented in each `null_meaning`. State pivot confirms the state values are fully populated. Investigated and cleared.
- **YoY continuity (3d):** no >10× adjacent-year jumps in any of the 6 state measure series; no spike-revert (cumulative-publication) signature. Zero-reporting years verified per measure and match the contract exactly: delinquency & status-offense **non-petitioned** = 0 counties in 1997–2000 and 2010–2013; **dependency petitioned** = 0 in 2015/2019/2021–2023; dependency non-petitioned = the union of both gaps (as expected). The 34 state `--` cells decompose accordingly.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `_read_ezaco_json` hard-stops on any key drift (extra/missing beyond the state row's absent `court`) per row |
| Era routing | N/A | Single era; signature guards a future API format change |
| Filter logic | PASS | Zero rows filtered (`total_filtered=0`); nothing to justify |
| Normalization map completeness | PASS | 6/6 measures, 5/5 shape markers, 160/160 fct values mapped; unmapped=0 |
| `strict=False` casts | PASS | Applied only after `_guard_value_vocabulary` whitelists every non-numeric cell (unknown non-numerics hard-stop), so `strict=False` can only NULL the four known markers |
| Dedup keys + tie-break | PASS | Duplicates impossible by construction; collision guard raises before the documented `sort_col="case_count"` safety net |
| Year extraction | PASS | Filename year cross-checked against every row's `yr` (hard stop on mismatch) |
| §4b masks (5b) | PASS | No §4b masks; all 17,114 suppression masks recorded and independently re-counted from bronze |

## Notes

- `schema_hash`: `0e0036f7ce4fb3de8f7a72a1742fd9359de3fc305224d00bacdfe9495a4e39e7`; validation 19 pass / 0 fail / 1 warning (explained); freshness FRESH; read_loss 0.
- **Contract grain includes `reporting_status`** (PK position 5, `key_metric_grain_contributor: true`), auto-derived by the emitter because it is a fact categorical with no total. The semantic grain is year × county_fips × case_type × petition_status; `reporting_status` is functionally dependent on those (each county×measure×year has exactly one status), so grain uniqueness holds (validator confirms). Consistent with platform convention; noted for dashboard consumers (a grain categorical with no `all` total becomes a required single-select).
- `case_rate_per_1000` carries no `unit` marker (per-1,000 fits neither `proportion` nor `ratio`); the authored `case_rate_per_1000_non_negative` check keeps it guarded — acceptable per the emitter's unit-exemption provision.
- 2014 is a genuine source gap (API returns no GA rows); correctly absent from gold, listed in the contract's `year_gaps`, never interpolated.
