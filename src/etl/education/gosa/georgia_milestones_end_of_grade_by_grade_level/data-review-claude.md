# Data Review: georgia_milestones_end_of_grade_eog_assessment_by_grade

**Date**: 2026-06-11
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

No required fixes. v1 parity: **MATCH — byte-identical with v1 gold** (verified via `compute_gold_sha256` against `docs/rebuild/v1-baseline.yaml`). Bronze rows equal gold rows exactly (1,995,262; zero filters, zero dedup losses, zero read loss, zero masks), every categorical mapping is semantically correct with `unmapped_count = 0`, the split Asian/Pacific-Islander race convention is verified positively (separate NHPI rows in all 9 bronze files; the 7 split race buckets partition the state cohort at ratio 1.0000), all extreme- and ordinary-row traces match bronze exactly, and the Foster Care anomaly accounting (deviator counts, all-zeros placeholders, 28 state-level count-shortfall rows) reproduces in gold. One judgment call: the all-four-zeros Foster Care placeholder shares (4,436 rows, 2022–2024) are preserved as published even though 477 of them sit alongside a published `num_tested ≥ 1`, making the zero-set collectively impossible as real shares — preservation is documented and standard-conformant, but deserves explicit sign-off.

## Manifest Verification

### Categorical map summary

| Column | Map entries | Bronze values seen | Unmapped | Status |
|---|---|---|---|---|
| `demographic` | 22 | 22 (matches structure doc: 18 core + Active Duty + Homeless + Foster Care + Military Connected) | 0 | PASS |
| `grade_level` | 12 (6 unpadded + 6 padded) | 12 (`3`–`8` from 2015/2019; `03`–`08` elsewhere) | 0 | PASS |
| `subject` | 5 topic-local (+6 shared-normalizer entries never seen) | 5 | 0 | PASS |

### Full map review — `demographic` (every entry)

| Bronze (upper) | Gold | Correct? |
|---|---|---|
| ALL STUDENTS | `all` | Yes — aggregate lane |
| ASIAN | `asian` | Yes — split convention proven (see §2e below); bare Asian is genuinely Asian-only here |
| BLACK OR AFRICAN AMERICAN | `black` | Yes |
| HISPANIC | `hispanic` | Yes |
| WHITE | `white` | Yes |
| TWO OR MORE RACES | `multiracial` | Yes |
| AMERICAN INDIAN OR ALASKAN NATIVE | `native_american` | Yes |
| NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER | `pacific_islander` | Yes — the post-1997 OMB NHPI-only key |
| MALE / FEMALE | `male` / `female` | Yes |
| ECONOMICALLY DISADVANTAGED / NOT ECONOMICALLY DISADVANTAGED | `economically_disadvantaged` / `not_economically_disadvantaged` | Yes — polarity preserved |
| LIMITED ENGLISH PROFICIENT / NOT LIMITED ENGLISH PROFICIENT | `english_learners` / `not_english_learners` | Yes — LEP is the legacy term for EL; canonical `not_` negation per §5a |
| MIGRANT / NON-MIGRANT | `migrant` / `not_migrant` | Yes |
| STUDENTS WITH DISABILITIES / STUDENTS WITHOUT DISABILITIES | `students_with_disabilities` / `students_without_disabilities` | Yes |
| HOMELESS | `homeless` | Yes (2021+) |
| ACTIVE DUTY | `active_duty` | Yes — 2021-only label kept as its own key |
| MILITARY CONNECTED | `military_connected` | Yes — 2022+ renamed label kept distinct; non-additivity documented in contract |
| FOSTER CARE | `foster_care` | Yes (2022+) |

`active_duty` and `military_connected` never co-occur in a year (2021-only vs 2022+), so no two bronze labels collapse to one canonical key within a year — the absence of `aggregate_demographic_collisions()` is correct, and `assert_no_natural_key_collisions` guards the future.

### Full map review — `grade_level`

`"3"→"03"`, `"4"→"04"`, `"5"→"05"`, `"6"→"06"`, `"7"→"07"`, `"8"→"08"` plus padded identity entries — all correct per §16 (zero-padded 2-char). Gold produces exactly `03`–`08`.

### Full map review — `subject`

| Bronze | Gold | Correct? |
|---|---|---|
| English Language Arts | `english_language_arts` | Yes |
| Mathematics | `mathematics` | Yes |
| Science | `science` | Yes |
| Social Studies | `social_studies` | Yes |
| Physical Science | `physical_science` | Yes — real 2022+ 8th-grade accelerated addition, correctly NOT merged with `science` |

The 6 extra `map_used` entries (`united_states_history→us_history`, etc.) are the shared `SUBJECT_NORMALIZATION_MAP` recorded alongside; none appear in `bronze_values_seen` — no-ops as documented.

**2c contract cross-check**: contract enum SQL (`demographic_in_allowed_values` 22 values, `grade_level_in_allowed_values` 6 values, `subject_in_allowed_values` 5 values) equals `gold_values_produced` exactly for all three columns. PASS.

**2d unmapped**: 0 for all three columns. PASS.

### 2e Asian/Pacific Islander conflation (Risk 1)

- Grep: `Native Hawaiian or Other Pacific Islander` label present in the structure doc AND counted in raw bronze: 72/82/53/50/46/17/50/61/2,206 rows across the 2015–2024 files respectively — **NHPI published separately in all 9 files**.
- Math test (executed, state level, `demographic` race buckets vs `all`, grade 05 ELA):
  - `year=2023: num_tested total=126232 race_sum=126229 ratio=1.0000`
  - `year=2024: num_tested total=126179 race_sum=126179 ratio=1.0000`
  The 7 **split** buckets (`asian`, `pacific_islander`, `black`, `hispanic`, `white`, `multiracial`, `native_american`) partition the cohort exactly — positive proof that bare "Asian" excludes NHPI. **PASS — split convention correct**, consistent with §5b's known-split list (the "Georgia Milestones by-grade EOC/EOG topics").

### 2f Demographic mutual exclusivity (Risk 6)

`gold_values_produced` contains `asian` and `pacific_islander` and NO `asian_pacific_islander` — single convention, no rollup coexistence possible. **PASS — single convention.**

### Row-count reconciliation

| Year | Bronze | Gold | Filtered | Expansion | Structure-doc bronze | Match |
|---|---|---|---|---|---|---|
| 2015 | 288,475 | 288,475 | 0 | 1.0 | 288,475 | YES |
| 2016 | 290,060 | 290,060 | 0 | 1.0 | 290,060 | YES |
| 2017 | 194,195 | 194,195 | 0 | 1.0 | 194,195 | YES |
| 2018 | 194,378 | 194,378 | 0 | 1.0 | 194,378 | YES |
| 2019 | 195,503 | 195,503 | 0 | 1.0 | 195,503 | YES |
| 2021 | 170,679 | 170,679 | 0 | 1.0 | 170,679 | YES |
| 2022 | 190,320 | 190,320 | 0 | 1.0 | 190,320 | YES |
| 2023 | 192,568 | 192,568 | 0 | 1.0 | 192,568 | YES |
| 2024 | 279,084 | 279,084 | 0 | 1.0 | 279,084 | YES |
| **Total** | **1,995,262** | **1,995,262** | **0** | | | |

Actual parquet row count = 1,995,262 = manifest `total_gold` (3b PASS). All 9 expected years present; 2020 correctly absent (COVID — no bronze file, no fabrication). The 2017 drop (~33%) and the 2024 jump (+45%) are both explained by the structure doc (Science/Social-Studies grade restriction; more charter entities + more published cells).

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `#ASSMT_CD` (Era 2) | — | CORRECTLY EXCLUDED (constant `EOG_by_GRADE`, validated then dropped; hard-fails on any other value) |
| `LONG_SCHOOL_YEAR` | `year` (Int32) | MAPPED (ending-year parse, cross-checked vs filename) |
| `SCHOOL_DISTRCT_CD` | `district_code` | MAPPED (zfill(3); 7-digit codes pass through; `ALL`→NULL) |
| `SCHOOL_DSTRCT_NM` | — | CORRECTLY EXCLUDED (dimension attribute) |
| `INSTN_NUMBER` | `school_code` | MAPPED (zfill(4) repairs unpadded 2015/2019; `ALL`→NULL) |
| `INSTN_NAME` | — | CORRECTLY EXCLUDED (dimension attribute) |
| `ACDMC_LVL` | `grade_level` | MAPPED (canonical 2-char string; the structure doc's Int32 suggestion is overridden by §16's VARCHAR mandate — correct) |
| `SUBGROUP_NAME` | `demographic` | MAPPED (shared normalizer) |
| `TEST_CMPNT_TYP_NM` | `subject` | MAPPED (the structure doc suggested `test_component`, but §16 reserves that for non-academic sections; `subject` is the canonical choice for academic content — correct) |
| `NUM_TESTED_CNT` | `num_tested` | MAPPED (Int64, strict=False) |
| `BEGIN_CNT` / `DEVELOPING_CNT` / `PROFICIENT_CNT` / `DISTINGUISHED_CNT` | `num_{beginning,developing,proficient,distinguished}_learner` | MAPPED (canonical §16 proficiency-band names supersede the structure doc's `*_count` suggestions — correct) |
| `BEGIN_PCT` / `DEVELOPING_PCT` / `PROFICIENT_PCT` / `DISTINGUISHED_PCT` | `pct_{beginning,developing,proficient,distinguished}_learner` | MAPPED (÷100 to 0–1 scale) |
| — (derived) | `pct_developing_learner_or_above`, `pct_proficient_learner_or_above` | DERIVED at transform time per §16 (bronze does not publish them); not fabrication — documented derivation with NULL propagation |

No gold column lacks a bronze (or documented-derivation) source. `_require_columns` hard-stops on any missing expected bronze column in either era.

## Value-Level Spot Checks

### Extreme-row traces (global per-metric max/min from manifest stats)

1. **`num_tested` global MAX 137,213 (2018)** — bronze:
   `"2017-18","ALL","ALL","ALL","ALL","05","All Students","English Language Arts",137213,28460,51900,43645,13208,20.7,37.8,31.8,9.6`
   Gold (state, all, 05, ELA): `num_tested=137213`, counts `28460/51900/43645/13208`, pcts `0.207/0.378/0.318/0.096`, `dev_or_above=0.792`, `prof_or_above=0.414`. **MATCH** (incl. both derived cumulatives).
2. **`num_tested` global MIN 1 (2016)** — bronze:
   `"2015-16","891","Department of Juvenile Justice","ALL","ALL","06","All Students","English Language Arts",1,,,,,,,,`
   Gold (district 891, school NULL): `num_tested=1`, all counts/pcts NULL (genuine empty CSV fields → NULL). **MATCH** — also the empty-field suppression trace for the 2016–2018 mechanism.
3. **`num_beginning_learner` global MAX 50,042 (2015)** — bronze:
   `2014-15,ALL,ALL,ALL,ALL,8,All Students,Science,130226,50042,38840,32345,8999,38.4,29.8,24.8,6.9`
   Gold: `50042`, pcts `0.384/0.298/0.248/0.069`. **MATCH** (also verifies unpadded grade `8` → `08` and unquoted-file parsing).
4. **`num_developing_learner` global MAX 64,234 (2019)** — bronze:
   `2018-19,ALL,ALL,ALL,ALL,5,All Students,Social Studies,135538,29754,64234,25955,15595,22,47.4,19.1,11.5`
   Gold: `64234`, pcts `0.22/0.474/0.191/0.115`. **MATCH**.
5. **`num_proficient_learner` global MAX 49,616 (2019)** — bronze:
   `2018-19,ALL,ALL,ALL,ALL,3,All Students,Mathematics,128610,22464,39610,49616,16920,17.5,30.8,38.6,13.2`
   Gold: `49616`, `prof_or_above=0.518`. **MATCH**.
6. **`num_distinguished_learner` global MAX 26,710 (2024, Era 2)** — bronze:
   `"EOG_by_GRADE","2023-24","ALL","ALL","ALL","ALL","08","All Students","Mathematics","129466","28868","43873","30015","26710","22.3","33.9","23.2","20.6"`
   Gold: `26710`, pcts `0.223/0.339/0.232/0.206`. **MATCH** (also verifies the Era-2 `#ASSMT_CD` drop and quoted-numeric parsing).
7. **Pct extremes** — all six pct columns: gold min 0.0 / max exactly 1.0 in the manifest stats; bounded-proportion checks pass (validator). Consistent with publisher percentages of 0 and 100.

### Ordinary traces (one per era)

8. **Era 1 (2015)** — bronze:
   `2014-15,732,Tattnall County,101,Reidsville Middle School,8,Economically Disadvantaged,Mathematics,102,16,56,26,TFS,15.7,54.9,25.5,3.9`
   Gold (`732`/`0101`, `economically_disadvantaged`, `08`, `mathematics`): `num_tested=102`, counts `16/56/26/NULL`, pcts `0.157/0.549/0.255/0.039`, `dev_or_above=0.843`, `prof_or_above=0.294`. **MATCH** — covers TFS→NULL on a count, school-code zfill repair (`101`→`0101`), and correct cumulative derivation from published (not recomputed) shares.
9. **Era 2 (2024)** — bronze:
   `"EOG_by_GRADE","2023-24","746","Walker County","0106","Chattanooga Valley Middle School","08","Economically Disadvantaged","Mathematics","118","51","48","13","TFS","43.2","40.7","11","5.1"`
   Gold (`746`/`0106`): `118`, `51/48/13/NULL`, pcts `0.432/0.407/0.11/0.051`, `dev_or_above=0.568`, `prof_or_above=0.161`. **MATCH**.

### Foster Care traces

10. **State-level count-shortfall row (2022, grade 03, mathematics)** — bronze:
    `"2021-22","ALL","ALL","ALL","ALL","03","Foster Care","Mathematics","602","200","247","130","17","33.2","41","21.6","2.8"`
    Level-count sum 200+247+130+17 = **594 < 602** tested (the documented unassigned-level shortfall); pct sum 0.986. Gold preserves every value exactly. **MATCH** — and gold-wide, count-sum ≠ num_tested occurs on exactly 7/11/10 state-level `foster_care` rows in 2022/2023/2024 and **0 rows where the sum exceeds num_tested** — the one-directional claim verified.
11. **All-four-zeros placeholder row (2024)** — bronze:
    `"EOG_by_GRADE","2023-24","601","Appling County","0177","Appling County Elementary School","03","Foster Care","Science","TFS","TFS","TFS","TFS","TFS","0","0","0","0"`
    Gold (`601`/`0177`, `foster_care`, `03`, `science`): all five counts NULL, all four pcts 0.0, both `_or_above` 0.0. **MATCH — preserved as published** (see Judgment Call 1).
12. **Anomaly census reproduces in gold**: four-pct partition deviators (|sum−1| > 0.02) = 206 / **283** / 4,738 in 2022/2023/2024, zero elsewhere, **all `foster_care`**; all-four-zeros rows = 157 / 173 / 4,106, all `foster_care`. The 283-vs-282 (2023) difference vs the structure doc is a single float-boundary row (district 706, grade 08: shares sum to 0.98; |0.98−1.0| = 0.020000000000000018 > 0.02 in float64, while the doc's bronze-scale |98−100| > 2 test excludes it) — an accounting artifact, not a data difference; the row itself is `foster_care` and its values match bronze.

### Other Step-4 items

- **4c sentinel year-attribution**: N/A as a risk — the only year-bearing content is `LONG_SCHOOL_YEAR`, and `_resolve_year` raises unless its ending year equals the filename year (each file verified to carry exactly one value). All 12 traces above land in the correct gold year.
- **4d aggregate feasibility screen** (aggregates COME FROM BRONZE — no derived rows): executed across all years — `district num_tested < max school num_tested` violations: **0 of 377,328** joined district cells; `district < visible school sum` violations: **0**. State-vs-district-sum probes: 2018 grade-05 ELA state 137,213 = Σ districts 137,213 (ratio 1.0000); 2024 same cell 126,179 = 126,179. PASS.
- **4e dedup tie-break**: N/A — 9 files, 9 distinct years (manifest `files_processed`), no overlap years; bronze = gold counts prove dedup discarded nothing.
- **4f suppression semantics**: TFS→NULL traced on counts (traces 8, 9, 11) and genuine-empty→NULL traced (trace 2). Whole-cell pct suppression: gold 2023 `num_tested` NULLs = **357** = the structure doc's 2023 `NUM_TESTED_CNT` TFS count exactly; gold 2024 `num_tested` NULLs = **85,104** = the doc's 2024 TFS count exactly. No suppression markers survive in gold (validator check passes).

## Validation Cross-Read

- `_validation.json`: `passed: true` — 20 checks pass (`contract_parquet_schema`, `contract_quality_sql`, `grain_uniqueness`, `foreign_keys`, `geography_nulling` ×3 detail levels, etc.); **1 warning**: `null_rate_spikes` on 2024 (`num_tested` 30.5% vs 0.2% median; three count columns +20–29pp) — fully explained by GOSA's 2024 extension of TFS to `NUM_TESTED_CNT` (85,104/279,084 = 30.5%, matched to bronze above) and documented in the contract `null_meaning`/description. Explained — not escalated.
- Contract `schema_hash`: `692af1c294d3905d0aeceba72f51ac9e4ab6c34b14fd9c9eb4fff20a69a28c7f`; version 1.0.0/active; 17 properties in parquet order; PK = (year, district_code, school_code, demographic, grade_level, subject); units: 5×`count`, 6×`proportion` — all correct classifications (the four level shares and both cumulatives are genuinely bounded; the snap-to-1.0 keeps them so).
- **§4b masking audit**: no `_null_*` helpers in transform.py; manifest has no `masked_values`/`reclassified` sections — consistent. N/A.
- **§15b coverage judgment**: 23 contract quality checks = 15 auto-derived + **8 authored**: partition-sum scoped to exclude `foster_care` (verified: excluding foster_care the four-level sum spans [0.999, 1.002] — margin ~0.002 as claimed), both `_or_above` reconciliations (±0.011 covering the 0.005 snap), nested-cumulative ordering, level-count ≤ num_tested, count-sum ≤ num_tested, count-sum = num_tested below state level (self-scoped by geography NULL-ness per §15b), and pct = count/num_tested within ±0.0006. This covers every cross-column invariant a hand reviewer would check; no missing obvious invariant.
- **v1 parity** (executed verbatim): `MATCH — byte-identical with v1 gold`.
- Bronze freshness gate re-run: `PASS: all 9 bronze file checksums match; no unanalyzed files`.

## Cross-Era Consistency

- **Overlap years**: none (9 files, 9 distinct years) — dedup-inversion risk N/A.
- **Era boundary (2023 Era 1 → 2024 Era 2)**: state-level `sum(num_tested)` 1,916,103 → 1,901,442 (smooth); mean `pct_proficient` 0.277 → 0.248 (plausible cohort shift). The only year-over-year level flag is 2019→2021 `sum_tested` ratio 0.65 — the documented COVID participation drop (2020 cancelled entirely), not a scale defect; pct means stay continuous (0.297 → 0.270).
- **Cross-year NULL sweep (Risk 2)**: clean — no column is ~100% NULL in any year while populated in others; no column is all-NULL everywhere.
- **Scale consistency**: pct columns 0–1 in every year (max 1.0); counts Int64 in every year; `_or_above` snap applied uniformly (6,599 dev-cumulative and 70 prof-cumulative rows had raw sums in (1.0, 1.005] snapped to 1.0; **zero** rows exceeded 1.005 — max raw 3-summand sum 1.001, matching the docstring's "bronze max sum 100.1").

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | none | PASS — `_require_columns` hard-stops on missing bronze columns; only documented exclusions (`#ASSMT_CD` validated constant, two name columns, `LONG_SCHOOL_YEAR`) |
| Era routing correctness | none | PASS — `detect_era_by_columns`, most-specific-first; manifest shows 8× era_1, 1× era_2 as expected |
| Filter logic | none | PASS — no filters exist; `total_filtered = 0`, bronze = gold per year |
| Normalization map completeness | none | PASS — 22/12/5 bronze values all mapped; `unmapped_count = 0` ×3 |
| `strict=False` casts | none | PASS — applied only to metric casts after all-Utf8 read; suppression markers pre-nulled by `read_bronze_file` |
| Dedup keys + tie-break | none | PASS — explicit `sort_col="num_tested"` documented as safety net; `assert_no_natural_key_collisions` runs first; zero rows actually deduped |
| Year extraction | none | PASS — filename year cross-checked against the file's single `LONG_SCHOOL_YEAR`; mismatch raises |
| §5b masking (unrecorded) | none | N/A — no masks exist, manifest agrees |

## NEEDS_JUDGMENT

### Judgment Call 1: Foster Care all-zeros placeholder shares are preserved as real 0.0 values
- **Severity if confirmed**: MEDIUM
- **Suspicion**: 4,436 `foster_care` rows (157 in 2022, 173 in 2023, 4,106 in 2024) publish `0,0,0,0` across the four pct columns on fully-count-suppressed cells. Gold stores them as 0.0 (and the derived `_or_above` columns inherit 0.0). For **477** of these rows (157 + 173 + 147 in 2024) a published `num_tested ≥ 1` coexists (e.g., 2022 district 611, grade 03, science: `num_tested=11`, all shares 0.0) — since the four levels partition test-takers, an all-zero share set is *collectively* impossible for a tested cell, i.e., these zeros are placeholders, not measurements. Any naive `AVG(pct_proficient_learner)` over `foster_care` rows (especially 2024, where placeholders are 4,106 rows) is biased toward zero.
- **Evidence available**: bronze line `"EOG_by_GRADE","2023-24","601","Appling County","0177",...,"03","Foster Care","Science","TFS","TFS","TFS","TFS","TFS","0","0","0","0"`; gold placeholder census by year/demographic (all `foster_care`); 2022/2023 placeholders all carry published `num_tested`; contract documents the pattern in `limitations` and the `pct_beginning_learner` description.
- **Why uncertain**: §4b's impossibility test is **per-value** — 0.0 is on the possible domain for each individual share, so the standard's default is preserve + document, which the transform follows; the collective-impossibility argument for a §4b-style mask is reasonable but is an extension of the written rule. Masking would also break v1 byte parity (currently MATCH) and the placeholder rows are excluded from the partition-sum quality check via the `foster_care` scope, so nothing enforced is violated either way.
- **Location**: `_transform_era()` pct casts in `transform.py` (no masking seam exists today; a `_null_foster_care_placeholder_pcts` helper in `main()` would be the §4b pattern).
- **If confirmed, suggested fix**: NULL the four pct columns (and the two derived `_or_above`) on rows where all four counts are suppressed AND all four shares are exactly 0 AND `demographic = 'foster_care'`, recording via `manifest.record_masked(...)` and updating the contract descriptions. **Recommendation: keep as-is** — preservation is bronze-faithful, documented in the contract, consistent with the sibling EOG/EOC topics and with v1 (parity MATCH), and the all-zeros pattern is mechanically identifiable by consumers (`num_* all NULL AND pct sum = 0`); revisit only if API consumers report aggregation confusion.

## Notes

- Contract `schema_hash`: `692af1c294d3905d0aeceba72f51ac9e4ab6c34b14fd9c9eb4fff20a69a28c7f` (version 1.0.0).
- Validation: 20 pass + 1 explained warning (`null_rate_spikes`, 2024 TFS-on-`num_tested` extension); 23 contract quality checks (8 authored) all enforced and passing.
- v1 parity: `MATCH — byte-identical with v1 gold`.
- The 2023 partition-deviator count is 283 under a strict float `> 0.02` gold-scale test vs 282 in the structure doc's bronze-scale test — one boundary row at exactly 0.98; same data, different tolerance arithmetic. Not a defect.
- Gold layout: `states/districts/schools.parquet` under 9 `year=` partitions; no empty files; `README.md` present; bronze freshness gate re-verified PASS (9/9 checksums).
- Grain/sparsity: grade×subject availability changes (Science/Social Studies grades 5+8 from 2017; Social Studies grade 8 from 2021; Physical Science grade 8 only) are preserved naturally — no fabricated cells; rare audit/retest rows (e.g., 2024 grade-03 Science) retained per the structure doc.
