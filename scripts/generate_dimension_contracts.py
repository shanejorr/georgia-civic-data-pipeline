"""Re-emit the ODCS data contracts for the gold dimension tables.

Thin batch wrapper, the dimension-table sibling of
``scripts/generate_contracts.py``. Unlike the fact-contract wrapper (which
re-runs each topic's transform), this script emits the dimension contracts
DIRECTLY from the in-code dimension schema declarations in
``src/utils/dimension_contract_emitter.py`` plus the live code constants
(``DISTRICT_TYPE_*`` / ``HARDCODED_DISTRICTS`` for district_type,
``DEMOGRAPHIC_CATEGORIES`` for demographic_category). It does NOT re-scan the
1.6G bronze tree, so it is fast and deterministic.

The same emission happens as a side effect of the dim build scripts'
``main()`` (``src.etl.education.build_dimensions`` /
``src.etl.build_demographics_dimension``); use this wrapper to refresh all
dimension contracts at once without rebuilding the dimension parquet.

Run from the repo root:
    uv run python scripts/generate_dimension_contracts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.utils.dimension_contract_emitter import (  # noqa: E402
    emit_counties_contract,
    emit_demographics_contract,
    emit_districts_contract,
    emit_schools_contract,
)


def main() -> int:
    """Emit all dimension contracts; print ok/error per dim."""
    emitters = [
        ("districts", emit_districts_contract),
        ("schools", emit_schools_contract),
        ("demographics", emit_demographics_contract),
        ("counties", emit_counties_contract),
    ]

    errors = 0
    for name, emit in emitters:
        try:
            path = emit()
            print(f"ok    {name:14s} {path.relative_to(REPO)}")
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"ERROR {name:14s} {exc}", file=sys.stderr)

    print(f"\n{len(emitters) - errors}/{len(emitters)} dimension contracts emitted")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
