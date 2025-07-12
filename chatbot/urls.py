from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    path("api/chat/", views.chat_response, name="chat-response"),
    path("api/chat/public-swim/", views.public_swim_chat, name="public-swim-chat"),
    path("public-chat/", views.public_swim_chat_ui, name="public-swim-ui"),
    path("public-lessons/", views.public_lesson_chat_ui, name="public-lesson-ui"),
    path("api/chat/public-lessons/", views.public_lesson_chat_api, name="public-lesson-chat"),
]
