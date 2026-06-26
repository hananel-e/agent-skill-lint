#!/usr/bin/env python3
"""Collect mode slugs from .roomodes files and merge into slugs.json.

Usage (from repo root):
    python3 scripts/collect_slugs.py \\
        --input slugs.json \\
        --output slugs.json \\
        --roomodes-glob "**/.roomodes"

The script:
  1. Reads the existing slugs.json (--input) to get the current slug list.
  2. Walks the repo for all .roomodes files matching --roomodes-glob.
  3. Extracts customModes[].slug from each file.
  4. Merges new slugs with the existing set (union, sorted).
  5. Writes the result to --output.

Exit codes:
  0  success (file written or unchanged)
  1  error (parse failure, I/O error)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def collect_from_roomodes(glob_pattern: str, repo_root: Path) -> set[str]:
    """Walk repo_root for .roomodes files and extract all customModes slugs."""
    slugs: set[str] = set()
    for roomodes_path in repo_root.glob(glob_pattern):
        try:
            data = json.loads(roomodes_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  [warn] Could not parse {roomodes_path}: {exc}", file=sys.stderr)
            continue

        custom_modes = data.get("customModes", [])
        if not isinstance(custom_modes, list):
            continue
        for mode in custom_modes:
            slug = mode.get("slug")
            if isinstance(slug, str) and slug:
                slugs.add(slug)
                print(f"  found slug: {slug!r} (from {roomodes_path})")

    return slugs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Existing slugs.json path")
    parser.add_argument("--output", required=True, help="Output slugs.json path")
    parser.add_argument(
        "--roomodes-glob",
        default="**/.roomodes",
        help="Glob pattern for .roomodes files (relative to repo root)",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    input_path = Path(args.input)
    output_path = Path(args.output)

    # Load existing slugs
    existing_slugs: set[str] = set()
    if input_path.exists():
        try:
            data = json.loads(input_path.read_text(encoding="utf-8"))
            existing_slugs = set(data.get("slugs", []))
            print(f"Loaded {len(existing_slugs)} existing slugs from {input_path}")
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Error reading {input_path}: {exc}", file=sys.stderr)
            return 1
    else:
        print(f"No existing {input_path}, starting fresh.")

    # Collect from .roomodes
    print(f"\nScanning for .roomodes files (pattern: {args.roomodes_glob})…")
    discovered = collect_from_roomodes(args.roomodes_glob, repo_root)
    print(f"Discovered {len(discovered)} slug(s) from .roomodes files.")

    # Merge
    merged = sorted(existing_slugs | discovered)
    added = sorted(discovered - existing_slugs)

    if added:
        print(f"\nNew slugs to add: {added}")
    else:
        print("\nNo new slugs found.")

    # Write output
    payload = {
        "version": 1,
        "source": "collected",
        "slugs": merged,
    }
    try:
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {len(merged)} slugs → {output_path}")
    except OSError as exc:
        print(f"Error writing {output_path}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
