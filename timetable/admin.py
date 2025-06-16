from django.contrib import admin
from .models import TimetableOverride

@admin.register(TimetableOverride)
class TimetableOverrideAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'date', 'start_time', 'end_time', 'created_by')
    list_filter = ('event_type', 'date')
    search_fields = ('title', 'notes')

