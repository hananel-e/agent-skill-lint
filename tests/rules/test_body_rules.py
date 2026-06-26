"""Tests for body structure rules ROO020–ROO025."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_lint.models import Severity
from skill_lint.rules.roo.body_rules import (
    ROO020,
    ROO021,
    ROO022,
    ROO023,
    ROO024,
    ROO025,
)

import skill_lint.rules.roo.body_rules  # noqa: F401


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

## 2. Steps

Follow these steps carefully.
"""


class TestROO020:
    def test_passes_with_h1(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO020().check(skill) == []

    def test_fails_without_h1(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite. Invoked when the user asks.
modeSlugs:
  - code
---

## 1. Overview

No H1 heading here.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO020().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO020"
        assert violations[0].severity == Severity.ERROR


class TestROO021:
    def test_passes_when_h1_matches_name(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO021().check(skill) == []

    def test_fails_when_h1_mismatches_name(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite. Invoked when the user asks.
modeSlugs:
  - code
---

# Different Title

## 1. Overview

Content here.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO021().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO021"
        assert violations[0].severity == Severity.WARNING


class TestROO022:
    def test_passes_with_numbered_sections(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO022().check(skill) == []

    def test_fails_without_numbered_sections(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## Overview

No numbered sections here, just regular headings.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO022().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO022"
        assert violations[0].severity == Severity.WARNING


class TestROO023:
    def test_passes_with_no_links(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO023().check(skill, repo_root=tmp_path) == []

    def test_passes_with_existing_link(self, tmp_path):
        # Create the target file
        target = tmp_path / "existing.md"
        target.write_text("# Existing", encoding="utf-8")

        content = f"""\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

See [existing file](existing.md) for details.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO023().check(skill, repo_root=tmp_path)
        assert violations == []

    def test_fails_with_broken_link(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

See [missing file](./does-not-exist.md) for details.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO023().check(skill, repo_root=tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "ROO023"
        assert violations[0].severity == Severity.ERROR

    def test_ignores_http_links(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

See [external](https://example.com) for details.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO023().check(skill, repo_root=tmp_path)
        assert violations == []


class TestROO024:
    def test_skips_when_no_roomodes(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        # No .roomodes file in tmp_path
        violations = ROO024().check(skill, repo_root=tmp_path)
        assert violations == []

    def test_passes_when_slug_in_roomodes(self, tmp_path):
        import json
        roomodes = {"customModes": [{"slug": "code", "name": "Code"}]}
        (tmp_path / ".roomodes").write_text(json.dumps(roomodes), encoding="utf-8")

        content = """\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

## 1. Overview

Use in code mode.
"""
        skill = make_skill(tmp_path, content)
        violations = ROO024().check(skill, repo_root=tmp_path)
        assert violations == []


class TestROO025:
    def test_passes_with_long_body(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO025().check(skill) == []

    def test_fails_with_short_body(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need to generate a comprehensive test suite. Invoked when the user asks.
modeSlugs:
  - code
---

# my-skill

TODO
"""
        skill = make_skill(tmp_path, content)
        violations = ROO025().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO025"
        assert violations[0].severity == Severity.WARNING
