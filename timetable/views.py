from django.shortcuts import render
from django.utils import timezone

from .year import year_calendar


def timetable_grid(request):
    return render(request, "timetable/timetable_grid.html", {
        "year": year_calendar(timezone.localdate()),
    })


def calendar_page(request):
    # The detailed FullCalendar view (school terms, booking pause), for staff.
    return render(request, 'timetable/calendar_overview.html')
