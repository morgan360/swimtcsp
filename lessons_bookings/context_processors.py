from datetime import date, datetime
from django.utils import formats
from .models import Term


def current_term(request):
    today = date.today()
    current_term = Term.objects.filter(start__lte=today,
                                       end__gte=today).first()

    # Include formatted term information
    if current_term:
        current_term_formatted = f"{current_term.term_id}, {formats.date_format(current_term.start, 'd M Y')} - {formats.date_format(current_term.end, 'd M Y')}"
    else:
        current_term_formatted = None

    return {'current_term': current_term,
            'current_term_formatted': current_term_formatted}

