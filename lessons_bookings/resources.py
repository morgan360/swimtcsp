from import_export import resources, fields
from .models import Term, LessonEnrollment
from datetime import datetime


class TermResource(resources.ModelResource):
    term_id = fields.Field(attribute='id')
    start_date = fields.Field(attribute='start_date')
    finish_date = fields.Field(attribute='end_date')
    rebook_start = fields.Field(attribute='rebooking_date')
    booking_switch_date = fields.Field(attribute='booking_date')
    assesments_complete = fields.Field(attribute='assesment_date')

    class Meta:
        model = Term
        import_id_fields = 'term_id',
        fields = (' term_id', 'start_date', 'finish_date', 'rebook_start',
                  'booking_switch_date', 'assesments_complete')

    # Import Bookings from TCSP


class EnrollementResource(resources.ModelResource):
    class Meta:
        model = LessonEnrollment
        import_id_fields = ('id',)
        fields = ('id', 'term', 'swimling', 'lesson', 'notes', 'created', 'updated', 'changed_by')
