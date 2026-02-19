"""
AI adapters for search orchestration.

Best practice: each subpackage owns its API in its own __init__.py.
This module exposes only subpackages and main entry points so it stays
stable as prompts/schemas/utils grow.

- Prompt helpers: use `from search_orchestration.adapters.ai.prompts import ...`
  or `from search_orchestration.adapters.ai import prompts`.
- Orchestrator: use `stream_orchestrated_search` (below).
- State/schemas/llms/utils: import from their modules or subpackages.
"""

from . import prompts
from .state import SearchState, Selection
from .llm_search_orchestrator_v2 import (
    stream_orchestrated_search,
)
from .utils import song_to_context_item, message_chunk_content

__all__ = [
    "prompts",
    "SearchState",
    "Selection",
    "stream_orchestrated_search",
    "song_to_context_item",
    "message_chunk_content",
]
