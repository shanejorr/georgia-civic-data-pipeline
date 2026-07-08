# Data Review: postsecondary_c11_report

**Date**: 2026-06-10
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is accurate: every value-level trace (extremes, one entity per era, all 14
demographic groups for a full entity, suppression cells) matches bronze
exactly, the gold NULL-cell counts tie out to the documented bronze TFS counts
**exactly in every era** (8,174 / 17,908 / 72,857 / 9,317 / 9,482), and v1
parity is **MATCH — byte-identical with v1 gold**. The split Asian/PI
convention is verified positively (seven race buckets, including a separate
`pacific_islander`, sum exactly to the `all` total at state level 2011+). The
single Required Fix is documentation-only: the bronze-data-structure.md sample
tables for Eras 2–4 contain fabricated values that do not exist in bronze
(gold is unaffected — it matches bronze, not the doc).

## Manifest Verification

### Categorical map: `demographic`

| Column | Entries | Bronze seen | Unmapped | Status |
|---|---|---|---|---|
| demographic | 20 | 27 | 0 | PASS |

The 27 `bronze_values_seen` are exactly the union of the 14 Excel labels
(Eras 1–3; 13 in Era 1) and the 14 CSV tokens (Era 4), with `LEP` shared
between the two sets (14 + 14 − 1 = 27). Every label documented in
bronze-data-structure.md appears; no undocumented label appears. The
`map_used` is the effective slice of the shared `DEMOGRAPHIC_ALIASES`
(uppercased keys), so mixed-case Excel labels and uppercase CSV tokens hit the
same entries.

Full map review — every entry:

| Bronze (uppercased) | Gold | Correct? |
|---|---|---|
| TOTAL ALL | all | YES — Excel total row |
| TOTAL | all | YES — CSV total token |
| MALE | male | YES |
| FEMALE | female | YES |
| FREE REDUCED LUNCH | economically_disadvantaged | YES — FRL is the canonical economic-disadvantage proxy |
| FRL | economically_disadvantaged | YES |
| MIGRANT | migrant | YES |
| LEP | english_learners | YES — Limited English Proficiency |
| DISABILITY | students_with_disabilities | YES — Excel label for SWD |
| SWD | students_with_disabilities | YES |
| HISPANIC | hispanic | YES |
| TWO OR MORE RACE(S) | multiracial | YES |
| TWOORMORE | multiracial | YES — CSV token |
| AMERICAN INDIAN OR ALASKAN NATIVE | native_american | YES |
| NATIVE | native_american | YES — CSV token (per doc: American Indian / Alaskan Native) |
| ASIAN | asian | YES — split convention, see §2e below |
| BLACK | black | YES |
| WHITE | white | YES |
| PACIFIC ISLANDER | pacific_islander | YES |
| PACIFIC | pacific_islander | YES — CSV token |

- **2c contract cross-check**: `gold_values_produced` (14 values) equals the
  contract `enum` for `demographic` exactly. PASS.
- **2d unmapped**: `unmapped_count` = 0. PASS.

### 2e Asian / Pacific Islander conflation — PASS (split convention proven)

The skill's math test printed:

```
graduate_count: year=2022 total=114148 race_sum=114148 ratio=1.0000 -> CONFLATED
```

The mechanical `CONFLATED` label is a false positive here: the race sum
**includes a separate `pacific_islander` bucket** (buckets present: asian,
black, hispanic, multiracial, native_american, pacific_islander, white). Seven
buckets summing exactly to the total is the *positive* proof that the split
convention is correct — if bare "Asian" secretly contained PI, adding the
separate PI bucket would push the sum *over* the total. Per-year state-level
partition (both metrics):

```
2010: buckets=6 all_g=89284 race_g=88327 (diff 957) all_e=67479 race_e=66536 (diff 943)
2011-2018, 2020, 2022: diff 0 / 0 (exact)
2019: diff 8 / 8     2021: diff 1 / 1
```

2010 (Era 1, no PI group): the six buckets fall short by 957 graduates
(~1.1%), an order of magnitude more than the NHPI share (2011 state PI = 67 of
88,017 = 0.076%) — the residue is transition-year unreported-race students,
not a hidden PI fold-in, so bare `Asian` → `asian` is right. The Asian share
trend (2010: 3.659%, 2011 asian-only: 3.563%, 2011 asian+pi: 3.639%) cannot
discriminate (YoY noise exceeds the ~0.08pp PI delta), but remapping only 2010
to `asian_pacific_islander` would put a combined key alongside the split pair
within the same topic — forbidden by §5a/§5b — so `asian` is correct under the
standards regardless. Both structural facts are pinned as contract quality
checks (`pacific_islander_absent_in_2010`, `pacific_islander_present_2011_onward`).

### 2f Mutual exclusivity — PASS (single convention)

`gold_values_produced` contains `asian` and `pacific_islander` and no
`asian_pacific_islander` rollup. Single split convention throughout; no
double-counting possible.

### Row-count reconciliation

| Year | Bronze | × groups | Gold | Match |
|---|---|---|---|---|
| 2010 | 588 | 13 | 7,644 | YES |
| 2011 | 592 | 14 | 8,288 | YES |
| 2012 | 608 | 14 | 8,512 | YES |
| 2013 | 612 | 14 | 8,568 | YES |
| 2014 | 618 | 14 | 8,652 | YES |
| 2015 | 628 | 14 | 8,792 | YES |
| 2016 | 626 | 14 | 8,764 | YES |
| 2017 | 634 | 14 | 8,876 | YES |
| 2018 | 644 | 14 | 9,016 | YES |
| 2019 | 646 | 14 | 9,044 | YES |
| 2020 | 649 | 14 | 9,086 | YES |
| 2021 | 652 | 14 | 9,128 | YES |
| 2022 | 659 | 14 | 9,226 | YES |

Expansion factor is exactly the group count per era (13 in 2010, 14
elsewhere); `filtered` = 0 everywhere; all 13 cohort years present. Actual
parquet row total = **113,596** = manifest `total_gold`. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| School Year / SCHOOL_YEAR | year | MAPPED (in-file cohort year; Int32) |
| School District Code / SCHOOL_DISTRCT_CD | district_code | MAPPED (zfill(3), ALL → NULL) |
| School District Name / SCHOOL_DSTRCT_NM | — | CORRECTLY EXCLUDED (districts dimension) |
| School Code / INSTN_NUMBER | school_code | MAPPED (zfill(4), ALL → NULL) |
| School Name / INSTN_NAME | — | CORRECTLY EXCLUDED (schools dimension) |
| {Group} Total High School Graduates / {GROUP}_HS_GRADS | graduate_count | MAPPED (doc suggested `hs_grads`; canonical §16 name used instead — validator's canonical_vocabulary check passes) |
| {Group} …Enrolled in Postsecondary Institution / {GROUP}_IN_COLLEGE, TOTAL_ENROLLED_IN_COLLEGE | num_enrolled_in_college | MAPPED (sibling-pair name shared with postsecondary_c12_report; TOTAL's irregular column handled explicitly) |
| Demographic group label (merged header / column prefix) | demographic | MAPPED (unpivot; 20-entry alias slice) |
| #RPT_NAME (Era 4) | — | CORRECTLY EXCLUDED (constant; guarded == 'C11 Report Metrics') |
| REPORTING_YEAR (Era 4) | — | CORRECTLY EXCLUDED (publication year; enforced == filename year) |

No gold column lacks a bronze source (no fabrication). Note one deliberate,
documented deviation from the structure doc's ETL consideration #3: the doc
suggested emitting 2010 `pacific_islander` rows with NULL metrics; the
transform instead emits no 2010 PI rows (absent, not fabricated) — the better
call (no bronze source exists to NULL out) and pinned by two quality checks.

## Value-Level Spot Checks

All bronze cells below were read directly from the bronze files (pandas
`header=None` for Excel, all-string CSV read) — independent of the transform's
stitcher.

### Extreme rows first

| Trace | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|
| Global max graduate_count | 2024.csv state row: `TOTAL_HS_GRADS= 114148`, `TOTAL_ENROLLED_IN_COLLEGE= 72156` (SCHOOL_YEAR= 2022) | 2022 state all: 114148/72156 | MATCH |
| Global max num_enrolled_in_college | 2020.xlsx state row: `TotAll HS= 111296`, `TotAll COLL= 74876` (SY= 2018) | 2018 state all: 111296/74876 | MATCH |
| Era 1 state row | 2012.xlsx state: `89284 / 67479`, Asian `3267 / 2796` (SY= 2010) | 2010 state all 89284/67479; asian 3267/2796 | MATCH |
| Global min graduate_count (=10) | 2012.xlsx district 603 (Bacon County) ALL row: `FRL grads= '10'`, `FRL enrolled= 'TFS'` | 2010 district 603 economically_disadvantaged: 10 / None | MATCH (also the per-cell suppression trace) |
| Min num_enrolled_in_college (=10) | gold 2010/621/economically_disadvantaged 20/10 et al. — consistent with the ≥10 threshold; contract check `published_counts_meet_reporting_threshold` passes over all rows | min_val = 10.0 every metric, every year (manifest) | MATCH |

### One ordinary entity per era

| Era | Entity | Bronze (quoted) | Gold | Verdict |
|---|---|---|---|---|
| 1 (2012.xlsx) | Towns Co 739/204, Douglas Co 648/187, Social Circle 786/300, Pike Co 714/ALL, Terrell 735/105 | `55/43`, `430/299`, `97/61`, `207/154`, `73/53` (Total All) | same five values | MATCH ×5 |
| 2 (2013.xlsx) | Appling 601/0103 | Total All `162 / 100`; Pacific Islander `TFS / TFS` | 162/100; PI None/None | MATCH |
| 2 (2013.xlsx) | State | Total All `88017 / 64893`; PI `67 / 44` | 88017/64893; 67/44 | MATCH |
| 3 (2019.xlsx) | Appling 601/103 (bronze int code → gold `0103`) | Total All `198 / 118`; White `116 / 68` | 198/118; 116/68 | MATCH (zfill verified) |
| 3 (2019.xlsx) | State | `106934 / 72472`; Black `39070 / 25398`; White `47731 / 34072` | manifest 2017 max 106934/72472 confirms | MATCH |
| 4 (2023.csv) | District 601; school 602/0103 | `215 / 113`; Atkinson County HS `116 / 50` | 215/113; 116/50 | MATCH |
| 4 (2024.csv) | District 602 ALL row, **all 14 groups** | e.g. TOTAL `90/48`, MALE `45/18`, BLACK `16/TFS`, FRL `TFS/TFS`, HISPANIC `33/18`, WHITE `39/23` | 14/14 rows match incl. per-cell suppression BLACK 16/None | MATCH (0 mismatches) |

### 4c Sentinel year-attribution — PASS

Year-bearing parsing exists (in-file `School Year`/`SCHOOL_YEAR`). Traced: the
file named `…_2012.xlsx` carries `SY= 2010` in-file and gold rows land in
`year=2010` — the embedded year wins; the filename is only the enforced
`cohort + 2` cross-check (plus Era 4's `REPORTING_YEAR == filename` guard). A
mis-shipped file would raise, not mislabel.

### 4d Aggregate feasibility screen (aggregates come from bronze) — PASS

Suppression-heavy topic → screened for impossibly-LOW aggregates on
`demographic='all'` across all years:

- district < max school: **0** violations (both metrics).
- district < visible school sum: 3 hits, all **bronze-real off-by-ones**:
  - 2016.xlsx Atlanta (761): district ALL row `1791 / 1216` vs visible school
    sums 1792 (0 TFS) / 1210 (1 TFS) — bronze publishes grads 1 below sum.
  - 2021.xlsx Gwinnett (667): district `11600 / 8864` vs school sums 11595
    (1 TFS) / 8865 (1 TFS) — enrolled 1 below visible sum.
  - 2023.csv Gwinnett (667): district `12022 / 8735` vs school sums
    12016 / 8736 — enrolled 1 below visible sum.

  All three exist verbatim in bronze; ±1 publisher-side residue, preserved
  correctly. Not a transform defect; no fix.
- state vs sum of visible district all-rows: residues 0–20 per year, always
  state ≥ sum (benign; small unattributable remainder).

### 4e Dedup tie-break — N/A

Each of the 13 files carries exactly one distinct cohort year (manifest
`files_processed`: 2010–2022, no repeats); no overlap years exist. The
collision guard runs before dedup and would raise on any surprise.

### 4f Suppression semantics — PASS

Only one marker (`TFS`). Traced 2012.xlsx district 603 `FRL grads='10'` /
`FRL enrolled='TFS'` → gold `10 / None`, plus 2024.csv district 602
`BLACK 16/TFS` → `16 / None` (per-cell, one-directional suppression preserved).
Era-level total proof: gold NULL metric cells equal the structure doc's
counted bronze TFS cells **exactly** — Era 1: 8,174; Era 2: 17,908; Era 3:
72,857; Era 4: 9,317 (2021) and 9,482 (2022). `strict=False` nulled exactly
the TFS cells and nothing else.

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warnings**; `passed: true`
  (2026-06-11T01:17:52Z, fresh against the manifest). `contract_parquet_schema`
  (39 files), `contract_quality_sql` (all 12), `grain_uniqueness`
  (year, district_code, school_code, demographic), and `foreign_keys`
  (199 districts, 565 schools, 14 demographics — all resolve) all pass.
- `schema_hash`: `eda332ef3584a7a2c7a6d5d4a665fccbfb645779aef6b10f3ffb28a06ea01e96`
- **§4b masking audit**: no `_null_*` helpers in transform.py, no
  `masked_values` section in the manifest, and the module docstring documents
  the full-scan finding (no impossible values in any of the 13 files).
  Consistent. N/A — nothing unrecorded.
- **§15b coverage judgment**: strong. The 8 authored checks pin the topic's
  real invariants: enrolled ≤ graduates, one-directional co-null, ≥10
  publication threshold, state rows never suppressed, gender partition exact,
  race partition within residue 8 (2011+), and both PI structural facts.
  No obvious missing invariant (a district ≥ max-school check would be
  satisfiable — 0 violations found — but is marginal; not required).
- **v1 parity** (verbatim): `MATCH — byte-identical with v1 gold`

## Cross-Era Consistency

- **Overlap years**: none (one cohort per file, 2010–2022 contiguous).
- **Era boundaries**: row counts step smoothly (588 → 592 → … → 659); state
  totals continuous across all boundaries — max YoY step is grads ×1.119
  (2014→2015, real cohort growth); no >10x jumps, no revert-style level
  shifts for either count metric.
- **Cross-year NULL sweep**: zero FLAG/INVESTIGATE columns — no era-localized
  ~100%-NULL column (rules out the rename-typo signature). NULL rates are
  46–56% per metric-year, uniform, and equal bronze TFS counts exactly.
- Era routing in the manifest matches the doc: 1 file Era 1, 2 files Era 2,
  8 files Era 3, 2 files Era 4; Era 2 vs 3 split (2- vs 3-row header)
  resolved from the located header index, never hardcoded.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | none | PASS — Excel stitch raises on any unrecognized metric label; CSV requires all 28 expected metric columns and warns on extras; identifier/name columns consumed explicitly |
| Era routing correctness | none | PASS — signature-based detection (most-specific first), 13/13 files routed as documented |
| Filter logic | none | PASS — no filters; `filtered = 0` every year |
| Normalization map completeness | none | PASS — 27/27 documented labels seen and mapped; unmapped 0 |
| `strict=False` casts | none | PASS — Float64 hop tolerates decimal strings; NULL counts tie out to bronze TFS counts exactly in every era, so nothing else was nulled |
| Dedup keys + tie-break | none | PASS — no overlap possible; collision guard precedes dedup; `sort_col="graduate_count"` is a documented no-op safety net |
| Year extraction | none | PASS — in-file year authoritative with two enforced cross-checks (filename offset; Era 4 REPORTING_YEAR) |
| §4b masks | none | N/A — no masks; documented full-scan found no impossible values |

## Required Fixes

### Fix 1: Correct the fabricated sample-table values in bronze-data-structure.md (Eras 2–4)
- **Severity**: LOW
- **Issue**: The structure doc's illustrative "Sample Data" tables for Eras
  2, 3, and 4 contain values that do not exist in bronze. Gold is unaffected
  (it matches bronze, verified above), but the doc is the review surface for
  future audits and currently misleads anyone spot-checking against it.
- **Evidence** (bronze quoted vs doc claim):
  - Era 2 (2013.xlsx) state row: bronze `88017 / 64893` vs doc `88127 / 56194`;
    doc's Fulton row `679/0193 Chattahoochee HS 496/376` — **no such row in
    bronze**. (Doc's Appling `162/100` and state PI `67/44` are correct.)
  - Era 3 (2019.xlsx): bronze state `106934 / 72472`, Black `39070 / 25398`,
    White `47731 / 34072` vs doc `107009 / 71110`, `38937 / 25051`,
    `44894 / 32048`; Appling bronze `198 / 118` vs doc `206 / 137`.
  - Era 4 (2023.csv): bronze state `110804 / 71791` vs doc `104263 / 66010`;
    district 601 bronze `215 / 113` vs doc `172 / 97`; school 602/0103 bronze
    `116 / 50` vs doc `89 / 52`. The doc's state row also shows `BlackHS/BlackC
    = TFS` — impossible, since state rows are never suppressed (verified in
    all 13 files and pinned by a quality check).
  - Era 1 sample rows were verified correct (all five match bronze exactly).
- **Location**: `data/bronze/education/gosa/postsecondary_c11_report/bronze-data-structure.md`,
  "Sample Data" subsections of Era 2, Era 3, and Era 4 (transform.py needs no change)
- **Suggested fix**: Regenerate the three sample tables from the actual bronze
  files (quote real rows), or replace the fabricated values with the verified
  ones above. Do not change gold or transform.py.

## Notes

- `schema_hash`: `eda332ef3584a7a2c7a6d5d4a665fccbfb645779aef6b10f3ffb28a06ea01e96`;
  validation 21 pass / 0 fail / 0 warnings; v1 parity MATCH (byte-identical).
- Read loss: zero events (Excel whole-sheet reads are raw == parsed by
  construction; CSV read-loss tracked via the shared reader).
- The 2010 bare-Asian call carries an irreducible ≤~70-student ambiguity
  (whether GOSA's 2010 "Asian" column included the future PI group cannot be
  proven from this file alone), but the gold representation `asian` is forced
  by the standards either way: §5a/§5b forbid mixing a combined key into a
  split-convention topic, the 957-graduate residue is dominated by
  transition-year unreported-race students, and the convention is documented
  in the contract and pinned by quality checks.
- Three ±1 district-vs-school-sum discrepancies (Atlanta 2014 grads; Gwinnett
  2019/2021 enrolled) are bronze-real and preserved; suppressed cells make the
  visible-sum comparison approximate, and the contract's limitations text
  already directs consumers to official aggregate rows.
- The structure doc's suggested gold names (`hs_grads`/`in_college`) were
  superseded by the canonical/sibling-pair names `graduate_count` /
  `num_enrolled_in_college` — intentional, contract-documented, and
  join-compatible with postsecondary_c12_report.
