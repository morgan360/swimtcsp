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


# ✅ Export Bookings with readable fields



class EnrollmentResource(resources.ModelResource):
    # custom export-only fields
    swimling_name = fields.Field(column_name='Swimling')
    term_label = fields.Field(column_name='Term')
    lesson_name = fields.Field(column_name='Lesson')
    changed_by_name = fields.Field(column_name='Changed By')

    class Meta:
        model = LessonEnrollment
        import_id_fields = ('id',)
        # ✅ only include the custom field names here
        fields = (
            'id',
            'swimling_name',
            'term_label',
            'lesson_name',
            'notes',
            'created',
            'updated',
            'changed_by_name',
        )
        export_order = fields

    # ✅ hydrate fields with readable values
    def dehydrate_swimling_name(self, obj):
        return str(obj.swimling) if obj.swimling else ""

    def dehydrate_term_label(self, obj):
        return obj.term.label if obj.term else ""

    def dehydrate_lesson_name(self, obj):
        return str(obj.lesson) if obj.lesson else ""

    def dehydrate_changed_by_name(self, obj):
        return str(obj.changed_by) if obj.changed_by else "-"