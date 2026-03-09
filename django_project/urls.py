from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from search_orchestration.views.ai_sfx_search import sfx_search_api_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("pages.urls")),
    path("chats/", include("chats.urls")),
    path("search/", include("search_orchestration.urls.ai_songs_search")),
    path("sfx-search/", include("search_orchestration.urls.ai_sfx_search")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
