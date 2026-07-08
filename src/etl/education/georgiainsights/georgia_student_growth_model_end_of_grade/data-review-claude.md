# Data Review: georgia_student_growth_model_end_of_grade

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

All checks pass with zero required fixes and zero judgment items. Gold is **byte-identical with the v1 baseline** (`96276b0b…`), every categorical map entry is semantically correct, all 18 extreme-row and per-era ordinary traces match bronze exactly, the 34-row §4b empty-cohort `sgp_median` mask is precise (companion zeros preserved; the one genuine `Median SGP = 1` row survives), and the 790 charter campus promotions (272/324/194 in 2015/2016/2017) reproduce the 2018+ bronze convention exactly. The five statewide `sgp_median` values ≠ 50 were independently re-verified as source-published in the 2015/2016 bronze state files.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `grade_level` | 12 | 12 (all in map) | 0 | PASS |
| `subject` | 6 | 6 (all in map) | 0 | PASS |

**grade_level — full map review (every entry):**

| Bronze | Gold | Correct? |
|---|---|---|
| `4` / `5` / `6` / `7` / `8` (in-file GRADE column, 2015-2018 per-grade + 2016-2019/2023 state) | `04`/`05`/`06`/`07`/`08` | ✓ zero-padded canonical codes; only grades 4-8 exist (SGP requires a prior-year score) |
| `ALL` (state GRADE column 2016-2019) | `all` | ✓ published cross-grade aggregate |
| `ALLGRADES` (sheet-name token, AllGrades sheets without a Grade column) | `all` | ✓ same aggregate, sheet-name-derived |
| `GRADE4`-`GRADE8` (sheet-name tokens, 2019 + 2023 system/school per-grade sheets) | `04`-`08` | ✓ matches sheet content (verified in traces below) |

**subject — full map review (every entry):**

| Bronze | Gold | Correct? |
|---|---|---|
| `ELA` (flat-era prefix 2015-2017) | `english_language_arts` | ✓ |
| `ENGLISH LANGUAGE ARTS` (super-header 2018+) | `english_language_arts` | ✓ |
| `MATH` (flat-era prefix) | `mathematics` | ✓ |
| `MATHEMATICS` (super-header) | `mathematics` | ✓ |
| `SCIENCE` (flat-era prefix, 2015-2016 only) | `science` | ✓ |
| `SOCIAL STUDIES` (flat-era prefix, 2015-2016 only) | `social_studies` | ✓ |

Completeness (2a): every value the structure doc documents appears in `bronze_values_seen`; the super-header forms of Science/Social Studies correctly never appear (those subjects were dropped in 2017, before the two-row-pivot era). Contract cross-check (2c): `gold_values_produced` for both columns equals the contract `enum` exactly. Unmapped (2d): 0 for both.

Gold availability confirms the era story: 4 subjects in 2015-2016, ELA+Math only from 2017; `grade_level="all"` present 2015-2019 (7,828/7,876/3,950/3,980/3,994 rows), absent in 2023 — exactly as bronze publishes.

**2e Asian/Pacific Islander conflation**: N/A — this bronze has no demographic axis anywhere (every row is All Students); gold has no `demographic` column and no `pct_asian`-style columns.

**2f Demographic mutual exclusivity**: N/A — no demographic column.

**Row-count reconciliation:**

| Year | Bronze (long) | Gold | Filtered | Expansion | Parquet actual |
|---|---|---|---|---|---|
| 2015 | 28,560 | 28,560 | 0 | 1.0 | 23,920 + 4,616 + 24 ✓ |
| 2016 | 28,692 | 28,692 | 0 | 1.0 | 23,988 + 4,680 + 24 ✓ |
| 2017 | 14,396 | 14,396 | 0 | 1.0 | 12,012 + 2,372 + 12 ✓ |
| 2018 | 14,526 | 14,526 | 0 | 1.0 | 12,072 + 2,442 + 12 ✓ |
| 2019 | 14,594 | 14,594 | 0 | 1.0 | 12,134 + 2,448 + 12 ✓ |
| 2023 | 10,910 | 10,910 | 0 | 1.0 | 8,770 + 2,130 + 10 ✓ |
| **Total** | **111,678** | **111,678** | **0** | | **111,678** ✓ |

Per-detail-level parquet row counts equal the per-file manifest `bronze_rows` exactly (each (year, detail) is fed by exactly one workbook). Sanity anchors: 2015 state = 24 = 6 sheets × 1 row × 4 subjects; 2016 state = 24 = 1 sheet × 6 rows × 4 subjects; 2017-2019 state = 12 = 6 rows × 2 subjects; 2023 state = 10 = 5 grade rows × 2 subjects (no ALL row). Expansion factor 1.0 everywhere because the manifest records post-unpivot long rows.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `State` (2015 state files, literal "Georgia") | — | CORRECTLY EXCLUDED (constant; state rows get NULL geography) |
| `State` (2015 system/school files, system code) | `district_code` | MAPPED (detail-level-contextual rename verified in traces) |
| `System ID` (2016-2017 system) | `district_code` | MAPPED |
| `System Code` (2018+) | `district_code` | MAPPED |
| `KEY`/`Key` (2015-2017 school, 7-digit) | `district_code` + `school_code` (split DDDSSSS) | MAPPED (verified: `6742050` → `674`/`2050`) |
| `School Code` (2018+) | `school_code` | MAPPED (zfill(4) verified: `177` → `0177`) |
| `GRADE`/`Grade` | `grade_level` | MAPPED |
| Subject prefix / super-header | `subject` | MAPPED (unpivot) |
| `System Name`, `School Name` | — | CORRECTLY EXCLUDED (dimension attributes) |
| `RESAName_RPT` (2023) | — | CORRECTLY EXCLUDED (dimension attribute; districts dim carries RESA typing) |
| `N Tested` / `Number Tested` | `num_tested` | MAPPED |
| `N Received SGP` / `Number Received SGP` | `num_received_sgp` | MAPPED (§16 name, not `number_received_sgp`) |
| `% Received SGP` | `pct_received_sgp` | MAPPED (/100) |
| `Median SGP` | `sgp_median` | MAPPED (natural 1-99 scale preserved) |
| `% Proficient Learner and above/Above` | `pct_proficient_learner_or_above` | MAPPED (/100; `_or_above` per §16) |
| `% Developing Learner and above/Above` | `pct_developing_learner_or_above` | MAPPED (/100) |
| `% Typical or High Growth` | `pct_typical_or_high_growth` | MAPPED (/100) |
| `% Low Growth` / `% Typical Growth` / `% High Growth` (2023) | `pct_sgp_low_growth` / `pct_sgp_typical_growth` / `pct_sgp_high_growth` | MAPPED (/100; §16 names per structure-doc Correction 5) |
| Filename year | `year` | MAPPED |
| File detail level | parquet split (`schools`/`districts`/`states.parquet`) | MAPPED (domain convention; not a gold column) |
| Title banner row 0 / sheet tab strings | — | CORRECTLY EXCLUDED |

Every gold column traces back to bronze — no fabrication. `_rename_and_drop` raises on any unmapped header, so an unhandled bronze column cannot become a silent NULL metric.

## Value-Level Spot Checks

### Extreme-row traces (global max/min, every metric)

| Metric | Extreme | Bronze (file:sheet, entity, quoted value) | Gold | Verdict |
|---|---|---|---|---|
| `num_tested` max | 664,513 | 2019 State `EOG_AllGrades_2019_State` GRADE=ALL ELA: `Number Tested = 664513` | 664513 (year=2019 state, all, ELA) | MATCH |
| `num_tested` min | 0 (42 rows) | 2016 System `EOG_Grade8_2016_System` 708 Oconee / 785 Rome Science: `N Tested = 0` (whole-row zero block) | 0 | MATCH |
| `num_received_sgp` max | 624,665 | same 2019 state row: `Number Received SGP = 624665` | 624665 | MATCH |
| `num_received_sgp` min | 0 (34 rows) | same 2016 empty-cohort blocks: `N Received SGP = 0` | 0 | MATCH |
| `pct_received_sgp` max | 1.0 | 2015 System `EOG_Grade4_2015_System` 601 Appling Science/SocStud: `% Received SGP = 100` | 1.0 | MATCH |
| `pct_received_sgp` min | 0.0 | 2016 empty-cohort blocks: `% Received SGP = 0` (0 of 0 students — possible value, preserved per §4b) | 0.0 | MATCH |
| `sgp_median` max | 97.0 | 2016 School `EOG_Grade4_2016_School` KEY `6742050` (Ephesus Elementary, Heard): `ELA: Median SGP = 97` (N=15) | 97.0 at 674/2050 | MATCH |
| `sgp_median` min | 1.0 | 2016 System `EOG_Grade8_2016_System` 658 Forsyth Science: `Median SGP = 1` with `N Received SGP = 10` | 1.0 (NOT masked — cohort non-empty) | MATCH |
| `pct_proficient_learner_or_above` max | 1.0 | 2016 School `EOG_Grade8_2016_School` KEY `6580219` (i-Achieve Academy): `ELA: % Proficient... = 100` | 1.0 | MATCH |
| `pct_proficient_learner_or_above` min | 0.0 (395 rows) | 2015 School `EOG_Grade6_2015_School` KEY `6440291` (Salem Middle): `Social Studies: % Proficient... = 0` (`% Developing = 37`) | 0.0 | MATCH |
| `pct_developing_learner_or_above` max | 1.0 | 2015 System `EOG_Grade5_2015_System` 630 Clay: `Math: % Developing... = 100` | 1.0 | MATCH |
| `pct_typical_or_high_growth` max | 1.0 | 2015 System `EOG_Grade7_2015_System` 604 Baker: `Math: % Typical or High Growth = 100` | 1.0 | MATCH |
| `pct_sgp_high_growth` max | 0.907103825136612 | 2023 School `Grade6_School_2023` 647/0103 (Robert A. Cross Middle Magnet): `Mathematics % High Growth = 90.7103825136612`, `Median SGP = 94` | 0.907103825136612; sgp_median 94 (= 2023 max) | MATCH |
| `pct_sgp_high_growth` min | 0.0 | 2023 School `Grade5_School_2023` 611/1311: `ELA % High Growth = 0` (`Low 86.67 + Typical 13.33 = 100`) | 0.0 | MATCH |
| `pct_sgp_low_growth` max | 0.8947368421052632 | 2023 School+System Grade6, 752/0104 Webster County: `ELA % Low Growth = 89.47368421052632` (identical school & system rows — single-school district) | 0.8947368… on both detail levels | MATCH |
| `pct_sgp_low_growth` min | 0.0 | 2023 System `Grade5_System_2023` 7830616 (Genesis Innovation Academy for Girls): `Mathematics % Low Growth = 0` (`Typical 44.44 + High 55.56`) | 0.0 | MATCH |
| `pct_sgp_typical_growth` min | 0.037037… | 2023 School `Grade4_School_2023` 644/4059 (Kelley Lake Elementary): `Mathematics % Typical Growth = 3.7037037037037037` | 0.037037037037037035 | MATCH |

### Ordinary per-era traces (one entity, all columns)

Entity 601/0177 (Appling County Elementary), `grade_level=all` (grade 04 for 2023):

- **Era 1 (2015 School, KEY `6010177`)**: all 4 subjects × 7 metrics verified. ELA `356/343/96/43/22/60/59` → gold `356/343/0.96/43.0/0.22/0.60/0.59`; Math `359/349/97/31/21/60/47`; Science `359/354/99/58/21/62/71`; SocStud `358/353/99/66/22/67/74` — all MATCH.
- **Era 2 (2016 School, Key `6010177`)**: ELA `367/353/96/38/24/58/53` → gold matches exactly. MATCH.
- **Era 3 (2017 School, Key `6010177`)**: ELA `367/359/98/51/26/66/69`, Math `367/359/98/66/45/82/80` → gold matches both. MATCH.
- **Era 4 (2018 School, `601`/`177`)**: ELA `395/380/96/43/25/65/56`, Math `395/378/96/58/44/85/76` → gold matches (school_code zfilled to `0177`). MATCH.
- **Era 5 (2019 State, GRADE=ALL)**: ELA `664513/624665/94.003428/50/44.503534/76.036756/65.443878` → gold `664513/624665/0.94003428/50.0/0.44503534/0.76036756/0.65443878`; Math row also matches. MATCH.
- **Era 6 (2023 School Grade4, `601`/`0177`)**: ELA `164/45.5/39.02439…/30.48780…/30.48780…`, Math `165/52/29.09090…/34.54545…/36.36363…` → gold matches all ten cells on the 0-1 scale. MATCH.

### Sentinel year-attribution (Risk 3)

The only year-bearing parsing is the filename regex; the 2016 state workbook's sheet tab is mis-labeled `EOG_AllGrades_2015_State`. Trace: that file's Grade 7 ELA row reads `127512 / 118956 / Median 49`; gold year=2016 state grade 07 ELA is exactly `127512 / 118956 / 49.0`, while gold year=2015 (from the 2015 file's own Grade7 sheet: `127837 / 116746 / 50`) is distinct. Year attribution follows the filename, not the tab. MATCH.

### Aggregate feasibility screen (Risk 4 — aggregates come from bronze)

- State vs sum(district rows) per (year, grade, subject), count metrics: 94 cells each; `num_tested` ratios 0.99998–1.00000, `num_received_sgp` 0.99962–1.00000 — zero outside ±3%.
- District vs school rows (18,688 joined cells per metric): zero districts below their max school; zero below 0.98 × visible school sum. No impossibly-low aggregates.

### Dedup tie-break (Risk 5)

N/A — manifest `files_processed` shows each (year, detail_level) fed by exactly one workbook; no overlap years exist. Dedup is purely defensive and `assert_no_natural_key_collisions` runs before it.

### Suppression semantics (one trace per marker type)

| Marker | Bronze evidence | Gold | Verdict |
|---|---|---|---|
| `----` (2015-2017) | 2015 School AllGrades KEY `6110407`: `ELA: % Received SGP = '----'`, `Median SGP = '----'` (N Tested 7, N Received 4 clean) | 611/0407: pct_received_sgp NULL, sgp_median NULL; counts 7/4 intact | MATCH |
| `TFS` (2017) | 2017 School AllGrades Key `6220112`: `Math: % Proficient Learner and above = 'TFS'` | 622/0112 math: pct_proficient NULL (sgp_median also NULL — `----`-suppressed) | MATCH |
| `TFS` (2018) | 2018 School AllGrades 614/394: `ELA Median SGP = 'TFS'` | 614/0394: sgp_median NULL, pct_received_sgp NULL | MATCH |
| true null (2019) | no string marker exists (verified: zero `TFS`/`----` cells); bronze NULLs land directly | 2019 null counts (396 per pct column) match bronze block null counts | MATCH |
| `--` (2023) | 2023 School Grade4 611/0307: `ELA Median SGP = '--'` with `Number Received SGP = 2` | 611/0307 gr4 ELA: sgp_median NULL, pct_sgp_low_growth NULL; num_received_sgp = 2 | MATCH |

### Charter campus promotion (2015-2017)

Bronze 2015 School AllGrades carries 13 KEYs prefixed 782/783 (e.g. `7820110` Odyssey School, `7820120` Georgia Cyber Academy `ELA: N Tested = 5196, Median SGP = 39`). Gold school-level rows: district_code `7820110`/school `0110` and `7820120`/`0120` with `5196 / 39.0` — MATCH; zero school-level rows remain under bare `782`/`783` in any year. Promoted row counts (272/324/194 for 2015/2016/2017) equal the manifest `reclassified` ledger; 2018/2019/2023 school rows carry 7-digit codes natively from bronze (240/246/312). The 2015-2017 **system** files already publish per-campus 7-digit codes (`7820110`…, verified by direct read), so district-level rows needed no rewrite and gold's school rows now join them consistently. The single `799` "State Schools" umbrella district row per system sheet survives as district_code `799` (a valid districts-dim FK), with school-level 799-prefixed campuses keyed separately — matches structure-doc Correction 4.

## Validation Cross-Read

- `_validation.json`: **20 pass / 0 fail / 1 warning**, `passed: true`, timestamp fresh against the manifest. `contract_parquet_schema` (18 files), `contract_quality_sql` (17 checks), `grain_uniqueness`, `foreign_keys` (225 district keys, 1,945 school keys all resolve), and all geography-nulling checks pass.
- The single warning is `null_rate_spikes` listing the five 2023 era-break columns — fully explained by the Era 6 metric break (see Cross-Era Consistency).
- Contract `schema_hash`: `488ddb7e73308450b72a74a39ec44243f021f13fde8184702b4e6bfa41cda7a5`.

**§4b masking audit (5b)**: one `_null_*` helper (`_null_empty_cohort_sgp_median`). Manifest `masked_values` records column `sgp_median`, count 34, reason (bronze sentinel 0 on empty-cohort rows), years [2016, 2018] — verified in gold: exactly 34 rows have `num_received_sgp == 0` (31 in 2016, 3 in 2018 — matching the structure-doc Correction 1 split of 29 school + 2 system in 2016 and 3 school in 2018), all with `sgp_median` NULL; companion zero counts/percentages preserved; the genuine `Median SGP = 1` row (Forsyth 658, N=10) was correctly NOT masked. The contract `sgp_median` description documents the mask, and the `[1, 99]` `value_min`/`value_max` guard keeps it enforceable. PASS.

**§15b coverage judgment (5c)**: the four authored checks (`num_received_sgp_le_num_tested`, `pct_received_sgp_matches_counts` ±0.02, `proficient_le_developing_or_above`, `sgp_growth_bands_sum_to_one` ±0.02) cover this topic's real cross-column invariants. The one further candidate — "statewide `sgp_median` = 50" — is falsified by the source itself: bronze publishes five statewide medians ≠ 50, re-verified by direct read (2015 State Grade5 `Social Studies: Median SGP = 51`; 2016 State Grade7 `ELA = 49`, Grade4 `Science = 51`, Grade4 `Social Studies = 51`, Grade8 `Social Studies = 51`), so it is correctly NOT authored as a hard check. The era-disjointness of the two growth-metric families holds in gold (0 rows with both families non-null) and is documented in the contract. Coverage adequate. PASS.

**v1 parity (5d)** — verbatim:

```
MATCH — byte-identical with v1 gold
hash: 96276b0b1eb4b15ac7750963cff50337893afeaa29a7d6b1ed06231c887a3de6
```

## Cross-Era Consistency

- **Overlap years**: none — each (year, detail_level) comes from exactly one workbook.
- **Era-boundary continuity** (state level): `sum(num_tested)` 5.13M → 5.08M (2015→2016, 4 subjects), 2.58M → 2.60M → 2.61M (2017-2019, 2 subjects); the 2016→2017 halving is the documented subject drop (4 → 2), and the 2023 `num_tested = 0` is the Era 6 column removal. Mean state `sgp_median` 50.04/50.08/50.0/50.0/50.0/50.0; mean `pct_typical_or_high_growth` 0.64-0.66 across 2015-2019. No >10x jumps, no cumulative-publication signatures.
- **Cross-year NULL sweep**: flags exactly the eight documented era-break patterns — `num_tested`, `pct_received_sgp`, `pct_proficient_learner_or_above`, `pct_developing_learner_or_above`, `pct_typical_or_high_growth` 100% NULL only in 2023; `pct_sgp_low/typical/high_growth` 100% NULL only in 2015-2019. No column is NULL in all years; no unexplained era-localized NULL column (Risk 2 ruled out).
- **Scale consistency**: percent columns integer-grain through 2018, decimal-grain 2019+ (bronze precision change, both 0-100 → /100); 2015 caps at 0.99 for `pct_proficient` because that era rounds to integers — no scale break.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | `_rename_and_drop` raises on any header missing from `_BRONZE_HEADER_MAP`; only name/RESA dimension attributes dropped |
| Era routing correctness | PASS | Structural header-row probing (`_detect_file_shape`), never filename-based; unknown shapes raise; manifest era labels match the structure doc per file |
| Filter logic logged + justified | PASS | Only the defensive unparseable-grade filter; fired 0 times (`total_filtered = 0`); ledgered if it ever fires |
| Normalization map completeness | PASS | Full 18-file header inventory covered; manifest `unmapped_count = 0` on both categoricals |
| `strict=False` casts | PASS | Applied after era-specific `na_values`; all five suppression conventions verified to land as NULL; validator confirms no residual markers |
| Dedup keys + tie-break | PASS | Defensive only (no overlap years); `assert_no_natural_key_collisions` precedes dedup so divergent duplicates fail loudly |
| Year extraction | PASS | Filename regex; sheet tab never trusted — verified via the 2016 mis-labeled-tab trace |
| §4b mask (5b) | PASS | Recorded, documented, range-guarded, count-verified in gold (34) |

## Notes

- Contract `schema_hash`: `488ddb7e73308450b72a74a39ec44243f021f13fde8184702b4e6bfa41cda7a5`; validation 20 pass / 0 fail / 1 warning (the documented 2023 era-break NULL spikes).
- v1 parity: MATCH (`96276b0b1eb4b15ac7750963cff50337893afeaa29a7d6b1ed06231c887a3de6`).
- Shared module `_charter_district_promotion.py` consumed read-only — verified unmodified (`git diff HEAD` clean; last change is the committed Phase 4 batch 23 history).
- Minor prose nit (no data impact): the transform docstring and structure-doc Correction 2 say district-level **bare** 782/783 umbrella rows "are left as-is", but this bronze's 2015-2017 system files publish per-campus 7-digit codes directly (`7820110`…, plus `799` State Schools) — no bare 782/783 district rows exist in this topic, so the sentence is vacuous here (it describes the shared module's general safety property). Gold is correct and v1-identical either way.
- Read loss: none recorded — whole-sheet Excel reads cannot drop records at parse time; `masked_values` (34) and `reclassified` (790) are the only manifest event ledgers, both verified.
- AWS S3 not touched per task constraints (profile known broken); review conducted entirely against local bronze/gold.
