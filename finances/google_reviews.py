"""The pool's Google rating and review count, for the Live Dashboard.

Read from the Places API (New) at most every REFRESH_HOURS and kept as
GoogleReviewSnapshot rows, whose rising count gives "new reviews today / this
week". The Places API can't sort reviews by newest (it gives the five Google
ranks most relevant, for the pool 3-9 years old), so the latest reviews come
from the Google Business Profile API instead, when its GBP_* settings are set.
Only the reviewer's first name is kept. If Google can't be reached the
dashboard gets the last good snapshot: it must never fail because of Google.
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
FIELD_MASK = 'rating,userRatingCount,googleMapsUri'  # no reviews: see above
REFRESH_HOURS = 6
TIMEOUT_SECONDS = 5

GBP_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GBP_REVIEWS_URL = 'https://mybusiness.googleapis.com/v4/accounts/{account}/locations/{location}/reviews'
LATEST_REVIEWS = 3
STARS = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5}


def configured():
    return bool(settings.GOOGLE_PLACES_API_KEY and settings.GOOGLE_PLACE_ID)


def reviews_configured():
    return all([settings.GBP_CLIENT_ID, settings.GBP_CLIENT_SECRET, settings.GBP_REFRESH_TOKEN,
                settings.GBP_ACCOUNT_ID, settings.GBP_LOCATION_ID])


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
    """Ask Google for the rating and review count and save a snapshot. None on failure."""
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

    latest = fetch_latest_reviews() if reviews_configured() else []
    if latest is None:  # Business Profile failed: keep the reviews we last had
        previous = GoogleReviewSnapshot.objects.first()
        latest = previous.latest_reviews if previous else []

    snapshot = GoogleReviewSnapshot.objects.create(
        rating=rating,
        review_count=int(place.get('userRatingCount') or 0),
        maps_url=place.get('googleMapsUri', '')[:500],
        latest_reviews=latest,
    )
    return snapshot


def gbp_access_token():
    """A short-lived Business Profile access token from the stored refresh token.

    Raises requests.RequestException / KeyError on failure, for the caller to log.
    Also used by finances.google_performance.
    """
    token = requests.post(GBP_TOKEN_URL, data={
        'client_id': settings.GBP_CLIENT_ID,
        'client_secret': settings.GBP_CLIENT_SECRET,
        'refresh_token': settings.GBP_REFRESH_TOKEN,
        'grant_type': 'refresh_token',
    }, timeout=TIMEOUT_SECONDS)
    token.raise_for_status()
    return token.json()['access_token']


def fetch_latest_reviews():
    """The newest LATEST_REVIEWS reviews from the Business Profile API. None on failure."""
    try:
        response = requests.get(
            GBP_REVIEWS_URL.format(account=settings.GBP_ACCOUNT_ID, location=settings.GBP_LOCATION_ID),
            headers={'Authorization': f'Bearer {gbp_access_token()}'},
            params={'pageSize': LATEST_REVIEWS, 'orderBy': 'updateTime desc'},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        reviews = response.json().get('reviews', [])
    except (requests.RequestException, ValueError, KeyError) as exc:
        # Google's error bodies never echo the secret or tokens. "invalid_grant"
        # means the refresh token was revoked: redo the one-off sign-in.
        body = getattr(getattr(exc, 'response', None), 'text', '')[:300]
        logger.error('Google latest reviews fetch failed: %s %s', exc.__class__.__name__, body or exc)
        return None
    return [_review(r) for r in reviews[:LATEST_REVIEWS]]


def _review(review):
    reviewer = review.get('reviewer') or {}
    name = (reviewer.get('displayName') or '').split()
    return {
        'first_name': name[0] if name and not reviewer.get('isAnonymous') else '',
        'stars': STARS.get(review.get('starRating'), 0),
        'date': (review.get('createTime') or '')[:10],
        'text': _own_words(review.get('comment', '')),
        'replied': bool(review.get('reviewReply')),
    }


def _own_words(comment):
    """Google's translation of a review if it added one, otherwise the review as written.

    A translated review comes as "(Translated by Google) <English>\n\n(Original)\n<original>".
    """
    comment = comment.strip()
    if comment.startswith('(Translated by Google)'):
        comment = comment[len('(Translated by Google)'):].split('(Original)')[0]
    return comment.strip()


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
