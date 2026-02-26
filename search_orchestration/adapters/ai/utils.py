from typing import Any, Dict, List, Optional, Set
import json

from search_orchestration.adapters.ai.state import Selection, Taxonomy
from search_orchestration.adapters.ai.taxonomy import MUSIC_TAXONOMY

MAX_TERMS_PER_SELECTION = 3
MAX_SELECTIONS = 4


def _format_duration(seconds: Optional[int]) -> str:
    """Format seconds as M:SS for display."""
    if seconds is None or seconds < 0:
        return ""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def song_to_context_item(song: Dict[str, Any]) -> Dict[str, Any]:
    """Serializable dict for UI: title, artists, primary_audio, tags (genre/mood/instrument/characteristic), duration, bpm."""
    artists: List[Dict[str, str]] = [
        {"name": (a.get("name") or ""), "image": (a.get("image") or "")}
        for a in (song.get("artists") or [])
    ]
    primary = song.get("primary_audio") or {}
    tags = song.get("tags") or {}
    duration_s = primary.get("duration_s") or song.get("duration")
    return {
        "id": song.get("id"),
        "title": song.get("title") or f"Track (id: {song.get('id', '?')})",
        "artists": artists,
        "primary_audio_mp3": primary.get("mp3") or "",
        "tags": {
            "genre": list(tags.get("genre") or []),
            "mood": list(tags.get("mood") or []),
            "instrument": list(tags.get("instrument") or []),
            "characteristic": list(tags.get("characteristic") or []),
        },
        "duration_display": _format_duration(duration_s),
        "bpm": song.get("bpm"),
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


def _allowed_terms_set(taxonomy: Taxonomy) -> Dict[str, Set[str]]:
    return {k: set(v) for k, v in taxonomy.items()}


def merge_selection_into(target: Selection, source: Selection) -> None:
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


def decode_unicode(str: str) -> str:
    try:
        return json.loads('"' + str.replace('"', '\\"') + '"')
    except Exception:
        return str
