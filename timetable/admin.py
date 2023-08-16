from django.contrib import admin
from .models import Events  # Import your model


class EventsAdminArea(admin.AdminSite):
    # site_header = "Events Area"
    # Change Site Labels
    site_header = "TCSP Events Management"
    site_title = "TCSP Events Management"
    index_title = "TCSP Events"


events_site = EventsAdminArea(name='EventsAdmin')


@admin.register(Events)
class YourModelNameAdmin(admin.ModelAdmin):
    pass


events_site.register(Events)
