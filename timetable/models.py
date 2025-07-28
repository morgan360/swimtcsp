# timetable/models.py

from django.db import models

class CalendarEvent(models.Model):
    CATEGORY_CHOICES = [
        ('term', 'Term Dates'),
        ('rebooking', 'Rebooking Window'),
        ('closure', 'Closure'),
        ('special', 'Special Event'),
    ]

    title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)

    def get_color(self):
        return {
            'term': '#3B82F6',        # blue
            'rebooking': '#F59E0B',   # yellow
            'closure': '#EF4444',     # red
            'special': '#10B981',     # green
        }.get(self.category, '#6B7280')  # default gray

    def __str__(self):
        return f"{self.title} ({self.category})"
