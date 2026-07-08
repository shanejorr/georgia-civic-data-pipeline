# How Georgia Data Contracts Are Created

## Summary

Contracts are emitted directly by each topic's `transform.py` rather than authored by hand. When the transform calls `write_data_dictionary()` (in `src/utils/metadata.py`), that function hands the transform's in-code column declaration — the `columns=[...]` list, with each column's `column_role` and optional `unit` key, plus topic-level metadata — to `src/utils/contract_emitter.py`, which projects it into a standards-compliant **ODCS v3.1** document and writes it to `contracts/{main_topic}/{topic}.odcs.yaml`. The emitter fills in the rest from what the transform just produced: it reads the detail levels from the gold parquet basenames under the topic's `output_dir` (`year=*/*.parquet`), derives each metric column's range-check quality SQL from its `unit`, auto-derives the row grain, `limitations`/`null_semantics`, layout metadata, a deterministic `schema_hash`, example queries, and a `foreign_keys` block, and folds in `sub_topic`, `year_range`, and descriptions. There is no separate generate step and no `_metadata.json` intermediary — re-running the transform re-emits the contract, and `scripts/generate_contracts.py` is just a thin batch wrapper that re-runs every approved topic's transform to refresh all contracts at once.

## Flow

```
src/etl/{main_topic}/{sub_topic}/{topic}/transform.py
   │  columns=[{ name, logical_type, column_role, unit?, value_min?, value_max?, null_meaning?, key_metric?, metric_component?, description }, ...]
   │  + topic metadata (source, source_url, sub_topic; optional limitations/usage/example_queries overrides)
   ▼
write_data_dictionary()                         ── src/utils/metadata.py
   │
   ▼
contract_emitter.py  ──────────────────────────── src/utils/contract_emitter.py
   │   ├─ projects columns → ODCS schema[0].properties[]
   │   ├─ reads detail levels from gold just written:
   │   │     data/gold/{main_topic}/{topic}/year=*/*.parquet  (basenames)
   │   ├─ derives quality SQL from each column's unit
   │   ├─ auto-derives grain (primaryKey/primaryKeyPosition + dataGranularityDescription)
   │   ├─ derives limitations + null_semantics; emits layout (partition_columns/path_template + local_gold server)
   │   ├─ computes a deterministic schema_hash; builds example_queries + a foreign_keys block
   │   └─ folds in sub_topic, year_range, descriptions
   ▼
contracts/{main_topic}/{topic}.odcs.yaml         ── the contract (git-tracked)
```

## Inputs → Where They Come From

| Contract element | Source | Notes |
|---|---|---|
| Column names, types, descriptions | `transform.py` `columns=[...]` declaration | The in-code schema is authored once, here |
| `column_role` (per property) | `transform.py` column key | `year` / `fk_*` / `categorical` / `metric` — drives FK joins + allowlist |
| `unit` (per property) | `transform.py` column key | `count \| proportion \| ratio \| score \| rating \| currency \| percentile` (+ optional `value_min` / `value_max`); omit for exempt columns. Replaces the old `pct_scale`. |
| Quality SQL (range checks) | Derived by emitter from `unit` | `proportion` → within `[0, 1]`; `ratio` / `count` → `≥ 0`; `score`/`rating`/`percentile` → within `[value_min, value_max]` (percentile defaults 0–100); `currency` → none |
| `key_metric` (per property + schema pointer) | `transform.py` column key `"key_metric": True` | The single headline metric — the one most users want given the description (prefer a score/proportion over a count, the most granular over a derived category). **Exactly one per fact table with metrics** (emitter raises otherwise). Also emitted as a schema-object `key_metric: <colname>` pointer for one-lookup resolution. A categorical key metric additionally needs `"key_metric_categorical": True`. |
| `metric_component` (per property) | `transform.py` column key `"metric_component": "numerator" \| "denominator"` | On the count column(s) composing the key metric when it is a rate/average (must be `unit: count`). e.g. `num_tested` is the `denominator` of `avg_score`; `graduate_count`/`cohort_size` are the `numerator`/`denominator` of `graduation_rate`. |
| `key_metric_grain_contributor` (per property) | **Auto-derived** by emitter from the grain | The key metric's disaggregation axes = grain − `year` − geography columns (so it keeps `demographic` + every categorical like `test_component`/`grade_level`, and excludes `year`/`district_code`/`school_code`). No authoring. |
| Row grain (`primaryKey`/`primaryKeyPosition`, `dataGranularityDescription`, `grain`) | Auto-derived by emitter | `year` + present FK cols + categoricals, in declared order |
| `limitations` + `null_semantics` / `null_meaning` | Derived by emitter from detail levels (+ optional per-column `null_meaning`) | Mentions state/district nulling only for levels that exist; `limitations`/`usage` overridable via kwargs |
| Layout (`partition_columns`, `path_template`, `local_gold` server) | Emitter logic | Makes gold paths self-describing; second `servers` entry for local reads |
| `schema_hash` (top-level) | Deterministic sha256 over each property's name/type/role/unit/sorted-enum + grain | Same schema → same hash → reproducible regeneration |
| `example_queries` | Auto-derived from shape (overridable via kwarg) | 2–3 deterministic DuckDB queries |
| `foreign_keys` (schema custom property) | Emitter (one descriptor per FK column) | `target_object` / `target_columns` / `attribute_columns` / `scope`; for MCP/non-API consumers |
| `detail_levels` / `default_detail` | Gold parquet basenames under `output_dir` | Read from `year=*/*.parquet` the transform just wrote |
| `sub_topic`, `year_range`, `source`, descriptions | Topic metadata + emitter logic | Folded in at emit time |

> **Served, not contract-only.** `key_metric` (topic-level), `key_metric_grain_contributor`,
> and `metric_component` are surfaced on the REST schema endpoint (`/datasets/{m}/{t}`) and MCP
> `describe_dataset` — so a consumer resolves the headline metric without parsing the raw ODCS.
> The registry parses them once at boot (`src/api/registry.py`); `query_dataset`/`aggregate`
> additionally flag the headline column with `is_key_metric`.

## Single-Topic vs. All-Topics

| Goal | Command | What runs |
|---|---|---|
| Re-emit **one** topic's contract | `uv run python -m src.etl.{main_topic}.{sub_topic}.{topic}.transform` | The transform writes gold **and** re-emits its contract |
| Refresh **all** approved contracts | `uv run python scripts/generate_contracts.py` | Thin batch wrapper that re-runs every approved topic's transform |
| Refresh the **dimension** contracts | `uv run python scripts/generate_dimension_contracts.py` | Re-runs both dimension builds, which re-emit the 3 dim contracts |

## Dimension Contracts

The shared dimension tables have ODCS contracts too, emitted the same way — as a side effect of the dimension **build scripts** (`src/etl/education/build_dimensions.py` and `src/etl/build_demographics_dimension.py`), via `src/utils/dimension_contract_emitter.py`. They live at `contracts/education/_dimensions/{districts,schools}.odcs.yaml` (domain-scoped) and `contracts/_dimensions/demographics.odcs.yaml` (global). `scripts/generate_dimension_contracts.py` re-runs both builds to refresh all three at once.

What's distinct about a dimension contract:

- **`entity_kind: dimension` + `scope`** (`domain`/`global`) — the absence of `sub_topic`/`detail_levels` (plus this marker) is what keeps a dim contract from being parsed as a fact topic.
- **Key vs. attribute `column_role`s** and native `primaryKey`/`primaryKeyPosition` on the key column(s). The **schools** dim has a composite primary key `(district_code, school_code)` — the API derives its composite join from this, not from hardcoded SQL.
- **Enums** for `district_type` and `demographic_category`.
- **`link_keys`** — the **districts** dim declares `district_census_id` as a cross-dataset link key (target `census.county_fips` via the Census crosswalk; NULL for charters/RESAs/state agencies).
- **`semantics`** — the **demographics** dim declares mutual-exclusivity within a category and that `all` is the denominator.

The REST API consumes these contracts directly: it derives its fact→dimension **joins** from the dimension contracts (FK role → dim → join on the dim's full primary key) and surfaces every categorical column as an **independent per-column filter** (the old single `category` param is gone).

## Key Property

The transform is the **single schema source**. Because the contract is a byproduct of the same run that writes the gold parquet, the two cannot drift — and `scripts/generate_contracts.py` is just a loop over that one mechanism. The same is true for the dimension contracts and their build scripts.
