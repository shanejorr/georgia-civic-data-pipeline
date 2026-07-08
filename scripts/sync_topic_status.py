"""Sync topic-status.yaml with topics discovered under data/bronze/.

Idempotent: adds missing topics with `approved: false`, never removes or
overwrites existing entries. Run this whenever new bronze data lands.

Usage:
    uv run python scripts/sync_topic_status.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BRONZE_ROOT = REPO_ROOT / "data" / "bronze"
STATUS_FILE = REPO_ROOT / "topic-status.yaml"

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


def discover_bronze_topics() -> list[str]:
    """Walk data/bronze/{main}/{sub}/{topic}/ and return sorted topic keys."""
    if not BRONZE_ROOT.exists():
        raise SystemExit(f"Error: {BRONZE_ROOT} not found. Run from project root.")

    keys: list[str] = []
    for main_topic in sorted(BRONZE_ROOT.iterdir()):
        if not _is_topic_dir(main_topic):
            continue
        for sub_topic in sorted(main_topic.iterdir()):
            if not _is_topic_dir(sub_topic):
                continue
            for topic in sorted(sub_topic.iterdir()):
                if not _is_topic_dir(topic):
                    continue
                keys.append(f"{main_topic.name}/{sub_topic.name}/{topic.name}")
    return keys


def _is_topic_dir(path: Path) -> bool:
    return path.is_dir() and not path.name.startswith((".", "_"))


def load_existing() -> dict:
    if not STATUS_FILE.exists():
        return {"topics": {}}
    with STATUS_FILE.open() as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("topics", {})
    return data


def write_status(data: dict) -> None:
    # Sort topic keys alphabetically for deterministic output.
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


def main() -> None:
    bronze_keys = discover_bronze_topics()
    data = load_existing()

    existing_keys = set(data["topics"].keys())
    new_keys = [k for k in bronze_keys if k not in existing_keys]
    stale_keys = [k for k in existing_keys if k not in set(bronze_keys)]

    for key in new_keys:
        data["topics"][key] = {"approved": False}

    write_status(data)

    print(f"Bronze topics discovered: {len(bronze_keys)}")
    print(f"Already tracked:          {len(existing_keys)}")
    print(f"Newly added:              {len(new_keys)}")
    if new_keys:
        for k in new_keys:
            print(f"  + {k}")
    if stale_keys:
        print()
        print(
            f"Warning: {len(stale_keys)} tracked topics not found in bronze"
            " (kept in file):"
        )
        for k in stale_keys:
            print(f"  ? {k}")


if __name__ == "__main__":
    main()
