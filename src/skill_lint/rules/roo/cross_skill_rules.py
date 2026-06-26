"""Cross-skill consistency rules: ROO030–ROO032."""

from __future__ import annotations

import re
from pathlib import Path

from skill_lint.models import Severity, Violation
from skill_lint.rules.base import Rule, register

_HANDOFF_PATH_RE = re.compile(r"\.idex/handoff/[^/\s]+/")


@register
class ROO030(Rule):
    rule_id = "ROO030"
    severity = Severity.WARNING
    description = "Body references a skill name that has no corresponding `skill.md` in the scanned tree"
    rationale = (
        "If a skill references another skill by name but no matching `skill.md` exists, "
        "the handoff will fail at runtime."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        all_skills = kwargs.get("all_skills", [])
        if not all_skills:
            return []

        # Build set of known skill names
        known_names = {s.name for s in all_skills if s.name}

        violations = []
        for ref in skill.skill_name_refs:
            # Only flag refs that look like skill names (contain hyphens or match known patterns)
            # and are NOT the skill's own name
            if ref == skill.name:
                continue
            # Heuristic: if it looks like a skill name (kebab-case or matches known name pattern)
            if re.match(r"^[a-z][a-z0-9-]+$", ref) and ref not in known_names:
                violations.append(
                    self._violation(
                        skill,
                        f"body references skill `{ref}` but no matching `skill.md` found in scanned tree",
                        line=None,
                    )
                )
        return violations


@register
class ROO031(Rule):
    rule_id = "ROO031"
    severity = Severity.WARNING
    description = "Handoff file path pattern uses a non-standard field name"
    rationale = (
        "Handoff paths should follow the standard pattern `.idex/handoff/<TICKET_ID>/`. "
        "Non-standard paths may break handoff workflows."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        body = skill.body
        violations = []

        # Find any path that looks like a handoff path but doesn't match the standard
        # Look for patterns like handoff/ or .idex/ paths
        handoff_candidates = re.finditer(
            r"(?:handoff|\.idex)[/\\][^\s`\"')\]]+", body
        )
        for m in handoff_candidates:
            path_str = m.group(0)
            # Check if it matches the standard pattern
            if not _HANDOFF_PATH_RE.search(path_str) and "handoff" in path_str.lower():
                violations.append(
                    self._violation(
                        skill,
                        f"handoff path `{path_str}` does not follow standard pattern "
                        "`.idex/handoff/<TICKET_ID>/`",
                        line=None,
                    )
                )
        return violations


@register
class ROO032(Rule):
    rule_id = "ROO032"
    severity = Severity.ERROR
    description = "Two or more skills claim the same `modeSlugs` entry — ambiguous routing"
    rationale = (
        "When multiple skills claim the same mode slug, the agent cannot determine "
        "which skill to load. Each mode slug should be claimed by at most one skill."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        all_skills = kwargs.get("all_skills", [])
        if not all_skills:
            return []

        violations = []
        for slug in skill.mode_slugs:
            claimants = [
                s for s in all_skills
                if s.path != skill.path and slug in s.mode_slugs
            ]
            if claimants:
                claimant_paths = ", ".join(str(s.path) for s in claimants)
                violations.append(
                    self._violation(
                        skill,
                        f"mode slug `{slug}` is also claimed by: {claimant_paths}",
                        line=skill.mode_slugs_line,
                    )
                )
        return violations
