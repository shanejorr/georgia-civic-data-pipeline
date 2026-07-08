# Data Review: gsp_traffic_stops

**Date**: 2026-07-07
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Every value-level trace ties out exactly: the five state `all` rows reproduce the bronze per-year stop counts to the row (372,285 / 415,242 / 411,036 / 369,441 / 338,768), all six race-group state totals across years match independent bronze recounts to the stop, and ordinary + extreme cell traces (Fulton 2014, Echols 2016, Taliaferro 2012, global min cell Baker 2012) all MATCH. v1 parity is N/A — `docs/rebuild/v1-baseline.yaml` has no entry for this topic (new in v2). The combined `asian_pacific_islander` convention is correct (bronze publishes only the combined `asian/pacific islander` bucket; no separate Pacific Islander value exists anywhere in the source), and the race axis partitions the `all` row exactly (ratio 1.0000).

## Manifest Verification

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| demographic | 6 | 6 | 0 | PASS |
| county_fips | 166 (159 FIPS + 7 placeholder markers) | 166 | 0 | PASS |

**demographic — full map review (6/6 entries):**

| Bronze | Gold | Correct? |
|--------|------|----------|
| `white` | `white` | YES |
| `black` | `black` | YES |
| `hispanic` | `hispanic` | YES |
| `asian/pacific islander` | `asian_pacific_islander` | YES — source's combined bucket (structure doc: "no separate Pacific Islander value → maps to asian_pacific_islander, never bare asian") |
| `other` | `other` | YES — source standardization folds raw `Native American` (4,339) into `other` (7,984 = 4,339 + 3,645); documented in the contract description |
| `unknown` (fill for the NA sentinel) | `race_unknown` | YES — 898,309 stops (47.1%) with unrecorded race, published as a real race-axis population so the six race values partition `all` exactly; deliberate, documented revision of the "NULL demographic stays NULL" default, appropriate for microdata |

**county_fips — map review (166 entries):** 159 real county names (post " County"-strip) → 5-digit FIPS via the shared `add_county_fips` crosswalk. Spot-verified semantically: Fulton→13121, Cobb→13067, Gwinnett→13135, Clarke→13059, Muscogee→13215, Richmond→13245, Bibb→13021, Echols→13101, Taliaferro→13265, Baker→13007 — all correct; the validator's FK check confirms all 159 keys resolve in the counties dimension. The 7 `G###` placeholder codes (G047/G059/G115/G139/G143/G213/G223) map to the explicit `state_rollup_only_no_county_fips` marker — deliberately excluded from county rows and kept in the state rollup, with a hard-stop guard for any non-G-code unmatched name.

- **2a Completeness**: bronze_values_seen for `demographic` covers all 5 real race labels + the `unknown` fill (doc lists exactly `white/black/hispanic/asian pacific islander/other/NA`); `county_fips` covers all 159 real counties + 7 placeholders documented in the structure doc. No documented value unencountered. PASS.
- **2c Contract cross-check**: `gold_values_produced` (6 race values) ∪ {`all`} (added at aggregation) == contract enum of 7. PASS.
- **2d Unmapped**: 0 in both columns. PASS.

**2e Asian/PI (Risk 1): PASS — combined bucket published under the correct name.** No NHPI/Pacific-Islander-only label exists in bronze; the structure doc's explicit check: "publishes a combined `asian/pacific islander` bucket (8,753) with no separate Pacific Islander value". Positive math test at latest state row:

```
traffic_stops: year=2016 total=338768 race_sum=338768 ratio=1.0000
```

**2f Mutual exclusivity (Risk 6): PASS — single convention.** Only the combined `asian_pacific_islander` rollup is emitted; no `asian`/`pacific_islander` split rows exist.

### Row-count reconciliation

| Year | Bronze stops | Gold cells | Filtered (explicit) | Assessment |
|------|-------------:|-----------:|--------------------:|------------|
| 2012 | 372,285 | 1,060 | 0 | aggregation (factor ~0.0028) |
| 2013 | 415,242 | 1,052 | 4 | 4 G-code stops → state rollup only |
| 2014 | 411,036 | 1,064 | 5 | 5 G-code stops → state rollup only |
| 2015 | 369,441 | 1,048 | 1 | 1 NULL-county stop → state rollup only |
| 2016 | 338,768 | 1,060 | 0 | — |

Bronze per-year totals match the structure doc's statistics line exactly. The "filtered" bulk is aggregation collapse (1.9M stops → 5,284 cells), not row loss; the 10 explicitly-filtered stops are the documented unmappable-county set, and my bronze recount confirms their year distribution independently (G-code rows: 2013=4, 2014=5; NULL county row: one 2015-02-16 stop). Actual parquet rows = 5,284 = manifest `total_gold`. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| county_name | county_fips | MAPPED (strip " County" → add_county_fips) |
| date | year | MAPPED (`date[:4]`, NULL-year hard-stop) |
| subject_race | demographic | MAPPED (NA → race_unknown) |
| (row count) | traffic_stops | MAPPED (group_by count; key_metric) |
| subject_sex | — | CORRECTLY EXCLUDED (structure doc marks it optional — "else roll into `all`"; transform rolled into `all`) |
| raw_race | — | CORRECTLY EXCLUDED (audit-only pre-standardization string) |
| outcome, type | — | CORRECTLY EXCLUDED (constants `warning` / `vehicular`; zero information — scope stated in contract) |
| violation | — | CORRECTLY EXCLUDED (30,255-value dirty free text) |
| location, lat, lng, time, officer_id_hash | — | CORRECTLY EXCLUDED (PII; never read — READ_COLUMNS restricts the read to 3 columns) |
| department_name | — | CORRECTLY EXCLUDED (effectively constant single agency; 302-row residual documented in limitations) |
| vehicle_color/make/model/year, raw_row_number | — | CORRECTLY EXCLUDED (descriptors / source row id) |

No gold column lacks a bronze source (traffic_stops is a transform-computed count, declared as such). The exact-header guard (`EXPECTED_HEADER`) hard-stops on any source format change.

**Contract prose fidelity**: audited `purpose`/`limitations`/`usage` and column descriptions against the structure doc — 47.1% unknown race, 10 of 1,906,772 unmappable stops, 302 residual agency-label rows (298 DNR + 4 GSP), warnings-only/no search/contraband/arrest/citation fields, combined AAPI bucket, Native American folded into `other`, frozen 2012-2016 coverage, no suppression. No contradictions found.

## Value-Level Spot Checks

All bronze figures below independently recomputed from the zip member (`ga_statewide_2020_04_01.csv`, 1,906,772 rows) reading only `date`/`county_name`/`subject_race`.

**Extreme rows first:**

| Trace | Bronze evidence | Gold | Verdict |
|-------|-----------------|------|---------|
| Global max (state `all` 2013) | 415,242 stops with `date` starting `2013` | 415,242 | MATCH |
| State `all`, all 5 years | 372,285 / 415,242 / 411,036 / 369,441 / 338,768 | identical | MATCH (×5) |
| Global min (Baker County 2012, `other`) | exactly 1 bronze row: `{date: 2012-09-09, county_name: Baker County, subject_race: other}` | 1 | MATCH |

**State race totals (sum over 2012-2016) vs bronze `subject_race` counts:**

| demographic | Bronze | Gold | Verdict |
|-------------|-------:|-----:|---------|
| white | 660,855 | 660,855 | MATCH |
| black | 297,156 | 297,156 | MATCH |
| hispanic | 33,715 | 33,715 | MATCH |
| asian_pacific_islander | 8,753 | 8,753 | MATCH |
| other | 7,984 | 7,984 | MATCH |
| race_unknown | 898,309 (bronze NA count) | 898,309 | MATCH |

**Ordinary cell traces (single era):**

| Cell | Bronze recount | Gold | Verdict |
|------|---------------:|-----:|---------|
| Fulton (13121) all-years `all` | 108,085 (doc top-county figure confirmed) | 108,085 | MATCH |
| Cobb (13067) all-years `all` | 71,779 | 71,779 | MATCH |
| Gwinnett (13135) all-years `all` | 70,789 | 70,789 | MATCH |
| Fulton 2014 `black` | 5,370 | 5,370 | MATCH |
| Fulton 2014 `asian_pacific_islander` | 174 | 174 | MATCH |
| Echols (13101) 2016 `hispanic` | 33 | 33 | MATCH |
| Taliaferro (13265) 2012, all 7 rows | black 93, aapi 3, hispanic 2, race_unknown 141, white 138, other 4 (sum 381) | identical incl. `all`=381 | MATCH |

**4c Sentinel year-attribution (Risk 3)**: PASS — `year` derives per-row from the ISO `date` column (`date[:4]`, strict NULL guard); the manifest's file-level `year: 2016` is bookkeeping only. Per-year gold totals matching the doc's per-year bronze counts prove correct attribution.

**4d Aggregate-row reconciliation (Risk 4)**: PASS — state rows are derived by summing counts (never averaging). Per (year, demographic), state − county_sum diffs are exactly {2013 `all`: +4, 2014 `all`: +5, 2015 `all`: +1, plus consistent race-slice components}, totaling the 10 unmappable stops in the correct years; all other groups diff 0.

**4e Dedup tie-break (Risk 5)**: N/A — single bronze file, single era; every cell comes from one group_by, collision guard runs first.

**4f Suppression semantics**: N/A — unsuppressed microdata (structure doc: "no small-count suppression codes"); `suppressed_to_null: false`.

## Validation Cross-Read

- `_validation.json`: **20 passed / 0 failed / 0 warnings** (2026-07-07T04:27:31Z, fresh vs manifest). `contract_parquet_schema`, `contract_quality_sql` (7 checks), `grain_uniqueness` (year × county_fips × demographic), and `foreign_keys` (159 county + 7 demographic keys resolve) all pass.
- **schema_hash**: `a9064c5e243b69cd245d5f1179c4452ce26594605e0ff92c4a9ad091589d024a`
- **§4b masking audit**: PASS — no `_null_*` helpers in transform.py, no `masked_values` section in the manifest; consistent with the docstring rationale (the sole metric is a transform-computed row count; no source-published value exists to mask). `lat`/`lng` garbage is moot — coordinates are never read.
- **§15b coverage judgment**: PASS — the authored quality checks cover the topic's real invariants: `race_partition_traffic_stops` (six race rows sum exactly to `all` per year × county), `state_covers_county_sum` (state ≥ county sum, excess ≤ 10), `traffic_stops_positive` (no zero-fill), `year_at_or_after_2000`. No obvious invariant is missing for a single-metric count table.
- **v1 parity**: verbatim —

```
DIFFERS from v1
  v1:  None
  now: 6cc86c1646f5ddd94b2cc11e6b38b6d31a266097f24708caa970ffcae30237f2
```

  N/A in substance: `docs/rebuild/v1-baseline.yaml` has no entry for `criminal_justice/open_policing/gsp_traffic_stops` — this topic is new in v2, so there is no baseline to match.

## Cross-Era Consistency

- **Single era** (`sopp_ga_statewide_v1`), single frozen file — no overlap years, no era boundaries.
- **Cross-year NULL sweep (Risk 2)**: clean — no column is ≥95% NULL in any year (`traffic_stops` has zero NULLs everywhere; `county_fips` NULL only on the 7 state rows per year, by design).
- **Year-over-year continuity (3d)**: state `all` moves 372,285 → 415,242 → 411,036 → 369,441 → 338,768 (max adjacent ratio 1.12x). No 10x jumps, no cumulative-publication signature.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Only 3 columns read by design (PII contract); `EXPECTED_HEADER` byte-exact guard hard-stops on any header change |
| Era routing | PASS | Single era; signature guard present for future format drift |
| Filter logic logged + justified | PASS | 10 unmappable-county stops recorded via `record_filtered` with reason, bounded by `UNMAPPABLE_STOPS_BOUND=10` hard-stop; year floor defensive (0 rows) |
| Normalization map completeness | PASS | All 6 race labels + 166 county labels covered; unexpected demographic value raises; non-G-code unmatched county name raises |
| `strict=False` casts | PASS | Only on `date[:4]→year`, immediately followed by a NULL-count hard-stop (net effect is strict) |
| Dedup keys + tie-break | PASS | Collision guard before dedup; duplicates impossible by construction (one file, one group_by); `sort_col="traffic_stops"` documented safety net |
| Year extraction | PASS | Per-row from ISO date; verified against doc per-year counts |
| §4b masks (5b) | PASS | None needed; absence justified in docstring and manifest |

## Notes

- schema_hash `a9064c5e243b69cd245d5f1179c4452ce26594605e0ff92c4a9ad091589d024a`; validation 20/0/0; manifest generated 2026-07-07T04:27:31Z.
- Read-loss: 0 events (streamed line count minus header equals parsed rows).
- The transform deviates from the structure doc's ETL #3 proposal (NULL county_fips on the 10 unmappable stops) in favor of excluding them from county rows and keeping them in the state rollup. This is the better choice — a NULL `county_fips` at county detail would collide with the state-row convention — and it is documented in the docstring, the contract `limitations`, and enforced by the `state_covers_county_sum` quality check. Not a finding.
- `subject_sex` (3.9% NA) is available in bronze should a sex-axis breakdown ever be wanted; the structure doc marks it optional and the transform rolled it into `all`.
