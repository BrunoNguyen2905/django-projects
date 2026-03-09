from django.urls import path

from ..views.ai_sfx_search import sfx_search_api_view, sfx_search_view

urlpatterns = [
    path("", sfx_search_view, name="sfx_search"),
    path("api/search/", sfx_search_api_view, name="sfx_search_api"),
]
