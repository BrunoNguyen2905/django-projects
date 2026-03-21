"""
Render HTML fragments for DataStar SSE patch_elements.
Used by the AI search stream to send thinking lines and song cards as HTML.
"""
import html
from typing import Any, Dict, List


def _attr(s: str) -> str:
    """Escape for HTML attribute value."""
    return html.escape(s, quote=True)


def _text(s: str) -> str:
    """Escape for HTML text content."""
    return html.escape(s)


def render_thinking_line(text: str, node: str = "") -> str:
    """Render one thinking line as <li> for appending to #thinkingHistory."""
    content = (text or "").strip()
    if not content:
        return ""
    node_attr = f' data-node="{_attr(node)}"' if node else ""
    return f'<li class="typed-line"{node_attr}>{_text(content)}</li>'


def render_thinking_current_li(node: str = "") -> str:
    """Render the live-updated thinking line with id='thinking-current' (stream tokens into this).
    Uses class typing-line so the blinking cursor (::after) is shown while thinking is in progress.
    """
    node_attr = f' data-node="{_attr(node)}"' if node else ""
    return f'<li id="thinking-current" class="typing-line"{node_attr}></li>'


def escape_thinking_text(text: str) -> str:
    """Escape text for use inside the current thinking li (innerHTML update)."""
    return _text(text or "")


def _tag_line(tags: Dict[str, List[str]]) -> str:
    """Comma-separated tag line (genre, instrument, mood, characteristic), max 4 shown."""
    all_terms: List[str] = []
    for key in ("genre", "instrument", "mood", "characteristic"):
        all_terms.extend(tags.get(key) or [])
    all_terms = [t for t in all_terms if t]
    limited = all_terms[:4]
    return ", ".join(limited) + ("..." if len(all_terms) > 4 else "")


def render_song_card(item: Dict[str, Any]) -> str:
    """
    Render one song context item as a full card HTML (same structure as template).
    Returns a single root element: <div class="col-12">...</div> for append to #resultsWrap.
    """
    title = _text((item.get("title") or "Track"))
    artists = item.get("artists") or []
    artist_names = ", ".join((a.get("name") or "")
                             for a in artists if isinstance(a, dict))
    artist_esc = _text(artist_names)
    duration = _text((item.get("duration_display") or ""))
    bpm_val = item.get("bpm")
    bpm_str = f"{bpm_val}BPM" if bpm_val is not None else ""
    bpm_esc = _text(bpm_str)
    bpm_style = ' style="display: none;"' if not bpm_str else ""
    tags = item.get("tags") or {}
    line = _tag_line(tags)
    line_esc = _text(line)
    line_style = ' style="display: none;"' if not line else ""
    art_src = ""
    art_style = ' style="display: none;"'
    if artists and isinstance(artists[0], dict) and artists[0].get("image"):
        art_src = _attr(artists[0]["image"])
        art_style = ""

    audio_html = ""
    mp3 = item.get("primary_audio_mp3") or ""
    if mp3:
        mp3_esc = _attr(mp3)
        audio_html = f"""<div class="song-item-audio-controls">
        <button class="play-btn" type="button" aria-label="Play preview" aria-pressed="false">
          <span class="play-btn__glyph play-btn__glyph--play" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"></polygon></svg></span>
          <span class="play-btn__glyph play-btn__glyph--pause" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 24 24"><rect x="6" y="5" width="4" height="14"></rect><rect x="14" y="5" width="4" height="14"></rect></svg></span>
        </button>
        <audio preload="metadata" class="w-100" data-song-audio data-song-id="{_attr(str(item.get('id') or ''))}">
          <source src="{mp3_esc}" type="audio/mpeg">Your browser does not support the audio element.
        </audio>
        <input type="range" min="0" value="0" class="progress-bar" aria-label="Audio progress">
      </div>"""
    else:
        audio_html = '<div class="song-item-audio-controls"><span class="text-muted small">No preview</span></div>'

    return f"""<div class="col-12">
      <div class="song-item-card">
        <div class="song-item-art">
          <img data-slot="art" src="{art_src}" alt=""{art_style} />
        </div>
        <div class="song-item-info">
          <div class="song-item-title-row">
            <span class="song-item-title">{title}</span>
          </div>
          <p class="song-item-artist mb-0">{artist_esc}</p>
        </div>
        {audio_html}
        <div class="song-item-meta">
          <div class="song-item-duration">{duration}</div>
          <div class="song-item-bpm"{bpm_style}>{bpm_esc}</div>
        </div>
        <div class="song-item-tags">
          <div class="song-item-tags-line"{line_style}>{line_esc}</div>
        </div>
        <div class="song-item-actions">
          <a href="#" class="btn-link" title="Add to playlist"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg></a>
          <a href="#" class="btn-link" title="Like"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg></a>
          <a href="#" class="btn-link" title="Add"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></a>
          <a href="#" class="btn-link" title="More"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg></a>
        </div>
      </div>
    </div>"""
