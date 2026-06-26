"""Framework sync checker: compare .roomodes definitions against skill files.

Detects two classes of drift:
  - Orphaned skill slugs: a skill's modeSlugs references a mode that is not
    defined in any .roomodes file found in the repo.
  - Undocumented modes: a mode defined in .roomodes has no skill that covers it
    (i.e. no skill lists that slug in its modeSlugs).

Public API
----------
  load_roomodes(repo_root)  → dict[slug, source_path]
  sync_report(skills, roomodes_slugs) → SyncReport
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from skill_lint.models import SkillFile


# ── data classes ─────────────────────────────────────────────────────────────


@dataclass
class SyncReport:
    """Result of comparing .roomodes definitions against scanned skills."""

    # Slugs present in .roomodes but not covered by any skill
    undocumented_modes: list[str] = field(default_factory=list)

    # {slug: [skill_paths]} — skills that reference a slug absent from .roomodes
    orphaned_skill_slugs: dict[str, list[Path]] = field(default_factory=dict)

    # All slugs found in .roomodes files
    roomodes_slugs: dict[str, Path] = field(default_factory=dict)

    # All slugs covered by at least one skill
    covered_slugs: set[str] = field(default_factory=set)

    @property
    def is_clean(self) -> bool:
        return not self.undocumented_modes and not self.orphaned_skill_slugs

    def to_dict(self) -> dict:
        return {
            "is_clean": self.is_clean,
            "undocumented_modes": self.undocumented_modes,
            "orphaned_skill_slugs": {
                slug: [str(p) for p in paths]
                for slug, paths in self.orphaned_skill_slugs.items()
            },
            "roomodes_slugs": {
                slug: str(path) for slug, path in self.roomodes_slugs.items()
            },
            "covered_slugs": sorted(self.covered_slugs),
        }


# ── public API ────────────────────────────────────────────────────────────────


def load_roomodes(repo_root: Path) -> dict[str, Path]:
    """Walk repo_root for .roomodes files and return {slug: source_path}.

    If a slug appears in multiple .roomodes files, the last one wins
    (alphabetical order by path).
    """
    slugs: dict[str, Path] = {}
    for roomodes_path in sorted(repo_root.rglob(".roomodes")):
        try:
            data = json.loads(roomodes_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for mode in data.get("customModes", []):
            slug = mode.get("slug")
            if isinstance(slug, str) and slug:
                slugs[slug] = roomodes_path
    return slugs


def sync_report(
    skills: list[SkillFile],
    roomodes_slugs: dict[str, Path],
) -> SyncReport:
    """Build a SyncReport comparing skills against roomodes_slugs."""
    # Which slugs are covered by at least one skill?
    covered: set[str] = set()
    for skill in skills:
        covered.update(skill.mode_slugs)

    # Undocumented: in .roomodes but no skill covers it
    undocumented = sorted(
        slug for slug in roomodes_slugs if slug not in covered
    )

    # Orphaned: skill references a slug not in .roomodes
    orphaned: dict[str, list[Path]] = {}
    if roomodes_slugs:  # only meaningful when .roomodes files exist
        for skill in skills:
            for slug in skill.mode_slugs:
                if slug not in roomodes_slugs:
                    orphaned.setdefault(slug, []).append(skill.path)

    return SyncReport(
        undocumented_modes=undocumented,
        orphaned_skill_slugs=orphaned,
        roomodes_slugs=roomodes_slugs,
        covered_slugs=covered,
    )
