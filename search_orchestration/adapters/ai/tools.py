from __future__ import annotations

from typing import Any, Dict, List
from langchain_core.tools import tool

from search_orchestration.adapters.soundstripe_adapter import soundstripe_search

@tool
def soundstripe_search_tool(selection: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Search Soundstripe given a merged taxonomy selection dict.
    Returns list of song dicts.
    """
    return soundstripe_search(selection)