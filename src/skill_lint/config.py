"""Configuration loader for .skill-lint.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


_DEFAULT_CONFIG: dict[str, Any] = {
    "rules": {},
    "ignore": [],
    "vague_words": [],
    "extra_mode_slugs": [],
}


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load and return the merged configuration dictionary.

    Searches for `.skill-lint.yaml` in the current directory if no path given.
    Returns defaults if no config file is found.
    """
    cfg = dict(_DEFAULT_CONFIG)

    if config_path is None:
        candidates = [
            Path(".skill-lint.yaml"),
            Path(".skill-lint.yml"),
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = candidate
                break

    if config_path is None or not config_path.exists():
        return cfg

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        # Return defaults on parse error — don't crash the linter
        return cfg

    # Merge rules overrides
    if "rules" in raw and isinstance(raw["rules"], dict):
        cfg["rules"] = raw["rules"]

    # Build ignore_rules set from the ignore list
    ignore_list = raw.get("ignore", [])
    ignore_rules: list[str] = []
    ignore_paths: list[str] = []
    for item in ignore_list:
        item = str(item)
        if item.startswith("ROO") or item.startswith("roo"):
            ignore_rules.append(item.upper())
        else:
            ignore_paths.append(item)

    cfg["ignore_rules"] = ignore_rules
    cfg["ignore_paths"] = ignore_paths

    # Vague words extension
    if "vague_words" in raw and isinstance(raw["vague_words"], list):
        cfg["vague_words"] = [str(w) for w in raw["vague_words"]]

    # Extra mode slugs
    if "extra_mode_slugs" in raw and isinstance(raw["extra_mode_slugs"], list):
        cfg["extra_mode_slugs"] = [str(s) for s in raw["extra_mode_slugs"]]

    return cfg
