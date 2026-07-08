# Data Review: inmate_releases_county

**Date**: 2026-07-07
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Gold is verified correct at 100% cell coverage: an independent pdfplumber re-parse of both bronze PDFs was compared against gold cell-by-cell — **1,600 of 1,600 cells match exactly** (all 159 counties × 10 year-editions + all 10 statewide Total rows), and the county-sum + residuals == printed-Total reconciliation holds independently for all 10 year-editions. Both categorical maps (159-entry county_fips, 2-entry reporting_period) are semantically verified with zero errors, including positive evidence that FIPS resolution went by county NAME, not GDC's index. v1 parity is N/A (no entry for this topic in `docs/rebuild/v1-baseline.yaml` — new criminal-justice topic, not part of the v1 rebuild baseline). The only open item is a LOW judgment call on an auto-derived contract example query that returns zero rows (an emitter-level pattern shared with the approved sibling `recidivism_reconviction`).

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|--------|------------|--------------------|----------|--------|
| county_fips | 159 | 159 (`001 - Appling County` … `159 - Worth County`) | 0 | PASS — 100% verified |
| reporting_period | 2 | 2 (the printed edition subtitles) | 0 | PASS — 100% verified |

**county_fips — full 159-entry semantic verification.** Every `"NNN - X County" → FIPS` entry was checked against the global counties dimension by name: **0 mismatches** (e.g. `060 - Fulton County → 13121`, `025 - Chatham County → 13051`, `044 - Dekalb County → 13089`, `094 - Macon County → 13193`). Decisive positive evidence that resolution used the NAME and not the 001–159 prefix: GDC's index sorts ASCII (`Macon` < `Mcduffie`) while FIPS assignment alphabetizes "Mc" as "Mac" (`McDuffie = 13189` before `Macon = 13193`) — the map carries the correct FIPS for all five counties in that region (`094 - Macon → 13193`, `095 - Madison → 13195`, `096 - Marion → 13197`, `097 - Mcduffie → 13189`, `098 - Mcintosh → 13191`), which an index-based mapping would have gotten wrong. The map also correctly skips 13041 (Campbell) and 13203 (Milton), the two former counties merged into Fulton in 1932. `094 - Macon County` maps to the real Macon County (13193) — the bronze prints plain county names, so no consolidated-government override was needed.

**reporting_period.** `"the past five complete calendar years" → calendar_year`, `"the past five complete fiscal years" → fiscal_year` — both semantically correct; detection is content-based (printed subtitle), never filename-based. `gold_values_produced` = `[calendar_year, fiscal_year]` equals the contract enum exactly (2c PASS) and matches the sibling `recidivism_reconviction` vocabulary as prescribed.

**Unmapped (2d):** 0 in both columns. **Completeness (2a):** all 159 county labels + both subtitles documented in `bronze-data-structure.md` appear in `bronze_values_seen`; no documented value went unencountered.

**2e Asian/PI conflation:** N/A — no demographic column, no race metrics (validator: "No demographic column (skipped)").
**2f Demographic mutual exclusivity:** N/A — no demographic column.

**Row-count reconciliation:**

| Year | Bronze | Filtered (explicit) | Gold | Check |
|------|--------|---------------------|------|-------|
| 2021 | 162 | 2 | 160 | ✓ (CY only) |
| 2022 | 324 | 4 | 320 | ✓ (CY + FY) |
| 2023 | 324 | 4 | 320 | ✓ |
| 2024 | 324 | 4 | 320 | ✓ |
| 2025 | 324 | 4 | 320 | ✓ |
| 2026 | 162 | 2 | 160 | ✓ (FY only) |
| **Total** | **1,620** | **20** | **1,600** | ✓ |

Bronze 1,620 = 162 table rows × 10 year-columns (2 files × 5 years). Filtered 20 = the 2 residual rows (`999 - Other Custody/Out Of State`, `Unknown, not reported`) × 10 year-editions, all recorded under one explicit reason. Actual parquet row sum = 1,600 = manifest `total_gold` (3b PASS). Uniform expansion factor 0.988 across all years — no outliers.

## Column Coverage

| Bronze element | Gold column | Status |
|----------------|-------------|--------|
| `Home County` (name part) | `county_fips` | MAPPED (via counties dimension) |
| `Home County` (001–159 prefix) | — | CORRECTLY EXCLUDED (GDC alphabetical index, not FIPS) |
| {year} column headers | `year` | MAPPED (from content, not filename) |
| CY vs FY edition (subtitle) | `reporting_period` | MAPPED |
| cell value | `inmate_releases` | MAPPED (structure doc's suggested name was `releases`; served name passes canonical vocabulary — a best-effort naming note, not a defect) |
| `Total` row | state rows (NULL `county_fips`) | MAPPED — served as the state detail level per domain convention (jail_population precedent); deviates from the structure doc's best-effort "not_in_gold" suggestion, deliberately and documented |
| `999 - Other Custody/Out Of State`, `Unknown, not reported` | — | CORRECTLY EXCLUDED (documented judgment call: excluded AFTER exact Total reconciliation, retained inside the state Total; recorded via `record_filtered`; stated in contract purpose/limitations/description and enforced by the `state_total_at_least_county_sum` `>=` check) |

No fabricated gold columns — every gold column traces to bronze.

## Value-Level Spot Checks

**Full-cell comparison (supersedes sampling).** Both PDFs were independently re-parsed with pdfplumber and every county cell and Total cell compared to gold: **1,600 cells checked, 0 mismatches.** The reconciliation `sum(159 county values) + residual_999 + residual_unknown == printed Total` was re-verified independently for all 10 year-editions: all exact.

Extreme and ordinary traces (bronze quoted → gold):

| Trace | Bronze (quoted) | Gold | Verdict |
|-------|-----------------|------|---------|
| Global max: FY `Total` row | `Total 13,073 13,156 12,858 13,182 13,730` → FY2026 = 13,730 | state row, fiscal_year 2026 = 13730 | MATCH |
| Global min: `026 - Chattahoochee County` CY | `4 4 7 5 0` → CY2025 = 0 | 13053 calendar_year 2025 = 0 | MATCH (real zero, per structure doc) |
| CY `Total` row (all 5 years) | `13,460 13,061 13,007 13,227 13,422` | state rows CY 2021–2025 = 13460/13061/13007/13227/13422 | MATCH |
| `060 - Fulton County` CY (ordinary, calendar era) | `982 935 870 923 1,033` | 13121 CY 2021–2025 = 982/935/870/923/1033 | MATCH |
| `060 - Fulton County` FY (ordinary, fiscal era) | `955 895 883 964 1,087` | 13121 FY 2022–2026 = 955/895/883/964/1087 | MATCH |
| `152 - Webster County` CY (small county) | `3 1 1 1 2` | 13307 CY = 3/1/1/1/2 | MATCH |
| Other zeros | Glascock CY2021=0, Taliaferro CY2022=0, Echols FY2026=0 | 13125/13265/13101 = 0 | MATCH |
| Residuals (excluded) | CY `999`: `4 9 5 2 2`; CY Unknown: `1,022 1,232 1,273 1,192 1,047`; FY `999`: `5 8 4 1 4`; FY Unknown: `1,103 1,260 1,186 1,160 877` | not served (retained inside state Total) | CORRECT — matches transform logs and the ~1–9 / ~880–1,270 ranges stated in the contract |

- **4a extremes:** global max (13,730, FY2026 state) and global min (0, Chattahoochee CY2025) traced above — MATCH. Thousands-comma parsing verified on `13,730`/`1,033`/`1,087`.
- **4b ordinary per era:** Fulton in both editions (each edition is an "era") — MATCH on all 10 values.
- **4c sentinel year-attribution:** years come from the printed column headers, not the filename. Verified: the FY file (manifest `year: 2026`) contributes gold years 2022–2026, and overlapping-year values stay edition-distinct (Fulton CY2022 = 935 ≠ FY2022 = 955, each matching its own edition's bronze) — PASS.
- **4d aggregate reconciliation:** state rows COME FROM BRONZE (printed Total). Independent screen: for every (year, edition), county sum + residuals == Total exactly, and gold state row == printed Total — PASS. The contract's `state_total_at_least_county_sum` (`>=`) correctly encodes the served relationship (county rows sum to less by the excluded residual amount).
- **4e dedup tie-break:** N/A — the two files overlap on years 2022–2025 but carry disjoint `reporting_period` values, so natural keys never collide (grain_uniqueness passed; `assert_no_natural_key_collisions` ran before dedup).
- **4f suppression:** N/A — `suppressed_to_null: false`; every bronze cell is a published integer (verified: 0 NULLs in `inmate_releases` across all 1,600 rows).

## Validation Cross-Read

- `_validation.json`: **20 passed, 0 failed, 0 warnings** (2026-07-07T04:09:33Z, fresh vs manifest `generated_at` 04:09:33Z). `contract_parquet_schema`, `contract_quality_sql` (9/9), `grain_uniqueness` (`['year', 'county_fips', 'reporting_period']`), and `foreign_keys` (`county_fips -> counties: all 159 keys resolve`) all pass.
- **schema_hash**: `c4a7ef2bce93d8898677eec223417cf0c01ec56c5adb69bc8170a4361a5c2e2e`
- **§4b masking audit:** no `_null_*` helpers in transform.py; no `masked_values` section on the manifest (absent = zero events); contract declares `suppressed_to_null: false` and `unit: count` gives the ≥0 range guard. Consistent — nothing unrecorded.
- **§15b coverage judgment:** the 9 quality checks cover the topic's real invariants well — non-negative count, enum conformity, no-NULL metric, exactly-159-counties and exactly-one-state-row per (year, edition), state ≥ county-sum, 5 distinct years per edition, and the year-2000 floor. The one invariant not expressible as contract SQL (exact Total reconciliation including the dropped residuals) is asserted at transform time before the residuals are excluded. No missing obvious invariant.
- **v1 parity (verbatim):** `v1 parity: NO ENTRY for criminal_justice/gdc/inmate_releases_county` — N/A, new criminal-justice topic outside the v1 rebuild baseline.
- **Contract prose fidelity:** purpose/limitations/descriptions checked against `bronze-data-structure.md` — year windows (CY 2021–2025, FY 2022–2026), home-county semantics, residual magnitudes (~1–9 and ~880–1,270/yr, ~7–10%), no-suppression + real zeros (Chattahoochee CY2025 = 0), and the FY definition (Jul 1–Jun 30, labeled by ending year) all agree with bronze. No contradictions.

## Cross-Era Consistency

- **Overlap years 2022–2025** appear in both editions but never collide (disjoint `reporting_period`); overlapping values are correctly edition-distinct (Fulton 935 CY vs 955 FY in 2022).
- **Cross-year NULL sweep (Risk 2):** 0 NULLs in `inmate_releases`, `year`, `reporting_period` in every year; `county_fips` NULL on exactly the 10 state rows. No era-localized NULL signature.
- **Level continuity (3d):** state totals per edition — CY 13460→13061→13007→13227→13422; FY 13073→13156→12858→13182→13730. Max adjacent-year change ~4%; no scale jumps, no cumulative-publication signature.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Fixed-shape parser hard-fails on any unrecognized line; label-set + 159-index-sequence + row-count guards make unparsed rows impossible. |
| Era (edition) routing | PASS | Content-based (printed subtitle), asserted exactly one subtitle per file and exactly one CY + one FY edition per run. |
| Filter logic logged + justified | PASS | Only the 2 residual rows/year-edition filtered, after exact Total reconciliation; recorded via `record_filtered` with an explicit reason; residual magnitudes logged per year. |
| Normalization map completeness | PASS | 159/159 county labels + 2/2 subtitles seen and mapped; unmapped 0. |
| `strict=False` casts | PASS | None — explicit schema on DataFrame construction; the row regex cannot yield negative/fractional counts. |
| Dedup keys + tie-break | PASS | Collision guard (`assert_no_natural_key_collisions`) runs first; `deduplicate_by_levels(sort_col="inmate_releases")` is a documented no-op safety net (duplicates impossible by construction today). |
| Year extraction | PASS | From the printed column header (5 consecutive years asserted), never the filename; header repeated per page and asserted identical. |
| §4b masks (Step 5b) | PASS | None needed; no unrecorded masking. |

## NEEDS_JUDGMENT

### Judgment Call 1: Auto-derived contract example query returns zero rows

- **Severity if confirmed**: LOW
- **Suspicion**: The emitter's second auto-derived example query — `SELECT * FROM inmate_releases_county WHERE reporting_period = 'calendar_year' AND year = 2026 LIMIT 100` ("Filter by reporting_period = calendar_year") — returns **0 rows**, because it combines the topic's global latest year (2026, fiscal-only) with the first enum value (`calendar_year`, which ends at 2025). Served example queries ground DataTalk/MCP consumers; an always-empty example is mildly misleading.
- **Evidence available**: Executed: `example query 2 rows: 0`; per-edition year sets `calendar_year: 2021–2025`, `fiscal_year: 2022–2026`. The approved sibling `recidivism_reconviction` has the same pattern (calendar_year max 2022, example pinned to global latest year 2023), so this is emitter-level behavior already shipped elsewhere, and DataTalk carries empty-result retry armor.
- **Why uncertain**: Whether to fix per-topic (an `example_queries=` override in `_emit_contract`, e.g. pinning the CY example to `year = 2025`) or once in `src/utils/contract_emitter.py` (derive the example year per enum value's actual coverage) is a repo-level call — a topic-local override would leave the sibling inconsistent, while an emitter change touches every contract.
- **Location**: `src/utils/contract_emitter.py` (example-query derivation); topic-local alternative: `_emit_contract()` in `src/etl/criminal_justice/gdc/inmate_releases_county/transform.py`.
- **If confirmed, suggested fix**: Prefer the emitter-level fix: when composing a categorical-filter example, pick the latest year that actually co-occurs with the chosen enum value (then regenerate contracts). Gold data values are unaffected either way.

## Notes

- schema_hash: `c4a7ef2bce93d8898677eec223417cf0c01ec56c5adb69bc8170a4361a5c2e2e`; validation 20 passed / 0 failed / 0 warnings; contract version 1.0.0.
- Verification here exceeded the sampling protocol: 100% of gold cells (1,600) were compared against an independent re-parse of the bronze PDFs — zero discrepancies.
- The rolling five-year window means a future bronze refresh shifts coverage (oldest year drops); the `five_years_per_reporting_period` check will catch a stale-window survival.
- Bronze checksums (2026-07-04) match the analyzed files; read-loss events: 0 (per-file parity no-ops recorded per the recidivism_reconviction precedent — PDF parsing is guarded by exact-shape asserts instead).
