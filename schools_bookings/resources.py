from import_export import resources, fields
from .models import ScoTerm, ScoEnrollment
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
        model = ScoTerm
        import_id_fields = 'id',
        fields = ('id', 'start_date', 'end_date', 'booking_start_date',
                  'booking_end_date', 'assessment_date')

    # Import Bookings from TCSP


class EnrollmentResource(resources.ModelResource):
    class Meta:
        model = ScoEnrollment
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
