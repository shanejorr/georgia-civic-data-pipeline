# enrollment_by_grade — Bronze Data Structure

## Overview

- Topic: enrollment_by_grade
- Source: georgiainsights
- Files: **66 CSVs** = the two FTE snapshot cycles merged into one topic:
  - **Fall (October Cycle 1, `-1` suffix):** 34 files spanning fiscal years
    2010-2026 (one District CSV + one School CSV per fiscal year, 17 years × 2).
  - **Spring (March Cycle 3, `-3` suffix):** 32 files spanning fiscal years
    2010-2025 (16 years × 2).
- Unreadable files: none.
- This topic is the union of the two former period-split topics
  `enrollment_october_grade` (fall) and `enrollment_march_grade` (spring). The
  snapshot period — previously encoded only in the topic name — is folded into
  an `enrollment_period` column (`fall` / `spring`), matching the period
  vocabulary of the GOSA `enrollment_by_grade_level` topic.
- Year representation: encoded in the filename
  (`...Fiscal Year{YYYY}-{1|3} {District|School}.csv`); also embedded in the
  in-file preamble (`FTE Enrollment by Grade Level(PK-12) - Fiscal Year
  {YYYY}-{1|3} Data Report`). No year column inside the data itself.
- Period representation: encoded in the filename cycle suffix — `-1` = October
  Cycle 1 = **fall**; `-3` = March Cycle 3 = **spring**. Also confirmable from
  the preamble caption (October vs March date) and the `-{1|3}` in the
  preamble title line.
- Filename-to-data year offset: same. Per Georgia DOE convention, fiscal year
  YYYY = school year ending in YYYY. `Fiscal Year 2010-1` is the October 2009
  count (fall of the 2009-2010 school year); `Fiscal Year 2010-3` is the March
  2010 count (spring of the same year).
- Detail levels: state (single State-Wide Total row at end of every file),
  district (District file rows + the per-district `System Total` rows in the
  School file), school (per-school rows in the School file).
- Percentage scale: N/A — every metric is an enrollment count (Int64 ≥ 0).
- Checksums generated: 2026-05-22 (carried over from the two source topics; the
  CSV bytes are unchanged — only the directory location changed).

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads
  (https://georgiainsights.gadoe.org/data-downloads/) — exact acquisition-time
  page URL not recorded.
- **Retrieved**: unknown — predates provenance tracking.
- **Method**: manual download (assumed; not recorded at acquisition time).

## File Checksums

Generated: 2026-05-22. SHA-256 unchanged from the two source topics (files were
relocated, not re-acquired).

### Fall (October Cycle 1, `-1`)

| File | SHA-256 |
|------|---------|
| FTE Enrollment by Grade Fiscal Year2010-1 District.csv | d4c54c35859c02d25a5807a143f18bda0ee1a6258b168ceb8711b29c2bf00862 |
| FTE Enrollment by Grade Fiscal Year2010-1 School.csv | 240661628371efd270d9bd2b7e4f7503b156b0e9b4ba13f8c8ad83f2e4a3db1f |
| FTE Enrollment by Grade Fiscal Year2011-1 District.csv | 3dbb38684f5aeddb386a133e06be4b3249df3c149f69eb6e56e4da43ecb55c91 |
| FTE Enrollment by Grade Fiscal Year2011-1 School.csv | 5520fcee4300abdfcec684050b53cb5cf9a54a08b2b10298351e3f0be2e6769e |
| FTE Enrollment by Grade Fiscal Year2012-1 District.csv | da5f13306fa3f8a591570e51c2d67bd068c38856dc775e624d5ca9d09fd890d1 |
| FTE Enrollment by Grade Fiscal Year2012-1 School.csv | 99563c28574fa3a16192b2631b3414cbd0adb334468c1bb1bebcc152394af7ab |
| FTE Enrollment by Grade Fiscal Year2013-1 District.csv | d57f2d30bdac8379e3a3dbc9b6fca3b6ce00748e4c1ef0d8f12d11ec0939eacf |
| FTE Enrollment by Grade Fiscal Year2013-1 School.csv | d2363f0e146a443b19deebac15a797d654b05794820e790c75db77ac697fbe5b |
| FTE Enrollment by Grade Fiscal Year2014-1 District.csv | 2c41cb40b32cdcd690c8ffb6d32bdd928b0c6e16736fb18d7ce5230ea8ccd464 |
| FTE Enrollment by Grade Fiscal Year2014-1 School.csv | 4f0476958c949f29a4e7e76eb90a65f1ccb0f1449714311c360708b8f2cb7f10 |
| FTE Enrollment by Grade Fiscal Year2015-1 District.csv | 2e56faeaaeb0031861f1d78b3415add7e13e18903bd239be760a6e5a1be6ba8d |
| FTE Enrollment by Grade Fiscal Year2015-1 School.csv | 6530e4b01c0a678830ae939628c7239b01cd550dff90ed4a92ae99a300d0c423 |
| FTE Enrollment by Grade Fiscal Year2016-1 District.csv | 13bbcdb413d6290b3447a5a3aacfe74eccb769c0ae4fbcda32dd961723211b6d |
| FTE Enrollment by Grade Fiscal Year2016-1 School.csv | 55d2a6bbf078938616bdca0f07ae94cd3d3b82c2b8fe40a8824c82c658665f13 |
| FTE Enrollment by Grade Fiscal Year2017-1 District.csv | ae1e6e9dc2e11c88c6393f1b6ed2d4c93775404d77bf0ac945d0fa9262b2583b |
| FTE Enrollment by Grade Fiscal Year2017-1 School.csv | e00822c2821bba6b5465bb4ff28f5dcf8660ffb21f4b9c0f1c284f7ec8d6e40c |
| FTE Enrollment by Grade Fiscal Year2018-1 District.csv | 8270397141094afe6b86c870fc9777b3b9e62dccb7428fc89625c83430ef52e2 |
| FTE Enrollment by Grade Fiscal Year2018-1 School.csv | 8777f27f291f0d53eb3b359f498e3620822cb2346a947f4bb2487491a78df01a |
| FTE Enrollment by Grade Fiscal Year2019-1 District.csv | 4bbff38bf5326503a37050a3fe4acffa030a93b1e6ff2b87bac39d0b36d785a5 |
| FTE Enrollment by Grade Fiscal Year2019-1 School.csv | 561bba9a63e551b6770de0cad0a1442cbe3c601d4c461b1e3e3109e56a5a92b7 |
| FTE Enrollment by Grade Fiscal Year2020-1 District.csv | 8bc3f73c5a1bb04a0cb8dd225b7af93afb7fb0c5392e1d7ffd78f4c9089de4f8 |
| FTE Enrollment by Grade Fiscal Year2020-1 School.csv | 4fe9914bfcea92e50382db0516c7cae85fa8c24f978871a518b1748608e7ee41 |
| FTE Enrollment by Grade Fiscal Year2021-1 District.csv | 081d92883ba7f15ebe4e06fa4a7aacece99055d8c975f5d5e34205ed8426f5b6 |
| FTE Enrollment by Grade Fiscal Year2021-1 School.csv | 6313ab47ea1b0e68629d932e8a158e0a38763ecf721b74b2da9d1a8ff6b086d8 |
| FTE Enrollment by Grade Fiscal Year2022-1 District.csv | 02b527cae15685f0c7639d31b0d0d5a0b4c2c75a5156ce16c0f79b338f032dc0 |
| FTE Enrollment by Grade Fiscal Year2022-1 School.csv | a175dd04e1a5d0623272f891b06a03cfa38c00119faf745d3410ffa1a8f6bdc0 |
| FTE Enrollment by Grade Fiscal Year2023-1 District.csv | 88ae1a906afca06b6f2297b3d1a6a1d728b673eb490bb94d3b170f520817265a |
| FTE Enrollment by Grade Fiscal Year2023-1 School.csv | 6131c073d0a0c4934255004cdc61689870aad392112d82e0c299f329104d810c |
| FTE Enrollment by Grade Fiscal Year2024-1 District.csv | 49bb875bdb9b83a37e91f3fe850e0419b4b067c9d52ffc6db4c8b4d723833b05 |
| FTE Enrollment by Grade Fiscal Year2024-1 School.csv | 1a929ce9b0371900b719a45229c028bdbc25773208a4170c96b4f2f78a47c2da |
| FTE Enrollment by Grade Fiscal Year2025-1 District.csv | ab7c499085ee1db027eb8c5f6f002f79dcfb5c93145d7e157b133592585af7ae |
| FTE Enrollment by Grade Fiscal Year2025-1 School.csv | 02de54ce36bbeb52158de4fc8d55584e838647b88cff1ee6ae560971a9feb90a |
| FTE Enrollment by Grade Fiscal Year2026-1 District.csv | 7ba7f63018658c32ca09c7ba684d07f84be10acbbf71e341d11c7efbe456d9c5 |
| FTE Enrollment by Grade Fiscal Year2026-1 School.csv | e1aa4723bf029061600c60ce69ffd77ff6681f6297dab9288987bc3f8206eade |

### Spring (March Cycle 3, `-3`)

| File | SHA-256 |
|------|---------|
| FTE Enrollment by Grade Fiscal Year2010-3 District.csv | 2398f0073cb198ec881d9265401dba44fe0a6ddd03aaa37350544666bd4a2eef |
| FTE Enrollment by Grade Fiscal Year2010-3 School.csv | 31f37e4fc90eba74df9a53bddce8de45a4f46004238420e8675234c05aebf0a7 |
| FTE Enrollment by Grade Fiscal Year2011-3 District.csv | b73b23029de3708f4a5634fc7e55870a8a6ec234057616ef5d4ab152e0c282b4 |
| FTE Enrollment by Grade Fiscal Year2011-3 School.csv | 636bf09ac1e938a89b099445abcdeda967200ac69a3012ba30d435f1cff4618d |
| FTE Enrollment by Grade Fiscal Year2012-3 District.csv | adfc415bf44b33d49c1d471539ed0ec108af716e3a7d2c00c84ec8e53a602efa |
| FTE Enrollment by Grade Fiscal Year2012-3 School.csv | d4f21e75395c9f720e11514a8c6178e05a7623a48dc6119822c5ab92e18a9a8e |
| FTE Enrollment by Grade Fiscal Year2013-3 District.csv | 40d9a29d01a5c459f1749c37eb69f04a6b54392a3062011857e39fed037abd6a |
| FTE Enrollment by Grade Fiscal Year2013-3 School.csv | 078643e620faecc5829434ef80d5c98ae5068dcf79b48163e927b6bb173d3052 |
| FTE Enrollment by Grade Fiscal Year2014-3 District.csv | f3a3a3bda54cdeafe34b466be04f6578d07c5aadf39f5910e283c52fd91cd559 |
| FTE Enrollment by Grade Fiscal Year2014-3 School.csv | b02e19e5115ef60cb0bf5e7ca448903946304c28f2ecec795b92d9bdbd8aa7e7 |
| FTE Enrollment by Grade Fiscal Year2015-3 District.csv | aba7bba004382815ec42c2985068e9a62ccad3d8fae8cb07294a1ea4c8cc65e7 |
| FTE Enrollment by Grade Fiscal Year2015-3 School.csv | bd2fbc3e7de91b951524afb264dc56fdf60f49bb0c6a1768304c1da844c68ee3 |
| FTE Enrollment by Grade Fiscal Year2016-3 District.csv | 23d4d601b46f913563c6849885e0b4301fcfc7abc9c2916514da8eb1639b1074 |
| FTE Enrollment by Grade Fiscal Year2016-3 School.csv | 070fa1fa465183017b999755d9820b0f757e4ffdf50229f1e4f609167c8cb519 |
| FTE Enrollment by Grade Fiscal Year2017-3 District.csv | d017382202dd0ee0c776523e5d1f2958900892e7d90ceac8433f845681802262 |
| FTE Enrollment by Grade Fiscal Year2017-3 School.csv | 730f60cbe814b220f2a6aa3b9bfc6dfba352672a4056542a512f9ceb991bcf08 |
| FTE Enrollment by Grade Fiscal Year2018-3 District.csv | 7b0ad5596567d3ed117c9d65303cb30c0054b2398b4ed3366182cffe21e8d3ae |
| FTE Enrollment by Grade Fiscal Year2018-3 School.csv | 1968a8ea78b7e91750b738c05aedda96f973d2d56aab68f216325611d2d7d255 |
| FTE Enrollment by Grade Fiscal Year2019-3 District.csv | 3f6e48ab431bcc06ab2b08d7e7d5fc70a2521c0957d74427cdde08fe9cf7bd71 |
| FTE Enrollment by Grade Fiscal Year2019-3 School.csv | b1c1d7786ed0f7e49b07b8b166392eaae9b85bc9434f8baddefa4c9286cff323 |
| FTE Enrollment by Grade Fiscal Year2020-3 District.csv | 762c0787d4df52e18862de4ccaf6cf8e2ec8e410f6fb77263b91bceff59ce26d |
| FTE Enrollment by Grade Fiscal Year2020-3 School.csv | 537a05945f7db16b784f3182c4a530942cc91a0ca65c3b4629d788f3b0551000 |
| FTE Enrollment by Grade Fiscal Year2021-3 District.csv | 57e4ac2ec6f98153320f5ddab8ea92d4c583ba8f5802e46e7a795de887f8952b |
| FTE Enrollment by Grade Fiscal Year2021-3 School.csv | a44c0fe253e497cb4bc317d4ad8ac7f9c2ed96e20fe3fce246fa6b3ac9e52ea9 |
| FTE Enrollment by Grade Fiscal Year2022-3 District.csv | 1c4d94bc165a7e6a54a6cba2909bef6bb9da16806d973cd025f6d3201e894d03 |
| FTE Enrollment by Grade Fiscal Year2022-3 School.csv | fd061da66b60732927e6843b2453626e819bb9363ac291eb77f1bc997b990871 |
| FTE Enrollment by Grade Fiscal Year2023-3 District.csv | 8da7d110d7aec16a231505cc4f5c302d22311ba022768a8553f31c33805f2f25 |
| FTE Enrollment by Grade Fiscal Year2023-3 School.csv | 9d2b6e474c424ca08c0d01392eb410e86c0adbd2cd48df28edb879c7031ff99a |
| FTE Enrollment by Grade Fiscal Year2024-3 District.csv | d0fb210ef1bed0578deb08c67b3cd0ea94118b851f15997ad3ec148425698342 |
| FTE Enrollment by Grade Fiscal Year2024-3 School.csv | 86f0b17a67c8396e5235155866057cf4977f1474c7cd1250d30b3142611c7ae3 |
| FTE Enrollment by Grade Fiscal Year2025-3 District.csv | 863768e473c8e4b9a25afa95a73f6e4b3447d115d9a5cbe6cdce81a0ab3bc4e2 |
| FTE Enrollment by Grade Fiscal Year2025-3 School.csv | bc6631bb5a2bbb4b1ef8b7a2fd365746c507902354fd74ada548481b995ff4d8 |

## Summary

GaDOE FTE (Full-Time Equivalent) enrollment counts for every Georgia public
school and district, broken out by grade level (Pre-K, Kindergarten,
Grades 1-12). The single metric is **headcount enrollment per grade per entity
per snapshot period**. Georgia takes two FTE counts per school year for
funding-formula calculations: the **October** count (first Tuesday of October,
Cycle 1, fall) and the **March** count (third Tuesday of March, Cycle 3,
spring). This topic carries both, distinguished by `enrollment_period`. There
is no demographic breakdown (no race, gender, or special-population columns) —
the only dimensions are geography (district/school), grade, and the snapshot
period.

Each file also contains a pre-aggregated `Total` column equal to the row-wise
sum of the 14 grade columns (verified bit-exact for every row in every file of
both periods); this is the same `Total` enrollment used in many other GaDOE
topics' denominators.

The two snapshot families are structurally identical — identical column
headers, identical sheet layout, identical row-type conventions, and the same
quirks (column-header whitespace, the `SChool` typo, the state-schools era
split). They differ only in the filename suffix (`-1` fall vs `-3` spring), the
preamble caption (October vs March date), and the exact bounds of the
state-schools split era (see ETL Considerations).

## Eras

### Single layout, two periods (fall 2010-2026; spring 2010-2025)

Column names are **identical across all years and both periods** for both the
District file (17 columns) and the School file (18 columns — adds
`SChool Name`). The District and School files differ only in (a) the presence
of the `SChool Name` column and (b) some leading-whitespace differences in
column headers (see ETL Considerations).

#### District file columns (17 columns)

Column header strings shown verbatim — note the leading spaces:

| Column (verbatim) | Description |
|-------------------|-------------|
| `System ID` | GOSA district code. 3 digits for standard districts (e.g., `601`), 7 digits for state charter / state specialty schools (e.g., `7820108`). Also used as a sentinel: blank/whitespace value identifies the State-Wide Total row at the end of the file. |
| `' System Name'` (leading space) | District name in title case (e.g., `Appling County`). `State-Wide Total` for the state row. **Null/empty** in the split era for the three state schools (System IDs `7991893/4/5`). |
| `' Total'` (leading space) | Int64. Total FTE enrollment across all grades; equals the row-wise sum of the 14 grade columns (verified). |
| `' Grade PK'` (leading space) | Int64. Pre-Kindergarten enrollment count. |
| `Grade KK` | Int64. Kindergarten enrollment count. |
| `' Grade 01'` (leading space) | Int64. Grade 1 enrollment. |
| `Grade 02` ... `Grade 12` | Int64. Grades 2-12 enrollment counts. |

#### School file columns (18 columns)

Same as District plus `SChool Name`. Subtle whitespace differences vs the
District file (`'Grade PK'` no leading space in School vs `' Grade PK'` with
leading space in District):

| Column (verbatim) | Description |
|-------------------|-------------|
| `System ID` | Same as District file. |
| `' System Name'` | Same as District file (null in District file vs `''` empty string in School file for the split-era state schools — both mean "missing name"). |
| `' SChool Name'` | School name in title case, prefixed with the 4-digit GOSA school code: `NNNN-School Name`. **Special values:** `' System Total'` (with leading space) for per-district aggregate rows; `'  '` (whitespace) on the State-Wide Total row. **Anomaly:** in the split era the three state schools appear as `1893-N/A`, `1894-N/A`, `1895-N/A`. |
| `' Total'` | Int64. Same as District file. |
| `Grade PK` (no leading space) | Int64. Pre-Kindergarten enrollment. |
| `Grade KK` ... `Grade 12` | Int64. Kindergarten and Grades 1-12. |

#### Row Counts Per File

(School-file totals **include** the single State-Wide Total row at the end of
every file plus one `System Total` row per district.)

##### Fall (`-1`)

| Year | District rows (incl. State-Wide) | School rows (incl. all aggregates) | School rows: per-district `System Total` | School rows: actual schools |
|-----:|----:|----:|----:|----:|
| 2010 | 187 | 2,458 | 186 | 2,271 |
| 2011 | 193 | 2,485 | 192 | 2,292 |
| 2012 | 197 | 2,489 | 196 | 2,292 |
| 2013 | 199 | 2,474 | 198 | 2,275 |
| 2014 | 199 | 2,462 | 198 | 2,263 |
| 2015 | 199 | 2,466 | 198 | 2,267 |
| 2016 | 204 | 2,468 | 203 | 2,264 |
| 2017 | 208 | 2,500 | 207 | 2,292 |
| 2018 | 214 | 2,514 | 213 | 2,300 |
| 2019 | 214 | 2,516 | 213 | 2,302 |
| 2020 | 216 | 2,516 | 215 | 2,300 |
| 2021 | 222 | 2,528 | 221 | 2,306 |
| 2022 | 224 | 2,537 | 223 | 2,313 |
| 2023 | 227 | 2,541 | 226 | 2,314 |
| 2024 | 235 | 2,557 | 234 | 2,322 |
| 2025 | 235 | 2,558 | 234 | 2,323 |
| 2026 | 238 | 2,554 | 237 | 2,316 |

##### Spring (`-3`)

| Year | District rows (incl. State-Wide) | School rows (incl. all aggregates) | School rows: per-district `System Total` | School rows: actual schools |
|-----:|----:|----:|----:|----:|
| 2010 | 187 | 2,457 | 186 | 2,270 |
| 2011 | 195 | 2,485 | 194 | 2,290 |
| 2012 | 197 | 2,488 | 196 | 2,291 |
| 2013 | 199 | 2,472 | 198 | 2,273 |
| 2014 | 199 | 2,463 | 198 | 2,264 |
| 2015 | 199 | 2,466 | 198 | 2,267 |
| 2016 | 204 | 2,467 | 203 | 2,263 |
| 2017 | 208 | 2,499 | 207 | 2,291 |
| 2018 | 214 | 2,513 | 213 | 2,299 |
| 2019 | 214 | 2,516 | 213 | 2,302 |
| 2020 | 216 | 2,516 | 215 | 2,300 |
| 2021 | 222 | 2,528 | 221 | 2,306 |
| 2022 | 224 | 2,537 | 223 | 2,313 |
| 2023 | 227 | 2,541 | 226 | 2,314 |
| 2024 | 235 | 2,557 | 234 | 2,322 |
| 2025 | 235 | 2,558 | 234 | 2,323 |

Each year/period's District file has exactly one State-Wide Total row at the
end; each School file has one State-Wide Total row plus one `System Total` row
per district. The District file row count minus 1 = the School file
`System Total` count, every year/period — verified.

#### Suppression Markers

**None.** Verified cell-by-cell across all 66 files in both periods. The only
"non-numeric" value found in any column read as Utf8 is the literal `' '`
(single space) in `System ID` on the State-Wide Total row, a structural
sentinel, not a suppression marker. All grade columns and the `Total` column
are clean integer counts in every row of every file. (Enrollment headcounts are
not small-cell suppressed; suppression applies to rate metrics and demographic
breakdowns, neither of which exists here.)

## ETL Considerations

### File-Level Header Skip

Every CSV (both periods, both file types, every year) has the same 4-row
preamble before the column header row:

```text
Row 0: Georgia Department of Education
Row 1: FTE Enrollment by Grade Level(PK-12) - Fiscal Year YYYY-{1|3} Data Report
Row 2: "<Oct|October|March> D, YYYY... (FTE YYYY-{1|3})"
Row 3: (single space, not a truly blank line)
Row 4: System ID, System Name, ...   <-- actual column header
Row 5+: data rows
```

The transform reads with `pl.read_csv(..., skip_rows=4)` and verifies the
line-2 title + year before parsing.

### Period from the Cycle Suffix

`Fiscal Year YYYY-1` = October Cycle 1 = **fall**; `Fiscal Year YYYY-3` = March
Cycle 3 = **spring**. The transform parses the suffix from the filename (and
cross-checks it against the preamble cycle) and writes it to the
`enrollment_period` column with values `fall` / `spring` — matching the GOSA
`enrollment_by_grade_level` vocabulary. This is the only structural difference
between the two former topics; everything else is identical.

### Column Header Quirks (whitespace + typo)

Source column headers contain inconsistent leading whitespace and an embedded
typo (`SChool` not `School`). The transform strips every header at read; the
`SChool` typo is preserved because it is the real header. A rename-coverage
guard raises if any expected column is missing post-strip.

### Three Detail Levels Encoded Structurally

| Gold detail level | Source file | Identifying pattern |
|-------------------|-------------|---------------------|
| `state` | Either file (one kept) | `System ID` is whitespace-only / blank; row label is `State-Wide Total` |
| `district` | District file rows (excluding State-Wide) | `System ID` non-blank in the District file |
| `school` | School file only | `' SChool Name'` starts with `NNNN-` (i.e., not `System Total`, not whitespace) |

The transform reads district rows from the District file and school rows from
the School file; the School file's per-district `System Total` aggregate rows
are dropped (bit-equal to the District file rows, verified for every district
in every year/period). Both files publish an identical State-Wide Total row per
period; the transform keeps one copy.

### School Code Extraction

The 4-digit GOSA school code is the leading prefix of `' SChool Name'`
(`NNNN-Friendly Name`), extracted with `^(\d{4})-` and `zfill(4)`-padded
defensively. Verified across all years/periods: every actual school row matches
`^\d{4}-` (the only non-matches are aggregate rows, filtered out separately).
A failed extraction raises.

### State Schools (district 799) Era Split

The three state schools (`1893-Atlanta Area School for the Deaf`,
`1894-Georgia Academy for the Blind`, `1895-Georgia School for the Deaf`)
appear under two organizational structures depending on the year:

- **Consolidated under district `799`** with proper school names: fall
  2010-2011 and 2020-2026; spring 2010 and 2020-2025.
- **Split into three 7-digit pseudo-districts** `7991893`/`7991894`/`7991895`
  (school names `1893-N/A` etc., null/empty `System Name`): **fall 2012-2019;
  spring 2011-2019**. Note the boundary differs by one year between the two
  periods.

The transform preserves bronze identifiers as-is (district_code = the 7-digit
pseudo-code, school_code = `1893`/`1894`/`1895`) rather than remapping to 799 —
rewriting bronze IDs is discouraged. **Because IDs are never remapped, the
slightly different split boundary between the two periods needs no branching in
the transform** — it is documentation-only. Names are the dimension builder's
concern.

### Year + Period Come From the Filename, Not the Data

There is no `year`, `school_year`, or `period` column inside the data. The
transform injects `year` (parsed from the filename, cross-checked against the
preamble) and `enrollment_period` (parsed from the cycle suffix). Cast year to
`pl.Int32` per education domain.

### Total Equals Sum of Grades

The `Total` column is **always** the row-wise sum of the 14 grade columns
(verified bit-exact for every row in every file of both periods). It is
preserved as the `grade_level = 'all'` row in gold, and the
`all_equals_sum_of_grades` contract check re-asserts the identity on every
validation run.

### District Codes — Two Width Patterns

`System ID` is 3 digits (standard districts) or 7 digits (state charter /
specialty / state-school pseudo-districts). The transform uses `.str.zfill(3)`
(pads only if shorter; 7-digit codes pass through unchanged) and never
truncates.

### State-Wide Total Row Has Blank `System ID`

The State-Wide Total row has `System ID = ' '` (single space). The transform
identifies state rows by whitespace-only `System ID`, maps them to
`detail_level = state` with NULL district_code and school_code, BEFORE zfill so
the blank cannot mint a phantom district "000".

## Gold Schema

Long form, one row per `(year, district_code, school_code, enrollment_period,
grade_level)`:

| Gold column | Type | Source |
|-------------|------|--------|
| `year` | `pl.Int32` | Filename, cross-checked against preamble. |
| `district_code` | `pl.Utf8` | `System ID`; blank → NULL (state), `zfill(3)`. FK to districts dim. |
| `school_code` | `pl.Utf8` | 4-digit prefix of `' SChool Name'`; NULL for state/district rows. FK to schools dim. |
| `enrollment_period` | `pl.Utf8` | Cycle suffix: `-1` → `fall`, `-3` → `spring`. |
| `grade_level` | `pl.Utf8` | 14 grade columns + `Total`, normalized to `pk`/`k`/`01`..`12`/`all`. |
| `num_students` | `pl.Int64` | The 14 grade cells + `Total` cell, unpivoted. Renamed from the source topics' `student_count`. |

`detail_level` is carried internally for geography nulling / export splitting,
then dropped — it is implicit in the per-detail-level filename
(`states.parquet` / `districts.parquet` / `schools.parquet`). Output is split
per the education domain convention:

```text
data/gold/education/enrollment_by_grade/
  year=YYYY/
    states.parquet      # state-wide rows (both periods)
    districts.parquet   # district aggregate rows (both periods)
    schools.parquet     # school rows (both periods)
```

(The dimension joins live in `data/gold/education/_dimensions/`.)

## Provenance of This Merge

This topic supersedes the two former period-split topics:

- `enrollment_october_grade` → `enrollment_period = 'fall'`
- `enrollment_march_grade` → `enrollment_period = 'spring'`

The bronze CSV bytes are unchanged (relocated from the two source bronze dirs,
checksums identical). The transform was authored by merging the two source
transforms: a single shared body now threads `enrollment_period` (from the
cycle suffix) onto every row, renames the metric `student_count → num_students`,
and folds both snapshot families into one gold fact table. Every per-period
invariant carried over from the two source transforms' verification (see their
prior `bronze-data-structure.md` history): `Total == sum of 14 grades`,
School-file `System Total` rows bit-equal the District file, State-Wide twins
bit-equal across the District/School files, state = Σ districts, schools = Σ
district per grade — all re-asserted as contract quality checks, now grouped by
`enrollment_period`.
