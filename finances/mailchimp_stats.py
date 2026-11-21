"""Newsletter figures from Mailchimp, for the Live Dashboard.

Fetched at most every REFRESH_HOURS and kept in the cache, with a second copy
that never expires: if Mailchimp can't be reached the dashboard shows the last
good figures, and it must never fail because of Mailchimp (the same approach as
finances.google_performance).
"""
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger('finances')

REFRESH_HOURS = 6
PERIOD_DAYS = 30
RECENT_CAMPAIGNS = 5
CACHE_KEY = 'mailchimp_stats_v1'
LAST_GOOD_KEY = 'mailchimp_stats_v1_last_good'

INFO = {
    'Subscribers': "Everyone on the Mailchimp audience who is currently subscribed and can be emailed.",
    'Joined': f"Contacts who subscribed in the last {PERIOD_DAYS} days, from any source: the homepage box, "
              "the tick-box on the booking site, or added in Mailchimp.",
    'Left': f"Contacts who unsubscribed in the last {PERIOD_DAYS} days.",
    'Dropped': "Addresses Mailchimp has stopped sending to because the email bounced. All time.",
    'Opened': "Average share of each email's recipients who opened it, across every email sent to this "
              "audience. Apple Mail opens emails automatically for privacy, which makes this read high.",
    'Clicked': "Average share of each email's recipients who clicked a link in it.",
}


def configured():
    return bool(getattr(settings, 'MAILCHIMP_API_KEY', '') and getattr(settings, 'MAILCHIMP_LIST_ID', ''))


def summary():
    """The figures for the dashboard, or None when not set up or never fetched."""
    if not configured():
        return None
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    fresh = fetch()
    if fresh is None:
        return cache.get(LAST_GOOD_KEY)
    cache.set(CACHE_KEY, fresh, REFRESH_HOURS * 3600)
    cache.set(LAST_GOOD_KEY, fresh, None)
    return fresh


def fetch(now=None):
    """Ask Mailchimp for the audience and recent emails. None on failure."""
    from mailchimp.client import get_mailchimp_client

    now = now or timezone.now()
    since = (now - timedelta(days=PERIOD_DAYS)).isoformat()
    list_id = settings.MAILCHIMP_LIST_ID
    try:
        client = get_mailchimp_client()
        stats = client.lists.get_list(list_id, fields=['stats'])['stats']
        joined = client.lists.get_list_members_info(
            list_id, count=1, status='subscribed', since_timestamp_opt=since, fields=['total_items'])['total_items']
        left = client.lists.get_list_members_info(
            list_id, count=1, status='unsubscribed', unsubscribed_since=since, fields=['total_items'])['total_items']
        campaigns = client.campaigns.list(
            count=RECENT_CAMPAIGNS, status='sent', list_id=list_id, sort_field='send_time', sort_dir='DESC',
            fields=['campaigns.settings.subject_line', 'campaigns.send_time', 'campaigns.emails_sent',
                    'campaigns.report_summary', 'campaigns.long_archive_url'])['campaigns']
    except Exception as exc:  # noqa: BLE001 - the SDK raises its own types and plain HTTP errors
        logger.error('Mailchimp stats fetch failed: %s %s', exc.__class__.__name__,
                     (getattr(exc, 'text', '') or str(exc))[:300])
        return None

    def figure(label, value, kind='count'):
        return {'label': label, 'value': value, 'kind': kind, 'info': INFO[label]}

    return {
        'fetched_at': now,
        'days': PERIOD_DAYS,
        'figures': [
            figure('Subscribers', stats.get('member_count', 0)),
            figure('Joined', joined),
            figure('Left', left),
            figure('Dropped', stats.get('cleaned_count', 0)),
            figure('Opened', round(stats.get('open_rate') or 0), 'pct'),
            figure('Clicked', round(stats.get('click_rate') or 0, 1), 'pct'),
        ],
        'last_sent': _when(stats.get('campaign_last_sent')),
        'campaigns': [_campaign(c) for c in campaigns],
    }


def _when(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    return parsed if isinstance(parsed, datetime) else None


def _campaign(c):
    report = c.get('report_summary') or {}
    return {
        'subject': (c.get('settings') or {}).get('subject_line', ''),
        'sent': _when(c.get('send_time')),
        'recipients': c.get('emails_sent', 0),
        # Mailchimp gives these as fractions in a report, percentages in list stats.
        'opened': round((report.get('open_rate') or 0) * 100),
        'clicked': round((report.get('click_rate') or 0) * 100),
        'url': c.get('long_archive_url') or '',
    }


def opted_in_on_site():
    """Customers who ticked "News by email" on the booking site (not cached: one cheap query)."""
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(marketing_opt_in=True, anonymised_at__isnull=True).count()
