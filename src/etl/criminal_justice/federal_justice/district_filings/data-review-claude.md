# Data Review: district_filings

**Date**: 2026-07-07
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Zero required fixes. Gold is a faithful aggregation of the bronze IDB microdata: an independent full recompute of **all 81 gold cells** (4 metrics x 27 fiscal years x 3 districts) from the streamed `cr96on.txt` (all 6,299,908 national rows, never extracted to disk) matched gold **exactly**. Every codebook-derived semantic constant in the transform (DISP1 conviction set, FOFFLVL1 felony code, CTFILTRN/CTTRTRN flag meanings, the D-tables convention) was verified verbatim against the bundled "Criminal Code Book 1996 Forward" PDF, and both empirical contract claims (CTTRTRN ≡ TERMDATE-in-FY; excluding-transfers variant differs <1.5%/year) were independently reproduced. v1 parity: **N/A — no v1 baseline entry** (the parity script prints `DIFFERS / v1: None`, meaning "nothing to compare" — new topic, not a divergence). One judgment call carried forward from the 2026-07-04 review (re-verified, still unaddressed): FY2026's filings include 583 late-reported FY2025-commenced proceedings — a one-clause contract-caveat strengthening is recommended, no data change.

## Manifest Verification

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| federal_district | 3 | 3 (`3E`, `3G`, `3J`) | 0 | PASS |

Full map review (every entry):

| Bronze | Gold | Correct? |
|--------|------|----------|
| `3E` | `georgia_northern` | YES — bronze-data-structure.md Era 1 table: "GA `DISTRICT`: 3E = Northern, 3G = Middle, 3J = Southern" |
| `3G` | `georgia_middle` | YES — same source line |
| `3J` | `georgia_southern` | YES — same source line |

- **2a Completeness**: bronze doc documents exactly {3E, 3G, 3J} as the GA codes; all three appear in `bronze_values_seen`. No documented-but-unseen values.
- **2b Correctness**: all 3 entries semantically verified above (100% coverage).
- **2c Contract cross-check**: `gold_values_produced` = {georgia_middle, georgia_northern, georgia_southern} = contract `enum` for `federal_district`. Match.
- **2d Unmapped**: 0.
- **2e Asian/PI conflation**: N/A — no `demographic` column and no `pct_asian` column (validator: "No demographic column (skipped)").
- **2f Mutual exclusivity**: N/A — no demographic column.

Row-count reconciliation:

| Item | Value | Assessment |
|------|-------|------------|
| Bronze rows streamed | 6,299,908 | Matches the structure-doc anchor exactly (hard-asserted in `_verify_anchors_and_record`) |
| GA rows by district | 3E=80,277, 3G=45,937, 3J=43,188 | Matches structure-doc table exactly (hard-asserted) |
| Filtered: non-GA | 6,130,506 | Explicit filtered event |
| Filtered: pre-FY2000 GA | 20,778 | Explicit filtered event (project year floor) |
| GA rows aggregated (FY2000+) | 148,624 (per-year `filtered − filtered_explicit` gap) | 80,277+45,937+43,188 − 20,778 = 148,624 ✓ — aggregation, not loss |
| Gold rows | 81 = 27 years x 3 districts | Manifest `total_gold` = 81 = actual parquet row sum (verified) |
| Expansion factors | ~1.3–1.8e-05, consistent across years | Expected for microdata→district-year aggregation |
| Years | FY2000–FY2026, no gaps | Matches structure doc (FISCALYR 1996–2026; 1996–1999 floored) |

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| `DISTRICT` | `federal_district` | MAPPED |
| `FISCALYR` | `year` | MAPPED (fiscal-year basis, documented) |
| `CTFILTRN` | `defendants_filed` | MAPPED — AOUSC count flag, not raw row count (raw counts would triple-count pending defendants; codebook-prescribed method) |
| `CTTRTRN` | `defendants_terminated` | MAPPED — same convention |
| `FOFFLVL1` | `felony_defendants_filed` (derivation input) | MAPPED (FOFFLVL1=4 on flagged filings) |
| `DISP1` | `defendants_convicted` (derivation input) | MAPPED (conviction codes 4,5,8,9,17,19) |
| `PRISTOT`/`PROBTOT`/`FINETOT` | — | CORRECTLY EXCLUDED — sentinel codes (-1..-5, -8) for life/death/sealed would bias any mean; documented in contract limitations; USSC district_sentences covers sentencing |
| Offense-mix (`FTITLE*`/`FOFFCD*`/`D2*`), disposition categorical | — | CORRECTLY EXCLUDED — optional in structure doc; lean-counts decision documented in docstring |
| `SEX`/`RACE`/`BIRTHYR` demographics | — | CORRECTLY EXCLUDED — structure doc: "Era 1 only carries demographics"; Era 1 (cr70to95, 1970–1995) is entirely below the FY2000 floor |
| `CIRCUIT` | — | CORRECTLY EXCLUDED — structure doc ETL #3: circuit filter unsafe (5th→11th recode); transform filters DISTRICT only |
| `COUNTY` | — | CORRECTLY EXCLUDED — structure doc ETL #6: unreliable for criminal IDB; district grain served instead |
| `NAME`, `DOCKET`, `DEFNO`, judges/counsel, transfer/magistrate keys, load metadata | — | CORRECTLY EXCLUDED — PII/operational; the streaming parser selects only the 6 analytic fields, so PII never leaves the stream |
| `cr70to95.zip` (Era 1 file) | — | CORRECTLY EXCLUDED — covers SY1970–FY1995 only, entirely below the FY2000 project floor; analyzed in the structure doc and documented in contract limitations ("an earlier-format archive that is not ingested") |

No gold column lacks a bronze ancestor (no fabrication): all 4 metrics are sums/filtered sums of the 4 bronze code fields.

## Value-Level Spot Checks

**Full-population recompute (supersedes sampling).** All 81 gold cells were independently recomputed from bronze with a separate awk implementation over `unzip -p cr96on_0.zip cr96on.txt` (filter DISTRICT ∈ {3E,3G,3J}, FISCALYR ≥ 2000; filed = CTFILTRN=1; felony = CTFILTRN=1 & FOFFLVL1=4; terminated = CTTRTRN=1; convicted = CTTRTRN=1 & DISP1 ∈ {4,5,8,9,17,19}), then joined to gold:

```
gold rows: 81 | independent rows: 81
MISMATCHED CELLS: 0
ALL 81 gold cells == independent bronze recompute (4 metrics x 27 years x 3 districts)
```

- **4a Extremes** (covered by the full recompute; called out explicitly): global max `defendants_filed` = 1,934 — bronze recompute `CELL 2000 3G 1934 351 1986 1398` → gold (2000, georgia_middle) = 1934/351/1986/1398, MATCH (also equals manifest 2000 max). Global min `defendants_filed` = 266 (FY2026) — matches manifest min and recompute. Global max `defendants_terminated` = 1,986 (2000, 3G) — MATCH.
- **4b Ordinary trace** (one entity, single era): bronze recompute `CELL 2017 3E 620 606 613 540` → gold (2017, georgia_northern) = 620/606/613/540, MATCH.
- **4c Sentinel year-attribution**: N/A in the risky sense — `year` comes directly from the bronze `FISCALYR` column (no year parsed from strings/filenames); the only year literal is the FY2000 floor. Attribution verified by the recompute keying on FISCALYR.
- **4d Aggregate-row reconciliation**: N/A — gold derives no district/state rollup rows beyond the grain itself (no all-Georgia row; each district row is the atomic grain), and no percentages exist.
- **4e Dedup tie-break**: N/A — single bronze member, one group_by pass; `assert_no_natural_key_collisions` runs before the documented safety-net dedup.
- **4f Suppression semantics**: N/A — complete unsuppressed census (`suppressed_to_null: false`); validator confirms no suppression markers.

**Semantic constants verified against the bundled codebook** (`Criminal Code Book 1996 Forward.pdf`, extracted with pdftotext):

- DISP1: "The AOUSC uses TERMINATION DISPOSITION CODE 1 when reporting a defendant's final disposition. ... 4 - Convicted/final plea of guilty / 5 - Convicted/final plea of nolo contendere / 8 - Convicted by court after trial / 9 - Convicted by jury after trial / ... 17 - Guilty but insane (court trial) / 19 - Guilty but insane (jury trial)" — exactly `CONVICTION_DISP1_CODES`. Excluded codes verified non-convictions: "0 - Rule 20(a)/21 transfers", "10 - NARA Titles I and III", "12 - Pretrial diversion", "16/18 - Not guilty by reason of insanity". Codebook code list {0–21, -8} minus {6,7} = `KNOWN_DISP1_CODES` exactly.
- FOFFLVL1: "1 - Petty offense / 3 - Class A misdemeanor / 4 - Felony / -8 = Missing data" — `FELONY_FOFFLVL1 = "4"` correct. Observed distribution on flagged GA filings: 1→431, 3→17,248, 4→41,033, **no -8** — confirms the contract claim "the offense level is populated for every counted filing in the served years". The codebook line "Petty offenses assigned to magistrate judges are not reported to the AOUSC" backs the contract's petty-offense caveat verbatim.
- Count flags: codebook field table (fields 131/135): "Count Filings Including Transfers = CTFILTRN", "Count Terminations Including Transfers = CTTRTRN"; and "To match to the published filing statistics on those tables including inter-district transfers, the user should select cases using the fields FISCAL YEAR and COUNT FILINGS INCLUDING TRANSFERS" — the transform's exact method.
- **CTTRTRN ≡ TERMDATE-in-FY**: independently reproduced over every GA row FY2000+ — `CTTRTRN1_but_termdate_outside_fy 0` and `CTTRTRN0_but_termdate_inside_fy 0`. The contract's "verified exactly in every served year" claim holds, including FY2000–2004 (where the codebook says flags were back-calculated only to FY2005 — see Notes).
- **<1.5% excluding-transfers claim**: second stream pass comparing CTFILTRN vs CTFIL and CTTRTRN vs CTTR per GA year: `WORST filings diff: 1.267% (FY2005); WORST terminations diff: 1.091% (FY2002)` — claim holds in every year.

## Validation Cross-Read

- `_validation.json`: **19 passed, 0 failed, 0 warnings** (2026-07-07T04:09:24Z, fresh vs manifest). `contract_parquet_schema`, `contract_quality_sql` (11 checks), `grain_uniqueness` (['year','federal_district']), `foreign_keys` (none declared — correct: no dimension FKs at this grain), `geography_nulling` all pass.
- `schema_hash`: `5003140ea08dd4e100bf018fe5437653a0a243287f6a52eb0aae834e7d2dcdfb`
- **§4b masking audit**: no `_null_*` helpers in transform.py, no `masked_values` section in the manifest — correct: every metric is a sum of hard-asserted 0/1 flags, so impossible values cannot occur (domain membership hard-fails via `_assert_code_domains`). Consistent.
- **§15b coverage judgment**: authored checks cover the topic's real invariants — the two subset facts (`felony_filed_within_filed`, `convicted_within_terminated`), the FY2000 floor, the complete 3-district densified grid, and never-NULL metrics. No partition-sum or co-null families exist (no proportions, no NULLs). No missing obvious invariant.
- **v1 parity** (verbatim): `DIFFERS from v1 / v1: None / now: a45e4ee72cb048e0c83e9dcbb79e45b12f4dd6874b657deb809fc21f08bdd4db` — no baseline entry exists for `criminal_justice/federal_justice/district_filings`; new topic, parity N/A (nothing to explain).

## Cross-Era Consistency

- Single era (`newstats_fy1996_forward_144col`, one file) — no overlap years, no era boundaries. Header signature + 144-column count asserted at parse time.
- Cross-year NULL sweep: **CLEAN** for all 4 metrics (no ~100%-NULL years; no all-NULL columns).
- YoY continuity on state-level sums: smooth (all adjacent ratios within [0.66, 1.5]) for filed and felony_filed; single flags on terminated (0.48x) and convicted (0.50x) at **FY2026 only** — the documented partial fiscal year (snapshot retrieved 2026-07-04, ~3 quarters of FY2026; terminations lag filings), flagged as provisional in the contract. No >10x jumps, no cumulative-publication signature.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Only 6 analytic fields selected, deliberately (PII containment); `_parse_header` hard-fails on missing required columns and on column-count drift |
| Era routing | PASS | Single era; signature columns + 144-col count asserted on the header, never on year ranges |
| Filter logic logged + justified | PASS | Non-GA (6,130,506) and pre-floor GA (20,778) recorded as explicit filtered events; national + per-district anchors hard-asserted against the structure doc |
| Normalization map completeness | PASS | 3/3 district codes mapped; `replace_strict` would raise on any unmapped value |
| `strict=False` casts | PASS | None; `int(parts[0])` and code-domain assertions hard-fail on bad data |
| Dedup keys + tie-break | PASS | Collision guard before dedup; single-pass group_by makes collisions impossible by construction; `sort_col="defendants_filed"` documented safety net |
| Year extraction | PASS | Direct from `FISCALYR`; recompute confirms attribution |
| §4b masks (5b) | PASS | None needed; domain hard-asserts instead — documented in docstring and contract |

## NEEDS_JUDGMENT

### Judgment Call 1: FY2026 filings include 583 late-reported FY2025-commenced proceedings — strengthen the provisional-year caveat
- **Severity if confirmed**: LOW (documentation only; no data change — gold matches bronze and the AOUSC convention exactly)
- **Suspicion**: The in-progress fiscal year's `defendants_filed` is not just truncated (~3 quarters) but also compositionally distorted: 583 of FY2026's 1,238 counted filings (47%) have PROCDATE (and FILEDATE) inside FY2025 — proceedings that commenced in the prior fiscal year but were reported/loaded to the AOUSC during FY2026.
- **Evidence available**: Re-verified in this run with an independent stream pass: `FY2026 filed: procdate_in_fy=655 procdate_out=583 blank=0 unparsed=0`, while **every closed year FY2000–FY2025 shows `procdate_out=0`** (exact alignment) — implying the AOUSC reconciles FISCALYR to the proceeding year after year-end, so the current FY2026 value will likely be restated in a later snapshot. FY2026 terminations show no such spillover (CTTRTRN ≡ TERMDATE-in-FY exact, 0 mismatches).
- **Why uncertain**: Whether the AOUSC will reassign these records at year-end reconciliation (the closed-year pattern says yes) or keep them counted in FY2026 (reporting-period convention) cannot be determined from this snapshot alone; either way the served number is faithful to the current source. This item was first raised in the 2026-07-04 review; the current contract text ("the final fiscal year is partial until it closes ... treat the latest year as provisional") still does not carry the suggested clause.
- **Location**: `_emit_contract()` in transform.py — `year` column description / `limitations`.
- **If confirmed, suggested fix**: Extend the existing provisional-year caveat by one clause, e.g. "...and its counts may include late-reported proceedings that commenced in the prior fiscal year (subsequent quarterly refreshes reconcile these), so year-over-year comparisons should exclude the in-progress year." No transform-logic or data change.

## Notes

- schema_hash: `5003140ea08dd4e100bf018fe5437653a0a243287f6a52eb0aae834e7d2dcdfb`; validation 19 passed / 0 failed / 0 warnings; manifest fresh (generated 2026-07-07T04:09:23Z), read_loss events: 0.
- **Count-flag provenance for FY2000–2004**: the codebook states the count fields "were created in FY 2012. Counts for FY 2005 through FY 2011 have been calculated" — leaving FY1996–2004 formally undocumented. The transform addresses this empirically (flags fully populated 0/1 in every year) and this review independently confirmed the strongest available consistency test: CTTRTRN ≡ TERMDATE-in-fiscal-year holds with **zero** exceptions across all GA rows FY2000+, including 2000–2004, and the filed series is smooth across the 2004/2005 boundary. Adequately mitigated; no action needed.
- FY2000 georgia_middle exceeding georgia_northern in filings (1,934 vs 1,362) is genuine bronze signal, not a swap: 3G's felony share that year is low (351/1,934), consistent with high petty/misdemeanor federal-enclave volume in the Middle District's early-2000s docket; the recompute ties every cell to bronze.
- Contract prose fidelity audit found no contradictions with bronze-data-structure.md (year range, FY2026-partial, county-unreliability, no-suppression, petty-offense, and <1.5%-transfers claims all verified — several against the codebook or by direct recomputation).
