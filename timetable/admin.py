from django.contrib import admin

from custom_admins.base import TCSPModelAdmin
from custom_admins.panels import operations_site

from .models import CalendarEvent


class CalendarEventAdmin(TCSPModelAdmin):
    """Closures entered here show on the public timetable and homepage, and stop
    public swims being booked for those days. The other categories only appear
    on the staff calendar."""

    list_display = ['title', 'category', 'affects', 'start_date', 'end_date']
    list_filter = ['category', 'affects']
    search_fields = ['title', 'description']
    date_hierarchy = 'start_date'
    ordering = ['-start_date']
    fields = ['category', 'title', 'affects', 'start_date', 'end_date', 'description']

    def get_changeform_initial_data(self, request):
        # Closures are what staff add here day to day.
        return {'category': 'closure', **super().get_changeform_initial_data(request)}


# Every staff member can record a closure, so it lives in Operations.
operations_site.register(CalendarEvent, CalendarEventAdmin)
