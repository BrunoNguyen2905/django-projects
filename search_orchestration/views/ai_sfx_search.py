import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render

from search_orchestration.adapters.ai.llm_sfx_search_orchestrator import stream_orchestrated_search
from search_orchestration.clients.soundstripe_client import get_categories, get_sound_effects


@login_required
def sfx_search_view(request):
    """
    GET-only page that shows the SFX search form + JS that connects to SSE stream.
    """
    return render(request, "search_orchestration/sfx_search.html", {
        "query": "",
        "sound_effects": [],
        "active_filters": {},
        "error": None,
    })


@login_required
def sfx_search_api_view(request):
    """
    API endpoint for SFX search. GET params: q (optional), categories (comma-separated, optional).
    Returns JSON: { "sound_effects": [...], "error": null }
    """
    q = (request.GET.get("q") or "").strip()
    categories_param = request.GET.get("categories", "").strip()

    # Parse categories
    categories = None
    if categories_param:
        categories = categories_param

    try:
        sound_effects = get_sound_effects(q=q, categories=categories)
        return JsonResponse({"sound_effects": sound_effects.get("data", []), "error": None})
    except Exception as e:
        return JsonResponse({"sound_effects": [], "error": str(e)}, status=500)


@login_required
def sfx_search_stream_view(request):
    """
    SSE endpoint:
      /sfx/search/stream?q=your+query

    Streams:
      - log: progress messages (custom events from graph)
      - results: incremental sfx batches (custom events from graph)
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
