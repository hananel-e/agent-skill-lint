"""Rule ABC and global rule registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from skill_lint.models import Severity, Violation

if TYPE_CHECKING:
    from skill_lint.models import SkillFile

# Global registry: rule_id -> Rule instance
RULE_REGISTRY: dict[str, "Rule"] = {}


def register(cls: type["Rule"]) -> type["Rule"]:
    """Class decorator that registers a Rule subclass in RULE_REGISTRY."""
    instance = cls()
    RULE_REGISTRY[instance.rule_id] = instance
    return cls


class Rule(ABC):
    """Abstract base class for all lint rules."""

    rule_id: str
    severity: Severity
    description: str
    rationale: str = ""

    @abstractmethod
    def check(self, skill: "SkillFile", **kwargs) -> list[Violation]:
        """Run the rule against a parsed SkillFile.

        kwargs may include:
          - all_skills: list[SkillFile]  (for cross-skill rules)
          - cfg: dict                    (loaded config)
          - repo_root: Path              (for link resolution)
        """
        ...

    def _violation(self, skill: "SkillFile", message: str, line: int | None = None) -> Violation:
        return Violation(
            file=str(skill.path),
            rule=self.rule_id,
            severity=self.severity,
            message=message,
            line=line,
        )
