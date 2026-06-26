"""Shared pytest fixtures for skill-lint tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_lint.models import SkillFile
from skill_lint.parsers.frontmatter import parse_frontmatter
from skill_lint.parsers.markdown_body import parse_body


def make_skill(tmp_path: Path, content: str, filename: str = "skill.md") -> SkillFile:
    """Write content to a temp skill.md and parse it into a SkillFile."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / filename
    skill_file.write_text(content, encoding="utf-8")
    skill = parse_frontmatter(skill_file)
    skill = parse_body(skill)
    return skill


@pytest.fixture
def good_skill(tmp_path: Path) -> SkillFile:
    """A fully valid skill file that should pass all rules."""
    content = (tmp_path.parent / "tests" / "fixtures" / "valid" / "good_skill.md").read_text()
    return make_skill(tmp_path, content)
