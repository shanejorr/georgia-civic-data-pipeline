# Data Review: enrollment_march_gender_race_ethnicity

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Gold data is accurate: **v1 parity MATCH (byte-identical, independently
re-verified: `d4e81a74…`)**. All 9 categorical map entries (7 race + 2 gender)
are semantically correct; per-year row reconciliation is *exact* for all 16
years under the formula `(bronze − bronze/3) × 7 − 14`; an independent
re-derivation of two whole bronze files (2010 District + 2025 School, 35,168
cells through a different code path) reproduced gold with **0 mismatches**;
and the aggregate feasibility screen is perfectly consistent (11,512
fully-visible district cells equal their school sums to the row, 0
impossibly-low aggregates in 27,277 district and 224 state comparisons). The
shared `_enrollment_race_lookups.py` module encodes the split-Asian/PI and
Hispanic-precedence conventions correctly for reuse by the October sibling.
No required fixes, no judgment items.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
| --- | --- | --- | --- | --- |
| `race` | 7 | 7 (= structure-doc set) | 0 | PASS |
| `gender` | 2 | 2 (`Total` dropped pre-map — see below) | 0 | PASS |

**`race` — all 7 entries reviewed semantically (2b), all correct** (keys are
bronze *column names* unpivoted into rows; map lives in the shared
`_enrollment_race_lookups.py`):

| Bronze column | Gold | Correct? |
| --- | --- | --- |
| Ethnic Hispanic | `hispanic` | Yes — non-overlapping ethnicity bucket; GaDOE FTE coding gives Hispanic precedence over race (partition proof in 2e below); contract description warns against treating it as an any-race overlay |
| Race AmericanIndian | `native_american` | Yes — canonical key, category `race` in `DEMOGRAPHIC_CATEGORIES` |
| Race Asian | `asian` | Yes — split convention proven (2e) |
| Race Black | `black` | Yes |
| Race Pacific Islander | `pacific_islander` | Yes — separate bronze column in every file |
| Race White | `white` | Yes |
| Two or more Races | `multiracial` | Yes — canonical key for "Two or More Races" |

**`gender` — both entries correct:** Female → `female`, Male → `male`. The
structure doc documents a third bronze value, `Total`; it is absent from
`bronze_values_seen` **by design** — the transform drops `Total` rows *before*
the map applies, and the drop is fully accounted: 40,112 recorded filtered
rows = exactly `total_bronze / 3` = 120,336 / 3 (every geography publishes
exactly 3 gender rows). Not a routing bug.

- **2a Completeness**: all 7 documented race columns and both retained gender
  values appear in `bronze_values_seen`. The only documented-but-unseen value
  (`Total`) is explained above.
- **2c Contract cross-check**: `gold_values_produced` equals the contract
  `enum` exactly for both columns (7 race values sorted; `female`/`male`).
- **2d Unmapped**: 0 for both (and both maps use `replace_strict` with a
  sentinel default, so a bypass is impossible).

### 2e Asian / Pacific Islander (Risk 1) — PASS, split convention

Bronze publishes **explicit separate `Race Asian` and `Race Pacific Islander`
columns in every one of the 32 files** (structure doc + verified headers), so
bare "Asian" is genuinely Asian-only. Positive-evidence math test (this topic
has `race`+`gender` columns and no `all` row, so the test is the published
partition): 2025 state bronze `Total` row =

```
"","State-Wide","Total","340147","4052","90874","625059","1721","589160","85717"
```

340,147 + 4,052 + 90,874 + 625,059 + 1,721 + 589,160 + 85,717 = **1,736,730**,
and the sum of the 14 gold state cells for 2025 = **1,736,730** — equal to the
published statewide March 2025 FTE enrollment. The seven buckets partition
total enrollment with the split pair present → split convention is correct
and `asian_pacific_islander` is correctly never emitted.

### 2f Demographic mutual exclusivity (Risk 6) — PASS, single convention

`gold_values_produced` contains `asian` and `pacific_islander` but no
`asian_pacific_islander` rollup (and no other rollup/split pair). Single
convention throughout.

## Manifest Verification — row counts

Exact reconciliation for **all 16 years** (executed, every year MATCH):

| Quantity | Formula | Verified |
| --- | --- | --- |
| Total-gender drops | `bronze / 3` per year | 40,112 total = 120,336/3 ✓ |
| State-twin drops | 14 per year (2 gender × 7 race) | 224 = 14 × 16 ✓ |
| Gold per year | `(bronze − bronze/3) × 7 − 14` | exact, e.g. 2010: (7,374−2,458)×7−14 = 34,398 ✓; 2025: (7,683−2,561)×7−14 = 35,840 ✓ |
| Gold per year (structural) | `14 × (n_districts + n_schools + 1)` | exact for all 16 years (e.g. 2010: 14×(186+2,270+1) = 34,398) ✓ |
| Parquet total | sum of 48 files | 561,344 = manifest `total_gold` ✓ |

Expansion factor ≈ 4.6648 (= 7 × 2/3 minus the 14-row state dedup) is
consistent across all years. All 16 expected years present; all 32 bronze
CSVs appear in `files_processed` (the bronze dir contains exactly 32 CSVs).

## Column Coverage

| Bronze column | Gold column | Status |
| --- | --- | --- |
| (filename `Fiscal YearYYYY-3`) | `year` | MAPPED (cross-checked vs preamble, hard raise on mismatch) |
| `System ID` | `district_code` | MAPPED (`""` → NULL before zfill(3)) |
| `System Name` | — | CORRECTLY EXCLUDED (districts dimension attribute; FK check: all 250 district keys resolve) |
| `School ID` (NNNN prefix) | `school_code` | MAPPED (first-hyphen split, zfill(4); `State-Wide` fails regex → NULL, correct) |
| `School ID` (name part) | — | CORRECTLY EXCLUDED (schools dimension attribute; all 2,705 school keys resolve) |
| `Gender` | `gender` | MAPPED (`Total` rows dropped, recorded) |
| 7 race/ethnicity count columns | `race` + `student_count` (unpivot ×7) | MAPPED |

No gold column lacks a bronze ancestor (no fabrication). The
`require_race_columns` guard plus the `base_required` check fail loudly if any
bronze column goes missing, so silent-NULL renames are structurally prevented.

## Value-Level Spot Checks

All traces MATCH. Extreme rows first:

| Trace | Bronze (quoted) | Gold | Verdict |
| --- | --- | --- | --- |
| **Global max** — 2010 state, white male | 2010 District state Male row: `"","State-Wide","Male","97352","2155","27399","312055","744","383296","23719"` → Race White = 383296 | `(2010, NULL, NULL, white, male) = 383296` | MATCH |
| **Global min (15, suppression floor)** — 2010 district 608, native_american male | `"608","Bartow County","Male","673","15","50","652","*","5901","122"` → Race AmericanIndian = 15 | `(2010, 608, NULL, native_american, male) = 15` | MATCH (5,548 gold rows sit exactly at the floor; contract enforces ≥ 15) |
| Ordinary — 2010 district 608, all 14 cells | Female row `"616","26","48","631","*","5642","130"` / Male row above | hispanic f=616, native_american f=26, asian f=48, black f=631, pacific_islander f=NULL, white f=5642, multiracial f=130; male likewise (PI m=NULL from `*`) | MATCH |
| Ordinary — 2017 district 644 (DeKalb) | `"644","DeKalb County","Female","8569","125","3214","31013","60","5382","921"` (+ Male row) | all 14 gold cells equal, e.g. black f=31013, pacific_islander m=67 | MATCH |
| Ordinary — 2017 school 601/0103 (Appling County High) | `"601","Appling County","0103-Appling County High School","Male","59","*","*","106","*","323","*"` | hispanic m=59, black m=106, white m=323, others NULL | MATCH |
| **Suppression (4f)** — 2025 school 737/3052 (Northeast Middle) | `"737","Tift County","3052-Northeast Middle School","Male","89","*","*","131","*","121","*"` | hispanic m=89, black m=131, white m=121; native_american/asian/pacific_islander/multiracial m = NULL | MATCH — every `*` → NULL |
| **State twins (4e analog)** — 2025 | District-file and School-file state rows are byte-identical (both quoted from bronze: Female `166312,1984,44042,309028,852,285306,42374`; Male `173835,2068,46832,316031,869,303854,43343`) | exactly 14 state rows in gold 2025, values equal the bronze Female/Male rows | MATCH |

**Full-file independent recomputation** (stronger than spot checks): re-read
2010 District and 2025 School bronze through a separate code path (manual
split/zfill/int, no transform imports) and compared every resulting cell to
gold — **2,618 + 32,550 = 35,168 cells, 0 mismatches** (including every
`*` → NULL cell).

- **4c Sentinel year-attribution (Risk 3)**: year-bearing patterns exist only
  in `FILENAME_PATTERN` / `PREAMBLE_YEAR_PATTERN`. The preamble year is
  *cross-checked* against the filename year with a hard raise; verified
  line 2 of the 2010 file reads `FTE Enrollment by Race/Ethnicity and Gender
  - Fiscal Year 2010-3 Data Report` and its rows land at gold `year = 2010`.
  No in-data year strings exist. PASS.
- **4d Aggregate feasibility screen (Risk 4)**: aggregates COME FROM BRONZE
  (not derived). Executed screen: across 27,277 non-null district cells with
  school coverage, **0** are impossibly low (district < max school or
  district < visible school sum); the 11,512 district cells whose schools are
  fully visible equal the school sum **exactly** (max abs diff = 0). State
  cells: 224 compared, **0** below the visible district sum (coverage ratio
  0.5914–0.9999 — never > 1, shortfall fully explained by suppression). PASS.
- **4e Dedup tie-break (Risk 5)**: single era, no overlap years → N/A. The
  state-twin dedup analog is verified above (collision guard groups on keys
  *including* `detail_level`, so the District-file and School-file state
  copies are proven value-identical before `deduplicate_by_detail_level`
  keeps one; the guard raises on any divergence, nulls counted as distinct).

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning** (2026-06-12T16:28:10Z,
  fresh vs transform 16:28:03 and shared module 16:23:22).
  `contract_parquet_schema` (48 files), `contract_quality_sql` (7 checks),
  `grain_uniqueness`, and `foreign_keys` all pass.
- Contract `schema_hash`: `1cdd6e5ae6719bfdf75e40e5470b8dbf10b209d491c22b9bf2eb6a1019c57ab2`.
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no
  `masked_values` / `read_loss` / `reclassified` sections (absent = zero
  events). Read loss is MEASURED (raw line counts vs parsed, raw == parsed for
  all 32 files). Nothing to audit — N/A, consistent.
- **§15b coverage judgment**: adequate. Authored checks pin the topic's three
  distinctive invariants — suppression floor exactly 15 (5,548 gold rows sit
  at the floor, none below), state rows never suppressed, and the state
  race×gender partition = 14 rows/year (the dedup-output invariant, i.e. the
  riskiest step). Auto-derived checks cover enums, non-negativity, and
  non-emptiness. Optional future hardening noted in Notes (not a gap that
  affects current data).
- **v1 parity (5d)** — independently re-executed:

```
v1 : d4e81a74b3f18d5772ee5071aeb2aa0bb01e839b530350f763dd185d13a33ada
now: d4e81a74b3f18d5772ee5071aeb2aa0bb01e839b530350f763dd185d13a33ada
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

Single era (2010–2025, one post-strip column set across all 32 files; manifest
confirms identical `bronze_columns` for every file, School files adding only
`School ID`). No overlap years. Cross-year NULL sweep: `student_count` null
rate ranges 0.5319–0.5978 with a smooth monotone-ish decline (suppression
falls as small populations grow) — no ~100%-NULL year, no rename-bug
signature. Year-over-year state totals are smooth: 1,656,689 (2010) →
1,747,791 (2024) → 1,736,730 (2025); max adjacent-year ratio 1.0139, min
0.9786 — no scale jumps, no cumulative-publication signature.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
| --- | --- | --- |
| Silent column drops | none | PASS — `System Name`/school-name dropped intentionally (dimension attributes); `require_race_columns` + `base_required` raise on any missing bronze column |
| Era routing correctness | none | PASS — single era; `FILENAME_PATTERN` hard-raises on unexpected filenames; 32/32 files processed; School files guarded against hidden district-aggregate rows (hard raise, verified 0) |
| Filter logic logged + justified | none | PASS — both filters recorded per year via `record_filtered` with reason strings; counts reconcile exactly (40,112 + 224) |
| Normalization map completeness | none | PASS — 7 race + 2 gender entries cover every documented bronze value; `Total` dropped pre-map by design; `replace_strict` + sentinel prevents silent unmapped values |
| `strict=False` casts | low (accepted) | PASS — reader already nulls `*` via `null_values`; cast is belt-and-braces; independent `int()` recompute of 35,168 cells found no other non-numeric value |
| Dedup keys + tie-break | none | PASS — collision guard (keys include `detail_level`) proves state twins identical before dedup; tie-break irrelevant for identical twins and stated explicitly |
| Year extraction | none | PASS — filename regex cross-checked against preamble year, hard raise on disagreement; no year strings in data rows |
| §4b masks (5b) | none | N/A — no masks; no impossible values exist (counts ≥ 15 by construction) |

Shared module (`_enrollment_race_lookups.py`): constants only, no I/O;
`RACE_ETHNICITY_COLUMNS`/`RACE_VALUES` derived from the single map so they
cannot drift; the split-A/PI decision is documented once with the partition
proof; all 9 keys verified present in `demographics.parquet` with category
`race` (and `female`/`male` present). Safe for the October sibling to reuse —
note the gender `Total`-drop contract: the map intentionally omits `Total`,
so any consumer transform MUST filter `GENDER_TOTAL_LABEL` before applying
`GENDER_MAP` (this transform does; the module docstring says so).

## Notes

- `schema_hash`: `1cdd6e5ae6719bfdf75e40e5470b8dbf10b209d491c22b9bf2eb6a1019c57ab2`
- Validation: 21 pass / 0 fail / 0 warning; v1 parity MATCH (`d4e81a74…`),
  independently re-verified by this review.
- Verified-but-unauthored invariant (optional future hardening, not a fix):
  every (year, district_code, school_code) geography carries exactly 14 rows
  (7 race × 2 gender) and every (year, geography, race) cell has exactly the
  female+male pair — verified true across all 561,344 rows. A
  `geography_race_gender_partition_complete` quality check generalizing the
  authored state-level check would make this enforceable; consider adding it
  (both topics) when the October sibling is authored. Contract-note-only
  change — would not alter gold bytes or v1 parity.
- The structure doc's 4-entry Corrections block accurately supersedes its own
  stale prose (race-column convention vs `demographic`, the 21→14 state-row
  arithmetic, the local-reader rationale, and the authoring-time invariants);
  the transform follows the corrected guidance in all four cases.
- Suppression floor context: 15 is the *observed* floor (GaDOE small-cell
  rule); 5,548 rows sit exactly at 15, so the contract check would catch any
  future sub-floor leak immediately.
