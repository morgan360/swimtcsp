from import_export import resources, fields
from .models import Term, LessonEnrollment
from datetime import datetime
from import_export.results import RowResult
from utils.sync_terms import sync_terms_from_remote

class TermResource(resources.ModelResource):
    term_id = fields.Field(attribute='id', column_name='term_id')
    start_date = fields.Field(attribute='start_date', column_name='start_date')
    finish_date = fields.Field(attribute='end_date', column_name='finish_date')
    rebook_start = fields.Field(attribute='rebooking_date', column_name='rebook_start')
    booking_switch_date = fields.Field(attribute='booking_date', column_name='booking_switch_date')
    assessment_date = fields.Field(attribute='assessment_date', column_name='assesments_complete')

    class Meta:
        model = Term
        import_id_fields = ('term_id',)
        fields = (
            'term_id',
            'start_date',
            'finish_date',
            'rebook_start',
            'booking_switch_date',
            'assessment_date',
        )

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        sync_terms_from_remote()
        return super().before_import(dataset, using_transactions, dry_run, **kwargs)

    def clean_date(self, value):
        if value in ("0000-00-00", None, ""):
            return None
        return value

    def before_import_row(self, row, **kwargs):
        row["start_date"] = self.clean_date(row.get("start_date"))
        row["finish_date"] = self.clean_date(row.get("finish_date"))
        row["rebook_start"] = self.clean_date(row.get("rebook_start"))
        row["booking_switch_date"] = self.clean_date(row.get("booking_switch_date"))
        row["assesments_complete"] = self.clean_date(row.get("assesments_complete"))


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
