from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional, TypedDict, NotRequired
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

Taxonomy = Dict[str, List[str]]
Selection = Dict[str, List[str]]


class SearchState(TypedDict):
    # Inputs

    # The raw user query.
    user_text: str

    # The minimum number of results to return.
    min_results: int

    # The maximum number of rounds to run.
    max_rounds: int

    # Runtime state (optional keys)

    # The current round index.
    round_idx: NotRequired[int]

    # History of how many tracks were returned each round (from Soundstripe, before dedupe). Used as signal for “broaden more / adjust.”
    prior_counts: NotRequired[List[int]]

    # The merged selection (after dedupe).
    merged_selection: NotRequired[Selection]

    # The results returned from Soundstripe.
    results: NotRequired[List[Dict[str, Any]]]

    # The IDs of the songs that have already been seen.
    seen_ids: NotRequired[List[str]]

    # Count of songs returned by Soundstripe this round (pre-dedupe).
    last_round_count: NotRequired[int]

    # for explanation nodes
    explain_key: str
    explain_ctx: Dict[str, Any]

    # lets graph stream LLM tokens in stream_mode="messages"
    messages: Annotated[List[BaseMessage], add_messages]
