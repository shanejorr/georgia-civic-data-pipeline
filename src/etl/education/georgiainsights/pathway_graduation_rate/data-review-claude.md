# Data Review: pathway_graduation_rate

**Date**: 2026-06-12
**Reviewer**: Claude (automated data review)
**Status**: NEEDS_JUDGMENT

## Summary

Verdict: no data inaccuracies found. **v1 parity: MATCH — byte-identical with v1
gold** (`4fc058624f64f6078ccfe64f48caa1728d9dea4cb66e6d532f13978888f6ef68`).
Every bronze→gold trace (extremes, ordinary entities, both suppression marker
types, the 2021 mask, zfill alignment) matched exactly; null counts reconcile
to the marker counts cell-for-cell; all four Corrections-section claims in
`bronze-data-structure.md` re-verified true. One judgment call: new quantified
evidence that ~95% of the 2021 zero cells that *survive* the all-four-zero mask
pattern-match suppression in 2022 — recommendation is to keep the data as-is
(documented, conservative, parity-preserving), optionally tightening the
contract-limitations prose.

## Manifest Verification

**Categorical mappings**: `categorical_mappings` is `{}` — correct by
construction. The structure doc confirms "no true categorical columns" (no
demographic, no subject/pathway-type column; each pathway is its own metric).
The only categorical-behaving values are the `"ALL"` geography sentinels,
handled as NULL keys, not recodes. `unmapped_count` N/A. Steps 2a–2d: PASS
(vacuous). Step 2e (Asian/PI conflation): **N/A** — no `demographic` column,
no race columns anywhere in bronze. Step 2f (mutual exclusivity): **N/A**.

**Row-count reconciliation** (manifest vs structure doc vs parquet):

| Year | Bronze (doc) | Manifest bronze | Manifest gold | Parquet rows | state/district/school | Expansion |
|------|-------------:|----------------:|--------------:|-------------:|----------------------|----------:|
| 2021 | 688 | 688 | 688 | 688 | 1 / 195 / 492 | 1.0 |
| 2022 | 690 | 690 | 690 | 690 | 1 / 194 / 495 | 1.0 |
| 2023 | 694 | 694 | 694 | 694 | 1 / 195 / 498 | 1.0 |
| 2024 | 701 | 701 | 701 | 701 | 1 / 197 / 503 | 1.0 |

Total 2,773 = manifest `total_gold` = actual parquet sum. `total_filtered` = 0
(no row filters — correct: every bronze row is a fact row at some detail
level). Per-level splits match the structure doc's Statistics table exactly.

**NULL reconciliation** (gold null count = bronze NA + TFS, +47 mask in 2021)
— exact for all 12 year×metric cells, e.g.:

| Year | Metric | Bronze NA | Bronze TFS | Mask | Gold NULLs |
|------|--------|----------:|-----------:|-----:|-----------:|
| 2021 | all four | 0 | 0 | 47 | 47 each |
| 2022 | advanced_academic | 64 | 76 | 0 | 140 |
| 2022 | world_language | 136 | 166 | 0 | 302 |
| 2022 | fine_arts | 77 | 118 | 0 | 195 |
| 2022 | ctae | 50 | 44 | 0 | 94 |
| 2023 | advanced_academic | 58 | 72 | 0 | 130 |
| 2023 | world_language | 168 | 119 | 0 | 287 |
| 2023 | fine_arts | 66 | 121 | 0 | 187 |
| 2023 | ctae | 45 | 52 | 0 | 97 |
| 2024 | advanced_academic | 59 | 63 | 0 | 122 |
| 2024 | world_language | 171 | 136 | 0 | 307 |
| 2024 | fine_arts | 70 | 109 | 0 | 179 |
| 2024 | ctae | 49 | 52 | 0 | 101 |

All NA/TFS counts independently recounted from bronze with
`keep_default_na=False` and they match the structure doc's Suppression Markers
table cell-for-cell.

## Column Coverage

| Bronze column | Gold column | Status |
|---------------|-------------|--------|
| COHORT YEAR | `year` | MAPPED (Int32; single value per file = filename year, verified all 4 files) |
| SYSTEM ID | `district_code` | MAPPED ("ALL"→NULL before zfill(3); 7-digit charters pass through) |
| SYSTEM NAME | — | CORRECTLY EXCLUDED (districts dimension attribute) |
| SCHOOL ID | `school_code` | MAPPED ("ALL"→NULL before zfill(4)) |
| SCHOOL NAME | — | CORRECTLY EXCLUDED (schools dimension attribute) |
| ADVANCED ACADEMIC | `advanced_academic_pathway_rate` | MAPPED (÷100, proportion) |
| WORLD LANGUAGE | `world_language_pathway_rate` | MAPPED (÷100, proportion) |
| FINE ARTS | `fine_arts_pathway_rate` | MAPPED (÷100, proportion) |
| CTAE | `ctae_pathway_rate` | MAPPED (÷100, proportion) |

9/9 bronze columns accounted for; no fabricated gold columns (`detail_level`
is carried only for the per-level export split and encoded in the filename).

## Value-Level Spot Checks

All MATCH. Extreme rows first (global/per-era min/max per metric), then
ordinary entities, then suppression semantics.

**Extremes:**

| Trace | Bronze (quoted) | Gold | Verdict |
|-------|-----------------|------|---------|
| 2022 global min AA + FA — district `7820613` (Foothills Charter, 7-digit charter) | `['30.43', '48', '18.18', '17.8']` | `(0.3043, 0.48, 0.1818, 0.178)` | MATCH |
| 2022 school `7820613`/`613` (same values at school level) | `['30.43', '48', '18.18', '17.8']` | `(0.3043, 0.48, 0.1818, 0.178)` at `0613` | MATCH (zfill) |
| 2023 global min WL — `7820618`/`618` Coastal Plains Charter HS | `['58.82', '35', '28.26', '40.83']` | `(0.5882, 0.35, 0.2826, 0.4083)` | MATCH |
| 2022 global min CTAE — `644`/`810` Elizabeth Andrews HS (DeKalb) | `['TFS', 'TFS', 'TFS', '15.79']` | `(None, None, None, 0.1579)` at `0810` | MATCH |
| Global max 1.0 (n=1,588 AA cells) — e.g. Islands High below at 100.00 | `'100.00'` | `1.0` | MATCH |
| 2021 min 0.0 — surviving partial zeros (see Cross-Era and NEEDS_JUDGMENT) | `'0'` | `0.0` | MATCH (by design) |

**Ordinary entities (single era, multiple years traced):**

| Trace | Bronze (quoted) | Gold | Verdict |
|-------|-----------------|------|---------|
| State row 2024 (`ALL`/`ALL`) | `['99.50', '99.26', '97.89', '98.24']` | `(0.995, 0.9926, 0.9789, 0.9824)` with NULL/NULL keys | MATCH |
| State row 2021 | `['99.28', '98.76', '96.7', '96.71']` | `(0.9928, 0.9876, 0.967, 0.9671)` | MATCH |
| Islands High 2024 `625`/`0411` | `['100.00', '100.00', '100.00', '98.92']` | `(1.0, 1.0, 1.0, 0.9892)` | MATCH |
| Ware County HS 2021 `748`/`195` (3-char bronze code) | `['99.12', '100', '95', '98.81']` | `(0.9912, 1.0, 0.95, 0.9881)` at `school_code='0195'` | MATCH (zfill alignment with 2024's native `0195`) |

**Suppression semantics (4f) — one trace per marker type plus the mask:**

| Trace | Bronze (quoted) | Gold | Verdict |
|-------|-----------------|------|---------|
| TFS: Taylor County district 2024 `733`/`ALL` | `['100.00', 'TFS', '100.00', '100.00']` | `(1.0, None, 1.0, 1.0)` | MATCH |
| NA: KidsPeace 2024 `622`/`0112` | `['NA', 'NA', 'NA', 'NA']` | `(None, None, None, None)` | MATCH |
| 2021 mask: KidsPeace 2021 `622`/`112` | `['0', '0', '0', '0']` | `(None, None, None, None)` | MATCH (masked) |
| 2021 mask: UHS of Savannah Coastal Harbor `625`/`107` | `['0', '0', '0', '0']` | `(None, None, None, None)` | MATCH (masked) |
| 2021 partial zero preserved: Atkinson County district `602`/`ALL` | `['100', '0', '100', '97.65']` | `(1.0, 0.0, 1.0, 0.9765)` | MATCH (preserved by design) |

**4c sentinel year-attribution**: PASS — `COHORT YEAR` has exactly one
distinct value per file and equals the filename year in all four files
(re-verified: `['2021']`, `['2022']`, `['2023']`, `['2024']`); the transform
raises on any mismatch. The `2021` literal in the transform scopes the mask,
not year attribution.

**4d aggregate feasibility screen** (aggregates COME FROM BRONZE — district
and state rows are published, not derived): district rates vs the range of
their visible school rows: AA 7/698 outside, WL 5/499, FA 28/639, CTAE 39/747.
Every flagged case has exactly **one** visible school row (`n=1`) with all
other schools NA/TFS-suppressed, and the worst deviation is 4.7pp (FA 2022,
district `609`: district 0.90 vs lone school 0.9474). A district aggregate
including suppressed-school students legitimately falls outside its lone
visible school's value — no impossibly-low aggregates found. PASS.

**4e dedup tie-break**: N/A — one file per year, zero duplicate
(SYSTEM ID, SCHOOL ID) keys in every bronze file (independently re-verified:
0/0/0/0). Dedup is purely defensive.

## Validation Cross-Read

`_validation.json`: **passed=true, 21 pass / 0 fail / 0 warning**
(2026-06-12T20:02:54Z, fresh vs manifest 20:02:54Z and transform mtime
20:02:32Z). `contract_parquet_schema` (12 files), `contract_quality_sql`
(all 7), `grain_uniqueness` (`['year','district_code','school_code']`), and
`foreign_keys` (197 district keys, 514 school keys — includes the 7-digit
charters) all pass.

**schema_hash**: `e31c596116d259a2604d2e2b2753906ccb45e31dcf57095c7d32dfae0cc552bd`

**§4b masking audit**: PASS. `_null_2021_zero_suppression` is the only mask.
Manifest `masked_values` records 4 entries (one per metric) × count 47, with
reason and `years: [2021]` — verified against gold: exactly 47 all-four-NULL
rows in 2021, 188 cells, 180 of bronze's 368 zero cells remaining
(368 − 47×4 = 180, exact). Documented in every metric's contract
`null_meaning` and in `limitations`. Enforceable guards present: per-metric
proportion unit-interval checks plus the dedicated `no_all_zero_pathway_rows`
quality check (returns 0 rows — would catch mask regression).

**§15b coverage judgment**: PASS. `one_state_row_per_year` (verified: exactly
1 state row per file in bronze) and `no_all_zero_pathway_rows` cover the real
invariants. A partition-sum check is correctly NOT authored — the four rates
are independent, overlapping per-area completions (state rows sum to ~3.9),
and the docstring/contract say so explicitly.

**v1 parity** (verbatim):

```
MATCH — byte-identical with v1 gold
hash: 4fc058624f64f6078ccfe64f48caa1728d9dea4cb66e6d532f13978888f6ef68
```

**Corrections-section claims (structure doc, 2026-06-12) — all re-verified:**

1. School-ID width mix 2021-2023: confirmed — 2021: 142 distinct 3-char + 80
   distinct 4-char (none zero-padded); 2022: 146+83; 2023: 147+85; 2024:
   uniformly 4-char (234 distinct, 148 zero-padded). Matches the claim.
2. `dtype=str` read yields zero SYSTEM ID nulls; state row carries literal
   `ALL`: confirmed in all four files (nulls=0, ALL count=1).
3. No `_metadata.json` in gold: confirmed (README.md, manifest, validation,
   `year=*` partitions only).
4. 47 all-zero rows / 368 zero cells in 2021; zero `0` cells in 2022-2024:
   confirmed exactly (47, 368, and 0/0/0 respectively).

## Cross-Era Consistency

Single era (one 9-column schema across 2021-2024); no overlap years. Cross-year
NULL sweep (3c): no column is ≥95% NULL in any year (max NULL rate 43.8% — WL
2024, fully explained by NA+TFS counts). No era-localized rename signature.
State-level continuity (3d): smooth monotone drift, AA 0.9928→0.995,
WL 0.9876→0.9926, FA 0.967→0.9789, CTAE 0.9671→0.9824 — no scale jumps. The
2021 school/district *means* sit well below later years (WL 0.8197 vs ~0.99)
— an artifact of 2021's preserved zero cells, the subject of the judgment call
below; the structure doc documents the same shift in bronze.

## Transform Logic Risks

| Risk | Severity | Verdict / details |
|------|----------|-------------------|
| Silent column drops | — | PASS — only SYSTEM NAME / SCHOOL NAME dropped, explicitly, as dimension attributes |
| Era routing | — | PASS — signature-based detection, raises on unknown schema; rename-coverage guard raises on missing columns |
| Filter logic | — | PASS — no row filters (`total_filtered` 0; bronze == gold per year) |
| Normalization map completeness | — | N/A — no categorical columns |
| `strict=False` casts | LOW | PASS with note — metric markers already NULLed at read (`SUPPRESSION_VALUES` covers TFS; pandas default NA-handling absorbs `NA` even earlier); a *novel* future marker would silently NULL rather than raise, but null-reconciliation here is exact (0 unexplained NULLs) |
| Dedup keys + tie-break | — | PASS — collision guard before dedup; zero bronze duplicate keys re-verified; dedup defensive only |
| Year extraction | — | PASS — in-file COHORT YEAR is source of truth, cross-checked against filename year, raises on mismatch |
| §4b mask (5b) | — | PASS — recorded, documented, guarded (see masking audit) |

Risk hypotheses: 1 (Asian/PI) N/A · 2 (rename-typo NULL year) ruled out ·
3 (sentinel year) PASS · 4 (aggregation) screened, PASS · 5 (dedup inversion)
N/A · 6 (mutual exclusivity) N/A · 7 (wrong mapping) no recodes; renames
verified semantically.

## NEEDS_JUDGMENT

### Judgment Call 1: ~95% of surviving 2021 zero cells pattern-match suppression in 2022

- **Severity if confirmed**: MEDIUM
- **Suspicion**: The conservative all-four-zero mask (47 rows) leaves 180 zero
  cells across 122 partial-zero 2021 rows, and most of these are probably also
  the 2021 zero-encoding of "no applicable students"/suppression rather than
  genuine 0% rates — meaning 2021 school/district means (e.g., WL 0.8197 vs
  0.9865 in 2022) are biased low and year-over-year comparisons show a phantom
  jump.
- **Evidence available**: Tracking each surviving 2021 zero cell to the same
  (district, school, metric) cell in 2022 bronze: **TFS 63, NA 108, entity
  absent 6, numeric 3** — i.e., 171/180 (95%) present as suppression markers
  in 2022. Only 3 cells are numeric in 2022, and all flip 0→100 (e.g.,
  Atkinson County `602` WL: 2021 `'0'` → 2022-2024 `'100'`), which is itself
  more consistent with the 2021 zero being an encoding artifact than a real
  rate. Counter-evidence: small entities legitimately produce both genuine 0%
  rates and next-year TFS (both correlate with tiny denominators), so the
  pattern match is suggestive, not conclusive; with no denominator column
  there is no clean signal (the structure doc's own finding).
- **Why uncertain**: A genuine 0% world-language pathway rate at a small rural
  district is entirely plausible; masking on a cross-year pattern match would
  null some real zeros and is fragile (entities change year to year). The
  structure doc explicitly deliberated this (options 1-3) and recommended the
  adopted option 2; v1 shipped the identical bytes; the contract limitations
  already disclose the ambiguity.
- **Location**: `_null_2021_zero_suppression` in `transform.py`; contract
  `limitations` prose.
- **If confirmed, suggested fix**: **Recommendation: keep the data as-is** —
  the conservative mask is the documented, deliberated choice, preserves v1
  parity (MATCH), and any stronger heuristic (e.g., also masking 2021 zeros
  whose 2022 counterpart is NA) risks false nullification it cannot verify.
  Optional, zero-data-impact improvement at the next contract touch: tighten
  the limitations wording from "a small number of remaining 2021 zeros are
  ambiguous" to the quantified reality ("180 zero cells across 122 rows;
  ~95% of the same cells appear as NA/TFS in 2022"), since "small number"
  understates ~18% of 2021 rows. (Prose-only re-emit; parquet bytes — and the
  parity hash — are unaffected.)

## Notes

- schema_hash: `e31c596116d259a2604d2e2b2753906ccb45e31dcf57095c7d32dfae0cc552bd`;
  validation 21 pass / 0 fail / 0 warning; manifest read_loss: 0 events
  (whole-sheet Excel reads — raw == parsed by construction).
- v1 parity: MATCH (byte-identical), hash
  `4fc058624f64f6078ccfe64f48caa1728d9dea4cb66e6d532f13978888f6ef68`.
- The shared reader's pandas `read_excel(dtype=str)` path converts bronze
  `'NA'` to NaN via pandas' *default* NA-handling before `SUPPRESSION_VALUES`
  is even consulted; `'TFS'` is nulled by `SUPPRESSION_VALUES`. Both routes
  end at NULL as intended, and the exact NULL reconciliation above confirms no
  collateral nulling (bronze `'ALL'`, names, and numeric strings are
  unaffected).
- Contract `null_semantics.zero_is_real: true` is the emitter's generic
  derivation; for this topic the 2021-specific nuance (remaining zeros
  ambiguous) lives in `limitations` and each metric's `null_meaning` — the
  authoritative caveats.
- Topic name caveat (`pathway_graduation_rate` is a pathway-completion
  indicator, not a graduation rate) is prominently documented in the contract
  purpose, README, and transform docstring; renaming would be a breaking
  change for no data benefit.
- The upstream catalog lists a 2025 file not yet in bronze — noted in the
  contract; not a gap in this review's scope (freshness gate passed 4/4).
