# wida_access - Bronze Data Structure

## Overview

- Topic: wida_access
- Source: georgiainsights
- Files: 8 files spanning 2017-2024 (one .xlsx per spring testing year; no file for 2016 or earlier)
- Unreadable files: none
- Year representation: Year is embedded only in the filename (e.g., `ACCESS_for_ELLs_2023_State_Results.xlsx`, `WIDA-ACCESS-2024-State-Results.xlsx`) and echoed in a title string in row 1 (e.g., `Spring 2024 WIDA ACCESS State Results`). There is **no year column in the data itself.**
- Filename-to-data year offset: same (filename year = spring testing year = school year ending in that calendar year — e.g., `ACCESS_for_ELLs_2024_State_Results.xlsx` reports spring 2024 results for school year 2023-2024).
- Detail levels: **state only** (these are state-aggregate reports; every file reports statewide totals for Georgia, disaggregated only by grade).
- Percentage scale: All percentage columns (`% of Total Tested`, `Percentage of Enrolled Students Tested...`) are on a **0-100 scale** (e.g., 45.77 means 45.77%). Verified by min/max and by confirming level percentages sum to 100.0 per domain per grade across every file.
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| ACCESS for ELLs 2021 State Results.xlsx | 79beefd4c8906af1ddef67fd944e778982f5f09968cbe13a7206958e75f0cee0 |
| ACCESS_for_ELLs_2017_State_Results.xlsx | be569ef349cc0ce11b33bccafe83ae55e13d36774d6d4efa28ca151b669a2764 |
| ACCESS_for_ELLs_2018_State_Results.xlsx | d5feb65eb8262f850f7f67aa437fcbccd1799612d4c387b559071505c413b4ab |
| ACCESS_for_ELLs_2019_State_Results.xlsx | 29ddde40b3e4f5db8f852c48ff3e7190a147999657a7ee0f78287de8753182bf |
| ACCESS_for_ELLs_2020_State_Results.xlsx | 5b2bb1f0833fddf153a42fd75db39e1b33ab560ebf47b0b1eb9f994a92c2c283 |
| ACCESS_for_ELLs_2022_State_Results.xlsx | e3c9b9b58d770c8e581cb6f89ef29edef9e5400a46936644ed10dcb83162ba4d |
| ACCESS_for_ELLs_2023_State_Results.xlsx | 0beccddd4a1268985b25356d131326c9e46dfeb9b960d1000ce8570875bba923 |
| WIDA-ACCESS-2024-State-Results.xlsx | c56004a402f5062ea4cb81a4cad46c99525764b5d312999b20d251eb703ea941 |

## Excel Sheet Structure

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2017-2024 (all 8 files) | `State` (Data) | A single sheet named `State` in every file. No metadata, legend, or pivot sheets. The sheet is a wide pivot-style report: row 1 is a title, rows 2-4 are multi-level header rows (domain / proficiency level / metric), and rows 5-17 are one row per grade (K through 12). The 2021 file has 4 additional "footnote" rows (19-25) explaining composite-score weightings and a URL, which must be filtered out by keeping only rows whose first column is `K` or a grade integer 1-12. |

The multi-level headers must be flattened programmatically before the data becomes usable. Polars' built-in `read_excel` reads row 1 (the title) as the only header, which is why the raw column names come back as `__UNNAMED__N`. The transform must parse the workbook with openpyxl (or equivalent) and build composite column names by **forward-filling** the domain row (row 2) and the level row (row 3) across merged cells, then concatenating with the metric row (row 4).

## Summary

Spring ACCESS for ELLs / WIDA ACCESS state-level results for Georgia English Learners — reports statewide proficiency-level distributions across four language domains (Listening, Speaking, Reading, Writing) and four composite scores (Oral Language, Literacy, Comprehension, Overall). For each domain or composite, the data reports the count and percentage of ELL students scoring at each of six proficiency levels (Level 1 Entering through Level 6 Reaching, the WIDA proficiency scale), broken out by grade K through 12. Starting in 2021 (the COVID year), the report also publishes enrollment-adjusted testing participation rates (percentage of enrolled ELLs who actually tested in each domain).

Each row represents one grade; there is no district- or school-level detail in bronze. No demographic breakdown beyond grade is provided.

## Eras

### Era 1: 2017, 2018, 2019, 2020, 2022, 2023, 2024 (7 files)

Standard state-aggregate format: 98 columns per file, 13 data rows (grades K-12), no testing-participation metrics.

After flattening the multi-level headers, the 98 columns resolve to:

| Column | Description |
|--------|-------------|
| `Grade` | String/Int. Grade level. Values: `K` (stored as string), integers 1-12. |
| `Total Number of Students Tested` | Int64. Students tested in at least one domain (not a per-domain denominator). |
| `{Domain} \| Level N {LevelName} \| # of Students at Level` (48 columns) | Int64. Count of students scoring at each of six proficiency levels in each of eight domains/composites. Domains: Listening, Speaking, Reading, Writing. Composites: Oral Language, Literacy, Comprehension, Overall Score. Levels: Level 1 Entering, Level 2 Emerging, Level 3 Developing, Level 4 Expanding, Level 5 Bridging, Level 6 Reaching. |
| `{Domain} \| Level N {LevelName} \| % of Total Tested` (48 columns) | Float64. Percentage on a 0-100 scale. **Denominator is the domain-specific total (students tested in that domain), NOT `Total Number of Students Tested`.** The denominator is implicit — it equals the sum of `# of Students at Level` across all six levels for that domain. See ETL Considerations below. |

#### Sample Data (2024 file — first 4 columns of each grade row)

```text
Grade=K   Total Tested=14148  Listening L1 #=6475   Listening L1 %=45.766186
Grade=1   Total Tested=17139  Listening L1 #=3300   Listening L1 %=19.254332
Grade=2   Total Tested=17527  Listening L1 #=3057   Listening L1 %=17.442657
Grade=3   Total Tested=16292  Listening L1 #=3015   Listening L1 %=18.507151
Grade=4   Total Tested=15498  Listening L1 #=577    Listening L1 %=3.724022
Grade=5   Total Tested=11884  (not shown)
Grade=6   Total Tested=9782   (not shown)
Grade=7   Total Tested=10806  (not shown)
Grade=8   Total Tested=11259  (not shown)
Grade=9   Total Tested=12604  (not shown)
Grade=10  Total Tested=8843   (not shown)
Grade=11  Total Tested=6104   (not shown)
Grade=12  Total Tested=4008   (not shown)
```

#### Statistics

**Total tested state-wide per year (sum across all 13 grades):**

| Year | Total Tested (at least one domain) | K grade | Grade 1 | Grade 12 |
|------|-----------------------------------:|--------:|--------:|---------:|
| 2017 | 104,876 | 17,212 | 17,153 | 1,121 |
| 2018 | 115,639 | 16,152 | 17,255 | 1,608 |
| 2019 | 122,062 | 15,865 | 16,377 | 2,297 |
| 2020 | 129,551 | 15,453 | 16,274 | 2,908 |
| 2022 | 136,399 | 15,044 | 14,732 | 3,219 |
| 2023 | 144,036 | 15,342 | 16,189 | 3,523 |
| 2024 | 155,894 | 14,148 | 17,139 | 4,008 |

(Note the year-over-year growth in total ELL students, especially in the upper grades.)

**Representative describe (2024 file):**

| Column | min | max | mean |
|--------|----:|----:|-----:|
| Total Number of Students Tested | 4,008 | 17,527 | 11,991.8 |
| Listening Domain Level 1 Entering # | 523 | 6,475 | 1,832.4 |
| Listening Domain Level 1 Entering % | 3.72 | 45.77 | 14.39 |
| Overall Score Level 6 Reaching # | 0 | 217 | 30.2 |
| Overall Score Level 6 Reaching % | 0.0 | 1.41 | 0.21 |

#### Null Counts

**Zero nulls in any file/column.** The data is fully populated — every grade × domain × level × metric cell contains a numeric value. When students don't score at a level, the file contains an explicit `0` (for `#`) and `0.0` (for `%`), not null.

#### Categorical Columns

Only one string column: `Grade`. Distinct values (identical across every year):

| Column | Distinct Values |
|--------|-----------------|
| `Grade` | `K`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`, `11`, `12` (13 values total) |

Note: in the raw workbook, `K` appears as a Python string while `1` through `12` appear as integers. Polars (via our programmatic header-flattening) coerces all to String. The transform must map these to the global demographics dimension codes (see Gold Schema Classification below).

#### Suppression Markers

**None.** Zero suppression markers appear in any file — no `TFS`, no `*`, no `--`, no `N/A`. The state-level aggregates are large enough that individual cell counts are never below the small-cell threshold. Cells with zero students at a level are explicitly written as `0`, not suppressed.

### Era 2: 2021 (1 file only — COVID testing-participation reporting)

The 2021 file (`ACCESS for ELLs 2021 State Results.xlsx`) adds participation-rate columns because ACCESS testing was voluntary/disrupted that year. It has 115 columns (vs. 98 in Era 1) and 25 total rows (vs. 17 in Era 1; rows 19-25 are footnotes that must be filtered out).

After flattening headers, the 115 columns resolve to:

| Column | Description |
|--------|-------------|
| `Grade` | Same as Era 1. |
| `Total Number of Students Tested in At Least One Domain` | Int64. Same semantic as Era 1's `Total Number of Students Tested` but with explicit labeling. |
| `Percentage of Enrolled Students Tested in At Least One Domain` | Float64, 0-100 scale. NEW in 2021 — share of enrolled ELLs who tested in at least one domain. Not present in any Era 1 file. |
| `{Domain} \| Total Tested in Domain` (8 columns, one per domain/composite) | Int64. NEW in 2021 — per-domain denominator explicitly published. In Era 1 this number is implicit (sum of `# of Students at Level` across levels). |
| `{Domain} \| Percentage of Enrolled Students Tested in Domain` (for 4 individual domains) | Float64, 0-100 scale. Per-domain testing-participation rate. |
| `{Domain} \| Percentage of Enrolled Students Tested in Both Domains` (for Oral Language, Literacy, Comprehension composites) | Float64, 0-100 scale. The header row literally says "Both Domains" for composites built from two domains. |
| `{Domain} \| Percentage of Enrolled Students Tested in All Four Domains` (for Overall Score composite) | Float64, 0-100 scale. The header row literally says "All Four Domains" for Overall Score. |
| `{Domain} \| Level N {LevelName} \| # of Students at Level` (48 columns) | Int64. Same as Era 1. |
| `{Domain} \| Level N {LevelName} \| % of Total Tested` (48 columns) | Float64, 0-100 scale. Same as Era 1 — denominator is the domain-specific total (`Total Tested in Domain`). |

**Quirk:** 2021's domain names for the four composites include a trailing letter (`Oral Language CompositeA`, `Literacy CompositeB`, `Comprehension CompositeC`, `Overall Score CompositeD`) that maps to footnotes in rows 19-22 of the raw workbook explaining the composite-score weightings (e.g., `AOral Language = 50% Listening + 50% Speaking`). Era 1 files have no such suffix. The transform must strip the trailing letter when normalizing composite names.

#### Sample Data (2021 file, first 5 columns of Grade K row)

```text
Grade=K
Total Number of Students Tested in At Least One Domain = 12779
Percentage of Enrolled Students Tested in At Least One Domain = 95.45115
Listening Domain | Total Tested in Domain = 12774
Listening Domain | Percentage of Enrolled Students Tested in Domain = 95.413803
Listening Domain | Level 1 Entering | # of Students at Level = 4391
Listening Domain | Level 1 Entering | % of Total Tested = 34.374511
```

#### Statistics (2021 file)

| Column | min | max | mean |
|--------|----:|----:|-----:|
| Total Number of Students Tested in At Least One Domain | 2,304 | 14,224 | 8,805.1 |
| Percentage of Enrolled Students Tested in At Least One Domain | 66.65 | 95.45 | 87.02 |
| Listening Domain Total Tested | 2,299 | 14,186 | 8,792.2 |
| Listening Domain % Enrolled Tested | 66.50 | 95.41 | 86.89 |
| Overall Score Total Tested | 2,227 | 14,014 | 8,671.3 |
| Overall Score % Enrolled Tested in All Four Domains | 64.42 | 95.18 | 85.39 |

#### Null Counts

Zero nulls. Same as Era 1 — fully populated.

#### Categorical Columns

Same as Era 1 — only `Grade`, same 13 distinct values.

#### Suppression Markers

None. Same as Era 1.

## ETL Considerations

### Pivoted header structure requires programmatic flattening

The source files are pivot-style reports (grade × domain × level × metric), not tabular CSVs. Every file has three header rows that must be combined into a single column name:

- Row 2 (domain row): `Listening Domain`, `Speaking Domain`, `Reading Domain`, `Writing Domain`, `Oral Language Composite` (or `Oral Language CompositeA` in 2021), `Literacy Composite(B)`, `Comprehension Composite(C)`, `Overall Score Composite(D)`. Only the first cell of each domain group is populated — the other 11 cells in that domain are `None` because Excel merges cells.
- Row 3 (level row): `Level 1\nEntering` through `Level 6\nReaching`, with one cell populated per level. For 2021, row 3 also contains `Total Tested \nin Domain` and `Percentage of Enrolled Students Tested in (Domain / Both Domains / All Four Domains)`.
- Row 4 (metric row): `# of Students at Level` and `% of Total Tested` for every level cell.

`pl.read_excel()` alone does not flatten these — it reads row 1 (the title) as the only header and returns `__UNNAMED__N` column names. The transform **must** use `openpyxl` (or a manual polars approach with `header_row=0` plus forward-filling) to pull rows 2-4 and build composite column names. Suggested approach:

```python
import openpyxl

wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
ws = wb['State']
rows = list(ws.iter_rows(values_only=True))
# rows[1] = domains, rows[2] = levels, rows[3] = metrics
# Forward-fill domains and levels across merged/None cells, then combine with metrics
```

### Denominator for `% of Total Tested` is domain-specific, NOT `Total Number of Students Tested`

This is the most important numerical fact to preserve. For every domain/composite:

- The six `% of Total Tested` values in that domain sum to exactly 100.0 per grade (verified across all files — no rounding drift).
- The six `# of Students at Level` values in that domain sum to a number that is **less than or equal to** the overall `Total Number of Students Tested` — because not every student tested in the overall column tested in every specific domain.
- Specifically, for 2024 Grade 6: overall `Total Number of Students Tested = 9782`, but Listening sum = 9724 (58 students missing), Speaking sum = 9707 (75 missing), Overall Score Composite sum = 9668 (114 missing).

The denominator `% of Total Tested` divides by is **the implicit per-domain total** (sum of `# of Students at Level` across the six levels of that domain), not the overall column. In Era 2 (2021) this denominator is made explicit as `{Domain} | Total Tested in Domain`.

**Implication for gold schema:** If the gold fact table stores rate metrics, it must either (a) emit a separate `num_tested_in_domain` per-domain denominator column alongside each rate, or (b) store both the `# of Students at Level` and `% of Total Tested` values so downstream queries can reconstitute the denominator. Option (b) is simpler and is what the current bronze publishes directly. Just propagating the published `% of Total Tested` verbatim is the safest approach.

### 2021 has extra footnote rows that must be filtered out

The 2021 file's `State` sheet has 25 total rows:

- Rows 1-4: headers (as elsewhere).
- Rows 5-17: the 13 grade rows (K, 1-12).
- Rows 18-25: blank rows and footnotes describing composite weightings and linking to a state assessment URL. The footnote text appears in column 0 (the `Grade` column) and breaks any naive "read all rows" loop.

Filter rule: keep a row if and only if its `Grade` column value is literally `K` or an integer in the range 1-12. Rows with `None`, or text like `AOral Language = 50%...`, or a URL, must be dropped.

### 2021 composite names have trailing footnote letters

In 2021, composite domain headers are `Oral Language CompositeA`, `Literacy CompositeB`, `Comprehension CompositeC`, `Overall Score CompositeD`. The trailing letter maps to footnotes in rows 19-22. The transform should strip these trailing single uppercase letters so composites normalize to `Oral Language Composite`, `Literacy Composite`, `Comprehension Composite`, `Overall Score Composite` and align with Era 1.

### Year is only in the filename

No `year` column exists in the data. The transform must extract year from the filename using a regex that handles both naming patterns:

- `ACCESS for ELLs YYYY State Results.xlsx` (2021)
- `ACCESS_for_ELLs_YYYY_State_Results.xlsx` (2017, 2018, 2019, 2020, 2022, 2023)
- `WIDA-ACCESS-YYYY-State-Results.xlsx` (2024)

Suggested regex: `r"(\d{4})"` anchored by checking the extracted year is between 2015 and the current year — works on all three patterns. The year represents the **spring testing year** (end of a school year): file `..._2024_...` = spring 2024 results = school year 2023-2024. Per education domain conventions, `year` in gold is the ending calendar year (so 2024 for school year 2023-2024) — that maps directly to the filename year. No offset needed.

### Missing 2016 and earlier

There is no 2016 file or earlier. ACCESS for ELLs has been administered in Georgia since before 2016, but the georgiainsights portal only publishes these `State Results.xlsx` files starting in 2017. No action needed; just note the coverage gap in gold metadata.

### No 2021 gap (but 2021 is Era 2)

Unlike GOSA assessment topics which skip 2020 (state assessments cancelled), WIDA ACCESS testing continued through the pandemic. The 2021 file is present — it just adds the `Percentage of Enrolled Students Tested` participation-rate columns because testing participation was unusually low that year.

### Grade is a mixed int/str column

In the raw workbook, `K` is a Python string but grades 1-12 are Python integers. Polars' column inference will make the column `Object` or fail. The transform must cast everything to string early (`pl.col("Grade").cast(pl.Utf8)`) — this gives `"K"`, `"1"`, `"2"`, ..., `"12"`. The integer grades become the string representation when cast.

### All state-level aggregates — single detail level

Every row in every file is a state-aggregate for Georgia. There is no district or school breakdown in bronze. Per education conventions, the gold fact should output to `data/gold/education/wida_access/year=YYYY/states.parquet` only. No `districts.parquet` or `schools.parquet` file should be produced — only the single `states.parquet` file per year (empty-file rule from the project CLAUDE: "only create files for detail levels that have data").

Both `district_code` and `school_code` must be NULL for every row.

### Per-grade demographic mapping

Grades in bronze map cleanly to the global demographics dimension (`data/gold/_dimensions/demographics.parquet`, category = `grade`):

| Bronze `Grade` | Gold `demographic` |
|----------------|--------------------|
| `K` | `kindergarten` |
| `1` | `grade_1` |
| `2` | `grade_2` |
| `3` | `grade_3` |
| `4` | `grade_4` |
| `5` | `grade_5` |
| `6` | `grade_6` |
| `7` | `grade_7` |
| `8` | `grade_8` |
| `9` | `grade_9` |
| `10` | `grade_10` |
| `11` | `grade_11` |
| `12` | `grade_12` |

All 13 values are already present in the global demographics dimension — no new demographic codes need to be added.

### Tidy format strongly recommended

The bronze layout is heavily pivoted: 96 metric columns per grade row in Era 1 (and 113 in Era 2), expressing every (domain × level × metric) combination as a separate wide column. This is not practical for the gold fact table under star-schema conventions. The transform should **unpivot/melt** the data into a tidy long format with one row per (`year`, `grade`, `domain`, `proficiency_level`), keyed as follows:

- `year` (Int32, from filename) — fact key
- `district_code` (Utf8, always NULL) — fact key
- `school_code` (Utf8, always NULL) — fact key
- `demographic` (Utf8, grade code) — fact key
- `domain` (Utf8, categorical — 8 values: `listening`, `speaking`, `reading`, `writing`, `oral_language_composite`, `literacy_composite`, `comprehension_composite`, `overall_score_composite`) — fact categorical
- `proficiency_level` (Utf8, categorical — 6 values: `level_1_entering`, `level_2_emerging`, `level_3_developing`, `level_4_expanding`, `level_5_bridging`, `level_6_reaching`) — fact categorical
- Metrics (one row per domain × level combination):
  - `students_at_level` (Int64, from `# of Students at Level`)
  - `pct_of_tested` (Float64, 0-100 scale, from `% of Total Tested`)
- Secondary row-level context (one row per grade, joined back or repeated):
  - `num_tested` (Int64, from `Total Number of Students Tested` or `Total Number of Students Tested in At Least One Domain`) — students tested in at least one domain (denominator-at-large)
  - `pct_enrolled_tested` (Float64, 0-100 scale, NULL for Era 1, populated for Era 2) — overall testing participation rate

(Alternatively, the per-domain `num_tested_in_domain` and `pct_enrolled_tested_in_domain` could be stored as additional fact attributes — they're only available in 2021 but would be NULL for Era 1 years.)

This long-format design produces approximately 13 grades × 8 domains × 6 levels = 624 rows per year, which is a dramatic improvement over the 13-row × 96-metric wide bronze format.

### Percentage scale — keep as 0-100, do not rescale

Per the education domain CLAUDE.md, "Percentage Scale Exceptions" includes "Percentile ranks — preserve as 0-100 integers." The `% of Total Tested` values in this dataset are proficiency-level shares — not percentile ranks — so they follow the **default** data-cleaning rule of 0-1 (0.4577) rather than 0-100 (45.77). The transform should **divide by 100** to put these on the 0-1 scale consistent with the rest of the gold corpus. Same treatment for Era 2's `Percentage of Enrolled Students Tested` columns.

### Level name normalization

The WIDA proficiency levels are always six, in order: `Level 1 Entering`, `Level 2 Emerging`, `Level 3 Developing`, `Level 4 Expanding`, `Level 5 Bridging`, `Level 6 Reaching`. These are intrinsic to the WIDA scale and never change across years. Snake-case as `level_1_entering`, `level_2_emerging`, etc.

### Domain name normalization

Four test domains (always tested individually) and four composites (always computed from combinations):

| Bronze (Era 1) | Bronze (Era 2) | Gold (snake_case) |
|----------------|----------------|-------------------|
| Listening Domain | Listening Domain | listening |
| Speaking Domain | Speaking Domain | speaking |
| Reading Domain | Reading Domain | reading |
| Writing Domain | Writing Domain | writing |
| Oral Language Composite | Oral Language CompositeA | oral_language_composite |
| Literacy Composite | Literacy CompositeB | literacy_composite |
| Comprehension Composite | Comprehension CompositeC | comprehension_composite |
| Overall Score Composite | Overall Score CompositeD | overall_score_composite |

The trailing `A`/`B`/`C`/`D` in 2021 are footnote references and must be stripped.

## Gold Schema Classification

For the pivot-to-tidy long-form output described above, each bronze column resolves as follows. Since bronze is heavily pivoted, I describe the gold role of each bronze **column group** rather than each of the 98/115 individual columns.

| Bronze Column Group | Gold Role | Gold Name | Notes |
|---------------------|-----------|-----------|-------|
| `Grade` | fact_key | `demographic` | Map to demographics dimension codes (`kindergarten`, `grade_1`-`grade_12`). Cast Int/Str to Str first. |
| `Total Number of Students Tested` (Era 1) / `Total Number of Students Tested in At Least One Domain` (Era 2) | fact_metric | `num_tested` | Int64. Students tested in at least one domain — the "all-domain" grade denominator. Repeated on every long-form row for that grade × year. |
| `Percentage of Enrolled Students Tested in At Least One Domain` (Era 2 only, NULL for Era 1) | fact_metric | `pct_enrolled_tested` | Float64, scale to 0-1. Testing-participation rate. Era 1 values are NULL. Repeated on every long-form row for that grade × year. |
| `{Domain} \| Total Tested in Domain` (Era 2 only) | fact_metric | `num_tested_in_domain` | Int64. Per-domain denominator. Era 1 rows: NULL (not published explicitly) — OR the transform can reconstruct by summing `# of Students at Level` across levels for that row × domain. Recommend reconstructing so Era 1 also has this value. |
| `{Domain} \| Percentage of Enrolled Students Tested in Domain/Both Domains/All Four Domains` (Era 2 only) | fact_metric | `pct_enrolled_tested_in_domain` | Float64, scale to 0-1. Era 1 rows: NULL. |
| `{Domain} \| Level N {LevelName}` (via the pivot key) | fact_categorical | `domain` + `proficiency_level` | Split into two categorical columns: `domain` (8 values) and `proficiency_level` (6 values). |
| `{Domain} \| Level N {LevelName} \| # of Students at Level` | fact_metric | `students_at_level` | Int64. Student count at that proficiency level in that domain. |
| `{Domain} \| Level N {LevelName} \| % of Total Tested` | fact_metric | `pct_of_tested` | Float64, scale from 0-100 to 0-1. Share of domain-tested students scoring at that level. |
| (implicit from filename) | fact_key | `year` | Int32. Spring testing year = school year ending year (e.g., 2024 for school year 2023-2024). |
| (implicit — state-only data) | fact_key | `district_code` | Utf8, always NULL. |
| (implicit — state-only data) | fact_key | `school_code` | Utf8, always NULL. |
| Row 1 title string (e.g., `Spring 2024 WIDA ACCESS State Results`) | not_in_gold | — | Redundant with filename year; skip. |
| Rows 19-25 in 2021 (footnotes, composite-weighting definitions, URL) | not_in_gold | — | Non-data rows; filter out by keeping only grade-valued rows. |

Final fact table grain: one row per (`year`, `district_code=NULL`, `school_code=NULL`, `demographic=grade`, `domain`, `proficiency_level`). Expected row counts: ~624 rows per year × 8 years = ~5,000 rows total across the topic.

Output only `data/gold/education/wida_access/year=YYYY/states.parquet` per year — no `districts.parquet` or `schools.parquet` (empty-file rule: only create files for detail levels that have data).

## Corrections

- **2026-06-12 (transform authoring)**: The 2021 footnote-row counts above are imprecise in two places. The "Excel Sheet Structure" table says the 2021 file has "4 additional 'footnote' rows (19-25)", and the Era 2 section says "rows 19-25 are footnotes". Verified with openpyxl: the 2021 sheet has **8 additional non-data rows below the 13 grade rows — 1-indexed rows 18-25** — consisting of 2 blank separator rows, the 4 composite-weighting footnote rows (A-D), 1 explanatory note row, and 1 URL row. The "ETL Considerations" section ("Rows 18-25: blank rows and footnotes") was already correct. The grade-token filter (keep only `K`/`1`..`12` in column 0) drops exactly 8 rows in 2021 and 0 in every other year.
- **2026-06-12 (transform authoring)**: The "Per-grade demographic mapping" and "Gold Schema Classification" sections recommend mapping the bronze `Grade` column into the `demographic` column (`kindergarten`, `grade_1`..`grade_12`). This is superseded by the education-domain **grade-in-demographic policy** (`src/etl/education/CLAUDE.md`): grade is the *primary row axis* for this topic (no race/gender/economic breakouts exist), so gold stores it in `grade_level` with canonical codes (`k`, `01`..`12`) via `src/utils/grades.py` and emits **no `demographic` column**. This matches the v1 gold schema. The recommended metric names also differ from the actual gold names: gold uses `num_at_proficiency_level` / `pct_at_proficiency_level` (per §16 the level-condition counts take the `num_*`/`pct_*` pattern), not `students_at_level` / `pct_of_tested`, and the Era-2 participation rates are `enrollment_tested_rate` / `enrollment_tested_in_domain_rate`, not `pct_enrolled_tested*`.
- **2026-06-12 (transform authoring)**: Precision note on "level percentages sum to exactly 100.0 per domain per grade ... no rounding drift": re-verified across all 8 files — the maximum observed deviation of the six-level sum from 100.0 is 2e-06 (float noise at publication precision), and the 2021 published `Total Tested in Domain` equals the six-level count sum in **every** cell (0 mismatches). The substance of the claim stands; the tolerance is now quantified.
