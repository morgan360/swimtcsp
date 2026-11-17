"""How people find the pool on Google, for the Live Dashboard.

From the Business Profile Performance API, using the same GBP_* sign-in as the
latest reviews (finances.google_reviews). Google's daily figures run 3-4 days
behind, so the dashboard compares the last PERIOD_DAYS days Google has figures
for with the PERIOD_DAYS before them, rather than showing "today".

Fetched at most every REFRESH_HOURS and kept in the cache, with a second copy
that never expires: if Google can't be reached the dashboard shows the last
good figures, and it must never fail because of Google.
"""
import logging
from datetime import date, timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from finances import google_reviews

logger = logging.getLogger('finances')

DAILY_URL = ('https://businessprofileperformance.googleapis.com/v1/locations/{location}'
             ':fetchMultiDailyMetricsTimeSeries')
KEYWORDS_URL = ('https://businessprofileperformance.googleapis.com/v1/locations/{location}'
                '/searchkeywords/impressions/monthly')
PERIOD_DAYS = 28
REFRESH_HOURS = 12
TOP_SEARCHES = 10
CACHE_KEY = 'google_performance_v1'
LAST_GOOD_KEY = 'google_performance_v1_last_good'

VIEWS = {
    'BUSINESS_IMPRESSIONS_MOBILE_MAPS': 'Maps, phone',
    'BUSINESS_IMPRESSIONS_MOBILE_SEARCH': 'Search, phone',
    'BUSINESS_IMPRESSIONS_DESKTOP_MAPS': 'Maps, computer',
    'BUSINESS_IMPRESSIONS_DESKTOP_SEARCH': 'Search, computer',
}
ACTIONS = {
    'WEBSITE_CLICKS': 'Website clicks',
    'BUSINESS_DIRECTION_REQUESTS': 'Directions',
    'CALL_CLICKS': 'Calls',
}
# The "i" pop-up for each figure on the dashboard.
INFO = {
    'Views of the listing': ("How often the pool's Google listing was shown, on Google Search or Google Maps, "
                             "on phones and computers. Google counts each person at most once a day on each of "
                             "these, so it's close to people rather than page loads."),
    'Website clicks': "Clicks on the website link in the pool's Google listing.",
    'Directions': "Requests for directions to the pool from its Google listing.",
    'Calls': ("Taps on the call button in the pool's Google listing. Google can't tell whether the call went "
              "through or was answered."),
}

# People searching for the pool by its name or address, which Google lists as
# many near-identical spellings of the address. Shown as one line.
BY_NAME = 'templeogue college swimming pool'


def summary():
    """The figures for the dashboard, or None when not set up or never fetched."""
    if not google_reviews.reviews_configured():
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


def fetch(today=None):
    """Ask Google for the daily figures and last month's searches. None on failure."""
    today = today or timezone.localdate()
    start = today - timedelta(days=2 * PERIOD_DAYS + 10)  # room for Google's lag
    try:
        headers = {'Authorization': f'Bearer {google_reviews.gbp_access_token()}'}
        location = _location()
        daily = requests.get(
            DAILY_URL.format(location=location), headers=headers,
            params=[('dailyMetrics', m) for m in [*VIEWS, *ACTIONS]] + _range('dailyRange', start, today),
            timeout=google_reviews.TIMEOUT_SECONDS)
        daily.raise_for_status()
        series = _series(daily.json())

        month_end = today.replace(day=1) - timedelta(days=1)  # last complete month
        keywords = requests.get(
            KEYWORDS_URL.format(location=location), headers=headers,
            params={'monthlyRange.startMonth.year': month_end.year, 'monthlyRange.startMonth.month': month_end.month,
                    'monthlyRange.endMonth.year': month_end.year, 'monthlyRange.endMonth.month': month_end.month,
                    'pageSize': 100},
            timeout=google_reviews.TIMEOUT_SECONDS)
        keywords.raise_for_status()
        searches = _searches(keywords.json())
    except (requests.RequestException, ValueError, KeyError) as exc:
        body = getattr(getattr(exc, 'response', None), 'text', '')[:300]
        logger.error('Google performance fetch failed: %s %s', exc.__class__.__name__, body or exc)
        return None

    dated = [d for values in series.values() for d in values]
    if not dated:
        return None
    through = max(dated)
    now_from = through - timedelta(days=PERIOD_DAYS - 1)
    before_from = now_from - timedelta(days=PERIOD_DAYS)

    def total(metric, first, last):
        return sum(v for d, v in series.get(metric, {}).items() if first <= d <= last)

    def figure(label, metrics):
        now = sum(total(m, now_from, through) for m in metrics)
        before = sum(total(m, before_from, now_from - timedelta(days=1)) for m in metrics)
        change = round((now - before) * 100 / before) if before else None
        return {'label': label, 'now': now, 'before': before, 'change': change, 'info': INFO.get(label, '')}

    return {
        'fetched_at': timezone.now(),
        'from': now_from,
        'through': through,
        'days': PERIOD_DAYS,
        'figures': [figure('Views of the listing', list(VIEWS))]
                   + [figure(label, [metric]) for metric, label in ACTIONS.items()],
        'views_split': [figure(label, [metric]) for metric, label in VIEWS.items()],
        'searches_month': month_end,
        'searches': searches,
    }


def _location():
    return settings.GBP_LOCATION_ID


def _range(name, start, end):
    params = []
    for edge, day in (('startDate', start), ('endDate', end)):
        params += [(f'{name}.{edge}.year', day.year), (f'{name}.{edge}.month', day.month),
                   (f'{name}.{edge}.day', day.day)]
    return params


def _series(payload):
    """{metric: {date: value}} for the days Google has a figure for."""
    out = {}
    for group in payload.get('multiDailyMetricTimeSeries', []):
        for metric in group.get('dailyMetricTimeSeries', []):
            values = out.setdefault(metric['dailyMetric'], {})
            for point in metric.get('timeSeries', {}).get('datedValues', []):
                if 'value' in point:
                    d = point['date']
                    values[date(d['year'], d['month'], d['day'])] = int(point['value'])
    return out


def _searches(payload):
    """The top searches, biggest first. Google gives small counts only as "under N"."""
    by_name, rows = 0, []
    for row in payload.get('searchKeywordsCounts', []):
        term = row.get('searchKeyword', '')
        value = row.get('insightsValue', {})
        if 'value' in value:
            count, under = int(value['value']), False
        else:
            count, under = int(value.get('threshold', 0)), True
        if term.lower().replace(',', '').startswith(BY_NAME):
            by_name += 0 if under else count  # "under N" can't be added up
        else:
            rows.append({'term': term, 'count': count, 'under': under})
    if by_name:
        rows.append({'term': 'The pool by name or address', 'count': by_name, 'under': False})
    # Exact counts before "under N" ones, then biggest first.
    rows.sort(key=lambda r: (r['under'], -r['count']))
    return rows[:TOP_SEARCHES]
