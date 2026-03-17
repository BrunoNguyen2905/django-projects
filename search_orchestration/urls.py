from django.urls import path

from .views import (
    search_clear_thinking_view,
    search_stream_view,
    search_tags_view,
    search_view,
)

urlpatterns = [
    path("", search_view, name="search"),
    path("stream/", search_stream_view, name="search_stream"),
    path("tags/", search_tags_view, name="search_tags"),
    path("clear-thinking/", search_clear_thinking_view, name="search_clear_thinking"),
]
