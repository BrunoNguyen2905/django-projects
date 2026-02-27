from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer

from search_orchestration.adapters.ai.llms import (
    get_explain_llm_streaming,
    get_structured_selection_llm,
    get_structured_explain_llm,
)
from search_orchestration.adapters.ai.prompts import (
    get_selection_prompt,
    get_selection_instruction,
    get_explain_prompt_for_node,
)
from search_orchestration.adapters.ai.utils import merge_selection_into, song_to_context_item, format_filters_summary, validate_and_normalize_selections
from search_orchestration.adapters.ai.state import Taxonomy, Selection, SearchState
from search_orchestration.adapters.ai.taxonomy import MUSIC_TAXONOMY
from search_orchestration.adapters.soundstripe_adapter import soundstripe_search

# Defaults for search loop
DEFAULT_MIN_RESULTS = 20
DEFAULT_MAX_ROUNDS = 3


def generate_search_selections(
    user_text: str,
    *,
    broaden: bool,
    prior_counts: Optional[List[int]],
) -> List[Dict[str, Any]]:
    """
    Generate taxonomy selections from user text using structured LLM + prompt template.
    Returns a list of selection dicts (validated and normalized).
    """
    instruction = get_selection_instruction(
        broaden=broaden, prior_counts=prior_counts)
    taxonomy_json = json.dumps(MUSIC_TAXONOMY, ensure_ascii=False, indent=2)

    prompt = get_selection_prompt()
    messages = prompt.format_prompt(
        instruction=instruction,
        user_text=user_text,
        taxonomy_json=taxonomy_json,
    ).to_messages()

    structured_llm = get_structured_selection_llm()
    res = structured_llm.invoke(messages)

    raw: List[Dict[str, Any]] = [
        {k: v for k, v in item.model_dump().items() if v is not None}
        for item in res.selections
    ]
    return validate_and_normalize_selections(raw)


def explain_for_node(
    node_name: str, state: SearchState, *, extra: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a short user-facing explanation for the given graph node using node-specific prompts.
    extra: optional kwargs for nodes that need runtime values (e.g. soundstripe_search: songs_count, new_songs_count).
    """
    # Accept "node_xyz" (log prefix) or "xyz" (graph node name)
    key = node_name.replace("node_", "", 1) if node_name.startswith(
        "node_") else node_name
    user_text: str = state.get("user_text") or ""
    prompt = get_explain_prompt_for_node(key)
    extra = extra or {}
    # Use current-round merged_selection from extra when present (e.g. validate_and_merge computes it before state is updated)
    merged_selection = extra.get(
        "merged_selection") if "merged_selection" in extra else state.get("merged_selection")

    if key == "announce_start":
        messages = prompt.format_prompt(user_text=user_text).to_messages()
    elif key == "generate_selections":
        broaden = bool(state.get("round_idx", 0) > 0)
        messages = prompt.format_prompt(
            user_text=user_text, broaden=broaden).to_messages()
    elif key == "validate_and_merge":
        messages = prompt.format_prompt(
            user_text=user_text,
            filters_summary=format_filters_summary(merged_selection),
        ).to_messages()
    elif key == "soundstripe_search":
        messages = prompt.format_prompt(
            user_text=user_text,
            filters_summary=format_filters_summary(merged_selection),
            songs_count=extra.get("songs_count", 0),
            new_songs_count=extra.get("new_songs_count", 0),
        ).to_messages()
    elif key == "record_debug":
        results = state.get("results") or []
        min_results = int(state.get("min_results", DEFAULT_MIN_RESULTS))
        max_rounds = int(state.get("max_rounds", DEFAULT_MAX_ROUNDS))
        round_idx = int(state.get("round_idx", 0))
        total_results = len(results)
        target_achieved = total_results >= min_results
        will_loop = not target_achieved and (round_idx + 1 < max_rounds)
        messages = prompt.format_prompt(
            user_text=user_text,
            filters_summary=format_filters_summary(merged_selection),
            total_results=total_results,
            last_round_count=int(state.get("last_round_count") or 0),
            prior_counts_str=str(state.get("prior_counts") or []),
            min_results=min_results,
            target_achieved=target_achieved,
            will_loop=will_loop,
        ).to_messages()
    elif key == "explain_strategy":
        results = state.get("results") or []
        messages = prompt.format_prompt(
            user_text=user_text,
            total_results=len(results),
            prior_counts_str=str(state.get("prior_counts") or []),
        ).to_messages()
    elif key == "finish":
        results = state.get("results") or []
        messages = prompt.format_prompt(
            user_text=user_text,
            total_results=len(results),
        ).to_messages()
    elif key == "plan_round":
        messages = prompt.format_prompt(
            user_text=user_text,
            broaden=bool(state.get("round_idx", 0) > 0),
            filters_summary=format_filters_summary(
                extra.get("merged_selection") or merged_selection),
            is_first_round=bool(state.get("round_idx", 0) == 0),
        ).to_messages()
    else:
        messages = prompt.format_prompt(user_text=user_text).to_messages()

    # structured_llm = get_structured_explain_llm()
    # res = structured_llm.invoke(messages)
    # return (res.content or "").strip()
    llm = get_explain_llm_streaming()
    parts: List[str] = []
    for chunk in llm.stream(messages):
        token = getattr(chunk, "content", None)
        if token:
            parts.append(token)

    return "".join(parts).strip()


# -----------------------------
# LangGraph State + Graph
# -----------------------------

StreamWriter = Callable[[Dict[str, Any]], None]


def _emit(writer: StreamWriter, *, type_: str, **payload: Any) -> None:
    """Helper to stream structured custom events (stream_mode='custom')."""
    writer({"type": type_, **payload})


def _emit_explanation(
    writer: StreamWriter,
    state: SearchState,
    fallback: str = "",
    node: str = "",
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit an AI-generated explanation for the given node as log; use fallback if empty.
    extra: passed to explain_for_node for nodes that need runtime values (e.g. soundstripe_search counts).
    """
    explanation = explain_for_node(node, state, extra=extra or {})
    msg = (explanation or fallback).strip()

    _emit(writer, type_="log", message=msg)


def node_plan_round(state: SearchState) -> Dict[str, Any]:
    writer: StreamWriter = get_stream_writer()

    user_text: str = state.get("user_text") or ""
    round_idx = int(state.get("round_idx", 0))
    is_first_round = (round_idx == 0)
    broaden = bool(round_idx > 0)
    if is_first_round:
        # Emit a fast log immediately (no LLM) to reduce perceived latency
        _emit(writer, type_="log",
              message=f"Starting search for: {user_text or '(no query)'}")

        # Initialize fields (keep same defaults you had)
        state = {
            **state,
            "min_results": state.get("min_results", DEFAULT_MIN_RESULTS),
            "max_rounds": state.get("max_rounds", DEFAULT_MAX_ROUNDS),
            "round_idx": 0,
            "prior_counts": [],
            "results": [],
            "seen_ids": [],
        }

    # (Optional) quick non-LLM log so user sees movement while LLM runs
    _emit(writer, type_="log", message="Planning your search filters…")

    try:
        valid = generate_search_selections(
            user_text,
            broaden=broaden,
            prior_counts=state.get("prior_counts") or [],
        )
    except Exception as e:
        _emit(writer, type_="log", message=f"Selection validation error: {e}")
        valid = []

    merged: Selection = {}
    for sel in valid:
        merge_selection_into(merged, sel)

    _emit_explanation(
        writer,
        state,
        fallback="Locked in your filters. Searching the catalog now…",
        node="node_plan_round",
        extra={
            "merged_selection": merged,
        },
    )

    return {
        "merged_selection": merged,
    }


def node_soundstripe_search(state: SearchState) -> Dict[str, Any]:
    writer = get_stream_writer()
    merged: Selection = state.get("merged_selection") or {}
    songs: List[Dict[str, Any]] = soundstripe_search(merged)

    results: List[Dict[str, Any]] = list(state.get("results") or [])
    seen_ids_set: Set[str] = set(state.get("seen_ids") or [])

    new_songs: List[Dict[str, Any]] = []
    for song in songs:
        sid = str(song.get("id") or "")
        if not sid or sid in seen_ids_set:
            continue
        seen_ids_set.add(sid)
        results.append(song)
        new_songs.append(song)

    _emit_explanation(
        writer,
        state,
        fallback=f"Found {len(songs)} tracks; {len(new_songs)} new added to your results.",
        node="node_soundstripe_search",
        extra={"songs_count": len(songs), "new_songs_count": len(new_songs)},
    )

    if new_songs:
        _emit(
            writer,
            type_="results",
            items=[song_to_context_item(s) for s in new_songs],
        )
        n = len(new_songs)
        _emit(writer, type_="log",
              message=f"Found {n} new track{'s' if n != 1 else ''}.")

    return {
        "results": results,
        "seen_ids": list(seen_ids_set),  # JSON-safe
        "last_round_count": len(songs),
    }


def node_record_debug(state: SearchState) -> Dict[str, Any]:
    writer = get_stream_writer()
    round_idx = int(state.get("round_idx", 0))
    total_results = len(state.get("results") or [])
    min_results = int(state.get("min_results", DEFAULT_MIN_RESULTS))
    last_round_count = int(state.get("last_round_count", 0))
    max_rounds = int(state.get("max_rounds", DEFAULT_MAX_ROUNDS))
    target_achieved = total_results >= min_results
    will_loop = not target_achieved and (round_idx + 1 < max_rounds)
    if target_achieved:
        fallback = f"We have enough tracks ({total_results}). Presenting your results."
    elif will_loop:
        fallback = "We'll broaden the filters and fetch more tracks."
    else:
        fallback = f"This is the total we managed to find ({total_results} tracks). Presenting your results."
    _emit_explanation(writer, state, fallback=fallback,
                      node="node_record_debug")

    # When we're about to stop, emit a clear wrap-up so the user sees "we have enough" before "Search complete"
    if total_results >= min_results:
        _emit(
            writer,
            type_="log",
            message="We have enough tracks that match your request. Presenting your results.",
        )
    elif round_idx + 1 >= max_rounds:
        _emit(
            writer,
            type_="log",
            message="We've completed the search with the tracks we found. Here are your results.",
        )
    prior = list(state.get("prior_counts") or [])
    prior.append(last_round_count)
    return {
        "prior_counts": prior,
        "round_idx": round_idx + 1,
    }


def _should_continue(state: SearchState) -> str:
    total_results = len(state.get("results") or [])
    min_results = int(state.get("min_results", DEFAULT_MIN_RESULTS))
    round_idx = int(state.get("round_idx"))
    max_rounds = int(state.get("max_rounds", DEFAULT_MAX_ROUNDS))

    if total_results >= min_results:
        return "finish"
    if round_idx >= max_rounds:
        return "finish"
    return "loop"


def node_finish(state: SearchState) -> Dict[str, Any]:
    writer = get_stream_writer()
    total_results = len(state.get("results") or [])
    _emit_explanation(
        writer, state,
        fallback=f"Search complete. We found {total_results} tracks for you.",
        node="node_finish"
    )


def build_search_graph() -> Any:
    g: StateGraph[SearchState] = StateGraph(SearchState)

    # New combined node
    g.add_node("plan_round", node_plan_round)

    g.add_node("soundstripe_search", node_soundstripe_search)
    g.add_node("record_debug", node_record_debug)
    g.add_node("finish", node_finish)

    # Flow
    g.add_edge(START, "plan_round")
    g.add_edge("plan_round", "soundstripe_search")
    g.add_edge("soundstripe_search", "record_debug")

    g.add_conditional_edges(
        "record_debug",
        _should_continue,
        {
            "loop": "plan_round",
            "finish": "finish",
        },
    )

    g.add_edge("finish", END)
    return g.compile()


def stream_orchestrated_search(
    *,
    user_text: str,
    min_results: int = DEFAULT_MIN_RESULTS,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    stream_mode: Tuple[str, ...] = ("custom", "messages", "updates"),
) -> Generator[Tuple[str, Any], None, None]:
    """
    Stream the search graph for Django SSE views.

    Yields (mode, chunk) where:
      - mode == "custom": log/results events
      - mode == "messages": LLM token streaming
      - mode == "updates": state deltas per node
    """
    graph = build_search_graph()
    inputs: SearchState = {
        "user_text": user_text,
        "min_results": min_results,
        "max_rounds": max_rounds,
    }
    for mode, chunk in graph.stream(inputs, stream_mode=list(stream_mode)):
        yield mode, chunk
