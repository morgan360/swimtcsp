# timetable/models.py

from django.db import models

class CalendarEvent(models.Model):
    CATEGORY_CHOICES = [
        ('term', 'Term Dates'),
        ('rebooking', 'Rebooking Window'),
        ('closure', 'Closure'),
        ('special', 'Special Event'),
    ]

    # For closures: what is off that day. Customers see these on the timetable
    # and the homepage; the other categories are for the staff calendar only.
    AFFECTS_ALL, AFFECTS_LESSONS, AFFECTS_SWIMS = 'all', 'lessons', 'swims'
    AFFECTS_CHOICES = [
        (AFFECTS_ALL, 'Whole pool closed'),
        (AFFECTS_LESSONS, 'No lessons'),
        (AFFECTS_SWIMS, 'No public swims'),
    ]

    title = models.CharField(
        max_length=200,
        help_text="For a closure, customers see this as the reason, e.g. \"Bank holiday\" or \"Midterm break\".",
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    affects = models.CharField(
        max_length=10, choices=AFFECTS_CHOICES, default=AFFECTS_ALL,
        help_text="Closures only: what is off on these days.",
    )
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
