from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict, NotRequired

Taxonomy = Dict[str, List[str]]
Selection = Dict[str, List[str]]

class SearchState(TypedDict):
    # Inputs
    user_text: str
    min_results: int
    max_rounds: int

    # Runtime state (optional keys)
    round_idx: NotRequired[int]
    broaden: NotRequired[bool]
    prior_counts: NotRequired[Optional[List[int]]]

    explanation: NotRequired[str]

    selections_raw: NotRequired[Any]
    selections_valid: NotRequired[List[Selection]]
    merged_selection: NotRequired[Selection]

    results: NotRequired[List[Dict[str, Any]]]
    # JSON-friendly: store as list, convert to set inside nodes
    seen_ids: NotRequired[List[str]]

    last_round_count: NotRequired[int]

    debug_rounds: NotRequired[List[Dict[str, Any]]]
    done: NotRequired[bool]
    stop_reason: NotRequired[Optional[str]]