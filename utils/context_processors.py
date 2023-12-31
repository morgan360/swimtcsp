from datetime import datetime
from django.utils import formats
from .terms_utils import get_current_term
from lessons_bookings.models import Term  # Import your Term model


def get_term(request):
    current_term = Term.get_current_term_id()

    if current_term is not None:
        term = Term.objects.get(id=current_term)
        term_string = term.concatenated_term()
    else:
        term_string = "No current term"

    return {'current_term': term_string}


# Different Footor for each version production ,local
def footer_message(request):
    from django.conf import settings
    return {'FOOTER_MESSAGE': settings.FOOTER_MESSAGE}
