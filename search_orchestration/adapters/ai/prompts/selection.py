"""Prompt template for music taxonomy selection (search filters)."""
from __future__ import annotations

from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import SystemMessagePromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate


def get_selection_instruction(
    *,
    broaden: bool,
    prior_counts: Optional[List[int]],
) -> str:
    """Build the instruction for the human message. System message holds the main rules; this adds context (and broaden hint when needed)."""
    instruction = "Follow the user's request using the allowed taxonomies below."
    if broaden:
        instruction += (
            "\n\nPrevious queries returned too few results."
            "\nGenerate broader selections by reducing the number of terms:"
            "\n- Use fewer terms than before (e.g. if you used 4 terms, use 2–3 now)"
            "\n- Prefer 2–3 total terms per selection; do not add more terms"
            "\n- Use broad genres/moods and avoid overly specific combinations"
        )
        if prior_counts is not None:
            instruction += f"\nPrevious result counts: {prior_counts}"
    return instruction


def get_selection_prompt() -> ChatPromptTemplate:
    """Get the prompt template for generating taxonomy selections from user text."""
    system_msg = SystemMessagePromptTemplate.from_template(
        "You are an expert music librarian specializing in audio track classification.\n"
        "Your task is to analyze user requests and return taxonomy selections.\n\n"
        "CRITICAL: Return between 1 and 5 selection objects. "
        "Simple queries need 1 selection; complex ones may use 2–5. Never more than 5.\n\n"
        "Each selection uses only the allowed taxonomies: genre, instrument, characteristic, mood. "
        "Each taxonomy has 0+ terms; max 5 terms total per selection. "
        "Use only terms that appear in the taxonomy JSON provided in the user message."
    )
    human_msg = HumanMessagePromptTemplate.from_template(
        "{instruction}\n\n"
        "User request:\n{user_text}\n\n"
        "Allowed taxonomies and terms (use only these):\n"
        "```json\n{taxonomy_json}\n```"
    )
    return ChatPromptTemplate.from_messages([system_msg, human_msg])
