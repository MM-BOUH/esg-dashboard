"""
Context assembly: merges structured (MongoDB) and semantic (ChromaDB) results
into a single ranked text block and extracts Citation objects.
"""

from __future__ import annotations

from assistant.models.schemas import Citation

RISK_LABEL: dict[str, str] = {
    "co2_risk": "CO2 Emissions",
    "corruption_risk": "Corruption",
    "forced_labor_risk": "Forced Labor",
    "water_stress_risk": "Water Stress",
    "child_labor_risk": "Child Labor",
}

SOURCE_META: dict[str, dict] = {
    "CO2 Emissions": {"source": "Our World in Data / Global Carbon Project", "url": "https://ourworldindata.org/co2-emissions"},
    "Corruption": {"source": "Transparency International CPI 2025", "url": "https://www.transparency.org/en/cpi"},
    "Forced Labor": {"source": "Walk Free Global Slavery Index 2023", "url": "https://www.walkfree.org/global-slavery-index/"},
    "Water Stress": {"source": "WRI Aqueduct 4.0", "url": "https://www.wri.org/aqueduct"},
    "Child Labor": {"source": "UNICEF Jun 2025", "url": "https://data.unicef.org/topic/child-protection/child-labour/"},
}


def _format_supplier(doc: dict) -> str:
    indicators = doc.get("indicators", {})
    lines = [
        f"Supplier: {doc.get('name', 'N/A')} | Material: {doc.get('material', 'N/A')}",
        f"  Country: {doc.get('country_name', 'N/A')} | Cost: ${doc.get('cost_usd', 0):,.0f}",
        f"  Overall risk: {doc.get('overall_risk', 'N/A')}/10",
    ]
    if indicators:
        scores = ", ".join(
            f"{RISK_LABEL.get(k, k)}: {v}"
            for k, v in indicators.items()
            if v is not None
        )
        lines.append(f"  Scores: {scores}")
    return "\n".join(lines)


def _format_country(doc: dict) -> str:
    indicators = doc.get("indicators", {})
    lines = [
        f"Country: {doc.get('country_name', 'N/A')} ({doc.get('country_code', '')})",
        f"  Overall risk: {doc.get('overall_risk', 'N/A')}/10",
    ]
    if indicators:
        scores = ", ".join(
            f"{RISK_LABEL.get(k, k)}: {v}"
            for k, v in indicators.items()
            if v is not None
        )
        lines.append(f"  Scores: {scores}")
    return "\n".join(lines)


def assemble_context(
    structured_results: list[dict],
    semantic_results: list[dict],
    max_semantic_chars: int = 3000,
) -> tuple[str, list[Citation]]:
    """
    Build a context string and a deduplicated list of Citations.

    Returns (context_text, citations).
    """
    parts: list[str] = []
    citations: list[Citation] = []
    seen_sources: set[str] = set()

    # --- Structured section ---
    if structured_results:
        supplier_blocks = []
        country_blocks = []

        for doc in structured_results:
            rtype = doc.get("result_type", "")
            if rtype in ("supplier", "supplier_ranked"):
                supplier_blocks.append(_format_supplier(doc))
            elif rtype == "country":
                country_blocks.append(_format_country(doc))

        if country_blocks:
            parts.append("=== Country Data ===\n" + "\n\n".join(country_blocks))

        if supplier_blocks:
            parts.append("=== Supplier Data ===\n" + "\n\n".join(supplier_blocks))

        # Add one citation per indicator present in the results
        indicators_seen: set[str] = set()
        for doc in structured_results:
            for col in doc.get("indicators", {}).keys():
                label = RISK_LABEL.get(col)
                if label and label not in indicators_seen:
                    indicators_seen.add(label)
                    meta = SOURCE_META.get(label, {})
                    cit_key = meta.get("source", label)
                    if cit_key not in seen_sources:
                        seen_sources.add(cit_key)
                        citations.append(
                            Citation(
                                source=meta.get("source", label),
                                indicator=label,
                                url=meta.get("url"),
                            )
                        )

    # --- Semantic section ---
    if semantic_results:
        semantic_text_parts = []
        char_budget = max_semantic_chars

        for chunk in semantic_results:
            doc_text = chunk.get("document", "")
            if len(doc_text) > char_budget:
                doc_text = doc_text[:char_budget] + "..."
                char_budget = 0
            else:
                char_budget -= len(doc_text)

            source = chunk.get("source", "")
            indicator = chunk.get("indicator", "")
            url = chunk.get("url", "")
            chunk_index = chunk.get("chunk_index", 0)

            header = f"[{source} - {indicator}]" if indicator else f"[{source}]"
            semantic_text_parts.append(f"{header}\n{doc_text}")

            cit_key = f"{source}:{chunk_index}"
            if cit_key not in seen_sources:
                seen_sources.add(cit_key)
                citations.append(
                    Citation(
                        source=source,
                        indicator=indicator or None,
                        url=url or None,
                        chunk_index=chunk_index,
                    )
                )

            if char_budget <= 0:
                break

        parts.append("=== Methodology / Background ===\n" + "\n\n".join(semantic_text_parts))

    context_text = "\n\n".join(parts)
    return context_text, citations
