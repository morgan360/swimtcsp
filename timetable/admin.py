
from django.contrib import admin
from .models import CalendarEvent
from custom_admins.base import TCSPModelAdmin

@admin.register(CalendarEvent)
class CalendarEventAdmin(TCSPModelAdmin):
    list_display = ['title', 'category', 'start_date', 'end_date']
    list_filter = ['category']
    search_fields = ['title', 'description']
