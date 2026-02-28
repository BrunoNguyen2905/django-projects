"""Prompt template for music taxonomy selection (search filters)."""
from __future__ import annotations

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import SystemMessagePromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate


def get_selection_prompt() -> ChatPromptTemplate:
    system_msg = SystemMessagePromptTemplate.from_template(
        "You are an expert music librarian specializing in audio track classification.\n"
        "Your task is to analyze the user request and return taxonomy selections.\n\n"
        "OUTPUT RULES (STRICT):\n"
        "- Return EXACTLY ONE selection object.\n"
        "- The selection object may include ONLY these keys: genre, instrument, characteristic, mood.\n"
        "- Each key maps to a LIST of terms.\n"
        "- Decide if the query is SIMPLE or COMPLEX:\n"
        "  * SIMPLE: clear/short request with 1 main vibe (e.g., one genre + one mood).\n"
        "  * COMPLEX: multiple constraints, comparisons, multiple vibes, or specific production needs.\n"
        "- If SIMPLE: choose 1 term per key.\n"
        "- If COMPLEX: choose 1–3 terms per key.\n"
        "- Prefer fewer terms overall. Use instrument/characteristic only if clearly implied.\n"
        "- Do NOT include duplicates within a key.\n"
        "- Use ONLY terms that appear in the provided taxonomy JSON.\n"
        "- Output selections only; no prose, no code fences, no extra keys."
    )

    human_msg = HumanMessagePromptTemplate.from_template(
        "{instruction}\n\n"
        "User request:\n{user_text}\n\n"
        "Allowed taxonomies and terms (use only these):\n"
        "```json\n{taxonomy_json}\n```"
    )

    return ChatPromptTemplate.from_messages([system_msg, human_msg])


def get_selection_instruction(*, broaden: bool, prior_counts: List[int]) -> str:
    instruction = "Select taxonomy terms that best match the request, following the output rules."
    if broaden:
        instruction += (
            "\n\nBroaden the selection to increase results:"
            "\n- Remove secondary constraints first (drop instrument/characteristic before genre/mood)"
            "\n- Use broader genre/mood terms"
            "\n- Keep it SIMPLE when broadening (0–1 term per key if possible)"
        )
        if prior_counts is not None:
            instruction += f"\nPrevious result counts: {prior_counts}"
    return instruction
