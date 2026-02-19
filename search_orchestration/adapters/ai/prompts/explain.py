"""Node-specific prompts for user-facing search progress messages (1–3 sentences)."""
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import SystemMessagePromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate

from search_orchestration.adapters.ai.taxonomy import get_taxonomy_summary_for_prompts

_TAXONOMY_SUMMARY = get_taxonomy_summary_for_prompts(max_examples=None)

_CROSS_CHECK_RULES = (
    "Before you respond, cross-check: (1) Any filter term you mention MUST appear in the taxonomy list above. "
    "(2) Your explanation must stay aligned with what the user asked (user_text). "
    "(3) When filters_summary is given, only mention filter terms that appear in that filters_summary."
)

_HUMAN_TONE = (
    "Sound like a real person: natural, warm, concise. Short sentences. Use music-friendly language (vibe, feel, style, sound). "
    "Never output long lists like 'Genre: X; Instrument: Y; Characteristic: Z; Mood: W'. "
    "When mentioning filters, use at most 2–3 terms in a natural phrase. "
    "Do not use the word 'something' or vague phrases like 'things like'."
)

_EXPLAIN_SYSTEM = (
    "You are a helpful assistant explaining what is happening in the music search, step by step, "
    "in simple human language so the user can follow along. Write 1–3 short sentences. Be clear and friendly. "
    f"{_HUMAN_TONE} "
    "Our search uses only these filter categories and their allowed terms: "
    f"{_TAXONOMY_SUMMARY}. "
    f"{_CROSS_CHECK_RULES} "
    "Do not mention internal details like 'round', 'broaden', or JSON."
)


def get_explain_prompt_announce_start() -> ChatPromptTemplate:
    human_msg = HumanMessagePromptTemplate.from_template(
        "The user asked for: {user_text}\n\n"
        "We are at the very beginning. In 1–3 sentences, give a brief overview: "
        "we'll turn their request into search filters (genre, mood, instruments), search the catalog, "
        "and if we need more we'll widen the search and try again. Do not mention 'round' or 'broaden'."
    )
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM),
        human_msg,
    ])


def get_explain_prompt_generate_selections() -> ChatPromptTemplate:
    human_msg = HumanMessagePromptTemplate.from_template(
        "The user asked for: {user_text}\n"
        "Current step: we are converting their description into search filters. broaden={broaden}\n\n"
        "If broaden is False: Say we're turning their request into filters and we'll search. "
        "You may hint at the vibe with at most 1–2 terms from the taxonomy. Use tentative wording. "
        "If broaden is True: Say we're building broader filters to find more options. Do not list specific terms. "
        "Do not use 'something' or 'things like'. Use music words: vibe, feel, style."
    )
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM),
        human_msg,
    ])


def get_explain_prompt_validate_and_merge() -> ChatPromptTemplate:
    human_msg = HumanMessagePromptTemplate.from_template(
        "The user asked for: {user_text}\n"
        "Filters we're using: {filters_summary}\n\n"
        "In 1–3 short sentences, say we've converted their request into filters and we're searching the catalog now. "
        "Use at most 2–3 terms from {filters_summary} in a natural phrase. Do not use 'something' or 'things like'. "
        "Use ONLY terms from {filters_summary}."
    )
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM),
        human_msg,
    ])


def get_explain_prompt_soundstripe_search() -> ChatPromptTemplate:
    human_msg = HumanMessagePromptTemplate.from_template(
        "The user asked for: {user_text}\n"
        "Filters we used: {filters_summary}\n\n"
        "We found {songs_count} tracks; {new_songs_count} are new (added to their results).\n\n"
        "In 1–2 short sentences tell them we found {songs_count} tracks and added {new_songs_count} new ones. "
        "Use the exact numbers. Optionally add a brief phrase with at most 2–3 terms from {filters_summary}. "
        "Do not use 'something' or 'things like'."
    )
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM),
        human_msg,
    ])


def get_explain_prompt_record_debug() -> ChatPromptTemplate:
    human_msg = HumanMessagePromptTemplate.from_template(
        "The user asked for: {user_text}\n"
        "Filters we just used: {filters_summary}\n"
        "Tracks this round: {last_round_count}. Total so far: {total_results}. Target achieved: {target_achieved}. Will loop: {will_loop}.\n\n"
        "If target_achieved is True: Say we have enough tracks and we're presenting the results. "
        "If target_achieved is False and will_loop is True: Say we'll broaden the filters and fetch more tracks. "
        "If target_achieved is False and will_loop is False: Say this is what we found and we're presenting the results. "
        "Use at most 2–3 terms from {filters_summary} when mentioning filters. Do not use 'something' or 'things like'."
    )
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM),
        human_msg,
    ])


def get_explain_prompt_explain_strategy() -> ChatPromptTemplate:
    human_msg = HumanMessagePromptTemplate.from_template(
        "The user asked for: {user_text}\n"
        "We have {total_results} tracks so far; we're going to run the search again with broader filters.\n\n"
        "In 1–3 short sentences say we're running the search again to find more options, "
        "this time with broader filters, and we'll show them the new tracks. "
        "Do not say 'round', 'broaden', or 'loop'."
    )
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM),
        human_msg,
    ])


def get_explain_prompt_finish() -> ChatPromptTemplate:
    human_msg = HumanMessagePromptTemplate.from_template(
        "The user asked for: {user_text}\n"
        "Search is complete. We found {total_results} tracks.\n\n"
        "In one short sentence say search is complete and we're presenting the results."
    )
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM),
        human_msg,
    ])


def get_explain_prompt_plan_round() -> ChatPromptTemplate:
    """Single combined explain for plan_round: announce + explain_strategy + generate + validate in one message."""
    human_msg = HumanMessagePromptTemplate.from_template(
        "The user asked for: {user_text}\n"
        "We just completed the planning step: we turned their request into filters and merged them. "
        "is_first_round={is_first_round}, broaden={broaden}. Filters we're using: {filters_summary}\n\n"
        "Write one short paragraph (2–4 sentences) that combines:\n"
        "1) If is_first_round: briefly say we're starting their search, then that we've turned their request into filters. "
        "2) If not is_first_round: say we're running the search again with broader filters, then that we've got new filters. "
        "3) Mention the filters using at most 2–3 terms from {filters_summary} in a natural phrase (e.g. that Acoustic, Chill vibe). "
        "4) Say we're about to search the catalog with these filters. "
        "Keep it human and concise. Do not use 'something' or 'things like'. No long Category: Term lists."
    )
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM),
        human_msg,
    ])


def get_explain_prompt_for_node(node_name: str) -> ChatPromptTemplate:
    """Return the explain prompt template for the given graph node name."""
    prompts = {
        "announce_start": get_explain_prompt_announce_start,
        "generate_selections": get_explain_prompt_generate_selections,
        "validate_and_merge": get_explain_prompt_validate_and_merge,
        "soundstripe_search": get_explain_prompt_soundstripe_search,
        "record_debug": get_explain_prompt_record_debug,
        "explain_strategy": get_explain_prompt_explain_strategy,
        "finish": get_explain_prompt_finish,
        "plan_round": get_explain_prompt_plan_round,
    }
    fn = prompts.get(node_name)
    if not fn:
        raise ValueError(f"Unknown explain node: {node_name}. Known: {list(prompts)}")
    return fn()


def get_explain_prompt() -> ChatPromptTemplate:
    """Generic explain prompt (legacy). Prefer get_explain_prompt_for_node for node-specific messages."""
    system_msg = SystemMessagePromptTemplate.from_template(_EXPLAIN_SYSTEM)
    human_msg = HumanMessagePromptTemplate.from_template(
        "What the user asked for: {user_text}\n"
        "Current step: round {round_num}, broaden = {broaden}. Prior counts: {prior_counts}\n\n"
        "In 1–3 sentences, explain in plain language what we are doing or what we will do next."
    )
    return ChatPromptTemplate.from_messages([system_msg, human_msg])
