"""Counting how often the timetable is used (timetable.models.PageVisit)."""
import re

from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from utils.terms_utils import acting_as_staff

from .models import PageVisit

PAGES = {key for key, _ in PageVisit.PAGE_CHOICES}

# Crawlers and tools, which fill the server logs with requests for the old
# WordPress site; a request with no user agent at all is one of them too.
BOT_AGENT = re.compile(
    r"bot|crawl|spider|slurp|preview|monitor|headless|curl|wget|python|scrapy|"
    r"httpclient|java/|go-http|facebookexternalhit|lighthouse",
    re.IGNORECASE,
)


def count_visit(request, page):
    """Add one to today's count for ``page``, unless staff or a bot is asking."""
    if page not in PAGES:
        return
    agent = request.META.get('HTTP_USER_AGENT', '')
    if not agent or BOT_AGENT.search(agent) or acting_as_staff(request):
        return
    today = timezone.localdate()
    if PageVisit.objects.filter(date=today, page=page).update(count=F('count') + 1):
        return
    try:
        with transaction.atomic():
            PageVisit.objects.create(date=today, page=page, count=1)
    except IntegrityError:
        # Another request created today's row first.
        PageVisit.objects.filter(date=today, page=page).update(count=F('count') + 1)


def visit_totals(pages, start, end):
    """Total count for ``pages`` from ``start`` up to, not including, ``end`` (dates)."""
    return (PageVisit.objects.filter(page__in=pages, date__gte=start, date__lt=end)
            .aggregate(n=Sum('count'))['n'] or 0)
