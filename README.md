# agent-skill-lint

> Static quality linter for AI agent skill definitions (`SKILL.md` files).

`agent-skill-lint` is the `eslint` of the agent skill world — pure static analysis, zero LLM calls, zero cloud dependency, pre-commit-friendly, CI-ready.

It catches bad skill definitions **at development time**, before they reach the agent.

---

## Installation

```bash
pip install agent-skill-lint
```

Or from source:

```bash
git clone https://github.com/hananel-e/agent-skill-lint
cd agent-skill-lint
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

# ── v0.2.0 commands ──────────────────────────────────────────────────────────

# Score skills (A-F quality grades)
skill-lint roo score .
skill-lint roo score . --format json
skill-lint roo score . --fail-under 80       # exit 1 if average < 80

# Simulate routing for a query (no ML required)
skill-lint roo simulate "write and fix code" --path .roo/skills/
skill-lint roo simulate "plan architecture" --path . --top 3
skill-lint roo simulate "debug errors" --path . --embeddings   # requires [embeddings] extra

# Check framework sync (.roomodes ↔ skills)
skill-lint roo sync .
skill-lint roo sync . --format json
skill-lint roo sync . --roomodes .roomodes   # use a specific .roomodes file

# Update the known mode slug cache from GitHub
skill-lint roo update-slugs
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
| `ROO034` | warning | Two skills have descriptions with high token overlap — ambiguous routing |
| `ROO035` | warning | Skill's `modeSlugs` references a mode not defined in any `.roomodes` file |
| `ROO036` | warning | A mode defined in `.roomodes` has no skill covering it |

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

Four rules accept numeric overrides under the `rules:` key:

| Rule | Config key | Default | Effect |
|---|---|---|---|
| `ROO007` | `rules.ROO007.min_length` | `50` | Minimum description length in characters. Raise it if your team requires more detail. |
| `ROO008` | `rules.ROO008.max_length` | `400` | Maximum description length in characters. Lower it to enforce tighter descriptions. |
| `ROO013` | `rules.ROO013.similarity_threshold` | `0.75` | Token-overlap ratio (0–1) above which two skill descriptions are flagged as too similar. Raise it to allow more overlap; lower it to enforce stricter uniqueness. |
| `ROO034` | `rules.ROO034.overlap_threshold` | `0.60` | SequenceMatcher ratio (0–1) above which two skill descriptions are flagged as routing-ambiguous. |

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
  - repo: https://github.com/hananel-e/agent-skill-lint
    rev: v0.2.0
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
| Token overlap (ROO013, ROO034) | `difflib.SequenceMatcher` (stdlib) |
| Config file | `pyyaml` |
| Slug registry | stdlib `urllib`, `json` |
| Routing simulator | stdlib `difflib`, `re` |
| Embedding backend (opt-in) | `sentence-transformers` + `numpy` |
| Build backend | `hatchling` |
| Test framework | `pytest` |

Zero heavy dependencies by default — no `scikit-learn`, no LLM calls.
Use `pip install 'agent-skill-lint[embeddings]'` to enable the embedding-based routing simulator.

---

## v0.2.0 Features

### Quality Scorer (`roo score`)

Converts lint violations into a numeric score (0–100) and letter grade (A–F) per skill, plus an aggregate average. Use `--fail-under N` to gate CI on quality.

```
Scoring: base 100, -15 per ERROR, -5 per WARNING (clamped to 0)
Grades:  A ≥90  B ≥80  C ≥70  D ≥60  F <60
```

### Routing Simulator (`roo simulate`)

Ranks all scanned skills by how well their description matches a natural-language query. Useful for spotting ambiguous descriptions before deploying to a live agent.

- Default: heuristic keyword scoring (no extra deps)
- `--embeddings`: cosine similarity via `sentence-transformers` (more accurate)
- `--top N`: show top N matches
- `--fuzzy-threshold`: tune fuzzy matching sensitivity

### Framework Sync Checker (`roo sync`)

Compares `.roomodes` definitions against scanned skill files. Detects:
- **Undocumented modes**: defined in `.roomodes` but no skill covers them
- **Orphaned slugs**: a skill's `modeSlugs` references a mode absent from `.roomodes`

### Slug Registry (`roo update-slugs`)

Fetches the latest known mode slugs from GitHub and caches them at `~/.cache/skill-lint/slugs.json`. ROO005 reads from this cache so the known-slug list stays current without a code release.

### New Rules

| Rule | Description |
|---|---|
| `ROO034` | Two skills have descriptions with high token overlap — ambiguous routing |
| `ROO035` | Skill's `modeSlugs` references a mode not defined in any `.roomodes` file |
| `ROO036` | A mode defined in `.roomodes` has no skill covering it |

---

## Limitations

**Heuristic rules are not perfect.** ROO010–ROO014 and ROO034 fire on patterns that *correlate* with poor skill quality — they are not proofs. A description can pass all rules and still be a bad routing signal, or fail ROO011 and still work fine in practice. Treat warnings as prompts to review, not verdicts.

**Routing simulator is heuristic by default.** The `roo simulate` command uses keyword overlap, not semantic understanding. Use `--embeddings` with `sentence-transformers` for more accurate results.

**Sync checker requires `.roomodes`.** `roo sync` and ROO035/ROO036 are no-ops when no `.roomodes` files are found in the repo. They are only meaningful for Roo-based agent setups.

---

## License

Apache 2.0
