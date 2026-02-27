import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render

from search_orchestration.adapters.ai import (
    stream_orchestrated_search,
    song_to_context_item,
)
from search_orchestration.adapters.ai.utils import decode_unicode
from search_orchestration.adapters.soundstripe_adapter import soundstripe_search

from search_orchestration.adapters.ai.taxonomy import MUSIC_TAXONOMY


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
        print('songs from soundstripe_search', songs)
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
    GET-only page that shows the search form + JS that connects to SSE stream.
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


def _sse(event: str, data: dict) -> str:
    """
    Format a Server-Sent Event message.
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@login_required
def search_stream_view(request):
    """
    SSE endpoint:
      /search/stream?q=your+query

    Streams:
      - log: progress messages (custom events from graph)
      - results: incremental song batches (custom events from graph)
      - llm_token: token chunks from LLM generation (messages stream_mode)
      - state: optional node updates (updates stream_mode)
      - error: errors
      - END: completion
    """
    query = (request.GET.get("q") or "").strip()
    if not query:
        return StreamingHttpResponse(
            iter([_sse("error", {"message": "Missing q parameter"})]),
            content_type="text/event-stream",
        )

    def event_generator():
        # Initial status: we're starting to process the request
        # yield _sse("log", {"message": "Starting your search…"})
        results_sent = 0  # only send new items from updates (client appends)

        try:
            for mode, chunk in stream_orchestrated_search(
                user_text=query,
                min_results=100,
                max_rounds=3,
                stream_mode=("custom", "messages", "updates"),
            ):
                if mode == "custom":
                    t = chunk.get("type")
                    if t == "log":
                        msg = chunk.get("message", "")
                        if msg:
                            yield _sse("log", {"message": msg})
                    elif t == "results":
                        yield _sse("results", {"items": chunk.get("items", [])})
        except Exception as e:
            yield _sse("error", {"message": str(e)})

        yield _sse("END", {"message": "Search complete"})

    resp = StreamingHttpResponse(
        event_generator(), content_type="text/event-stream")
    # SSE + proxies: prevent buffering
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"  # for nginx
    return resp
