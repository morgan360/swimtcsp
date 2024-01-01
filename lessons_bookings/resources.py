from import_export import resources, fields
from .models import Term, LessonEnrollment
from datetime import datetime
from import_export.results import RowResult


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


class EnrollmentResource(resources.ModelResource):
    class Meta:
        model = LessonEnrollment
        import_id_fields = ('id',)
        fields = ('id', 'term', 'swimling', 'lesson', 'notes', 'created', 'updated', 'changed_by')

    def import_row(self, row, instance_loader, **kwargs):
        import_result = super().import_row(row, instance_loader, **kwargs)

        if import_result.import_type == RowResult.IMPORT_TYPE_ERROR:
            # Manually construct field names list
            field_names = self._meta.fields

            # Log the row values and the errors
            import_result.diff = [row.get(name, '') for name in field_names]
            import_result.diff.append("Errors: {}".format(", ".join([str(err.error) for err in import_result.errors])))

            # Clear errors and mark the record to skip
            import_result.errors = []
            import_result.import_type = RowResult.IMPORT_TYPE_SKIP

        return import_result
