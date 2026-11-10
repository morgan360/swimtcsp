from django.db import models


class GoogleReviewSnapshot(models.Model):
    """One look at the pool's Google rating, taken by finances.google_reviews.

    The rating and count are kept so the dashboard can count new reviews. Google's
    terms don't allow holding review text for long, so `reviews` is cleared once a
    snapshot is older than google_reviews.KEEP_REVIEW_TEXT_DAYS.
    """

    fetched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)
    reviews = models.JSONField(default=list, blank=True)
    maps_url = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ['-fetched_at']
        get_latest_by = 'fetched_at'

    def __str__(self):
        return f'{self.rating}★ from {self.review_count} reviews at {self.fetched_at:%Y-%m-%d %H:%M}'
