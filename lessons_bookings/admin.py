from django.contrib import admin
from import_export.admin import ImportExportMixin
from .models import Term
# from .resources import TermsResource


# class TermsAdmin(ImportExportMixin, admin.ModelAdmin):
#     resource_class = TermsResource
#     list_display = ['term_id', 'start_date', 'end_date', 'rebooking_date',
#                     'booking_date', 'assessments_date']
#
#
# admin.site.register(Term, TermsAdmin)
