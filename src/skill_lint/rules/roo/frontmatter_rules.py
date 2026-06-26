"""Frontmatter rules: ROO001–ROO008."""

from __future__ import annotations

from skill_lint.models import Severity, Violation
from skill_lint.rules.base import Rule, register

KNOWN_MODE_SLUGS = frozenset(
    [
        "code",
        "architect",
        "ask",
        "debug",
        "orchestrator",
        "task-break",
        "test",
        "review",
        "env",
        "spec",
        "build",
        "ship",
        "test-dev-orchestrator",
        "analyst",
        "merge-resolver",
    ]
)


@register
class ROO001(Rule):
    rule_id = "ROO001"
    severity = Severity.ERROR
    description = "`name` field missing from frontmatter"
    rationale = (
        "The `name` field is required for skill routing and identification. "
        "Without it, the skill cannot be referenced by other skills or the agent."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if skill.name is None:
            return [self._violation(skill, "frontmatter is missing required field: `name`", line=1)]
        return []


@register
class ROO002(Rule):
    rule_id = "ROO002"
    severity = Severity.ERROR
    description = "`description` field missing from frontmatter"
    rationale = (
        "The `description` field is the LLM routing signal. "
        "Without it, the agent cannot select this skill."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if skill.description is None:
            return [self._violation(skill, "frontmatter is missing required field: `description`", line=1)]
        return []


@register
class ROO003(Rule):
    rule_id = "ROO003"
    severity = Severity.ERROR
    description = "`modeSlugs` field missing from frontmatter"
    rationale = (
        "The `modeSlugs` field tells Roo which modes can load this skill. "
        "Without it, the skill will never be activated."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        # mode_slugs is an empty list both when missing and when explicitly empty
        # We distinguish by checking extra_frontmatter and the raw
        raw = skill.raw
        if "modeSlugs" not in raw:
            return [self._violation(skill, "frontmatter is missing required field: `modeSlugs`", line=1)]
        return []


@register
class ROO004(Rule):
    rule_id = "ROO004"
    severity = Severity.ERROR
    description = "`modeSlugs` is an empty list"
    rationale = (
        "An empty `modeSlugs` list means no mode can load this skill. "
        "Add at least one valid mode slug."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if "modeSlugs" in skill.raw and len(skill.mode_slugs) == 0:
            return [
                self._violation(
                    skill,
                    "`modeSlugs` is an empty list — skill will never be activated",
                    line=skill.mode_slugs_line,
                )
            ]
        return []


@register
class ROO005(Rule):
    rule_id = "ROO005"
    severity = Severity.WARNING
    description = "`modeSlugs` contains an unrecognised mode slug"
    rationale = (
        "Unrecognised mode slugs may indicate a typo or a mode that no longer exists. "
        "Check the list of known Roo mode slugs."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        cfg = kwargs.get("cfg", {})
        extra_slugs = frozenset(cfg.get("extra_mode_slugs", []))
        known = KNOWN_MODE_SLUGS | extra_slugs

        violations = []
        for slug in skill.mode_slugs:
            if slug not in known:
                violations.append(
                    self._violation(
                        skill,
                        f"`modeSlugs` contains unrecognised mode slug: `{slug}`",
                        line=skill.mode_slugs_line,
                    )
                )
        return violations


@register
class ROO006(Rule):
    rule_id = "ROO006"
    severity = Severity.WARNING
    description = "`name` value does not match the parent directory name"
    rationale = (
        "By convention, the skill `name` should match its parent directory name "
        "to keep the file system and frontmatter in sync."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if skill.name is None:
            return []
        parent_dir = skill.path.parent.name
        if skill.name != parent_dir:
            return [
                self._violation(
                    skill,
                    f"`name` is `{skill.name}` but parent directory is `{parent_dir}`",
                    line=skill.name_line,
                )
            ]
        return []


@register
class ROO007(Rule):
    rule_id = "ROO007"
    severity = Severity.ERROR
    description = "`description` is too short (< 50 characters)"
    rationale = (
        "A description shorter than 50 characters is unlikely to provide enough context "
        "for the LLM to reliably route to this skill."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if skill.description is None:
            return []
        cfg = kwargs.get("cfg", {})
        min_len = cfg.get("rules", {}).get("ROO007", {}).get("min_length", 50)
        desc_len = len(skill.description)
        if desc_len < min_len:
            return [
                self._violation(
                    skill,
                    f"`description` is {desc_len} chars (min {min_len})",
                    line=skill.description_line,
                )
            ]
        return []


@register
class ROO008(Rule):
    rule_id = "ROO008"
    severity = Severity.WARNING
    description = "`description` is too long (> 400 characters)"
    rationale = (
        "Very long descriptions may exceed context windows or confuse the routing LLM. "
        "Keep descriptions concise and focused."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if skill.description is None:
            return []
        cfg = kwargs.get("cfg", {})
        max_len = cfg.get("rules", {}).get("ROO008", {}).get("max_length", 400)
        desc_len = len(skill.description)
        if desc_len > max_len:
            return [
                self._violation(
                    skill,
                    f"`description` is {desc_len} chars (max {max_len})",
                    line=skill.description_line,
                )
            ]
        return []
