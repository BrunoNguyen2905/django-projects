from typing import Any, Dict, List, Optional
import json

from search_orchestration.adapters.ai.state import Selection


def song_to_context_item(song: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal serializable dict for UI: title, artists (name, image), primary_audio mp3."""
    artists: List[Dict[str, str]] = [
        {"name": (a.get("name") or ""), "image": (a.get("image") or "")}
        for a in (song.get("artists") or [])
    ]
    primary = song.get("primary_audio") or {}
    return {
        "id": song.get("id"),
        "title": song.get("title") or f"Track (id: {song.get('id', '?')})",
        "artists": artists,
        "primary_audio_mp3": primary.get("mp3") or "",
    }


def format_filters_summary(merged_selection: Optional[Selection]) -> str:
    """Format merged selection for use in explain prompts (e.g. 'genre: Cinematic; mood: Uplifting'). Safe for None/empty."""
    if not merged_selection:
        return "none yet"
    parts = []
    for category, terms in merged_selection.items():
        if terms:
            parts.append(f"{category}: {', '.join(terms)}")
    return "; ".join(parts) if parts else "none yet"


def message_chunk_content(message_chunk):
    """
    Extract displayable text from a LangChain message chunk.
    Returns (text, is_full_message). Handles content that is either plain text or
    JSON like {"content": "..."} (e.g. structured LLM response). is_full_message is True
    when we parsed JSON with a "content" key (so it's safe to emit as a single log line).
    """
    raw = getattr(message_chunk, "content", None)
    if raw is None:
        raw = message_chunk.get("content", "") if isinstance(
            message_chunk, dict) else ""
    if not raw:
        return "", False
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "content" in parsed:
                return (parsed.get("content") or "").strip(), True
        except (json.JSONDecodeError, TypeError):
            pass
    return (raw if isinstance(raw, str) else str(raw)), False
