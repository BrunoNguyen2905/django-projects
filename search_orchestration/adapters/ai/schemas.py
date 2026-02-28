"""Pydantic schemas for LLM structured output (with_structured_output)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SelectionItem(BaseModel):
    """One taxonomy selection: optional lists of terms per category. Max 5 terms total per selection."""

    genre: Optional[List[str]] = Field(
        default=None,
        description="Genre terms from the allowed taxonomy (e.g. Acoustic, Cinematic).",
    )
    instrument: Optional[List[str]] = Field(
        default=None,
        description="Instrument terms from the allowed taxonomy (e.g. Piano, Strings).",
    )
    characteristic: Optional[List[str]] = Field(
        default=None,
        description="Characteristic terms (e.g. Epic, Mellow, Building).",
    )
    mood: Optional[List[str]] = Field(
        default=None,
        description="Mood terms (e.g. Inspiring, Chill, Hopeful).",
    )


class SearchSelectionsResponse(BaseModel):
    """Between 0 and 3 selection objects. Simple queries: 1; richer requests: 2-3."""

    selections: List[SelectionItem] = Field(
        description="List of 0 to 3 selection objects. Each object may have genre, instrument, characteristic, and/or mood as lists of allowed terms. Max 3 terms total per selection.",
        min_length=0,
        max_length=3,
    )


class ExplainResponse(BaseModel):
    """Short user-facing plan in 1–3 sentences."""

    content: str = Field(
        description="1–3 sentences describing what will be tried next. Practical and concise. No internal reasoning.",
    )
