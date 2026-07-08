# district_filings — Bronze Data Structure

## Overview

- Topic: district_filings
- Source: federal_justice (FJC Integrated Database — IDB — **criminal defendant** filings/terminations)
- Files: 2 tab-delimited text zips (one per period) + 2 codebook PDFs
- Unreadable files: none (both zips pass CRC; both `.txt` members parse as tab-delimited). **`cr96on_0.zip` uses Deflate64** ("enhanced-64k") — see ETL #1.
- Year representation: **inside the data** — `cr96on.txt` has an explicit `FISCALYR` column (values 1996–2026); `cr70to95.txt` has no fiscal-year column, so the reporting year is derived from `filedate` / `termdate` / `TAPEYEAR`. Records are keyed to filing and termination events, so a filing-year and a termination-year are both derivable.
- Filename-to-data year offset: **N/A** — the file basenames encode the *period span* (`cr70to95`, `cr96on`), not a single year.
- Detail levels: **defendant-level microdata** (one row per federal criminal defendant per case), **national coverage**; a **circuit + district** key isolates Georgia's three districts. Gold target is `federal_district × year` aggregation, filtered to GA.
- Percentage scale: N/A — no percentage columns; values are counts, codes, dates, sentence terms (months), and fine amounts (dollars).
- Checksums generated: 2026-07-04

## Source Provenance

- **Source URL**: hub <https://www.fjc.gov/research/idb>; Research Guide
  <https://www.fjc.gov/sites/default/files/IDB-Research-Guide.pdf>. The two
  criminal-dataset landing pages (reached via the "Criminal Data" filter) are
  <https://www.fjc.gov/research/idb/criminal-defendants-filed-and-terminated-sy-1970-through-fy-1995>
  and <https://www.fjc.gov/research/idb/criminal-defendants-filed-terminated-and-pending-fy-1996-present>.
  Files resolve under `https://www.fjc.gov/sites/default/files/idb/textfiles/` (tab-delimited zips) and `…/idb/codebooks/` (PDF codebooks).
- **Retrieved**: 2026-07-04 (UTC)
- **Method**: scripted fetch — `uv run python -m src.etl.criminal_justice.federal_justice.district_filings.download`. The IDB download buttons sit behind a Drupal *antibot* JavaScript widget; the downloader **bypasses it** by requesting the Views exposed filter as a plain GET query parameter (`?field_type_tid=6876` = Criminal Data), which returns the landing pages server-side, then scrapes the real file URLs. Full details in [`_provenance.md`](_provenance.md). **Zips are never extracted** — the transform must read members directly from the zips.
- **License**: US federal government work — public domain (17 U.S.C. §105). Cite Federal Judicial Center, Integrated Database. Defendant `NAME` is present in the raw text but is aggregated away and not carried to gold.

## File Checksums

Generated: 2026-07-04

| File | SHA-256 |
|------|---------|
| Criminal Code Book 1970-1995.pdf | dd9ef72aca6ec12c49d11d05f59371ae9f7a0959b736a8391ec920e1b821ad68 |
| Criminal Code Book 1996 Forward.pdf | f8baa660dfd7aa5dd8242149fbb46cfbfea2709f79a07c1019885f702034c4bf |
| cr70to95.zip | ec7a25822dbaca8a608f5a3ea532b88182ca1c917d0a9ce2fc0834b0fbfe12c7 |
| cr96on_0.zip | 70871ff0a3af082d0ad325e22bc6ea579d05fee57a6a3c3222579b0eeb340783 |

## Zip / Table Structure

Not Excel — each period zip bundles a single tab-delimited text member:

| Zip | Member | Uncompressed | Rows (excl. header) | Columns | Compression |
|-----|--------|--------------|---------------------|---------|-------------|
| `cr70to95.zip` (15.7 MB) | `cr70to95.txt` | 178,239,657 B (170 MB) | 1,420,711 | 39 | standard Deflate |
| `cr96on_0.zip` (252.8 MB) | `cr96on.txt` | 3,524,429,156 B (3.28 GB) | 6,299,908 | 144 | **Deflate64 (enhanced-64k)** |

Both members are **tab-delimited** with a header row. The two periods have
**different column layouts** (39 vs 144 columns) and their own codebook.

## Summary

The FJC Integrated Database criminal file is the authoritative national record
of **every federal criminal defendant filing/termination** in the U.S. district
courts, statistical year 1970 through the current fiscal year (updated
quarterly). Each row is one defendant in one case. The measurable user metrics
are **criminal filings and terminations** (counts by district-year), **offense
mix** (up to five filing offenses `FTITLE1–FTITLE5`/`FOFFCD1–FOFFCD5` and five
termination offenses `TTITLE1–TTITLE5`/`TOFFCD1–TOFFCD5`, with severity
`FSEV*`/`TSEV*`), **disposition type** (`DISP1–DISP5`), and **sentence imposed**
(`PRISTIM*`/`PRISTOT` prison months, `PROBMON*`/`PROBTOT` probation months,
`FINEAMT*`/`FINETOT` fines, `SUPVREL*` supervised release). Filing and
termination dates (`FILEDATE`, `TERMDATE`, `SENTDATE`, `DISPDATE`) give exact
timing. Georgia's three districts are filterable on `DISTRICT`.

Georgia defendant counts (`DISTRICT` ∈ {3E, 3G, 3J}):

| Period | GA-N (3E) | GA-M (3G) | GA-S (3J) |
|--------|-----------|-----------|-----------|
| SY1970–FY1995 (`cr70to95`) | 21,536 | 31,902 | 15,815 |
| FY1996–FY2026 (`cr96on`) | 80,277 | 45,937 | 43,188 |

## Eras

The partitions are the **two period files** (different layouts + codebooks), the
**statistical-year → fiscal-year** reporting-basis change, and the **circuit
recode** — not annual column churn within a period.

### Era 1: SY1970–FY1995 (`cr70to95.txt`, 39 columns)

Statistical years (SY, ending June 30) 1970–1991, a **15-month bridge in 1992**,
then fiscal years (FY, ending Sep 30) 1992–1995. No `FISCALYR` column; year comes
from `filedate`/`termdate`/`TAPEYEAR`.

| Column | Description |
|--------|-------------|
| `CIRCUIT`, `DISTRICT`, `OFFICE`, `DOCKET`, `DEFNO` | Case/defendant key. **GA `DISTRICT`: 3E = Northern, 3G = Middle, 3J = Southern.** `CIRCUIT` = 11 from SY82 (Georgia was in the 5th Circuit before the 1981 split — pre-SY82 `CIRCUIT` = 5). |
| `filedate`, `termdate`, `INTERVAL` | Filing date, termination date, and interval between them. |
| `PROCCODE`, `FOFFCODE`, `TOFFCODE`, `MAJOROFF` | Procedural code; filing/terminating offense code; major offense. |
| `MOFFLVL`, `TOFFLVL` | Filing / terminating offense level (severity). |
| `SENTCAT`, `SENTSTAT`, `SENTTYPE`, `PRISONMO`, `PROBMO`, `FINE` | Sentence category/status/type; **prison months, probation months, fine**. |
| `SEX`, `RACE`, `BIRTHYR`, `MARITAL`, `EDUCAT`, `PRIORREC` | Defendant demographics + prior record. |
| `JUDGE`, `COUNSEL`, `DUPDEF`, `RULE20`, `TAPEYEAR`, `NAME` | Judge, counsel type, duplicate-defendant flag, Rule 20 transfer, tape year, name (**PII — aggregate away**). |

### Era 2: FY1996–present (`cr96on.txt`, 144 columns)

Explicit `FISCALYR` (1996–2026 in this snapshot; FY2026 is a partial year — the
DB updates quarterly). Richer layout carrying **up to five filing and five
termination offenses** and per-count sentencing.

| Column group | Columns | Description |
|--------------|---------|-------------|
| Key | `FISCALYR`, `CIRCUIT`, `DISTRICT`, `OFFICE`, `DOCKET`, `DEFNO`, `CTDEF` | **GA `DISTRICT`: 3E/3G/3J** (94 distinct district codes nationally). |
| Case status | `STATUSCD`, `FUGSTAT`, `TYPEREG`, `TYPETRN`, `TYPEMAG`, `MAGDOCK`/`MAGDEF` | Status, fugitive status, registration/transfer/magistrate type. |
| Dates | `FILEDATE`, `PROCDATE`, `APPDATE`, `DISPDATE`, `SENTDATE`, `TERMDATE` | Filing, processing, appointment, disposition, sentencing, termination. |
| Filing offenses (×5) | `FTITLE1–5`, `FOFFLVL1–5`, `FOFFCD1–5`, `D2FOFFCD1–5`, `FSEV1–5` | Up to five charged offenses: statute title, level, offense code, severity. |
| Termination offenses (×5) | `TTITLE1–5`, `TOFFLVL1–5`, `TOFFCD1–5`, `D2TOFFCD1–5`, `TSEV1–5` | Up to five offenses of conviction. |
| Disposition/sentence (×5) | `DISP1–5`, `PRISTIM1–5`, `PRISCD1–5`, `PROBMON1–5`, `PROBCD1–5`, `SUPVREL1–5`, `FINEAMT1–5` | Per-count disposition, prison time, probation months, supervised release, fine. |
| Sentence totals | `PRISTOT`, `PROBTOT`, `FINETOT` | **Total prison months, probation months, fine dollars.** |
| Counts-of-counts | `CTFIL`, `CTFILWOR`, `CTFILR`, `CTTR`, `CTTRWOR`, `CTTRR`, `CTPN`, `CTPNWOF` | Number of counts filed / terminated / pending. |
| Other | `COUNTY`, `TRANDIST`/`TRANOFF`/`TRANDOCK`/`TRANDEF`, `FJUDGE`/`TJUDGE`, `FCOUNSEL`/`TCOUNSEL`, `SOURCE`, `VER`, `LOADDATE`, `TAPEYEAR`, `NAME` | County code (see ETL #6), transfer keys, judge/counsel, load metadata, name (**PII**). |

## ETL Considerations

1. **`cr96on.zip` is Deflate64** ("enhanced-64k"). Python's stdlib `zipfile`
   **cannot** decompress it (`NotImplementedError: That compression method is
   not supported`). Read it with a Deflate64-capable path — system `unzip -p`
   streamed into polars, `libarchive`, or a `stream-inflate64`/`zipfile-deflate64`
   backport. `cr70to95.zip` is standard Deflate (stdlib `zipfile` works). **Never
   extract to disk** (provenance contract) — stream the member.
2. **Read as tab-delimited with a header row** (`separator="\t"`). Both files
   are wide-but-typed; select only the gold-relevant columns. `cr96on.txt` is
   ~3.3 GB uncompressed / 6.3 M rows — stream or use a lazy scan.
3. **Filter to Georgia by `DISTRICT` ∈ {3E, 3G, 3J}** (Northern/Middle/Southern);
   both codebooks use identical GA codes. Do **not** filter on `CIRCUIT`: it is
   5 for Georgia before SY82 and 11 after (the 11th Circuit split from the 5th
   in 1981), so a `CIRCUIT = 11` filter would silently drop GA's 1970–1981 rows.
4. **Two layouts** (39 vs 144 columns) with different column names for the same
   concepts (e.g. `PRISONMO`/`PROBMO`/`FINE` in Era 1 vs `PRISTOT`/`PROBTOT`/
   `FINETOT` in Era 2; single offense code vs five). Harmonize per era; do not
   assume a shared schema.
5. **Choose filing-year vs termination-year explicitly.** A "criminal filings"
   metric counts rows by filing year (`filedate`/`FILEDATE`); a "terminations"
   metric counts by `termdate`/`TERMDATE`. `FISCALYR` (Era 2 only) is the
   reporting fiscal year. Densify to a full district×year grid; missing
   district-years in a complete census are **true zeros**.
6. **`COUNTY` is unreliable for criminal data.** Era 2 has a `COUNTY` column but
   the IDB Research Guide flags criminal county coding as sparse/inconsistent;
   the blueprint (source #17) treats the criminal IDB as having **no usable
   county code**. Serve at **federal-district grain**, not county — do not join
   `COUNTY` to the county-FIPS dimension without separate verification.
7. **Sentence terms & sentinels.** Prison/probation months and fines use IDB
   sentinel codes for life/indeterminate/unknown (see codebooks) — NULL these
   before averaging. Offense/disposition/demographic fields are coded integers
   or short codes with value labels in the period codebook; a per-era recode map
   is required if any reach gold as categoricals.
8. **Grain is one defendant-case.** Aggregating to `federal_district × year`
   yields defendant filing/termination counts and distributional metrics (mean
   prison months, offense mix, disposition share). District ≠ county —
   **sub-state, non-county** grain (see Gold Schema Classification).
9. **1992 15-month bridge.** The reporting basis shifted from statistical year
   (SY, July–June) to fiscal year (FY, Oct–Sep) around 1992 with a 15-month
   transition; counts spanning that boundary are not directly comparable
   year-over-year. Document the break.

## Gold Schema Classification

Proposed gold grain: **federal_district × year** (aggregated from national
defendant-level microdata, filtered to GA districts 3E/3G/3J). This is a
**federal-district grain**, distinct from the county-FIPS grain used by most
criminal_justice topics — decide the district-grain serving model before
building (blueprint source #17). Pairs naturally with the USSC
`district_sentences` topic (same district grain).

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| `DISTRICT` | fact_key | federal_district | keep {3E,3G,3J}; map to GA-N/GA-M/GA-S |
| `FISCALYR` / `filedate`/`FILEDATE` / `termdate`/`TERMDATE` | fact_key | year | choose filing-year and/or termination-year basis; document |
| (row count) | fact_metric | defendants_filed / defendants_terminated | count of defendant rows; unit: count; **key_metric candidate** |
| `PRISTOT` / `PRISONMO` | fact_metric | mean/median_prison_months | NULL life/indeterminate sentinels first |
| `PROBTOT` / `PROBMO`, `FINETOT` / `FINE` | fact_metric (optional) | probation_months, fine_amount | probation months; fine dollars (currency) |
| `DISP1`/`DISP*` | fact_categorical (optional) | disposition_type | recode from codebook value labels |
| `TOFFCD1`/`FOFFCD1` / `MAJOROFF` | fact_categorical (optional) | primary_offense | offense-of-conviction / filing offense mix |
| `SEX`, `RACE`, `BIRTHYR`/age | fact_categorical → demographic | demographic | Era 1 only carries demographics; map to demographics dimension if published |
| `CIRCUIT` | not_in_gold | — | redundant with district; changes 5→11 at SY82 (do not filter on it) |
| `COUNTY` | not_in_gold | — | unreliable for criminal IDB (ETL #6) |
| `NAME`, `DOCKET`, `DEFNO`, `JUDGE`/`FJUDGE`/`TJUDGE`, `COUNSEL`, transfer/magistrate keys | not_in_gold | — | PII / within-case identifiers / operational detail below gold grain |
| offense-detail counts-of-counts, load metadata (`SOURCE`,`VER`,`LOADDATE`,`TAPEYEAR`) | not_in_gold | — | not aggregated |
