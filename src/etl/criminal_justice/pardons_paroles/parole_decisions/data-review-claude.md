# Data Review: parole_decisions

**Date**: 2026-07-07
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

All 24 gold rows verify against bronze: every global max/min of all 20 metrics was traced to a quoted bronze PDF line (via the independent `pdftotext -layout` path), all 100 crosswalk entries are semantically correct, and the per-metric NULL pattern exactly equals the transform's `EXPECTED_COVERAGE` matrix (which the run enforces). The prior review's required fix has landed: FY2023/FY2024 `rights_restorations` now ship 95 and 100 (second wrapped-label variant + anchors), verified here against the published pardons+restorations identities. The one load-bearing judgment — mapping Era 3 "Total Prison Releases by Parole" to `total_releases` rather than the structure doc's proposed `parole_releases` — is proven correct by component sums quoted from bronze (FY2016: 7,233+426+904+183+1,517+21+2,850+25+215 = 13,374). No Required Fixes; one LOW judgment item: the structure doc's proposed `cost_avoidance` / cost-per-day metrics were never served and the exclusion is not documented in the served contract. v1 parity: N/A — `docs/rebuild/v1-baseline.yaml` has no entry for this topic.

## Manifest Verification

| Column | Map entries | Bronze seen | Unmapped | Status |
|--------|------------|-------------|----------|--------|
| metric_source_label | 100 | 99 | 0 | PASS |
| supervision_era | 2 (identity) | 2 | 0 | PASS |

**metric_source_label — 100% semantic review.** Every entry of `map_used` was reviewed; groups and verdicts:

- **Era 1/2 clemency-action table** — `parole → parole_releases`, `supervised reprieve(s) → supervised_reprieves`, `conditional transfer(s) → conditional_transfers`, `commutation(s) → commutations`, `total releases → total_releases`, `total parole revocations → parole_revocations`, `total discharges → total_discharges`, `total decision(s) under guidelines → guidelines_decisions_total` (FY2006 singular variant included), `initial decisions under guidelines → guidelines_decisions_initial`, `deny/grant parole to life cases → life_cases_denied/_granted`, `total life decisions → life_decisions_total`, `pardon → pardons_granted`, `restoration of rights → rights_restorations`, `total parolee/parole population → parole_population_end` — all CORRECT (each label matches its published table row; values verified below).
- **FY2014 + Era 3 stats table** — `parole certificates → parole_certificates`, `total prison releases by parole → total_releases` (**verified as the rollup, not the parole line** — see Spot Checks), `total discharges from parole → total_discharges`, `initial guidelines decisions → guidelines_decisions_initial`, `total guidelines decisions → guidelines_decisions_total`, `life sentence(d) cases granted/denied (parole)` + `granted/released → life_cases_granted/_denied`, `pardon grants` / `pardons granted all types → pardons_granted`, `restoration of (civil and political )rights granted → rights_restorations` (incl. both wrapped-label variants) — all CORRECT.
- **Internal verification-only series** (`_remission`, `_other_releases`, `_discharge_from_*`, `_commutation_to_discharge`, `_pop_*`, `_oos_*`, `_medical_reprieves`, `_other_guidelines_decisions`, `_total_pardons_restorations`) — correctly withheld from gold; used by the sum identities.
- **PROSE:/LINE:/BAND:/TRANSCRIBED: entries** — each regex/source is scoped to the years and metric it claims (revocations prose, completion-rate percent→proportion, population July-1/June-30 pair, expenditures millions-format guards, FY2025 clemency-votes tile) — CORRECT.
- **2a completeness**: 99 of 100 map entries were seen in bronze; the single unseen entry (`total pardons restorations granted`, the no-ampersand variant of the seen `total pardons & restorations granted`) is a defensive variant — not a routing bug. Every metric label documented in bronze-data-structure.md's era descriptions is covered; doc-listed labels intentionally not served (`Commutation Reducing Sentence`, `Medical/Compassionate Reprieve`, `Visitor Interview`, per-unit Pardon Administration counts) are correctly absent from gold.
- **2c**: `supervision_era` gold values {board, dcs} match the contract enum exactly. `metric_source_label` is a process categorical (not a gold column) — no contract enum applies. **2d**: unmapped_count = 0 for both.
- **2e Asian/PI conflation**: N/A — no `demographic` column and no race metrics exist (statewide clemency counts only).
- **2f Mutual exclusivity**: N/A for demographics. The analogous era-scoped pair `parole_releases`/`parole_certificates` never coexists in any year (contract quality check `parole_releases_certificates_mutually_exclusive` passes).

**Row-count reconciliation**: 24 bronze "rows" (one statewide observation per report) → 24 gold rows, expansion factor 1.00x in all 24 years; 0 filtered; parquet total (24) equals manifest `total_gold` (24). FY2015 absent by source (never published); FY2016 counted once (the 2-up `annual_report_fy2016_spread.pdf` is skipped as a provenance-only duplicate — `files_processed` lists exactly 24 files, one per year).

## Column Coverage

| Bronze concept (structure doc) | Gold column | Status |
|---|---|---|
| fiscal year (title/filename) | `year` | MAPPED (canonical name, not the doc's `fiscal_year`) |
| statewide (implicit) `county_fips` | — | CORRECTLY EXCLUDED (geography omitted entirely, mirroring gdc/inmate_population; validator geography-nulling passes; documented in contract usage) |
| Parole / Total Prison Releases by Parole | `parole_releases` (Era 1/2 only) | MAPPED — **deliberately split from the doc's proposal**: the Era 3 label is the release-actions TOTAL (component-sum proof below), so pooling it into `parole_releases` as the doc proposed would have been wrong |
| Parole Certificates | `parole_certificates` | MAPPED |
| TOTAL RELEASES | `total_releases` | MAPPED (key metric — the only full-coverage series) |
| Supervised Reprieve / Conditional Transfer / Commutation | `supervised_reprieves` / `conditional_transfers` / `commutations` | MAPPED |
| TOTAL/Initial DECISIONS UNDER GUIDELINES | `guidelines_decisions_total` + `guidelines_decisions_initial` | MAPPED (doc proposed one pooled `guidelines_decisions`; the split is more correct — the two definitions differ and are never pooled) |
| Grant/Deny Parole to Life Cases, TOTAL LIFE DECISIONS | `life_cases_granted` / `life_cases_denied` / `life_decisions_total` | MAPPED |
| TOTAL PAROLE REVOCATIONS / "revoked N violators" | `parole_revocations` | MAPPED |
| DISCHARGES | `total_discharges` | MAPPED |
| Pardons Granted / Pardon | `pardons_granted` | MAPPED |
| Restorations of Civil & Political Rights | `rights_restorations` | MAPPED (incl. FY2023/FY2024 second wrap variant) |
| Parole population July 1 / June 30 | `parole_population_start` / `parole_population_end` | MAPPED |
| Successful completion rate | `parole_completion_rate` | MAPPED (%→[0,1]) |
| Clemency votes | `clemency_votes` | MAPPED |
| TOTAL EXPENDITURES | `total_expenditures` | MAPPED |
| Cost avoidance / cost-per-day | — | **MISSING vs the doc's proposal** — see Judgment Call 1 |
| Board bios / narrative | — | CORRECTLY EXCLUDED (not_in_gold) |

No gold column lacks a bronze source (no fabrication); `supervision_era` is a derived methodological flag (pure function of year, HB310), matching the domain "version methodological breaks" rule.

## Value-Level Spot Checks

All quotes below are from `pdftotext -layout` output of the bronze PDFs — an extraction path independent of the transform's pdfplumber geometry.

**Extreme rows (global max/min of every metric)** — all MATCH:

| Metric | Extreme | Bronze quote | Gold |
|---|---|---|---|
| total_releases max | FY2014 | `TOTAL RELEASES 16,212` | 16212 ✓ |
| total_releases min | FY2024 | `Total Prison Releases by Parole 5,443` | 5443 ✓ |
| parole_releases max | FY2011 | `Parole 10,938` | 10938 ✓ |
| parole_releases min | FY2001 | FY2001 table block with `TOTAL RELEASES 10,164` (anchor 7,305) | 7305 ✓ |
| parole_certificates max/min | FY2014 / FY2024 | `Parole Certificates 8,934` / `Parole Certificates 3,890` | 8934 / 3890 ✓ |
| supervised_reprieves max | FY2005 | `Supervised Reprieve 2,779` | 2779 ✓ |
| conditional_transfers max | FY2013 | table row (sum-verified: 10,828+1,780+1,669+1,357 = 15,634 = published total) | 1669 ✓ |
| commutations max | FY2014 | `Commutations 3,119` | 3119 ✓ |
| guidelines_decisions_total max/min | FY2019 (anchor 15,535) / FY2016 `Total Guidelines Decisions 8,439` | 15535 / 8439 ✓ |
| guidelines_decisions_initial max | FY2013 | `INITIAL DECISIONS UNDER GUIDELINES 14,915` | 14915 ✓ |
| life_cases_granted min | FY2024 | `Life Sentence Cases Granted/released 93` | 93 ✓ |
| life_cases_denied max | FY2025 | stats table (2,154; total 2,277 = 123+2,154) | 2154 ✓ |
| parole_revocations max | FY2005 | `TOTAL PAROLE REVOCATIONS 3,684` | 3684 ✓ |
| parole_revocations min | FY2025 | `During FY25, the Board revoked 1,273 parole viola-` + `FY25 1,273` chart | 1273 ✓ |
| total_discharges max | FY2012 | `TOTAL DISCHARGES 13,505` | 13505 ✓ |
| total_discharges min | FY2025 | `from parole was 4,729` | 4729 ✓ |
| pardons_granted max/min | FY2013 (anchor 1,349) / FY2020 `Pardon Grants .....323` | 1349 / 323 ✓ |
| rights_restorations max | FY2001 | `Restoration of Rights 332` | 332 ✓ |
| rights_restorations min | FY2018 | wrapped label `Rights Granted. ... 70`; identity 412+70 = published `Total Pardons & Restorations Granted.......482` | 70 ✓ |
| clemency_votes max | FY2013 | `the five members made 88,302 clemency votes` | 88302 ✓ |
| clemency_votes min | FY2022 | `51,243 Clemency votes` | 51243 ✓ |
| parole_population_start max/min | FY2016 `decreased from 23,859 on July 1, 2015, to 22,901` / FY2025 `from 15,105 on July 1, 2024, to 14,568` | 23859 / 15105 ✓ |
| parole_population_end max | FY2013 | `TOTAL PAROLE POPULATION 27,285` (components 24,026+994+2,265 = 27,285) | 27285 ✓ |
| parole_population_end min | FY2025 | `to 14,568 on` (June 30) | 14568 ✓ |
| parole_completion_rate max | FY2013 | `At 74%, the Georgia pa-` … `rate rose to 74%` | 0.74 ✓ |
| parole_completion_rate min | FY2005 | `60% of Georgia's parolees successfully completed` | 0.60 ✓ |
| total_expenditures max | FY2008 | `Total Expenditures $55,980,192` | 55980192.0 ✓ |
| total_expenditures min | FY2017 | anchor 16,846,903 (FY2016 `Total: $45,782,940` and FY2025 `Total FY25 Expenditures $21,634,700.96` also verified) | 16846903.0 ✓ |

**The load-bearing mapping judgment (Risk 7)** — Era 3 "Total Prison Releases by Parole" is the release-actions TOTAL, not the parole line: FY2016 bronze prints `Parole Certificates 7,233`, `Commutations 2,850`, `Total Prison Releases by Parole 13,374`; the nine published components sum to exactly 13,374, and 7,233 ≠ 13,374 — so the label is the rollup and correctly maps to `total_releases`, with the Era 1/2 `Parole` line kept as the separate `parole_releases`. MATCH.

**Ordinary traces, one per era** — all MATCH:

- **Era 1 (FY2005, full row)**: bronze `CLEMENCY ACTION IN FY05` table — Parole 8,956, Supervised Reprieve 2,779, Conditional Transfer 972, Commutation 1, Remission 0, Other 0, TOTAL RELEASES 12,708 (8,956+2,779+972+1 = 12,708 exact); TOTAL PAROLE REVOCATIONS 3,684; Discharges 5,841+1,823+171 = 7,835; TOTAL DECISIONS UNDER GUIDELINES 15,315; Life 495 denied + 188 granted = 683; Pardon 335; `TOTAL EXPENDITURES 45,135,674.89`; `the parolee population stood at 24,276`; `60%`. Gold FY2005 row equals every one of these.
- **Era 2 (FY2013)**: 88,302 votes, population components 24,026+994+2,265 = 27,285, 74%, INITIAL DECISIONS 14,915, revocations 2,199 (restated by the FY2014 report, whose own 2,380 appears as `During FY14, 2,380 offenders had their paroles revoked`). Gold matches. Note: the FY2013 narrative's "22,480 → 25,020" population pair is the **in-Georgia-only** basis (24,026+994 = 25,020) — the transform correctly captures the table total (27,285) and not the narrative pair.
- **Era 3 (FY2022, FY2024)**: `The Board released 6,245 offenders in FY22`; `51,243 votes`. FY2024: table 5,443 / 3,890 / 1,953 / 93 / 2,046 / 346; `Total Discharges from Parole 4,930` **and** prose `from parole was 4,930` (the table/prose cross-check the transform relies on, observed directly); revocations `the Board revoked 1,437` with the FY2025 chart restating 2,373/1,825/1,552/1,437 for FY21–FY24; wrapped restorations identity 346+100 = published `Total Pardons & Restorations Granted 446`. All equal gold.
- **Transcribed years (FY2002/FY2007/FY2008)**: table pages are images (no text layer) — text-level verification impossible by construction; the transcriptions pass the same component-sum identities at runtime, and the two **parsed** values in those reports verify directly: FY2007 `61%` + `TOTAL EXPENDITURES $51,403,882`; FY2008 `64%` + `Total Expenditures $55,980,192`. Gold matches all four.

**4c Sentinel year-attribution**: PASS — `year` comes solely from the filename (`fy(\d{4})`), and bronze-data-structure.md states filename FY = report FY with no offset. Year-bearing prose (e.g. "on July 1, 2024") is never captured as a value: the population regex captures only comma-grouped thousands, and the expenditures patterns require a millions-format token precisely so "FY 2018" can never be captured.

**4d Aggregate reconciliation**: N/A for derived rows (nothing is derived; one published state row per year). The bronze-published rollups are instead reconciled as identities: release components = total (exact in FY2005/FY2013/FY2016; FY2001–FY2013 residual ≤ 23 = remission/other, enforced by `board_era_release_components_reconcile`), life granted+denied = total, discharge components = total, population components = total, pardons+restorations = combined total (FY2018: 412+70=482; FY2023: 469+95=564; FY2024: 346+100=446).

**4e Dedup tie-break**: N/A — no overlap years; one report per fiscal year (the FY2016 spread duplicate is skipped before parsing). The collision guard runs before dedup and would raise on any future overlap.

**4f Suppression semantics**: N/A — the source publishes unsuppressed statewide aggregates (`suppressed_to_null: false`); NULL means "not published", set per `EXPECTED_COVERAGE`, never from a marker.

## Validation Cross-Read

- `_validation.json` (2026-07-07T04:35:49Z): **18 passed, 0 failed, 1 warning**; `contract_parquet_schema`, `contract_quality_sql` (31 checks), `grain_uniqueness` (year × supervision_era), `foreign_keys` (none declared — correct: no geography/demographic columns) all pass.
- The single warning is `null_rate_spikes` (39 spikes). Every flagged (column, year) is exactly a documented coverage gap: FY2009's 18-page mini-report (most metrics), the guidelines total-vs-initial era split, clemency-votes publication windows (FY2009–14, FY2019+), pardons/restorations FY2025 (split-only publication, verified below), completion-rate FY2001–04 (non-comparable RDS formula), expenditures FY2009/FY2012–14 (no published total — FY2012 prints only fund-source `Total Funds $54,510,846`, verified). The flagged set is congruent with `EXPECTED_COVERAGE`, which the transform asserts exactly — nothing unexplained.
- **§4b masking audit**: PASS — no `_null_*` helpers in transform.py, no `masked_values`/`read_loss`/`reclassified` sections in the manifest (absent = zero events), `suppressed_to_null: false`, and per-column `null_meaning` documents every NULL family. Nothing is masked; every extracted value is sum- or anchor-verified instead.
- **§15b coverage judgment**: GOOD — 10 authored quality checks cover the real invariants: life components sum, release components within/reconciling to total, era-scoped mutual exclusivity of `parole_releases`/`parole_certificates`, initial ≤ total guidelines, HB310 era boundary, FY2015 gap, year floor, key-metric completeness, population-start era scoping. The DCS-era population chain (July-1 start = prior June-30 end) is enforced at transform time (`_verify_cross_year`) but is a cross-row invariant not expressed in the contract's quality SQL — acceptable, noted in Notes.
- **v1 parity**: `DIFFERS from v1 / v1: None / now: c07c328b252da9f27aea6bb40a3e41690b98d9b3c0128e293c26411676ec85e0` — the baseline has **no entry** for this topic (new criminal_justice topic, not in the v1 baseline), so this is a documented N/A, not a drift finding.

## Cross-Era Consistency

- **No overlap years** between eras (era = f(year)); the FY2016 duplicate file never enters the pipeline.
- **Era-boundary continuity**: the FY2014→FY2016 discontinuities are real and flagged — `total_expenditures` drops ~$45–56M → ~$17–22M (HB310 moved supervision costs to DCS; `supervision_era` + contract prose document it); `parole_population_*` changes basis (board table vs DCS narrative; documented per column). The clemency-decision series is continuous across the break.
- **Cross-year NULL sweep**: every ~100%-NULL (column, year) cell matches `EXPECTED_COVERAGE` exactly (re-derived independently from gold parquet). No column is NULL in all years. No era-localized rename bug signature.
- **>10x YoY jumps**: `commutations` 350→19→1,357 (FY2011–13) and 1,215→1 (FY2017–18) — genuine policy volatility; the outlying values are anchor-pinned (FY2012 = 19; FY2018 = 1 appears verbatim in bronze: `Commutations....1`) and release-sum-verified. No scale inconsistency; no cumulative-publication signature.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — `EXPECTED_COVERAGE` asserts the exact non-NULL pattern per metric; a silently failed parse or unexpected new match fails the run loudly |
| Era routing | — | PASS — era label is a function of year; 24 files processed, spread duplicate skipped with logged reason; bronze inventory asserted against `ALL_YEARS` |
| Filter logic | — | PASS — only the defensive year≥2000 floor (0 rows dropped; would be manifest-recorded) |
| Normalization map completeness | — | PASS — all doc-listed labels covered incl. FY2006 singular/slash variants and both wrapped-label forms; 1 unseen defensive variant only |
| `strict=False` casts | — | N/A — values are typed explicitly (int/float per metric) before the frame is built |
| Dedup keys + tie-break | — | PASS — collision guard (raises on divergent duplicates) runs before `deduplicate_by_levels(sort_col="total_releases")`; collisions impossible by construction today |
| Year extraction | — | PASS — filename `fy(\d{4})`; doc confirms zero offset |
| §5b masks | — | PASS — none exist; nothing unrecorded |
| Divergent-duplicate guards | — | PASS — `_merge_value`, table-duplicate, prose multi-match, and population-pair divergence all raise rather than pick silently; Era 3 prose restatements act as free cross-checks (observed: FY2024 discharges table = prose = 4,930) |

## NEEDS_JUDGMENT

### Judgment Call 1: Proposed cost-avoidance / cost-per-day metrics were not served and the exclusion is undocumented
- **Severity if confirmed**: LOW
- **Suspicion**: bronze-data-structure.md's Gold Schema Classification proposes `cost_avoidance` (and/or `parole_cost_per_day` / `prison_cost_per_day`, `unit: currency`) as a fact_metric, but no such column exists in gold, and neither the transform docstring's design-decision list nor the served contract (`limitations`/`description`) mentions the exclusion.
- **Evidence available**: structure doc line: "Cost avoidance / cost-per-day | fact_metric | `cost_avoidance` … basis varies by era (ETL #11) — document, don't recompute." Gold columns contain no cost metric. The doc itself flags the extraction obstacle: these values live in chart labels and prose whose basis changes across eras ("$/day parole vs prison in Era 1; aggregate '$380 million cost avoidance' in Era 3") and ETL #2 notes chart labels are mangled by text extraction.
- **Why uncertain**: the omission looks intentional and defensible (era-inconsistent basis + chart-label extraction infeasibility), but the intent is not recorded anywhere a data consumer or future maintainer can see — the structure doc says "document, don't recompute", and nothing was documented.
- **Location**: `_emit_contract()` (limitations/usage) in `src/etl/criminal_justice/pardons_paroles/parole_decisions/transform.py`; optionally the module docstring's design-decision list.
- **If confirmed, suggested fix**: add one sentence to the contract `limitations` (and the docstring) stating that the reports' cost-avoidance / cost-per-day figures are not served because their published basis changes across eras and the values are chart-label/prose-only; alternatively serve them as era-scoped metrics later. No gold values change.

## Notes

- schema_hash: `6caab5ad63e796fe14882ea42cc517ca18e1671d41792ebce1d34591638a9713`; contract `version: 1.0.0`.
- Validation: 18 passed / 0 failed / 1 warning (null_rate_spikes — fully explained above). Manifest fresh (generated 2026-07-07T04:35:49Z, validation 108ms later); no read-loss events.
- Contract prose fidelity: audited against bronze-data-structure.md — no contradictions. Notable verified claims: FY2025 publishes pardons/restorations **only** as a with/without-firearms split (bronze: `Pardons granted without firearms being restored 169`, `Pardons granted with firearms being restored 164`, `rights with firearms restored 23` — no total line), and NOT summing them is provably right because in years publishing both, the split does not sum to the all-types total (FY2014: 297+684 = 981 ≠ published `Pardons Granted (all types) 1,151`); FY2009 prose `By Board action 12,938 offenders were released` / `75,245 individual votes` / `66%`; FY2012 publishes only `Total Funds $54,510,846` (a fund-source budget, hence NULL expenditures).
- The DCS-era population chain check lives only in the transform (`_verify_cross_year`), not the contract quality SQL. Since gold can only change via the transform, it is enforced at every rewrite; authoring a window-function quality check would additionally cover served-gold conformance runs but is optional.
- Grain is (`year`, `supervision_era`) per the contract; `supervision_era` is a pure function of `year` (enforced by `supervision_era_matches_hb310_boundary`), so this is equivalent to one row per fiscal year.
- The three transcribed years (FY2002 scan; FY2007/FY2008 image tables) are unverifiable by text extraction by construction; their values carry page-level provenance in `TRANSCRIBED_VALUES` and pass the same sum identities as parsed years. FY2007/FY2008's parsed (non-transcribed) values were independently verified here.
