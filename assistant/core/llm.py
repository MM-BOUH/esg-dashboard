"""
LangChain LLM abstraction.
Returns a ChatAnthropic or ChatOpenAI instance based on LLM_PROVIDER env var.
The caller chains this with a prompt template: prompt | get_llm().
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from assistant.config import get_settings


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    settings = get_settings()

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )

    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=0.2,
        max_tokens=1024,
    )


def format_history(turns: list[dict]) -> str:
    """
    Convert stored conversation turns into a plain-text history string
    passed into the prompt template.
    """
    if not turns:
        return "(no prior conversation)"

    lines = []
    for turn in turns[-6:]:  # last 3 round-trips to stay within context budget
        lines.append(f"User: {turn.get('user_message', '')}")
        lines.append(f"Assistant: {turn.get('assistant_message', '')}")
    return "\n".join(lines)
