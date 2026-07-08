# Data Review: district_filings

## Verdict

**Status**: PASS
**Must-fix count**: 0

Summary: Bronze-to-gold recomputation matched all 81 gold rows exactly; no transform accuracy fixes are required.

## Summary

- Review date: 2026-07-07
- Review mode: Contract-and-manifest-first
- Scope: bronze -> transform.py -> contract -> validator -> gold accuracy review
- Artifact freshness: FRESH - bronze freshness gate passed for all 4 profiled files; transform mtime 2026-07-07T04:06:26Z is before manifest generation 2026-07-07T04:09:23Z, and validation timestamp 2026-07-07T04:09:24Z is after the manifest.

## Files Reviewed

- Transform: `src/etl/criminal_justice/federal_justice/district_filings/transform.py`
- Contract: `contracts/criminal_justice/district_filings.odcs.yaml`
- Bronze files: `cr96on_0.zip`, `cr70to95.zip`, `Criminal Code Book 1996 Forward.pdf`, `Criminal Code Book 1970-1995.pdf`
- Gold files: 27 `year=2000` through `year=2026` `states.parquet` files under `data/gold/criminal_justice/district_filings/`
- Manifest: `data/gold/criminal_justice/district_filings/_transform_manifest.json`
- Validation report: `data/gold/criminal_justice/district_filings/_validation.json`
- Supporting docs: `docs/contract-creation.md`, `docs/codex-review-contract.md`, data-cleaning standards/checklist, bronze/transform/review/fix/full-pipeline skills, `AGENTS.md`, `CLAUDE.md`, `src/etl/CLAUDE.md`, `src/etl/criminal_justice/CLAUDE.md`, bronze structure report, `_provenance.md`

## Contract Verification

- Schema/parquet column match: PASS - contract properties exactly match parquet columns: `year`, `federal_district`, `defendants_filed`, `felony_defendants_filed`, `defendants_terminated`, `defendants_convicted`.
- Column roles and grain: PASS - contract grain is `year, federal_district`; `year` is role `year`, `federal_district` is categorical and primary-key position 2, all four count columns are metrics.
- Metric units and derived quality checks: PASS - all metrics are `unit: count`; contract has non-negative checks plus `felony_defendants_filed <= defendants_filed` and `defendants_convicted <= defendants_terminated`.
- Categorical enums: PASS - `federal_district` enum equals actual gold and manifest values: `georgia_middle`, `georgia_northern`, `georgia_southern`.
- Detail levels and layout metadata: PASS - contract declares `detail_levels: [states]`, path template `criminal_justice/district_filings/year={year}/{detail}.parquet`, and available years 2000-2026 with no gaps.
- Foreign-key descriptors: PASS - contract declares no FKs; this topic has no county or dimension FK and uses `federal_district` as its own grain categorical.
- Schema hash/version consistency: PASS - version is `1.0.0`, schema hash is present, and the contract mtime is after the manifest mtime and before validation. No `_metadata.json` dependency exists.

## Validator Verification

- `_validation.json` fresh + passing: PASS - validation passed at 2026-07-07T04:09:24.014984+00:00, after manifest generation at 2026-07-07T04:09:23.953901+00:00.
- Contract-driven checks (schema, grain, quality SQL, FKs, vocabulary): PASS - 19 pass, 0 fail, 0 warning; schema, grain uniqueness, all 11 quality SQL checks, no-FK declaration, and canonical vocabulary all passed.
- Validator warnings explained: N/A - validation reports no warnings.
- Section 15b quality-check coverage (cross-column invariants authored): PASS - authored checks cover the applicable invariants: no pre-2000 years, complete 3-district grid, never-null metrics, non-negative counts, and subset constraints. There are no proportion partitions, co-null status fields, or joins to enforce.

## Manifest Verification

- Files processed coverage: PASS - `cr96on_0.zip` is the only processed source data file because it covers FY1996-2026; direct inspection confirms `cr70to95.zip` has no `FISCALYR`, `TAPEYEAR` 1970-1995 only, and is outside the FY2000+ served scope. The two PDFs are codebooks, not fact inputs.
- Categorical and recode coverage: PASS - manifest maps `3E -> georgia_northern`, `3G -> georgia_middle`, `3J -> georgia_southern`; `unmapped_count` is 0 and actual gold values match.
- Row-count reconciliation: PASS - source stream has 6,299,908 rows; explicit filters account for 6,130,506 non-Georgia rows and 20,778 pre-2000 Georgia rows; the retained 148,624 Georgia FY2000+ rows aggregate to exactly 81 district-year gold rows.
- Metric stats sanity: PASS - all count metrics are non-null, non-negative, and in plausible ranges; FY2026 drops are expected because FY2026 is partial and documented in contract limitations.

## Row and Join Accounting

- Bronze file/year disposition: PASS - current-format `cr96on_0.zip` has 144 columns and years 1996-2026; gold intentionally serves 2000-2026. Older `cr70to95.zip` is 39 columns, TAPEYEAR 1970-1995, and has no served year.
- Filter accounting: PASS - transform records `non_georgia_district_row` and `pre_2000_fiscal_year_floor`; direct stream counts match manifest totals.
- Join accounting: N/A - the transform performs no joins.
- Deduplication accounting: PASS - recomputed aggregation produced 81 unique `(year, DISTRICT)` keys; gold has 0 duplicate `(year, federal_district)` groups, so `deduplicate_by_levels` is a no-op safety net.
- Aggregation/unpivot accounting: PASS - no unpivot; one group-by aggregates defendant rows to district-year counts. A full recomputation of all four metrics from `CTFILTRN`, `FOFFLVL1`, `CTTRTRN`, and `DISP1` found 0 mismatches against gold.

## Reconciliation Checks

- Artifact freshness: PASS - bronze checksums match, manifest and validation are fresh, and gold files match manifest row counts.
- Contract freshness: PASS - contract was emitted from the current transform/gold run; no `_metadata.json` exists or is used.
- Year coverage: PASS - source `cr96on_0.zip` covers 1996-2026; 1996-1999 are filtered by the project year floor; gold covers every year 2000-2026 exactly once per federal district.
- Row preservation: PASS - every retained Georgia FY2000+ source row contributes to one district-year aggregate; every excluded row has a code-backed disposition.
- Column coverage: PASS - gold lineage is complete: `year` <- `FISCALYR`, `federal_district` <- `DISTRICT`, `defendants_filed` <- sum `CTFILTRN=1`, `felony_defendants_filed` <- sum `CTFILTRN=1 and FOFFLVL1=4`, `defendants_terminated` <- sum `CTTRTRN=1`, `defendants_convicted` <- sum `CTTRTRN=1 and DISP1 in {4,5,8,9,17,19}`.
- Recode accuracy: PASS - codebook confirms Georgia district codes `3E`, `3G`, `3J`; transform maps them to the correct canonical federal district labels.
- Asian-family demographic recodes (section 5b): N/A - no demographic column or race metrics are emitted.
- Demographic mutual exclusivity (section 5a): N/A - no demographic rows are emitted.
- Demographic collision aggregation before dedup (section 5): N/A - no demographic normalization occurs.
- Fact-table column order (year -> geo -> demographic -> categoricals -> metrics, section 1): PASS - no county geography or demographic column exists; actual order is `year`, `federal_district`, then metrics, matching the contract grain and parquet.
- Forbidden columns absent (`topic`, `detail_level`, name columns, census IDs, section 11/12): PASS - parquet columns contain no `topic`, no `detail_level`, no names, no docket/defendant identifiers, and no county/crosswalk IDs.
- Canonical column vocabulary (section 16): PASS - validator reports canonical vocabulary clean.
- Shared categorical utilities applied (section 10a): N/A - no shared grade, subject, or demographic normalizer applies.
- Tidy long format (section 9): PASS - no years, demographics, components, or category values are encoded as metric column names beyond the four explicit count measures.
- FK keys present in dimension tables (section 13): N/A - contract declares no FK columns.
- Contract-driven API semantics (row grain, filterable categoricals, FK joins): PASS - `federal_district` is an enum-bearing categorical and is part of the grain; no FK joins are advertised. See follow-up note on broader federal-district serving design.
- Standards compliance (catch-all for sections 1-16 items not enumerated above): PASS - source PII stays in bronze, counts are Int64, year is Int32, zero is real, and the source has no suppression.

## Spot Checks

### Check 1

- Bronze: Full stream of `cr96on_0.zip/cr96on.txt` yielded 6,299,908 national rows, 169,402 Georgia rows, 148,624 retained Georgia FY2000+ rows, and 81 `(year, DISTRICT)` aggregate keys.
- Transform path: `_stream_georgia_rows()` lines 278-360 and `_aggregate_to_district_year()` lines 452-522.
- Gold: All 81 recomputed rows matched the corresponding parquet rows; mismatch count was 0.
- Result: MATCH

### Check 2

- Bronze: `cr96on.txt` Georgia row at data line 752626 has `FISCALYR=2000`, `DISTRICT=3E`, `FOFFLVL1=3`, `DISP1=4`, `CTFILTRN=1`, `CTTRTRN=1`; it contributes to filed, terminated, and convicted counts, but not felony-filed.
- Transform path: aggregation expressions at lines 470-482 and district map at lines 509-518.
- Gold: Recomputed 2000 `3E` totals are `defendants_filed=1362`, `felony_defendants_filed=1044`, `defendants_terminated=1154`, `defendants_convicted=1022`; gold row `2000/georgia_northern` has the same values.
- Result: MATCH

### Check 3

- Bronze: `cr96on.txt` Georgia row at data line 6298132 has `FISCALYR=2026`, `DISTRICT=3G`, `FOFFLVL1=4`, `DISP1=4`, `CTFILTRN=1`, `CTTRTRN=1`; it contributes to all four metrics.
- Transform path: aggregation expressions at lines 470-482 and district map at lines 509-518.
- Gold: Recomputed 2026 `3G` totals are `defendants_filed=266`, `felony_defendants_filed=220`, `defendants_terminated=213`, `defendants_convicted=203`; gold row `2026/georgia_middle` has the same values.
- Result: MATCH

### Check 4

- Bronze: `cr96on.txt` Georgia row at data line 127274 has `FISCALYR=1996`, `DISTRICT=3E`, `FOFFLVL1=4`, `DISP1=-8`, `CTFILTRN=0`, `CTTRTRN=0`.
- Transform path: `_stream_georgia_rows()` filters `fiscal_year < YEAR_FLOOR` at lines 330-333 and records `pre_2000_fiscal_year_floor` at lines 413-414.
- Gold: No `year=1996` partition exists; manifest records 20,778 pre-floor Georgia rows filtered.
- Result: MATCH

## Needs Follow-up

- The federal-district grain uses `states.parquet` only because the current exporter/detail-level vocabulary has no federal-district file type. The transform and contract correctly expose `federal_district` in the grain, but the broader serving/dimension design should be resolved before approval, as already noted in project status.

## Notes

- Direct codebook checks support the metric semantics: the 1996-forward codebook defines `FISCALYR` as Oct 1-Sep 30, district codes `3E/3G/3J` as Georgia Northern/Middle/Southern, `FOFFLVL1=4` as felony, `DISP1` as the AOUSC final disposition field, conviction codes 4/5/8/9/17/19, and count fields as 0/1.
- Transfer-count caveat verified: statewide including-transfer vs excluding-transfer gaps max at about 1.27% for filings and 1.50% for terminations in served Georgia years, consistent with the contract prose.
