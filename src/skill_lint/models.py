"""Core data models for skill-lint."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Violation:
    """A single lint violation found in a skill file."""

    file: str
    rule: str
    severity: Severity
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
        }


@dataclass
class SkillFile:
    """Parsed representation of a skill.md file."""

    path: Path
    raw: str

    # Frontmatter fields
    name: str | None = None
    description: str | None = None
    mode_slugs: list[str] = field(default_factory=list)
    extra_frontmatter: dict[str, Any] = field(default_factory=dict)

    # Frontmatter line numbers (1-based)
    name_line: int | None = None
    description_line: int | None = None
    mode_slugs_line: int | None = None

    # Body
    body: str = ""

    # Parsed body elements
    h1_title: str | None = None
    h1_line: int | None = None
    numbered_sections: list[str] = field(default_factory=list)
    links: list[tuple[str, int]] = field(default_factory=list)  # (target, line)
    body_mode_slug_refs: list[str] = field(default_factory=list)
    skill_name_refs: list[str] = field(default_factory=list)

    # Parse error
    parse_error: str | None = None


@dataclass
class ScanResult:
    """Result of scanning one or more skill files."""

    files_scanned: int = 0
    files_clean: int = 0
    violations: list[Violation] = field(default_factory=list)
    # Populated by runner so downstream consumers (scorer, simulator) can
    # iterate all parsed skills without re-scanning.
    skill_files: list["SkillFile"] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.ERROR)

    @property
    def warnings(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.WARNING)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "files_scanned": self.files_scanned,
                "files_clean": self.files_clean,
                "errors": self.errors,
                "warnings": self.warnings,
            },
            "violations": [v.to_dict() for v in self.violations],
        }
