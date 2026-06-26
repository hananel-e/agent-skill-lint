"""Tests for cross-skill consistency rules ROO030–ROO032."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_lint.models import Severity
from skill_lint.rules.roo.cross_skill_rules import (
    ROO030,
    ROO031,
    ROO032,
)

import skill_lint.rules.roo.cross_skill_rules  # noqa: F401


def make_skill(tmp_path: Path, content: str, dir_name: str = "my-skill"):
    from skill_lint.parsers.frontmatter import parse_frontmatter
    from skill_lint.parsers.markdown_body import parse_body

    skill_dir = tmp_path / dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "skill.md"
    skill_file.write_text(content, encoding="utf-8")
    skill = parse_frontmatter(skill_file)
    return parse_body(skill)


VALID_CONTENT = """\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite for any Python module. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

This skill generates comprehensive test suites for Python modules using pytest.
"""


class TestROO030:
    def test_passes_when_no_skill_refs(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        violations = ROO030().check(skill, all_skills=[skill])
        assert violations == []

    def test_passes_when_referenced_skill_exists(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate tests. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

Use `other-skill` to handle the deployment step.
"""
        skill_a = make_skill(tmp_path, content, dir_name="my-skill")

        other_content = """\
---
name: other-skill
description: Use this skill when you need to deploy. Invoked when deployment is needed.
modeSlugs:
  - code
---

# other-skill

## 1. Overview

Handles deployment.
"""
        skill_b = make_skill(tmp_path, other_content, dir_name="other-skill")
        violations = ROO030().check(skill_a, all_skills=[skill_a, skill_b])
        assert violations == []

    def test_fails_when_referenced_skill_missing(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate tests. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

Use `missing-skill` to handle the deployment step.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO030().check(skill, all_skills=[skill])
        assert len(violations) == 1
        assert violations[0].rule == "ROO030"
        assert violations[0].severity == Severity.WARNING


class TestROO031:
    def test_passes_with_standard_handoff_path(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate tests. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

Write output to `.idex/handoff/TICKET-123/result.md`.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO031().check(skill)
        assert violations == []

    def test_fails_with_non_standard_handoff_path(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate tests. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

Write output to `handoff/results/output.md`.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO031().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO031"
        assert violations[0].severity == Severity.WARNING


class TestROO032:
    def test_passes_when_no_slug_conflict(self, tmp_path):
        skill_a = make_skill(tmp_path, VALID_CONTENT, dir_name="skill-a")

        other_content = """\
---
name: skill-b
description: Use this skill when you need to deploy. Invoked when deployment is needed.
modeSlugs:
  - architect
---

# skill-b

## 1. Overview

Handles deployment.
"""
        skill_b = make_skill(tmp_path, other_content, dir_name="skill-b")
        violations = ROO032().check(skill_a, all_skills=[skill_a, skill_b])
        assert violations == []

    def test_fails_when_slug_conflict(self, tmp_path):
        skill_a = make_skill(tmp_path, VALID_CONTENT, dir_name="skill-a")

        other_content = """\
---
name: skill-b
description: Use this skill when you need to deploy. Invoked when deployment is needed.
modeSlugs:
  - code
---

# skill-b

## 1. Overview

Handles deployment.
"""
        skill_b = make_skill(tmp_path, other_content, dir_name="skill-b")
        violations = ROO032().check(skill_a, all_skills=[skill_a, skill_b])
        assert len(violations) == 1
        assert violations[0].rule == "ROO032"
        assert violations[0].severity == Severity.ERROR
        assert "skill-b" in violations[0].message
