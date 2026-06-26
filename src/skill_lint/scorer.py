"""Quality scorer for skill definitions.

Converts lint violations into a numeric score (0-100) and letter grade (A-F).

Scoring model
-------------
- Base score: 100
- Each ERROR violation:   -15 points
- Each WARNING violation:  -5 points
- Score is clamped to [0, 100]

Grade thresholds
----------------
  A  90 – 100
  B  80 –  89
  C  70 –  79
  D  60 –  69
  F   0 –  59
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from skill_lint.models import Severity, ScanResult, Violation

# ── tunables ─────────────────────────────────────────────────────────────────

ERROR_PENALTY = 15
WARNING_PENALTY = 5

GRADE_THRESHOLDS: list[tuple[int, str]] = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0, "F"),
]


# ── data classes ─────────────────────────────────────────────────────────────


@dataclass
class SkillScore:
    """Score for a single skill file."""

    path: Path
    score: int
    grade: str
    errors: int
    warnings: int
    violations: list[Violation] = field(default_factory=list)

    @property
    def grade_style(self) -> str:
        """Rich colour style for the grade."""
        return {
            "A": "bold green",
            "B": "green",
            "C": "yellow",
            "D": "dark_orange",
            "F": "bold red",
        }.get(self.grade, "white")


@dataclass
class ScanScore:
    """Aggregate score across all scanned skills."""

    skill_scores: list[SkillScore]

    @property
    def average_score(self) -> float:
        if not self.skill_scores:
            return 100.0
        return sum(s.score for s in self.skill_scores) / len(self.skill_scores)

    @property
    def average_grade(self) -> str:
        return _grade(round(self.average_score))

    @property
    def total_errors(self) -> int:
        return sum(s.errors for s in self.skill_scores)

    @property
    def total_warnings(self) -> int:
        return sum(s.warnings for s in self.skill_scores)

    def to_dict(self) -> dict:
        return {
            "average_score": round(self.average_score, 1),
            "average_grade": self.average_grade,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "skills": [
                {
                    "path": str(s.path),
                    "score": s.score,
                    "grade": s.grade,
                    "errors": s.errors,
                    "warnings": s.warnings,
                }
                for s in self.skill_scores
            ],
        }


# ── public API ───────────────────────────────────────────────────────────────


def score_result(result: ScanResult) -> ScanScore:
    """Convert a ScanResult into a ScanScore."""
    # Group violations by file path
    by_file: dict[Path, list[Violation]] = {}
    for v in result.violations:
        key = Path(v.file)
        by_file.setdefault(key, []).append(v)

    # Every scanned skill gets a score, even if it has zero violations
    all_paths: set[Path] = {skill.path for skill in result.skill_files}
    for p in by_file:
        all_paths.add(p)

    skill_scores: list[SkillScore] = []
    for path in sorted(all_paths):
        violations = by_file.get(path, [])
        errors = sum(1 for v in violations if v.severity == Severity.ERROR)
        warnings = sum(1 for v in violations if v.severity == Severity.WARNING)
        raw = 100 - errors * ERROR_PENALTY - warnings * WARNING_PENALTY
        clamped = max(0, min(100, raw))
        skill_scores.append(
            SkillScore(
                path=path,
                score=clamped,
                grade=_grade(clamped),
                errors=errors,
                warnings=warnings,
                violations=violations,
            )
        )

    return ScanScore(skill_scores=skill_scores)


# ── helpers ──────────────────────────────────────────────────────────────────


def _grade(score: int) -> str:
    for threshold, letter in GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "F"
