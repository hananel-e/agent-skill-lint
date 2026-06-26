"""Tests for description quality rules ROO010–ROO014."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_lint.models import Severity
from skill_lint.rules.roo.description_rules import (
    ROO010,
    ROO011,
    ROO012,
    ROO013,
    ROO014,
)

import skill_lint.rules.roo.description_rules  # noqa: F401


def make_skill(tmp_path: Path, content: str, dir_name: str = "my-skill"):
    from skill_lint.parsers.frontmatter import parse_frontmatter
    from skill_lint.parsers.markdown_body import parse_body

    skill_dir = tmp_path / dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "skill.md"
    skill_file.write_text(content, encoding="utf-8")
    skill = parse_frontmatter(skill_file)
    return parse_body(skill)


def skill_with_desc(tmp_path, description, dir_name="my-skill"):
    content = f"""\
---
name: my-skill
description: "{description}"
modeSlugs:
  - code
---

# my-skill

## 1. Overview

Some content here to avoid stub warnings.
"""
    return make_skill(tmp_path, content, dir_name=dir_name)


class TestROO010:
    def test_passes_with_trigger_keyword_when(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Use this skill when you need to generate tests for a Python module.",
        )
        assert ROO010().check(skill) == []

    def test_passes_with_trigger_keyword_invoked(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Generates test suites. Invoked when the user asks for test coverage.",
        )
        assert ROO010().check(skill) == []

    def test_fails_without_trigger_keyword(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Generates comprehensive test suites for Python modules using pytest framework.",
        )
        violations = ROO010().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO010"
        assert violations[0].severity == Severity.WARNING


class TestROO011:
    def test_passes_starting_with_use(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Use this skill when you need to generate tests for a Python module.",
        )
        assert ROO011().check(skill) == []

    def test_passes_starting_with_action_verb(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Generate comprehensive test suites when the user asks for coverage.",
        )
        assert ROO011().check(skill) == []

    def test_fails_starting_with_non_verb(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "This skill generates test suites when the user asks for coverage.",
        )
        violations = ROO011().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO011"
        assert violations[0].severity == Severity.WARNING


class TestROO012:
    def test_passes_without_vague_words(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Use this skill when you need to generate tests for a Python module.",
        )
        assert ROO012().check(skill) == []

    def test_fails_with_handles(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Use this skill when you need something. It handles all test generation tasks.",
        )
        violations = ROO012().check(skill)
        assert any(v.rule == "ROO012" for v in violations)
        assert any("handles" in v.message for v in violations)

    def test_fails_with_manages(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Use this skill when you need something. It manages the test pipeline.",
        )
        violations = ROO012().check(skill)
        assert any("manages" in v.message for v in violations)

    def test_respects_extra_vague_words_from_config(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Use this skill when you need something. It facilitates test generation.",
        )
        violations = ROO012().check(skill, cfg={"vague_words": ["facilitates"]})
        assert any("facilitates" in v.message for v in violations)


class TestROO013:
    def test_passes_with_unique_descriptions(self, tmp_path):
        skill_a = skill_with_desc(tmp_path, "Use this skill when you need to generate tests for Python.", dir_name="skill-a")
        skill_b_dir = tmp_path / "skill-b"
        skill_b_dir.mkdir(parents=True, exist_ok=True)
        (skill_b_dir / "skill.md").write_text(
            '---\nname: skill-b\ndescription: "Resolve merge conflicts when two branches diverge significantly."\nmodeSlugs:\n  - code\n---\n\n# skill-b\n',
            encoding="utf-8",
        )
        from skill_lint.parsers.frontmatter import parse_frontmatter
        from skill_lint.parsers.markdown_body import parse_body
        skill_b = parse_body(parse_frontmatter(skill_b_dir / "skill.md"))

        violations = ROO013().check(skill_a, all_skills=[skill_a, skill_b])
        assert violations == []

    def test_fails_with_high_overlap(self, tmp_path):
        desc = "Use this skill when you need to generate comprehensive test suites for Python modules."
        skill_a = skill_with_desc(tmp_path, desc, dir_name="skill-a")

        skill_b_dir = tmp_path / "skill-b"
        skill_b_dir.mkdir(parents=True, exist_ok=True)
        (skill_b_dir / "skill.md").write_text(
            f'---\nname: skill-b\ndescription: "{desc}"\nmodeSlugs:\n  - code\n---\n\n# skill-b\n',
            encoding="utf-8",
        )
        from skill_lint.parsers.frontmatter import parse_frontmatter
        from skill_lint.parsers.markdown_body import parse_body
        skill_b = parse_body(parse_frontmatter(skill_b_dir / "skill.md"))

        violations = ROO013().check(skill_a, all_skills=[skill_a, skill_b])
        assert len(violations) == 1
        assert violations[0].rule == "ROO013"


class TestROO014:
    def test_passes_when_no_name_mentioned(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Use this skill when you need to generate tests. Invoked when coverage is needed.",
        )
        assert ROO014().check(skill) == []

    def test_fails_when_wrong_name_mentioned(self, tmp_path):
        skill = skill_with_desc(
            tmp_path,
            "Use the other-skill skill when you need to generate tests.",
        )
        violations = ROO014().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO014"
        assert violations[0].severity == Severity.WARNING
