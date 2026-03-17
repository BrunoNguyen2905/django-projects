from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from datastar_py import ServerSentEventGenerator as SSE
from datastar_py.django import DatastarResponse

from search_orchestration.adapters.ai import (
    stream_orchestrated_search,
    song_to_context_item,
)
from search_orchestration.adapters.ai.utils import decode_unicode
from search_orchestration.adapters.soundstripe_adapter import soundstripe_search
from search_orchestration.adapters.ai.taxonomy import MUSIC_TAXONOMY
from search_orchestration.html_fragments import (
    render_song_card,
    render_thinking_line,
    render_thinking_current_li,
    escape_thinking_text,
)


@login_required
def search_tags_view(request):
    """
    Tag-based search: GET params q (optional), genre, mood, instrument, characteristic (multiple).
    Returns JSON: { "items": [...], "active_filters": { genre: [], mood: [], ... } }.
    """
    q = (request.GET.get("q") or "").strip()
    genre = request.GET.getlist("genre")
    mood = request.GET.getlist("mood")
    instrument = request.GET.getlist("instrument")
    characteristic = request.GET.getlist("characteristic")

    selection = {}
    if genre:
        selection["genre"] = [decode_unicode(g) for g in genre]
    if mood:
        selection["mood"] = [decode_unicode(m) for m in mood]
    if instrument:
        selection["instrument"] = [decode_unicode(i) for i in instrument]
    if characteristic:
        selection["characteristic"] = [
            decode_unicode(c) for c in characteristic]

    if not selection and not q:
        return JsonResponse(
            {"error": "Select at least one tag or enter search terms."},
            status=400,
        )

    try:
        songs = soundstripe_search(selection, q=q or None)
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500,
        )

    items = [song_to_context_item(s) for s in songs]
    active_filters = selection
    return JsonResponse({"items": items, "active_filters": active_filters})


@login_required
def search_view(request):
    """
    GET-only page that shows the search form. AI search stream is consumed via DataStar SSE.
    """
    return render(request, "search_orchestration/search.html", {
        "query": "",
        "songs": [],
        "active_filters": {},
        "error": None,
        "genres": MUSIC_TAXONOMY["genre"],
        "instruments": MUSIC_TAXONOMY["instrument"],
        "characteristics": MUSIC_TAXONOMY["characteristic"],
        "moods": MUSIC_TAXONOMY["mood"],
    })


@login_required
def search_stream_view(request):
    """
    DataStar SSE endpoint: /search/stream?q=your+query

    Yields DataStar events:
      - patch_signals: sending, showThinking, trackCount, error
      - patch_elements: thinking lines (append to #thinkingHistory), song cards (append to #resultsWrap)
    """
    query = (request.GET.get("q") or "").strip()
    if not query:
        return DatastarResponse(
            iter([
                SSE.patch_signals({
                    "sending": False,
                    "error": "Missing q parameter",
                }),
            ])
        )

    def event_generator():
        active_llm_node = None
        current_line_tokens = []
        total_count = 0

        # Stream start: show loading and thinking panel (client clears results/thinking before opening stream)
        yield SSE.patch_signals({
            "sending": True,
            "showThinking": True,
            "trackCount": 0,
            "error": None,
        })

        def finalize_current_thinking():
            """Replace #thinking-current with finalized <li> (no id) so next node can start fresh."""
            if not current_line_tokens or not active_llm_node:
                return
            line_html = render_thinking_line(
                "".join(current_line_tokens),
                node=active_llm_node,
            )
            if line_html:
                yield SSE.patch_elements(
                    line_html,
                    selector="#thinking-current",
                    mode="replace",
                )

        try:
            for mode, chunk in stream_orchestrated_search(
                user_text=query,
                min_results=100,
                max_rounds=3,
                stream_mode=("custom", "messages", "updates"),
            ):
                if mode == "custom":
                    t = chunk.get("type")
                    if t == "results":
                        # Finalize current thinking line before showing results
                        yield from finalize_current_thinking()
                        current_line_tokens.clear()
                        active_llm_node = None
                        items = chunk.get("items", [])
                        for item in items:
                            card_html = render_song_card(item)
                            yield SSE.patch_elements(
                                card_html,
                                selector="#resultsWrap",
                                mode="append",
                            )
                        total_count += len(items)
                        yield SSE.patch_signals({"trackCount": total_count})

                elif mode == "messages":
                    msg, meta = chunk
                    token = getattr(msg, "content", "") or ""
                    if not token:
                        continue

                    node = (meta.get("langgraph_node") or "").strip() or "llm"
                    if node == "plan_round":
                        continue

                    if active_llm_node is None:
                        # Start first thinking line: append current li, then stream into it
                        active_llm_node = node
                        current_line_tokens = [token]
                        yield SSE.patch_elements(
                            render_thinking_current_li(node),
                            selector="#thinkingHistory",
                            mode="append",
                        )
                        yield SSE.patch_elements(
                            escape_thinking_text(token),
                            selector="#thinking-current",
                            mode="inner",
                        )
                    elif node != active_llm_node:
                        # Switch node: finalize current line, start new one
                        yield from finalize_current_thinking()
                        active_llm_node = node
                        current_line_tokens = [token]
                        yield SSE.patch_elements(
                            render_thinking_current_li(node),
                            selector="#thinkingHistory",
                            mode="append",
                        )
                        yield SSE.patch_elements(
                            escape_thinking_text(token),
                            selector="#thinking-current",
                            mode="inner",
                        )
                    else:
                        # Same node: append token and update current line in place
                        current_line_tokens.append(token)
                        yield SSE.patch_elements(
                            escape_thinking_text("".join(current_line_tokens)),
                            selector="#thinking-current",
                            mode="inner",
                        )

        except Exception as e:
            yield from finalize_current_thinking()
            yield SSE.patch_signals({
                "sending": False,
                "error": str(e),
            })
            return

        # Finalize last thinking line (replace #thinking-current with plain li)
        yield from finalize_current_thinking()

        # Stream end: stop loading but keep thinking panel visible so user can review
        yield SSE.patch_signals({
            "sending": False,
            "trackCount": total_count,
        })

        if total_count == 0:
            yield SSE.patch_elements(
                '<p id="noResultsMsg" class="text-muted">No tracks found.</p>',
                selector="#resultsWrap",
                mode="append",
            )

    return DatastarResponse(event_generator())
