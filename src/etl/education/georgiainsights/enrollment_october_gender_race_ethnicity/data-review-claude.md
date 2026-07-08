# Data Review: enrollment_october_gender_race_ethnicity

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: PASS

## Summary

Gold is byte-identical with the approved v1 baseline (**v1 parity MATCH**, sha256 `e3ad1be5…`, re-verified independently). All 9 categorical map entries (7 race + 2 gender) are semantically correct; the row accounting closes exactly (128,571 bronze − 42,857 `Total` gender rows, ×7 race unpivot, −238 duplicate state twins = 599,760 gold); every value-level trace — global max, global min, ordinary district/school/charter rows across both eras' endpoints (2010 and 2026), and suppression — matched bronze exactly. The shared module `_enrollment_race_lookups.py` was consumed unmodified (mtime 12:23:22 predates this transform's authoring at 12:34:24; the march sibling's PASSed review at 12:37:53 covered those same bytes). Both aggregate feasibility screens ran with **0 violations**. No required fixes, no judgment items.

## Manifest Verification

| Column | Map entries | Bronze values seen | Unmapped | Status |
|--------|------------:|-------------------:|---------:|--------|
| `race` | 7 | 7 | 0 | PASS |
| `gender` | 2 | 2 | 0 | PASS |

**Full map review — `race` (7/7 entries):**

| Bronze (stripped column name) | Gold | Correct? |
|---|---|---|
| `Ethnic Hispanic` | `hispanic` | ✓ — non-overlapping ethnicity bucket (GaDOE FTE coding gives Hispanic precedence over race); partition math confirms (see 2e below) |
| `Race AmericanIndian` | `native_american` | ✓ — canonical key for AI/AN |
| `Race Asian` | `asian` | ✓ — split convention valid: bronze has a separate `Race Pacific Islander` column in every file |
| `Race Black` | `black` | ✓ |
| `Race Pacific Islander` | `pacific_islander` | ✓ — split key, never the rollup |
| `Race White` | `white` | ✓ |
| `Two or more Races` | `multiracial` | ✓ — canonical key for two-or-more |

**Full map review — `gender` (2/2 entries):**

| Bronze | Gold | Correct? |
|---|---|---|
| `Female` | `female` | ✓ |
| `Male` | `male` | ✓ |

**2a completeness note**: the structure doc documents a third bronze `Gender` value, `Total`. It is absent from `bronze_values_seen` because the transform drops it **before** the map applies — intentional and fully accounted: 42,857 rows recorded under `gender_total_rows_dropped_redundant_with_female_plus_male` (Total = Female + Male verified on all 123,666 complete triples per the structure doc's Corrections). Not a routing bug.

**2c contract cross-check**: `gold_values_produced` for `race` = contract enum (7 values, sorted) and for `gender` = contract enum (`female`, `male`). PASS.

**2d unmapped**: 0 for both columns. PASS.

### 2e Asian / Pacific Islander conflation (Risk 1)

PASS — **split convention, positively evidenced**. Bronze carries an explicit `Race Pacific Islander` column in all 34 files (10 NHPI-label hits in the structure doc). Partition math at the latest state level (executed):

```
sum of 7 races x 2 genders = 1715031 (published FTE Oct 2025 = 1,715,031)
asian present: True | pacific_islander present: True
asian_pacific_islander rollup present anywhere: 0
```

The seven buckets partition total enrollment exactly — `asian` (92,062) and `pacific_islander` (1,694) are genuinely separate, and `hispanic` is non-overlapping (the sum would exceed the published total if it were an overlay).

### 2f Demographic mutual exclusivity (Risk 6)

PASS — single convention. Gold contains only the split keys; zero `asian_pacific_islander` rows anywhere (executed check above).

### Row-count reconciliation

| Stage | Rows |
|---|---:|
| Bronze (34 CSVs, raw == parsed for all files; zero read loss) | 128,571 |
| − `Total` gender rows | −42,857 → 85,714 |
| ×7 race unpivot | 599,998 |
| − duplicate state twins (17 years × 14) | −238 |
| **Gold (manifest `total_gold` = actual parquet rows)** | **599,760** |

Per-year expansion factor is flat at ~4.6648 across all 17 years (= 14/3 minus the twin drop — single-era consistency). Per-year gold equals `14 × (1 + n_districts + n_school_pairs)` exactly for all 17 years (verified from the parquet: districts column reproduces the structure doc's roster counts 186→237; school pairs 2,271→2,316). All 17 years 2010–2026 present, no gaps.

## Column Coverage

| Bronze column | Gold column | Status |
|---|---|---|
| (filename year `Fiscal YearYYYY-1`) | `year` | MAPPED — preamble year cross-checked with hard raise |
| `System ID` | `district_code` | MAPPED — `""` → NULL before zfill(3); 7-digit charters pass through |
| `System Name` | — | CORRECTLY EXCLUDED (districts dimension attribute) |
| `School ID` code prefix (`NNNN-`) | `school_code` | MAPPED — split on first hyphen; `State-Wide` → NULL via regex non-match |
| `School ID` name part | — | CORRECTLY EXCLUDED (schools dimension attribute) |
| `Gender` | `gender` | MAPPED — `Total` dropped (documented, recorded) |
| 7 race/ethnicity count columns | `race` + `student_count` (unpivot) | MAPPED |

No gold column lacks a bronze ancestor (no fabrication). The structure doc's Gold Schema Classification named the race axis `demographic`; the Corrections entry (2026-06-12) supersedes it with `race` per the education CLAUDE.md race × gender two-column convention, which explicitly lists this topic — the transform follows the corrected convention.

## Value-Level Spot Checks

All traces MATCH; bronze quoted for each.

1. **Global max** — gold `2010 / state / white / male = 387073`. Bronze 2010 District file state row: `Male … Race White = 387073`. MATCH. (Bonus: bronze `Total` white = 749,829 = 362,756 F + 387,073 M ✓.)
2. **Global min (15, the suppression floor)** — gold `2010 / 602 / district / multiracial / female = 15`. Bronze 2010 District: `602 Atkinson County Female … Two or more Races = 15`. MATCH. Second min trace: gold `2010 / 605 / 0195 / multiracial / male = 15` ↔ bronze `0195-Blandy Hills Elementary School Male … Two or more Races = 15`. MATCH.
3. **Ordinary district (2026)** — district 675 Henry County, male. Bronze: `Hispanic=2775 AI=61 Asian=622 Black=13817 PI=21 White=2774 Two=1184`; gold rows match all 7 cells exactly. MATCH.
4. **Ordinary school (2026, suppression mix)** — 737/3052 Northeast Middle, male. Bronze: `Hispanic=86 AI=* Asian=* Black=127 PI=* White=128 Two=*`; gold: hispanic=86, black=127, white=128, other 4 NULL. MATCH.
5. **Ordinary school (2010 — earliest year)** — 601/0103 Appling County High, female. Bronze: `Hispanic=32 AI=* Asian=* Black=99 PI=* White=291 Two=*`; gold: hispanic=32, black=99, white=291, other 4 NULL. MATCH.
6. **7-digit charter passthrough** — bronze District `System ID=7830611` (Cirrus Charter Academy) `Female Black=243 / Male Black=214`, all else `*`; gold `district_code='7830611'` (unpadded, untruncated), district rows black female=243 / male=214, 12 NULLs. The parallel school-level rows (`school_code='0611'`) trace to the School file's `0611-Cirrus Charter Academy` rows with identical values — legitimate bronze, not a dedup artifact. MATCH.
7. **4f suppression** — 644/3056 DeKalb Flat Shoals, male: bronze `Hispanic=* AI=* Asian=* Black=178 PI=* White=* Two=*` → gold black=178, all six others NULL. MATCH (single `*` marker; no other markers exist per the structure doc, confirmed by `no_suppression_markers` PASS).
8. **4c year attribution** — year exists only in filename + preamble. 2010 District preamble line 2: `"FTE Enrollment by Race/Ethnicity and Gender - Fiscal Year 2010-1 Data Report"`, line 3: `"Oct 6, 2009 (FTE 2010-1)"` → fiscal 2010 = fall 2009 count; gold partition `year=2010` carries these rows. The reader hard-raises on filename↔preamble disagreement (all 34 agree). MATCH. Also confirms the early-year `"Oct D"` short-month preamble form parses fine (title check is substring, year regex is on line 2).
9. **4d aggregate feasibility screens** (aggregates COME FROM BRONZE; suppression-heavy → impossibly-LOW direction):
   - Visible district sum > state: **0 violations** across all 238 (year, race, gender) cells; coverage min 0.6026 (pacific_islander, exactly as heavy suppression predicts), median 0.9914.
   - District < visible school sum, district < max school: **0 violations** across all 29,239 published (year, district, race, gender) cells.
10. **4e dedup** — single era, no overlap years → N/A. The state-twin analog verified: bronze 2010 School-file state rows are byte-identical to the District-file state rows (both quoted; e.g. Male White=387073 in both), gold keeps exactly one set (14 rows/year, quality check enforces); the collision guard runs pre-dedup and raises on divergence, so the tie-break is provably irrelevant.

## Validation Cross-Read

- `_validation.json`: **21/21 checks PASS, 0 warnings** (timestamp 2026-06-12T16:34:50Z, newer than manifest `generated_at`; transform mtime older — FRESH). `contract_parquet_schema`, `contract_quality_sql`, `grain_uniqueness`, `foreign_keys` (all 256 district keys and 2,720 school pair keys resolve), `geography_nulling` ×3 all pass.
- `schema_hash`: `1cdd6e5ae6719bfdf75e40e5470b8dbf10b209d491c22b9bf2eb6a1019c57ab2`
- **§4b masking audit**: no `_null_*` helpers in transform.py (grep clean), no `masked_values` section in the manifest (absent = zero events), docstring states "No section 4b masks" — counts are non-negative by construction and the only non-numeric bronze value is the `*` marker handled at read. Consistent. PASS.
- **§15b coverage judgment**: the three authored checks (suppression floor ≥15, state rows never suppressed, 14-state-rows partition per year) plus the auto-derived enum/non-negative/non-empty checks cover the topic's enforceable invariants. The remaining bronze invariant (Total = F+M) is unenforceable in gold by design (Total rows dropped). Adequate. PASS (see Notes for one optional strengthening).
- **v1 parity** (executed independently):

```
v1 : e3ad1be5b8a96cf8b48e1828daca3a9a61fa3c8a9d395aa069c99f68d1766882
now: e3ad1be5b8a96cf8b48e1828daca3a9a61fa3c8a9d395aa069c99f68d1766882
MATCH — byte-identical with v1 gold
```

## Cross-Era Consistency

Single era (2010–2026, one column set, verified by the manifest's 34 identical `bronze_columns` lists modulo the School files' extra `School ID`). No overlap years → no dedup-inversion surface. Cross-year NULL sweep: only metric `student_count`, max yearly null rate 0.6019 (2010), declining monotonically to 0.5316 (2026) — the documented suppression-shrinks-as-multiracial-grows drift; no ~100%-NULL year. Year-over-year state totals are smooth (1.668M → 1.770M → 1.715M), worst adjacent ratio 0.9776 (2021, the well-documented COVID enrollment dip) — no scale jumps, no cumulative-publication signature. The pairs-vs-strings counting nuance from the structure doc Corrections verified in bronze: 2026 School file has 2,315 distinct `School ID` strings but 2,316 (System ID, School ID) pairs — `0176-Mount Zion Elementary School` exists under both districts 622 and 631; gold keeps both as distinct (district_code, school_code) rows. Every (year, geography) block in gold is a complete 14-row race×gender partition (0 of 42,840 blocks deviate).

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|---|---|---|
| Silent column drops | none | PASS — `require_race_columns` + `base_required` guard raise on any missing bronze column per file |
| Era routing | none | N/A — single era; filename regex raises on unmatched names; preamble title + year cross-checks raise on mismatch |
| Filter logic logged + justified | none | PASS — both filters (`Total` gender rows, state twins) recorded per year via `record_filtered` with reasons; totals 42,857 + 238 |
| Normalization map completeness | none | PASS — 7/7 race + 2/2 gender vs the structure doc; `replace_strict(default="99999999")` + manifest unmapped=0 |
| `strict=False` casts | low (accepted) | PASS — reader already nulls `*` via `null_values`; the Int64 `strict=False` is belt-and-braces (a future new marker would null silently, but `no_suppression_markers` + the suppression-floor quality check bound the blast radius) |
| Dedup keys + tie-break | none | PASS — collision guard (raises on divergent twins) runs before `deduplicate_by_detail_level`; twins proven identical, tie-break moot |
| Year extraction | none | PASS — filename regex, preamble cross-check with hard raise; traced (spot check 8) |
| §4b masking | none | PASS — no masks; see audit above |

## Notes

- `schema_hash`: `1cdd6e5ae6719bfdf75e40e5470b8dbf10b209d491c22b9bf2eb6a1019c57ab2`; validation 21/21 PASS, 0 warnings; read_loss: 0 events (raw == parsed for all 34 files).
- Shared module `src/etl/education/georgiainsights/_enrollment_race_lookups.py` consumed READ-ONLY and unmodified: file mtime 2026-06-12 12:23:22 (EDT) predates this transform's authoring (12:34:24) and run (12:34:50); the march sibling's data review (12:37:53), which PASSed the module, reviewed those same bytes. The module is still untracked in git, so no committed baseline exists yet — committing both topics together will fix that.
- Optional (non-blocking) contract strengthening: a `complete_race_gender_block` quality check (every (year, district_code, school_code) group has exactly 14 rows) generalizes the authored state-partition check to all geographies. The invariant currently holds for all 42,840 blocks and is structurally guaranteed by the unpivot of complete bronze F/M/T triples, so this is hardening against future regressions, not a present defect. Note that adding it would change only the contract, not gold (parity preserved).
- AWS profile known broken — S3 untouched per instructions; review ran entirely against local bronze/gold.
