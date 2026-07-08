# Data Review: inmate_population

**Date**: 2026-07-07
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

All 25 served gold values (2000–2024) are byte-identical to an independent `pdftotext -layout` re-extraction of the bronze PDF — zero mismatches. The one interpretive decision (year-2000 floor at the Dec-31 head-count methodology break, dropping the 1925–1979 NCRP and 1980–1999 December-ADP eras) follows the criminal_justice domain rule ("version methodological breaks, never pool across them") and is fully documented in the contract's purpose/limitations. v1 parity is N/A — this topic does not exist in `docs/rebuild/v1-baseline.yaml` (the v1 baseline contains no criminal_justice topics).

## Manifest Verification

**Categorical mappings**: the manifest's `categorical_mappings` is `{}` — gold has no categorical columns (single count metric, statewide grain). Nothing to verify for Steps 2a–2d.

The bronze structure doc *recommended* a `count_method` categorical (`ncrp` / `december_adp` / `dec31_headcount`) **or** documenting the break in `limitations`. The transform takes the doc's alternative: after the year-2000 floor the categorical would be the constant `dec31_headcount`, so it is dropped and the break is documented in the contract `description`/`limitations` (verified present, verbatim-consistent with the PDF's sources block). This satisfies the doc's stated option — not a fix.

**Row-count reconciliation** (manifest `row_counts`):

| Measure | Value | Assessment |
|---------|-------|------------|
| total_bronze | 100 | = 1925–2024, one row per published year |
| total_filtered | 75 | = 1925–1999, all with explicit reason `pre_2000_methodology_break_year_floor` |
| total_gold | 25 | = 2000–2024, expansion factor 1.00x every year |
| actual parquet rows | 25 | matches `total_gold` exactly (3b PASS) |
| read_loss events | 0 | contiguity assertion in transform makes loss impossible without a hard fail |

100 − 75 = 25 ✓. Every served year 2000–2024 present, no gaps (also enforced by the `year_series_contiguous` contract quality check).

## Column Coverage

| Bronze element | Gold column | Status |
|----------------|-------------|--------|
| `Year` | `year` (int32, fact_key) | MAPPED |
| `Count` | `year_end_inmate_population` (int64, fact_metric, unit=count, key_metric) | MAPPED |
| sources-block era (`count_method`) | — | CORRECTLY EXCLUDED — constant after the year-2000 floor; break documented in contract limitations per the structure doc's stated alternative |
| geography (`county_fips`) | — | CORRECTLY EXCLUDED — statewide-only report; column omitted entirely rather than 100%-NULL (validator supports absent geography) |
| bar chart | — | CORRECTLY EXCLUDED — rendered picture of the same series, never extracted |

No gold column lacks a bronze source (no fabrication).

## Value-Level Spot Checks

**Full-series comparison (supersedes sampling).** Because the topic is only 25 rows, I re-extracted the bronze PDF with an *independent* tool (`pdftotext -layout` + the same token-shape rule) and compared **every** gold row:

```
bronze pairs parsed: 100 span 1925 - 2024
gold rows: 25 | columns: ['year', 'year_end_inmate_population']
gold-vs-bronze mismatches: NONE — all 25 values identical to pdftotext extract
```

**Extreme rows (4a):**
- Global max: gold 2007 = 54,463. Bronze line (pdftotext): `2007  54,463` (block 5 pairing in row `1987 … 2007 54,463`). MATCH.
- Global min: gold 2000 = 43,875. Bronze line: `2000  43,875`. MATCH.

**Ordinary traces (4b)** — served-era values across print blocks:
- Bronze `2005  49,144` → gold 2005 = 49,144. MATCH.
- Bronze `2020  46,132` (COVID drop) → gold 2020 = 46,132. MATCH.
- Bronze `2024  50,107` (latest) → gold 2024 = 50,107. MATCH.

**Filtered-era check:** bronze `1925  3,007` and `1994  33,175` are present in the extract (full-series anchors verified by the transform's `_assert_full_series`) and correctly ABSENT from gold (pre-floor).

**4c Sentinel year-attribution:** year literals in transform (`YEAR_FLOOR = 2000`, anchor dicts) are QA constants, not attribution logic; each gold `year` comes from the year token physically paired with its count on the data line. The 100/100 independent re-extraction match proves attribution correct. PASS.

**4d Aggregate-row reconciliation:** N/A — no derived rows; the single state row per year comes directly from bronze (no county/facility grain exists to roll up).

**4e Dedup tie-break:** N/A — single bronze file, extraction asserted duplicate-free; no overlap years possible.

**4f Suppression semantics:** N/A — source publishes a complete unsuppressed series (`suppressed_to_null=False`; validator `no_suppression_markers` passed); gold has zero NULLs in both columns.

## Validation Cross-Read

- `_validation.json`: **19 passed, 0 failed, 0 warnings** (2026-07-07T04:09:27Z). `contract_parquet_schema`, `contract_quality_sql`, `grain_uniqueness`, `foreign_keys` all pass.
- `schema_hash`: `b4b589e9e20867a515acb0c9eefb94fb6cb1dadae82043f3484cc3f00110ee22`
- **§4b masking audit:** no `_null_*` helpers in transform.py, no `masked_values` section in the manifest — consistent. Nothing masked; every value is regex-validated and anchor-checked instead. PASS.
- **§15b coverage judgment:** authored checks (`no_pre_2000_years`, `population_never_null`, `year_series_contiguous`) plus the auto-derived count `>= 0` cover the topic's real invariants — the year floor, completeness, and gap-free annual cadence. With one metric and one grain column there are no partition/co-null/component shapes to check. In-transform pinned anchors (1925/1994 pre-filter; 2019/2020/2024 gold) additionally guard exact values on refresh. Adequate.
- **Contract prose fidelity:** purpose/limitations/usage assertions (scope inclusions/exclusions, era methodology 1925-1979 NCRP / 1980-1999 December ADP / 2000+ Dec-31 head count, "no suppression", statewide-only, annual first-week-of-January cadence) all match the bronze doc's verbatim scope block. No contradictions.
- **v1 parity:**

```
key present: False
criminal_justice keys in v1 baseline: NONE (v1 was education-only)
```

  N/A — new topic, no v1 baseline entry to compare (the compute yields `now: a5dcce972a8acdc300b20e5a16dbfeed43a7b09b59823576bf7426675e6e8f2b` with `v1: None`).

## Cross-Era Consistency

- **Overlap years:** none — single bronze file, single era served.
- **Era boundary (1999→2000):** the boundary is the deliberate serving floor; the 1999 December-ADP figure (41,557) is filtered, and the first served value 43,875 (2000, Dec-31 head count) is not pooled against it.
- **Cross-year NULL sweep (3c):** zero NULLs in every year for both columns — no era-localized rename signature possible.
- **YoY continuity (3d):** adjacent-year ratios span 0.855 (2019→2020, the documented COVID drop) to 1.071 — no >10x jumps, no cumulative-publication level shifts.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Only 2 fields exist; both land in gold; extraction hard-fails on any lost (year, count) pair via the contiguity assertion |
| Era routing | PASS | Single file; the methodology break is handled by the year floor with per-year `record_filtered` events |
| Filter logic logged + justified | PASS | 75 pre-2000 rows filtered with explicit reason `pre_2000_methodology_break_year_floor`, per-year in the manifest |
| Normalization map completeness | N/A | No categoricals |
| `strict=False` casts | PASS | None present; types declared explicitly at DataFrame construction |
| Dedup keys + tie-break | PASS | `assert_no_natural_key_collisions` runs BEFORE `deduplicate_by_levels(sort_col="year_end_inmate_population")`; collisions impossible by construction (asserted duplicate-free single file) |
| Year extraction | PASS | Years read from the data-line tokens themselves; 100/100 independent re-extraction match |
| §4b masks (5b) | PASS | None needed; none claimed; manifest consistent |

## Notes

- `schema_hash`: `b4b589e9e20867a515acb0c9eefb94fb6cb1dadae82043f3484cc3f00110ee22`; validation 19/0/0.
- Risk hypotheses 1 (Asian/PI conflation), 6 (mutual exclusivity): N/A — no demographic column anywhere in the source (Step 2e triage: no `asian` value, no `pct_asian` column; `grep -iE 'pacific'` on the structure doc finds nothing).
- The transform's extraction line-filter (alternating year/comma-count tokens) structurally excludes the bar chart's axis labels; my independent pdftotext parse using the same rule found exactly 100 pairs, confirming no chart contamination.
- Refresh safety is strong: pinned anchors + contiguity + `max_year >= 2024` assertions mean a drifted future PDF fails loudly rather than shipping silently truncated gold.
