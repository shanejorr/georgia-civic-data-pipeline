# financial_efficiency_star_rating — Bronze Data Structure

## Overview

This bronze directory **consolidates two formerly separate GOSA FESR download
families** into one multi-level topic:

- **District family** (`..._fesr_district_{YYYY}`): 9 files, 2016-2024, one row
  per district (180 traditional Georgia school systems, codes 601-793). Detail
  level **district** in gold (`school_code` NULL).
- **School family** (`..._fesr_school_{YYYY}`): 8 files, 2017-2024, one row per
  school. Detail level **school** in gold (both geography keys populated).

The two families are distinct GOSA downloads with overlapping metric vocabulary
(per-pupil expenditure inputs, CCRPI Single Score, FESR star rating). They are
kept distinguishable on disk by the `_fesr_district_` / `_fesr_school_` infix in
each filename; the merged transform routes each file to its family handler by
that infix (mirrors the `direct_certification` consolidation template).

- Topic: financial_efficiency_star_rating
- Source: gosa
- Files: 17 total (9 district 2016-2024 + 8 school 2017-2024)
- Unreadable files: none
- Year representation: year is embedded in each filename (`..._{YYYY}.xlsx|xls`)
  and as 2- or 4-digit suffixes on per-fiscal-year metric columns. The
  rolling-window files (district 2016-2019/2024; school 2019/2024) carry
  multiple fiscal years per file. Year-suffixed column names make every file
  its own column-detected era, cross-checked against the filename year.
- Detail levels: **district** (district family) and **school** (school family);
  no state rows in either family. In gold these unite into one fact table where
  detail is implicit in the geography-key NULL pattern (school ⟺ `school_code IS
  NOT NULL`; district ⟺ `school_code IS NULL`).
- Percentage scale: no percentage metrics. `PPE_PCTL`/`PPE_pctl` (district) is a
  1-100 integer percentile; `FESR` is a 1.0-5.0 (district) / 0.5-5.0 (school)
  star rating in 0.5 increments. The school family's `enroll_pct`/`weight`
  columns are already 0-1 decimal proportions (kept as-is, no division).
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

### District family

| File | SHA-256 |
|------|---------|
| financial_efficiency_star_rating_fesr_district_2016.xlsx | 11f287b494b7072f2ca6e28b8bf9b46180a56eeb7b4a40db7978698277e9b164 |
| financial_efficiency_star_rating_fesr_district_2017.xlsx | 82c47d65795dd1cefef6a9f00506a67ac4d6f529a84ea512bf41114414dfc348 |
| financial_efficiency_star_rating_fesr_district_2018.xlsx | 4da56b813e4e659c13c666c0a7523a9d8441762882a38db2be7d18a22b507264 |
| financial_efficiency_star_rating_fesr_district_2019.xls | 94776db22fc1331c13cd043a7033eeba33b7f63c57301322f931ae25acd7317a |
| financial_efficiency_star_rating_fesr_district_2020.xls | 2d9de15de2178a86baecdba06a663f7c9f903fb987fde8542fbfe2a0e0d838b8 |
| financial_efficiency_star_rating_fesr_district_2021.xls | 04038181bbd69272ad75b7f69c259fd7e7ad9a3ceb414522d927f6e4141e2925 |
| financial_efficiency_star_rating_fesr_district_2022.xls | 44a21d94f1da7fe509d91f7a4e4984ae3b894b1c0fb276ec9334666c274fd441 |
| financial_efficiency_star_rating_fesr_district_2023.xls | 95c1960226dbe6bd5f5a81419093d7055d4264cb00864075bd12b8b184a62a44 |
| financial_efficiency_star_rating_fesr_district_2024.xls | 4df41355f1eab15476b5d4704863c3a9c3b2b6afad44f1df40783a1842a11d3e |

### School family

| File | SHA-256 |
|------|---------|
| financial_efficiency_star_rating_fesr_school_2017.xlsx | 624d9b42123d4460b71e805614aa46a582128fa5a007c2cab42126a8e17dfdf5 |
| financial_efficiency_star_rating_fesr_school_2018.xlsx | b05edf2346465e75aba2459d8f73a8ec66240855a1af054cdd8e25da7eefa71c |
| financial_efficiency_star_rating_fesr_school_2019.xls | 24d09a44beeb7e3fcdb2a64bf23864b4b5dbf25aeb0fd46bff069843a77d1ef4 |
| financial_efficiency_star_rating_fesr_school_2020.xls | c816eabbadb6c657296d29e707defe3a91722a9832878954492164473b34fdd2 |
| financial_efficiency_star_rating_fesr_school_2021.xls | 3adc5e2a219cf6da41b672cded1240af2b11c13452bf78a0c93e29b4bd33cfb0 |
| financial_efficiency_star_rating_fesr_school_2022.xls | d315f1dfca92a3786eb25ed6ade2905a260aaff4c9704f22a568b37aee6aaf27 |
| financial_efficiency_star_rating_fesr_school_2023.xls | 21f76f6911f777b8c361f55cd981418cf5a52aad7120932a8c668627aa459018 |
| financial_efficiency_star_rating_fesr_school_2024.xls | 708ac6760d19e46170b40c49f94abbdd86f3927277bdc0951825d320f6fd118b |

## Excel Sheet Structure

The shared `read_bronze_file` reader takes the first sheet of each workbook,
which is the data sheet in every file of both families (verified); legend sheets
(`Key` / `Variable Key` / `Notes & Variable Key`) are never read. Sheet names
vary year-over-year (`Data`, `2019 FESR`, `{YYYY} PPE`, `Sheet1`).

## Eras

Detected by column signature, never by filename year (the filename year is
cross-checked against the detected era).

### District family (5 structural patterns)

- Pattern A (3-year window, no federal breakdown): 2016
- Pattern B (3-year window, federal/state-local breakdown, 4-digit suffix): 2017, 2018
- Pattern C (3-year window, 2-digit suffix, `School_Amt_*`/`k12_enrollment_*`): 2019
- Pattern D (single-year PPE only, no rating — program pause): 2020, 2021, 2022, 2023
- Pattern E (3-year window revived, non-contiguous FY19/FY23/FY24, `system_id`): 2024

### School family (8 eras, one per file)

- era_2017 / era_2018: PascalCase ids, `Included_School_Amt_{yy}`, string FESR
  with sentinels `.` and `Non-Compliant[ in 20YY]`.
- era_2019: FY17+FY18+FY19 blocks, lowercase ids, `amount_{yy}`/`school_ppe_{yy}`,
  `singlescore_{yy}` scores, numeric FESR, `note` non-compliance column.
- era_2020 / era_2021: single fiscal year, mostly unsuffixed amounts + `_{yy}`
  PPE; 2021 stores literal `Non-Compliant` in PPE columns for one school.
- era_2022: snake_case rename with bronze typos preserved (`included_school_amnt_22`).
- era_2023: hybrid naming; `schoolid2` (zero-padded) is canonical.
- era_2024: FY19+FY23+FY24 blocks, `weight_{yy}` shares, numeric FESR.

## Schema divergence (the merge)

Columns shared by both families (same name + verified-identical derivation,
populated for both levels): `year`, `district_code`, `school_code`,
`total_expenditures`, `fte_enrollment`, `per_pupil_expenditure`,
`federal_per_pupil_expenditure`, `state_local_per_pupil_expenditure`,
`ccrpi_single_score`, `fesr_star_rating`, `is_non_compliant`.

Verified identities (FY2018 gold, both families): `per_pupil_expenditure =
total_expenditures / fte_enrollment` (max gap $0.005 in both); the district's
`federal_expenditures + state_local_expenditures = total_expenditures` and the
school's `total_federal_expenditures + total_state_local_expenditures =
total_expenditures` (both split the same shared `total_expenditures`, gap
≈$0). The school's `included_*` columns instead split the **pre-allocation**
`included_expenditures` (`included/fte` does NOT equal PPE — gap ~$8,493),
confirming `included_*` has no district analog.

Level-specific columns kept separate and NULL on the level that lacks them:

- District-only: `federal_expenditures`, `state_local_expenditures`,
  `per_pupil_expenditure_three_year_avg` (C-1 rename of `ppe_three_year_avg`),
  `ccrpi_three_year_avg`, `per_pupil_expenditure_percentile` (C-1 rename of
  `ppe_percentile`) — NULL on school rows.
- School-only: `included_expenditures`, `included_federal_expenditures`,
  `included_state_local_expenditures`, `excluded_expenditures`,
  `total_federal_expenditures`, `total_state_local_expenditures`,
  `pct_of_district_enrollment` — NULL on district rows.

The district `federal_expenditures`/`state_local_expenditures` and the school
`total_federal_expenditures`/`total_state_local_expenditures` are the SAME
semantic quantity (federal/SL share of the shared `total_expenditures`), but
the two source downloads name them differently and the school family additionally
publishes the distinct `included_*` split. Per the merge's "keep separate when
names differ unless derivation is verified identical AND would not lose data"
rule, they are kept as level-specific columns rather than unified — a unification
would force a single column to carry two different bronze provenances and would
obscure that district rows have no `included_*` analog. The equivalence is
documented in each column's contract description.

---

_Per-family detail (full per-era column inventories, value distributions, and
the original judgment-call write-ups) is preserved in git history under the two
predecessor topics' `bronze-data-structure.md` files
(`financial_efficiency_star_rating_fesr_district` and
`financial_efficiency_star_rating_fesr_school`)._
