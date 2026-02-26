from django.urls import path

from .views import search_stream_view, search_view, search_tags_view

urlpatterns = [
    path("", search_view, name="search"),
    path("stream/", search_stream_view, name="search_stream"),
    path("tags/", search_tags_view, name="search_tags"),
]
