# direct_certification — Bronze Data Structure

## Overview

- Topic: direct_certification
- Source: gosa
- Files: 22 files — two GOSA download families covering the same fiscal years
  2014-2024:
  - **school family** (`direct_certification_school_YYYY.{csv,xls}`, 11 files):
    one row per school within a district; school detail level.
  - **district family** (`direct_certification_district_YYYY.{csv,xls}`, 11
    files): one row per district/system; district detail level, plus a
    statewide aggregate row (`SYSTEM_ID=999`) in 2022-2024.
- Unreadable files: none
- Provenance: this topic is the merge of the formerly separate
  `direct_certification_school` and `direct_certification_district` topics into
  one fact table with three detail levels (`schools`, `districts`, `states`).
  The two families are distinct GOSA downloads with identical metric semantics;
  the merged transform routes each file to the right per-family reader by the
  `_school_` / `_district_` infix in its filename.
- Year representation: a dedicated year column (`SCHOOL_YEAR` in 2014,
  `FISCAL_YEAR` in 2015-2024) in every file; one fiscal year per file matching
  the filename year. Georgia fiscal-year convention: FY2024 = the 2023-24
  school year.
- Filename-to-data year offset: same — each file's year column equals the
  filename year.
- Detail levels: `school` (school family, both geography keys populated),
  `district` (district family standard/charter/agency rows, `school_code`
  NULL), `state` (district family `SYSTEM_ID=999` "State of Georgia" row,
  2022-2024 only; both geography keys NULL).
- Percentage scale: `direct_cert_perc` is on the 0-100 scale in every file and
  family (integer in 2014-2016, one-decimal float in 2017+). Divided by 100 to
  the 0-1 proportion scale in gold.
- Checksums generated: 2026-05-22 (carried over from the two source topics'
  analyses; file bytes are unchanged copies).

## Source Provenance

- **Source URL**: https://gosa.georgia.gov/dashboards-data-report-card/downloadable-data (GOSA Downloadable Data page)
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| direct_certification_school_2014.csv | f4a983631be3a9cd723991a64830dae63947317f70b545c87fbc6d3379f1099d |
| direct_certification_school_2015.csv | d1ec3866f8659dd811b9aa2094022f4fae43a1d22676060676a48e13dca72e24 |
| direct_certification_school_2016.csv | 99ab205619e38a987b6ac42d8a0321430bc2ec158ed6052b80092b0e6646f1c2 |
| direct_certification_school_2017.xls | b397417e4feff4d1e07d9e09bf841ecfe44e688f64fd6d5083fd18e1ebcf5f17 |
| direct_certification_school_2018.xls | 7a18708bd1aca5130c733c77db38db3776e7c8d0a838f665819c945ee0a5012f |
| direct_certification_school_2019.xls | 8d7e9a9c91577449b5ae2ebaa2de6d0a1d0381aab1fc6af6c566ce28a85c3b5c |
| direct_certification_school_2020.xls | 8ad1f53c3aae2fd71434562c40bf2cb3bf82a43d50eddcf0fe63cbb4dd0b9acc |
| direct_certification_school_2021.xls | 5bb45dd3335cc28508ae79b5de2ad33135e94195dbd297d8539cd59e89b2cbd7 |
| direct_certification_school_2022.xls | a9c171ad9f8fc2e7b914f6b9bd7b572d7d6a38061493a72689fc69a81ee4d7ff |
| direct_certification_school_2023.xls | be708c568d873c16cfd93f888ff6a5cda37c1d7093bb732784af6d15e5afab06 |
| direct_certification_school_2024.xls | f9cad58624309455ee77031a16cdd4ba97d0b66cb3e851da87d094006e5a739c |
| direct_certification_district_2014.csv | 7526dae8b7b6c8454c694c1c221b7cef406e7afc26a182488ae75ac2c3b6f381 |
| direct_certification_district_2015.csv | 8813c02b37a6ffc23af19b2a38031b1a4340064439a2a624e7e351ff8aed5e07 |
| direct_certification_district_2016.csv | 59dbf4890d37baa7f1ecb982d1ff6ef484717856c533746ae25910eff1f5fa01 |
| direct_certification_district_2017.xls | 687f83e3a477ef85ed1a923d5a01d8d59b2d4c751ec5bc5bde1ece78b3d806c6 |
| direct_certification_district_2018.xls | f787a4bd94de7a71a46077bb759dc261dcbffaf36f9ba09e800723fbf430528e |
| direct_certification_district_2019.xls | be90f0b53eb9475c25a74c3d3100d4fc5f93bcb2e4974abbb24458ab018da7c1 |
| direct_certification_district_2020.xls | 45eec719fedf64fb82d59f11da5d8ceebdff9a84bf8e59e30465b8164daa88fe |
| direct_certification_district_2021.xls | cf03dfee0b6570c51d4438f5077f2cc20922f55c357cb842b9866013342f64c3 |
| direct_certification_district_2022.xls | b519cb1ac71c83b7de444b16a0d63c2dea36cb38a6a37fd204c4d19ddc13c50c |
| direct_certification_district_2023.xls | 91c4609d0828c0ff0cb314a2b451722642695a9478577c3887ebb3dec322b391 |
| direct_certification_district_2024.xls | 3a662bb28fd249151d085b15eb708b967d5b4b14ab089768abdcec98c8adac2d |

## Excel Sheet Structure

Both families share the same file-format timeline: 2014-2016 are CSV, 2017-2024
are legacy `.xls` (BIFF binary, single `Sheet1`, requiring the `xlrd` engine).
In both families the 2017 and 2018 `.xls` files carry a free-text methodology
note on row 0 with the real column headers on row 1; every other `.xls` file
has its header on row 0.

Embedded methodology notes (identical wording in both families):
- 2017.xls row 0: "*Note: The 2017 direct certification counts do not include
  foster students, so these percentages are not comparable to previous years."
- 2018.xls row 0: "*Note: The 2018 direct certification counts include foster
  students, so these percentages are not comparable to percentages from 2017."

## Summary

Annual **direct certification rate** for Georgia public schools and districts.
Direct certification identifies K-12 students automatically eligible for free
school meals through enrollment in means-tested programs (SNAP, TANF, FDPIR,
Medicaid expansion) or because the student is in foster care, homeless,
migrant, runaway, or a Head Start enrollee — without a household application.
The core metric `direct_cert_perc` is the share of K-12 students directly
certified. From FY2020 both families also publish the underlying numerator
(`K12_POVERTY_STUDENT_CT`) and denominator (`K12_STUDENT_COUNT`).

Two methodology breaks affect comparability across years (documented, never
mutated):
1. **FY2017 vs FY2018** — 2017 counts exclude foster students; 2018+ include
   them (per GOSA's embedded file note).
2. **FY2024** — Georgia joined the USDA Direct Certification with Medicaid
   (DC-M) Demonstration Project, adding a Medicaid income category; rates jump
   sharply (district mean ~0.38 → ~0.63).

## Eras

Both families share the same four-era column evolution, detected by column
signature (never by year range). The school family carries an extra `sys_sch`
column (a redundant `str(SYSTEM_ID)+str(SCHOOL_ID)` concatenation) from 2017
that is dropped; the district family has no per-school columns.

| Era | Years | Year column | Counts published | Family-specific notes |
|-----|-------|-------------|------------------|-----------------------|
| 1 | 2014 | `SCHOOL_YEAR` | no | integer percentages |
| 2 | 2015-2016 | `FISCAL_YEAR` | no | CSV, integer percentages |
| 3 | 2017-2019 | `FISCAL_YEAR` | no | `.xls`; school family adds redundant `sys_sch`; 2017/2018 note-on-row-0 |
| 4 | 2020-2024 | `FISCAL_YEAR` | yes (`K12_POVERTY_STUDENT_CT`, `K12_STUDENT_COUNT`) | `.xls` |

Per-family per-year row counts (verified in the two source analyses, retained
here for reference):
- **school family**: 2014 = 2,261; 2015 = 2,254; 2016 = 2,247; 2017 = 2,290;
  2018 = 2,297; 2019 = 2,299; 2020 = 2,296; 2021 = 2,302; 2022 = 2,308;
  2023 = 2,310; 2024 = 2,318.
- **district family**: 2014 = 198; 2015 = 198; 2016 = 203; 2017 = 207;
  2018 = 213; 2019 = 214; 2020 = 215; 2021 = 221; 2022 = 223 (incl. 1 state
  row); 2023 = 227 (incl. 1 state row); 2024 = 235 (incl. 1 state row).

The two source structure docs
(`direct_certification_school/bronze-data-structure.md` and
`direct_certification_district/bronze-data-structure.md`, removed when those
topics were retired) hold the full per-era column tables, sample data, and
statistics; nothing about the underlying files changed in the merge.

## ETL Considerations

- **Family routing by filename.** The merged transform lists all 22 files in
  this directory and routes each by its `_school_` / `_district_` infix to the
  matching per-family reader + era transform. The two readers differ only in
  the 2017/2018 header handling (the school reader promotes row 0 in-place; the
  district reader re-reads with pandas `header=1`) and the school family's
  `SCHOOL_ID`/`sys_sch` columns.
- **Year column rename across eras**: `SCHOOL_YEAR` (2014) → `FISCAL_YEAR`
  (2015+); coalesced to a single Int32 `year`, cross-checked against the
  filename year (a mismatch raises).
- **Counts are FY2020+ only**: `K12_POVERTY_STUDENT_CT` /`K12_STUDENT_COUNT`
  are NULL for 2014-2019 in both families (the source did not publish them);
  pinned by the `counts_*` quality checks in both directions.
- **ID formatting**: `SYSTEM_ID` → `district_code` via `.cast(Utf8).str.zfill(3)`
  (pads standard 3-digit codes, leaves 7-digit charter / 4-digit agency codes
  unchanged; never truncate). `SCHOOL_ID` → `school_code` via `.str.zfill(4)`
  (school family only). The school family's redundant `sys_sch` is dropped.
- **Rate scaling**: `direct_cert_perc` (0-100) → `direct_cert_rate` (0-1) by
  dividing by 100 and rounding to 3 decimals — lossless for the published
  one-decimal precision and collapses `.xls` binary-float artifacts
  (`82.400002` → `0.824`).
- **No suppression anywhere**: every file in both families is 100% numeric with
  zero nulls and no suppression markers. `suppressed_to_null=False`; pinned by
  `direct_cert_rate_never_null`.
- **Detail-level geography nulling**: district family `SYSTEM_ID=999` rows →
  `state` detail (both geography keys NULL); other district family rows →
  `district` detail (`school_code` NULL); school family rows → `school` detail
  (both keys populated).
- **Non-standard district codes kept as district rows** (district family; all
  resolve in the districts dimension): `799` combined State Schools (2020+),
  `890` Dept. of Corrections (2019 only), `891` Dept. of Juvenile Justice
  (2017+), `7991893`-`7991895` individual State Schools (2014-2019), and 7-digit
  `782xxxx`/`783xxxx` charter codes. The State-Schools representation change
  (three individual rows → one combined `799` row at 2020) is passed through
  as-is.
- **Statewide aggregate is partial**: the `State of Georgia` (`SYSTEM_ID=999`)
  row exists only 2022-2024; no state rows are synthesized for earlier years.
  The published state counts equal the district-row sums exactly in all three
  years (pinned by `state_counts_equal_district_sums`).
- **No demographic column**: no era of either family publishes any subgroup
  breakdown.

## Gold Schema Classification

One fact table, three detail levels, written as `schools.parquet`,
`districts.parquet`, and `states.parquet` under each `year=YYYY` partition.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SCHOOL_YEAR / FISCAL_YEAR | fact_key | year | Coalesced; Int32 year partition key. |
| SYSTEM_ID | fact_key | district_code | FK to districts dimension; `.str.zfill(3)`. NULL on state rows. |
| SCHOOL_ID (school family) | fact_key | school_code | FK to schools dimension; `.str.zfill(4)`. NULL on district/state rows. |
| SYSTEM_NAME | dimension_attribute | — | `district_name` in districts dimension; not in fact table. |
| SCHOOL_NAME (school family) | dimension_attribute | — | `school_name` in schools dimension; not in fact table. |
| direct_cert_perc | fact_metric | direct_cert_rate | 0-100 → 0-1 (÷100, round 3). `unit: proportion`. Key metric. |
| K12_POVERTY_STUDENT_CT | fact_metric | direct_cert_student_count | Numerator, Int64. FY2020+ only; NULL earlier. |
| K12_STUDENT_COUNT | fact_metric | k12_student_count | Denominator, Int64. FY2020+ only; NULL earlier. |
| sys_sch (school family) | not_in_gold | — | Redundant concatenation; dropped. |
