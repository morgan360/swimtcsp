from custom_admins.base import TCSPModelAdmin
from custom_admins.panels import settings_site

from .models import SecurityIncident


class SecurityIncidentAdmin(TCSPModelAdmin):
    list_display = ['created', 'kind', 'ip', 'path']
    list_filter = ['kind']
    search_fields = ['ip', 'path']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


settings_site.register(SecurityIncident, SecurityIncidentAdmin)
