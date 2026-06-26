# Changelog

All notable changes to `skill-lint` will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-06-26

### Added

- **`roo score` command** — quality scorer that converts lint violations into a numeric score
  (0–100) and letter grade (A–F) per skill, plus an aggregate average.
  Scoring: base 100, −15/ERROR, −5/WARNING, clamped to 0.
  Grades: A ≥90, B ≥80, C ≥70, D ≥60, F <60.
  Supports `--fail-under N` for CI gating and `--format json`.

- **`roo simulate` command** — routing simulator that ranks skills by how well their
  description matches a natural-language query. Uses 3-tier heuristic scoring
  (exact token overlap, substring, fuzzy via `difflib.SequenceMatcher`).
  Optional `--embeddings` flag uses `sentence-transformers` cosine similarity
  (requires `pip install 'agent-skill-lint[embeddings]'`).
  Detects ambiguous routing when top two matches are within 10% of each other.

- **`roo sync` command** — framework sync checker that compares `.roomodes` definitions
  against scanned skill files. Detects undocumented modes (in `.roomodes` but no skill
  covers them) and orphaned slugs (skill references a mode absent from `.roomodes`).
  Supports `--roomodes` to specify a file explicitly and `--format json`.

- **`roo update-slugs` command** — fetches the latest known mode slugs from GitHub and
  caches them at `~/.cache/skill-lint/slugs.json`. ROO005 reads from this cache so the
  known-slug list stays current without a code release.

- **`slugs.json`** — bundled seed file with 15 known Roo mode slugs, shipped with the
  package as a fallback when no cache exists.

- **`scripts/collect_slugs.py`** — helper script that scans the repo for `.roomodes` files,
  extracts `customModes[].slug` values, and merges them into `slugs.json`.

- **`.github/workflows/update-slugs.yml`** — weekly CI workflow that runs `collect_slugs.py`
  and opens a PR if `slugs.json` changes.

- **ROO034** (warning) — Two skills have descriptions with high token overlap (≥60% by
  default), indicating potential routing ambiguity. Configurable via
  `rules.ROO034.overlap_threshold`.

- **ROO035** (warning) — Skill's `modeSlugs` references a mode not defined in any
  `.roomodes` file found in the repo.

- **ROO036** (warning) — A mode defined in `.roomodes` has no skill covering it.

- **`[embeddings]` optional dependency group** — `sentence-transformers>=3.0.0` + `numpy`
  for the embedding-based routing simulator backend.

- **`ScanResult.skill_files`** field — populated by the runner so downstream consumers
  (scorer, simulator) can enumerate all parsed skills without re-scanning.

- **37 new tests** — covering slug_registry, scorer, sync, simulator, ROO034–ROO036.
  Total: 91 tests, all passing.

---

## [0.1.0] — 2026-06-26

### Added

- **22 lint rules** across four categories:
  - Category A (Frontmatter): ROO001–ROO008
  - Category B (Description quality): ROO010–ROO014
  - Category C (Body structure): ROO020–ROO025
  - Category D (Cross-skill consistency): ROO030–ROO032
- CLI commands: `skill-lint roo check`, `roo rules`, `roo explain`, `doctor`
- Output formats: `text` (rich terminal), `json`, `github` (Actions annotations)
- `.skill-lint.yaml` configuration file support
- Per-rule config overrides (thresholds, lengths)
- `--ignore` flag and `ignore:` config key for suppressing rules or paths
- `extra_mode_slugs` config key — extend known slug list without hardcoding
- `vague_words` config key — extend built-in vague word list
- Pre-commit hook support
- 54 unit tests, all passing
