"""The pool's Google rating and latest reviews, for the Live Dashboard.

Read from the Places API (New) at most every REFRESH_HOURS and kept as
GoogleReviewSnapshot rows. Google only shares up to five reviews (its "most
relevant"), so this shows a sample, not every review. If Google can't be
reached the dashboard gets the last good snapshot: it must never fail because
of Google.
"""
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.utils import timezone

from finances.models import GoogleReviewSnapshot

logger = logging.getLogger('finances')

PLACES_URL = 'https://places.googleapis.com/v1/places/{place_id}'
FIELD_MASK = 'rating,userRatingCount,reviews,googleMapsUri'
REFRESH_HOURS = 6
KEEP_REVIEW_TEXT_DAYS = 30
TIMEOUT_SECONDS = 5


def configured():
    return bool(settings.GOOGLE_PLACES_API_KEY and settings.GOOGLE_PLACE_ID)


def latest_snapshot():
    """The newest snapshot, fetching a new one first if it is stale.

    None when the feature isn't configured or nothing has ever been fetched.
    """
    if not configured():
        return None
    latest = GoogleReviewSnapshot.objects.first()
    if latest is None or latest.fetched_at < timezone.now() - timedelta(hours=REFRESH_HOURS):
        return fetch() or latest
    return latest


def fetch():
    """Ask Google for the rating and reviews and save a snapshot. None on failure."""
    try:
        response = requests.get(
            PLACES_URL.format(place_id=settings.GOOGLE_PLACE_ID),
            headers={'X-Goog-Api-Key': settings.GOOGLE_PLACES_API_KEY, 'X-Goog-FieldMask': FIELD_MASK},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        place = response.json()
        rating = Decimal(str(place['rating'])).quantize(Decimal('0.1')) if 'rating' in place else None
    except (requests.RequestException, ValueError, InvalidOperation) as exc:
        # The response body is Google's error message; it never echoes the key.
        body = getattr(getattr(exc, 'response', None), 'text', '')[:300]
        logger.error('Google reviews fetch failed: %s %s', exc.__class__.__name__, body or exc)
        return None

    snapshot = GoogleReviewSnapshot.objects.create(
        rating=rating,
        review_count=int(place.get('userRatingCount') or 0),
        reviews=[_review(r) for r in place.get('reviews', [])],
        maps_url=place.get('googleMapsUri', '')[:500],
    )
    GoogleReviewSnapshot.objects.filter(
        fetched_at__lt=timezone.now() - timedelta(days=KEEP_REVIEW_TEXT_DAYS),
    ).update(reviews=[])
    return snapshot


def _review(review):
    """Keep only what the dashboard shows, and Google's attribution for it."""
    author = review.get('authorAttribution') or {}
    text = review.get('text') or review.get('originalText') or {}
    return {
        'author': author.get('displayName', 'A Google user'),
        'author_url': author.get('uri', ''),
        'rating': int(review.get('rating') or 0),
        'text': text.get('text', ''),
        'when': review.get('relativePublishTimeDescription', ''),
        'published': review.get('publishTime', ''),
        'url': review.get('googleMapsUri', ''),
    }


def new_review_counts(periods):
    """How many reviews arrived in each (label, start, end) period.

    The rise in Google's count from the last snapshot before the period starts to
    the last one before it ends. Never below 0: Google sometimes removes reviews.
    Periods with no earlier snapshot to compare against count as 0.
    """
    counts = []
    snapshots = GoogleReviewSnapshot.objects.order_by('-fetched_at')
    for _, start, end in periods:
        before = snapshots.filter(fetched_at__lt=start).first()
        last = snapshots.filter(fetched_at__lt=end).first()
        counts.append(max(0, last.review_count - before.review_count) if before and last else 0)
    return counts
