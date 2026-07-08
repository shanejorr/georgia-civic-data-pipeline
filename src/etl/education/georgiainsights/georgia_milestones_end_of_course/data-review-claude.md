# Data Review: georgia_milestones_end_of_course

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS FIXES

## Summary

Gold is **byte-identical with the approved v1 baseline** (`8b4e9b2a…`, independently re-computed) and every value-level probe passed: all 34 extreme-row traces and 7 per-era ordinary traces match raw bronze exactly, aggregates reconcile at ratio 1.0000 (district = Σ schools, state = Σ districts), the charter SYSTEM→CAMPUS promotion ledger (107/122/51) was re-counted from bronze and matches to the row, and an anti-join over all 27 bronze files for 2023–2025 proves the only data rows absent from gold are the two empty Algebra CC state template rows. The single finding is a §15b gap: the contract does not enforce `num_received_sgp <= num_tested`, a definitional subset invariant that holds on all 3,590 SGP rows today (MEDIUM — author the quality check). The shared `_charter_district_promotion.py` module (reviewed for its 3 future consumers) is correct, narrow, and ledger-driven.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `administration` | 3 | 3 (`Winter`, `Spring`, `Full Year`) | 0 | PASS |
| `subject` | 118 | 118 (sheet names, zip member basenames, Content Area values) | 0 | PASS |

**administration** — all 3 entries semantically correct: `Winter → winter` (mid-year retest), `Spring → spring`, `Full Year → full_year`. Verified that the season token is filename-derived and the slices are genuinely distinct cohorts (state `num_tested` sums: e.g. 2022 winter 107,866 vs spring 404,351 vs full_year 512,217 — full_year ≈ winter + spring + fall, as documented).

**subject** — every one of the 118 entries reviewed individually. All correct, including the hard cases:

- US-history drift: `History`/`U. S. History`/`U.S. History`/`U S History`/`United States History` and all `School -`/`System -`/member-filename variants → `us_history` ✓ (12 distinct raw spellings).
- Literature: `9th Grade Literature`, `Ninth Grade Literature & Composition`, `9th Grade Literature and Composition.xls` → `9th_grade_literature_and_composition` ✓; American Literature variants → `american_literature_and_composition` ✓ (full `_and_composition` forms per §16).
- Algebra family kept DISTINCT across curriculum eras: `Coordinate Algebra → coordinate_algebra`, `Algebra I → algebra_i`, `Algebra CC → algebra_concepts_and_connections` ✓ — no conflation. Geometry/Analytic Geometry likewise distinct ✓.
- `Economics`/`Economics/Business/Free Enterprise` → `economics_business_free_enterprise` ✓.
- `Phys Science Gr8`/`Physical Science Gr8` → `physical_science` (intentional fold of Full-Year 2020-2021's 8th-grade-only administration; grade detail lives in the by-grade sibling topics; documented in the contract and traced below) — reasonable and documented ✓.

Contract cross-check (2c): contract `administration_in_allowed_values` enumerates exactly `{winter, spring, full_year}` and `subject_in_allowed_values` exactly the 11 produced values — both equal `gold_values_produced` ✓. `unmapped_count` = 0 for both (2d) ✓. Completeness (2a): all structure-doc label variants appear in `bronze_values_seen`; the 118-entry ledger covers every era's labeling channel ✓.

**2e Asian/Pacific Islander conflation**: N/A — this bronze has no demographic breakdowns anywhere (no `demographic` column in gold, no race labels in `bronze-data-structure.md`).
**2f Demographic mutual exclusivity**: N/A — no demographic column.

### Row-count reconciliation

| Year | Bronze (post-footnote) | All-metric-null dropped | Gold | Notes |
|---|---|---|---|---|
| 2015 | 9,861 | 0 | 9,861 | + 6 footnote rows (Spring 2015 "Results for all students…" placeholder members ×6) |
| 2016 | 10,989 | 0 | 10,989 | |
| 2017 | 11,366 | 0 | 11,366 | |
| 2018 | 10,927 | 0 | 10,927 | + 12 footnotes (Era 4 literature `*To achieve…`) |
| 2019 | 11,057 | 0 | 11,057 | + 12 footnotes |
| 2020 | 4,608 | 0 | 4,608 | Winter only — Spring 2020 cancelled (COVID); bronze has no Spring/Full-Year 2020 files |
| 2021 | 3,586 | 0 | 3,586 | Full-Year only; + 78 footnotes (COVID note block on School/System/State) |
| 2022 | 8,590 | 0 | 8,590 | |
| 2023 | 8,879 | 1 | 8,878 | 1 identity-less residue row |
| 2024 | 6,030 | 7 | 6,023 | incl. the 2 empty Algebra CC state template rows |
| 2025 | 8,869 | 1 | 8,868 | |
| **Total** | **94,762** | **9** | **94,753** | + 150 footnote rows ledgered (`footnote_row`); expansion factor 1.0 everywhere |

Actual parquet rows = **94,753** = manifest `total_gold` ✓ (33 files, 11 years × 3 detail levels). The bronze counter excludes footnote rows (filtered inside the readers before `record_bronze`); 150 + 9 = 159 = `total_filtered_explicit` ✓.

**Anti-join proof (2023–2025, all 27 files)**: rebuilt (district, school, subject) keys from raw `header=None` reads of every sheet and anti-joined against gold — the ONLY rows not in gold are
`Spring-2024-EOC-State-Level.xlsx :: State - Algebra CC raw-row 3 -> ['Algebra: Concepts and Connections']` and the identical Full-Year-2023-2024 row (every metric cell blank). The remaining 7 all-metric-null drops carried no identity keys at all (template/footer residue) — zero identity-bearing data loss.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| (filename year/season) | `year`, `administration` | MAPPED (year semantics verified below) |
| (sheet name / member basename / `Content Area`) | `subject` | MAPPED (`content_area` in the doc; `subject` per domain §16) |
| System Code / `Key`[0:3] | `district_code` | MAPPED (zfill 3; 7-digit campus codes preserved) |
| School Code / `Key`[3:7] | `school_code` | MAPPED (zfill 4; Spring 2017 bare-int handled) |
| System Name, School Name, RESA | — | CORRECTLY EXCLUDED (dimension attributes) |
| N / Number Tested | `num_tested` | MAPPED (incl. Era 1 bare `N` header) |
| Mean Scale Score | `avg_scale_score` | MAPPED (doc said `mean_scale_score`; `avg_` is the repo convention) |
| Standard Deviation | `scale_score_std_dev` | MAPPED (Spring-2015-System + Winter-2021 + 2022+, per the doc Corrections) |
| % Beginning/Developing/Proficient/Distinguished Learner | `pct_*_learner` | MAPPED, /100 |
| % Developing/Proficient Learner & Above | `pct_*_learner_or_above` | MAPPED (`_or_above` per domain convention, not the doc's `_and_above`) |
| % Below Grade Level / % Grade Level or Above (Lexile 1050L and 1185L headers) | `pct_below_grade_level_lexile` / `pct_grade_level_or_above_lexile` | MAPPED — both thresholds flatten to one pair; threshold history documented in the contract |
| Number Received SGP / SGP Median / % SGP Low/Typical/High Growth | `num_received_sgp`, `sgp_median`, `pct_sgp_*_growth` | MAPPED (`num_` per domain convention) |
| Percent of Enrolled Students Tested | `pct_enrolled_tested` | MAPPED (Full-Year 2020-2021 only) |
| Trailing unnamed/None columns; title rows; footnote rows | — | CORRECTLY EXCLUDED |

No fabricated columns: every gold column traces to a bronze header or the filename. `_frame_from_pandas` raises on any unknown surviving header (`_ALLOWED_POST_RENAME`), so silent drops are structurally impossible.

## Value-Level Spot Checks

**Extreme-row traces (4a)** — global MAX and MIN of all 17 metrics traced to raw bronze; 34/34 MATCH. Highlights (raw values quoted from `header=None, dtype=str` reads):

- `num_tested` MAX 143,619 — `Full-Year-2024-2025-EOC-State-Level.xlsx :: State - Algebra CC` raw `['Algebra: Concepts and Connections', '143619', '521.4857…', '67.704…', '26.527…', '28.542…', '26.197…', '18.731…', '73.472…', '44.929…', '118099', '50', '34.499…', '30.993…', '34.506…']` → gold state row matches every field (also covers `num_received_sgp` MAX 118,099; bands sum to 100.0) — MATCH.
- `num_tested` MIN 1 — `Spring 2015 EOC System.zip :: System - Physical Science.xls` `['604','BAKER COUNTY','1','-----',…]` → gold num_tested=1, all metrics NULL — MATCH.
- `avg_scale_score` MAX 718.692 — `Spring_2016_EOC-School_Level.zip :: Geometry_School.xlsx` compound Key `'6600402'` (River Trail MS, Fulton), N=13, 100% distinguished → gold d=660 s=0402 — MATCH (small-N gifted cohort, plausible, preserved).
- `avg_scale_score` MIN 370.067 — `Full-Year_2023_EOC-School_Level.xlsx :: School - American Literature` `['799','1893','STATE SCHOOLS','ATLANTA AREA SCHOOL FOR THE DEAF','15','100','0','370.0666…',…]` → gold matches incl. lexile below=1.0/above=0.0 — MATCH.
- `scale_score_std_dev` MAX 120.890 — Winter-2023 School Biology, North Gwinnett HS, N=17 (bimodal small-N, conceivable, preserved) — MATCH. MIN 6.364 — Spring 2015 System Economics, Ivy Prep `'7830110'` (bronze publishes the 7-digit campus code at system level; StdDev published even though the mean is suppressed — bronze quirk preserved) — MATCH.
- `sgp_median` MAX 92.5 (half-point median, KIPP South Fulton, raw `'92.5'`) and MIN 4.0 (Gainesville Middle East, raw `'4'`) — MATCH; 600 half-point medians in gold justify Float64.
- `pct_enrolled_tested` MIN 0.00409836 — `Full_Year_2021_EOC-School_Level.xlsx :: School - US History` `['631','2052',…,'1','0.409836','--',…]` (North Clayton HS, 1 tested, COVID year) → gold 0.00409836 — MATCH.
- All proportion MAX 1.0 / MIN 0.0 rows traced to raw `'100'`/`'0'` cells (e.g. Bartow 608 winter-2015 biology `'100','0','0','0','0','0'`; Cherokee Charter `7820212` spring-2018 lexile `'0','100'`) — MATCH.

**Ordinary traces (4b)** — one entity per era, every column compared:

| Era | Trace | Verdict |
|---|---|---|
| 1 (xls state, subjects-as-rows) | Winter 2014 State, Biology: raw `['Biology','21830','505.940…','35.945…','26.110…','29.642…','8.300…','64.054…','37.943…']` → gold state row, all 8 fields /100 where pct | MATCH |
| 2 (xls-in-zip, nested dir, compound Key) | `Winter_2016_EOC_School.zip :: Winter_2016_EOC_School/School - Biology.xls` raw `['6010103','APPLING…','132','509.931…',…]` → gold y2017 d=601 s=0103, all fields | MATCH |
| 3 (xlsx-in-zip, bare-int School Code) | Spring 2017 US History raw `['602','103',…,'71','489.140…',…]` → gold s=`'0103'` zero-padded, all fields | MATCH |
| 5 (Winter 2021: StdDev + Lexile 1185) | raw `['601','0103',…,'117','29.059…','70.940…','512.803…','48.881…',…]` → gold y2022 winter, lexile pair + std_dev correctly slotted from the two-row header | MATCH |
| 6 (Full-Year 2021: pct_enrolled + lexile) | raw `['602','0103',…,'102','97.115385','36.27451','63.72549','500.215686',…]` → gold pct_enrolled_tested=0.97115385, lexile pair, levels | MATCH |
| 6 (Phys Science Gr8 fold) | raw `['605','0100',…,'OAK HILL MS','85','--','513.682353',…]` → gold subject=`physical_science`, pct_enrolled NULL (suppressed `'--'`), all levels | MATCH |
| 7 (Spring 2022) | raw `['605','0189',…,'192','480.447…','65.505…','54.166…',…]` → gold all fields incl. std_dev | MATCH |

**4c Year attribution** — the only year-bearing parsing is `_parse_filename`. Decisive bronze evidence from title rows: `Winter 2021 … State Level - February 22, 2022` (→ SY 2021-22 → year 2022 ✓), `Winter 2024 … February 21, 2025` (→ 2025 ✓), `Winter 2019 … February 21, 2020` (→ 2020 ✓), `Winter 2014 Milestones EOC … November 16, 2015` (→ 2015 ✓), `Winter 2015 … February 15, 2016` (→ 2016 ✓). The +1 Winter rule is therefore correct, and the 2020 (winter-only) / 2021 (full-year-only) year shapes are genuine COVID artifacts of the source, not routing errors. Full-Year range form matched before single-year form (`Full-Year-2024-2025` → 2025 ✓ per ledger).

**4d Aggregate feasibility (aggregates COME FROM BRONZE)** — district `num_tested` vs Σ school `num_tested` (3-digit prefix rollup, so charter-campus school rows roll into their umbrella): 23,791 joinable district rows, ratio quantiles p01/p50/p99 = **1.0/1.0/1.0**, zero rows outside [0.95, 1.05], zero districts below their max school. State vs Σ districts: 163/163 (year, administration, subject) groups within [0.97, 1.03] (all exactly 1.0). The remaining 1,445 district rows are the 7-digit charter-campus district rows, which reconcile 1:1 against their own school rows. No swaps, no garbling.

**4e Dedup tie-break** — N/A: each (year, administration, detail_level) is fed by exactly one bronze file (verified in `files_processed`); no overlap years exist. `assert_no_natural_key_collisions` ran before the defensive dedup and the 2017 dual-representation year (winter promoted vs spring already campus-coded: 51 + 96 seven-digit school rows) is disjoint by administration.

**4f Suppression semantics** — one trace per marker type, all → NULL with row + `num_tested` preserved:
- `'     -----'` (Era 1): Winter 2014 School History `['605','189','BALDWIN COUNTY','BALDWIN HIGH','4','     -----'×7,'OCONEE']` → gold num_tested=4, all 16 metrics NULL — MATCH.
- `'---'` (Spring 2016 School): `US History_School.xlsx` `['6040105','BAKER COUNTY','BAKER COUNTY K12 SCHOOL','1','---'×7,…]` → gold d=604 s=0105 num_tested=1, all metrics NULL — MATCH.
- `'--'` (modern, partial): Spring-2025 System Algebra CC Chattahoochee `['626',…,'50','523.04','59.943…','20','38','28','14','80','42','1','--','--','--','--',…]` → gold keeps the achievement block + `num_received_sgp=1` and NULLs only the four `'--'` SGP cells — MATCH.

## Validation Cross-Read

- `_validation.json`: **21 pass / 0 fail / 0 warning** (2026-06-12T18:24:23Z, fresher than transform 18:21:44Z and shared module 18:21:44Z). `contract_parquet_schema` (33 files), `contract_quality_sql` (28 checks), `grain_uniqueness`, `foreign_keys` (district_code → districts: 222 keys; school_code → schools: 1,188 keys), geography_nulling ×3 — all pass.
- Contract `schema_hash`: `d7c32f13f97e8007fd0d61f7d6c01362a0ccef84152934bcec5f4c5835925491`; version 1.0.0; grain = (year, district_code, school_code, administration, subject).
- **§4b masking audit**: no `_null_*` known-bad masks exist; the only nulling helper is `_null_suppression_markers` (standard §6 suppression). Manifest has no `masked_values` and no `read_loss` sections (legitimately absent — whole-sheet Excel reads cannot lose records at parse time). The [0,1] boundary snap is a float-residue normalization, not a mask: bronze stores spreadsheet sums as e.g. `'-5.329070518200751e-15'` (Winter 2014 System History, Johnson County 683, `% Proficient Learner & Above`) — 48 such cells in the first three zips alone — and gold lands exactly `0.0` for that row (verified). Tolerance is 1e-9; real out-of-range values would still fail the contract proportion checks.
- **§15b coverage**: the 9 authored checks cover the partition sum, both cumulative consistencies, the lexile complement, the SGP-band partition, both subject-restriction structural facts, the pct_enrolled_tested year restriction, and num_tested completeness — a strong set. One genuine cross-column invariant is missing: `num_received_sgp <= num_tested` (definitionally a subset per the column's own description; holds on 3,590/3,590 SGP rows) → Fix 1.
- **v1 parity (5d)**, re-run independently:

```
v1 : 8b4e9b2ac0943218d56ae2bfdec56bd7e97bec49f31c3e45eff556ea4c156823
now: 8b4e9b2ac0943218d56ae2bfdec56bd7e97bec49f31c3e45eff556ea4c156823
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

- **Overlap years**: none (one file per year/administration/detail slot).
- **Era-boundary continuity (3d)**: state-level `num_tested` sums and mean scale scores are smooth across all adjacent year pairs (spring sums 795k→806k→804k→785k→769k for 2015–2019; means 502–520 throughout; no >10x jumps, no revert-next-year level shifts). The 2020 winter-only (217k) / 2021 full-year-only (329k) / 2024 (376k, no Algebra CC) dips are source-shape artifacts explained above.
- **Cross-year NULL sweep (3c)**: 9 flags, all era-explained and matching the structure doc + Corrections: `scale_score_std_dev` ≥95% NULL 2016–2021 (present 2015 via Spring-2015 System, then Winter-2021→gold-2022 and 2022+); lexile pair NULL 2015–2017 (Reading Status starts Winter 2017→year 2018); all 5 SGP columns NULL before 2025 (2024 Algebra CC sheets are empty templates — first populated SGP data is year 2025); `pct_enrolled_tested` NULL outside 2021 (enforced by quality check). No unexplained era-localized rename signatures; no column is 100% NULL in every year.
- 2015 state files contain **8** content areas (not the doc's "ten rows") — verified by raw read: Algebra I and Geometry were not yet in the SY 2014-15 slate. Gold matches bronze; the structure-doc claim is imprecise but harmless.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | — | PASS — `_ALLOWED_POST_RENAME` raises on unknown headers; only all-NaN columns and name/RESA dimension attributes dropped |
| Era routing correctness | — | PASS — structural (zip member count / sheet count), verified per file in `files_processed`; Spring-2018 zip-wrapped xlsx routed correctly |
| Filter logic logged + justified | — | PASS — 150 footnote + 9 all-metric-null drops ledgered; anti-join proves no identity-bearing loss |
| Normalization map completeness | — | PASS — `_canonical_subject` raises on unmapped labels; 118 entries, unmapped_count 0 |
| `strict=False` casts | — | PASS — preceded by `na_values` + explicit marker sweep; `num_tested` has 0 NULLs across 94,753 rows, proving no numeric strings silently nulled |
| Dedup keys + tie-break | — | PASS — purely defensive; collision guard (with metric divergence check) runs first; grain uniqueness validated |
| Year extraction | — | PASS — Winter +1 rule proven by bronze title-row publication dates (see 4c) |
| §4b masks | — | PASS — none; boundary snap verified at 1e-9 with bronze evidence |
| Shared `_charter_district_promotion.py` | — | PASS — only school-level 782/783 rows rewritten (0 remain), `school_code` untouched, aggregates untouched, ledger counts re-derived from bronze match exactly (2015: 36+71=107; 2016: 47+75=122; 2017: 51), promoted keys FK-resolve; called after `_format_ids` (4-digit school codes guaranteed) and before the collision guard, as its docstring requires. Safe for the 3 future consumers. |

## Required Fixes

### Fix 1: Author quality check `num_received_sgp <= num_tested`
- **Severity**: MEDIUM
- **Issue**: §15b coverage gap — the contract enforces SGP band partition and subject/year restrictions but not the definitional subset invariant that students receiving an SGP are a subset of students tested. The column's own contract description ("Number of tested students who received a Student Growth Percentile") states the invariant; it is unenforced, so a future bronze column swap (e.g. `num_received_sgp` landing in `num_tested`) would pass validation.
- **Evidence**: Probe executed on gold: `num_received_sgp > num_tested: 0 of 3590` rows where both are non-null (e.g. state full-year 2025 Algebra CC: 118,099 ≤ 143,619). The invariant holds everywhere today and is definitionally true.
- **Location**: `main()` → `write_data_dictionary(quality_checks=[...])` in `transform.py`
- **Suggested fix**: Add a consistency check: `SELECT COUNT(*) FROM {object} WHERE num_received_sgp IS NOT NULL AND num_tested IS NOT NULL AND num_received_sgp > num_tested` with `mustBe: 0`. Gold parquet is unchanged, so v1 parity is preserved; only the contract gains a 29th check.

## Notes

- schema_hash `d7c32f13f97e8007fd0d61f7d6c01362a0ccef84152934bcec5f4c5835925491`; validation 21 pass / 0 fail / 0 warning; v1 parity MATCH (`8b4e9b2a…`).
- Risk-hypothesis disposition: 1 (Asian/PI) N/A — no demographics; 2 (rename typo) ruled out via NULL sweep + per-era traces; 3 (year attribution) verified with bronze title-row dates; 4 (derived aggregation) N/A — aggregates from bronze, feasibility exact; 5 (dedup inversion) N/A — no overlap years; 6 (mutual exclusivity) N/A; 7 (wrong mapping) ruled out — 121/121 entries reviewed.
- Two bronze-published campus rows where the 7-digit district suffix ≠ school_code (`7820109`/`0108` Mountain Education, `7991895`/`1894` GA Academy for the Blind, Spring 2017) are faithful to bronze and both pairs exist verbatim in the schools dimension — not transform artifacts.
- year=2024 has no `algebra_concepts_and_connections` rows because the harvested Spring-2024 / Full-Year-2023-2024 Algebra CC sheets are empty templates (the two state template rows are the only identity-bearing rows filtered in 2023–2025). Documented in the contract notes; re-harvest would be needed to ingest GaDOE's separately published combined Winter+Spring 2024 Algebra CC results.
- 373 rows carry `num_received_sgp` with the rest of the SGP block suppressed (`'--'`) — partial suppression is real in this source, which is why no SGP co-null check was (correctly) authored. The lexile pair has no partial suppression today (0 rows with exactly one of the pair); a co-null check would be optional and slightly risky for future years.
- The 2015 state files publish 8 content areas, not the structure doc's "ten rows" — bronze-verified; doc imprecision only.
- AWS profile broken per task context — S3 not touched; review used local gold (canonical for this rebuild step).
