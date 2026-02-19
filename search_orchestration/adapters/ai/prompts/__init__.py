"""
Prompt builders for the search orchestrator.

Single source of truth for the prompts API. When adding new prompt modules
(e.g. refine.py), add imports and __all__ here only—no need to touch the
parent ai/__init__.py.
"""

from search_orchestration.adapters.ai.prompts.selection import (
    get_selection_prompt,
    get_selection_instruction,
)
from search_orchestration.adapters.ai.prompts.explain import (
    get_explain_prompt,
    get_explain_prompt_for_node,
)

__all__ = [
    "get_selection_prompt",
    "get_selection_instruction",
    "get_explain_prompt",
    "get_explain_prompt_for_node",
]
