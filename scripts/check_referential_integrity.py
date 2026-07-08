"""Verify fact→dimension FK integrity across topics — repeatable, post-approval.

Per-topic FK checking runs inside validation (``check_foreign_keys``, driven
by each contract's ``foreign_keys`` block). This script makes the same check
repeatable across the whole repo so a **dimension rebuild after approval**
cannot silently orphan fact rows: run it any time dimensions change, and from
/pipeline-status alongside drift detection.

It also asserts **dimension primary-key uniqueness** (and non-nullness) — the
invariant the API's joins and pre-join row counts depend on: a duplicate PK in a
dimension would silently fan out fact rows and inflate pagination totals.

Default scope: approved topics (the published surface). ``--all``: every topic
that has both gold data and a contract. Dimension PKs are always checked.

Usage (from the repo root):

    uv run python scripts/check_referential_integrity.py
    uv run python scripts/check_referential_integrity.py --all

Exit codes: 0 all FKs resolve + dim PKs unique | 1 violations | 2 setup error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.utils import contract_reader  # noqa: E402
from src.utils.contract_emitter import contract_path_for  # noqa: E402
from src.utils.dimension_contracts import (  # noqa: E402
    DimensionMeta,
    dimension_parquet_path,
    iter_dimension_metadata,
)
from src.utils.validators import check_foreign_keys  # noqa: E402

CONTRACTS_DIR = REPO / "contracts"

STATUS_FILE = REPO / "topic-status.yaml"
GOLD_ROOT = REPO / "data" / "gold"


def discover_topics(include_all: bool) -> list[tuple[str, str]]:
    """Return (main_topic, topic) pairs in scope."""
    if not STATUS_FILE.exists():
        raise FileNotFoundError(f"{STATUS_FILE} not found")
    status = yaml.safe_load(STATUS_FILE.read_text()) or {}
    topics = status.get("topics", {}) or {}
    out: list[tuple[str, str]] = []
    for key, entry in sorted(topics.items()):
        parts = key.split("/")
        if len(parts) != 3:
            continue
        main_topic, _, topic = parts
        if not include_all and not (entry or {}).get("approved"):
            continue
        out.append((main_topic, topic))
    return out


def check_topic(main_topic: str, topic: str) -> tuple[str, str]:
    """Run the FK check for one topic. Returns (status, detail)."""
    gold_dir = GOLD_ROOT / main_topic / topic
    if not gold_dir.exists() or not any(gold_dir.rglob("*.parquet")):
        return "SKIP", "no gold parquet"
    contract_path = contract_path_for(main_topic, topic)
    if not contract_path.exists():
        return "SKIP", f"no contract at {contract_path.relative_to(REPO)}"

    contract = contract_reader.load_contract(contract_path)
    fks = contract_reader.foreign_keys(contract)
    if not fks:
        return "PASS", "contract declares no foreign keys"

    frames = [
        pl.read_parquet(p)
        for p in sorted(gold_dir.rglob("*.parquet"))
        if not p.name.startswith("_")
    ]
    combined = pl.concat(frames, how="diagonal")
    result = check_foreign_keys(combined, gold_dir, fks)
    if result.status == "fail":
        return "FAIL", "; ".join(result.details or [result.message])
    return "PASS", result.message


def _dimension_parquet(dim: DimensionMeta) -> Path:
    """Resolve a dimension's on-disk parquet (mirrors the API engine).

    Delegates the global-vs-domain path logic to the shared helper so the file
    checked here is exactly the one the API engine reads.
    """
    return dimension_parquet_path(GOLD_ROOT, dim)


def check_dimension_pks() -> tuple[int, int, list[str]]:
    """Assert every dimension's primary key is unique and non-null in its parquet.

    This is the invariant the API's joins rely on: each fact table LEFT-joins a
    dimension on its PK and counts fact rows *pre-join*, both of which assume the
    PK is unique. A duplicate PK row would silently fan out fact rows (and inflate
    pagination totals) with no error anywhere; a NULL PK would never match. The
    dimensions (and their declared PKs) come from the same dimension contracts
    the API's ``build_registry`` loads — via the shared
    ``src.utils.dimension_contracts`` discovery — so this checks exactly what the
    running service depends on, without importing the serving layer.

    Returns ``(checked, failures, lines)`` for the caller to print and fold into
    the exit code.
    """
    checked = failures = 0
    lines: list[str] = []
    for dim in iter_dimension_metadata(CONTRACTS_DIR):
        pk = list(dim.primary_key)
        path = _dimension_parquet(dim)
        if not path.exists():
            lines.append(
                f"  SKIP  dim {dim.name:20s} no parquet at {path.relative_to(REPO)}"
            )
            continue
        checked += 1
        df = pl.read_parquet(path, columns=pk)
        rows = df.height
        uniq = df.n_unique()
        null_rows = df.filter(
            pl.any_horizontal([pl.col(c).is_null() for c in pk])
        ).height
        if rows == uniq and null_rows == 0:
            lines.append(
                f"  PASS  dim {dim.name:20s} pk={tuple(pk)} rows={rows} unique"
            )
            continue
        failures += 1
        problems: list[str] = []
        if rows != uniq:
            problems.append(
                f"{rows - uniq} duplicate PK row(s) (rows={rows}, distinct={uniq})"
            )
        if null_rows:
            problems.append(f"{null_rows} NULL-PK row(s)")
        lines.append(
            f"  FAIL  dim {dim.name:20s} pk={tuple(pk)}: " + "; ".join(problems)
        )
    return checked, failures, lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--all",
        action="store_true",
        help="check every topic with gold + contract (default: approved only)",
    )
    args = ap.parse_args()

    try:
        topics = discover_topics(include_all=args.all)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not topics:
        print("No topics in scope (none approved; use --all during a rebuild).")
        return 0

    failures = 0
    checked = 0
    for main_topic, topic in topics:
        status, detail = check_topic(main_topic, topic)
        if status == "SKIP":
            print(f"  SKIP  {main_topic}/{topic:55s} {detail}")
            continue
        checked += 1
        if status == "FAIL":
            failures += 1
            print(f"  FAIL  {main_topic}/{topic}")
            for part in detail.split("; "):
                print(f"        {part}")
        else:
            print(f"  PASS  {main_topic}/{topic:55s} {detail}")

    # Dimension PK uniqueness — the invariant the API's joins + pre-join counts
    # depend on. Checked here (not at API boot) so boot stays data-independent.
    dim_checked, dim_failures, dim_lines = check_dimension_pks()
    if dim_lines:
        print("\nDimension primary keys:")
        for line in dim_lines:
            print(line)

    summary = f"\nReferential integrity: {checked - failures}/{checked} topic(s) clean"
    if failures:
        summary += f", {failures} with violations"
    summary += f"; {dim_checked - dim_failures}/{dim_checked} dimension PK(s) unique"
    if dim_failures:
        summary += f", {dim_failures} with violations"
    print(summary)
    return 1 if (failures or dim_failures) else 0


if __name__ == "__main__":
    sys.exit(main())
