"""Routing simulator: rank skills by how well they match a natural-language query.

Two scoring backends are available:

Heuristic (default, no extra deps)
-----------------------------------
For each skill:
  1. Tokenise the skill's description into lowercase word tokens.
  2. Tokenise the query into lowercase word tokens.
  3. Compute a match score:
       - Exact token overlap (Jaccard-like): shared / (query_tokens | desc_tokens)
       - Bonus for each query token that is a substring of the description
       - Bonus for each query token that fuzzy-matches (SequenceMatcher ratio ≥ threshold)
         a description token
  4. Normalise to [0.0, 1.0] and sort descending.

Embedding (opt-in, requires sentence-transformers)
---------------------------------------------------
When use_embeddings=True is passed to simulate():
  - Encodes the query and all skill descriptions with a SentenceTransformer model.
  - Scores by cosine similarity between query embedding and each description embedding.
  - Falls back to heuristic if sentence-transformers is not installed.

The result is intentionally heuristic — it mirrors what a simple keyword-based
router would do, making it useful for spotting ambiguous or missing descriptions
without requiring any external model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from skill_lint.models import SkillFile

# ── constants ─────────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9-]*\b")

# Stop-words that carry no routing signal
_STOP_WORDS: frozenset[str] = frozenset(
    [
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "need", "dare",
        "ought", "used", "it", "its", "this", "that", "these", "those",
        "when", "where", "which", "who", "how", "what", "why", "use", "using",
        "you", "your", "we", "our", "they", "their", "any", "all", "not",
        "no", "so", "as", "if", "then", "than", "also", "more", "most",
    ]
)

DEFAULT_FUZZY_THRESHOLD = 0.75


# ── data classes ──────────────────────────────────────────────────────────────


@dataclass
class RouteMatch:
    """A single skill ranked against a query."""

    skill: SkillFile
    score: float          # 0.0 – 1.0
    matched_tokens: list[str] = field(default_factory=list)
    match_type: str = "none"  # "exact", "substring", "fuzzy", "none"

    @property
    def skill_name(self) -> str:
        return self.skill.name or str(self.skill.path)

    @property
    def description_preview(self) -> str:
        desc = self.skill.description or ""
        return desc[:120] + ("…" if len(desc) > 120 else "")

    def to_dict(self) -> dict:
        return {
            "skill": self.skill_name,
            "path": str(self.skill.path),
            "score": round(self.score, 4),
            "match_type": self.match_type,
            "matched_tokens": self.matched_tokens,
            "description_preview": self.description_preview,
        }


@dataclass
class SimulationResult:
    """Ranked list of skills for a given query."""

    query: str
    matches: list[RouteMatch]  # sorted descending by score

    @property
    def top_match(self) -> RouteMatch | None:
        return self.matches[0] if self.matches else None

    @property
    def is_ambiguous(self) -> bool:
        """True if the top two matches have scores within 10% of each other."""
        if len(self.matches) < 2:
            return False
        top, second = self.matches[0].score, self.matches[1].score
        return top > 0 and abs(top - second) / top < 0.10

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "is_ambiguous": self.is_ambiguous,
            "matches": [m.to_dict() for m in self.matches],
        }


# ── public API ────────────────────────────────────────────────────────────────

#: Default sentence-transformers model (small, fast, good quality)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def simulate(
    query: str,
    skills: list[SkillFile],
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    top_n: int = 5,
    use_embeddings: bool = False,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> SimulationResult:
    """Rank skills by how well they match the query.

    Args:
        query: Natural-language routing query.
        skills: List of parsed SkillFile objects.
        fuzzy_threshold: SequenceMatcher ratio threshold for fuzzy matching.
        top_n: Maximum number of results to return (0 = all).
        use_embeddings: If True, use sentence-transformers cosine similarity.
            Falls back to heuristic if the package is not installed.
        embedding_model: sentence-transformers model name (default: all-MiniLM-L6-v2).

    Returns:
        SimulationResult with matches sorted by score descending.
    """
    if use_embeddings:
        result = _simulate_embeddings(query, skills, top_n, embedding_model)
        if result is not None:
            return result
        # Fall through to heuristic if embeddings unavailable

    query_tokens = _tokenise(query)
    if not query_tokens:
        return SimulationResult(query=query, matches=[])

    matches: list[RouteMatch] = []
    for skill in skills:
        if not skill.description:
            matches.append(RouteMatch(skill=skill, score=0.0, match_type="none"))
            continue

        desc_tokens = _tokenise(skill.description)
        score, matched, match_type = _score(
            query_tokens, desc_tokens, skill.description.lower(), fuzzy_threshold
        )
        matches.append(
            RouteMatch(
                skill=skill,
                score=score,
                matched_tokens=matched,
                match_type=match_type,
            )
        )

    matches.sort(key=lambda m: m.score, reverse=True)
    if top_n > 0:
        matches = matches[:top_n]

    return SimulationResult(query=query, matches=matches)


def _simulate_embeddings(
    query: str,
    skills: list[SkillFile],
    top_n: int,
    model_name: str,
) -> SimulationResult | None:
    """Embedding-based simulation using sentence-transformers.

    Returns None if sentence-transformers is not installed (caller falls back
    to heuristic).
    """
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return None

    model = SentenceTransformer(model_name)

    descriptions = [skill.description or "" for skill in skills]
    all_texts = [query] + descriptions
    embeddings = model.encode(all_texts, convert_to_numpy=True, normalize_embeddings=True)

    query_emb = embeddings[0]
    desc_embs = embeddings[1:]

    matches: list[RouteMatch] = []
    for i, skill in enumerate(skills):
        # Cosine similarity (embeddings are L2-normalised → dot product = cosine)
        cos_sim = float(np.dot(query_emb, desc_embs[i]))
        score = max(0.0, min(1.0, (cos_sim + 1.0) / 2.0))  # map [-1,1] → [0,1]
        matches.append(
            RouteMatch(
                skill=skill,
                score=score,
                matched_tokens=[],
                match_type="embedding",
            )
        )

    matches.sort(key=lambda m: m.score, reverse=True)
    if top_n > 0:
        matches = matches[:top_n]

    return SimulationResult(query=query, matches=matches)


# ── helpers ───────────────────────────────────────────────────────────────────


def _tokenise(text: str) -> list[str]:
    """Lowercase, extract word tokens, remove stop-words."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP_WORDS]


def _score(
    query_tokens: list[str],
    desc_tokens: list[str],
    desc_lower: str,
    fuzzy_threshold: float,
) -> tuple[float, list[str], str]:
    """Return (score, matched_tokens, match_type)."""
    if not desc_tokens:
        return 0.0, [], "none"

    query_set = set(query_tokens)
    desc_set = set(desc_tokens)

    # 1. Exact token overlap
    exact = query_set & desc_set
    exact_score = len(exact) / len(query_set) if query_set else 0.0

    # 2. Substring bonus: query token appears anywhere in description text
    substring_hits = {t for t in query_set if t not in exact and t in desc_lower}
    substring_score = 0.5 * len(substring_hits) / len(query_set) if query_set else 0.0

    # 3. Fuzzy bonus: SequenceMatcher ratio ≥ threshold against any desc token
    fuzzy_hits: set[str] = set()
    for qt in query_set - exact - substring_hits:
        for dt in desc_set:
            ratio = SequenceMatcher(None, qt, dt).ratio()
            if ratio >= fuzzy_threshold:
                fuzzy_hits.add(qt)
                break
    fuzzy_score = 0.3 * len(fuzzy_hits) / len(query_set) if query_set else 0.0

    total = min(1.0, exact_score + substring_score + fuzzy_score)
    matched = sorted(exact | substring_hits | fuzzy_hits)

    if exact:
        match_type = "exact"
    elif substring_hits:
        match_type = "substring"
    elif fuzzy_hits:
        match_type = "fuzzy"
    else:
        match_type = "none"

    return total, matched, match_type
