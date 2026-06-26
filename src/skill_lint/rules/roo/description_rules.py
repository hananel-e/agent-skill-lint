"""Description quality rules: ROO010–ROO014."""

from __future__ import annotations

import difflib
import re

from skill_lint.models import Severity, Violation
from skill_lint.rules.base import Rule, register

_TRIGGER_KEYWORDS = re.compile(
    r"\b(when|use when|invoked when|spawned|triggered)\b", re.IGNORECASE
)

_ACTION_VERB_RE = re.compile(
    r"^(Use|Create|Build|Generate|Analyse|Analyze|Run|Execute|Plan|Design|"
    r"Review|Debug|Test|Implement|Write|Scan|Check|Validate|Extract|Parse|"
    r"Resolve|Detect|Fix|Refactor|Deploy|Configure|Set up|Initialize|"
    r"Coordinate|Orchestrate|Break|Deliver|Conduct|Produce|Apply|Load|"
    r"Fetch|Search|Find|List|Show|Report|Explain|Document|Summarize|"
    r"Convert|Transform|Format|Lint|Score|Audit|Monitor|Track|Manage)\b",
    re.IGNORECASE,
)

_DEFAULT_VAGUE_WORDS = frozenset(
    ["handles", "manages", "does", "performs", "processes"]
)


def _tokenize(text: str) -> list[str]:
    """Simple whitespace+punctuation tokenizer for overlap calculation."""
    return re.findall(r"\b\w+\b", text.lower())


@register
class ROO010(Rule):
    rule_id = "ROO010"
    severity = Severity.WARNING
    description = "Description missing a trigger condition keyword"
    rationale = (
        "Good skill descriptions tell the agent *when* to use the skill. "
        "Include a trigger keyword such as `when`, `use when`, `invoked when`, "
        "`spawned`, or `triggered`."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if not skill.description:
            return []
        if not _TRIGGER_KEYWORDS.search(skill.description):
            return [
                self._violation(
                    skill,
                    "description missing a trigger condition keyword "
                    "(`when`, `use when`, `invoked when`, `spawned`, `triggered`)",
                    line=skill.description_line,
                )
            ]
        return []


@register
class ROO011(Rule):
    rule_id = "ROO011"
    severity = Severity.WARNING
    description = "Description does not start with an action verb or `Use`"
    rationale = (
        "Descriptions should start with an imperative action verb (e.g. `Use`, `Create`, `Run`) "
        "so the agent understands the skill's purpose immediately."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if not skill.description:
            return []
        if not _ACTION_VERB_RE.match(skill.description.strip()):
            first_word = skill.description.strip().split()[0] if skill.description.strip() else ""
            return [
                self._violation(
                    skill,
                    f"description starts with `{first_word}` — expected an action verb or `Use`",
                    line=skill.description_line,
                )
            ]
        return []


@register
class ROO012(Rule):
    rule_id = "ROO012"
    severity = Severity.WARNING
    description = "Description contains vague words"
    rationale = (
        "Vague words like `handles`, `manages`, `does`, `performs`, `processes` "
        "do not help the agent understand what the skill actually does. "
        "Replace them with specific action verbs."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if not skill.description:
            return []
        cfg = kwargs.get("cfg", {})
        extra_vague = set(cfg.get("vague_words", []))
        vague_words = _DEFAULT_VAGUE_WORDS | extra_vague

        violations = []
        desc_lower = skill.description.lower()
        for word in sorted(vague_words):
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            if pattern.search(desc_lower):
                violations.append(
                    self._violation(
                        skill,
                        f'description uses vague word: "{word}"',
                        line=skill.description_line,
                    )
                )
        return violations


@register
class ROO013(Rule):
    rule_id = "ROO013"
    severity = Severity.WARNING
    description = "Description has >75% token overlap with another skill in the same scan"
    rationale = (
        "High description overlap between skills causes ambiguous routing — "
        "the agent may select the wrong skill. Make each description unique."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if not skill.description:
            return []
        all_skills = kwargs.get("all_skills", [])
        cfg = kwargs.get("cfg", {})
        threshold = cfg.get("rules", {}).get("ROO013", {}).get("similarity_threshold", 0.75)

        my_tokens = _tokenize(skill.description)
        violations = []

        for other in all_skills:
            if other.path == skill.path or not other.description:
                continue
            other_tokens = _tokenize(other.description)
            ratio = difflib.SequenceMatcher(None, my_tokens, other_tokens).ratio()
            if ratio >= threshold:
                violations.append(
                    self._violation(
                        skill,
                        f"description has {ratio:.0%} token overlap with `{other.path}` "
                        f"(threshold {threshold:.0%})",
                        line=skill.description_line,
                    )
                )
        return violations


@register
class ROO014(Rule):
    rule_id = "ROO014"
    severity = Severity.WARNING
    description = "Skill `name` mentioned in description body is inconsistent with frontmatter `name`"
    rationale = (
        "If the description mentions a skill name that differs from the frontmatter `name`, "
        "it may confuse the agent or indicate a copy-paste error."
    )

    def check(self, skill, **kwargs) -> list[Violation]:
        if not skill.description or not skill.name:
            return []

        # Look for patterns like "the <word> skill" or "`<word>`" in description
        name_pattern = re.compile(
            r"\bthe\s+([a-z0-9_-]+)\s+skill\b|`([a-z0-9_-]+)`", re.IGNORECASE
        )
        violations = []
        for m in name_pattern.finditer(skill.description):
            mentioned = (m.group(1) or m.group(2) or "").strip()
            if mentioned and mentioned.lower() != skill.name.lower():
                violations.append(
                    self._violation(
                        skill,
                        f"description mentions skill name `{mentioned}` "
                        f"but frontmatter `name` is `{skill.name}`",
                        line=skill.description_line,
                    )
                )
        return violations
