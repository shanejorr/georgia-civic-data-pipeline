# Data Review: jail_population

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Data accuracy is clean: every value-level trace (global extremes, all five §4b masks,
the 2018-09 five-county component repair, the no-jail / not-reported / isolated-flag
reclassifications, ordinary rows) MATCHes bronze exactly, and the derived state rollup
equals the bronze TOTALS row for all six metrics (0 mismatches, now enforced for every
metric). Every categorical map entry is semantically correct with 0 unmapped. **The two
Required Fixes from the prior (2026-07-02) review are already resolved in the current
contract** — all six `state_*_equals_sum_of_counties` checks are authored, and the
`counties_reporting` description now documents that it can differ from the source's
unreliable item 13. **No Required Fixes remain.** One LOW judgment call survives (the
Treutlen 2007-12 reclassification spanning the 2008-01/02 archive gap). **v1 parity:
no v1 baseline — `criminal_justice` is post-v1.**

## Manifest Verification

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| county_fips | 162 (→159 FIPS) | 162 | 0 | PASS |
| month | 12 (identity) | 12 | 0 | PASS |
| reporting_status | 3 | 3 | 0 | PASS |

**county_fips.** 162 distinct post-suffix-strip names → 159 FIPS = 159 counties + 3
casing variants the structure doc lists (`Mcduffie`/`McDuffie`, `Mcintosh`/`McIntosh`,
`Dekalb`/`DeKalb`), which `add_county_fips` folds to one FIPS each. `unmapped_count=0`;
the transform hard-fails on any unmatched name (never silent-NULLs). The validator FK
check confirms all 159 gold values resolve in the counties dimension.

**reporting_status (all three entries semantically correct):**

| Bronze marker | Gold value | Correct? |
|---------------|-----------|----------|
| `all_count_cells_blank` | `not_reported` | YES — a row with all six count cells blank = county did not submit (structure doc ETL #1) |
| `no_jail_suffix` | `no_jail` | YES — ` - NO JAIL` label with literal zeros |
| `count_data_present` | `reported` | YES |

`gold_values_produced` (`no_jail`, `not_reported`, `reported`) equals the contract enum
exactly (2c). Marker is derived from the six COUNT cells only — correct, since blank
rows' percent cells often render literal `0%` and cannot signal non-reporting.

**month:** identity map; all 12 values seen; enum matches. 2008 gold contains only
months 03–12 (2008-01/02 absent from the source archive, per the doc).

**Row-count reconciliation.** 222 files × 160 bronze rows (159 counties + TOTALS) =
35,520 bronze; gold = 159 county + 1 derived state row per month = 35,520. By-year
counts match file counts (2007: 2×160=320; 2008: 10×160=1,600; 2009–2025: 12×160=1,920;
2026: 6×160=960). `total_filtered=0`; expansion factor 1.0 every year. Actual parquet
rows 35,520 = manifest `total_gold`. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|------------|--------|
| *(row number, pos 0)* | — | CORRECTLY EXCLUDED (alphabetical index) |
| Jurisdiction (name) | county_fips | MAPPED |
| Jurisdiction (NO JAIL suffix) | reporting_status | MAPPED (derived categorical) |
| Number of Inmates in Jail | total_inmates | MAPPED |
| Jail Capacity | jail_capacity | MAPPED |
| Inmates as % of Capacity | — | CORRECTLY EXCLUDED (corrupted ×100 at source, ETL #4) |
| Number of Inmates Sentenced to State | state_sentenced_inmates | MAPPED |
| % of Inmates Sentenced to State | — | CORRECTLY EXCLUDED (ETL #4) |
| Number of Inmates Awaiting Trial in Jail | awaiting_trial_inmates | MAPPED |
| % of Inmates Awaiting Trial in Jail | — | CORRECTLY EXCLUDED (ETL #4) |
| Number of Inmates Serving County Sentence | county_sentenced_inmates | MAPPED |
| % of Inmates Serving County Sentence | — | CORRECTLY EXCLUDED (ETL #4) |
| Number of Other Inmates | other_inmates | MAPPED |
| % of Other Inmates | — | CORRECTLY EXCLUDED (ETL #4) |
| TOTALS row | state rows | MAPPED (consumed as a per-file parse check; re-emerges as the derived state row — verified identical) |
| Statewide summary table | — | CORRECTLY EXCLUDED (disagrees with county table, ETL #7) |
| Chart arrays / annual_totals CSV | — | CORRECTLY EXCLUDED (retrieval-date chrome; CSV recorded on manifest as excluded) |
| *(filename YYYY-MM)* | year, month | MAPPED |

`counties_reporting` is the only gold column with no single bronze cell behind it —
derived by counting submitting county rows (documented in code + contract). No
fabricated columns.

**Contract prose fidelity.** No contradictions found against `bronze-data-structure.md`:
year range (2007-11 → 2026, incl. missing 2008-01/02), suppression scheme ("no
suppression; NULL means not reported; zeros real"), percent-column corruption (×100 in
38 months), the 2023-06 additivity regime break, and the "159 in 2019-03 vs 59 in
2026-06" coverage range all agree with the doc. No demographic convention applies.

## Value-Level Spot Checks

All bronze cells quoted below were read directly from the bronze HTML with an
independent parser. Format: inmates/capacity/state/awaiting/county/other.

**Extreme rows (bronze → gold):**

| Trace | Bronze (file) | Gold | Verdict |
|-------|---------------|------|---------|
| total_inmates county max | 2010-10 Chatham `3775/1524/261/1506/112/1896` (248% over-capacity) | 13051 2010-10 same | MATCH (extreme-but-real, preserved; components sum 3775) |
| jail_capacity county max | 2023-12 DeKalb `2020/3800/0/0/0/0` | 13089 2023-12 same | MATCH (post-2023-06 non-additive: breakdown 0, total 2020 — documented regime) |
| large-jail check | 2022-10 Fulton `3543/2688/30/3250/33/230` | 13121 2022-10 same | MATCH |

Global min of every metric is 0 (no-jail / real-zero counties). `counties_reporting`
min 59 (2026-06) and max 159 match the documented coverage range.

**Ordinary trace:** 2019-03 Fulton bronze `2624/2688/106/2042/149/327` → gold identical,
`reported` — MATCH (matches the contract's own column examples).

**§4b mask traces (all five archive anomalies; impossible cell → NULL, rest of row intact):**

| Bronze (verbatim) | Gold | Verdict |
|-------------------|------|---------|
| Madison 2019-05 state = `0.01` | NULL; 83/96/·/26/19/37, `reported` | MATCH |
| Pulaski 2024-03 state = `-3` | NULL; 22/42/·/15/1/0 | MATCH |
| Long 2025-07 county = `-1` | NULL; 0/130/0/0/·/0 | MATCH |
| Long 2025-08 other = `-2` | NULL; 0/130/0/0/0/· | MATCH |
| Charlton 2026-02 other = `-2` | NULL; 0/0/0/0/0/· | MATCH |

**2018-09 component repair (five bronze identities re-verified):** bronze publishes
Macon `(2,88,4,13)`=107=McDuffie's total; Madison `(1,69,1,8)`=79=McIntosh's total;
Marion `(4,20,0,1)`=25=Macon's total; Mcduffie `(1,51,20,38)`=110=Madison's total;
Mcintosh `(1,17,2,1)`=21=Marion's total. Gold reassigns each set to its owner (Macon
gets (4,20,0,1); Madison (1,51,20,38); Marion (1,17,2,1); McDuffie (2,88,4,13); McIntosh
(1,69,1,8)); totals + capacity unchanged; every repaired component set sums to its
owner's total. MATCH.

**Reclassification / status traces:**
- Richmond 2024-06 bronze `'Richmond - NO JAIL' 0…`, flanked by reported 2024-05 (1144)
  and 2024-07 (1172) → gold `not_reported`, NULL metrics — MATCH (isolated erroneous flag).
- Clay 2019-03 / Quitman 2019-03 `' - NO JAIL' 0…` → gold `no_jail` with literal zeros —
  MATCH (real no-jail counties untouched).

**Derived state row vs bronze TOTALS (4d):** 2019-03 bronze TOTALS
`37,346/48,808/2,400/24,011/5,351/5,584` → gold state row 37346/48808/2400/24011/5351/5584,
`counties_reporting`=159 — MATCH. Reconciliation is a count-sum only (no percentage
averaging anywhere), and the six `state_*_equals_sum_of_counties` quality checks now
enforce it for every metric × every month (0 mismatches).

**4c sentinel year-attribution:** N/A — no year-bearing data strings; `year`/`month`
come from the filename, verified = in-page report month for all 222 files (structure doc).
**4e dedup tie-break:** N/A — one file per month, one row per county per file; no overlap
years; the collision guard runs before dedup. **4f suppression:** N/A as suppression
(`suppressed_to_null=False`); the blank→NULL and no-jail→zero traces cover the two
null/zero conventions.

## Validation Cross-Read

- `_validation.json`: **passed=true, 18 pass / 0 fail / 2 warnings.**
  `contract_parquet_schema`, `contract_quality_sql` (**23 checks**), `grain_uniqueness`
  (`['year','county_fips','month','reporting_status']`), `foreign_keys` (all 159 FIPS
  resolve) all pass. schema_hash `34227ee0354cfbf2779d567025753aaaafce80b3e1f39276b3af1d30c5198e72`.
- **Warning 1 (tidy_format):** "`other_inmates` matches demographic pattern 'other'" —
  false positive; a custody-category count column, not a wide demographic. No action.
- **Warning 2 (null_rate_spikes):** all six metrics ~21.7% NULL in 2026 — the documented
  voluntary-survey coverage collapse (59 of 159 counties reporting in 2026-06). Expected;
  documented in contract limitations. No action.
- **§4b masking audit:** the single `_null_impossible_counts` helper's masks are all
  recorded in manifest `masked_values` (state_sentenced: 1 non-integer 2019 + 1 negative
  2024; county_sentenced: 1 negative 2025; other: 2 negative 2025/2026 — 5 cells, counts
  match the five bronze traces), documented by name in each column's contract
  description, and guarded by the auto-derived `*_non_negative` quality checks (int64
  physical type additionally forecloses the non-integer shape). PASS.
- **§15b coverage judgment:** the invariant net is strong — not_reported⇒NULL,
  no_jail⇒zeros, `state_*=Σcounties` **for all six metrics**, counties_reporting
  consistency (matches submitters, state-rows-only, ≤159), reporting_status/state-row
  iff rules, and 159-counties-every-month completeness. The additivity identity
  (total = Σ of 4 components) is *intentionally* not enforced (regime break at 2023-06,
  documented) — a correct decision, not a gap. No missing obvious invariant.
- **v1 parity (verbatim):**

  ```
  DIFFERS from v1
    v1:  None
    now: 824d875c83ccd38051fb827d7de8552fa4fe505f64797ce4873c435781241f9c
  ```

  `docs/rebuild/v1-baseline.yaml` has no `criminal_justice/jails/jail_population` entry —
  **no v1 baseline; this topic is post-v1.** The "DIFFERS/None" line is the trivial
  no-baseline case, not a divergence.

## Cross-Era Consistency

- Single era: the 12-cell county-table header is byte-identical across all 222 files
  (transform hard-fails on any deviation); no era boundaries, no overlap years.
- Cross-year NULL sweep (3c): all six metrics clean in every year. `counties_reporting`
  is populated on exactly 1 of 160 rows per month (state rows) **by design** — the
  `counties_reporting_on_state_rows_only` check enforces exactly that (verified: 0 county
  rows populated, 0 state rows NULL). Documented N/A, not a rename bug.
- Year-over-year continuity (3d): statewide yearly means move smoothly (total_inmates
  ~40.6k in 2007 → 35–38k range; no >10x jumps, no revert-next-year level shifts). The
  2020 dip (~31.6k, COVID-era depopulation) and shrinking `state_sentenced_inmates`
  (~66→~20 per-county) are real secular trends.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Only the six corrupted percent columns dropped, deliberately + documented; counts parsed positionally with a hard per-file header-equality check |
| Era routing | PASS | Single era; signature + byte-identical header assertion; 13-cell row-shape + 159+1 row-count assertions per file |
| Filter logic | PASS | `total_filtered=0`; TOTALS consumed as a parse check (tolerance 0.5 absorbs only the 2019-05 `0.01` artifact); CSV exclusion logged + recorded |
| Normalization map completeness | PASS | Name map covers all casing variants the doc lists; unmatched names hard-fail |
| `strict`/recode casts | PASS | `replace_strict(default=None)` sees only the transform's own 3 constructed markers; `reporting_status_null_iff_state_row` catches any leak |
| Dedup keys + tie-break | PASS | Collision guard (raises on divergent duplicates) runs before dedup; duplicates impossible by construction; `sort_col="total_inmates"` documented safety net |
| Year extraction | PASS | Filename regex; filename month = in-page month verified for all 222 files |
| §5b masks | PASS | All recorded, documented, range-guarded (see Validation Cross-Read) |

## NEEDS_JUDGMENT

### Judgment Call 1: Treutlen 2007-12 reclassification spans the 2008-01/02 archive gap
- **Severity if confirmed**: LOW
- **Suspicion**: The isolated-NO-JAIL rule treats *archive-adjacent* months as adjacent.
  For the single 2007 reclassification — Treutlen (13283) 2007-12 — the flanking archive
  months are 2007-11 and 2008-03, three calendar months apart because 2008-01/02 are
  missing from the source. A brief real closure spanning Dec–Feb is marginally more
  conceivable than a literal one-month closure, so this county-month is weaker evidence
  than the other 57 isolated-flag reclassifications.
- **Evidence available**: Bronze — 2007-11 `Treutlen 16/18/6/4/5/1` (16 inmates, cap 18);
  2007-12 `Treutlen - NO JAIL 0/0/0/0/0/0`; 2008-03 `Treutlen 21/18/12/3/4/2` (21
  inmates, same cap 18). Continuous capacity and immediate repopulation argue strongly
  for a reporting error, consistent with the uniform rule; gold correctly shows 2007-12
  as `not_reported` with NULL metrics.
- **Why uncertain**: Cannot distinguish "erroneous flag" from "brief real closure Dec–Feb"
  from the data alone; the structure doc lists Treutlen among counties whose NO JAIL
  status legitimately toggles in other years.
- **Location**: `_reclassify_isolated_no_jail()` in `transform.py`
- **If confirmed, suggested fix**: None recommended. Keep the uniform rule — one
  documented, consistently-applied rule beats a per-case carve-out for a single 2007
  county-month whose only gold impact is NULL-vs-zero on six cells. (Optional
  alternative: exempt flags whose archive-adjacency spans the 2008-01/02 gap.)

## Notes

- schema_hash: `34227ee0354cfbf2779d567025753aaaafce80b3e1f39276b3af1d30c5198e72`
- Validation: 18 pass / 0 fail / 2 warnings (both explained); 23 contract quality checks
  pass; grain unique; FK 159/159.
- Prior-review Required Fixes (2026-07-02) both verified resolved in the current
  contract: (1) `state_*_equals_sum_of_counties` now authored for all six metrics;
  (2) `counties_reporting` description documents the item-13 divergence.
- Risk hypotheses: 1 (Asian/PI) N/A — no demographic column (structure doc confirms);
  2 (rename typo) PASS — 3c sweep clean; 3 (sentinel year) N/A; 4 (derived aggregation)
  PASS — 0 state-vs-Σcounties mismatches × 6 metrics; 5 (dedup inversion) N/A — no
  overlap; 6 (mutual exclusivity) N/A; 7 (wrong mapping) PASS — 100% of map entries
  reviewed.
- Reclassified events: 5 (2018-09 repair) + 58 isolated-NO-JAIL (2007:1, 2023:5, 2024:11,
  2025:26, 2026:15), matching the docstring and the contract's "58 county-months" claim.
- `read_loss`: zero events. `masked_values`: 5 cells across 4 events, all traced.
- Gold county-row status distribution: reported 31,599 / no_jail 2,935 / not_reported
  764 (= 222 × 159).
