---
name: bronze-data-structure
description: Bronze Data Structure: Create a data structure report for a single topic
disable-model-invocation: true
argument-hint: "[main_topic] [sub_topic] [topic]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Agent"]
---

# Bronze Data Structure Report

Create a data structure report for a single topic. Provides context for transforming bronze data to gold data via the transform.py.

## Input

Arguments: `$ARGUMENTS` (format: `[main_topic] [sub_topic] [topic]`)

Example: `education gosa act_scores`

**Parsed arguments:**
- `main_topic`: first argument (`$0`)
- `sub_topic`: second argument (`$1`)
- `topic`: third argument (`$2`)

**Derived paths:**
- Bronze data directory: `data/bronze/$0/$1/$2/`
- Output: `data/bronze/$0/$1/$2/bronze-data-structure.md`

## Step 1: Detect Excel Sheet Structure

For each Excel file (.xls, .xlsx) in the topic directory, list all sheet names:

```bash
uv run python -c "
import openpyxl
wb = openpyxl.load_workbook('data/bronze/$0/$1/$2/FILENAME', read_only=True)
print(wb.sheetnames)
wb.close()
"
```

For each sheet, read a few rows to classify its purpose:
- **Data** — Contains the actual dataset rows (use this sheet for all subsequent analysis steps)
- **Metadata/Legend** — Explains column definitions, suppression codes, footnotes, or data sources. Capture any useful details (e.g., suppression code definitions) for the ETL Considerations section.
- **Summary/Pivot** — Pre-aggregated views that should be skipped during transform

Note whether the sheet structure changes across files (e.g., "2020-2024 files have a single `Data` sheet, but 2015-2019 files split data across `District` and `School` sheets"). If data is split across multiple sheets that need to be concatenated during transform, flag this explicitly.

For CSV files, skip this step.

## Step 2: Detect Eras by Column Names

An **era** is a contiguous range of years where the files have the **exact same column names** (order doesn't matter, but names must match exactly).

1. List all files in `data/bronze/$0/$1/$2/` sorted by year (newest first).

2. Extract column names from each file. Use the Read tool for CSV files (just the header row). For Excel files (.xls, .xlsx), use Bash to run:
   ```bash
   uv run python -c "
   import polars as pl
   df = pl.read_excel('data/bronze/$0/$1/$2/FILENAME')
   print(df.columns)
   "
   ```

3. If a file cannot be read (corrupted, password-protected, unsupported format), log it as unreadable and continue.

4. Group years into eras: consecutive years with identical column name sets belong to the same era.

5. For each era, pick one representative file and read enough of it (header + a few rows) to write a brief description of each column.

## Step 3: Analyze Dataset

For each era's representative file, run the following Polars analysis and include the results in the report:

```bash
uv run python -c "
import polars as pl
pl.Config.set_tbl_cols(-1)
pl.Config.set_tbl_width_chars(400)
pl.Config.set_fmt_str_lengths(80)

df = pl.read_excel('data/bronze/$0/$1/$2/FILENAME')  # or pl.read_csv() for CSV files
print('=== Sample (5 rows) ===')
print(df.sample(min(5, len(df))))
print()
print('=== Describe ===')
print(df.describe())
print()
print('=== Null Counts ===')
print(df.null_count())
"
```

## Step 4: Classify Columns and Extract Distinct Values

For each era's representative file, classify every string (`Utf8`) column as either **categorical** or **numeric-with-suppression**:

```bash
uv run python -c "
import polars as pl
pl.Config.set_tbl_cols(-1)
pl.Config.set_tbl_width_chars(400)
pl.Config.set_fmt_str_lengths(80)

df = pl.read_excel('data/bronze/$0/$1/$2/FILENAME')  # or pl.read_csv() for CSV files

for col_name in df.select(pl.col(pl.Utf8)).columns:
    col = df[col_name].drop_nulls()
    if len(col) == 0:
        continue
    numeric_count = col.cast(pl.Float64, strict=False).drop_nulls().len()
    total = len(col)
    numeric_pct = numeric_count / total if total > 0 else 0

    if numeric_pct > 0.5:
        # Mostly numeric — show only the non-numeric values (suppression markers)
        non_numeric = col.filter(col.cast(pl.Float64, strict=False).is_null()).unique().sort().to_list()
        print(f'{col_name} [SUPPRESSION MARKERS]: {non_numeric}')
    else:
        # Truly categorical — show all distinct values
        distinct = col.unique().sort().to_list()
        print(f'{col_name} [CATEGORICAL]: {distinct}')
"
```

**How to interpret the results:**
- **`[CATEGORICAL]`** — Truly categorical column. List all distinct values with the counts of each value in the report. These are candidates for demographic mapping, detail level detection, etc.
- **`[SUPPRESSION MARKERS]`** — Numeric column stored as string due to suppressed values. Only list the non-numeric values with their counts. These are the markers that `strict=False` casting will convert to null.

**Asian / Pacific Islander check**: when the bronze includes race buckets (either as values in a `subgroup` column or as wide-format columns like `Number of Asians`), explicitly note whether a separate Pacific Islander bucket exists. If the bronze has only 6 race buckets (American Indian, Asian, Black, Hispanic, Multiracial, White), flag this in the report and apply the math test: at a state-level row, sum the race-bucket counts and compare to the cohort total. If race sum equals total exactly, "Asian" is the pre-1997 OMB combined Asian + Pacific Islander bucket — not Asian-only — and the transform must remap it to `asian_pacific_islander` rather than `asian`. Document this finding in the bronze structure report so the downstream `/transform-topic` step does not silently misclassify. Also flag whether bronze publishes both the split rows (`Asian` + `Pacific Islander`) AND a combined `Asian/Pacific Islander` row in the same file — if so, the transform must keep only one to preserve mutual exclusivity within the race category (see `data-cleaning-standards` skill §5a). See `data-cleaning-standards` skill §5b for the bare-Asian → combined-bucket remapping pattern.

## Step 5: Identify Detail Levels

Determine what geographic/organizational detail levels are present in the data (e.g., state, district, school). Look for:
- Columns that identify geography (district codes, school codes, institution numbers)
- Rows where these columns are blank, "ALL", or aggregated (indicating a higher-level summary row)
- Distinct patterns that indicate which levels exist

## Step 6: Identify Year Representation

Determine how the year is represented:
- Is it a column in the data? If so, what is the column name and format (e.g., `2024`, `2023-2024`, `FY2024`)?
- Is it only in the filename? If so, what is the naming pattern?
- Is it a school year (spanning two calendar years) or a single calendar year?
- What year(s) does the data actually represent? Check year columns or date values in the data itself.
- **Filename year vs data year**: The year in the filename is the *publication year*, which may differ from the year the data represents. For example, a file named `2023.xlsx` might contain 2022 graduation rates. If a year column exists, compare its values to the filename year and note any offset (e.g., "filename year is consistently data year + 1").

## Step 6.5: Record Source Provenance

Record where the bronze files came from so re-acquisition is never tribal
knowledge. If the source URL / retrieval date are not determinable (files
predate provenance tracking), say so explicitly rather than guessing.

The report's **Source Provenance** section records:
- **Source URL**: the page or endpoint the files were downloaded from (e.g.,
  the GOSA downloadable-data page, a Georgia Insights dashboard export)
- **Retrieved**: date (or "unknown — predates provenance tracking")
- **Method**: manual download / scripted fetch / emailed export / unknown

## Step 7: Generate File Checksums

Generate SHA-256 checksums for all bronze data files. These allow downstream steps (transform, audit) to detect when bronze files have changed since the structure report was generated.

```bash
uv run python -c "
import hashlib
from pathlib import Path

bronze_dir = Path('data/bronze/$0/$1/$2')
for path in sorted(bronze_dir.iterdir()):
    if path.is_file() and not path.name.endswith('.md'):
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f'{path.name}: {sha256}')
"
```

Include the results in the report (see Step 8).

## Step 8: Document Findings

Write the report to `data/bronze/$0/$1/$2/bronze-data-structure.md`.

Use this format:

```text
# $2 — Bronze Data Structure

## Overview

- Topic: $2
- Source: $1
- Files: {count} files spanning {year_range}
- Unreadable files: {list or "none"}
- Year representation: {description of how year is identified — column name and format, or filename pattern}
- Filename-to-data year offset: {e.g., "filename year = data year + 1" or "same" or "no year column to compare"}
- Detail levels: {e.g., state, district, school}
- Percentage scale: {0–100 or 0–1, noting which columns}
- Checksums generated: {date}

## Source Provenance

- **Source URL**: {url or "unknown — predates provenance tracking"}
- **Retrieved**: {date or "unknown"}
- **Method**: {manual download / scripted fetch / unknown}

## File Checksums

Generated: {current date}

| File | SHA-256 |
|------|---------|
| 2024.xlsx | a1b2c3d4... |
| 2023.xlsx | e5f6g7h8... |
| ... | ... |

## Excel Sheet Structure

{Only include this section for Excel files. Omit entirely for CSV-only topics.}

| File(s) | Sheets | Notes |
|---------|--------|-------|
| 2020-2024 | Sheet1 (Data) | Single data sheet |
| 2015-2019 | District (Data), School (Data), Legend (Metadata) | Data split across two sheets; Legend defines suppression codes |

{Note any changes in sheet structure across files and whether the transform needs to concatenate multiple sheets.}

## Summary

Brief summary of what distinguishes this dataset — focus on the specific measures and metrics it contains (e.g., SAT scores, percentage grade level mastery, graduation rates). These are the metrics a user would want to evaluate. Do not mention common fields like demographics or school identifiers that appear in most datasets.

## Eras

### Era 1: 2020-2024

| Column | Description |
|--------|-------------|
| SCHOOL_DSTRCT_CD | School district code |
| INSTN_NUMBER | Institution number |
| SUBGRP_DESC | Demographic subgroup name |
| SCORE | Test score value |
| ... | ... |

#### Sample Data

{output of df.sample(5)}

#### Statistics

{output of df.describe()}

#### Null Counts

{output of df.null_count()}

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| SUBGRP_DESC | All Students, Black, White, Hispanic, ... |
| GRADE_LEVEL | 9, 10, 11, 12 |
| ... | ... |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| SCORE | *, TFS |
| PCT_MEETING | *, N/A |
| ... | ... |

### Era 2: 2007-2019

{same sections as above}

## ETL Considerations

Important points to consider when transforming this bronze data to gold, including:
- Data quality issues or inconsistencies to watch out for
- Column name changes across eras that could cause mapping errors
- Values that need special handling (e.g., suppressed data markers, unusual null representations)
- Geography column formats (e.g., are FIPS codes zero-padded strings or bare integers?)
- Anything that could make the transformation inaccurate if not handled carefully

## Gold Schema Classification

For each bronze column (across all eras), classify its role in the gold star schema:

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| SCHOOL_DSTRCT_CD | fact_key | district_code | FK to districts dimension |
| INSTN_NUMBER | fact_key | school_code | FK to schools dimension |
| SCHOOL_DSTRCT_NM | dimension_attribute | — | district_name in districts dimension |
| INSTN_NAME | dimension_attribute | — | school_name in schools dimension |
| SUBGRP_DESC | fact_key | demographic | FK to demographics dimension (omit if always "All Students") |
| {metric columns} | fact_metric | {topic_specific_name} | {type and scale notes} |
| {category columns} | fact_categorical | {snake_case_name} | {normalization notes} |
| {columns not needed} | not_in_gold | — | {reason} |

**Gold roles:**
- `fact_key` — Foreign key column retained in the fact table
- `fact_metric` — Numeric measurement (count, score, rate) in the fact table
- `fact_categorical` — Topic-specific categorical column in the fact table (e.g., test component, subject)
- `dimension_attribute` — Descriptive attribute stored in a dimension table, NOT in the fact table
- `not_in_gold` — Column excluded from gold entirely (e.g., redundant identifiers, constant values)
```

## Rules

- Do not edit any bronze data files
- Only create/edit `data/bronze/$0/$1/$2/bronze-data-structure.md`
- If any bronze files are replaced or updated, regenerate the File Checksums section with fresh SHA-256 hashes and an updated generation date
