from __future__ import annotations
import time
import json
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer

from search_orchestration.adapters.ai.llms import (
    get_explain_llm_streaming,
    get_structured_sfx_selection_llm,
)
from search_orchestration.adapters.ai.prompts import (
    get_selection_prompt,
    get_selection_instruction,
)
from search_orchestration.adapters.ai.prompts.explain import EXPLAIN_PROMPTS_SFX
from search_orchestration.adapters.ai.utils import merge_selection_into, sfx_to_context_item, format_filters_summary, validate_and_normalize_sfx_selections
from search_orchestration.adapters.ai.state import Selection, SearchState
from search_orchestration.adapters.ai.taxonomy import SFX_TAXONOMY
from search_orchestration.adapters.soundstripe_adapter import soundstripe_sfx_search

# Defaults for search loop
DEFAULT_MIN_RESULTS = 20
DEFAULT_MAX_ROUNDS = 3
TAXONOMY_JSON = json.dumps(SFX_TAXONOMY, ensure_ascii=False, indent=2)
SELECTION_PROMPT = get_selection_prompt(SFX_TAXONOMY)


def generate_search_selections(
    user_text: str,
    *,
    broaden: bool,
    prior_counts: List[int],
) -> List[Dict[str, Any]]:
    """
    Generate taxonomy selections from user text using structured LLM + prompt template.
    Returns a list of selection dicts (validated and normalized).
    """
    instruction = get_selection_instruction(
        broaden=broaden, prior_counts=prior_counts, taxonomy=SFX_TAXONOMY)

    messages = SELECTION_PROMPT.format_prompt(
        instruction=instruction,
        user_text=user_text,
        taxonomy_json=TAXONOMY_JSON,
    ).to_messages()
    # print("messages from sfx generate_search_selections", messages)

    structured_llm = get_structured_sfx_selection_llm()
    res = structured_llm.invoke(messages)
    # Extract and parse JSON content from AIMessage
    content = res.content if hasattr(res, 'content') else str(res)
    try:
        selection_dict = json.loads(content)
        raw: List[Dict[str, Any]] = [selection_dict]
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        raw: List[Dict[str, Any]] = [{}]
        # TODO can be optimzed for the raw and validate_and_normalize_sfx_selections to be in the same function
    print("raw from sfx generate_search_selections", raw)
    print("validate_and_normalize_sfx_selections from sfx generate_search_selections",
          validate_and_normalize_sfx_selections(raw))
    return validate_and_normalize_sfx_selections(raw)


def _build_explain_prompt_messages(state: SearchState) -> List[BaseMessage]:
    key = state.get("explain_key") or "finish"
    ctx = state.get("explain_ctx") or {}
    prompt = EXPLAIN_PROMPTS_SFX[key]

    user_text: str = state.get("user_text") or ""
    filters_summary = format_filters_summary(
        state.get("merged_selection") or {}
    )

    if key == "plan_round":
        return prompt.format_prompt(
            user_text=user_text,
            broaden=bool(ctx.get("broaden", False)),
            filters_summary=filters_summary,
            is_first_round=bool(ctx.get("is_first_round", False)),
        ).to_messages()

    if key == "soundstripe_search":
        return prompt.format_prompt(
            user_text=user_text,
            filters_summary=filters_summary,
            songs_count=int(ctx.get("songs_count", 0)),
            new_songs_count=int(ctx.get("new_songs_count", 0)),
        ).to_messages()

    if key == "record_debug":
        return prompt.format_prompt(
            user_text=user_text,
            filters_summary=filters_summary,
            total_results=int(ctx.get("total_results", 0)),
            last_round_count=int(ctx.get("last_round_count", 0)),
            prior_counts_str=str(ctx.get("prior_counts", [])),
            min_results=int(ctx.get("min_results", 0)),
            target_achieved=bool(ctx.get("target_achieved", False)),
            will_loop=bool(ctx.get("will_loop", False)),
        ).to_messages()

    if key == "finish":
        return prompt.format_prompt(
            user_text=user_text,
            total_results=int(ctx.get("total_results", 0)),
        ).to_messages()

    return prompt.format_prompt(user_text=user_text).to_messages()


def make_explain_runnable():
    llm = get_explain_llm_streaming()
    # Returns AIMessage (final), and streams AIMessageChunk via stream_mode="messages"
    return RunnableLambda(_build_explain_prompt_messages) | llm


# -----------------------------
# LangGraph State + Graph
# -----------------------------


StreamWriter = Callable[[Dict[str, Any]], None]


def _emit(writer: StreamWriter, *, type_: str, **payload: Any) -> None:
    """Helper to stream structured custom events (stream_mode='custom')."""
    writer({"type": type_, **payload})


def node_plan_round(state: SearchState) -> Dict[str, Any]:
    user_text: str = state.get("user_text") or ""
    round_idx = int(state.get("round_idx", 0))
    is_first_round = (round_idx == 0)
    broaden = bool(round_idx > 0)
    if is_first_round and not state.get("results"):
        state = {
            **state,
            "min_results": state.get("min_results", DEFAULT_MIN_RESULTS),
            "max_rounds": state.get("max_rounds", DEFAULT_MAX_ROUNDS),
            "round_idx": 0,
            "prior_counts": [],
            "results": [],
            "seen_ids": [],
        }

    try:
        valid = generate_search_selections(
            user_text,
            broaden=broaden,
            prior_counts=state.get("prior_counts") or [],
        )
        print(f"Generated {len(valid)} selections: {valid}")
    except Exception as e:
        print(f"Selection validation error: {e}")
        valid = []

    merged: Selection = {}
    for sel in valid:
        merge_selection_into(merged, sel)

    return {
        "merged_selection": merged,
        "explain_key": "plan_round",
        "explain_ctx": {
            "broaden": broaden,
            "is_first_round": is_first_round,
        },
    }


def node_soundstripe_search(state: SearchState) -> Dict[str, Any]:
    writer = get_stream_writer()
    merged: Selection = state.get("merged_selection") or {}

    try:
        sfx_results: List[Dict[str, Any]] = soundstripe_sfx_search(merged)
    except Exception as e:
        print(f"Error in soundstripe_sfx_search: {e}")
        # Return empty results to continue the flow
        return {
            "results": state.get("results", []),
            "seen_ids": state.get("seen_ids", []),
            "last_round_count": 0,
            "explain_key": "soundstripe_search",
            "explain_ctx": {
                "songs_count": 0,
                "new_songs_count": 0,
                "error": str(e),
            },
        }

    results: List[Dict[str, Any]] = list(state.get("results") or [])
    seen_ids_set: Set[str] = set(state.get("seen_ids") or [])

    new_sfx: List[Dict[str, Any]] = []
    for sfx in sfx_results:
        sid = str(sfx.get("id") or "")
        if not sid or sid in seen_ids_set:
            continue
        seen_ids_set.add(sid)
        results.append(sfx)
        new_sfx.append(sfx)

    if new_sfx:
        _emit(
            writer,
            type_="results",
            items=[sfx_to_context_item(s) for s in new_sfx],
        )

    return {
        "results": results,
        "seen_ids": list(seen_ids_set),  # JSON-safe
        "last_round_count": len(sfx_results),
        "explain_key": "soundstripe_search",
        "explain_ctx": {
            "songs_count": len(sfx_results),
            "new_songs_count": len(new_sfx),
        },
    }


def node_record_debug(state: SearchState) -> Dict[str, Any]:
    # writer = get_stream_writer()
    round_idx = int(state.get("round_idx", 0))
    total_results = len(state.get("results") or [])
    min_results = int(state.get("min_results", DEFAULT_MIN_RESULTS))
    last_round_count = int(state.get("last_round_count", 0))
    max_rounds = int(state.get("max_rounds", DEFAULT_MAX_ROUNDS))
    target_achieved = total_results >= min_results
    will_loop = (not target_achieved) and (round_idx + 1 < max_rounds)
    prior = list(state.get("prior_counts") or [])
    prior.append(last_round_count)

    return {
        **state,
        "prior_counts": prior,
        "round_idx": round_idx + 1,
        "explain_key": "record_debug",
        "explain_ctx": {
            "total_results": total_results,
            "last_round_count": last_round_count,
            "prior_counts": prior,
            "min_results": min_results,
            "target_achieved": target_achieved,
            "will_loop": will_loop,
        },
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

    results = state.get("results") or []
    return {
        **state,
        "explain_key": "finish",
        "explain_ctx": {
            "total_results": len(results),
        },
    }


def build_search_graph() -> Any:
    g: StateGraph[SearchState] = StateGraph(SearchState)

    explain = make_explain_runnable()

    # Wrap explain runnable to write into state["messages"] so add_messages can collect it
    def explain_node(state: SearchState) -> Dict[str, Any]:
        try:
            # streams chunks via stream_mode="messages"
            msg = explain.invoke(state)
            return {"messages": [msg]}
        except Exception as e:
            print(f"Error in explain_node: {e}")
            # Return empty messages to continue flow
            return {"messages": []}

    # Register nodes
    g.add_node("plan_round", node_plan_round)
    g.add_node("plan_round_explain", explain_node)

    g.add_node("soundstripe_search", node_soundstripe_search)
    g.add_node("soundstripe_search_explain", explain_node)

    g.add_node("record_debug", node_record_debug)
    g.add_node("record_debug_explain", explain_node)

    g.add_node("finish", node_finish)
    g.add_node("finish_explain", explain_node)

    # Flow
    g.add_edge(START, "plan_round")
    g.add_edge("plan_round", "plan_round_explain")
    g.add_edge("plan_round_explain", "soundstripe_search")

    g.add_edge("soundstripe_search", "soundstripe_search_explain")
    g.add_edge("soundstripe_search_explain", "record_debug")

    g.add_edge("record_debug", "record_debug_explain")

    g.add_conditional_edges(
        "record_debug_explain",
        _should_continue,
        {
            "loop": "plan_round",
            "finish": "finish",
        },
    )

    g.add_edge("finish", "finish_explain")
    g.add_edge("finish_explain", END)

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
