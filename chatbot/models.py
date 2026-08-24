from django.db import models
from django.contrib.auth import get_user_model
from ckeditor.fields import RichTextField

User = get_user_model()

class ChatbotQuery(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    session_key = models.CharField(max_length=40, blank=True)
    source = models.CharField(max_length=30)  # e.g. 'public_swim' or 'public_lesson'
    message = models.TextField()
    response = models.TextField(blank=True, help_text="Bot's response to the query")
    response_type = models.CharField(max_length=20)  # 'FAQ', 'GPT' or 'BLOCKED'
    confidence_score = models.FloatField(null=True, blank=True, help_text="Embedding match confidence (0.0–1.0)")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source} query at {self.timestamp:%Y-%m-%d %H:%M}"

# faq/models.py

class FAQEntry(models.Model):
    question = models.TextField()
    answer = RichTextField()
    embedding = models.JSONField(blank=True, null=True)
    updated = models.DateTimeField(auto_now=True)
    lessons_only = models.BooleanField(
        default=False,
        help_text="Check this if this FAQ is *only* for the lessons chatbot."
    )

    def __str__(self):
        return self.question[:80]
