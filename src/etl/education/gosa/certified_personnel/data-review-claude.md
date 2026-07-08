# Data Review: certified_personnel

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is **byte-identical with the v1 approved baseline (parity MATCH)** and every
value-level trace (3 extreme rows + five full 81-row entity grids = 408 traced
cells across both eras and all three detail levels) reproduced bronze exactly.
All transform-agent claims verified: 1.00x bronze→gold row parity in all 14
years, zero read loss, zero masks, §5b math test confirmed (race-sum/gender-sum
ratios 0.9999–1.0004 in both directions), the 2016-17 certified_personnel family
anomaly preserved with exactly the documented values, and all 27+7+3 categorical
recodings semantically correct. One LOW documentation-only Required Fix: the
transform docstring (and the structure doc it cites) claims "3-character school
codes occur in every file" — raw bronze bytes show INSTN_NUMBER is uniformly
4-character in all 14 files; gold is unaffected (zfill(4) is a no-op). One
judgment item on a school-vs-district aggregation caveat for `personnel/part_time`.

## Manifest Verification

Preconditions: FRESH (transform mtime 18:41:39 < manifest 18:42:02 ≤ validation
18:42:02), `passed: true` (21 pass / 0 fail / 0 warning), `read_loss` section
absent (= zero events; independently re-verified: parsed == raw for all 14 files).

### Categorical map summary

| Column | Map entries | Bronze seen | Unmapped | Contract enum match | Status |
|---|---|---|---|---|---|
| `employee_type` | 3 | 3 (all in structure doc) | 0 | yes (3) | PASS |
| `measure_family` | 7 | 7 (all in structure doc) | 0 | yes (7) | PASS |
| `measure_label` | 27 | 27 (all in structure doc) | 0 | yes (27) | PASS |

No documented bronze value went unseen; no seen value is outside the maps.
The `replace_strict(..., default="99999999")` pattern routes any future new
bronze value into a manifest `unmapped_count` failure rather than a passthrough.

### Full map review (every entry)

**employee_type** — `Administrators`→`administrators` ✓, `PK-12 Teachers`→
`pk_12_teachers` ✓, `Support Personnel`→`support_personnel` ✓.

**measure_family** — `Certificate Level`→`certificate_level` ✓,
`Certified Personnel`→`certified_personnel` ✓, `Gender`→`gender` ✓,
`Personnel`→`personnel` ✓, `Positions`→`positions` ✓,
`Race/Ethnicity`→`race_ethnicity` ✓, `Years Experience`→`years_experience` ✓.

**measure_label** (27/27):

| Bronze | Gold | Verdict |
|---|---|---|
| `4 Yr Bachelor's` | `4_yr_bachelors` | ✓ |
| `5 Yr Master's` | `5_yr_masters` | ✓ |
| `6 Yr Specialist's` | `6_yr_specialists` | ✓ |
| `7 Yr Doctoral` | `7_yr_doctoral` | ✓ |
| `Other *` | `other` | ✓ — certificate-level-only label; gold has exactly 27 distinct (family,label) pairs and `other` pairs only with `certificate_level` (containment quality check enforces) |
| `Professional` | `professional` | ✓ |
| `Provisional` | `provisional` | ✓ |
| `Female` / `Male` | `female` / `male` | ✓ |
| `Full-time` / `Part-time` | `full_time` / `part_time` | ✓ |
| `Number` | `number` | ✓ — FTE-style position count |
| `Average Annual Salary` | `average_annual_salary` | ✓ |
| `Average Daily Salary` | `average_daily_salary` | ✓ |
| `Average Contract Days` | `average_contract_days` | ✓ |
| `Asian` | `asian_pacific_islander` | ✓ — §5b combined bucket; see math test below |
| `Black` / `Hispanic` / `Multiracial` / `Native American` / `White` | snake_case | ✓ |
| `< 1` | `less_than_1` | ✓ |
| `1-10` / `11-20` / `21-30` | `1_to_10` / `11_to_20` / `21_to_30` | ✓ |
| `> 30` | `greater_than_30` | ✓ |
| `Average` | `average` | ✓ — mean years of experience (a statistic, not a band) |

**2e Asian/Pacific Islander (Risk 1): PASS — combined convention, positively
evidenced.** No demographic column exists (staff race is a measure family), so
the structural + math variant applies:

- `grep -riE 'pacific|hawaii|nhpi'` over all 14 bronze CSVs and the structure
  doc → `NO_NHPI_LABEL_IN_ANY_BRONZE_CSV` / `NO_NHPI_IN_STRUCTURE_DOC`.
- Math test executed on gold state rows, all 14 years × 3 employee types:
  race-bucket sum vs gender-bucket sum (same certified-personnel population).
  Output: `ratio range: 0.9999001198561726 - 1.0003760340937577`; worst
  deviation 0.038% (`2021 support_personnel race_sum=15962.0
  gender_sum=15956.0 ratio=1.000376`); 2024 teachers
  `race_sum=123877.0 gender_sum=123848.0 ratio=1.000234` (matches the
  docstring's quoted figures exactly). Residuals in BOTH directions —
  inconsistent with a dropped ~0.1-0.2% NHPI population, consistent with the
  pre-1997 OMB combined bucket. certified_personnel is also on §5b's
  known-combined list.

**2f Mutual exclusivity (Risk 6): PASS — single convention.** Gold publishes
only `asian_pacific_islander`; no `asian` or `pacific_islander` label exists in
any era (bronze publishes 6 race buckets only).

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Factor |
|---|---|---|---|---|
| 2011 | 220,347 | 220,347 | 0 | 1.00 |
| 2012 | 220,725 | 220,725 | 0 | 1.00 |
| 2013 | 217,566 | 217,566 | 0 | 1.00 |
| 2014 | 218,160 | 218,160 | 0 | 1.00 |
| 2015 | 220,833 | 220,833 | 0 | 1.00 |
| 2016 | 221,130 | 221,130 | 0 | 1.00 |
| 2017 | 222,021 | 222,021 | 0 | 1.00 |
| 2018 | 222,966 | 222,966 | 0 | 1.00 |
| 2019 | 223,425 | 223,425 | 0 | 1.00 |
| 2020 | 224,127 | 224,127 | 0 | 1.00 |
| 2021 | 225,315 | 225,315 | 0 | 1.00 |
| 2022 | 226,638 | 226,638 | 0 | 1.00 |
| 2023 | 227,583 | 227,583 | 0 | 1.00 |
| 2024 | 229,797 | 229,797 | 0 | 1.00 |

Total 3,120,633 = manifest `total_gold` = actual parquet row count (re-summed:
3,120,633). Era 2 per-file counts match the structure doc's table exactly. The
"zero drops/masks/dedup" claim is verified: `total_filtered: 0`, no
`read_loss`/`masked_values`/`reclassified` sections, and bronze = gold per year.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `#RPT_NAME` (Era 1) | — | CORRECTLY EXCLUDED — asserted constant `CERTIFIED_PERSONNEL` (transform raises on any other value) |
| `LONG_SCHOOL_YEAR` | `year` | MAPPED — ending year via `parse_school_year` |
| `SCHOOL_DSTRCT_CD` | `district_code` | MAPPED — `ALL`→NULL before zfill(3); 7-digit charters pass through |
| `SCHOOL_DSTRCT_NM` | — | CORRECTLY EXCLUDED — districts dimension attribute |
| `INSTN_NUMBER` | `school_code` | MAPPED — `ALL`→NULL before zfill(4) |
| `INSTN_NAME` | — | CORRECTLY EXCLUDED — schools dimension attribute |
| `GRADES_SERVED_DESC` (Era 1) | — | CORRECTLY EXCLUDED — school metadata, belongs in schools dimension |
| `DATA_CATEGORY` | `measure_family` | MAPPED |
| `DATA_SUB_CATEGORY` | `measure_label` | MAPPED |
| `EMPLOYEE_TYPE` | `employee_type` | MAPPED |
| `MEASURE` | `measure_value` | MAPPED — Float64, `strict=False` (defensive; zero non-numeric values exist) |

Every gold column traces to bronze (no fabrication). The structure doc's
"alternative" 81-column pivot was correctly declined in favor of the bronze long
grain (matches v1).

## Value-Level Spot Checks

**Extreme traces (4a):**

1. **Global max** — bronze `certified_personnel_2017.csv:178127`:
   `"2016-17","731","Taliaferro County","0102","Taliaferro County School","Positions","Average Annual Salary","Administrators",250831.94`
   → gold `(2017, 731, 0102, administrators, positions, average_annual_salary, 250831.94)` — **MATCH**
   (also confirms the $250,831.94 manifest max and the salaries-uncapped
   decision: a small-district administrator average, conceivable).
2. **2024 max** — bronze `certified_personnel_2024.csv:73912`:
   `"CERTIFIED_PERSONNEL","2023-24","644","DeKalb County","8018","Sam Moss Service Center Facility",,"Positions","Average Annual Salary","Administrators","249599"`
   → gold `(2024, 644, 8018, administrators, positions, average_annual_salary, 249599.0)` — **MATCH**.
3. **Global min (0.0)** — bronze `certified_personnel_2024.csv:226095`:
   `"CERTIFIED_PERSONNEL","2023-24","785","Rome City","0275","East Central Elementary School",...,"Gender","Male","Administrators","0"`
   → gold `(2024, 785, 0275, administrators, gender, male, 0.0)` — **MATCH**
   (zeros are real published values; no suppression in this source).

**Ordinary full-grid traces (4b)** — for each entity, all 81 bronze rows
(27 labels × 3 employee types) recoded through the maps and joined against gold;
`mismatches=0` and exactly 81 rows on both sides in every case:

| Trace | Era | Result |
|---|---|---|
| School 644/5067 (Southwest DeKalb High), 2015 | 2 | 81/81 ALL MATCH |
| School 741/0189 (Long Cane Elementary), 2024 | 1 | 81/81 ALL MATCH |
| District 644 aggregate (bronze `INSTN_NUMBER='ALL'`), 2015 | 2 | 81/81 ALL MATCH — sentinel→NULL `school_code` |
| State aggregate (bronze both `'ALL'`), 2015 | 2 | 81/81 ALL MATCH — NULL/NULL geography |
| State aggregate, 2023 | 1 | 81/81 ALL MATCH |

**4c Year attribution: PASS.** `LONG_SCHOOL_YEAR` is the authoritative source,
asserted single-valued per file; the global-max trace shows `"2016-17"` landing
in gold `year=2017` (file `certified_personnel_2017.csv`). Filename year ==
column-derived year for all 14 files (manifest `files_processed`). The
`ALL`→NULL translation runs BEFORE zfill (transform lines 392–399), so the
`"0ALL"` trap is avoided — confirmed by zero non-NULL sentinel artifacts and the
passing `id_formatting` / `geography_nulling` checks.

**4d Aggregate feasibility screen (aggregates COME FROM BRONZE — not derived):**

- *State vs district-sum*, all 924 (year, employee_type, count-label) cells:
  ratio range 0.8421–1.0541; only 2 cells outside [0.97, 1.05], both tiny counts
  (`2018 support_personnel certificate_level/other: state 19 vs district-sum 16`;
  `2014 administrators certified_personnel/provisional: state 37 vs 39`) —
  small-count dedup-at-higher-level noise, conceivable.
- *District ≥ max single school*: 1,811 of 190,300 cells violate — **100%
  confined to `personnel/part_time`**, present every year (114–146/year), small
  magnitudes (p95 district value 9). Extreme example: 2018 district 721
  support_personnel part_time district=1 vs school_sum=128. This is the
  multi-school itinerant-staff pattern: a person serving several schools is
  part-time *at each school* but counted once (typically full-time) at the
  district level. Conceivable source semantics, uniform across all 14 years,
  and provably bronze-published (zero transform drops; v1 parity MATCH) — not a
  transform defect. → routed to NEEDS_JUDGMENT (contract caveat).
- *2016-17 anomaly verified*: professional pk_12_teachers state/district-sum/
  school-sum = 109,979 / 110,182 / 112,384 (2016) → **2,689 / 2,690 / 2,748
  (2017)** → 111,745 / 112,071 / 114,187 (2018). Internally consistent at all
  levels in 2017; all other families normal that year (e.g. gender/female
  teachers 90,802 → 92,194 → 93,011). §4b preserve+document is the right call.

**4e Dedup tie-break: N/A** — 14 files cover 14 disjoint school years (manifest
`files_processed`); no overlap years exist. Dedup removed 0 rows
(`total_filtered: 0`).

**4f Suppression: N/A** — no suppression markers in any year (verified by the
reader: parsed == raw, and gold `measure_value` has 0 NULLs in all 3,120,633
rows). `suppressed_to_null: false` correctly recorded in the contract.

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning**, including
  `contract_parquet_schema` (42 files), `contract_quality_sql` (all 11),
  `grain_uniqueness`, `foreign_keys` (242 district keys, 3,328 school keys all
  resolve), and 3× `geography_nulling`.
- `schema_hash`: `58b8da2cd1d4898b621e2e8405a632a1ff9897bd69f4c339ba4aa202b0ebe26b`.
- **§4b masking audit: PASS (none).** No `_null_*` helpers in transform.py (the
  only `_null_` grep hits are `check_null_rate_spikes`); no `masked_values`
  manifest section — consistent. The two extreme-but-conceivable findings
  (2016-17 family depression; $0 salary averages at small cells) are preserved
  and documented in the contract `measure_value` description, `limitations`,
  and README notes.
- **§15b coverage judgment: adequate.** 7 authored checks (family↔label
  containment over the 27 pairs; non-negativity; 22-label integrality;
  experience-average [0,60]; contract-days [0,366]; 81 state rows/year;
  complete 27-label grid per cell) + 4 auto-derived = 11. The per-label range
  checks are a sound compensation for the sanctioned unit-less `measure_value`
  exemption — they make ranges enforceable despite no `unit` marker. Candidates
  considered and reasonably not authored: race-sum ≈ gender-sum tolerance check
  (residual noise up to 0.04% in both directions makes any tolerance arbitrary;
  the convention is documented instead) and district ≥ max-school (provably
  violated in bronze by the part_time semantics — unauthorable).
- **v1 parity** (executed output, verbatim):

  ```
  MATCH — byte-identical with v1 gold
  ```

## Cross-Era Consistency

- **Overlap years**: none (Era 1 = 2023–2024, Era 2 = 2011–2022, disjoint).
- **Era boundary (2022→2023)**: no discontinuity — state-level count-family
  sums and positions/years-experience values continuous; the only >2x YoY jump
  anywhere in 14 years is the documented 2016-17 `certified_personnel` family
  (both edges 2016→2017 and 2017→2018, all three employee types), entirely
  inside Era 2.
- **Cross-year NULL sweep (Risk 2)**: zero FLAG/INVESTIGATE columns; every
  column populated in every year; `measure_value` has 0 NULLs in all years.
- **Scale consistency (3d)**: per-(label, employee_type) state-level values
  show no >1.5x shifts for salary/days/experience labels in any adjacent year
  pair — no cumulative-publication or scale-flip signature.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | none | PASS — Era 1 extras: `#RPT_NAME` asserted constant (raises on change), `GRADES_SERVED_DESC` dimension metadata; both documented |
| Era routing | none | PASS — `detect_era_by_columns`, most-specific-first signatures; manifest shows 12× era_2, 2× era_1 as expected |
| Filter logic | none | PASS — no filters; dedup removals would be recorded via `record_filtered` (0 occurred) |
| Normalization map completeness | none | PASS — 3+7+27 all seen, `unmapped_count` 0, sentinel default guards future values |
| `strict=False` casts | none | PASS — only on `MEASURE`, purely defensive (0 NULLs produced) |
| Dedup keys + tie-break | none | PASS — collision guard before dedup; explicit `sort_col="measure_value"`; purely defensive (keys unique in bronze) |
| Year extraction | none | PASS — `LONG_SCHOOL_YEAR` authoritative, single-value assertion, filename cross-check warns |
| §5b mapping (Risk 1/7) | none | PASS — math test + structural test both confirm combined bucket |
| Docstring provenance claim | LOW | FLAG — see Fix 1 (documentation only; gold unaffected) |

## Required Fixes

### Fix 1: Correct the false "3-character school codes" claim in the transform docstring and structure doc
- **Severity**: LOW
- **Issue**: The transform docstring ("Structure-doc corrections" item 3: "`INSTN_NUMBER` is not uniformly 4-digit: 3-character school codes occur in every file and require zfill(4)") and bronze-data-structure.md ("3-character values occur in every file (verified: distinct lengths {3, 4} in all 14 files)", with a "*Corrected 2026-06-11*" note) assert a verified fact that does not reproduce. This is documentation-only — **no gold value is wrong** — but it is a false provenance claim future maintainers and reviews would rely on.
- **Evidence**: Executed against the raw bronze bytes with the stdlib `csv` module AND via `read_bronze_file(..., infer_schema_length=0)` (the transform's own read path): `INSTN_NUMBER` field lengths are `[4]` (plus the `ALL` sentinel) in **all 14 files**; e.g. `certified_personnel_2011.csv INSTN_NUMBER: [4]` … `certified_personnel_2024.csv INSTN_NUMBER: [4]`. The likely origin of the claim is an int-typed read during doc authoring (`"0100"` → `100` → 3 chars). District codes DO reproduce as documented (`{3}` in 2011, `{3,7}` in 2012–2024).
- **Location**: module docstring of `src/etl/education/gosa/certified_personnel/transform.py` (correction item 3 and the zfill comment at the `school_code` select, line ~396); `data/bronze/education/gosa/certified_personnel/bronze-data-structure.md` ("Institution number format" bullet and the Gold Schema Classification row for INSTN_NUMBER).
- **Suggested fix**: Amend both to state that `INSTN_NUMBER` is uniformly 4-character in all 14 files when read as strings, and that `zfill(4)` is retained as a defensive no-op (it also guards any future short code). No transform logic change; a re-run will keep gold byte-identical (v1 parity MATCH).

## NEEDS_JUDGMENT

### Judgment Call 1: Contract caveat for per-assignment school-level counting (`personnel/part_time` exceeds district headcounts)
- **Severity if confirmed**: LOW
- **Suspicion**: School-level rows count staff per assignment, so a person serving multiple schools appears at each school (and can be part-time at each school while full-time / counted once at district level). Consumers summing school rows to rebuild district figures will overstate headcounts, and `part_time` flips meaning across detail levels. The contract `limitations` warns against cross-pair aggregation but not against cross-level summation of count labels.
- **Evidence available**: 1,811 of 190,300 (year, district, employee_type, family, label) cells have district value < max single-school value — **all 1,811 are `personnel/part_time`**, steady at 114–146 per year across all 14 years; extreme case 2018 district 721 support_personnel: district part_time=1 vs school sum=128, max single school=4. Overall school-sum/district ratio is p50=1.000 but p99=3.667 for these cells. Bronze-published (zero transform drops; v1 parity MATCH), so this is source semantics, not a pipeline defect.
- **Why uncertain**: The multi-school/FTE-reclassification explanation is strongly consistent with the pattern (confined to one label, both-direction state-vs-district residuals elsewhere ≤5%) but is not documented by GOSA, so I cannot *prove* the level-dependent classification semantics; and v1 shipped without this caveat, so adding prose changes the contract text (not the data).
- **Location**: `limitations=` / `notes=` in `_emit_contract_and_readme()`, `src/etl/education/gosa/certified_personnel/transform.py`.
- **If confirmed, suggested fix**: Add one sentence to the contract `limitations` and README notes: school-level headcounts are per-assignment (staff serving multiple schools appear at each), so school rows must not be summed to reconstruct district/state headcounts — use the published district/state rows; `personnel/part_time` in particular reflects the entity-level classification. Documentation-only; no gold change, parity preserved.

## Notes

- `schema_hash`: `58b8da2cd1d4898b621e2e8405a632a1ff9897bd69f4c339ba4aa202b0ebe26b`; validation 21 pass / 0 fail / 0 warning; 42 parquet files (14 years × 3 detail levels); grain `(year, district_code, school_code, employee_type, measure_family, measure_label)` unique.
- v1 parity: **MATCH — byte-identical with v1 gold** (`compute_gold_sha256` vs `docs/rebuild/v1-baseline.yaml`).
- The unit-less `measure_value` exemption is sanctioned and well-compensated: 5 per-label range/integrality quality checks + 2 structural-grid checks are all enforced via contract quality SQL (validator check 17).
- No `demographic` column is correct: gender/race rows describe STAFF as measure families; they intentionally do not join the demographics dimension, and the §5b combined-bucket convention is documented in the contract `measure_label` description.
- Bronze freshness gate passed 14/14 upstream; bronze CSV checksums in the structure doc dated 2026-05-22.
