# Data Review: georgia_student_growth_model_end_of_course

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold data is accurate: **v1 parity MATCH (byte-identical, `9deafb8c…`)**, all 23,861 bronze rows land in gold with zero filtering, every value-level trace across all three eras MATCHes, the 9999-sentinel mask and 191 charter promotions are verified against bronze, and all five authored quality-check claims reproduce exactly in gold. The only findings are two LOW prose-only inaccuracies in shipped metadata (a wrong row-population figure in one contract quality-check description, and a "one stray NULL literal" claim that is actually 33 cells — handling is correct either way; the 2017 null counts reconcile to bronze exactly). The shared `_charter_district_promotion.py` module is unmodified (clean `git status`/`git diff`).

## Manifest Verification

### Categorical map summary

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| subject | 97 | 97 (all mapped; `seen-but-unmapped: []`) | 0 | PASS |

`gold_values_produced` (10) equals the contract `enum` (10) exactly. Gold subject counts per year: 2015 = 8, 2016 = 10, 2017–2019 = 6, 2023 = 2 — matches the structure doc's coverage narrative.

### Full map review (all 97 entries, grouped by rule)

Programmatic check: every `EOC_<STEM>_<YYYY>_<Level>` entry was re-derived from the stem table and compared — `stem-map mismatches: []` (0 of 84 sheet-name entries deviate).

| Bronze entries | → Gold value | Correct? |
|---|---|---|
| `EOC_9LIT_{2015–2019}_{State,System,School}` (11), "Ninth Grade Literature & Composition" | `9th_grade_literature_and_composition` | YES — §16 canonical |
| `EOC_AMLIT_*` (11), "American Literature & Composition" | `american_literature_and_composition` | YES |
| `EOC_CAL_*` (11), "Coordinate Algebra", "School/State/System - Coordinate Algebra" (3) | `coordinate_algebra` | YES — kept distinct from algebra_i (curriculum-era distinction, per domain CLAUDE) |
| `EOC_AGE_*` (11), "Analytic Geometry" | `analytic_geometry` | YES — kept distinct from geometry |
| `EOC_ALG_{2016–2019}_*` (8), "Algebra I", "School/State/System - Algebra I" (3) | `algebra_i` | YES |
| `EOC_GEO_{2016–2019}_*` (8), "Geometry" | `geometry` | YES |
| `EOC_BIO_{2015,2016}_*` (5), "Biology" | `biology` | YES — BIO only exists 2015–2016, matching doc |
| `EOC_PHY_{2015,2016}_*` (5), "Physical Science" | `physical_science` | YES |
| `EOC_USH_{2015,2016}_*` (5), "United States History" | `us_history` | YES — §16 canonical short form |
| `EOC_ECO_{2015,2016}_*` (5), "Economics", "Economics/Business/Free Enterprise" | `economics_business_free_enterprise` | YES — 2015 short label "Economics" correctly folded into the 2016 long form (structure doc consideration 15 / §16) |

Completeness (2a): every sheet name the structure doc lists per file appears in `bronze_values_seen` (8 sheets × 3 levels 2015; 10 × School/System 2016; 6 × School/System 2017–2019; combined-state Subject values 2016–2019; 6 level-label sheets 2023); ALG/GEO entries correctly absent for 2015, BIO/PHY/USH/ECO correctly absent after 2016. No documented value is missing from the manifest. Unmapped (2d): 0.

**2e Asian/PI conflation: N/A** — this topic has no `demographic` column anywhere in bronze (every row is All Students; structure doc consideration 10) and gold has no race columns. **2f mutual exclusivity: N/A** — same reason.

### Row-count reconciliation

| Year | Bronze | Filtered | Gold | Expansion | Verdict |
|---|---|---|---|---|---|
| 2015 | 5,797 | 0 | 5,797 | 1.0 | PASS |
| 2016 | 6,507 | 0 | 6,507 | 1.0 | PASS |
| 2017 | 3,586 | 0 | 3,586 | 1.0 | PASS |
| 2018 | 3,337 | 0 | 3,337 | 1.0 | PASS |
| 2019 | 3,540 | 0 | 3,540 | 1.0 | PASS |
| 2023 | 1,094 | 0 | 1,094 | 1.0 | PASS |

Actual parquet rows = 23,861 = manifest `total_gold` (3b PASS). Detail split: schools 17,837 / districts 5,986 / states 38 — equals the per-file manifest sums (e.g. school files 4,283+4,805+2,685+2,512+2,671+881 = 17,837). 18 parquet files (6 years × 3 levels), no empty files. 2019 district analytic_geometry = 63 rows — confirms the `EOC_AGE_2019_System` 119 blank rows + the orphan lone-`TFS` row (raw row 184, quoted below) were dropped as structural padding, not data. 2023 raw reads carry exactly one all-blank spacer row (`School - Algebra I`: 834 raw → 833 data, first row all-null = True).

## Column Coverage

| Bronze column | Gold column | Verdict |
|---|---|---|
| (filename year) | `year` | MAPPED — filename-driven, asserted against sheet-name year for stem layouts |
| Key (2015–2017 School) | `district_code` + `school_code` | MAPPED — `zfill(7)` → slice(0,3)/slice(3,4); the structure doc's original `[1:4]`/`[4:]` constant-leading-6 claim is WRONG and the Corrections entry is verified below |
| System Code | `district_code` | MAPPED (zfill 3; 7-digit charter campus codes preserved) |
| School Code (2018+, 2023) | `school_code` | MAPPED (zfill 4) |
| Subject / Content Area / (sheet name) | `subject` | MAPPED — redundant columns cross-checked against sheet name then dropped (raise on mismatch) |
| State (2015–2017 State) | — | CORRECTLY EXCLUDED (constant "Georgia") |
| System Name / School Name | — | CORRECTLY EXCLUDED (dimension attributes) |
| RESA (2023) | — | CORRECTLY EXCLUDED (district dimension attribute; bronze value even truncated, `CENTRAL SAVANNAH RIV`) |
| N Tested / Number Tested | `num_tested` | MAPPED |
| N Received SGP / Number Received SGP | `num_received_sgp` | MAPPED (§16 canonical name, supersedes doc's `n_received_sgp`) |
| % Received SGP | `pct_received_sgp` | MAPPED, /100 |
| Median SGP / SGP Median | `sgp_median` | MAPPED, natural 1–99 scale (not divided) |
| % Proficient/Developing Learner and above/Above | `pct_proficient_learner_or_above` / `pct_developing_learner_or_above` | MAPPED, /100, case drift handled by uppercase canonicalization |
| % Typical or High Growth | `pct_typical_or_high_growth` | MAPPED, /100, NOT merged with 2023 bands (correct) |
| % SGP Low/Typical/High Growth | `pct_sgp_low_growth` / `pct_sgp_typical_growth` / `pct_sgp_high_growth` | MAPPED, /100, 2023 only |
| (title row 0) | — | CORRECTLY EXCLUDED (header=1 read) |

No gold column lacks a bronze source (no fabrication). `_rename_and_drop` raises on unknown headers, so a header drift cannot silently drop a column.

## Value-Level Spot Checks

All traces use raw bronze reads (`header=1, dtype=str`); verdicts quote the bronze line.

### Extreme rows (4a)

| Trace | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| Global max `num_tested`/`num_received_sgp`: 2015 State CAL | `Georgia, Coordinate Algebra, 149583, 134577, 90, 50, 35, 71, 64` | year=2015 state row: 149583, 134577, 0.9, 50.0 | MATCH |
| Global max `sgp_median`=97: 2015 School PHY | `Key 7214562, Richmond County, Davidson Magnet School, 109, 106, 97, 97, 86, 100, 100` | 721/4562 physical_science: num_tested 109, num_received 106, sgp_median 97.0 | MATCH (Key split 721+4562 correct — Richmond County is 721) |
| Global min `sgp_median`=1: 2015 School AGE | `Key 6671010, Gwinnett County, Bay Creek Middle School, 17, 17, 100, 1, ----, 76, ----` | 667/1010 analytic_geometry: 17, 17, 1.0, sgp_median 1.0, pct_proficient NULL, pct_developing 0.76, pct_typical NULL | MATCH (also the `----` suppression trace) |
| Global max `pct_sgp_low_growth`=0.95: 2023 School ALG | `721, 0394, RICHMOND COUNTY, BELAIR K-8 SCHOOL, 20, 10, 95, 5, 0, CENTRAL SAVANNAH RIV` | 721/0394 algebra_i: num_received 20, sgp_median 10.0, bands 0.95/0.05/0.0 | MATCH |
| 2019 min `num_received_sgp`=9: 2019 System AMLIT | `731, Taliaferro County, 9, 9, TFS, TFS, TFS, TFS, TFS` | 731 district row: num_tested 9, num_received 9, all pct + sgp_median NULL | MATCH (counts published while percentages suppressed — the doc-corrected non-row-uniform 2019 suppression) |

### Ordinary traces (4b), one per era

| Era | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| Era 1 (2017 School 9LIT) | `Key 6090291, Ben Hill County, Fitzgerald High School, 244, 232, 95, 36, 33, 69, 52` | 609/0291: 244, 232, 0.95, 36.0, 0.33, 0.69, 0.52 | MATCH |
| Era 1 state_combined (2016 State, Subject column) | `Georgia, Geometry, 39321, 32986, 84, 50, 46, 75, 64` | 2016 state geometry: 39321, 32986, 0.84, 50.0, 0.46, 0.75, 0.64 | MATCH |
| Era 2 (2019 School 9LIT, float era) | `622, 3050, Bowdon High School, 92, 86, 93.478261, 40.5, 73.255814, 93.023256, 59.302326` | 622/3050: 92, 86, 0.934783, 40.5, 0.732558, 0.930233, 0.593023 | MATCH (full float precision /100) |
| Era 3 (2023 School Algebra I) | `761, 4058, FREDERICK DOUGLASS HIGH SCHOOL, 262, 49.5, 34.732824427, 31.679389313, 33.58778626, METRO` | 761/4058 algebra_i: num_received 262, sgp_median 49.5, bands 0.347328/0.316794/0.335878; num_tested + 2015-era metrics NULL | MATCH |

### Charter promotion trace (2015–2017 ledgered reclassifications)

Bronze `GSGM_EOC_2015_School.xls:EOC_9LIT_2015_School` row 525: `Key 7820108, State Charter Schools- Mountain Education Charter High School, 86, 28, 33, 59.5, 21, 82, 71`. Naive Key split gives district `782` + school `0108`; gold publishes **district_code `7820108`, school_code `0108`** with metrics 86/28/0.33/59.5/0.21/0.82/0.71 — the promoted campus code, byte-matching the bronze 2015 **System** file's own row for the same entity (`System Code 7820108`, identical metrics). Gold school-level 7-digit district codes: 2015 = 69, 2016 = 78, 2017 = 44 — exactly the manifest `reclassified` ledger; 2018/2019/2023 counts (56/54/20) come straight from bronze `System Code` (no promotion needed, none ledgered). Prefixes confined to 782/783/799. PASS.

### Suppression traces (4f), one per marker

| Marker | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| `----` (2015–2016 + 2017 residue) | Bay Creek 2015 AGE above: `----` in % Proficient and % Typical | both NULL, neighbors 0.76 / sgp_median 1.0 intact | MATCH |
| `TFS` (2017–2019) | Lanier Career Academy 2017 9LIT: `Key 6690105, 19, 9, TFS, TFS, TFS, TFS, TFS` | 669/0105: num_tested 19, num_received 9, all 5 metrics NULL | MATCH |
| `--` (2023) | Tybee Island 2023 ALG: `625, 0125, 10, --, --, --, --` | 625/0125: num_received 10, sgp_median + bands NULL | MATCH |
| `NULL` literal (2017 School) | Coffee County 2017 9LIT: `Key 6340195, 32, 24, 75, 41.5, NULL, 25, 54` | 634/0195: 32, 24, 0.75, 41.5, pct_proficient NULL, 0.25, 0.54 | MATCH |
| `9999` sentinel (§4b) | see Validation Cross-Read | 11 rows × 5 columns NULL, counts intact | MATCH |

**Marker-to-NULL reconciliation, 2017 (exhaustive, all 3 files, `keep_default_na=False`):** bronze non-numeric cells vs gold 2017 nulls — `pct_received_sgp` 651=651, `sgp_median` 651=651, `pct_proficient_learner_or_above` 697=697 (524 TFS + 5 `----` + 31 `NULL` school; 127 TFS + 10 `----` system), `pct_developing_learner_or_above` 652=652, `pct_typical_or_high_growth` 652=652, counts 0=0. **All MATCH** — no value was lost to `strict=False` beyond documented markers.

### 4c sentinel year-attribution: N/A-equivalent PASS

No year-bearing data strings exist (year comes only from the filename; no year column). The stem-layout sheets embed the year and the transform **asserts** sheet year == filename year (`_read_per_subject_stem`), so a mis-filed workbook would crash, not mis-attribute. Title-row years were spot-confirmed by the structure doc.

### 4d aggregate feasibility screen (aggregates come from bronze)

- State vs sum-of-district rows: `num_tested` 36 pairs, ratio range [0.9872, 1.0000]; `num_received_sgp` 38 pairs, [0.9977, 1.0000] — 0 outside tolerance, no swaps/garbling.
- District vs school rows: 5,966 joined (year, district, subject) groups; **0** districts below their max school (impossibly-low check); school-sum/district ratio median = p05 = p95 = max = 1.0000 — school rows sum to the published district row exactly. PASS.

### 4e dedup tie-break: N/A

Each (year, detail_level) slice is fed by exactly one bronze file; no overlap years exist. `assert_no_natural_key_collisions` runs before the defensive dedup, so a divergent duplicate would have failed the transform.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning**, `passed: true`, timestamp fresh vs manifest. `contract_parquet_schema`, `contract_quality_sql` (17 checks), `grain_uniqueness`, `foreign_keys` (district 210 keys, school 1,049 keys — all resolve) all pass. The single warning is the documented null-spike set: the five 2015–2019-only columns at 100% NULL in 2023 plus (by the same sweep, run here) the three band columns NULL 2015–2019 — all genuine bronze design gaps per the 2023 redesign, correctly described in the contract column descriptions and notes. Explained, not escalated.
- Contract `schema_hash`: `3f59c82cb62f615ccd7365b3b927db2707b1bfddca3b0106c90a7bc84fd7874e`.
- **§4b masking audit (5b): PASS.** One `_null_*` helper (`_null_9999_sentinel`). Manifest `masked_values`: 5 entries (pct_received_sgp, sgp_median, pct_proficient…, pct_developing…, pct_typical_or_high_growth) × 11 cells, year 2016, reason cites the file and the impossibility argument. Bronze verified: exactly 11 rows in `EOC_PHY_2016_System` hold `9999` in all five metric columns (Clay 630, Gordon 664, Taliaferro 731, Walton 747, Webster 752, Buford 764, Commerce 771, Jefferson 779, Coweta Charter 7830610, Social Circle 786, GA Academy for the Blind 7991894 — all tiny cohorts, num_tested ≤ 10, consistent with suppression); **0** `9999` in any count column; full-file scan total = 55 cells. Gold: all 11 rows have the 5 metrics NULL with both counts preserved. Contract documents the mask in the `sgp_median` and `pct_proficient_learner_or_above` descriptions; range guards (proportion [0,1], percentile [1,99]) keep the mask enforceable. v1 parity MATCH confirms the masked cells are byte-identical to v1 (which nulled the same cells via `na_values` but never ledgered them — the ledger is the improvement, the data is unchanged).
- **§15b coverage judgment (5c): PASS.** The five authored cross-column invariants cover the topic's real structure, and each was re-verified directly against gold: subset (0 violations / 22,191 both-counts rows), pct↔count reconciliation (n = 20,004, max dev 0.0050 ≤ 0.02 band), nested cumulatives (0 / 19,809), band partition (964 rows, max |sum−1| = 2.2e-16), era mutual exclusivity (0 co-occurrence rows). The non-authorable invariant (typical_or_high = typical + high) is correctly documented as impossible (families never co-occur). No missing obvious invariant.
- **v1 parity (5d)**, executed output verbatim:

```
MATCH — byte-identical with v1 gold
hash: 9deafb8c2a9753925c75c38adce94dc45b2f59ec958ecd8988de3cd15ef0a9de
```

## Cross-Era Consistency

- **Overlap years**: none (one file per year × level) — N/A.
- **Era boundaries**: 2017→2018 (Era 1→2) and 2019→2023 (Era 2→3). State-level means are smooth across all adjacent pairs: sgp_median 48.7/47.7/48.4/48.6/48.7 → 45.7 (2023); pct_typical_or_high_growth 0.642/0.641/0.650/0.655/0.651; num_tested state means decline gently (122.8k → 90.4k, tracking subject-count contraction). No >10x jumps, no cumulative-publication signature.
- **Cross-year NULL sweep (3c)**: flags only the documented era gaps — `num_tested`/`pct_received_sgp`/`pct_proficient…`/`pct_developing…`/`pct_typical_or_high_growth` 100% NULL in 2023 only; the three band columns 100% NULL 2015–2019 only. No column is NULL in every year. No rename-typo signature.
- **Key-format era shift verified**: the structure-doc Correction is confirmed against bronze — 2015–2017 School `Key` prefixes span 601–799 plus 891 (84–85 of ~184 prefixes do NOT start with 6; `6010103`, `8915001`, `7820108` all present), so the original "constant leading-6, `[1:4]`/`[4:]`" parse would have produced garbage districts (e.g. `010`). The transform's district(3)+school(4) split is correct, and the same entities' 2018–2019 `System Code`/`School Code` values match the split.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — `_rename_and_drop` raises on any header not in `_HEADER_MAP` |
| Era routing correctness | — | PASS — structural sheet-name layout detection; stem-layout year+level asserted against filename |
| Filter logic logged + justified | — | PASS — only fully-blank spacer rows dropped (logged); defensive NULL-subject filter logged; orphan lone-TFS row reduces to blank after marker nulling (verified: 1 non-blank among 120 null-System-Code tail rows, content = lone `TFS` in % Received SGP) |
| Normalization map completeness | — | PASS — both subject maps raise on unmapped labels; manifest unmapped = 0 |
| `strict=False` casts | — | PASS — 2017 exhaustive marker-to-NULL reconciliation matches exactly on every column; no undocumented residue consumed |
| Dedup keys + tie-break | — | PASS — collision guard precedes purely-defensive dedup; no overlap years |
| Year extraction | — | PASS — filename regex, both patterns carry exactly one year token; belt-and-suspenders sheet assertion |
| §4b mask (5b) | — | PASS — ledgered, documented, range-guarded, bronze-verified (see Validation Cross-Read) |

## Required Fixes

### Fix 1: Contract subset-check description cites the wrong verified-row population (20,004 vs 22,191)
- **Severity**: LOW
- **Issue**: The `num_received_sgp_le_num_tested` quality-check description claims "verified 0 violations across all 20,004 bronze rows publishing both counts". The actual both-counts population is **22,191** rows; 20,004 is the population of the *other* check (`pct_received_sgp_matches_counts`, where the rate is also present). Data is unaffected — 0 violations hold across all 22,191 rows (re-verified in gold this review).
- **Evidence**: Executed against gold: `rows with both counts: 22191; subset violations: 0` vs `pct vs count: n = 20004, max dev = 0.0050…`. Decomposition: 19,227 rows (2015–2018, counts never suppressed) + 2,964 (2019 rows with num_received_sgp published) = 22,191; subtracting rows whose pct_received_sgp is suppressed (336+773+651+426+1) = 20,004.
- **Location**: `transform.py` `main()` → `write_data_dictionary(quality_checks=[...])`, the `num_received_sgp_le_num_tested` entry's `description`.
- **Suggested fix**: Change "all 20,004 bronze rows publishing both counts" to "all 22,191 bronze rows publishing both counts" (or drop the figure). Re-run the transform to re-emit the contract; parquet bytes are untouched so v1 parity stays MATCH.

### Fix 2: "One stray NULL literal" is actually 33 NULL-literal cells across 3 columns
- **Severity**: LOW
- **Issue**: The transform docstring ("one stray ``NULL`` literal (2017 School)"), the contract notes ("one stray 'NULL' literal in 2017 School"), and the original bronze-doc suppression table ("plus one literal `NULL` string … in % Proficient Learner and above") all undercount. Raw bronze (`keep_default_na=False`) shows **33** `NULL` literals in `GSGM_EOC_2017_School_Level.xlsx`: 31 in `% Proficient Learner and above` (sheets 9LIT 2, AMLIT 7, CAL 5, AGE 4, ALG 13), 1 in `% Developing Learner and above` (AMLIT, Key 7991893), 1 in `% Typical or High Growth` (ALG, Key 7260107). Gold is unaffected — all 33 land as NULL (pandas default NA plus the explicit `na_values` both cover `NULL`), and the 2017 null reconciliation (e.g. % Proficient: 524 TFS + 5 `----` + 31 NULL + 137 system = 697 = gold null count) proves it.
- **Evidence**: `NULL literals in 2017 School: [('EOC_9LIT_2017_School', '% Proficient Learner and above', 2, ['6340195', '6350112']), ('EOC_AMLIT_2017_School', '% Proficient Learner and above', 7, …), …, ('EOC_ALG_2017_School', '% Typical or High Growth', 1, ['7260107'])]`; gold trace of Key 6340195 shows the cell NULL with neighbors intact.
- **Location**: `transform.py` module docstring (suppression bullet) and the fourth `notes=` entry in `write_data_dictionary`; optionally the bronze-data-structure.md Corrections section (the 8-item amendment did not catch this original-doc undercount).
- **Suggested fix**: Reword to "33 stray `NULL` literals in the 2017 School file (31 in % Proficient Learner and above, 1 each in % Developing Learner and above and % Typical or High Growth)". Prose-only; no data change, parity unaffected.

## Notes

- `schema_hash`: `3f59c82cb62f615ccd7365b3b927db2707b1bfddca3b0106c90a7bc84fd7874e`; validation 20 pass / 0 fail / 1 warning (documented 2023 null spike); v1 parity **MATCH** (`9deafb8c2a9753925c75c38adce94dc45b2f59ec958ecd8988de3cd15ef0a9de`).
- Both Required Fixes are metadata-prose corrections; neither touches gold parquet. Re-running the transform after fixing them must keep parity MATCH (deterministic writes).
- Shared module check: `src/etl/education/georgiainsights/_charter_district_promotion.py` has no working-tree modifications (consumed READ-ONLY as required).
- Read-loss ledger is empty by construction (whole-sheet Excel reads); manifest carries `masked_values` (5 × 11) and `reclassified` (69/78/44) instead — both verified.
- The 2018/2019/2023 school-level 7-digit charter district codes (56/54/20 rows) come directly from bronze `System Code` and are intentionally NOT in the promotion ledger (only 2015–2017 Key-derived rows needed promotion) — consistent with the structure-doc Correction that system-level files publish campus codes in every year.
- Bronze checksums in the structure doc were generated 2026-05-22; no unanalyzed files (18/18 listed and processed).
