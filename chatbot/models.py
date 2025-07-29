from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatbotQuery(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    session_key = models.CharField(max_length=40, blank=True)
    source = models.CharField(max_length=30)  # e.g. 'public_swim' or 'public_lesson'
    message = models.TextField()
    response_type = models.CharField(max_length=20)  # 'FAQ' or 'GPT'
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source} query at {self.timestamp:%Y-%m-%d %H:%M}"
