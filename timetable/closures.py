"""Closures customers need to know about: bank holidays, midterm, Christmas.

Staff record them as CalendarEvents with category "closure" in Operations. The
timetable, the homepage and swim booking all read them from here, so they agree
on whether a day is open.
"""
from datetime import timedelta

from django.db.models import Q

from .models import CalendarEvent

# What each kind of session is stopped by.
STOPPED_BY = {
    'swim': (CalendarEvent.AFFECTS_ALL, CalendarEvent.AFFECTS_SWIMS),
    'lesson': (CalendarEvent.AFFECTS_ALL, CalendarEvent.AFFECTS_LESSONS),
}


CLOSURE_LABELS = {
    CalendarEvent.AFFECTS_ALL: 'Pool closed',
    CalendarEvent.AFFECTS_LESSONS: 'No lessons',
    CalendarEvent.AFFECTS_SWIMS: 'No public swims',
}


def closures_between(start, end):
    """Closures overlapping start..end inclusive, earliest first. A closure
    with no end date is the one day."""
    return list(
        CalendarEvent.objects.filter(category='closure', start_date__lte=end)
        .filter(Q(end_date__gte=start) | Q(end_date__isnull=True, start_date__gte=start))
        .order_by('start_date', 'id')
    )


def covers(closure, day):
    return closure.start_date <= day <= (closure.end_date or closure.start_date)


def closures_on(day, closures):
    return [c for c in closures if covers(c, day)]


def closure_for(kind, day, closures):
    """The closure that stops a 'swim' or 'lesson' on ``day``, or None."""
    for closure in closures_on(day, closures):
        if closure.affects in STOPPED_BY[kind]:
            return closure
    return None


def _day(d):
    return f"{d:%a} {d.day} {d:%b}"


def closures_text(today, days=42):
    """The coming closures as lines for the chatbot's prompt, e.g.
    "- Thu 29 Oct: Pool closed (Bank holiday)"; '' when there are none."""
    lines = []
    for closure in closures_between(today, today + timedelta(days=days)):
        first, last = closure.start_date, closure.end_date or closure.start_date
        when = _day(first) if last == first else f"{_day(first)} – {_day(last)}"
        lines.append(f"- {when}: {CLOSURE_LABELS.get(closure.affects, 'Closed')} ({closure.title})")
    return "\n".join(lines)
