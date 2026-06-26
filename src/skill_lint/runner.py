"""Orchestrates parse → lint → collect for skill-lint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skill_lint.models import ScanResult, SkillFile, Violation
from skill_lint.parsers.frontmatter import parse_frontmatter
from skill_lint.parsers.markdown_body import parse_body

# Import rule modules to trigger @register decorators
import skill_lint.rules.roo.frontmatter_rules  # noqa: F401
import skill_lint.rules.roo.description_rules  # noqa: F401
import skill_lint.rules.roo.body_rules  # noqa: F401
import skill_lint.rules.roo.cross_skill_rules  # noqa: F401

from skill_lint.rules.base import RULE_REGISTRY


def _find_skill_files(path: Path) -> list[Path]:
    """Recursively find all skill.md files under path."""
    if path.is_file():
        return [path]
    return sorted(path.rglob("skill.md"))


def _is_ignored_path(skill_path: Path, ignore_paths: list[str]) -> bool:
    """Return True if the skill path matches any ignored path prefix."""
    path_str = str(skill_path)
    for pattern in ignore_paths:
        if path_str.startswith(pattern) or pattern in path_str:
            return True
    return False


def run_scan(
    scan_path: Path,
    cfg: dict[str, Any] | None = None,
    ignored_rules: set[str] | None = None,
) -> ScanResult:
    """Run the full lint pipeline and return a ScanResult."""
    if cfg is None:
        cfg = {}
    if ignored_rules is None:
        ignored_rules = set()

    ignore_paths: list[str] = cfg.get("ignore_paths", [])

    # Determine repo root (walk up to find .git or use scan_path parent)
    repo_root = _find_repo_root(scan_path)

    # 1. Discover files
    raw_paths = _find_skill_files(scan_path)
    paths = [p for p in raw_paths if not _is_ignored_path(p, ignore_paths)]

    # 2. Parse all files
    skills: list[SkillFile] = []
    parse_errors: list[Violation] = []

    for path in paths:
        try:
            skill = parse_frontmatter(path)
            skill = parse_body(skill)
            skills.append(skill)
        except Exception as exc:
            parse_errors.append(
                Violation(
                    file=str(path),
                    rule="PARSE",
                    severity=__import__("skill_lint.models", fromlist=["Severity"]).Severity.ERROR,
                    message=f"Failed to parse file: {exc}",
                    line=None,
                )
            )

    # 3. Run rules
    all_violations: list[Violation] = list(parse_errors)
    files_with_violations: set[str] = set()

    for skill in skills:
        skill_violations: list[Violation] = []

        for rule_id, rule in sorted(RULE_REGISTRY.items()):
            if rule_id in ignored_rules:
                continue
            try:
                violations = rule.check(
                    skill,
                    all_skills=skills,
                    cfg=cfg,
                    repo_root=repo_root,
                )
                skill_violations.extend(violations)
            except Exception as exc:
                skill_violations.append(
                    Violation(
                        file=str(skill.path),
                        rule=rule_id,
                        severity=__import__("skill_lint.models", fromlist=["Severity"]).Severity.ERROR,
                        message=f"Rule check failed: {exc}",
                        line=None,
                    )
                )

        if skill_violations:
            files_with_violations.add(str(skill.path))
        all_violations.extend(skill_violations)

    # 4. Build result
    result = ScanResult(
        files_scanned=len(skills),
        files_clean=len(skills) - len(files_with_violations),
        violations=all_violations,
        skill_files=skills,
    )
    return result


def _find_repo_root(start: Path) -> Path:
    """Walk up from start to find the git repo root. Falls back to start."""
    current = start if start.is_dir() else start.parent
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return current
