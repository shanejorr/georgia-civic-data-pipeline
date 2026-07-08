# Criminal Justice ETL — Domain Conventions

> `AGENTS.md` is a symlink to this file — edit `CLAUDE.md` only.
> Read [`src/etl/CLAUDE.md`](../CLAUDE.md) first for the pipeline shape; this
> file covers only what differs for the `criminal_justice` main topic. The
> source blueprint (retrieval details, caveats, licenses per source) is
> [`data_sources/criminal_justice/criminal-justice-data-review.md`](../../../data_sources/criminal_justice/criminal-justice-data-review.md).

## Grain and geography

- **County grain.** Fact tables key on `county_fips` — 5-digit string, Georgia
  prefix `13` (e.g. `"13121"` = Fulton). FK to the **global counties
  dimension** (`data/gold/_dimensions/counties.parquet`, built by
  `src/etl/build_counties_dimension.py`). The contract emitter wires the FK
  automatically from the exact column name `county_fips`.
- **Detail levels:** `county` and `state`. Pass
  `COUNTY_DETAIL_LEVEL_FILES` (from `src/utils/transformers.py`) to
  `export_to_parquet` → `counties.parquet` / `states.parquet` per year
  partition. State rows get NULL `county_fips` via `null_aggregate_geography`
  with `CRIMINAL_JUSTICE_DOMAIN_CONFIG["detail_level_geography_rules"]`
  (`src/utils/validators.py`) — the validator enforces the same rules.
- **Dedup:** use the generic `deduplicate_by_levels(df, {"county": [...],
  "state": [...]}, sort_col=...)`, not the education
  `deduplicate_by_detail_level`.
- **Name→FIPS:** sources that report county *names* (GSA jail report, GDC
  PDFs, clearinghouse) resolve via
  `src/utils/crosswalks.add_county_fips(df, name_col)` +
  `COUNTY_NAME_OVERRIDES` (consolidated governments: Athens-Clarke→Clarke,
  Columbus→Muscogee, Augusta-Richmond→Richmond, Macon-Bibb→Bibb, …). Record
  unmatched names as unmapped categoricals on the manifest (blocking), never
  silently NULL.
- **Facility/agency sources:** ICE facilities join
  `data/gold/crosswalks/facility_to_county.parquet`
  (`src/etl/crosswalks/build_facility_to_county.py`; key `facility_id` =
  ICE `detention_facility_code`, filter `source == "ddp_ice"`). FBI ORIs join
  `data/gold/crosswalks/ori_to_county.parquet`
  (`src/etl/crosswalks/build_ori_to_county.py`). Fact tables carry
  `county_fips` after rollup — facility/agency identifiers stay out of gold
  unless the topic is explicitly facility-grain.

## Domain rules

- **Suppression → NULL, never 0.** Every source has its own marker and
  threshold (CDC <10 suppressed, OASIS <4, OJJDP small counts). Keep the
  bronze markers verbatim; convert to NULL in transform; record masked counts
  on the manifest; document the threshold in the contract via `null_meaning`.
- **`month` is a string categorical** (`"01"`–`"12"`) on monthly topics
  (GSA jail report, ICE) so it enters the grain as a categorical, not a
  metric.
- **Version methodological breaks, never pool across them:** SRS→NIBRS
  (GA Oct 2019), 2015 HB 310 (GDC→DCS/SBPP supervision split), COJ full
  enumeration vs ASJ sample years (coverage flag column), reconviction vs
  re-arrest recidivism.
- **PII stays in bronze.** Clearinghouse youth-level rows, DDP person-level
  records, stop-level data: aggregate to county/facility × year (or month)
  inside `transform.py`; gold serves aggregates only.
- **Coverage flags over imputation.** Voluntary/partial-coverage sources
  (GSA monthly report, ASJ sample years, OJJDP reporting counties) carry an
  explicit coverage/reporting flag or documented missingness — never impute
  non-reporting counties.
- **Attribution/licenses** (from the blueprint): DDP citation wording in the
  ICE `_provenance.md`; Stanford ODC-BY; WaPo CC-BY-NC-SA. Carry them into
  the contract `usage`/`limitations` when the topic ships.

## Bronze acquisition

Unlike education (manual downloads), every CJ topic has a re-runnable
`download.py` in its `src/etl/criminal_justice/{sub_topic}/{topic}/` dir that
re-scrapes parent pages for unstable URLs. `_provenance.md` in each bronze dir
records source URLs, retrieval timestamp, method, license. Re-running a
download that changes files requires re-running `/bronze-data-structure`
(checksums gate the transform via `scripts/check_bronze_freshness.py`).
