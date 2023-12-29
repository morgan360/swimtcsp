from datetime import datetime
from django.utils import formats
from lessons_bookings.models import Term
from .terms_utils import get_current_term


def get_term(request):
    term = get_current_term()
    c_term = term.concatenated_term()
    return {'term': c_term}


# Different Footor for each version production ,local
def footer_message(request):
    from django.conf import settings
    return {'FOOTER_MESSAGE': settings.FOOTER_MESSAGE}
