"""Recompute approved-topic gold hashes and report drift.

Every approved entry in ``topic-status.yaml`` stores an ``approved_gold_sha256``
field captured at approval time (see ``scripts/approve_topic.py``). This script
re-hashes each approved topic's ``data/gold/{main_topic}/{topic}/`` directory
and reports any drift.

Exit codes:
  0 — no approved topics drifted (missing-gold topics are reported as warnings).
  1 — at least one approved topic's gold hash differs from the stored hash.
  2 — ``topic-status.yaml`` missing or malformed.

Run from the repo root:

    uv run python scripts/check_approved_topics.py

Intended to be wired into CI and surfaced by the ``/pipeline-status`` skill.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from approve_topic import (  # noqa: E402
    GOLD_ROOT,
    STATUS_FILE,
    compute_dimension_hashes,
    compute_gold_sha256,
)


def check_dimension_drift(data: dict) -> list[str]:
    """Compare the stored ``dimensions:`` hash baseline against current parquet.

    The baseline is captured at approval time so a dimension rebuild after
    approval is a visible event (facts were FK-checked against those exact
    dimensions). Returns drift description lines (empty == clean / no baseline).
    """
    stored = data.get("dimensions") or {}
    if not stored:
        return []
    current = compute_dimension_hashes()
    drifted = []
    for name, stored_hash in sorted(stored.items()):
        cur = current.get(name)
        if cur is None:
            drifted.append(f"dimension {name}: parquet missing (baseline exists)")
        elif cur != stored_hash:
            drifted.append(
                f"dimension {name}\n    stored:  {stored_hash}\n    current: {cur}"
            )
    return drifted


def main() -> int:
    if not STATUS_FILE.exists():
        print(f"ERROR: {STATUS_FILE} not found", file=sys.stderr)
        return 2

    data = yaml.safe_load(STATUS_FILE.read_text()) or {}
    topics = data.get("topics", {}) or {}

    approved = [(k, v) for k, v in topics.items() if (v or {}).get("approved")]
    if not approved:
        print("No approved topics to check.")
        return 0

    drifted: list[str] = []
    missing_hash: list[str] = []
    missing_gold: list[str] = []

    for key, entry in approved:
        main_topic, _, topic = key.split("/")
        stored = entry.get("approved_gold_sha256")
        gold_dir = GOLD_ROOT / main_topic / topic

        # The gold_dir may exist on CI (README.md etc. are committed) but contain
        # no .parquet files, since those are gitignored. Treat that as missing gold
        # so drift detection only runs where parquet data is actually present.
        if not gold_dir.exists() or not any(gold_dir.rglob("*.parquet")):
            missing_gold.append(key)
            continue
        if not stored:
            missing_hash.append(key)
            continue

        current = compute_gold_sha256(main_topic, topic)
        if current != stored:
            drifted.append(f"{key}\n    stored:  {stored}\n    current: {current}")

    if missing_gold:
        print(f"WARN: {len(missing_gold)} approved topic(s) have no gold directory:")
        for key in missing_gold:
            print(f"  - {key}")
        print()

    if missing_hash:
        print(
            f"WARN: {len(missing_hash)} approved topic(s) were approved before hash "
            "capture was added. Re-run /approve-topic to record a baseline:"
        )
        for key in missing_hash:
            print(f"  - {key}")
        print()

    dimension_drift = check_dimension_drift(data)

    if drifted or dimension_drift:
        if drifted:
            print(
                f"DRIFT: {len(drifted)} approved topic(s) no longer match"
                " their stored hash:"
            )
            for line in drifted:
                print(f"  - {line}")
            print()
        if dimension_drift:
            print(
                f"DRIFT: {len(dimension_drift)} dimension table(s) changed "
                "since the approval baseline (facts were FK-checked against "
                "the old dimensions):"
            )
            for line in dimension_drift:
                print(f"  - {line}")
            print()
            print(
                "Run scripts/check_referential_integrity.py to confirm "
                "approved facts still resolve, then re-approve to refresh "
                "the baseline."
            )
        print(
            "Investigate whether the change is intentional."
            " If the new gold is correct, "
            "re-run /approve-topic to update the baseline."
        )
        return 1

    checked = len(approved) - len(missing_gold) - len(missing_hash)
    print(f"OK: {checked} approved topic(s) match their stored hash.")
    if data.get("dimensions"):
        print(f"OK: {len(data['dimensions'])} dimension baseline(s) match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
