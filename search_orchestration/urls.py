from django.urls import path

from .views import search_stream_view, search_view

urlpatterns = [
    path("", search_view, name="search"),
    path("stream/", search_stream_view, name="search_stream"),
]
