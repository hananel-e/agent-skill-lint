"""YAML frontmatter extractor for skill.md files."""

from __future__ import annotations

from pathlib import Path

import frontmatter

from skill_lint.models import SkillFile


def _find_line(raw: str, key: str) -> int | None:
    """Return the 1-based line number of the first occurrence of `key:` in raw text."""
    for i, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(f"{key}:") or stripped == f"{key}:":
            return i
    return None


def parse_frontmatter(path: Path) -> SkillFile:
    """Parse a skill.md file and return a SkillFile with frontmatter populated."""
    raw = path.read_text(encoding="utf-8")
    skill = SkillFile(path=path, raw=raw)

    try:
        post = frontmatter.loads(raw)
    except Exception as exc:
        skill.parse_error = f"Failed to parse frontmatter: {exc}"
        skill.body = raw
        return skill

    metadata = post.metadata
    skill.body = post.content

    # Extract known fields
    skill.name = metadata.get("name") or None
    skill.description = metadata.get("description") or None

    mode_slugs_raw = metadata.get("modeSlugs")
    if isinstance(mode_slugs_raw, list):
        skill.mode_slugs = [str(s) for s in mode_slugs_raw]
    elif mode_slugs_raw is not None:
        skill.mode_slugs = [str(mode_slugs_raw)]

    # Store remaining frontmatter
    skill.extra_frontmatter = {
        k: v for k, v in metadata.items() if k not in ("name", "description", "modeSlugs")
    }

    # Find line numbers within the raw frontmatter block
    skill.name_line = _find_line(raw, "name")
    skill.description_line = _find_line(raw, "description")
    skill.mode_slugs_line = _find_line(raw, "modeSlugs")

    return skill
