"""Cross-skill consistency rules: ROO030–ROO036."""

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


@register
class ROO034(Rule):
    rule_id = "ROO034"
    severity = Severity.WARNING
    description = "Two skills have descriptions with high token overlap — ambiguous routing"
    rationale = (
        "When two or more skills have very similar descriptions, the LLM router may "
        "select the wrong skill. Rewrite descriptions to be more distinct, or merge "
        "the skills if they truly cover the same use-case."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        all_skills = kwargs.get("all_skills", [])
        cfg = kwargs.get("cfg", {})
        if not all_skills or len(all_skills) < 2:
            return []

        if skill.description is None:
            return []

        threshold = cfg.get("rules", {}).get("ROO034", {}).get("overlap_threshold", 0.60)

        from difflib import SequenceMatcher

        violations = []
        for other in all_skills:
            if other.path == skill.path or other.description is None:
                continue
            ratio = SequenceMatcher(None, skill.description, other.description).ratio()
            if ratio >= threshold:
                violations.append(
                    self._violation(
                        skill,
                        f"description overlaps {ratio:.0%} with `{other.name or other.path}` "
                        f"(threshold {threshold:.0%}) — routing may be ambiguous",
                        line=skill.description_line,
                    )
                )
        return violations


@register
class ROO035(Rule):
    rule_id = "ROO035"
    severity = Severity.WARNING
    description = "Skill's `modeSlugs` references a mode not defined in any `.roomodes` file"
    rationale = (
        "If a skill claims a mode slug that is not defined in any `.roomodes` file in the "
        "repository, the skill will never be activated by the framework. Either add the mode "
        "to `.roomodes` or remove the slug from the skill."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        repo_root: Path | None = kwargs.get("repo_root")
        if repo_root is None:
            return []

        from skill_lint.sync import load_roomodes
        roomodes_slugs = load_roomodes(repo_root)
        if not roomodes_slugs:
            # No .roomodes files found — skip (repo may not use Roo framework)
            return []

        violations = []
        for slug in skill.mode_slugs:
            if slug not in roomodes_slugs:
                violations.append(
                    self._violation(
                        skill,
                        f"mode slug `{slug}` is not defined in any `.roomodes` file",
                        line=skill.mode_slugs_line,
                    )
                )
        return violations


@register
class ROO036(Rule):
    rule_id = "ROO036"
    severity = Severity.WARNING
    description = "A mode defined in `.roomodes` has no skill covering it"
    rationale = (
        "Every custom mode in `.roomodes` should have at least one skill that covers it "
        "(i.e. lists the slug in `modeSlugs`). Modes without skills have no specialised "
        "instructions and will fall back to default behaviour."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        # This is a cross-skill rule: only fire on the first skill to avoid duplicates.
        all_skills = kwargs.get("all_skills", [])
        if not all_skills or skill.path != all_skills[0].path:
            return []

        repo_root: Path | None = kwargs.get("repo_root")
        if repo_root is None:
            return []

        from skill_lint.sync import load_roomodes, sync_report
        roomodes_slugs = load_roomodes(repo_root)
        if not roomodes_slugs:
            return []

        report = sync_report(all_skills, roomodes_slugs)
        violations = []
        for slug in report.undocumented_modes:
            source = roomodes_slugs.get(slug)
            source_hint = f" (defined in {source})" if source else ""
            violations.append(
                self._violation(
                    skill,
                    f"mode `{slug}`{source_hint} has no skill covering it",
                    line=None,
                )
            )
        return violations
