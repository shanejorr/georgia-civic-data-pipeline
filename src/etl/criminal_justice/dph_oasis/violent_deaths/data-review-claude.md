# Data Review: violent_deaths

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Bronze-to-gold accuracy verified end-to-end with no Required Fixes and no
NEEDS_JUDGMENT items. All 17 categorical map entries (4 cause + 11 demographic +
2 icd) are semantically correct; row counts reconcile exactly (22,272 bronze −
1,316 filtered = 20,956 gold, matching the parquet and every-year 676-row grid);
every value-level spot check (both global extremes, the -5 and -2 suppression
sentinels, the ICD-9/ICD-10 boundary) MATCHES bronze byte-for-byte; the race and
sex breakdowns partition exactly to the `all` row and the 159 counties sum
exactly to the statewide total; and the sentinel-mask count recomputed
independently equals the manifest and the gold NULL count exactly (6,104 per rate
column). v1 parity: **no v1 baseline (topic is post-v1)** — `docs/rebuild/v1-baseline.yaml`
has no `criminal_justice` entries, so the parity script prints `v1: None`; not a
real divergence.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| cause_of_death | 4 | 4 | 0 | PASS |
| demographic | 11 | 11 | 0 | PASS |
| icd_revision | 2 | 2 | 0 | PASS |

**cause_of_death** (filename slug → gold, identity map, semantically correct):
- `homicide` → `homicide` — correct (OASIS "Assault").
- `suicide` → `suicide` — correct ("Intentional Self-Harm").
- `legal_intervention` → `legal_intervention` — correct (law-enforcement deaths).
- `accidental_shooting` → `accidental_shooting` — correct (unintentional firearm).

**demographic** (each entry verified against `src/utils/demographics.py` canon):
- `All Races` → `all` — correct (race total).
- `All Sexes` → `all` — correct (sex total; same `all` key as race total, deduped).
- `Asian` → `asian` — correct (split convention, separate from PI).
- `Native Hawaiian or Other Pacific Islander` → `pacific_islander` — correct (split partner; NOT conflated into asian).
- `Black or African-American` → `black` — correct.
- `White` → `white` — correct.
- `American Indian or Alaska Native` → `native_american` — correct.
- `Multiracial` → `multiracial` — correct.
- `Unknown` → `race_unknown` — correct (canonical; FK resolves).
- `Female` → `female`; `Male` → `male` — correct.

**icd_revision** (derived from year, pure function): `icd9`↔`icd9`, `icd10`↔`icd10` — correct.

- **2a Completeness** — every distinct bronze race/sex label documented in the
  structure doc appears in `bronze_values_seen`; the `Selected … Total` /
  `County Summary` / `selected_years_total` rows are dropped-as-derived, not
  mapped. PASS.
- **2c Contract cross-check** — `gold_values_produced` equals the contract enum
  for all three columns exactly (demographic = 10 values, cause = 4, icd = 2). PASS.
- **2d Unmapped** — `unmapped_count = 0` on all three. PASS.
- **2e Asian/PI conflation (Risk 1)** — PASS. Bronze publishes the SPLIT pair
  (`grep` confirms a separate `Native Hawaiian or Other Pacific Islander` row per
  cause/year). Positive math-test evidence: at state grain the 7 race buckets sum
  EXACTLY to `All Races` for every cause — 2023 homicide 1058=1058, suicide
  1658=1658, legal_intervention 27=27, accidental_shooting 18=18; 2024 all four
  ratio=1.0000. Not conflated.
- **2f Mutual exclusivity (Risk 6)** — PASS, single convention. Gold demographic
  set has the split pair `asian`/`pacific_islander` and NO `asian_pacific_islander`
  rollup (confirmed absent); race and sex are separate axes each summing to `all`.

**Row-count reconciliation:**

| Quantity | Value | Check |
|---|---|---|
| total_bronze (county+race+sex, 12 files) | 22,272 | 4×(5152+288+128) ✓ |
| filtered_explicit | 1,068 | selected_years_total 696 + county_summary 124 + race_total 124 + sex_total 124 ✓ |
| dedup (triplicate state `all`) | 248 | 2 surplus × 31 yr × 4 causes ✓ |
| total_filtered | 1,316 | 1,068 + 248 ✓ |
| total_gold | 20,956 | 22,272 − 1,316; = parquet row count ✓ |
| per-year rows | 676 | 636 county (159×4) + 40 state (10×4); 0 years deviate ✓ |

Expansion factor 0.9713 is uniform across all 30 real years; 2024 shows 0.4856
only because `_record_bronze_accounting` lumps the year-less `selected_years_total`
rows under max_year — explained, not an anomaly. All 31 years (1994–2024) present.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| geography | — | CORRECTLY EXCLUDED (used only to route Georgia→state and drop County Summary; county name lives in the counties dim) |
| county_fips | county_fips | MAPPED (Georgia `13`→NULL state; `13xxx` counties preserved) |
| race / sex | demographic | MAPPED |
| age / ethnicity | demographic | DEFERRED to v2 — documented (module docstring + contract limitations: "state-grain age and ethnicity breakdowns are not yet served"); 8 files stay in bronze, checksummed & analyzed |
| year | year | MAPPED (cast Int32 after dropping total-year rows) |
| *(filename slug)* | cause_of_death | MAPPED |
| *(derived from year)* | icd_revision | MAPPED (methodological-break flag; bronze doc ETL #5 calls for versioning the break) |
| deaths | deaths | MAPPED (empty→0 true zero) |
| death_rate | death_rate_per_100k | MAPPED (renamed; sentinels→NULL) |
| age_adjusted_death_rate | age_adjusted_death_rate_per_100k | MAPPED |
| County Summary / Selected … Total / selected_years_total rows | — | CORRECTLY EXCLUDED (derived duplicates; equality-asserted then dropped) |

No fabricated gold columns. **Contract prose fidelity** — audited served text
(`purpose`/`usage`/`limitations`/`null_semantics` + each column description)
against the bronze doc for contradictions: year range (1994–2024), suppression
scheme (rate <5 deaths → NULL; deaths never suppressed; -2 no-denominator),
per-100k scale, split-race convention, ICD break at 1998/1999, race_unknown
always-zero, and every `not_in_gold` claim all AGREE with `bronze-data-structure.md`.
No contradictions.

## Value-Level Spot Checks

| Trace | Bronze (file:line quoted) | Expected | Gold | Verdict |
|---|---|---|---|---|
| **Global max deaths** | `suicide__county_year.csv:29` `Georgia,13,2021,1659,15.371019725864024,15.0994168` | state `all`, deaths=1659 | 2021 / NULL fips / all / suicide / 1659 / 15.37102 / 15.099417 | MATCH |
| **Global max death_rate** | `homicide__county_year.csv:4109` `Stewart,13259,2005,5,89.36550491510278,88.60543949999999` | 13259, deaths=5, rate=89.37 | 2005 / 13259 / all / homicide / 5 / 89.365505 / 88.605439 | MATCH (extreme-but-conceivable: 5 deaths in a small county) |
| **-5 sentinel** | `homicide__county_year.csv:4090` `Stephens,13257,2018,1,-5,-5` | deaths=1, rates→NULL | 2018 / 13257 / homicide / 1 / NULL / NULL | MATCH |
| **-2 sentinel** | `suicide__state_race_year.csv:167` `Georgia,Native Hawaiian or Other Pacific Islander,1999,1,-2,-2` | deaths=1, rates→NULL | 1999 / state / pacific_islander / suicide / 1 / NULL / NULL | MATCH |
| **Race partition** | `homicide__state_race_year.csv` 2023: White 208 + Black 825 + Asian 14 + AmInd 2 + NHOPI 0 + Multiracial 9 + Unknown 0 | = All Races 1058 | race sum 1058 = all 1058 | MATCH |
| **Sex partition** | `homicide__state_sex_year.csv` 2023: Male 865 + Female 193 | = All Sexes 1058 | sex sum 1058 = all 1058 | MATCH |
| **County→state** | `homicide__county_year.csv` 2023: 159 counties | = Georgia row 1058 | county sum 1058 = state 1058 | MATCH |

- **4c Sentinel year-attribution (Risk 3)** — N/A. The only year literals in
  transform.py are `ICD9_MAX_YEAR=1998` and the icd derivation; year comes
  directly from the bronze `year` column (the string-year `selected_years_total`
  is dropped, never re-attributed). `icd_revision` is a pure function of the
  row's own year — verified partition icd9=1994–1998, icd10=1999–2024, 0 mismatches.
- **4d Aggregate reconciliation (Risk 4)** — PASS. Aggregates come FROM bronze
  (Georgia row + County Summary are source-published; the transform never derives
  them by summing/averaging). Free cross-source reconciliation: county deaths sum
  EXACTLY to the state total for every (year, cause) — quality check
  `county_deaths_sum_to_state_total` passes and the 2023 homicide manual trace
  ties (159 counties → 1058 = state). No `.mean()` on any rate anywhere.
- **4e Dedup tie-break (Risk 5)** — N/A/PASS. Single one-shot export, no
  overlapping vintages. The only dedup is the triplicate statewide `all` row
  (county/race/sex files), guarded by `assert_no_natural_key_collisions` (identical
  metrics required before dedup) with the removed count asserted to equal the
  exact surplus; tie-break immaterial because survivors are identical by assertion.
- **4f Suppression semantics** — both sentinel types traced above (-5 and -2) →
  NULL rate with the 1–4 deaths count preserved. PASS.

## Validation Cross-Read

`_validation.json`: **20 pass / 0 fail / 0 warning**;
`contract_parquet_schema`, `contract_quality_sql` (16 checks), `grain_uniqueness`,
and `foreign_keys` (county_fips→counties all 159; demographic→demographics all 10)
all pass. **schema_hash** `5f4f9f11a6d02a12b211f3e02b0a72ae9f0880b2cd0c1f12e9b72a03ab2b63a0`.

- **§4b masking audit** — only masks are the two sentinel rate nulls
  (`null_sentinel_rates`). Manifest `masked_values` records
  death_rate_per_100k=6,104 and age_adjusted_death_rate_per_100k=6,104 with
  reason (sentinels `[-5,-2]`) + all 31 years; independently recomputed gold NULL
  counts = 6,104 each (exact). Documented via `null_meaning` on both rate columns
  and the column descriptions; enforceability guarded by the authored
  `*_non_negative` quality checks. PASS.
- **§15b coverage judgment** — the `quality` list is comprehensive: partition
  sums (county/race/sex → state), grid completeness (159 counties, 10 state rows),
  the ICD partition, both non-negativity guards, `rates_null_only_when_deaths_1_to_4`,
  and `zero_deaths_implies_zero_rates`. Every real cross-column invariant is
  covered; no obvious missing check. PASS.
- **v1 parity** — verbatim script output:
  ```
  DIFFERS from v1
    v1:  None
    now: 9420b064ecf1fd8e161ad8e16ce68dae72539108c4f419df89e0573f83ad9348
  ```
  `v1: None` because `docs/rebuild/v1-baseline.yaml` has zero `criminal_justice`
  entries — **no v1 baseline (topic is post-v1)**, not a divergence.

## Cross-Era Consistency

Single era (one scripted 2026-07-02 export; 5 layouts, not eras). No overlap
years. Cross-year NULL sweep: no column ~100% NULL in any year — rate NULL density
stays a smooth 26.0%–32.5% across all 31 years (suppression, expected), `deaths`
0% NULL everywhere. Year-over-year continuity: `deaths` mean climbs gradually
9.0→17.2 (1998→2021) with no >10x jumps and no cumulative-publication spike; rate
means track 2.0–4.9. icd9/icd10 boundary is clean at 1998/1999.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | Explicit `STANDARD_COLUMNS` select + `harmonize_columns`; rates cast STRICTLY (raises on non-numeric residue); deferred layouts skipped with a log line, never silently NULLed |
| Era/layout routing | PASS | Layout detected by column signature (not filename); unknown layout raises; deferred age/ethnicity return None |
| Filter logic logged+justified | PASS | Every derived-row drop recorded on the manifest with a reason and asserted equal to its canonical row before dropping |
| Normalization completeness | PASS | Demographic aliases hit all bronze labels; unmatched → hard fail; effective alias slice recorded |
| strict casts | PASS | deaths→Int64 fill_null(0) (true zero); rates→Float64 STRICT; year→Int32 after total-year drop |
| Dedup keys + tie-break | PASS | Collision guard asserts identical metrics; removed count asserted = exact triplicate surplus |
| Year extraction | PASS | Year from bronze column; icd_revision pure function of year, partition verified |
| §4b masking | PASS | Sentinel masks recorded + documented + range-guarded (see Validation Cross-Read) |

## Notes

- schema_hash: `5f4f9f11a6d02a12b211f3e02b0a72ae9f0880b2cd0c1f12e9b72a03ab2b63a0`;
  contract `version: 1.0.0`.
- Validation: 20 pass / 0 fail / 0 warning; 16 contract quality checks all pass.
- Manifest: read_loss 0 events (section absent = zero); masked_values 6,104 per
  rate column across 1994–2024.
- All 7 risk hypotheses ruled out with executed evidence (2 documented N/A:
  sentinel year-attribution, era-overlap dedup).
- Scope note (not a defect): state-grain age and ethnicity breakdowns are
  deliberately deferred to v2 (matching sibling `overdose_deaths`); the 8 files
  remain in bronze, checksummed and analyzed, and the contract limitations disclose
  the deferral.
