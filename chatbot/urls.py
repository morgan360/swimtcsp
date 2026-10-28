from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "chatbot"

urlpatterns = [
    path("api/chat/", views.chat_response, name="chat-response"),
    path("api/chat/public-swim/", views.public_swim_chat, name="public-swim-chat"),
    path("public-chat/", views.public_swim_chat_ui, name="public-swim-ui"),
    # The lessons bot was merged into SplashBot (Oct 2026); old links and any
    # cached page still reach it.
    path("public-lessons/", RedirectView.as_view(pattern_name="chatbot:public-swim-ui", permanent=False),
         name="public-lesson-ui"),
    path("api/chat/public-lessons/", views.public_swim_chat, name="public-lesson-chat"),
    path("api/chat/rate/", views.rate_answer, name="rate-answer"),
]
