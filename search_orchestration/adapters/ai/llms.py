from django.conf import settings
from langchain_openai import ChatOpenAI

from search_orchestration.adapters.ai.schemas import (
    ExplainResponse,
    SearchSelectionsResponse,
)


def get_openai_api_key():
    # ApiKey.objects.get(provider='openai', org='CFE)
    return settings.OPENAI_API_KEY


def get_openai_model(model="gpt-5-nano", temperature=0.1, max_retries=2, streaming=False, max_tokens=1000, reasoning_effort="minimal", text_verbosity="low"):
    if model is None:
        model = "gpt-5-nano"
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_retries=max_retries,
        streaming=streaming,
        api_key=get_openai_api_key(),
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        verbosity=text_verbosity
    )


# Lazy-initialized structured LLMs (with_structured_output; typically non-streaming)
_structured_selection_llm = None
_structured_explain_llm = None


def get_structured_selection_llm():
    """LLM bound to SearchSelectionsResponse for taxonomy selection generation."""
    global _structured_selection_llm
    if _structured_selection_llm is None:
        base = get_openai_model(streaming=False, max_tokens=1000, reasoning_effort="minimal", text_verbosity="low")
        _structured_selection_llm = base.with_structured_output(SearchSelectionsResponse)
    return _structured_selection_llm


def get_structured_explain_llm():
    """LLM bound to ExplainResponse for user-facing strategy explanations."""
    global _structured_explain_llm
    if _structured_explain_llm is None:
        base = get_openai_model(streaming=True, max_tokens=1000, reasoning_effort="low", text_verbosity="low")
        _structured_explain_llm = base.with_structured_output(ExplainResponse)
    return _structured_explain_llm

def get_explain_llm_streaming():
    # NOTE: do NOT cache globally if you want per-request callbacks / streaming handlers
    return get_openai_model(streaming=True)  # <- streaming on