"""Validate a gold topic against its ODCS contract — the generic validator CLI.

There are no per-topic validate.py files: the entire validation config derives
from the topic's contract (``src/utils/contract_reader.derive_topic_config``),
and the full check suite — structural checks, contract↔parquet schema
conformance, percentage scale by ``unit``, grain uniqueness, the contract's
own quality SQL, FK integrity against the dimensions, canonical vocabulary —
runs via ``ValidationRunner`` / ``run_topic_validation``.

Transforms call ``run_topic_validation(GOLD_DIR)`` automatically as the last
statement of ``main()``; this script is the standalone re-run.

Usage (from the repo root):

    uv run python scripts/validate_topic.py education act_scores

Exit codes: 0 all checks pass | 1 failures (incl. missing contract).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.utils.validators import (  # noqa: E402
    GoldValidationError,
    run_topic_validation,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("main_topic", help="e.g. education")
    ap.add_argument("topic", help="e.g. act_scores")
    args = ap.parse_args()

    gold_dir = REPO / "data" / "gold" / args.main_topic / args.topic
    if not gold_dir.exists():
        print(f"ERROR: no gold directory at {gold_dir}", file=sys.stderr)
        return 1

    try:
        report = run_topic_validation(gold_dir, raise_on_failure=False)
    except GoldValidationError as exc:
        # Contract precondition failure — the fail report was still written.
        print(f"FAIL  {args.topic}: {exc}", file=sys.stderr)
        return 1

    counts = report.summary_counts
    status = "PASS" if report.passed else "FAIL"
    print(
        f"{status}  {args.topic}: {counts['pass']} passed, "
        f"{counts['fail']} failed, {counts['warning']} warnings "
        f"-> {report.gold_dir / '_validation.json'}"
    )
    for check in report.checks:
        if check.status == "fail":
            print(f"  FAIL {check.name}: {check.message}")
            for detail in check.details or []:
                print(f"    - {detail}")
        elif check.status == "warning":
            print(f"  WARN {check.name}: {check.message}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
