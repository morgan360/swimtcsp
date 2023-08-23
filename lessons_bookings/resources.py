from import_export import resources, fields
from .models import Term
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

    # def dehydrate_start(self, term):
    #     return term.assesment_date.strftime('%Y-%m-%d') if term.assesment_date else ''
    #
    # def dehydrate_rebook_start(self, term):
    #     return term.rebooking_date.strftime('%Y-%m-%d') if term.rebooking_date else ''
    #
    # def dehydrate_booking_switch_date(self, term):
    #     return term.booking_date.strftime('%Y-%m-%d') if term.booking_date else ''