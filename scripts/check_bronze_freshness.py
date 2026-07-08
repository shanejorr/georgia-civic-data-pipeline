"""Verify a topic's bronze files match its bronze-data-structure.md analysis.

The structure doc is the analysis every downstream step trusts; it embeds a
SHA-256 checksum table generated when the bronze was analyzed. This gate
fails when:

- a checksummed file CHANGED (content differs from what was analyzed),
- a checksummed file is MISSING from the bronze directory,
- a data file is PRESENT in the bronze directory but UNANALYZED (absent from
  the checksum table) — new files must go through /bronze-data-structure
  before any transform ingests them,
- the structure doc has NO checksum table at all.

Usage (from the repo root):

    uv run python scripts/check_bronze_freshness.py education gosa act_scores

Exit codes: 0 fresh | 1 stale/unanalyzed | 2 setup error (doc missing).
The /transform-topic and /full-pipeline skills run this as their preflight
gate; ``--allow-stale`` downgrades CHANGED/MISSING to warnings (UNANALYZED
always fails — there is no legitimate reason to transform an unanalyzed file).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Bronze data file extensions (everything else in the dir is documentation).
DATA_EXTENSIONS = {
    ".csv",
    ".xls",
    ".xlsx",
    ".tsv",
    ".txt",
    ".json",
    ".zip",
    ".html",
    ".parquet",
    ".dta",
    ".pdf",
}

# Checksum table rows: | filename.ext | 64-hex-sha256 |
# The filename group must tolerate spaces — georgiainsights bronze files are
# named like "2012 Content Mastery By Subgroups.xls". The v1 inline gate used
# \S+ here, which silently parsed zero rows for those topics and never
# actually protected them.
CHECKSUM_ROW_RE = re.compile(r"\|\s*([^|]+?\.\w{3,4})\s*\|\s*([a-f0-9]{64})\s*\|")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("main_topic")
    ap.add_argument("sub_topic")
    ap.add_argument("topic")
    ap.add_argument(
        "--allow-stale",
        action="store_true",
        help="downgrade CHANGED/MISSING to warnings (UNANALYZED still fails)",
    )
    args = ap.parse_args()

    bronze_dir = (
        REPO / "data" / "bronze" / args.main_topic / args.sub_topic / args.topic
    )
    structure_doc = bronze_dir / "bronze-data-structure.md"

    if not bronze_dir.exists():
        print(f"ERROR: bronze directory not found: {bronze_dir}", file=sys.stderr)
        return 2
    if not structure_doc.exists():
        print(
            f"ERROR: {structure_doc} not found — run /bronze-data-structure "
            f"{args.main_topic} {args.sub_topic} {args.topic} first",
            file=sys.stderr,
        )
        return 2

    checksums = dict(CHECKSUM_ROW_RE.findall(structure_doc.read_text()))
    if not checksums:
        print(
            "FAIL: bronze-data-structure.md has no checksum table — regenerate "
            "it with /bronze-data-structure (checksums are required)",
            file=sys.stderr,
        )
        return 1

    changed: list[str] = []
    missing: list[str] = []
    for filename, expected in sorted(checksums.items()):
        filepath = bronze_dir / filename
        if not filepath.exists():
            missing.append(filename)
            continue
        actual = hashlib.sha256(filepath.read_bytes()).hexdigest()
        if actual != expected:
            changed.append(filename)

    # Files on disk that the structure doc never analyzed. list_bronze_files()
    # globs the directory, so a transform WOULD ingest these — block that.
    on_disk = {
        p.name
        for p in bronze_dir.iterdir()
        if p.is_file() and p.suffix.lower() in DATA_EXTENSIONS
    }
    unanalyzed = sorted(on_disk - set(checksums))

    problems = False
    if changed or missing:
        level = "WARN" if args.allow_stale else "FAIL"
        print(f"{level}: bronze files differ from bronze-data-structure.md:")
        for f in changed:
            print(f"  CHANGED: {f}")
        for f in missing:
            print(f"  MISSING: {f}")
        if not args.allow_stale:
            problems = True
        else:
            print("WARNING: proceeding despite stale bronze per --allow-stale")
    if unanalyzed:
        print("FAIL: bronze files present but absent from the checksum table:")
        for f in unanalyzed:
            print(f"  UNANALYZED: {f}")
        print(
            "Re-run /bronze-data-structure so every file is analyzed before "
            "transforming."
        )
        problems = True

    if problems:
        return 1
    print(
        f"PASS: all {len(checksums)} bronze file checksums match; no unanalyzed files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
