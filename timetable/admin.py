
from django.contrib import admin
from .models import CalendarEvent

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'start_date', 'end_date']
    list_filter = ['category']
    search_fields = ['title', 'description']
