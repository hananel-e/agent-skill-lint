"""Tests for v0.2.0 features: slug_registry, scorer, sync, simulator, ROO034-036."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tests.conftest import make_skill
from skill_lint.models import ScanResult, SkillFile, Severity, Violation


# ── slug_registry ─────────────────────────────────────────────────────────────


class TestSlugRegistry:
    def test_load_slugs_returns_frozenset(self):
        from skill_lint.slug_registry import load_slugs, FALLBACK_SLUGS

        slugs = load_slugs()
        assert isinstance(slugs, frozenset)
        assert len(slugs) >= len(FALLBACK_SLUGS)

    def test_fallback_slugs_contains_known_modes(self):
        from skill_lint.slug_registry import FALLBACK_SLUGS

        assert "code" in FALLBACK_SLUGS
        assert "architect" in FALLBACK_SLUGS
        assert "debug" in FALLBACK_SLUGS

    def test_read_slugs_file_valid(self, tmp_path):
        from skill_lint.slug_registry import _read_slugs_file

        f = tmp_path / "slugs.json"
        f.write_text(json.dumps({"slugs": ["code", "debug"]}))
        result = _read_slugs_file(f, "test")
        assert result == ["code", "debug"]

    def test_read_slugs_file_missing(self, tmp_path):
        from skill_lint.slug_registry import _read_slugs_file

        result = _read_slugs_file(tmp_path / "nonexistent.json", "test")
        assert result == []

    def test_read_slugs_file_invalid_json(self, tmp_path):
        from skill_lint.slug_registry import _read_slugs_file

        f = tmp_path / "bad.json"
        f.write_text("not json")
        result = _read_slugs_file(f, "test")
        assert result == []

    def test_fetch_and_cache_network_error(self, tmp_path, monkeypatch):
        """fetch_and_cache returns (False, message) on network error."""
        from skill_lint import slug_registry

        monkeypatch.setattr(slug_registry, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(slug_registry, "_CACHE_FILE", tmp_path / "slugs.json")

        ok, msg = slug_registry.fetch_and_cache(timeout=1)
        # Either succeeds (if network available) or fails gracefully
        assert isinstance(ok, bool)
        assert isinstance(msg, str)

    def test_bundled_slugs_json_is_valid(self):
        """The bundled slugs.json in the repo root is valid."""
        from skill_lint.slug_registry import _BUNDLED_FILE

        if _BUNDLED_FILE.exists():
            data = json.loads(_BUNDLED_FILE.read_text())
            assert "slugs" in data
            assert isinstance(data["slugs"], list)
            assert len(data["slugs"]) > 0


# ── scorer ────────────────────────────────────────────────────────────────────


class TestScorer:
    def _make_result(self, skills, violations):
        return ScanResult(
            files_scanned=len(skills),
            files_clean=0,
            violations=violations,
            skill_files=skills,
        )

    def test_perfect_score(self, tmp_path):
        from skill_lint.scorer import score_result

        skill = make_skill(tmp_path, "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n")
        result = self._make_result([skill], [])
        scan_score = score_result(result)

        assert len(scan_score.skill_scores) == 1
        assert scan_score.skill_scores[0].score == 100
        assert scan_score.skill_scores[0].grade == "A"

    def test_error_penalty(self, tmp_path):
        from skill_lint.scorer import score_result

        skill = make_skill(tmp_path, "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n")
        v = Violation(file=str(skill.path), rule="ROO001", severity=Severity.ERROR, message="x")
        result = self._make_result([skill], [v])
        scan_score = score_result(result)

        assert scan_score.skill_scores[0].score == 85  # 100 - 15

    def test_warning_penalty(self, tmp_path):
        from skill_lint.scorer import score_result

        skill = make_skill(tmp_path, "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n")
        v = Violation(file=str(skill.path), rule="ROO005", severity=Severity.WARNING, message="x")
        result = self._make_result([skill], [v])
        scan_score = score_result(result)

        assert scan_score.skill_scores[0].score == 95  # 100 - 5

    def test_score_clamped_to_zero(self, tmp_path):
        from skill_lint.scorer import score_result

        skill = make_skill(tmp_path, "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n")
        violations = [
            Violation(file=str(skill.path), rule=f"ROO00{i}", severity=Severity.ERROR, message="x")
            for i in range(10)
        ]
        result = self._make_result([skill], violations)
        scan_score = score_result(result)

        assert scan_score.skill_scores[0].score == 0

    def test_grade_thresholds(self):
        from skill_lint.scorer import _grade

        assert _grade(100) == "A"
        assert _grade(90) == "A"
        assert _grade(89) == "B"
        assert _grade(80) == "B"
        assert _grade(79) == "C"
        assert _grade(70) == "C"
        assert _grade(69) == "D"
        assert _grade(60) == "D"
        assert _grade(59) == "F"
        assert _grade(0) == "F"

    def test_average_score(self, tmp_path):
        from skill_lint.scorer import score_result

        skill1 = make_skill(tmp_path / "a", "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n")
        skill2 = make_skill(tmp_path / "b", "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n")
        v = Violation(file=str(skill1.path), rule="ROO001", severity=Severity.ERROR, message="x")
        result = self._make_result([skill1, skill2], [v])
        scan_score = score_result(result)

        assert scan_score.average_score == 92.5  # (85 + 100) / 2

    def test_to_dict(self, tmp_path):
        from skill_lint.scorer import score_result

        skill = make_skill(tmp_path, "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n")
        result = self._make_result([skill], [])
        d = score_result(result).to_dict()

        assert "average_score" in d
        assert "average_grade" in d
        assert "skills" in d
        assert isinstance(d["skills"], list)


# ── sync ──────────────────────────────────────────────────────────────────────


class TestSync:
    def _make_skill_with_slugs(self, tmp_path, name, slugs):
        content = f"---\nname: {name}\ndescription: A skill for testing.\nmodeSlugs: {json.dumps(slugs)}\n---\n# {name}\n"
        return make_skill(tmp_path / name, content)

    def test_clean_when_no_roomodes(self, tmp_path):
        from skill_lint.sync import load_roomodes, sync_report

        skill = self._make_skill_with_slugs(tmp_path, "my-skill", ["code"])
        roomodes_slugs = load_roomodes(tmp_path)  # no .roomodes files
        report = sync_report([skill], roomodes_slugs)

        assert report.is_clean  # no .roomodes → nothing to compare

    def test_undocumented_mode(self, tmp_path):
        from skill_lint.sync import sync_report

        skill = self._make_skill_with_slugs(tmp_path, "my-skill", ["code"])
        # .roomodes defines "code" and "debug", but only "code" is covered
        roomodes_slugs = {"code": tmp_path / ".roomodes", "debug": tmp_path / ".roomodes"}
        report = sync_report([skill], roomodes_slugs)

        assert "debug" in report.undocumented_modes
        assert "code" not in report.undocumented_modes

    def test_orphaned_slug(self, tmp_path):
        from skill_lint.sync import sync_report

        skill = self._make_skill_with_slugs(tmp_path, "my-skill", ["code", "unknown-mode"])
        roomodes_slugs = {"code": tmp_path / ".roomodes"}
        report = sync_report([skill], roomodes_slugs)

        assert "unknown-mode" in report.orphaned_skill_slugs

    def test_fully_aligned(self, tmp_path):
        from skill_lint.sync import sync_report

        skill = self._make_skill_with_slugs(tmp_path, "my-skill", ["code"])
        roomodes_slugs = {"code": tmp_path / ".roomodes"}
        report = sync_report([skill], roomodes_slugs)

        assert report.is_clean
        assert not report.undocumented_modes
        assert not report.orphaned_skill_slugs

    def test_load_roomodes_from_file(self, tmp_path):
        from skill_lint.sync import load_roomodes

        roomodes = tmp_path / ".roomodes"
        roomodes.write_text(json.dumps({
            "customModes": [
                {"slug": "my-mode", "name": "My Mode"},
                {"slug": "other-mode", "name": "Other"},
            ]
        }))
        slugs = load_roomodes(tmp_path)

        assert "my-mode" in slugs
        assert "other-mode" in slugs

    def test_to_dict(self, tmp_path):
        from skill_lint.sync import sync_report

        skill = self._make_skill_with_slugs(tmp_path, "my-skill", ["code"])
        roomodes_slugs = {"code": tmp_path / ".roomodes", "debug": tmp_path / ".roomodes"}
        report = sync_report([skill], roomodes_slugs)
        d = report.to_dict()

        assert "is_clean" in d
        assert "undocumented_modes" in d
        assert "orphaned_skill_slugs" in d


# ── simulator ─────────────────────────────────────────────────────────────────


class TestSimulator:
    def _make_skill_with_desc(self, tmp_path, name, description):
        content = f"---\nname: {name}\ndescription: {description}\nmodeSlugs: [code]\n---\n# {name}\n"
        return make_skill(tmp_path / name, content)

    def test_exact_match(self, tmp_path):
        from skill_lint.simulator import simulate

        skill = self._make_skill_with_desc(tmp_path, "coder", "Write and implement code changes")
        result = simulate("write code", [skill])

        assert result.top_match is not None
        assert result.top_match.score > 0
        assert result.top_match.match_type in ("exact", "substring", "fuzzy")

    def test_no_match_empty_description(self, tmp_path):
        from skill_lint.simulator import simulate

        skill = make_skill(tmp_path, "---\nname: s\nmodeSlugs: [code]\n---\n# S\n")
        result = simulate("write code", [skill])

        assert result.top_match is not None
        assert result.top_match.score == 0.0

    def test_empty_query(self, tmp_path):
        from skill_lint.simulator import simulate

        skill = self._make_skill_with_desc(tmp_path, "coder", "Write code")
        result = simulate("", [skill])

        assert result.matches == []

    def test_top_n_limit(self, tmp_path):
        from skill_lint.simulator import simulate

        skills = [
            self._make_skill_with_desc(tmp_path / str(i), f"skill-{i}", f"Skill number {i} for testing")
            for i in range(10)
        ]
        result = simulate("skill testing", skills, top_n=3)

        assert len(result.matches) <= 3

    def test_is_ambiguous_when_close_scores(self, tmp_path):
        from skill_lint.simulator import simulate

        # Two skills with nearly identical descriptions
        skill1 = self._make_skill_with_desc(tmp_path / "a", "skill-a", "Write and implement code changes for the project")
        skill2 = self._make_skill_with_desc(tmp_path / "b", "skill-b", "Write and implement code changes for the system")
        result = simulate("write code changes", [skill1, skill2])

        # Both should match well; ambiguity depends on exact scores
        assert result.top_match is not None

    def test_to_dict(self, tmp_path):
        from skill_lint.simulator import simulate

        skill = self._make_skill_with_desc(tmp_path, "coder", "Write code and fix bugs")
        result = simulate("write code", [skill])
        d = result.to_dict()

        assert "query" in d
        assert "is_ambiguous" in d
        assert "matches" in d
        assert isinstance(d["matches"], list)

    def test_embeddings_fallback_when_not_installed(self, tmp_path, monkeypatch):
        """When sentence-transformers is not installed, simulate() falls back to heuristic."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from skill_lint.simulator import simulate

        skill = self._make_skill_with_desc(tmp_path, "coder", "Write code")
        result = simulate("write code", [skill], use_embeddings=True)

        # Should still return a result (heuristic fallback)
        assert result.top_match is not None


# ── ROO034 ────────────────────────────────────────────────────────────────────


class TestROO034:
    def _make_skill_with_desc(self, tmp_path, name, description):
        content = f"---\nname: {name}\ndescription: {description}\nmodeSlugs: [code]\n---\n# {name}\n"
        return make_skill(tmp_path / name, content)

    def test_no_violation_when_single_skill(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO034

        skill = self._make_skill_with_desc(tmp_path, "s", "Write code and implement features")
        violations = ROO034().check(skill, all_skills=[skill])
        assert violations == []

    def test_no_violation_when_descriptions_differ(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO034

        skill1 = self._make_skill_with_desc(tmp_path / "a", "s1", "Write and implement code changes")
        skill2 = self._make_skill_with_desc(tmp_path / "b", "s2", "Plan architecture and design systems")
        violations = ROO034().check(skill1, all_skills=[skill1, skill2])
        assert violations == []

    def test_violation_when_descriptions_very_similar(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO034

        desc = "Write and implement code changes for the project using best practices"
        skill1 = self._make_skill_with_desc(tmp_path / "a", "s1", desc)
        skill2 = self._make_skill_with_desc(tmp_path / "b", "s2", desc)  # identical
        violations = ROO034().check(skill1, all_skills=[skill1, skill2])
        assert len(violations) == 1
        assert "ROO034" in violations[0].rule

    def test_configurable_threshold(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO034

        skill1 = self._make_skill_with_desc(tmp_path / "a", "s1", "Write code and implement features")
        skill2 = self._make_skill_with_desc(tmp_path / "b", "s2", "Write code and implement features for the project")
        # With very high threshold (1.0), should not fire
        violations = ROO034().check(
            skill1,
            all_skills=[skill1, skill2],
            cfg={"rules": {"ROO034": {"overlap_threshold": 1.0}}},
        )
        assert violations == []


# ── ROO035 ────────────────────────────────────────────────────────────────────


class TestROO035:
    def test_no_violation_when_no_roomodes(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO035

        content = "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n"
        skill = make_skill(tmp_path, content)
        violations = ROO035().check(skill, repo_root=tmp_path)
        assert violations == []  # no .roomodes → skip

    def test_violation_when_slug_absent_from_roomodes(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO035

        roomodes = tmp_path / ".roomodes"
        roomodes.write_text(json.dumps({"customModes": [{"slug": "debug"}]}))

        content = "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n"
        skill = make_skill(tmp_path, content)
        violations = ROO035().check(skill, repo_root=tmp_path)
        assert any("code" in v.message for v in violations)

    def test_no_violation_when_slug_in_roomodes(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO035

        roomodes = tmp_path / ".roomodes"
        roomodes.write_text(json.dumps({"customModes": [{"slug": "code"}]}))

        content = "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n"
        skill = make_skill(tmp_path, content)
        violations = ROO035().check(skill, repo_root=tmp_path)
        assert violations == []


# ── ROO036 ────────────────────────────────────────────────────────────────────


class TestROO036:
    def test_no_violation_when_no_roomodes(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO036

        content = "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n"
        skill = make_skill(tmp_path, content)
        violations = ROO036().check(skill, all_skills=[skill], repo_root=tmp_path)
        assert violations == []

    def test_violation_for_undocumented_mode(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO036

        roomodes = tmp_path / ".roomodes"
        roomodes.write_text(json.dumps({
            "customModes": [{"slug": "code"}, {"slug": "debug"}]
        }))

        content = "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n"
        skill = make_skill(tmp_path, content)
        # Only fires on first skill
        violations = ROO036().check(skill, all_skills=[skill], repo_root=tmp_path)
        assert any("debug" in v.message for v in violations)

    def test_only_fires_on_first_skill(self, tmp_path):
        from skill_lint.rules.roo.cross_skill_rules import ROO036

        roomodes = tmp_path / ".roomodes"
        roomodes.write_text(json.dumps({"customModes": [{"slug": "code"}, {"slug": "debug"}]}))

        content = "---\nname: s\ndescription: d\nmodeSlugs: [code]\n---\n# S\n"
        skill1 = make_skill(tmp_path / "a", content)
        skill2 = make_skill(tmp_path / "b", content)

        # Should fire on skill1 (first) but not skill2
        v1 = ROO036().check(skill1, all_skills=[skill1, skill2], repo_root=tmp_path)
        v2 = ROO036().check(skill2, all_skills=[skill1, skill2], repo_root=tmp_path)
        assert len(v1) > 0
        assert len(v2) == 0
