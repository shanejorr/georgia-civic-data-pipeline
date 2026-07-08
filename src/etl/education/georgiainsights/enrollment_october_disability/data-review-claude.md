# Data Review: enrollment_october_disability

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Gold accurately reproduces all 13 bronze District files (FY2014–2026) at the
(year, district, disability_category) grain with zero row loss (2,838 bronze
rows × 17 = 48,246 gold rows, expansion factor exactly 17.00 every year).
**v1 parity: MATCH — byte-identical with v1 gold** (`da815d7e…`, re-verified
independently). All 17 categorical map entries are semantically correct, every
spot check (extremes, ordinary rows, pseudo-districts, suppression) matched
bronze exactly, and the 2026 gold per-category sums/mins/maxes/suppression
counts reproduce the structure doc's statistics table for all 17 categories.
No required fixes; no judgment items.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|--------|------------:|-------------------:|---------:|--------|
| `disability_category` | 17 | 17 (all documented codes, none missing/extra) | 0 | PASS |

Full semantic review of every map entry (GaDOE/IDEA standard codes):

| Bronze | Gold | Correct? |
|--------|------|----------|
| AUT | autism | YES |
| BL | blind_low_vision | YES |
| D | deaf | YES |
| DB | deaf_blind | YES |
| EBD | emotional_behavioral_disorder | YES |
| HH | hospital_homebound | YES |
| MID | mild_intellectual_disability | YES |
| MoID | moderate_intellectual_disability | YES |
| OHI | other_health_impairment | YES |
| OI | orthopedic_impairment | YES |
| PID | profound_intellectual_disability | YES |
| SDD | significant_developmental_delay | YES |
| SI | speech_language_impairment | YES |
| SID | severe_intellectual_disability | YES |
| SLD | specific_learning_disability | YES |
| TBI | traumatic_brain_injury | YES |
| VI | visual_impairment | YES |

The high-risk pair is SI vs SID (similar codes, very different meanings).
Magnitude evidence confirms the assignment is right and not swapped:
`speech_language_impairment` sums ~28,000–29,900 statewide every year (speech
is among the most common IDEA categories) while
`severe_intellectual_disability` sums 788–979 (rare category) — e.g. 2026:
SI = 28,998 vs SID = 788, exactly matching the bronze 2026 statistics table
(SI sum 28,998; SID sum 788).

- **2a Completeness**: `bronze_values_seen` = the 17 documented codes exactly;
  no documented value unencountered. PASS.
- **2c Contract cross-check**: `gold_values_produced` (17) == contract `enum`
  (17), value-for-value. PASS.
- **2d Unmapped**: `unmapped_count` = 0. PASS.
- **2e Asian/PI conflation**: **N/A** — triage script printed
  `SKIP: no demographic column`; no `pct_asian` column exists. This topic has
  no demographic axis (disability_category is a topic categorical).
- **2f Mutual exclusivity**: **N/A / PASS — single convention.** No
  `demographic` column; `disability_category` publishes no rollup value (no
  `all`), so no split-vs-rollup overlap is possible.

### Row-count reconciliation

| Year | Bronze | ×17 | Gold (manifest) | Gold (parquet) | Match |
|-----:|-------:|----:|----------------:|---------------:|-------|
| 2014 | 201 | 3,417 | 3,417 | 3,417 | YES |
| 2015 | 201 | 3,417 | 3,417 | 3,417 | YES |
| 2016 | 206 | 3,502 | 3,502 | 3,502 | YES |
| 2017 | 209 | 3,553 | 3,553 | 3,553 | YES |
| 2018 | 213 | 3,621 | 3,621 | 3,621 | YES |
| 2019 | 213 | 3,621 | 3,621 | 3,621 | YES |
| 2020 | 216 | 3,672 | 3,672 | 3,672 | YES |
| 2021 | 222 | 3,774 | 3,774 | 3,774 | YES |
| 2022 | 223 | 3,791 | 3,791 | 3,791 | YES |
| 2023 | 227 | 3,859 | 3,859 | 3,859 | YES |
| 2024 | 235 | 3,995 | 3,995 | 3,995 | YES |
| 2025 | 235 | 3,995 | 3,995 | 3,995 | YES |
| 2026 | 237 | 4,029 | 4,029 | 4,029 | YES |
| **Total** | **2,838** | **48,246** | **48,246** | **48,246** | YES |

Bronze per-file row counts equal the structure doc's table exactly; expansion
factor is 17.00 in every year (clean unpivot, zero filtered, zero read loss —
manifest `total_filtered` = 0, `read_loss` absent/empty). All 13 expected
years present, no gaps. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| (filename `Year{YYYY}-1`) | `year` | MAPPED (Int32; preamble cross-checked) |
| `System ID` | `district_code` | MAPPED (Utf8, zfill(3); 7-digit codes preserved) |
| `System Name` | — | CORRECTLY EXCLUDED (dimension attribute; names resolve in districts dimension, incl. the three blank-name pseudo-districts) |
| `AUT`…`VI` (17 columns, unpivoted) | `disability_category` | MAPPED (17-value enum) |
| `AUT`…`VI` (cell values) | `student_count` | MAPPED (Int64; `*` → NULL) |
| — | `school_code` | NOT FABRICATED — always-NULL key-shape column per education domain convention, guarded by `school_code_always_null` |

No gold column lacks a bronze provenance; no bronze fact column is dropped.
The required-columns guard in `_transform_file_frame` makes a missing bronze
disability column fail loudly rather than silently shrinking the unpivot.

## Value-Level Spot Checks

All traces quoted from the raw bronze CSVs; every one is a MATCH.

**4a Extreme rows (global max & min):**
- **Global max** — bronze 2020: `"667","Gwinnett County",…,"10526","31","52"`
  (SLD field = 10526). Gold (2020, 667, specific_learning_disability) =
  10526. All other 16 Gwinnett 2020 categories also matched cell-for-cell
  (AUT 3233, OHI 2762, SDD 2581, SI 2511, …, DB `*`→NULL). **MATCH**.
- **Global min (=10, 579 rows)** — bronze 2014:
  `"603","Bacon County","*","*","*","*","10",…` (EBD = 10). Gold (2014, 603,
  emotional_behavioral_disorder) = 10; all 17 Bacon categories matched
  (MID 17, MoID 12, OHI 51, SDD 61, SI 55, SLD 77, rest NULL). **MATCH**.

**4b Ordinary traces (full 17-category rows):**
- 2026 White County: bronze `"754","White County","81","*","*","*","32","*","11","*","121","*","*","114","64","*","211","*","*"`
  → gold autism 81, EBD 32, MID 11, OHI 121, SDD 114, SI 64, SLD 211, other
  10 categories NULL. **MATCH**.
- 2014 Worth County: bronze `"759","Worth County","10",…,"30","*","26","13","21","*","*","35","61","*","34","*","*"`
  → gold autism 10, EBD 30, MID 26, MoID 13, OHI 21, SDD 35, SI 61, SLD 34,
  rest NULL. **MATCH**.
- 2020 Appling County: bronze `"601","Appling County","28","*","*","*","42","*","23","15","48","*","*","89","80","*","153","*","*"`
  → gold autism 28, EBD 42, MID 23, MoID 15, OHI 48, SDD 89, SI 80, SLD 153,
  rest NULL. **MATCH** (single era — traces span 2014/2020/2026).

**Pseudo-districts (blank-name state schools, 2014-2019):** bronze 2014
`"7991893","","*","*","155",…` (D=155, MID=13), `"7991895","","*","*","88",…`
(D=88), `"7991894","",…,"13","11","*","*","*","12","*",…,"55"` (MID=13,
MoID=11, **SDD=12**, VI=55 — confirmed via csv-module parse of the raw line).
Gold matches all three exactly (7991894: significant_developmental_delay=12,
speech_language_impairment=NULL). Present in gold 2014–2019 only, absent
2020+ — matching bronze. All three resolve in the districts dimension with
hand-coded names (`state_school` type). **MATCH**. (Note: the structure doc's
fixed-width *sample rendering* of the 7991894 line misaligns the 12 under SI;
the raw CSV puts it in SDD — gold follows the raw CSV. Doc nit only; see
Notes.)

**4c Sentinel year-attribution:** Year-bearing patterns exist
(`FILENAME_PATTERN`, `PREAMBLE_YEAR_PATTERN`) but the year is taken from the
filename and *cross-checked* against the preamble with a loud failure on
mismatch. Quoted bronze 2020 file line 2:
`FTE Enrollment by Disability - Fiscal Year 2020-1 Data Report`, line 3:
`"October 1, 2019 (FTE 2020-1)"` — gold rows from this file carry year=2020
(Appling trace above). All 13 files passed the guard at transform time.
**PASS**.

**4d Aggregate-row reconciliation:** **N/A** — the transform derives no
district/state rows and bronze publishes no aggregates (no state row, no
'all' category, no row-total column), so there is nothing to reconcile. As a
substitute plausibility screen, the 2026 gold per-category sums, mins, maxes,
and suppressed-cell counts reproduce the structure doc's independently
measured 2026 statistics table **exactly for all 17 categories** (e.g. SLD
sum 80,154 / max 10,040 / 24 suppressed; AUT 39,917 / 5,384 / 51; DB sum 0 /
237 suppressed).

**4e Dedup tie-break:** **N/A** — one file per year, no overlap years; the
collision guard (`assert_no_natural_key_collisions`) ran before dedup and
found zero duplicates.

**4f Suppression semantics:** bronze 2026
`"662","Glascock County","*","*","*","*","*","*","*","*","25","*","*","12","13","*","21","*","*"`
— the 13 `*` cells are all NULL in gold; the 4 published cells (OHI 25,
SDD 12, SI 13, SLD 21) carry through exactly. `*` is the only marker
(transform's cell-conformance guard proves digits-or-asterisk per cell).
**MATCH**.

## Validation Cross-Read

- `_validation.json`: **19 pass / 0 fail / 0 warning**, `passed: true`,
  timestamp 2026-06-12T17:29:53Z (fresh vs manifest 17:29:52Z; transform
  mtime 17:29:25Z). `contract_parquet_schema`, `contract_quality_sql` (all 6),
  `grain_uniqueness`, and `foreign_keys` all pass; FK detail: all 252
  district codes resolve, school_code has no populated keys.
- Contract `schema_hash`: `998bb4e5859787daa7c9bbe0616c5348374d29417a65377a58bc876fd20a7ee1`.
- **§4b masking audit**: no `_null_*` helpers in transform.py (grep: only the
  docstring mention and `check_null_rate_spikes`); manifest has no
  `masked_values` section. Consistent — `*`→NULL is §8 suppression handling
  (row-preserving), correctly NOT recorded as a §4b mask, and documented in
  the `student_count` contract description + `null_meaning`.
- **§15b coverage judgment**: ADEQUATE. The three authored checks
  (`school_code_always_null`, `district_block_complete_17_categories`,
  `student_count_respects_suppression_floor`) capture this topic's real
  structural invariants. Partition-sum / hierarchy checks are genuinely
  inapplicable: bronze publishes no total column, no 'all' category, no state
  row, no school rows — there is no published aggregate to reconcile against.
- **v1 parity** (re-run independently):

```
current: da815d7e588c88112301982bc75bb5c6baa5d8c91d5f0319336b6f39e88da72a
v1     : da815d7e588c88112301982bc75bb5c6baa5d8c91d5f0319336b6f39e88da72a
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **Single era** (2014–2026, byte-identical post-strip headers across all 13
  files per the structure doc and the manifest's uniform `bronze_columns`).
  No overlap years, no era boundaries.
- **Cross-year NULL sweep**: no column ≥95% NULL in only some years; no
  whole-column 100%-NULL gold column. Within `disability_category`,
  `deaf_blind` is 100% NULL in all 13 years — the documented bronze reality
  (DB 100% suppressed in every file; structure-doc Corrections section), not
  a rename bug; rows are kept to preserve the 17-category block.
- **YoY level continuity**: statewide district-sum moves smoothly
  187,100 (2014) → 240,858 (2026); max adjacent-year ratio 1.034, min 0.986
  (the 2021 dip is the COVID year — plausible). No 10x jumps, no
  revert-next-year 1.5–2x shifts.
- **Per-category YoY sweep** (catches single-year category swaps): CLEAN — no
  category's statewide sum moves >2x or <0.5x between adjacent years. The
  `deaf` step-down (315 in 2019 → 218 in 2020) coincides exactly with the two
  deaf state schools (7991893/7991895, D=155/88 in 2014) leaving the report
  in 2020 — bronze composition change, not transform loss.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Required-columns guard fails loudly if any of the 19 bronze columns is missing; header whitespace stripped at read |
| Era routing | N/A | Single era, one file shape; filename pattern guard rejects unexpected names |
| Filter logic | PASS | No filters; `total_filtered` = 0, read loss raw==parsed for all 13 files |
| Normalization map completeness | PASS | 17/17 codes mapped via `replace_strict`; manifest unmapped = 0 |
| `strict=False` casts | PASS | Preceded by a digits-or-asterisk cell-conformance guard, so only `*` can become NULL |
| Dedup keys + tie-break | PASS | Collision guard before dedup (zero duplicates expected and found); explicit `sort_col="student_count"` tie-break as drift protection |
| Year extraction | PASS | Filename regex + preamble title/year cross-check guard; verified against quoted preamble lines |
| §4b masking | PASS | None needed; none present; manifest consistent |
| System ID shape guard | PASS | 3-/7-digit-only loud guard; zfill(3) pads without truncation; no state sentinel exists in this source |

## Notes

- `schema_hash`: `998bb4e5859787daa7c9bbe0616c5348374d29417a65377a58bc876fd20a7ee1`;
  validation 19/19 pass, 0 warnings; manifest generated 2026-06-12T17:29:52Z.
- v1 parity MATCH (`da815d7e…`) independently re-computed by this review.
- ~52% of bronze cells are suppressed (`*`), rising to ~63.7% NULL in
  2026 gold — consistent with the manifest's per-year `null_pct` trend
  (0.592 → 0.637) and bronze suppression rates; row-preserving NULL handling
  is the correct §8 treatment.
- Two cosmetic nits in `bronze-data-structure.md` (no gold impact, no
  transform change needed — flagging for whoever next amends the doc):
  (1) the fixed-width 2014 sample table renders 7991894's value `12` under
  `SI`; the raw CSV places it in `SDD` (`…,"11","*","*","*","12","*",…` —
  confirmed by csv-module parse). Gold correctly follows the raw CSV.
  (2) "each has non-suppressed counts in 1-3 disability columns" — 7991894
  has 4 (MID, MoID, SDD, VI).
- AWS profile is broken per run context — no S3 access attempted; all
  verification ran against local bronze/gold (local is in sync with the
  v1-approved hash, which is the stronger guarantee anyway).
