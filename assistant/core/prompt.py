"""
LangChain prompt templates for each query type.
Kept minimal: one system template and one human template per query type.
"""

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_BASE = (
    "You are a concise ESG supply chain risk analyst assistant. "
    "You have access to ESG risk scores for 214 countries across five indicators: "
    "CO2 Emissions, Corruption, Water Stress, Forced Labor, and Child Labor. "
    "All scores are normalized to a 0-10 scale where 10 is highest risk. "
    "Answer factually using only the context provided. "
    "If the context does not contain enough information, say so clearly. "
    "Do not invent data. "
    "Cite sources by name when referring to specific scores or methodology. "
    "Keep answers under 300 words unless a comparison table is needed."
)

_STRUCTURED_HUMAN = (
    "Context (supplier and country data):\n{context}\n\n"
    "Conversation so far:\n{history}\n\n"
    "Question: {query}"
)

_METHODOLOGY_HUMAN = (
    "Context (methodology and background):\n{context}\n\n"
    "Conversation so far:\n{history}\n\n"
    "Question: {query}"
)

_COMBINED_HUMAN = (
    "Context (supplier data and methodology):\n{context}\n\n"
    "Conversation so far:\n{history}\n\n"
    "Question: {query}"
)

STRUCTURED_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_BASE),
    ("human", _STRUCTURED_HUMAN),
])

METHODOLOGY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_BASE),
    ("human", _METHODOLOGY_HUMAN),
])

COMBINED_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_BASE),
    ("human", _COMBINED_HUMAN),
])

PROMPT_MAP = {
    "structured_lookup": STRUCTURED_PROMPT,
    "methodology": METHODOLOGY_PROMPT,
    "combined": COMBINED_PROMPT,
}
