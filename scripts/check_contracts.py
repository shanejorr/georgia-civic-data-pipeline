"""CI gate for the generated ODCS contracts. Sibling to check_approved_topics.py.

Covers both **fact** contracts (one per approved education topic, discovered
from ``topic-status.yaml``) and the **dimension** contracts under
``contracts/education/_dimensions/`` and ``contracts/_dimensions/`` (discovered
by glob, since dimensions are not in ``topic-status.yaml``).

Two modes:

  Default (fast, no network, no AWS):
    * coverage   -- every approved education topic has a committed contract,
                    AND the three expected dimension contracts (districts,
                    schools, demographics) exist
    * lint       -- `datacontract lint` passes for every contract (fact + dim)
    * type-guard -- every quality check declares a `type` (ODCS defaults to
                    `library`; a SQL check missing `type: sql` is SILENTLY
                    skipped at test time, so guard it statically here)

  --s3-test (heavy, needs AWS creds in env; intended for a scheduled job):
    * runs `datacontract test --server <s3 server> --output-format json` per
      contract (fact + dim; the s3 server is named ``s3_gold`` in both)
    * asserts the overall result is `passed`
    * CHECK-COUNT ASSERTION: the number of quality checks that actually ran
      (category == "quality") equals the number declared in the contract --
      catching any silent-skip regression on real data.

Exit codes: 0 ok | 1 failures | 2 setup error.

    uv run python scripts/check_contracts.py
    uv run python scripts/check_contracts.py --s3-test [-j 5]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO / "contracts"
STATUS_FILE = REPO / "topic-status.yaml"
DC = shutil.which("datacontract")

# Dimension contracts are not in topic-status.yaml; they live in fixed
# locations and have a known, closed set. Coverage fails if any is missing.
DIMENSION_CONTRACTS: dict[str, Path] = {
    "districts": CONTRACTS_DIR / "education" / "_dimensions" / "districts.odcs.yaml",
    "schools": CONTRACTS_DIR / "education" / "_dimensions" / "schools.odcs.yaml",
    "demographics": CONTRACTS_DIR / "_dimensions" / "demographics.odcs.yaml",
    "counties": CONTRACTS_DIR / "_dimensions" / "counties.odcs.yaml",
}


def approved_topics() -> list[tuple[str, str]]:
    """(main_topic, topic) for every approved topic, any main topic."""
    topics = yaml.safe_load(STATUS_FILE.read_text())["topics"]
    out = []
    for key, meta in sorted(topics.items()):
        if (meta or {}).get("approved"):
            parts = key.split("/")
            out.append((parts[0], "/".join(parts[2:])))
    return out


def contract_path(main: str, topic: str) -> Path:
    return CONTRACTS_DIR / main / f"{topic}.odcs.yaml"


def discover_dimension_contracts() -> list[Path]:
    """Glob the dimension contracts under the two ``_dimensions`` locations."""
    found: list[Path] = []
    dim_dirs = [CONTRACTS_DIR / "_dimensions"]
    dim_dirs.extend(
        sorted(
            p / "_dimensions"
            for p in CONTRACTS_DIR.iterdir()
            if p.is_dir()
            and not p.name.startswith("_")
            and (p / "_dimensions").is_dir()
        )
    )
    for dim_dir in dim_dirs:
        found.extend(sorted(dim_dir.glob("*.odcs.yaml")))
    return found


def declared_quality_count(path: Path) -> int:
    doc = yaml.safe_load(path.read_text())
    return sum(len(s.get("quality", []) or []) for s in doc.get("schema", []))


def s3_server_name(path: Path) -> str:
    """Name of the contract's ``s3``-type server (``s3_gold`` for fact + dim).

    Generalized so the dimension pass works even if a future dim contract
    names its S3 server differently — falls back to ``s3_gold``.
    """
    doc = yaml.safe_load(path.read_text())
    for srv in doc.get("servers", []) or []:
        if srv.get("type") == "s3":
            return srv.get("server", "s3_gold")
    return "s3_gold"


def lint_and_type_guard(path: Path, label: str | None = None) -> list[str]:
    """Run ``datacontract lint`` + the static quality-`type` guard on one contract.

    Contract-shape-agnostic: works on fact and dimension contracts alike.
    Returns a list of failure messages (empty == clean).
    """
    name = label or path.name
    failures: list[str] = []
    res = subprocess.run([DC, "lint", str(path)], capture_output=True, text=True)
    if res.returncode != 0:
        failures.append(f"LINT FAILED: {name}\n{res.stdout[-500:]}{res.stderr[-500:]}")
    doc = yaml.safe_load(path.read_text())
    for s in doc.get("schema", []):
        for q in s.get("quality", []) or []:
            if "type" not in q:
                failures.append(
                    f"SILENT-SKIP RISK: {name} quality check "
                    f"'{q.get('name', '?')}' has no `type` "
                    "(would be skipped at test time)"
                )
    return failures


def discover_all_fact_contracts() -> list[Path]:
    """Every committed fact contract, regardless of approval state.

    Used by ``--all`` during a rebuild window when nothing is approved yet but
    re-emitted contracts should still lint.
    """
    found: list[Path] = []
    for main_dir in sorted(CONTRACTS_DIR.iterdir()):
        if main_dir.is_dir() and not main_dir.name.startswith("_"):
            found.extend(sorted(main_dir.glob("*.odcs.yaml")))
    return found


def fast_checks(all_contracts: bool = False) -> int:
    failures: list[str] = []
    contracts: list[Path] = []

    # 1) fact coverage. Approval-driven by default; --all lints every
    # committed fact contract and skips the coverage assertion (mid-rebuild,
    # coverage of unapproved topics is expected to be partial).
    if all_contracts:
        contracts = discover_all_fact_contracts()
    else:
        for main, topic in approved_topics():
            p = contract_path(main, topic)
            if not p.exists():
                failures.append(
                    f"MISSING contract: {p.relative_to(REPO)} "
                    "(run scripts/generate_contracts.py)"
                )
            else:
                contracts.append(p)

    # 1b) dimension coverage -- the three expected dim contracts must exist
    # (run scripts/generate_dimension_contracts.py to (re)emit them).
    dim_contracts: list[Path] = []
    for dim_name, dim_path in DIMENSION_CONTRACTS.items():
        if not dim_path.exists():
            failures.append(
                f"MISSING dimension contract: {dim_path.relative_to(REPO)} "
                f"({dim_name}; run scripts/generate_dimension_contracts.py)"
            )
        else:
            dim_contracts.append(dim_path)
    # Surface any extra dim contracts we discover but don't expect (lint them too).
    for p in discover_dimension_contracts():
        if p not in dim_contracts and p.exists():
            dim_contracts.append(p)

    # 2) lint + 3) static type-guard (fact + dimension contracts)
    for p in contracts:
        failures.extend(lint_and_type_guard(p))
    for p in dim_contracts:
        failures.extend(lint_and_type_guard(p, label=f"_dimensions/{p.name}"))

    print(
        f"Fast checks: {len(contracts)} fact contracts + "
        f"{len(dim_contracts)} dimension contracts | "
        f"lint+type-guard {'PASS' if not failures else 'FAIL'}"
    )
    for f in failures:
        print(f"  - {f}")
    return 1 if failures else 0


def _test_contract(args: tuple[str, Path]) -> tuple[str, bool, str]:
    """Run ``datacontract test`` against the contract's S3 server.

    ``args`` is ``(label, path)``. The s3 server name is detected from the
    contract (``s3_gold`` for both fact and dim contracts today). Asserts the
    overall result is ``passed`` and that the quality-check count run equals
    the count declared (the CHECK-COUNT assertion).
    """
    label, p = args
    if not p.exists():
        return label, False, "missing contract"
    server = s3_server_name(p)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        rep = tf.name
    try:
        subprocess.run(
            [
                DC,
                "test",
                "--server",
                server,
                "--output-format",
                "json",
                "--output",
                rep,
                str(p),
            ],
            capture_output=True,
            text=True,
        )
        report = json.loads(Path(rep).read_text())
    except Exception as e:  # noqa: BLE001
        return label, False, f"test run/parse error: {e}"
    finally:
        Path(rep).unlink(missing_ok=True)

    overall = report.get("result")
    checks = report.get("checks", [])
    failed = [c["name"] for c in checks if c.get("result") not in ("passed", "info")]
    quality_ran = sum(1 for c in checks if c.get("category") == "quality")
    quality_expected = declared_quality_count(p)

    problems = []
    if overall != "passed":
        problems.append(f"overall={overall}")
    if failed:
        problems.append(f"{len(failed)} failed: {failed[:3]}")
    if quality_ran != quality_expected:
        problems.append(
            f"CHECK-COUNT MISMATCH: ran {quality_ran} quality checks, "
            f"expected {quality_expected} (silent skip?)"
        )
    ok = not problems
    detail = (
        f"{len(checks)} checks ({quality_ran} quality)" if ok else "; ".join(problems)
    )
    return label, ok, detail


def s3_checks(jobs: int) -> int:
    if not (
        os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("DATACONTRACT_S3_ACCESS_KEY_ID")
    ):
        print(
            "ERROR: --s3-test needs AWS credentials in the environment "
            "(AWS_ACCESS_KEY_ID/SECRET or DATACONTRACT_S3_*).",
            file=sys.stderr,
        )
        return 2
    # Fact contracts (labeled by topic) + dimension contracts (labeled
    # _dimensions/<name>), both tested against their s3 server with the same
    # CHECK-COUNT assertion.
    targets: list[tuple[str, Path]] = [
        ("/".join((main, topic)), contract_path(main, topic))
        for main, topic in approved_topics()
    ]
    for p in discover_dimension_contracts():
        targets.append((f"_dimensions/{p.stem.replace('.odcs', '')}", p))

    results = list(ThreadPoolExecutor(max_workers=jobs).map(_test_contract, targets))
    failures = [(t, d) for t, ok, d in results if not ok]
    for t, ok, d in sorted(results):
        print(f"  {'PASS' if ok else 'FAIL'}  {t:56s} {d}")
    print(
        f"\nS3 conformance: {len(results) - len(failures)}/{len(results)} "
        "contracts passed "
        f"({len(targets) - len(discover_dimension_contracts())} fact + "
        f"{len(discover_dimension_contracts())} dimension)"
    )
    for t, d in failures:
        print(f"  FAIL {t}: {d}")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--s3-test",
        action="store_true",
        help="run datacontract test against S3 (needs creds)",
    )
    ap.add_argument(
        "-j", "--jobs", type=int, default=5, help="parallelism for --s3-test"
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="lint every committed fact contract (not just approved topics)",
    )
    args = ap.parse_args()

    if DC is None:
        print(
            "ERROR: `datacontract` not on PATH. "
            "Install: uv tool install 'datacontract-cli[all]'",
            file=sys.stderr,
        )
        return 2
    if not STATUS_FILE.exists():
        print(f"ERROR: {STATUS_FILE} not found", file=sys.stderr)
        return 2

    rc = fast_checks(all_contracts=args.all)
    if args.s3_test:
        rc = s3_checks(args.jobs) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
