from datetime import date, datetime
from django.utils import formats
from .models import Term


def current_term(request):
    today = date.today()
    current_term = Term.objects.filter(start_date__lte=today,
                                       end_date__gte=today).first()

    # Include formatted term information
    if current_term:
        current_term_formatted = f"{current_term.id}, {formats.date_format(current_term.start_date, 'd M Y')} - " \
                                 f"{formats.date_format(current_term.end_date, 'd M Y')}"
    else:
        current_term_formatted = None

    return {'current_term': current_term,
            'current_term_formatted': current_term_formatted}

