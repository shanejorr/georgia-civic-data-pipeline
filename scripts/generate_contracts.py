"""Batch-regenerate ODCS data contracts for approved education topics.

Contracts are no longer generated from ``_metadata.json``. Each topic's
``transform.py`` emits its ODCS contract directly from its in-code schema
declaration (via ``write_data_dictionary`` -> ``src/utils/contract_emitter``).
This script is a thin batch wrapper: for each approved ``education/*`` topic it
re-runs the topic's ``transform.py`` (``python -m
src.etl.{main}.{sub}.{topic}.transform``), which rewrites the gold parquet
(byte-identical for an unchanged transform) and re-emits the contract under
``contracts/{main_topic}/{topic}.odcs.yaml``.

Because regeneration re-runs the transform, prefer running the transform
directly when you've just edited one topic; use this wrapper to refresh every
approved contract at once. The contract projection logic itself lives in
``src/utils/contract_emitter.py`` (importable and unit-testable).

Run from the repo root:
    uv run python scripts/generate_contracts.py        # all approved topics
    uv run python scripts/generate_contracts.py --topic attendance
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
STATUS_FILE = REPO / "topic-status.yaml"
ETL_ROOT = REPO / "src" / "etl"


def approved_topics() -> list[tuple[str, str, str]]:
    """Return (main_topic, sub_topic, topic) for every approved topic."""
    topics = yaml.safe_load(STATUS_FILE.read_text())["topics"]
    out: list[tuple[str, str, str]] = []
    for key, meta in sorted(topics.items()):
        if (meta or {}).get("approved"):
            parts = key.split("/")
            out.append((parts[0], parts[1], "/".join(parts[2:])))
    return out


def transform_module(main: str, sub: str, topic: str) -> str:
    """Dotted module path for a topic's transform entrypoint."""
    return f"src.etl.{main}.{sub}.{topic}.transform"


def regenerate_one(main: str, sub: str, topic: str) -> tuple[bool, str]:
    """Re-run a topic's transform to re-emit its contract.

    Returns (ok, detail). The transform rewrites gold (byte-identical when
    unchanged) and emits the contract as a side effect.
    """
    module = transform_module(main, sub, topic)
    if not (ETL_ROOT / main / sub / topic / "transform.py").exists():
        return False, f"transform.py not found for {main}/{sub}/{topic}"
    res = subprocess.run(
        [sys.executable, "-m", module],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        tail = (res.stderr or res.stdout)[-800:]
        return False, f"transform failed (rc={res.returncode}): {tail}"
    contract = REPO / "contracts" / main / f"{topic}.odcs.yaml"
    if not contract.exists():
        return False, f"transform ran but no contract at {contract.relative_to(REPO)}"
    return True, str(contract.relative_to(REPO))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--topic", help="regenerate a single topic by name (default: all approved)"
    )
    args = ap.parse_args()

    targets = approved_topics()
    if args.topic:
        targets = [t for t in targets if t[2] == args.topic]
        if not targets:
            print(
                f"ERROR: {args.topic} is not an approved topic",
                file=sys.stderr,
            )
            return 2

    errors = 0
    for main_t, sub, topic in targets:
        ok, detail = regenerate_one(main_t, sub, topic)
        if ok:
            print(f"ok    {topic:56s} {detail}")
        else:
            errors += 1
            print(f"ERROR {topic:56s} {detail}", file=sys.stderr)

    print(f"\n{len(targets) - errors}/{len(targets)} contracts regenerated")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
