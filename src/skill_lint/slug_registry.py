"""Slug registry: fetch, cache, and serve known Roo mode slugs.

Priority chain (highest → lowest):
  1. User cache  ~/.cache/skill-lint/slugs.json  (written by `update-slugs`)
  2. Bundled     <package_root>/../../slugs.json  (shipped with the package)
  3. Hard-coded  FALLBACK_SLUGS                   (last resort, no I/O)
"""

from __future__ import annotations

import json
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────────────────

#: Remote URL that `update-slugs` fetches from.
REMOTE_URL = (
    "https://raw.githubusercontent.com/hananel-e/agent-skill-lint/main/slugs.json"
)

#: User-level cache location.
_CACHE_DIR = Path.home() / ".cache" / "skill-lint"
_CACHE_FILE = _CACHE_DIR / "slugs.json"

#: Bundled slugs.json shipped alongside the package (repo root).
_BUNDLED_FILE = Path(__file__).parent.parent.parent / "slugs.json"

#: Hard-coded fallback — never changes without a code release.
FALLBACK_SLUGS: frozenset[str] = frozenset(
    [
        "architect",
        "ask",
        "build",
        "code",
        "debug",
        "env",
        "merge-resolver",
        "orchestrator",
        "review",
        "ship",
        "spec",
        "task-break",
        "test",
        "test-dev-orchestrator",
        "analyst",
    ]
)


# ── public API ───────────────────────────────────────────────────────────────


def load_slugs() -> frozenset[str]:
    """Return the best available set of known mode slugs.

    Tries (in order): user cache → bundled file → hard-coded fallback.
    Never raises; always returns a non-empty frozenset.
    """
    for source, path in [("cache", _CACHE_FILE), ("bundled", _BUNDLED_FILE)]:
        slugs = _read_slugs_file(path, source)
        if slugs:
            return frozenset(slugs)

    logger.debug("slug_registry: using hard-coded fallback slugs")
    return FALLBACK_SLUGS


def fetch_and_cache(timeout: int = 10) -> tuple[bool, str]:
    """Fetch slugs from REMOTE_URL and write to the user cache.

    Returns:
        (success, message) — message is human-readable status text.
    """
    try:
        req = urllib.request.Request(
            REMOTE_URL,
            headers={"User-Agent": "agent-skill-lint/slug-updater"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        return False, f"Network error: {exc}"

    try:
        data = json.loads(raw)
        slugs: list[str] = data["slugs"]
        if not isinstance(slugs, list) or not all(isinstance(s, str) for s in slugs):
            return False, "Remote slugs.json has unexpected format"
    except (json.JSONDecodeError, KeyError) as exc:
        return False, f"Parse error: {exc}"

    # Write to cache
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": data.get("version", 1),
            "source": "remote",
            "slugs": sorted(slugs),
        }
        _CACHE_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return False, f"Could not write cache: {exc}"

    return True, f"Updated {len(slugs)} slugs → {_CACHE_FILE}"


def cache_path() -> Path:
    """Return the path to the user-level cache file (may not exist yet)."""
    return _CACHE_FILE


# ── helpers ──────────────────────────────────────────────────────────────────


def _read_slugs_file(path: Path, label: str) -> list[str]:
    """Read a slugs.json file; return empty list on any error."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        slugs = data.get("slugs", [])
        if isinstance(slugs, list) and slugs:
            logger.debug("slug_registry: loaded %d slugs from %s (%s)", len(slugs), path, label)
            return [str(s) for s in slugs]
    except Exception as exc:  # noqa: BLE001
        logger.warning("slug_registry: could not read %s (%s): %s", path, label, exc)
    return []
