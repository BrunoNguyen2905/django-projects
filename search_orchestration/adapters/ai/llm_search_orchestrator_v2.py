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
from search_orchestration.adapters.ai.utils import song_to_context_item, format_filters_summary
from search_orchestration.adapters.ai.state import Taxonomy, Selection, SearchState
from search_orchestration.adapters.ai.taxonomy import MUSIC_TAXONOMY
from search_orchestration.adapters.soundstripe_adapter import soundstripe_search

# Defaults for search loop
DEFAULT_MIN_RESULTS = 20
DEFAULT_MAX_ROUNDS = 3
MAX_SELECTIONS = 5
MAX_TERMS_PER_SELECTION = 5


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
        broaden = bool(state.get("broaden", False))
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
            broaden=extra.get("broaden", int(state.get("round_idx", 0)) > 0),
            filters_summary=format_filters_summary(
                extra.get("merged_selection") or merged_selection),
            is_first_round=extra.get("is_first_round", int(
                state.get("round_idx", 0)) == 0),
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


@dataclass
class SearchDebug:
    rounds: List[Dict[str, Any]]


def _allowed_terms_set(taxonomy: Taxonomy) -> Dict[str, Set[str]]:
    return {k: set(v) for k, v in taxonomy.items()}


def _merge_selection_into(target: Selection, source: Selection) -> None:
    """Merge source selection into target (no duplicate terms per category)."""
    for category, values in source.items():
        if category not in target:
            target[category] = []
        for v in values:
            if v and v not in target[category]:
                target[category].append(v)


def _dedupe_keep_order(terms: List[str]) -> List[str]:
    """Return unique terms preserving first occurrence order."""
    seen: Set[str] = set()
    return [t for t in terms if t not in seen and not seen.add(t)]


def validate_and_normalize_selections(
    raw: Any,
    *,
    max_terms_total: int = MAX_TERMS_PER_SELECTION,
) -> List[Selection]:
    allowed_keys: Set[str] = set(MUSIC_TAXONOMY.keys())
    allowed_terms: Dict[str, Set[str]] = _allowed_terms_set(MUSIC_TAXONOMY)

    if not isinstance(raw, list):
        raise ValueError("LLM output must be a JSON list.")
    if len(raw) == 0:
        raise ValueError("LLM output must contain at least 1 selection.")
    if len(raw) > MAX_SELECTIONS:
        raise ValueError(
            f"LLM output contains too many selections ({len(raw)}), expected max {MAX_SELECTIONS}."
        )

    normalized: List[Selection] = []
    priority_keys = ["genre", "mood", "characteristic", "instrument"]

    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each selection must be an object.")

        clean: Selection = {}
        for k, v in item.items():
            if k not in allowed_keys or not isinstance(v, list):
                continue
            terms = [t for t in v if isinstance(
                t, str) and t in allowed_terms.get(k, set())]
            if terms:
                clean[k] = _dedupe_keep_order(terms)

        total_terms = sum(len(v) for v in clean.values())
        if total_terms > max_terms_total:
            trimmed: Selection = {}
            remaining = max_terms_total
            for k in priority_keys:
                if k in clean and remaining > 0:
                    take = clean[k][:remaining]
                    if take:
                        trimmed[k] = take
                        remaining -= len(take)
            clean = trimmed

        normalized.append(clean)

    return normalized


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
    # _emit(writer, type_="log", message=f"{node}: {msg}" if node else msg)
    _emit(writer, type_="log", message=msg)


def node_plan_round(state: SearchState) -> Dict[str, Any]:
    writer: StreamWriter = get_stream_writer()

    user_text: str = state.get("user_text") or ""
    # If this is the first time we run, initialize state (what announce_start used to do)
    initialized = bool(state.get("initialized", False))
    if not initialized:
        # Emit a fast log immediately (no LLM) to reduce perceived latency
        _emit(writer, type_="log",
              message=f"Starting search for: {user_text or '(no query)'}")

        # Initialize fields (keep same defaults you had)
        state = {
            **state,
            "min_results": state.get("min_results", DEFAULT_MIN_RESULTS),
            "max_rounds": state.get("max_rounds", DEFAULT_MAX_ROUNDS),
            "round_idx": 0,
            "broaden": False,
            "prior_counts": [],
            "results": [],
            "seen_ids": [],
            "debug_rounds": [],
            "done": False,
            "stop_reason": None,
            "initialized": True,
        }

    round_idx = int(state.get("round_idx", 0))
    broaden = bool(round_idx > 0)
    is_first_round = (round_idx == 0)

    # (Optional) quick non-LLM log so user sees movement while LLM runs
    _emit(writer, type_="log", message="Planning your search filters…")

    # 1) Generate selections (blocking structured LLM call)
    raw = generate_search_selections(
        user_text,
        broaden=broaden,
        prior_counts=state.get("prior_counts") or [],
    )

    # 2) Validate + merge (same logic as your validate_and_merge node)
    try:
        valid = [s for s in validate_and_normalize_selections(raw) if s]
    except Exception as e:
        _emit(writer, type_="log", message=f"Selection validation error: {e}")
        valid = []

    merged: Selection = {}
    for sel in valid:
        _merge_selection_into(merged, sel)

    # 3) One combined explanation (uses your get_explain_prompt_plan_round)
    _emit_explanation(
        writer,
        state,
        fallback="Locked in your filters. Searching the catalog now…",
        node="node_plan_round",
        extra={
            "merged_selection": merged,
            "broaden": broaden,
            "is_first_round": is_first_round,
        },
    )

    return {
        "initialized": True,
        "broaden": broaden,
        "selections_raw": raw,
        "selections_valid": valid,
        "merged_selection": merged,
    }

# def node_announce_start(state: SearchState) -> Dict[str, Any]:
#     writer: StreamWriter = get_stream_writer()
#     user_text: str = state.get("user_text") or ""
#     # explanation = explain_for_node("announce_start", state)
#     fallback = f"Starting search for: {user_text or '(no query)'}"
#     # _emit(
#     #     writer,
#     #     type_="log",
#     #     message=f"node_announce_start: {(explanation or fallback).strip()}",
#     # )
#     _emit_explanation(writer, state, fallback=fallback, node="node_announce_start")
#     return {
#         "user_text": user_text,
#         "min_results": state.get("min_results", DEFAULT_MIN_RESULTS),
#         "max_rounds": state.get("max_rounds", DEFAULT_MAX_ROUNDS),
#         "round_idx": 0,
#         "broaden": False,
#         "prior_counts": None,
#         "results": [],
#         "seen_ids": [],  # JSON-safe
#         "debug_rounds": [],
#         "done": False,
#         "stop_reason": None,
#     }


# def node_explain_strategy(state: SearchState) -> Dict[str, Any]:
#     """Emit AI-generated explanation: we're rerunning the search process with broader filters (loop)."""
#     writer = get_stream_writer()
#     total = len(state.get("results") or [])
#     explanation = explain_for_node("explain_strategy", state)
#     fallback = (
#         f"We're running the search again with broader filters to find more tracks (you have {total} so far)."
#     )
#     _emit(
#         writer,
#         type_="log",
#         message=f"node_explain_strategy: {(explanation or fallback).strip()}",
#     )
#     return {"explanation": explanation}


# def node_generate_selections(state: SearchState) -> Dict[str, Any]:
#     writer = get_stream_writer()
#     round_idx = int(state.get("round_idx", 0))
#     broaden = bool(round_idx > 0)
#     user_text = state.get("user_text") or ""

#     _emit_explanation(writer, state, fallback="Choosing the right genres and moods for your request…", node="node_generate_selections")
#     # explain_for_node("generate_selections", state)
#     raw = generate_search_selections(
#         user_text,
#         broaden=broaden,
#         prior_counts=state.get("prior_counts"),
#     )
#     return {"broaden": broaden, "selections_raw": raw}


# def node_validate_and_merge(state: SearchState) -> Dict[str, Any]:
#     writer = get_stream_writer()

#     raw = state.get("selections_raw", [])
#     try:
#         valid = [s for s in validate_and_normalize_selections(raw) if s]
#     except Exception as e:
#         _emit(writer, type_="log", message=f"Selection validation error: {e}")
#         valid = []

#     merged: Selection = {}
#     for sel in valid:
#         _merge_selection_into(merged, sel)

#     # Explain using this round's merged filters (state not updated until we return)
#     # explain_for_node("validate_and_merge", state, extra={"merged_selection": merged})
#     _emit_explanation(writer, state, fallback="Validating and merging selections…", node="node_validate_and_merge", extra={"merged_selection": merged})

#     return {"selections_valid": valid, "merged_selection": merged}


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
    # explain_for_node("soundstripe_search", state, extra={"songs_count": len(songs), "new_songs_count": len(new_songs)})

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
    broaden = bool(state.get("broaden", False))
    prior_counts = state.get("prior_counts")

    debug_rounds: List[Dict[str, Any]] = list(state.get("debug_rounds") or [])
    entry: Dict[str, Any] = {
        "round": round_idx + 1,
        "broaden": broaden,
        "selections_generated": len(state.get("selections_valid") or []),
        "round_results": last_round_count,
        "total_results": total_results,
        "target_achieved": total_results >= min_results,
        "prior_counts": prior_counts,
    }
    debug_rounds.append(entry)

    # Emit human-language explanation: enough tracks, or will loop, or no more rounds
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
    # explain_for_node("record_debug", state)
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
        "debug_rounds": debug_rounds,
        "prior_counts": prior,
        "round_idx": round_idx + 1,
    }


def _should_continue(state: SearchState) -> str:
    total_results = len(state.get("results") or [])
    min_results = int(state.get("min_results", DEFAULT_MIN_RESULTS))
    round_idx = int(state.get("round_idx", 0))
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
    # explain_for_node("finish", state)
    return {"done": True}


# def build_search_graph() -> Any:
#     """
#     Build & compile the LangGraph StateGraph for the search agent.

#     Stream modes:
#       - custom: progress logs + result batches
#       - messages: LLM tokens (explanation + selection)
#       - updates: state deltas per node (JSON-safe)
#     """
#     g: StateGraph[SearchState] = StateGraph(SearchState)

#     g.add_node("announce_start", node_announce_start)
#     g.add_node("explain_strategy", node_explain_strategy)
#     g.add_node("generate_selections", node_generate_selections)
#     g.add_node("validate_and_merge", node_validate_and_merge)
#     g.add_node("soundstripe_search", node_soundstripe_search)
#     g.add_node("record_debug", node_record_debug)
#     g.add_node("finish", node_finish)
#     # Combined node: announce_start + explain_strategy + generate_selections + validate_and_merge (optional path)
#     # g.add_node("plan_round", node_plan_round)

#     g.add_edge(START, "announce_start")
#     g.add_edge("announce_start", "generate_selections")
#     g.add_edge("generate_selections", "validate_and_merge")
#     # g.add_edge(START, "plan_round")
#     g.add_edge("validate_and_merge", "soundstripe_search")

#     # g.add_edge("plan_round", "soundstripe_search")
#     g.add_edge("soundstripe_search", "record_debug")

#     g.add_conditional_edges(
#         "record_debug",
#         _should_continue,
#         {
#             "loop": "explain_strategy",
#             "finish": "finish",
#         },
#     )
#     # loop: re-run with broader filters
#     g.add_edge("explain_strategy", "generate_selections")
#     # g.add_edge("explain_strategy", "soundstripe_search")

#     g.add_edge("finish", END)

#     return g.compile()
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
