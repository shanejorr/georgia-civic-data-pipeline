"""Mark a topic as approved in topic-status.yaml.

Approval requires a fresh, **passing** ``_validation.json`` (written by the
generic validator at the end of every transform run) in addition to the
transform + gold + review artifacts. Approval captures:

- ``approved_gold_sha256`` — sha256 over the topic's gold parquet (drift
  baseline for ``scripts/check_approved_topics.py``), and
- a top-level ``dimensions:`` sha256 map (districts/schools/demographics) so a
  dimension rebuild after approval is a visible, detectable event.

Usage:
    uv run python scripts/approve_topic.py <main_topic> <sub_topic> <topic>
    uv run python scripts/approve_topic.py --list-pending
    uv run python scripts/approve_topic.py --approve-all-pending
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BRONZE_ROOT = REPO_ROOT / "data" / "bronze"
GOLD_ROOT = REPO_ROOT / "data" / "gold"
ETL_ROOT = REPO_ROOT / "src" / "etl"
STATUS_FILE = REPO_ROOT / "topic-status.yaml"

# Dimension parquet files captured in the approval-time hash baseline.
DIMENSION_PARQUETS: dict[str, Path] = {
    "districts": GOLD_ROOT / "education" / "_dimensions" / "districts.parquet",
    "schools": GOLD_ROOT / "education" / "_dimensions" / "schools.parquet",
    "demographics": GOLD_ROOT / "_dimensions" / "demographics.parquet",
    "counties": GOLD_ROOT / "_dimensions" / "counties.parquet",
}

HEADER = """\
# Topic approval tracker.
#
# Each entry records whether the user has reviewed and approved a topic's
# gold output. "Approved" means the user has personally inspected the gold
# parquet, reviews, and validation report and is satisfied with the result.
#
# To add new bronze topics to this file, run:
#   uv run python scripts/sync_topic_status.py
#
# To mark a topic approved, run:
#   /approve-topic <main_topic> <sub_topic> <topic>
"""


def load_status() -> dict:
    if not STATUS_FILE.exists():
        sys.exit(
            f"Error: {STATUS_FILE} not found. Run scripts/sync_topic_status.py first."
        )
    with STATUS_FILE.open() as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("topics", {})
    return data


def write_status(data: dict) -> None:
    sorted_topics = {k: data["topics"][k] for k in sorted(data["topics"])}
    data["topics"] = sorted_topics
    body = yaml.safe_dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        allow_unicode=True,
    )
    STATUS_FILE.write_text(HEADER + body)


def _hash_paths(paths: list[Path], base: Path) -> str:
    """sha256 over file bytes + base-relative paths (renames register as drift)."""
    hasher = hashlib.sha256()
    for path in paths:
        rel = path.relative_to(base).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                hasher.update(chunk)
        hasher.update(b"\0")
    return hasher.hexdigest()


def compute_gold_sha256(main_topic: str, topic: str) -> str:
    """Hash every .parquet under data/gold/{main_topic}/{topic}/, sorted by
    relative path.

    The relative path is fed into the hasher alongside file bytes so that a rename
    without content change still registers as drift. Returns a hex sha256 digest.
    """
    gold_dir = GOLD_ROOT / main_topic / topic
    return _hash_paths(sorted(gold_dir.rglob("*.parquet")), gold_dir)


def compute_dimension_hashes() -> dict[str, str]:
    """sha256 per dimension parquet (missing files are omitted)."""
    hashes: dict[str, str] = {}
    for name, path in DIMENSION_PARQUETS.items():
        if path.exists():
            hashes[name] = _hash_paths([path], path.parent)
    return hashes


def is_processed(
    main_topic: str, sub_topic: str, topic: str
) -> tuple[bool, bool, bool, bool]:
    """Return (has_transform, has_gold, has_review_claude, has_review_codex)."""
    etl_dir = ETL_ROOT / main_topic / sub_topic / topic
    gold_dir = GOLD_ROOT / main_topic / topic
    has_transform = (etl_dir / "transform.py").exists()
    has_gold = gold_dir.exists() and any(gold_dir.glob("year=*/"))
    has_review_claude = (etl_dir / "data-review-claude.md").exists()
    has_review_codex = (etl_dir / "data-review-codex.md").exists()
    return has_transform, has_gold, has_review_claude, has_review_codex


def validation_state(main_topic: str, topic: str) -> tuple[bool, str]:
    """Check the topic's _validation.json is present, passing, and fresh.

    Fresh = the validation report timestamp is not older than the transform
    manifest's generated_at (both are written by the same transform run, with
    validation last; a validation older than the manifest means the gold was
    regenerated without re-validating).
    """
    gold_dir = GOLD_ROOT / main_topic / topic
    val_path = gold_dir / "_validation.json"
    manifest_path = gold_dir / "_transform_manifest.json"
    if not val_path.exists():
        return False, "no _validation.json (re-run the transform)"
    try:
        val = json.loads(val_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"_validation.json unreadable: {exc}"
    if not val.get("passed"):
        return False, "_validation.json reports failures"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            if str(val.get("timestamp", "")) < str(manifest.get("generated_at", "")):
                return False, (
                    "_validation.json predates the transform manifest — "
                    "re-run the transform"
                )
        except (OSError, json.JSONDecodeError):
            pass
    return True, "validation passed"


def list_pending(data: dict) -> list[str]:
    """Print and return topics that are processed but not approved."""
    pending = []
    for key, entry in data["topics"].items():
        if entry.get("approved"):
            continue
        main_topic, sub_topic, topic = key.split("/")
        has_transform, has_gold, _, _ = is_processed(main_topic, sub_topic, topic)
        if has_transform and has_gold:
            pending.append(key)

    if not pending:
        print("No topics awaiting approval.")
        return pending

    print(f"Topics processed but awaiting approval ({len(pending)}):")
    for key in pending:
        print(f"  {key}")
    print()
    print("To approve one:  /approve-topic <main_topic> <sub_topic> <topic>")
    print(
        "To approve all:  uv run python scripts/approve_topic.py --approve-all-pending"
    )
    return pending


def approve(
    main_topic: str, sub_topic: str, topic: str, data: dict | None = None
) -> int:
    key = f"{main_topic}/{sub_topic}/{topic}"
    standalone = data is None
    if data is None:
        data = load_status()

    if key not in data["topics"]:
        print(f"Error: {key} not in topic-status.yaml.")
        print(
            "Hint: run 'uv run python scripts/sync_topic_status.py'"
            " if it's a new bronze topic."
        )
        return 1

    has_transform, has_gold, has_review_claude, has_review_codex = is_processed(
        main_topic, sub_topic, topic
    )

    if not has_transform:
        print(f"Error: cannot approve {key} — transform.py does not exist.")
        print("Run /full-pipeline first to process this topic.")
        return 1
    if not has_gold:
        print(f"Error: cannot approve {key} — no gold data found.")
        print("Run /full-pipeline first to process this topic.")
        return 1

    val_ok, val_detail = validation_state(main_topic, topic)
    if not val_ok:
        print(f"Error: cannot approve {key} — {val_detail}.")
        return 1

    if not has_review_claude:
        print(f"Warning: {key} has no data-review-claude.md.")
    if not has_review_codex:
        print(f"Warning: {key} has no data-review-codex.md.")

    entry = data["topics"][key]
    already = bool(entry.get("approved"))
    entry["approved"] = True
    entry["approved_at"] = dt.date.today().isoformat()
    entry["approved_gold_sha256"] = compute_gold_sha256(main_topic, topic)

    # Refresh the dimension baseline alongside every approval so the hashes
    # always describe the dimensions the just-approved facts were checked
    # against.
    data["dimensions"] = compute_dimension_hashes()

    if standalone:
        write_status(data)

    verb = "Re-approved" if already else "Approved"
    print(f"{verb} {key} on {entry['approved_at']} ({val_detail}).")
    return 0


def approve_all_pending() -> int:
    """Approve every processed-but-unapproved topic (per-topic gates enforced)."""
    data = load_status()
    pending = []
    for key, entry in data["topics"].items():
        if entry.get("approved"):
            continue
        main_topic, sub_topic, topic = key.split("/")
        has_transform, has_gold, _, _ = is_processed(main_topic, sub_topic, topic)
        if has_transform and has_gold:
            pending.append((main_topic, sub_topic, topic))

    if not pending:
        print("No topics awaiting approval.")
        return 0

    failures = 0
    for main_topic, sub_topic, topic in pending:
        if approve(main_topic, sub_topic, topic, data=data) != 0:
            failures += 1

    write_status(data)
    approved = len(pending) - failures
    print(f"\nApproved {approved}/{len(pending)} pending topic(s).")
    if failures:
        print(f"{failures} topic(s) failed their approval gates — see above.")
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mark a topic approved in topic-status.yaml."
    )
    parser.add_argument("main_topic", nargs="?", help="Main topic (e.g., education)")
    parser.add_argument("sub_topic", nargs="?", help="Sub topic (e.g., gosa)")
    parser.add_argument("topic", nargs="?", help="Topic (e.g., act_scores)")
    parser.add_argument(
        "--list-pending",
        action="store_true",
        help="List topics processed but not yet approved.",
    )
    parser.add_argument(
        "--approve-all-pending",
        action="store_true",
        help="Approve every processed-but-unapproved topic (gates still enforced).",
    )
    args = parser.parse_args()

    if args.list_pending:
        list_pending(load_status())
        return

    if args.approve_all_pending:
        sys.exit(approve_all_pending())

    if not (args.main_topic and args.sub_topic and args.topic):
        list_pending(load_status())
        print()
        print("Pass <main_topic> <sub_topic> <topic> to approve one.")
        sys.exit(0)

    sys.exit(approve(args.main_topic, args.sub_topic, args.topic))


if __name__ == "__main__":
    main()
