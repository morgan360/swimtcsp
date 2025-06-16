from django.db import models
from django.conf import settings

class TimetableOverride(models.Model):
    EVENT_TYPE_CHOICES = [
        ('bespoke', 'Bespoke Session'),
        ('closure', 'Closure'),
    ]

    title = models.CharField(max_length=100)
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return f"{self.title} ({self.event_type}) on {self.date}"
