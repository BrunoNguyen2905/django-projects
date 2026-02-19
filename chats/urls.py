from django.urls import path

from .views import home, new_chat, chat_view
app_name = "chats"

urlpatterns = [
    path("", home, name="chat_home"),
    path("new/", new_chat, name="new_chat"),
    path("<str:id>/", chat_view, name="chat"),
]
