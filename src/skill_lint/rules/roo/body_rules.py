"""Body structure rules: ROO020–ROO025."""

from __future__ import annotations

import re
from pathlib import Path

from skill_lint.models import Severity, Violation
from skill_lint.rules.base import Rule, register
from skill_lint.rules.roo.frontmatter_rules import KNOWN_MODE_SLUGS


def _load_roomodes_slugs(repo_root: Path) -> frozenset[str]:
    """Parse .roomodes file and return the set of defined mode slugs."""
    roomodes_path = repo_root / ".roomodes"
    if not roomodes_path.exists():
        return frozenset()
    try:
        import json
        data = json.loads(roomodes_path.read_text(encoding="utf-8"))
        modes = data.get("customModes", [])
        return frozenset(m.get("slug", "") for m in modes if m.get("slug"))
    except Exception:
        return frozenset()


@register
class ROO020(Rule):
    rule_id = "ROO020"
    severity = Severity.ERROR
    description = "No H1 heading (`# Title`) found after frontmatter"
    rationale = (
        "Every skill file must have an H1 heading immediately after the frontmatter. "
        "It serves as the canonical title of the skill."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if skill.h1_title is None:
            return [
                self._violation(
                    skill,
                    "no H1 heading (`# Title`) found after frontmatter",
                    line=None,
                )
            ]
        return []


@register
class ROO021(Rule):
    rule_id = "ROO021"
    severity = Severity.WARNING
    description = "H1 heading text does not match frontmatter `name`"
    rationale = (
        "The H1 heading should match the frontmatter `name` field for consistency. "
        "Mismatches may indicate a copy-paste error."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if skill.h1_title is None or skill.name is None:
            return []
        if skill.h1_title.strip().lower() != skill.name.strip().lower():
            return [
                self._violation(
                    skill,
                    f"H1 heading `{skill.h1_title}` does not match frontmatter `name` `{skill.name}`",
                    line=skill.h1_line,
                )
            ]
        return []


@register
class ROO022(Rule):
    rule_id = "ROO022"
    severity = Severity.WARNING
    description = "Body has no numbered sections (`## 1.`, `## 2.`, …) — likely a stub"
    rationale = (
        "Well-structured skills use numbered sections to organise their content. "
        "A skill without numbered sections is likely a stub or incomplete."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if not skill.numbered_sections:
            return [
                self._violation(
                    skill,
                    "body has no numbered sections (`## 1.`, `## 2.`, …) — likely a stub",
                    line=None,
                )
            ]
        return []


@register
class ROO023(Rule):
    rule_id = "ROO023"
    severity = Severity.ERROR
    description = "Markdown link target does not exist relative to repo root"
    rationale = (
        "Broken links in skill files cause runtime errors when the agent tries to follow them. "
        "Ensure all relative links point to existing files."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        repo_root: Path = kwargs.get("repo_root", skill.path.parent)
        violations = []
        for href, line_no in skill.links:
            # Strip fragment
            target = href.split("#")[0]
            if not target:
                continue
            resolved = (repo_root / target).resolve()
            if not resolved.exists():
                violations.append(
                    self._violation(
                        skill,
                        f"broken link: {href}",
                        line=line_no,
                    )
                )
        return violations


@register
class ROO024(Rule):
    rule_id = "ROO024"
    severity = Severity.WARNING
    description = "Body references a mode slug not present in `.roomodes`"
    rationale = (
        "If the skill body references a mode slug that is not defined in `.roomodes`, "
        "the reference may be stale or incorrect."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        repo_root: Path = kwargs.get("repo_root", skill.path.parent)
        defined_slugs = _load_roomodes_slugs(repo_root)
        if not defined_slugs:
            # No .roomodes file — skip this rule
            return []

        cfg = kwargs.get("cfg", {})
        extra_slugs = frozenset(cfg.get("extra_mode_slugs", []))
        # Full known set: built-in + config extras + .roomodes defined slugs
        all_known = KNOWN_MODE_SLUGS | extra_slugs | defined_slugs

        # body_mode_slug_refs now contains ALL word tokens from the body.
        # Intersect with all_known to find only slug-like tokens, then check
        # whether those slugs are in the .roomodes-defined set.
        violations = []
        for token in skill.body_mode_slug_refs:
            if token in all_known and token not in defined_slugs:
                violations.append(
                    self._violation(
                        skill,
                        f"body references mode slug `{token}` not found in `.roomodes`",
                        line=None,
                    )
                )
        return violations


@register
class ROO025(Rule):
    rule_id = "ROO025"
    severity = Severity.WARNING
    description = "Body after frontmatter is < 100 characters — stub skill"
    rationale = (
        "A skill body shorter than 100 characters is almost certainly a stub. "
        "Add meaningful content before shipping."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        body_len = len(skill.body.strip())
        if body_len < 100:
            return [
                self._violation(
                    skill,
                    f"body is only {body_len} characters — stub skill (min 100)",
                    line=None,
                )
            ]
        return []
