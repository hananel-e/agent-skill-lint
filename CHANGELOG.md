# Changelog

All notable changes to `skill-lint` will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
