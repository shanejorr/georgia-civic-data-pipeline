# Data Review: juvenile_population

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

The gold data is accurate. All value-level spot checks (global extremes + one entity per
axis) match bronze exactly; row counts reconcile perfectly across all 35 years (156,800
bronze cells − 11,200 ethnicity cells folded into columns = 145,600 gold rows); every
categorical map entry is semantically correct against `src/utils/demographics.py`; and the
§5b `Asian → asian_pacific_islander` remap is proven by an exact math test (race buckets
sum to the juvenile total, ratio = 1.0000). All 15 contract quality checks and both FK
sweeps pass. **v1 parity: no v1 baseline (topic is post-v1)** — `docs/rebuild/v1-baseline.yaml`
has no `criminal_justice/ojjdp/juvenile_population` entry. No Required Fixes, no
NEEDS_JUDGMENT items. (The prior report's single fix — bronze doc mis-stating "27 CSV files"
— is resolved: the doc now reads "28 CSV files".)

## Manifest Verification

Categorical map coverage (from `_transform_manifest.json`; every `unmapped_count` = 0):

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| demographic | 7 | 7 labels | 0 | PASS |
| age_group | 27 files → 20 codes | 27 filenames | 0 | PASS |
| county_fips | 160 names | 160 (All Counties + 159) | 0 | PASS |

**demographic — full map review (2b, 100% coverage):**

| Bronze → Gold | Correct? |
|---------------|----------|
| `All` → `all` | ✓ aggregate total |
| `American Indian` → `native_american` | ✓ canonical race code for American Indian |
| `Asian` → `asian_pacific_islander` | ✓ §5b combined pre-1997-OMB bucket (topic-local remap of `Asian/Pacific Islander` label; proven by exact race-sum math test below) |
| `Black` → `black` | ✓ |
| `White` → `white` | ✓ |
| `Female` → `female` | ✓ |
| `Male` → `male` | ✓ |

All seven land in the shared `race`/`gender`/`aggregate` demographic categories; no
`asian` or `pacific_islander` split key is emitted alongside `asian_pacific_islander`
(mutual exclusivity preserved — see 2f).

**age_group — full map review (2b):** each of the 18 single-age files maps to its two-digit
code (`age_00.csv`→`00` … `age_17.csv`→`17`), `all_ages.csv`→`all_ages`, `juveniles_age00_17.csv`
and the six sex/race juvenile files →`00_17`. All semantically correct (the sex/race files
carry the juvenile-total age slice; single-age and all_ages files carry `demographic='all'`).

**county_fips — full map review (2b):** 159 county names → their 5-digit FIPS
(`Fulton County`→`13121`, `Spalding County`→`13255`, …); the one documented mismatch
`De Kalb County` → `13089` resolved via the `COUNTY_NAME_OVERRIDES` spacing variant
(verified present in gold); `All Counties` → `state_row_no_county_fips` marker (state rows
get NULL `county_fips`). No unmatched names.

**2c Contract cross-check:** `gold_values_produced` equals the contract `enum` exactly —
demographic {all, asian_pacific_islander, black, female, male, native_american, white} (7);
age_group {00, 00_17, 01–17, all_ages} (20). PASS.

**Row-count reconciliation (3a):** identical every year 1990–2024 — bronze 4,480, gold
4,160, filtered 320 (expansion 0.9286 = 26/28 base files). Totals: bronze 156,800, gold
145,600, filtered 11,200 (`ethnicity_marginal_rows_pivoted_to_partition_columns`, = 2 files
× 160 rows × 35 years). Actual parquet height = 145,600 = manifest `total_gold` (3b). PASS.

## Column Coverage

| Bronze Column | Gold Column | Status |
|---------------|-------------|--------|
| counts (county name) | county_fips | MAPPED (name→FIPS; De Kalb override; All Counties→NULL) |
| counts (county name) | — | CORRECTLY EXCLUDED (county_name lives in counties dim) |
| 1990 … 2024 (headers) | year | MAPPED (unpivot to Int32) |
| filename sex/race slice | demographic | MAPPED |
| filename ethnicity slice | hispanic_population / not_hispanic_population | MAPPED (served as metric partition columns, not demographic rows — resolved design decision, see Notes) |
| filename age slice | age_group | MAPPED |
| cell values | population | MAPPED (working name `juvenile_population` renamed to `population` — column also carries all_ages total resident pop) |
| Total | — | CORRECTLY EXCLUDED (row sum; verified against year sum in `_verify_export`, then dropped) |
| trailing empty column | — | CORRECTLY EXCLUDED (trailing-comma artifact) |
| preamble/footer rows | — | CORRECTLY EXCLUDED (provenance only) |

No fabricated columns: all 7 gold columns trace to bronze. **Contract prose fidelity:** the
contract `purpose`/`limitations`/`null_semantics` and per-column descriptions agree with
`bronze-data-structure.md` on every audited point (year range 1990–2024; no suppression /
full 159-county coverage; counts not percentages; bridged race with Asian-includes-PI and
no multiracial bucket; ethnicity served as columns; all `not_in_gold` claims). No
contradictions found.

## Value-Level Spot Checks

Extreme rows first (4a), then one ordinary entity per axis (4b). Each gold value was traced
back to the quoted bronze line.

| Trace | Bronze (file, row, cell) | Gold | Verdict |
|-------|--------------------------|------|---------|
| Global max population | `all_ages` / `All Counties` / 2024 = **11180878** | 11,180,878 (2024, state, all_ages) | MATCH (≈ GA 2024 resident pop 11.18M) |
| all_ages state 1990 | `all_ages` / `All Counties` / 1990 = **6512602** | 6,512,602 | MATCH |
| County max population 2024 | Fulton all_ages ≈ 1.09M | 1,090,354 (13121, all, all_ages) | MATCH (Fulton scale) |
| Global min population | small-county race buckets = 0 | 743 rows = 0 (e.g. 1990 Atkinson/Bacon asian_pacific_islander & native_american) | MATCH (real zeros) |
| Juvenile total state 2024 | `juveniles_age00_17` / `All Counties` / 2024 = **2540751** | 2,540,751 | MATCH |
| Spalding juvenile total 2024 | `juveniles_age00_17` / `Spalding County` / 2024 = **16130** | 16,130 (13255, all, 00_17) | MATCH (= contract example) |
| Asian/PI Fulton | `race_asian` / `Fulton County` / 1990=**2335**, 2024=**20118** | 2,335 / 20,118 (13121, asian_pacific_islander, 00_17) | MATCH |
| Male Fulton | `sex_male` / `Fulton County` / 1990=**80721**, 2024=**113166** | 80,721 / 113,166 (13121, male, 00_17) | MATCH |
| Single age 10 state | `age_10` / `All Counties` / 1990=**101705**, 2024=**143570** | 101,705 / 143,570 (state, all, age 10) | MATCH (year correctly from wide header, not file slot) |

**Partition math (positive evidence):** at year=2024, age_group=00_17, state level —
male+female = 2,540,751 = total; hispanic+not_hispanic = 2,540,751 = population;
4 race buckets = 2,540,751 = total (exact, ratio 1.0000 → confirms combined Asian/PI bucket
and multiracial-allocated-into-4 convention).

## Validation Cross-Read

`_validation.json`: **passed=true**, 19 pass / 0 fail / 1 warning. The warning is
`tidy_format` flagging `hispanic_population` as "possible wide-format" because the name
contains `hispanic` — a documented false positive: ethnicity is deliberately served as
metric partition columns (nibrs_arrests precedent), enforced by the
`ethnicity_columns_structural_nulls` quality check. `contract_parquet_schema`,
`contract_quality_sql` (all 15), `grain_uniqueness` (0 dups over
[year, county_fips, demographic, age_group]), and `foreign_keys` (county_fips→counties 159
keys; demographic→demographics 7 keys) all pass (5a). schema_hash:
`629af9781d613887eda60bbcdb8475c5908de80f14f72718d304f03f73fef767`.

**§4b masking audit (5b):** N/A — no `_null_*` helpers and no masks; `masked_values` /
`read_loss` sections are absent (= zero events). Source has full coverage and no
suppression; the transform hard-stops on any NULL introduced by casting.

**§15b coverage judgment (5c):** the contract authors 9 cross-column quality checks
(+ 6 auto-derived enum/range checks). They cover every documented invariant: sex partition,
race partition, ethnicity partition, single-ages-sum-to-total, state=county sum,
juveniles≤total-population, ethnicity structural nulls, one-way-marginal structure, and
population-never-null. Comprehensive — no obvious invariant missing.

**v1 parity (5d):** no v1 baseline — `v1-baseline.yaml` has no
`criminal_justice/ojjdp/juvenile_population` entry (old=None). Topic is post-v1; not a
divergence.

## Cross-Era Consistency

Single era (1990–2024; the 28 files are disjoint one-way slices with identical layout — no
era boundaries, no overlap years). **Dedup tie-break (4e): N/A** — every
(year, county, demographic, age_group) cell comes from exactly one file; the collision
guard runs before dedup and would hard-error on any divergent duplicate. **Cross-year NULL
sweep (3c):** `population` has zero NULLs in every year; `hispanic_population` /
`not_hispanic_population` are ≥95% NULL in *every* year — the intended structural pattern
(populated only on the demographic='all', age_group='00_17' rows, ~3.85% of rows/year),
documented in the contract `null_meaning` and enforced by a quality check; not an
era-localized rename bug. **Year continuity (3d):** state juvenile total moves smoothly
(largest single-year change 2.60% at 1992→1993); no >10× jumps anywhere. **State=county
reconciliation (4d):** state rows come from bronze `All Counties`; verified exact for 2024
juvenile total across all + each race bucket (e.g. black 949,877 = 949,877; white
1,421,364 = 1,421,364), consistent with the `state_row_equals_county_sum` quality check.

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | Only `Total` (verified vs year-sum then dropped) and the trailing-empty column dropped; `_verify_export` hard-stops on missing year/Total columns |
| Era routing correctness | N/A | Single era; slice identity asserted per file (`Selecting:` preamble must carry the filename's filter) |
| Filter logic logged + justified | PASS | 11,200 ethnicity rows recorded as `filtered_explicit` with reason; folded into partition columns |
| Normalization map completeness | PASS | All 7 bronze demographic labels + all 27 filenames + 160 county names mapped; `unmapped_count`=0 everywhere |
| `strict=False` casts | PASS | `population` cast guarded — any resulting NULL raises (no suppression in source); `Total` cast guarded by parse-integrity check |
| Dedup keys + tie-break | PASS | Collision guard first; disjoint slices make duplicates impossible; `sort_col=population` documented safety net |
| Year extraction | PASS | From wide column headers (verified: `age_10` 1990 header → gold year=1990), not the file's record slot |
| §4b masks (5b) | N/A | No masks; no impossible values to NULL |
| A/PI conflation (Risk 1) | PASS | `asian_pacific_islander` from explicit combined bronze label; race-sum math exact |
| Demographic mutual exclusivity (Risk 6) | PASS | Single race convention; no split+rollup double publication |

## Notes

- schema_hash: `629af9781d613887eda60bbcdb8475c5908de80f14f72718d304f03f73fef767`
- Validation summary: 19 pass / 0 fail / 1 warning (documented `tidy_format` false positive).
- **Ethnicity design decision (resolved):** the bronze structure doc recommended either
  adding an `ethnicity` demographic category or omitting the ethnicity files. The transform
  chose a third, well-grounded path — serving Hispanic/non-Hispanic as `hispanic_population`
  / `not_hispanic_population` metric partition columns (nibrs_arrests precedent) — which
  satisfies the underlying mutual-exclusivity concern (bridged-race buckets include Hispanic
  persons, so a `hispanic` demographic row would double-count the race axis) while keeping
  Hispanic denominators available. Documented in the module docstring and contract. Not a
  finding.
- Grain: year × county_fips × demographic × age_group, one-way marginals only (sex/race
  splits exist only at age_group='00_17'; single ages / all_ages only at demographic='all')
  — enforced by `demographic_splits_only_for_juvenile_total`.
