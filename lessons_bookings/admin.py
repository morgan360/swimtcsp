from django.contrib import admin
from import_export.admin import ImportExportMixin
from .models import Term
from .resources import TermResource


class TermAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = TermResource
    list_display = ['term_id', 'start', 'end', 'rebooking',
                    'booking', 'assessments']


admin.site.register(Term, TermAdmin)
