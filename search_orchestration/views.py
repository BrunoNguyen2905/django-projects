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
        active_llm_node = None
        started_for_node = False

        def start_node(node: str):
            nonlocal active_llm_node, started_for_node
            active_llm_node = node
            started_for_node = True
            return _sse("llm_token", {"node": node, "start": True})

        def end_node(node: str):
            nonlocal started_for_node
            started_for_node = False
            return _sse("llm_token", {"node": node, "end": True})

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
                        yield _sse("results", {"items": chunk.get("items", [])})
                elif mode == "messages":
                    msg, meta = chunk
                    token = getattr(msg, "content", "") or ""
                    if not token:
                        continue

                    node = (meta.get("langgraph_node") or "").strip() or "llm"
                    # Don't stream internal selection JSON node(s)
                    if node == "plan_round":
                        continue
                    # If node switched, close previous + open new
                    if active_llm_node is None:
                        yield start_node(node)
                    elif node != active_llm_node:
                        yield end_node(active_llm_node)
                        yield start_node(node)

                    # Normal token emit
                    yield _sse("llm_token", {"node": node, "token": token})
        except Exception as e:
            # close cursor cleanly on error
            if active_llm_node and started_for_node:
                yield end_node(active_llm_node)
            yield _sse("error", {"message": str(e)})

        # close cursor cleanly at the end
        if active_llm_node and started_for_node:
            yield end_node(active_llm_node)
        yield _sse("END", {})
    resp = StreamingHttpResponse(
        event_generator(), content_type="text/event-stream")

    resp['Cache-Control'] = "no-cache"
    resp['X-Accel-Buffering'] = "no"
    return resp


def _sse(event: str, data: dict) -> str:
    """
    Format a Server-Sent Event message.
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
