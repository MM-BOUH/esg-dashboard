"""
Retrieval functions for MongoDB (structured data) and ChromaDB (semantic search).
Each function returns a list of result dicts ready for context assembly.
"""

from __future__ import annotations

import re

from assistant.db.chroma import get_collection
from assistant.db.mongo import countries_col, suppliers_col

RISK_COLS = [
    "co2_risk",
    "corruption_risk",
    "forced_labor_risk",
    "water_stress_risk",
    "child_labor_risk",
]

INDICATOR_ALIASES: dict[str, str] = {
    "co2": "co2_risk",
    "carbon": "co2_risk",
    "emissions": "co2_risk",
    "co2 emissions": "co2_risk",
    "corruption": "corruption_risk",
    "cpi": "corruption_risk",
    "governance": "corruption_risk",
    "forced labor": "forced_labor_risk",
    "forced labour": "forced_labor_risk",
    "modern slavery": "forced_labor_risk",
    "slavery": "forced_labor_risk",
    "human trafficking": "forced_labor_risk",
    "water": "water_stress_risk",
    "water stress": "water_stress_risk",
    "water scarcity": "water_stress_risk",
    "child labor": "child_labor_risk",
    "child labour": "child_labor_risk",
    "child": "child_labor_risk",
}


def _resolve_indicator(text: str) -> str | None:
    """Return the canonical risk column name for a free-text indicator mention."""
    lowered = text.lower()
    for alias, col in sorted(INDICATOR_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in lowered:
            return col
    return None


# ---------------------------------------------------------------------------
# MongoDB retrieval
# ---------------------------------------------------------------------------

def get_all_suppliers() -> list[dict]:
    """Return all demo suppliers with their risk scores."""
    return list(
        suppliers_col().find(
            {},
            {"_id": 0, "supplier_id": 1, "name": 1, "material": 1,
             "country_name": 1, "cost_usd": 1, "indicators": 1, "overall_risk": 1},
        )
    )


def get_suppliers_ranked_by_indicator(indicator_col: str, limit: int = 10) -> list[dict]:
    """Return suppliers sorted descending by a specific risk indicator."""
    all_suppliers = get_all_suppliers()
    scored = []
    for s in all_suppliers:
        val = s.get("indicators", {}).get(indicator_col)
        if val is not None:
            scored.append({**s, "_sort_score": val})
    scored.sort(key=lambda x: x["_sort_score"], reverse=True)
    for s in scored:
        s.pop("_sort_score", None)
    return scored[:limit]


def get_country_data(country_name: str) -> dict | None:
    """Return one country doc by name (case-insensitive prefix match)."""
    pattern = re.compile(re.escape(country_name), re.IGNORECASE)
    doc = countries_col().find_one(
        {"country_name": {"$regex": pattern}},
        {"_id": 0},
    )
    return doc


def get_suppliers_for_countries(country_names: list[str]) -> list[dict]:
    """Return all suppliers sourced from any of the given countries."""
    patterns = [re.compile(re.escape(n), re.IGNORECASE) for n in country_names]
    query = {"country_name": {"$in": [p.pattern for p in patterns]}}
    # PyMongo does not support list of regex in $in directly, so we use $or
    query = {"$or": [{"country_name": {"$regex": p}} for p in patterns]}
    return list(
        suppliers_col().find(query, {"_id": 0})
    )


def retrieve_structured(query: str) -> list[dict]:
    """
    Decide what structured data to fetch based on the query text.
    Returns a list of result dicts tagged with a 'result_type' key.
    """
    indicator = _resolve_indicator(query)
    results = []

    # Country-specific lookup
    country_mentions = _extract_country_mentions(query)
    if country_mentions:
        for name in country_mentions:
            doc = get_country_data(name)
            if doc:
                results.append({"result_type": "country", **doc})
        suppliers = get_suppliers_for_countries(country_mentions)
        for s in suppliers:
            results.append({"result_type": "supplier", **s})

    # Indicator-ranked suppliers
    if indicator and not country_mentions:
        ranked = get_suppliers_ranked_by_indicator(indicator, limit=10)
        for s in ranked:
            results.append({"result_type": "supplier_ranked", **s})

    # Fallback: return all suppliers if nothing specific matched
    if not results:
        for s in get_all_suppliers():
            results.append({"result_type": "supplier", **s})

    return results


# ---------------------------------------------------------------------------
# ChromaDB retrieval
# ---------------------------------------------------------------------------

def retrieve_semantic(query: str, n_results: int = 5) -> list[dict]:
    """
    Semantic search over the methodology knowledge base.
    Returns list of dicts with 'document', 'source', 'indicator', 'url', 'chunk_index'.
    """
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    n = min(n_results, count)
    results = collection.query(query_texts=[query], n_results=n)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    output = []
    for doc, meta in zip(docs, metas):
        output.append({
            "document": doc,
            "source": meta.get("source", ""),
            "indicator": meta.get("indicator", ""),
            "url": meta.get("url", ""),
            "chunk_index": meta.get("chunk_index", 0),
        })
    return output


# ---------------------------------------------------------------------------
# Country mention extraction (simple heuristic)
# ---------------------------------------------------------------------------

_KNOWN_COUNTRIES = [
    "china", "india", "vietnam", "bangladesh", "malaysia", "indonesia",
    "taiwan", "brazil", "chile", "mexico", "philippines", "thailand",
    "singapore", "south korea", "democratic republic of congo", "congo",
    "united states", "usa", "germany", "france", "united kingdom", "uk",
    "japan", "australia", "canada", "nigeria", "ethiopia", "pakistan",
    "myanmar", "cambodia", "sri lanka", "turkey", "egypt", "morocco",
]

_COUNTRY_PATTERN = re.compile(
    "|".join(re.escape(c) for c in sorted(_KNOWN_COUNTRIES, key=len, reverse=True)),
    re.IGNORECASE,
)


def _extract_country_mentions(text: str) -> list[str]:
    matches = _COUNTRY_PATTERN.findall(text)
    seen = set()
    out = []
    for m in matches:
        key = m.lower()
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out
