# Data Review: district_sentences

**Date**: 2026-07-07
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Gold is verified accurate against bronze on this rerun: an **independent recompute of 6 of 24 fiscal years (54 of 216 gold rows, both format eras, all 8 global metric extremes) reproduced every gold value exactly** — own `.sas` layout parsing, own CSV reads, own aggregation, not the transform's code path. All three categorical maps are semantically confirmed against the structure doc / USSC codebook value labels (DISTRICT `32 = Northern, 33 = Middle, 34 = Southern`; MONSEX `0 = Male, 1 = Female, 2 = Other (FY2024+)`). v1 parity: **N/A — topic not in `docs/rebuild/v1-baseline.yaml`** (baseline covers education topics only). Validation: 19 passed / 0 failed / 0 warnings. No required fixes; no unresolved suspicions.

## Manifest Verification

| Column | Entries | Bronze seen | Unmapped | Status |
|--------|---------|-------------|----------|--------|
| `federal_district` | 3 | 32, 33, 34 | 0 | PASS |
| `offender_sex` (intermediate) | 3 | 0, 1 | 0 | PASS |
| `demographic` | 3 | All, Female, Male | 0 | PASS |

**Full map review — every entry, semantic verdict:**

| Bronze → Gold | Correct? | Evidence |
|---|---|---|
| DISTRICT `32` → `georgia_northern` | YES | Structure doc: "Georgia: 32 = Northern, 33 = Middle, 34 = Southern (NUM, range 00–96)" |
| DISTRICT `33` → `georgia_middle` | YES | same line |
| DISTRICT `34` → `georgia_southern` | YES | same line |
| MONSEX `0` → `Male` | YES | Structure doc: "`MONSEX` = sex (0 = male, 1 = female)" |
| MONSEX `1` → `Female` | YES | same line |
| MONSEX `2` → `Other` | YES | Codebook FY2024+ addition; mapped but never encountered (`bronze_values_seen` = 0, 1 only); Other/missing route to the `all` row only, never a synthesized demographic |
| demographic `ALL` → `all` | YES | `DEMOGRAPHIC_ALIASES['ALL'] == 'all'`; demographics dimension category `aggregate` |
| demographic `MALE` → `male` | YES | alias + dimension row `male / Male / gender` |
| demographic `FEMALE` → `female` | YES | alias + dimension row `female / Female / gender` |

- **2a Completeness**: every distinct bronze value documented in the structure doc appears in `bronze_values_seen`. The DISTRICT map is applied post-GA-filter, so only 32/33/34 are seen — correct by design. MONSEX `2` is documented-but-unseen (no GA `Other` rows through FY2025), consistent with the contract's "no Georgia rows yet".
- **2c Contract cross-check**: `gold_values_produced` equals the contract enums — `federal_district` (`georgia_middle/northern/southern`) and `demographic` (`all/female/male`). `offender_sex` is an intermediate map with no contract column — correct.
- **2d Unmapped**: 0 for all three maps.
- **2e Asian/PI conflation**: **N/A** — executed triage: `demographic values: ['all', 'female', 'male'] | asian present: False`; gold has no `pct_asian` column (gender-only breakdown). Race is deferred precisely because NEWRACE's `Other` conflates Asian/PI/Native American/multiracial — the deferral is the correct response to this exact risk.
- **2f Mutual exclusivity**: **PASS — single convention.** Only `male`/`female` (+ `all`) in one category; MONSEX codes are mutually exclusive by construction; no rollup/split coexistence.

**Row-count reconciliation** (manifest `row_counts`): all 24 years FY2002–FY2025 present; per-year gold is exactly 9 (3 districts × 3 demographics), total 216 = actual parquet row count (executed: `3b parquet rows: 216 | manifest total_gold: 216`). `filtered_explicit` = non-GA national rows (1,683,826 total, sole reason `non_georgia_district_row`); bronze − filtered_explicit = GA offender rows, independently reproduced for all 6 recomputed years (2002: 64,366−62,937=1,429; 2009: 81,372−79,602=1,770; 2011: 86,201−84,293=1,908; 2013: 80,035−78,548=1,487; 2024: 61,678−60,406=1,272; 2025: 66,662−65,483=1,179). Remaining implicit "filtered" rows are GA offender rows aggregated into the 9 group rows — standard microdata-aggregation accounting; expansion factors uniform (~1.0–1.6e-4). Anchors: FY2024 national = **61,678** (structure-doc anchor) confirmed by my own CSV read; pinned GA anchors 1,429 (FY2002) / 1,646 (FY2012, manifest arithmetic 84,173−82,527) / 1,272 (FY2024) all hold.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| `DISTRICT` | `federal_district` | MAPPED (filter {32,33,34} → recode) |
| filename `opafy{YY}` | `year` | MAPPED (fiscal year; in-file SENTYR hard-asserted ∈ {fy−1, fy} where present) |
| (row count) | `offenders_sentenced` | MAPPED (key metric) |
| `SENTTOT` | `num_with_prison_sentence`, `avg_sentence_months`, `median_sentence_months` | MAPPED (mask ≥9992 / ≤0 → NULL; cap 470; mean/median over non-missing) |
| `MONSEX` | `demographic` | MAPPED (0/1 → male/female; 2/missing → `all` only) |
| `USSCIDN` | — | CORRECTLY EXCLUDED (in-memory within-year duplicate guard only) |
| `SENTYR` | — | CORRECTLY EXCLUDED (fiscal-year agreement guard only; FY2004–FY2023 layouts) |
| `CIRCDIST` | — | CORRECTLY EXCLUDED (redundant alternate code scheme, deliberately unused) |
| `NAME` (PII) | — | CORRECTLY EXCLUDED (allowlist-only reads; never materialized) |
| `DEPART`/`BOOKERCD`, `DRUGTYP*`, `GLMIN`/`GLMAX`/`XFOLSOR`/`XCRHISSR`, `MONRACE`/`NEWRACE`/`AGE`/`NEWCIT` | — | CORRECTLY EXCLUDED (documented deferrals — FY2018 methodology break / race-vocabulary conflation; carried in contract `limitations`; see Notes) |
| ~18k–27k other columns | — | CORRECTLY EXCLUDED (below gold grain; never materialized — FY2024 header has 27,265 columns, 4 read) |

Every gold column traces to bronze; no fabrication. The structure doc's proposed `share_with_departure` fact_metric is not served — a documented scope deferral (the contract limitations state departure/variance must be versioned at the FY2018 recode, not pooled), not a silent omission. The doc's proposed gold name `fiscal_year` lands as the platform-standard `year` with fiscal-year semantics prominently documented in the contract.

## Value-Level Spot Checks

Method: full independent per-year recompute (own `.sas` INPUT parse + LRECL-asserted line slicing for the fixed-width era; own header capture + `pl.read_csv` on the zip member for the CSV era; own aggregation with the documented rules — GA filter, MONSEX 0/1 → male/female, SENTTOT `.`/blank → NULL, mask ≥9992 / ≤0, cap 470, mean/median rounded to 2). Executed verdict per year, all six: **"MATCH — all 9 rows identical to gold"** (FY2002, FY2009, FY2011 fixed-width; FY2013, FY2024, FY2025 CSV — 54 rows, every column).

Quoted layout evidence (this run): FY2002 `opafy02nid.sas` — LRECL=18173, `DISTRICT 135-136`, `SENTTOT 54-59`, `MONSEX 195`, `USSCIDN 85-90`, SENTYR absent (expected pre-FY2004).

**Extreme-row traces (all 8 global extremes recomputed from bronze → MATCH):**

| Extreme | Gold row | Verdict |
|---|---|---|
| `offenders_sentenced` global max | 2009 georgia_northern all = 789 | MATCH (from 81,372 national fixed-width lines; GA rows 1,770) |
| `offenders_sentenced` global min | 2025 georgia_southern female = 39 | MATCH |
| `num_with_prison_sentence` max | 2009 georgia_northern all = 716 | MATCH |
| `num_with_prison_sentence` min | 2002 georgia_middle female = 20 | MATCH |
| `avg_sentence_months` global max | 2024 georgia_middle male = 102.47 | MATCH (raw SENTTOT max 1,200 → capped 470) |
| `avg_sentence_months` global min | 2011 georgia_middle female = 12.49 | MATCH |
| `median_sentence_months` max | 2013 georgia_southern male = 71.0 | MATCH (full row 323 / 263 / 95.73 / 71.0 reproduced) |
| `median_sentence_months` min | 2011 georgia_middle female = 8.0 | MATCH |

**Ordinary traces (one raw bronze record quoted per era, traced into its recomputed-and-matching group):**

- Era 1 (fixed-width), FY2002 first GA record: `USSCIDN='526554' DISTRICT='34' SENTTOT='162' MONSEX='0'` → contributes to 2002/georgia_southern/male — group reproduced exactly in the full-frame match.
- Era 2 (CSV), FY2024 first GA record: `USSCIDN='2828375' DISTRICT='34' SENTTOT='60' MONSEX='1'` → 2024/georgia_southern/female — group reproduced exactly. CSV header matched 4 of 27,265 columns — allowlist reads confirmed.

**4c Sentinel year-attribution**: N/A — `year` derives only from the zip filename (`opafy{YY}`); no year-bearing bronze string is parsed into `year`. The in-file SENTYR guard (must be fy−1 or fy, FY2004–FY2023) raises on violation and passed at transform time.

**4d Aggregate-row reconciliation**: the `all` and gender rows are transform-derived; the recompute re-derived all 54 from offender microdata and matched. Means are computed at offender level (no `.mean()` over percentages exists); `male + female <= all` is enforced globally by the authored `gender_counts_within_all_total` check (passing).

**4e Dedup tie-break**: N/A — each fiscal year comes from exactly one national zip; `assert_no_natural_key_collisions` runs before the (no-op) safety-net dedup. No overlap years exist.

**4f Suppression semantics**: N/A — USSC publishes complete unsuppressed microdata (`suppressed_to_null=False`); validator confirms no suppression markers. Gold contains zero NULL cells (every group had ≥1 reported prison sentence), consistent with the co-null contract rule.

**Sentinel/mask verification**: across all 6 recomputed years, bronze GA rows contained **zero** SENTTOT values ≥ 9992 and **zero** non-positive values — independently confirming the manifest's absent `masked_values` section (defensive masks, zero occurrences; executed: `manifest masked_values section: False`). Values above the 470 cap: 3/6/2/3/4/5 per recomputed year (max raw 2,005 months, FY2009), all clipped to 470 as documented — consistent with the transform log's 69 capped values across all 24 years.

## Validation Cross-Read

- `_validation.json`: **19 pass / 0 fail / 0 warning** (2026-07-07T04:11:16Z, fresh vs manifest 04:11:16Z; transform mtime 04:06 predates both — FRESH). `contract_parquet_schema`, `contract_quality_sql` (14 checks), `grain_uniqueness` (`year, federal_district, demographic`), `foreign_keys` (demographic → demographics, 3/3 keys) all pass. Read-loss events: 0 (absent section = zero events).
- `schema_hash`: `24fbba0810374a4bc42f3cd3f23cca0ef607d08d14188a2edac3bca6995caa2c`
- **§4b masking audit**: two defensive offender-level masks in `_clean_offenders` (SENTTOT ≥ 9992 sentinel zone; SENTTOT ≤ 0 impossible per codebook), both wired to `manifest.record_masked` under the bronze column name SENTTOT (documented recording choice: one input feeds three gold columns); zero occurrences → no `masked_values` section, verified in bronze this run. Handling documented in the contract's `avg_sentence_months` description and `null_meaning`; enforceable range guards authored (`avg/median_sentence_months_within_cap`, (0, 470]). PASS.
- **§15b coverage judgment**: GOOD. Nine authored checks cover the real cross-column invariants: partition subset (male+female ≤ all), completeness (all-row present per district-year; exactly 3 districts every year), denominator subset (num_with_prison ≤ offenders), co-null (avg/median NULL ⇔ denominator 0), metric ranges (0, 470], count ≥ 1, year floor. No obvious missing invariant.
- **v1 parity** (executed verbatim): `5d v1 parity: topic not in v1 baseline -> N/A` — expected; the baseline contains education topics only. Not a DIFFERS; no explanation owed.
- **Contract prose fidelity**: audited `purpose`/`usage`/`limitations` and every served description against the structure doc — no contradictions. Year range FY2002–FY2025 ✓; "complete unsuppressed microdata" matches the doc's "there is no suppression" ✓; fiscal-year semantics match "federal fiscal year in the filename" ✓; SENTTOT months + sentinel handling match ETL consideration 4 ✓; sub-state non-county grain matches the classification ✓; sentenced-individuals-not-filings matches consideration 9 ✓.

## Cross-Era Consistency

- **Overlap years**: none — one zip per fiscal year; era boundary is FY2011 (fixed-width) → FY2012 (CSV), detected structurally from zip members, and the manifest's era assignments match the filename split exactly (2002–2011 `fixed_width_sas_layout`, 2012–2025 `csv_wide`).
- **Era-boundary continuity**: 2011 → 2012 GA offenders 1,908 → 1,646 (−14%, national also fell 86,201 → 84,173); manifest avg means 55.45 → 55.26. FY2011 was recomputed exactly from bronze, so the boundary is value-verified on one side and anchor-verified (1,646) on the other.
- **Cross-year NULL sweep (Risk 2)**: executed — `CLEAN`; no column ~100% NULL in any year, no column NULL in every year (zero NULLs anywhere, 24/24 years populated).
- **Adjacent-year continuity (3d)**: executed over all 23 adjacent pairs on district-summed `all` rows — no >1.5x moves (executed: "none"), no 10x scale jumps, no cumulative-publication signature.

## Transform Logic Risks

| Risk | Severity | Details |
|---|---|---|
| Silent column drops | PASS | Allowlist-only reads; missing REQUIRED_VARS raise per file (both readers); optional SENTYR absence logged with expected-era note |
| Era routing | PASS | Structural detection (`.csv` member present?), never year ranges; manifest eras match the format split exactly |
| Filter logic logged + justified | PASS | Non-GA drop recorded as `filtered_explicit` (1,683,826, reason `non_georgia_district_row`); NULL-DISTRICT rows warned before dropping; national + GA anchors pinned for 3 years |
| Normalization map completeness | PASS | All bronze values mapped; `replace_strict` on DISTRICT post-filter; unmapped MONSEX codes would block via the manifest guard |
| `strict=False` casts | PASS | DISTRICT cast strict=False guarded by NULL-count warning + anchors; SENTTOT cast strict=False guarded by an explicit raise on non-numeric non-missing values |
| Dedup keys + tie-break | PASS | Collision guard before dedup; single source per year makes collisions impossible; documented safety-net `sort_col="offenders_sentenced"` |
| Year extraction | PASS | Filename regex (raises on unrecognized names); 24-zip count gate; LRECL assertion per line; SENTYR ∈ {fy−1, fy} hard check; defensive year floor |
| §4b masks (5b) | PASS | Defensive, recorded-when-fired, documented, range-guarded; zero occurrences verified in bronze |

## Notes

- `schema_hash` `24fbba0810374a4bc42f3cd3f23cca0ef607d08d14188a2edac3bca6995caa2c`; validation 19/0/0; contract version 1.0.0; 216 rows = 24 years × 9; manifest fresh; read_loss events 0.
- **Recompute coverage**: 6 of 24 years (25%), 54 of 216 rows, both eras, all 8 global metric extremes, 2 of 3 pinned GA anchor years directly (third via manifest arithmetic) — 0 mismatches. Remaining years are protected by the same single code path, per-year row anchors, grain checks, and the 14 contract quality checks.
- **Docstring prose nit (no gold impact, no fix required)**: the transform docstring says "9 GA values above the cap in FY2024"; executed bronze check shows 4 values strictly **above** 470 (480, 480, 540, 1200) and 9 values **≥** 470 (including five life-coded exactly-470s the cap leaves unchanged). The "max 1,200" part is exact; only the word "above" is loose, and the docstring is not a served surface.
- **SENTTOT sentinel-range nuance**: the structure doc gives SENTTOT's range as "0.01–9997" while the transform's defensive mask treats ≥ 9992 as impossible-in-SENTTOT sentinels (TOTPRISN's zone, life = 470 by convention). Zero such values exist in the GA rows of any recomputed year — the mask is dormant either way, and if it ever fires on a refresh the masked count surfaces in the manifest for review.
- **Pre-declared design deferrals (for the approver; documented in contract `limitations`, not data-accuracy defects)**: (1) departure/variance and offense/drug-type metrics deferred rather than pooled across the FY2018 USSC recode break; (2) race breakdown deferred because NEWRACE's `Other` conflates Asian/PI/Native American/multiracial; (3) the FY2018 time-served refinement (SENTTOT 0.03 instead of missing) documented as a caveat rather than versioned — matches the Commission's own single-series treatment; (4) long-term serving/dimension design for the sub-state federal-district grain deferred (enum categorical, `detail_level='state'`, no dimension join — validator passes as-is).
- SENTYR availability: present FY2004–FY2023 in the manifest's `bronze_columns`, absent FY2002–03 and FY2024–25 — matches the documented window; treated as optional either way.
