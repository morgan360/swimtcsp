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


class PageVisit(models.Model):
    """How often a page was used on a day, for the live dashboard.

    Only a count: no cookies, IP addresses or anything about who visited, so it
    needs no consent. Written by timetable.visits.count_visit, which leaves out
    staff and bots.
    """
    HOME, TIMETABLE = 'home', 'timetable'
    TAB_SWIMS, TAB_LESSONS, TAB_CALENDAR = 'tab:swims', 'tab:lessons', 'tab:calendar'
    BOOK_TIMETABLE, BOOK_HOME = 'book:timetable', 'book:home'
    PAGE_CHOICES = [
        (HOME, 'Homepage'),
        (TIMETABLE, 'Timetable page'),
        (TAB_SWIMS, 'Timetable: public swims tab'),
        (TAB_LESSONS, 'Timetable: lessons tab'),
        (TAB_CALENDAR, 'Timetable: calendar tab'),
        (BOOK_TIMETABLE, 'Book clicked on the timetable'),
        (BOOK_HOME, 'Book clicked on the homepage card'),
    ]

    date = models.DateField(db_index=True)
    page = models.CharField(max_length=20, choices=PAGE_CHOICES)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-date', 'page']
        constraints = [models.UniqueConstraint(fields=['date', 'page'], name='unique_page_visit_day')]

    def __str__(self):
        return f"{self.get_page_display()} on {self.date}: {self.count}"
