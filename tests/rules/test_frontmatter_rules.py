"""Tests for frontmatter rules ROO001–ROO008."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_lint.models import Severity
from skill_lint.rules.roo.frontmatter_rules import (
    ROO001,
    ROO002,
    ROO003,
    ROO004,
    ROO005,
    ROO006,
    ROO007,
    ROO008,
)

# Import to trigger registration
import skill_lint.rules.roo.frontmatter_rules  # noqa: F401


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


class TestROO001:
    def test_passes_when_name_present(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO001().check(skill) == []

    def test_fails_when_name_missing(self, tmp_path):
        content = """\
---
description: Use this skill when you need something. Invoked when the user asks for help.
modeSlugs:
  - code
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        violations = ROO001().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO001"
        assert violations[0].severity == Severity.ERROR


class TestROO002:
    def test_passes_when_description_present(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO002().check(skill) == []

    def test_fails_when_description_missing(self, tmp_path):
        content = """\
---
name: my-skill
modeSlugs:
  - code
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        violations = ROO002().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO002"
        assert violations[0].severity == Severity.ERROR


class TestROO003:
    def test_passes_when_mode_slugs_present(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO003().check(skill) == []

    def test_fails_when_mode_slugs_missing(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need something. Invoked when the user asks for help.
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        violations = ROO003().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO003"
        assert violations[0].severity == Severity.ERROR


class TestROO004:
    def test_passes_when_mode_slugs_non_empty(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO004().check(skill) == []

    def test_fails_when_mode_slugs_empty(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need something. Invoked when the user asks for help.
modeSlugs: []
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        violations = ROO004().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO004"
        assert violations[0].severity == Severity.ERROR


class TestROO005:
    def test_passes_with_known_slug(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO005().check(skill) == []

    def test_fails_with_unknown_slug(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need something. Invoked when the user asks for help.
modeSlugs:
  - unknown-mode
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        violations = ROO005().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO005"
        assert violations[0].severity == Severity.WARNING

    def test_passes_with_extra_slug_in_config(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need something. Invoked when the user asks for help.
modeSlugs:
  - my-custom-mode
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        violations = ROO005().check(skill, cfg={"extra_mode_slugs": ["my-custom-mode"]})
        assert violations == []


class TestROO006:
    def test_passes_when_name_matches_dir(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT, dir_name="my-skill")
        assert ROO006().check(skill) == []

    def test_fails_when_name_mismatches_dir(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT, dir_name="other-name")
        violations = ROO006().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO006"
        assert violations[0].severity == Severity.WARNING


class TestROO007:
    def test_passes_with_long_enough_description(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO007().check(skill) == []

    def test_fails_with_short_description(self, tmp_path):
        content = """\
---
name: my-skill
description: Too short.
modeSlugs:
  - code
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        violations = ROO007().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO007"
        assert violations[0].severity == Severity.ERROR

    def test_respects_config_override(self, tmp_path):
        content = """\
---
name: my-skill
description: Use this skill when you need something useful done.
modeSlugs:
  - code
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        # Default min is 50, this description is ~50 chars — pass with default
        violations_default = ROO007().check(skill)
        # With min_length=100, it should fail
        violations_strict = ROO007().check(skill, cfg={"rules": {"ROO007": {"min_length": 100}}})
        assert len(violations_strict) == 1


class TestROO008:
    def test_passes_with_short_enough_description(self, tmp_path):
        skill = make_skill(tmp_path, VALID_CONTENT)
        assert ROO008().check(skill) == []

    def test_fails_with_too_long_description(self, tmp_path):
        long_desc = "Use this skill when " + "x" * 400
        content = f"""\
---
name: my-skill
description: "{long_desc}"
modeSlugs:
  - code
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        violations = ROO008().check(skill)
        assert len(violations) == 1
        assert violations[0].rule == "ROO008"
        assert violations[0].severity == Severity.WARNING

    def test_respects_config_override(self, tmp_path):
        desc = "Use this skill when you need something. " * 5  # ~200 chars
        content = f"""\
---
name: my-skill
description: "{desc}"
modeSlugs:
  - code
---

# my-skill
"""
        skill = make_skill(tmp_path, content)
        # With max_length=50, should fail
        violations = ROO008().check(skill, cfg={"rules": {"ROO008": {"max_length": 50}}})
        assert len(violations) == 1
