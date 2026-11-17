from datetime import date

from django.db import models


class GoogleReviewSnapshot(models.Model):
    """One look at the pool's Google rating, taken by finances.google_reviews.

    The rating and count are kept so the dashboard can count new reviews.
    latest_reviews holds the newest few reviews from the Business Profile API
    (first name, stars, date, text, replied), or [] when that isn't set up.
    """

    fetched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)
    maps_url = models.URLField(max_length=500, blank=True)
    latest_reviews = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-fetched_at']
        get_latest_by = 'fetched_at'

    def __str__(self):
        return f'{self.rating}★ from {self.review_count} reviews at {self.fetched_at:%Y-%m-%d %H:%M}'

    def reviews_for_display(self):
        """latest_reviews with the date as a date and the stars spelled out."""
        shown = []
        for review in self.latest_reviews:
            stars = int(review.get('stars') or 0)
            try:
                when = date.fromisoformat(review.get('date', ''))
            except ValueError:
                when = None
            shown.append({**review, 'date': when, 'filled': '★' * stars, 'empty': '★' * (5 - stars)})
        return shown


class DashboardOpen(models.Model):
    """How often each staff member opened the Live Dashboard on a day.

    One row per person per day with a count, written by finances.views.live_dashboard.
    Only the Live Dashboard is counted, and only staff can open it.
    """

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='dashboard_opens')
    date = models.DateField(db_index=True)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-date']
        constraints = [models.UniqueConstraint(fields=['user', 'date'], name='unique_dashboard_open_day')]

    def __str__(self):
        return f'{self.user} opened the Live Dashboard {self.count}× on {self.date}'
