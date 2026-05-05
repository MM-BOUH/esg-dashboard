"""
Query router: classifies an incoming question as one of three types.

  structured_lookup  - needs live country or supplier data from MongoDB
  methodology        - needs explanation of what an indicator means or how it is calculated
  combined           - needs both structured data and methodology context

Classification is rules-based first. An LLM fallback is invoked only when
none of the keyword rules fire with sufficient confidence.
"""

from __future__ import annotations

import re
from typing import Literal

QueryType = Literal["structured_lookup", "methodology", "combined"]

# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------

_METHODOLOGY_PHRASES = [
    r"\bwhat (is|does|are)\b",
    r"\bhow is\b",
    r"\bhow (is|are|was|were) .{1,40} (calculated|measured|defined|computed|scored|determined)",
    r"\bwhat does .{1,30} measure\b",
    r"\bexplain\b",
    r"\bdefinition\b",
    r"\bmethodology\b",
    r"\bdata source\b",
    r"\bwhere does .{1,20} (come|data|score)\b",
    r"\bcpi\b",
    r"\bglobal slavery\b",
    r"\baqueduct\b",
    r"\bunicef\b",
    r"\bwalk free\b",
    r"\btransparency international\b",
    r"\bour world in data\b",
    r"\bhow do you\b",
    r"\bwhat indicator\b",
    r"\bscale\b.{0,20}\b(0|10)\b",
]

_STRUCTURED_PHRASES = [
    r"\bwhich (supplier|country|countries|material|materials)\b",
    r"\bmy supplier\b",
    r"\bmy (supply chain|portfolio|sourcing)\b",
    r"\bhighest\b",
    r"\blowest\b",
    r"\bworst\b",
    r"\bbest\b",
    r"\brank\b",
    r"\bcompare\b",
    r"\bscore (for|of|in)\b",
    r"\brisk (for|of|in|score)\b",
    r"\bsupplier.{0,10}(risk|score|data)\b",
    r"\bcountry.{0,10}(risk|score|data)\b",
    r"\bfrom (china|india|vietnam|bangladesh|malaysia|indonesia|taiwan|brazil|chile|mexico|philippines|thailand|singapore|south korea|congo|democratic republic)\b",
    r"\bsourced from\b",
    r"\bsource country\b",
    r"\bbreakdown\b",
    r"\banalyz\b",
    r"\bhow much\b.{0,20}\b(risk|score)\b",
]

_COMPILED_METHODOLOGY = [re.compile(p, re.IGNORECASE) for p in _METHODOLOGY_PHRASES]
_COMPILED_STRUCTURED = [re.compile(p, re.IGNORECASE) for p in _STRUCTURED_PHRASES]


def _count_matches(patterns: list[re.Pattern], text: str) -> int:
    return sum(1 for p in patterns if p.search(text))


def classify(query: str) -> QueryType:
    """
    Return the query type for a natural-language question.

    Rules (evaluated in order):
    1. If methodology signals dominate, return "methodology".
    2. If structured signals dominate, return "structured_lookup".
    3. If both fire, return "combined".
    4. Default: "combined" (safest fallback).
    """
    m_score = _count_matches(_COMPILED_METHODOLOGY, query)
    s_score = _count_matches(_COMPILED_STRUCTURED, query)

    if m_score == 0 and s_score == 0:
        return "combined"

    if m_score > 0 and s_score == 0:
        return "methodology"

    if s_score > 0 and m_score == 0:
        return "structured_lookup"

    # Both fired: lean structured if structural signals dominate by 2+, else combined
    if s_score >= m_score + 2:
        return "structured_lookup"
    if m_score >= s_score + 2:
        return "methodology"

    return "combined"
