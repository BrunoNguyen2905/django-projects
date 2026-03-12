"""Prompt template for music taxonomy selection (search filters)."""
from __future__ import annotations

import json
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import SystemMessagePromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate

from search_orchestration.adapters.ai.taxonomy import MUSIC_TAXONOMY, SFX_TAXONOMY


def get_selection_prompt(taxonomy: dict = MUSIC_TAXONOMY) -> ChatPromptTemplate:
    # Determine if this is music or SFX taxonomy
    is_sfx = taxonomy == SFX_TAXONOMY

    if is_sfx:
        system_content = (
            "You are an expert sound designer specializing in SFX (sound effects) classification.\n"
            "Your task is to analyze the user request and return taxonomy selections for Soundstripe search filters.\n\n"
            "IMPORTANT CONTEXT:\n"
            "- The downstream API uses a flat category filter: filter[categories]=id1,id2,id3\n"
            "- Soundstripe search works best with the MOST SPECIFIC relevant terms.\n"
            "- Parent categories and subcategories should NOT usually be selected together.\n"
            "- If a subcategory clearly matches the request, prefer the subcategory and omit its parent category.\n"
            "- Avoid combining multiple unrelated top-level branches unless the query truly requires it.\n"
            "- Keys in the output object are only for organizing the selection.\n"
            "- The actual search filter will be built mostly from the selected subcategory terms.\n"
            "- If the user explicitly names a main sound family and there is no exact subcategory match, include the parent category with an empty list.\n"
            "- Keep the dominant sound family even when supporting details are mapped to other branches.\n"
            "- Contextual details such as surface, environment, or material should not replace the main sound family.\n\n"
            "OUTPUT RULES (STRICT):\n"
            "- Return EXACTLY ONE JSON object.\n"
            f"- The object may include ONLY these keys: {', '.join(taxonomy.keys())}.\n"
            "- Each included key maps to a LIST of selected subcategory terms.\n"
            "- Values must be valid subcategories listed under that key.\n"
            "- An empty list means: keep this broad parent category because it is the dominant sound family.\n"
            "- Do NOT include a category name as a value.\n"
            "- Do NOT include duplicate terms anywhere in the object.\n"
            "- Do NOT select both a parent category and one of its subcategories unless the request clearly needs the broad parent as well.\n"
            "- Prefer the most specific matching subcategories over broad parent categories.\n"
            "- If the request spans multiple branches, prefer only the most relevant 1-2 branches.\n"
            "- The dominant sound family should appear first.\n"
            "- Supporting/contextual branches should appear after it.\n"
            "- Order keys from MOST RELEVANT to LEAST RELEVANT.\n"
            "- Within each key, order subcategories from MOST RELEVANT to LEAST RELEVANT.\n"
            "- Decide if the query is SIMPLE or COMPLEX:\n"
            "  * SIMPLE: one clear sound need or one main sound family.\n"
            "  * COMPLEX: multiple sound needs, multiple constraints, or layered production intent.\n"
            "- If SIMPLE: include 1-2 keys total and 0-2 subcategory values total.\n"
            "- If COMPLEX: include 1-3 keys total and 1-4 subcategory values total.\n"
            "- Prefer fewer terms overall.\n"
            "- Use ONLY terms that appear in the provided taxonomy JSON.\n"
            "- Output selections only: no prose, no code fences, no comments, no extra keys."
        )
    else:
        system_content = (
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

    system_msg = SystemMessagePromptTemplate.from_template(system_content)

    human_msg = HumanMessagePromptTemplate.from_template(
        "{instruction}\n\n"
        "User request:\n{user_text}\n\n"
        "Allowed taxonomies and terms (use only these):\n"
        "```json\n{taxonomy_json}\n```"
    )

    return ChatPromptTemplate.from_messages([system_msg, human_msg])


# def get_music_selection_prompt() -> ChatPromptTemplate:
#     """Get selection prompt for music taxonomy."""
#     return get_selection_prompt(MUSIC_TAXONOMY)


# def get_sfx_selection_prompt() -> ChatPromptTemplate:
#     """Get selection prompt for SFX taxonomy."""
#     return get_selection_prompt(SFX_TAXONOMY)


def get_selection_instruction(*, broaden: bool, prior_counts: List[int], taxonomy: dict) -> str:
    is_sfx = taxonomy == SFX_TAXONOMY
    instruction = "Select taxonomy terms that best match the request, following the output rules."
    if broaden:
        if is_sfx:
            instruction += (
                "\n\nBroaden the selection to increase results:"
                "\n- The previous selection returned too few or zero results."
                "\n- Broadening now takes priority over preserving all details of the original request."
                "\n- Aggressively simplify the selection."
                "\n- Keep ONLY the single strongest branch unless another branch is absolutely essential."
                "\n- Remove entire weaker branches before removing the strongest branch."
                "\n- Do NOT add new branches when broadening."
                "\n- Do NOT replace missing results with adjacent or creative interpretations."
                "\n- If multiple subcategories are selected under one key, keep only the single most important one."
                "\n- If the remaining subcategory is still too narrow, remove it and keep only the parent category."
                "\n- If the dominant sound family has no exact remaining subcategory, keep the parent category with an empty list."
                "\n- Do not drop the dominant sound family before dropping contextual branches."
                "\n- Prefer 1 broad parent category over several specific subcategories."
                "\n- Do NOT keep both a parent category and its child together unless absolutely necessary."
                "\n- The broadened result should usually be exactly one of these:"
                "\n  * 1 key with 1 subcategory"
                "\n  * 1 key with no subcategories"
                "\n- Identify the dominant sound family (the main sound the user is trying to find)."
                "\n- When broadening, keep the dominant branch and remove supporting branches."
                "\n- Supporting branches are contextual details or secondary sounds."
                "\n- If multiple branches exist, remove the least essential branch first."
                "\n- Broadening ladder:"
                "\n  1. Keep only the strongest key and its single strongest subcategory."
                "\n  2. Keep only the strongest key with no subcategories."
                "\n  3. Keep only the broadest matching parent category."
                "\n- Never broaden by adding more categories or more subcategories."
                "\n- Never increase the number of selected categories when broadening."
            )
        else:
            instruction += (
                "\n\nBroaden the selection to increase results:"
                "\n- Remove secondary constraints first (drop instrument/characteristic before genre/mood)"
                "\n- Use broader genre/mood terms"
                "\n- Keep it SIMPLE when broadening (0–1 term per key if possible)"
            )
        if prior_counts is not None:
            instruction += f"\nPrevious result counts: {prior_counts}"
    return instruction


# def get_music_selection_instruction(*, broaden: bool, prior_counts: List[int]) -> str:
#     """Get selection instruction for music taxonomy."""
#     return get_selection_instruction(broaden=broaden, prior_counts=prior_counts, is_sfx=False)


# def get_sfx_selection_instruction(*, broaden: bool, prior_counts: List[int]) -> str:
#     """Get selection instruction for SFX taxonomy."""
#     return get_selection_instruction(broaden=broaden, prior_counts=prior_counts, is_sfx=True)


# def create_selection_prompt_with_taxonomy(taxonomy: dict = MUSIC_TAXONOMY, *, broaden: bool, prior_counts: List[int]) -> ChatPromptTemplate:
#     """Create a complete selection prompt with taxonomy JSON and instruction."""
#     template = get_selection_prompt(taxonomy)
#     is_sfx = taxonomy == SFX_TAXONOMY
#     instruction = get_selection_instruction(
#         broaden=broaden, prior_counts=prior_counts, is_sfx=is_sfx)
#     taxonomy_json = json.dumps(taxonomy, indent=2)

#     return template.partial(
#         instruction=instruction,
#         taxonomy_json=taxonomy_json
#     )


# def create_music_selection_prompt(*, broaden: bool, prior_counts: List[int]) -> ChatPromptTemplate:
#     """Create selection prompt for music taxonomy."""
#     return create_selection_prompt_with_taxonomy(MUSIC_TAXONOMY, broaden=broaden, prior_counts=prior_counts)


# def create_sfx_selection_prompt(*, broaden: bool, prior_counts: List[int]) -> ChatPromptTemplate:
#     """Create selection prompt for SFX taxonomy."""
#     return create_selection_prompt_with_taxonomy(SFX_TAXONOMY, broaden=broaden, prior_counts=prior_counts)
