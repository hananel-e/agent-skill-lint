# skill-lint

> Static quality linter for AI agent skill definitions (`SKILL.md` files).

`skill-lint` is the `eslint` of the agent skill world — pure static analysis, zero LLM calls, zero cloud dependency, pre-commit-friendly, CI-ready.

It catches bad skill definitions **at development time**, before they reach the agent.

---

## Installation

```bash
pip install skill-lint
```

Or from source:

```bash
git clone https://github.com/hananel-e/skill-lint
cd skill-lint
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Lint all skill.md files found recursively under a path
skill-lint roo check .

# Lint a single file
skill-lint roo check .roo/skills-build/coder/skill.md

# Filter by severity
skill-lint roo check . --severity error      # errors only

# Output formats
skill-lint roo check . --format json         # machine-readable
skill-lint roo check . --format github       # GitHub Actions annotations

# Disable specific rules
skill-lint roo check . --ignore ROO012,ROO031

# List all rules
skill-lint roo rules

# Explain a specific rule
skill-lint roo explain ROO013

# Check tool dependencies
skill-lint doctor
```

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Clean — no violations |
| `1` | One or more violations found |
| `2` | Tool error (file not found, parse failure, etc.) |

---

## Rule Catalogue

### Category A — Frontmatter Rules

| Rule ID | Severity | Description |
|---|---|---|
| `ROO001` | error | `name` field missing from frontmatter |
| `ROO002` | error | `description` field missing from frontmatter |
| `ROO003` | error | `modeSlugs` field missing from frontmatter |
| `ROO004` | error | `modeSlugs` is an empty list |
| `ROO005` | warning | `modeSlugs` contains an unrecognised mode slug |
| `ROO006` | warning | `name` value does not match the parent directory name |
| `ROO007` | error | `description` is too short (< 50 characters) |
| `ROO008` | warning | `description` is too long (> 400 characters) |

### Category B — Description Quality Rules

| Rule ID | Severity | Description |
|---|---|---|
| `ROO010` | warning | Description missing a trigger condition keyword |
| `ROO011` | warning | Description does not start with an action verb or `Use` |
| `ROO012` | warning | Description contains vague words |
| `ROO013` | warning | Description has >75% token overlap with another skill |
| `ROO014` | warning | Skill `name` mentioned in description is inconsistent with frontmatter |

### Category C — Body Structure Rules

| Rule ID | Severity | Description |
|---|---|---|
| `ROO020` | error | No H1 heading found after frontmatter |
| `ROO021` | warning | H1 heading text does not match frontmatter `name` |
| `ROO022` | warning | Body has no numbered sections — likely a stub |
| `ROO023` | error | Markdown link target does not exist relative to repo root |
| `ROO024` | warning | Body references a mode slug not present in `.roomodes` |
| `ROO025` | warning | Body after frontmatter is < 100 characters — stub skill |

### Category D — Cross-Skill Consistency Rules

| Rule ID | Severity | Description |
|---|---|---|
| `ROO030` | warning | Body references a skill name with no corresponding `skill.md` |
| `ROO031` | warning | Handoff file path uses a non-standard pattern |
| `ROO032` | error | Two or more skills claim the same `modeSlugs` entry |

---

## Configuration

Place a `.skill-lint.yaml` file at your repo root (copy from [`.skill-lint.yaml.example`](.skill-lint.yaml.example)):

```yaml
rules:
  ROO007:
    min_length: 60          # override default (50)
  ROO008:
    max_length: 300         # override default (400)
  ROO013:
    similarity_threshold: 0.80   # override default (0.75)

ignore:
  - ".roo/skills/legacy/"        # skip entire directory
  - "ROO031"                     # globally disable a rule

# Custom vague words (appended to built-in list)
vague_words:
  - "facilitates"

# Known mode slugs (appended to built-in list)
extra_mode_slugs:
  - "my-custom-mode"
```

### Per-rule overrides

Three rules accept numeric overrides under the `rules:` key:

| Rule | Config key | Default | Effect |
|---|---|---|---|
| `ROO007` | `rules.ROO007.min_length` | `50` | Minimum description length in characters. Raise it if your team requires more detail. |
| `ROO008` | `rules.ROO008.max_length` | `400` | Maximum description length in characters. Lower it to enforce tighter descriptions. |
| `ROO013` | `rules.ROO013.similarity_threshold` | `0.75` | Token-overlap ratio (0–1) above which two skill descriptions are flagged as too similar. Raise it to allow more overlap; lower it to enforce stricter uniqueness. |

**Example** — enforce 60-char minimum and flag descriptions that are 80%+ similar:

```yaml
rules:
  ROO007:
    min_length: 60
  ROO013:
    similarity_threshold: 0.80
```

### Ignoring rules and paths

```yaml
ignore:
  - "ROO031"                  # disable rule globally
  - ".roo/skills/legacy/"     # skip all skill.md files under this path prefix
```

You can also suppress rules for a single run without touching the config:

```bash
skill-lint roo check . --ignore ROO012,ROO031
```

### Extending the mode slug allowlist

If your Roo setup uses custom modes not in the built-in list, add them so `ROO005` does not flag them as unknown:

```yaml
extra_mode_slugs:
  - "my-workflow"
  - "data-analyst"
```

### Extending the vague word list

The built-in vague words are: `handles`, `manages`, `does`, `performs`, `processes`.
Append your own:

```yaml
vague_words:
  - "facilitates"
  - "coordinates"
  - "oversees"
```

---

## Example Output

```
.roo/skills-build/coder/skill.md
  ✗ ROO008  description is 412 chars (max 400)                    [error]
  ⚠ ROO012  description uses vague word: "owns"                   [warning]

.roo/skills/api-schema-generator/skill.md
  ✗ ROO023  broken link: .roo/skills-build/coder/ui-patterns.md   [error]
  ⚠ ROO022  no numbered sections found                            [warning]

────────────────────────────────────────────────────────────
2 errors  |  2 warnings  |  3 files scanned  |  1 clean
```

---

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/hananel-e/skill-lint
    rev: v0.1.0
    hooks:
      - id: skill-lint-roo
        name: skill-lint (Roo skills)
        language: python
        entry: skill-lint roo check
        files: skill\.md$
        pass_filenames: false
        args: ["."]
```

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

---

## Tech Stack

| Concern | Library |
|---|---|
| CLI | `typer` |
| Terminal output | `rich` |
| Frontmatter parsing | `python-frontmatter` |
| Markdown parsing | `markdown-it-py` |
| Token overlap (ROO013) | `difflib.SequenceMatcher` (stdlib) |
| Config file | `pyyaml` |
| Build backend | `hatchling` |
| Test framework | `pytest` |

Zero heavy dependencies — no `scikit-learn`, no `sentence-transformers`, no LLM calls.

---

## License

Apache 2.0
