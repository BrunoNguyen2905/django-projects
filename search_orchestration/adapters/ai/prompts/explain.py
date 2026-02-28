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


EXPLAIN_PROMPTS = {
    "plan_round": get_explain_prompt_plan_round(),
    "soundstripe_search": get_explain_prompt_soundstripe_search(),
    "record_debug": get_explain_prompt_record_debug(),
    "finish": get_explain_prompt_finish(),
}
