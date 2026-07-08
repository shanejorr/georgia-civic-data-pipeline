# Data Review: out_of_home_placement

**Date**: 2026-07-06
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Bronze-to-gold accuracy is clean end-to-end. All 21 years (2005-2025) reconcile exactly under `(bronze − 1 OUT OF STATE row) × 5 = gold`; every extreme-row and ordinary trace MATCHes bronze verbatim (values, race splits, and by-design race-row NULLs); the single categorical map is semantically correct with zero unmapped values; and validation passes 19/0/0 (15 contract quality checks, FKs, grain uniqueness, geography nulling). No Asian/PI conflation risk — the source publishes exactly four exhaustive race buckets (race sums ≡ totals, ratio 1.0000) and the `other`-absorbs-Asian/PI convention is documented in the contract. **v1 parity: no baseline (post-v1)** — `docs/rebuild/v1-baseline.yaml` has no `criminal_justice` entries, so the parity script's `DIFFERS (v1: None)` is a null-vs-hash artifact, not a divergence.

## Manifest Verification

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| demographic | 5 | 5 (All, Black, Hispanic, Other, White) | 0 | PASS |

Full map review (`demographic` — labels are transform-controlled unpivot literals; the effective `DEMOGRAPHIC_ALIASES` slice is recorded per §4.3a):

| Bronze → Gold | Correct? |
|---------------|----------|
| ALL → all | ✓ — parent-total rows carrying all five measures |
| BLACK → black | ✓ — from `FelonyCommitBlack` / `AllStpAdmissionBlack` |
| WHITE → white | ✓ — from `FelonyCommitWhite` / `AllStpAdmissionWhite` |
| HISPANIC → hispanic | ✓ — source treats Hispanic as a race-level bucket (exhaustive proof); demographics dim classes it `race` |
| OTHER → other | ✓ — absorbs Asian/PI/Native American/multiracial/unknown per the exhaustiveness identity; documented in the contract `demographic` description |

- **2a Completeness**: `bronze_values_seen` = {All, Black, Hispanic, Other, White} matches the structure doc's four race-split columns + the synthesized `all` label. No documented value unencountered. PASS.
- **2c Contract cross-check**: `gold_values_produced` = [all, black, hispanic, other, white] ≡ contract `enum`. PASS.
- **2d Unmapped**: 0. PASS.
- **2e Asian/PI conflation (Risk 1)**: N/A with positive evidence. No `asian` key in gold and no combined-label remap. `grep` returns only the structure-doc section that documents the *absence* of any Asian/PI/NHPI bucket (`NO_NHPI_LABEL_IN_BRONZE`). Math test executed at 2025 statewide: `felony_commitments all_sum=369 race_sum=369 ratio=1.0000`; `all_stp_admissions all_sum=389 race_sum=389 ratio=1.0000` — the four buckets are exhaustive, so no separate Asian bucket exists to conflate. The identity is permanently enforced by two contract quality checks (`race_*_sum_to_total`). PASS.
- **2f Mutual exclusivity (Risk 6)**: PASS — single convention; no rollup key coexists with split keys (`asian_pacific_islander` / `asian` / `pacific_islander` all absent). The four race buckets are mutually exclusive and exhaustive; `all` is the only overlap.

Row-count reconciliation (manifest `row_counts` vs formula `(bronze − 1 OUT OF STATE row) × 5`):

| Year | Bronze | −OOS ×5 | Gold | Match | | Year | Bronze | −OOS ×5 | Gold | Match |
|------|--------|---------|------|-------|-|------|--------|---------|------|-------|
| 2005 | 147 | 730 | 730 | ✓ | | 2016 | 132 | 655 | 655 | ✓ |
| 2006 | 150 | 745 | 745 | ✓ | | 2017 | 140 | 695 | 695 | ✓ |
| 2007 | 153 | 760 | 760 | ✓ | | 2018 | 136 | 675 | 675 | ✓ |
| 2008 | 153 | 760 | 760 | ✓ | | 2019 | 138 | 685 | 685 | ✓ |
| 2009 | 156 | 775 | 775 | ✓ | | 2020 | 107 | 530 | 530 | ✓ |
| 2010 | 156 | 775 | 775 | ✓ | | 2021 | 127 | 630 | 630 | ✓ |
| 2011 | 151 | 750 | 750 | ✓ | | 2022 | 130 | 645 | 645 | ✓ |
| 2012 | 152 | 755 | 755 | ✓ | | 2023 | 116 | 575 | 575 | ✓ |
| 2013 | 149 | 740 | 740 | ✓ | | 2024 | 127 | 630 | 630 | ✓ |
| 2014 | 147 | 730 | 730 | ✓ | | 2025 | 117 | 580 | 580 | ✓ |
| 2015 | 137 | 680 | 680 | ✓ | | | | | | |

Total: (2,921 − 21) × 5 = 14,500 = manifest `total_gold` = actual parquet row count (read all 21 partitions: 14,500). `filtered_explicit` = 21, all reason `out_of_state_pseudo_county_row` (exactly one per year — matches the 21 OUT OF STATE bronze rows). Expansion factor ~4.96 uniform (5x per kept row, diluted by the one dropped OOS row per year). All 21 expected years present, no gaps. PASS.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| CountyName | — | CORRECTLY EXCLUDED (dimension attribute; used for OOS filter + name↔FIPS guard, then dropped) |
| PeriodYear | year | MAPPED (strict Int32 cast) |
| CountyFips | county_fips | MAPPED (Utf8, `^13\d{3}$` guard + counties-dimension pair cross-check) |
| AllCommitments | all_commitments | MAPPED (`all` rows only) |
| FelonyCommitments | felony_commitments | MAPPED (`all` + race rows) |
| FelonyCommitmentsOhp | felony_commitments_ohp | MAPPED (`all` rows only; key metric) |
| AllStpAdmissions | all_stp_admissions | MAPPED (`all` + race rows) |
| FelonyStpAdmissions | felony_stp_admissions | MAPPED (`all` rows only) |
| FelonyCommitBlack/White/Hispanic/Other | demographic + felony_commitments | MAPPED (unpivot → race rows) |
| AllStpAdmissionBlack/White/Hispanic/Other | demographic + all_stp_admissions | MAPPED (unpivot → race rows) |

All 16 bronze columns accounted for; no gold column lacks a bronze source (no fabrication). Rename maps checked against the structure doc's Gold Schema Classification — no typos, no unhandled conditional columns.

**Contract prose fidelity** (checked against `bronze-data-structure.md` for contradictions): year range 2005-2025 ✓, no suppression / `suppressed_to_null: false` ✓, no percentage columns (all counts) ✓, four-bucket race convention with Hispanic as race-level and `other` as catch-all ✓, OUT OF STATE excluded with invalid FIPS ✓, sparse-panel absence≈zero ✓, race splits only on `felony_commitments` + `all_stp_admissions` ✓, `county_fips` "Never NULL in this topic" ✓ (verified 0 nulls in gold), PeriodYear calendar-vs-fiscal ambiguity disclosed ✓. No contradictions.

## Value-Level Spot Checks

Extreme rows first (global max of every metric), then ordinary + min traces. Bronze quoted verbatim from `decision_point_raw_data_ohp_stp_2026-06.csv` (header order: CountyName, PeriodYear, CountyFips, AllCommitments, FelonyCommitments, FelonyCommitmentsOhp, AllStpAdmissions, FelonyStpAdmissions, FCBlack, FCWhite, FCHispanic, FCOther, STPBlack, STPWhite, STPHispanic, STPOther).

1. **Global max `all_commitments`=417, `felony_commitments`=179 — DeKalb 2007**: bronze `DEKALB,2007,13089,417,179,102,118,58,167,3,7,2,104,4,9,1` → gold `all` = 417/179/102/118/58; race rows black FC=167 STP=104, white FC=3 STP=4, hispanic FC=7 STP=9, other FC=2 STP=1; the three unsplit metrics NULL on all four race rows. Race sums: FC 167+3+7+2=179 ✓, STP 104+4+9+1=118 ✓. **MATCH** (also rules out any Black↔White or FC↔STP block swap).
2. **Global max `felony_commitments_ohp`=102 (tie) — Chatham 2006**: bronze `CHATHAM,2006,13051,233,123,102,203,63,113,6,2,2,189,13,1,0` → gold `all` = 233/123/102/203/63; race FC 113+6+2+2=123 ✓, STP 189+13+1+0=203 ✓. **MATCH**.
3. **Global max `all_stp_admissions`=277 — Chatham 2009**: bronze `CHATHAM,2009,13051,146,84,64,277,123,75,7,1,1,243,31,1,2` → gold `all` = 146/84/64/277/123; race FC 75+7+1+1=84 ✓, STP 243+31+1+2=277 ✓. **MATCH**.
4. **Global max `felony_stp_admissions`=187 — Muscogee 2010**: bronze `MUSCOGEE,2010,13215,82,74,63,225,187,69,4,1,0,210,13,1,1` → gold `all` = 82/74/63/225/187; race FC 69+4+1+0=74 ✓, STP 210+13+1+1=225 ✓. **MATCH**.
5. **Ordinary trace — Laurens 2021**: bronze `LAURENS,2021,13175,11,10,8,9,4,7,3,0,0,6,3,0,0` → gold `all` = 11/10/8/9/4; black 7/6, white 3/3, hispanic 0/0, other 0/0. FC 7+3+0+0=10 ✓, STP 6+3+0+0=9 ✓. **MATCH** (single era — one entity satisfies per-era coverage).
6. **Min / zero-preservation trace — Twiggs 2018**: bronze `TWIGGS,2018,13289,4,4,4,0,0,4,0,0,0,0,0,0,0` → gold `all` = 4/4/4/0/0; race rows carry FC black=4, others 0; STP all 0 — zeros preserved as 0, **not** NULLed. **MATCH** — `zero_is_real` semantics correct.

- **4a/4b traces**: covered above — 5 extreme + 1 min/ordinary across the single era, all columns, all MATCH.
- **4c Sentinel year-attribution (Risk 3)**: N/A — `year` comes solely from the `PeriodYear` column (strict Int32 cast); the filename's `2026-06` is the WordPress upload month and is never parsed into a data year. The only year-bearing literals in transform.py are the era name/comments.
- **4d Aggregate reconciliation (Risk 4)**: no derived aggregates (no state rows synthesized). The only bronze-published aggregate is the `all` row; its race-sum identity is the reconciliation and is enforced exactly by the two `race_*_sum_to_total` contract checks (0 violations this run) plus the 2e math test (ratio 1.0000). Per-year statewide sums of all five metrics also traced against bronze: exact match in every year (e.g. 2007 AllCommitments Σ=3,191; 2025 Σ=503). PASS.
- **4e Dedup tie-break (Risk 5)**: N/A — single file, single era, no overlap years; bronze (CountyName, PeriodYear) grain verified unique; `assert_no_natural_key_collisions` runs before dedup.
- **4f Suppression semantics**: N/A — no suppression markers anywhere (counts of 1 and 2 published as-is; validator `no_suppression_markers` pass). Contract emitted with `suppressed_to_null: false`; race-row NULLs are correctly described as "not published for race rows", never "suppressed".
- **OUT OF STATE drop trace**: 21 bronze rows quoted — FIPS `13222` for 2005-2022 (e.g. `OUT OF STATE,2005,13222,37,27,...,0`), blank for 2023-2024, literal `NULL` for 2025 (`OUT OF STATE,2025,NULL,5,5,...,0`). AllCommitments range 4-68/yr (matches contract limitations "4-68 commitments per year"); AllStpAdmissions always 0. Gold rows with `county_fips='13222'` or NULL: **0**; distinct gold counties: 159; all FIPS match `^13\d{3}$`. All 21 recorded via `record_filtered`. **MATCH**.

## Validation Cross-Read

- `_validation.json` (2026-07-02T13:21:02Z): **passed=true, 19 pass / 0 fail / 0 warning** — including `contract_parquet_schema` (21 files), `contract_quality_sql` (all 15 checks), `grain_uniqueness` (year, county_fips, demographic), `foreign_keys` (county_fips → counties: all 159 keys; demographic → demographics: all 5 keys), `geography_nulling`, `null_rate_spikes` (none).
- `schema_hash`: `a1589d9ae9e7de3e21c0b9fe09487172023a284780d9f892e5877f3a56d36b69`.
- **§4b masking audit**: no `_null_*` helpers in transform.py and no `masked_values` section in the manifest — consistent. Bronze min is 0 on every metric with no impossible values; the bogus `13222` FIPS is handled by the row filter (documented), not a value mask. Count metrics get auto-derived `≥ 0` range checks. PASS.
- **§15b coverage judgment**: the quality list covers the topic's real cross-column invariants unusually thoroughly — three subset invariants (felony ≤ all commitments; OHP ≤ felony; felony STP ≤ all STP), two exact race-sum partition identities, and three structural null/populated patterns (unsplit metrics NULL on race rows; split metrics populated on race rows; all five measures populated on `all` rows). The one un-authored relation (`felony_commitments_ohp ≤ all_commitments`) is implied transitively by two enforced checks. No missing obvious invariant. PASS.
- **v1 parity** (executed verbatim):
  ```
  baseline entry present: False
  DIFFERS from v1
    v1:  None
    now: 7bfc78d900de3fff84bb700cdd2862a74b646066249faf33522687317e41431a
  ```
  **No v1 baseline (topic is post-v1)** — `docs/rebuild/v1-baseline.yaml` contains zero `criminal_justice` keys. The `DIFFERS (v1: None)` line is the script's null-vs-hash artifact, not a divergence from any prior approved gold. Not a finding.

## Cross-Era Consistency

- Single era, single file — no era boundaries, no overlap years.
- Cross-year NULL sweep (Risk 2): **0 flags**. The three unsplit metrics (`all_commitments`, `felony_commitments_ohp`, `felony_stp_admissions`) sit at a uniform 0.800 NULL rate every year (4 race rows per 5-row group, by design); `felony_commitments` and `all_stp_admissions` are 0.000 NULL everywhere. No era-localized rename signature possible or present.
- Year-over-year continuity (3d): no >10x jumps. Largest moves are bronze-native (gold ≡ bronze every year): 2020 COVID collapse (state AllCommitments 1,402→459, 0.33x) and 2021 rebound (1.97x); a 2005→2006 step-up (1,364→3,363, 2.47x — see Notes). No cumulative-publication signature (no single-year level shift that reverts).

## Transform Logic Risks

| Risk | Severity | Details |
|------|----------|---------|
| Silent column drops | PASS | `_require_columns` hard-stops on any missing expected bronze column (all 16 named); only CountyName intentionally excluded (dimension attribute) |
| Era routing correctness | PASS | Single era detected by the full 8-column FIPS+CamelCase signature; unmatched signature raises; UTF-8 BOM defensively stripped before detection |
| Filter logic logged + justified | PASS | Only filter is the OUT OF STATE drop: logged with years + sample values, recorded via `record_filtered` (21 rows), justified in module docstring + contract limitations |
| Normalization map completeness | PASS | 5/5 labels via shared `normalize_demographic_column` + recorded `DEMOGRAPHIC_ALIASES` slice; matches the structure doc exactly |
| `strict=False` casts | PASS | None — year and all counts use `strict=True` casts (junk fails loudly); FIPS is regex-guarded, not cast |
| Dedup keys + tie-break | PASS | Collision guard runs before dedup; grain verified unique upstream; `sort_col="felony_commitments"` is populated on every gold row, so the safety net cannot invert |
| Year extraction | PASS | From `PeriodYear` column only, strict cast; filename month never used |
| §4b masks (5b) | PASS | None needed; none present; manifest agrees |

## Notes

- schema_hash `a1589d9ae9e7de3e21c0b9fe09487172023a284780d9f892e5877f3a56d36b69`; validation 19 pass / 0 fail / 0 warning; read_loss events: 0; unmapped: 0; masked: 0; filtered: 21 (all OUT OF STATE, one per year).
- **2005 level observation (no action recommended).** State-summed commitments in 2005 (AllCommitments=1,364; FelonyCommitments=633) are roughly half the 2006-2008 level (~3,200 / ~1,600), while STP admissions show a much smaller step (2,744→3,625). Gold matches bronze exactly in every year, so this is bronze-native — most plausibly first-year ramp-up of the source's reporting, not a transform artifact (it does not revert, so it is not the cumulative-publication signature). No fix; if the clearinghouse ever documents partial 2005 coverage, add one limitations sentence.
- `PeriodYear` calendar-vs-fiscal ambiguity is source-level and already disclosed in the contract's year `description` and `limitations`.
- The contract quality suite makes the race-sum exhaustiveness identity (the load-bearing fact behind the four-bucket race convention, and the reason there is no split-vs-rollup duplication) permanently enforced — a future source revision that breaks it will fail validation rather than ship.
