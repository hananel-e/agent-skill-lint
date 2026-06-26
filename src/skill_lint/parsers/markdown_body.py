"""Markdown body parser — extracts H1, sections, links, and mode slug refs."""

from __future__ import annotations

import re
from pathlib import Path

from markdown_it import MarkdownIt

from skill_lint.models import SkillFile

_md = MarkdownIt()

# Regex for numbered section headings: ## 1. Title
_NUMBERED_SECTION_RE = re.compile(r"^#{1,6}\s+\d+\.\s+")

# Regex to find skill name references (words in backticks or bold that look like skill names)
_SKILL_NAME_REF_RE = re.compile(r"`([^`]+)`|\*\*([^*]+)\*\*")

# Regex to extract all word-like tokens from body text (used for dynamic slug detection)
_WORD_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9-]*\b")


def _count_lines_before(raw_body: str, char_offset: int) -> int:
    """Return the 1-based line number at a character offset within the body."""
    return raw_body[:char_offset].count("\n") + 1


def parse_body(skill: SkillFile) -> SkillFile:
    """Populate body-related fields on a SkillFile in-place. Returns the same object."""
    body = skill.body
    if not body:
        return skill

    tokens = _md.parse(body)

    # Walk tokens to extract H1, sections, links
    i = 0
    inline_map: dict[int, list] = {}  # token index -> children

    while i < len(tokens):
        tok = tokens[i]

        # Track heading tokens
        if tok.type == "heading_open":
            level = tok.tag  # "h1", "h2", etc.
            map_info = tok.map  # [start_line, end_line] (0-based)
            line_no = (map_info[0] + 1) if map_info else None

            # Next token should be inline content
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                inline_tok = tokens[i + 1]
                heading_text = inline_tok.content.strip()

                if level == "h1" and skill.h1_title is None:
                    skill.h1_title = heading_text
                    skill.h1_line = line_no

                if _NUMBERED_SECTION_RE.match(f"{'#' * int(level[1])} {heading_text}"):
                    skill.numbered_sections.append(heading_text)

        # Track link tokens
        if tok.type == "inline" and tok.children:
            for child in tok.children:
                if child.type == "link_open":
                    href = child.attrGet("href") or ""
                    # Only flag relative (non-http) links
                    if href and not href.startswith(("http://", "https://", "mailto:", "#")):
                        map_info = tok.map
                        line_no = (map_info[0] + 1) if map_info else None
                        skill.links.append((href, line_no))

        i += 1

    # Extract all word tokens from body text so ROO024 can match against
    # any dynamic slug set (built-in + config extra_mode_slugs) at rule time.
    # Storing all tokens avoids hardcoding any slug list in the parser.
    skill.body_mode_slug_refs = list(set(_WORD_TOKEN_RE.findall(body)))

    # Extract skill name references (backtick or bold words)
    refs = []
    for m in _SKILL_NAME_REF_RE.finditer(body):
        ref = m.group(1) or m.group(2)
        if ref:
            refs.append(ref.strip())
    skill.skill_name_refs = refs

    return skill
