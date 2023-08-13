from import_export import resources
from .models import Term


class TermResource(resources.ModelResource):
    class Meta:
        model = Term
        import_id_fields = 'term_id',
        fields = ('term_id', 'start', 'end', 'rebooking',
                  'booking', 'assessments')

