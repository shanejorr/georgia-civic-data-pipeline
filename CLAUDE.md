# Georgia Data — Agent Instructions

> `AGENTS.md` is a symlink to this file — edit `CLAUDE.md` only.

## Project Overview

Georgia Public Data Aggregation Platform — aggregates, cleans, and serves public data for Georgia (education, criminal justice) via a REST API, MCP server, Data Explorer, and the Data Talk chatbot, with cross-dataset linking.

**Public name & domain**: **Georgia Civic Data** at **[georgiacivicdata.org](https://georgiacivicdata.org)** (canonical). `georgiacivicdata.com` also registered.


---

## Code Conventions

- Use **polars** over pandas for all ETL code; **pathlib** for file paths
- Column names: **snake_case** and descriptive; proper names: **title case**; sentences: **sentence case**
- **FIPS codes** for county identifiers; **Census GEOIDs** for tract-level data

---

## Data Hierarchy

Three levels: **main_topic** / **sub_topic** / **topic** (e.g., `education` / `gosa` / `act_scores`).

Key paths:
- Bronze: `data/bronze/{main_topic}/{sub_topic}/{topic}/`
- Gold: `data/gold/{main_topic}/{topic}/` (no sub_topic)
- ETL scripts: `src/etl/{main_topic}/{sub_topic}/{topic}/`

---

## Key Commands

```bash
uv sync                                          # Install dependencies
uv run pytest                                    # Run all tests
uv run ruff check src/                           # Lint
uv run ruff format src/                          # Format
uv run python -m src.etl.{main_topic}.{sub_topic}.{topic}.transform   # Run transform (self-validates)
uv run python scripts/validate_topic.py {main_topic} {topic}          # Re-run the generic validator
uv run python scripts/check_bronze_freshness.py {main} {sub} {topic}  # Bronze checksum + unanalyzed-file gate
uv run python scripts/check_referential_integrity.py [--all]          # Fact->dimension FK sweep
uv run python scripts/check_approved_topics.py   # Detect drift in approved gold + dimension baselines
uv run python scripts/generate_contracts.py      # (Re)generate ODCS contracts for approved topics
uv run python scripts/generate_dimension_contracts.py  # (Re)emit the 4 dimension contracts
uv run python scripts/check_contracts.py         # Contract CI gate (add --s3-test for R2 conformance)
uv tool install 'datacontract-cli[all]'          # Install the datacontract CLI
```

**Object store (Cloudflare R2)**: gold/bronze live in R2 (S3-compatible). Access via the `rclone` remote `r2:` or `aws s3 … --endpoint-url https://$R2_ACCOUNT_ID.r2.cloudflarestorage.com`. Creds: `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`.

---

## ETL Architecture

> **Code-level ETL guide: [`src/etl/CLAUDE.md`](src/etl/CLAUDE.md)** — the
> `transform.py` pipeline shape, shared `src/utils/` toolkit, and the manifest.
> Domain conventions: [`src/etl/education/CLAUDE.md`](src/etl/education/CLAUDE.md).
> This section covers the **workflow/skills** layer.

### Cardinal Rule

**Never edit gold data directly.** All changes must go through the topic's `transform.py`. After every edit, re-run both transform and validation.

Data quality always takes priority over code quality.

### Bronze-to-Gold Workflow

| Step | Skill / Tool | What it does |
|------|-------------|--------------|
| 1 | `/bronze-data-structure` | Analyze bronze files; produce `bronze-data-structure.md` (incl. provenance + checksums) |
| 2 | `/transform-topic` | Author + run `transform.py` — emits gold Parquet, the ODCS contract, the manifest, and **validates itself** (generic contract-driven validator; no per-topic validate.py) |
| 3a | `/data-review-claude` | Value-level accuracy review (judgment layer over the validator); produces `data-review-claude.md` |
| 3b | `data-review-codex` | Independent Codex review; produces `data-review-codex.md`. See [docs/codex-review-contract.md](docs/codex-review-contract.md) |
| 4 (user) | `/approve-topic` | Flip `approved: true`; capture gold + dimension hash baselines (requires fresh passing validation) |

**Orchestrators:** `/full-pipeline` (steps 1-gate + 2–3 + fix-from-reviews when needed), `/batch-pipeline` (parallel non-prompting batches of full-pipeline).

**Blocking integrity checks** — halt with a clear message instead of warning:
- Stale bronze checksums or **unanalyzed bronze files** (`scripts/check_bronze_freshness.py`; `--allow-stale-bronze` overrides staleness only, never unanalyzed files)
- Any categorical with `unmapped_count > 0` in `_transform_manifest.json`
- Any failing validation check — the transform exits non-zero (schema↔contract↔parquet, units/scale, grain uniqueness, contract quality SQL, FK integrity, vocabulary, geography nulling)
- Missing/stale manifest or `_validation.json` at data-review time; unacknowledged read-loss events

**Other skills:** `/pipeline-status`, `/review-transform`, `/fix-from-reviews`, `/next-topic`.

**"Next topic" semantics.** When no topic is named, invoke `/next-topic` — it picks the first unapproved topic alphabetically that has `bronze-data-structure.md` but no `transform.py` yet (topics awaiting approval are surfaced separately, not re-run). Pass `--dry-run` to preview.

**Maintenance:** `uv run python scripts/sync_topic_status.py` adds new bronze topics to the tracker (idempotent).

### Gold output + transform manifest

Fact tables are year-partitioned Parquet under `data/gold/{main_topic}/{topic}/`; dimensions are single non-partitioned Parquet under `data/gold/_dimensions/` (global) and `data/gold/{main_topic}/_dimensions/` (domain). Each `transform.py` emits `_transform_manifest.json` (categorical recode maps, per-year counts, metric summaries) that `/data-review-claude` reads for 100% categorical verification. Full mechanics: [`src/etl/CLAUDE.md`](src/etl/CLAUDE.md).

### Topic Approval Tracker

`topic-status.yaml` records approval state. Workflow:
1. Run `/full-pipeline <main_topic> <sub_topic> <topic>`.
2. Review gold parquet + both data-review reports.
3. Run `/approve-topic <main_topic> <sub_topic> <topic>` → flips `approved: true`, captures `approved_gold_sha256`.

**Drift detection.** `scripts/check_approved_topics.py` re-hashes approved gold **and the dimension baselines** and reports changes. `/pipeline-status` runs it (CI cannot — parquet is not in git). After a dimension rebuild, also run `scripts/check_referential_integrity.py`.

---

## Gold Data Model

Star schema: lean fact tables (keys + metrics) + shared dimension tables. Full spec in `data-cleaning-standards` skill.

- Fact tables contain only `year`, geography FKs, `demographic` (if applicable), categoricals, and metrics — no names or labels.
- **Natural keys only** — no surrogate integer keys. Fact tables join to dimensions on the natural key.
- **Demographic categories are mutually exclusive within a category.** The `all` row is the only row allowed to overlap with category-specific rows. `asian` / `pacific_islander` are mutually exclusive with `asian_pacific_islander` — a topic publishes the split pair OR the combined rollup, never both. See `data-cleaning-standards` §5a–§5b.

---

## Data Contracts

Each approved topic has a git-tracked **ODCS v3.1.0** contract at `contracts/{main_topic}/{topic}.odcs.yaml` — the single machine-readable schema artifact consumed by the API, the generic validator (which derives its entire per-topic config from it — see `src/utils/contract_reader.py`), the MCP server, and Data Talk (whose catalog digest + planner dataset enum are built from the same registry at boot). See [docs/contract-creation.md](docs/contract-creation.md) for how contracts are emitted.

**Emitted by the transform.** `write_data_dictionary()` (`src/utils/metadata.py`) → `src/utils/contract_emitter.py`. No `_metadata.json`. Re-running the transform re-emits the contract.

**Per-column `unit`.** Each metric column declares `unit`: `count | proportion | ratio | score | rating | currency | percentile` (with optional `value_min`/`value_max`; omit for exempt columns). Range checks auto-derive: `proportion` → `[0,1]`; `ratio`/`count` → `≥ 0`; `score`/`rating`/`percentile` → `[value_min, value_max]`.

**Per-column key metric.** Every fact table declares its headline metric: **exactly one** column sets `"key_metric": True` (the single metric most users want — a score/proportion over a count, the most granular over a derived category; the emitter raises otherwise, and also emits a schema-object `key_metric: <colname>` pointer). The count column(s) composing a rate/average key metric set `"metric_component": "numerator"|"denominator"` (`unit: count`). See data-cleaning-standards §4c. **These are served, not contract-only:** the schema endpoint (`/datasets/{m}/{t}`) and MCP `describe_dataset` expose the topic-level `key_metric` + per-column `key_metric_grain_contributor` / `metric_component`, and MCP `query_dataset`/`aggregate` flag the headline column with `is_key_metric`.

**Auto-derived fields (no authoring needed).** The emitter auto-derives: row grain (`primaryKey`/`primaryKeyPosition`), the key metric's `key_metric_grain_contributor` flags (grain − year − geography), `limitations`, `schema_hash`, `example_queries`, `foreign_keys` block, and layout properties. Override `limitations`/`usage`/`example_queries` via kwargs only when the derived prose is insufficient.

**`version` / `schema_hash` policy.** Stay at `version: 1.0.0`. Bump minor for additive changes; bump major for breaking changes (renamed/removed/retyped column, changed grain). Unchanged `schema_hash` guarantees reproducible regeneration.

**Dimension contracts.** `contracts/education/_dimensions/{districts,schools}.odcs.yaml` and `contracts/_dimensions/{demographics,counties}.odcs.yaml`. Re-emit: `uv run python scripts/generate_dimension_contracts.py`. The districts dim exposes a `district_census_id` link key (NULL for charters/RESAs/state agencies). **A dimension attribute that declares an `enum` becomes a fact-query filter** (see REST/MCP "Dimension-attribute filters"): currently `demographic_category` and `district_type`. Adding/removing such an enum attribute changes the filter surface for every topic that joins that dimension — no per-topic change needed.

**The API consumes contracts directly** — joins and filters derived from contracts, nothing hardcoded.

**CI gate (`scripts/check_contracts.py`):** Fast (every push): lint + quality-type guard for all approved fact + dimension contracts (`--all` lints every committed fact contract regardless of approval). `--s3-test` (opt-in nightly): full `datacontract test` against R2 gold (via the S3-compatible API) + check-count assertion.

---

## Schema Evolution

### Fact table changes

1. Update `transform.py` — set `unit` on metric columns; author/adjust `quality_checks=` for any new cross-column invariant; grain/schema_hash/foreign_keys auto-derived.
2. Re-run transform → rewrites gold, re-emits the contract, and re-validates (the validator derives its config from the new contract — nothing to mirror). Bump `version` if breaking.

**Adding a column:** also verify it exists in bronze, add to `STANDARD_COLUMNS`/`TARGET_TYPES`.  
**Renaming a column:** also update any API endpoints referencing the old name.

> To refresh all approved contracts at once: `uv run python scripts/generate_contracts.py`.

### Dimension table changes

1. Update `src/etl/{main_topic}/build_dimensions.py` (or `build_demographics_dimension.py`).
2. Rebuild (see domain CLAUDE.md).
3. Verify FK columns in fact tables still match dimension PKs.

---

## Data Cleaning Standards

Full standards in the `data-cleaning-standards` skill: column naming, data types, percentage scaling, demographics, suppression, tidy format, logging.

**Known-bad data is NULLed.** Impossible values (e.g., ACT score > 36, proportion outside `[0,1]`) → NULL, row preserved, count logged. Extreme-but-conceivable values are preserved + documented. See `data-cleaning-standards` §4b.

---

## Object Storage (Cloudflare R2)

Gold and bronze live in **Cloudflare R2** (S3-compatible API). Bucket names are unchanged, and code/DuckDB still address objects with the `s3://` scheme — DuckDB resolves it through its R2 secret (`src/api/sql.py`), and boto3 through the R2 endpoint (`src/utils/s3.py`).

| Bucket | Purpose | Path pattern |
|--------|---------|-------------|
| `georgia-data-bronze` | Raw source files | `{main_topic}/{sub_topic}/{topic}/` |
| `georgia-data-gold` | Processed Parquet | `{main_topic}/{topic}/year=YYYY/` |

Gold also contains: `_dimensions/` (global), `{main_topic}/_dimensions/` (domain-specific), `crosswalks/`.

R2 is canonical. Local `data/` are working copies — wipe-and-rebuild safe.

Access via an `rclone` remote named `r2:` (recommended) or the AWS CLI with `--endpoint-url`. Credentials come from `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`.

```bash
# Hydrate locally (rclone sync mirrors the source, like aws s3 sync --delete; --dry-run first)
rclone sync r2:georgia-data-bronze data/bronze/
rclone sync r2:georgia-data-gold   data/gold/

# Push back (mirrors local → R2; deletes R2 objects absent locally, so --dry-run first)
rclone sync data/bronze/ r2:georgia-data-bronze
rclone sync data/gold/   r2:georgia-data-gold
```

**Geography identifiers:** State FIPS `13`; county FIPS 5-digit (e.g., `13121`); Census Tract GEOID 11-digit. Domain-specific IDs in the relevant domain `CLAUDE.md`.

---

## Common Tasks


### Adding a new data source

1. Create the `src/etl/{main_topic}/{sub_topic}/{topic}/` module + `transform.py` (extraction → bronze; transform → gold Parquet). Fact tables: geography keys only; names/census IDs belong in dimension tables.
2. Run the pipeline (`/full-pipeline`) + reviews, then approve in `topic-status.yaml` → API, MCP, Data Explorer, and Data Talk pick it up automatically. Add tests.

### Updating geography crosswalks

- **Logic:** `src/utils/crosswalks.py` — `add_census_district_code()` populates `district_census_id`. Add GOSA-to-Census name mismatches to `DISTRICT_NAME_OVERRIDES`.
- **Data:** `data/gold/crosswalks/ga_census_crosswalk.parquet` (no build script — maintained artifact; do not look for `src/crosswalks/build_crosswalks.py`).
- To fix a missing `district_census_id`: add to `DISTRICT_NAME_OVERRIDES`, then `uv run python -m src.etl.education.build_dimensions`.

