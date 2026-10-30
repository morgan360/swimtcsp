"""The 12-month calendar customers see: when lessons start, when rebooking and
booking open, and when the pool or lessons are off.

Deliberately little else. The old FullCalendar view showed term bars from the
1st to the last of the month, school terms and the booking pause, and Esther hid
it because parents read the term dates as class dates. Here a term shows only as
the day its lessons actually start.
"""
import calendar
from datetime import date, timedelta

from lessons.models import Product
from lessons_bookings.models import Term

from .closures import CLOSURE_LABELS, closure_for, closures_between
from .models import CalendarEvent

LESSONS_START, REBOOKING, BOOKING = 'start', 'rebooking', 'booking'
CLOSED, PARTIAL = 'closed', 'partial'  # whole pool / only lessons or only swims

LEGEND = [
    (LESSONS_START, 'Lessons start'),
    (REBOOKING, 'Rebooking opens (current members)'),
    (BOOKING, 'Booking opens to everyone'),
    (CLOSED, 'Pool closed'),
    (PARTIAL, 'No lessons or no public swims'),
]

# What is still running during a partial closure.
STILL_ON = {
    CalendarEvent.AFFECTS_LESSONS: 'public swims on',
    CalendarEvent.AFFECTS_SWIMS: 'lessons on',
}


def _closure_event(closure, start, end):
    label = f"{CLOSURE_LABELS.get(closure.affects, 'Closed')}: {closure.title}"
    still_on = STILL_ON.get(closure.affects)
    return (max(closure.start_date, start), min(closure.end_date or closure.start_date, end),
            PARTIAL if still_on else CLOSED, f"{label} ({still_on})" if still_on else label)


def _when(first, last):
    """"Thu 31 Dec", "24–27 Dec" or "28 Dec – 2 Jan"."""
    if first == last:
        return f"{first:%a} {first.day} {first:%b}"
    if (first.year, first.month) == (last.year, last.month):
        return f"{first.day}–{last.day} {last:%b}"
    return f"{first.day} {first:%b} – {last.day} {last:%b}"


def _add_months(day, months):
    month = day.month - 1 + months
    return date(day.year + month // 12, month % 12 + 1, 1)


def first_lesson_day(term, lesson_days, closures):
    """The first day from the term's start that has a lesson and isn't closed
    for lessons. A term starting on the 1st often has its first class days later."""
    day, last = term.start_date, term.end_date or term.start_date + timedelta(days=60)
    while day <= last:
        if day.weekday() in lesson_days and not closure_for('lesson', day, closures):
            return day
        day += timedelta(days=1)
    return None


def year_calendar(today, months=12):
    start = date(today.year, today.month, 1)
    end = _add_months(start, months) - timedelta(days=1)
    closures = closures_between(start, end)
    lesson_days = set(Product.objects.filter(active=True).values_list('day_of_week', flat=True))

    events = []  # (first day, last day, kind, label)
    for term in Term.objects.filter(start_date__isnull=False).order_by('start_date'):
        lessons_start = first_lesson_day(term, lesson_days, closures)
        for day, kind, label in ((lessons_start, LESSONS_START, 'Lessons start'),
                                 (term.rebooking_date, REBOOKING, 'Rebooking opens for current members'),
                                 (term.booking_date, BOOKING, 'Booking opens to everyone')):
            if day and start <= day <= end:
                events.append((day, day, kind, label))
    events.extend(_closure_event(closure, start, end) for closure in closures)
    events.sort(key=lambda e: (e[0], e[1]))

    marks = {}
    for first, last, kind, label in events:
        day = first
        while day <= last:
            marks.setdefault(day, []).append({'kind': kind, 'label': label})
            day += timedelta(days=1)

    weeks_of = calendar.Calendar(firstweekday=0).monthdatescalendar
    month_list = []
    for offset in range(months):
        first = _add_months(start, offset)
        month_list.append({
            'first': first,
            'weeks': [
                [{'date': d, 'in_month': d.month == first.month, 'is_today': d == today,
                  'marks': marks.get(d, []) if d.month == first.month else []}
                 for d in week]
                for week in weeks_of(first.year, first.month)
            ],
        })

    key_dates = [{'first': first, 'last': last, 'when': _when(first, last), 'kind': kind, 'label': label,
                  'is_closure': kind in (CLOSED, PARTIAL)}
                 for first, last, kind, label in events]
    upcoming = [k for k in key_dates if k['last'] >= today]
    return {'months': month_list, 'key_dates': key_dates, 'upcoming': upcoming, 'legend': LEGEND}
