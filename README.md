# Georgia Civic Data — Pipeline

The **data-cleaning pipeline** behind [Georgia Civic Data](https://georgiacivicdata.org):
the code, data contracts, and provenance documentation that turn messy public-agency
files into clean, validated, well-documented datasets about Georgia (education and
criminal justice, with more to come).

This repository is a **public, filtered mirror** of the pipeline half of a larger private
monorepo. It is regenerated from that monorepo by a script, so it always reflects the
canonical source. The public serving layers (REST API, MCP server, chatbot, web app) are
**not** part of this repo.

## What's here — and what isn't

**Here (the pipeline):**

- `src/etl/` — per-topic `transform.py` pipelines (extraction → *bronze*, transform → *gold*).
- `src/utils/` — the shared ETL toolkit (transformers, validators, contract emitter/reader,
  vocabulary, demographics, crosswalks, geography).
- `contracts/` — the [ODCS](https://bitol-io.github.io/open-data-contract-standard/) v3.1
  data contracts each approved dataset is emitted with and validated against.
- `data/` — **provenance and structure docs only** (`bronze-data-structure.md`,
  `_provenance.md`) describing where every source file came from and what it contains.
- `data_sources/` — source-catalog / ingestion blueprint notes per domain.
- `scripts/` — pipeline tooling (validate a topic, (re)generate contracts, freshness/drift
  checks, approval).
- `.claude/skills/` — the authoring/review workflow the pipeline is built with.
- `docs/` — how the pipeline and contracts work.

**Not here:**

- **The bulk data bytes.** Bronze and gold live in **Cloudflare R2** (S3-compatible), not
  in git — several GB, including files past GitHub's size limits. This repo ships the code
  + contracts + provenance docs that *describe and produce* that data, not the data itself.
- **The serving layers** — REST API, MCP server, the "Data Talk" chatbot, and the Next.js
  web app / Data Explorer live in the private monorepo and are stripped from this mirror.

## The pipeline in one picture

```
public-agency files  ──▶  bronze/  ──▶  transform.py  ──▶  gold/  ──▶  ODCS contract
   (raw, as-downloaded)    (documented,   (clean + tidy +    (star-schema   (machine-readable
                            checksummed)   self-validating)    parquet)       schema + quality)
```

A **medallion** flow with a hard rule: **never edit gold directly** — every change goes
through a topic's `transform.py`, which re-emits gold, re-emits the contract, and
**validates itself** on every run (schema ↔ contract ↔ parquet, units/scale, grain
uniqueness, foreign-key integrity, controlled vocabularies, geography nulling). Data
quality always takes priority over code quality.

Gold is a **star schema**: lean fact tables (geography keys + metrics) joined to shared
dimension tables on natural keys — no surrogate integers, no names or labels in fact tables.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11.

```bash
uv sync                                                    # install dependencies
uv run pytest                                              # run the pure ETL/contract test suite

# Work a topic (needs the bronze bytes hydrated from R2 — see "Data lives in R2" below):
uv run python -m src.etl.education.gosa.act_scores.transform   # run a transform (self-validating)
uv run python scripts/validate_topic.py education act_scores   # re-run the generic validator

# Contracts:
uv run python scripts/generate_contracts.py                # (re)generate ODCS contracts
uv run python scripts/check_contracts.py                   # contract CI gate (lint + quality types)
```

`uv run pytest` passes **without any bulk data** — the committed tests exercise the shared
utilities and contract logic over synthetic inputs. Commands that read bronze/gold require
the data to be hydrated first.

## Data lives in R2

Gold and bronze are stored in **Cloudflare R2** (S3-compatible). DuckDB and the pipeline
address objects with the `s3://` scheme. Hydrate a local working copy (e.g. with
[`rclone`](https://rclone.org/)) before running data-dependent steps; local `data/` is a
disposable working copy, R2 is canonical. See [`CLAUDE.md`](CLAUDE.md) → *Object Storage*
for bucket layout and access details.

## Data contracts

Every approved dataset has a git-tracked **ODCS v3.1** contract under `contracts/`. The
contract is the single machine-readable schema artifact: the validator derives its entire
per-topic configuration from it, and each metric column declares a `unit`
(`count | proportion | ratio | score | rating | currency | percentile`) from which range
checks auto-derive. Exactly one column per fact table is the headline `key_metric`. See
[`docs/contract-creation.md`](docs/contract-creation.md).

## Repository layout

| Path | What it is |
|------|-----------|
| `src/etl/{main_topic}/{sub_topic}/{topic}/transform.py` | Per-topic ETL |
| `src/utils/` | Shared ETL toolkit (validators, contract emitter/reader, …) |
| `contracts/{main_topic}/{topic}.odcs.yaml` | ODCS data contracts (+ dimension contracts) |
| `data/**/{bronze-data-structure,_provenance}.md` | Provenance + structure docs |
| `topic-status.yaml` | Per-topic approval tracker |
| `scripts/` | Pipeline tooling |
| `docs/` | Pipeline + contract documentation |

Deeper guides: [`CLAUDE.md`](CLAUDE.md) (top-level conventions),
[`src/etl/CLAUDE.md`](src/etl/CLAUDE.md) (the `transform.py` shape + shared toolkit),
[`src/etl/education/CLAUDE.md`](src/etl/education/CLAUDE.md) (domain conventions),
[`docs/data-cleaning.md`](docs/data-cleaning.md) (end-to-end walkthrough).

## Contributing

Issues and PRs that improve data quality, provenance documentation, contracts, or the
shared toolkit are welcome. Because this is a generated mirror, code changes are ultimately
integrated in the upstream monorepo; a merged PR here will be reflected there. Please keep
the medallion rule (edit `transform.py`, never gold) and make sure `uv run pytest` and
`scripts/check_contracts.py` pass.

## License

[MIT](LICENSE) © 2026 Shane Orr.
