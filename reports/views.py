from django.shortcuts import render
import datetime
from lessons_bookings.models import Term


def show_todays_date(request):
    current_term_id = Term.get_current_term_id()  # Get the ID of the current term

    if current_term_id is not None:
        try:
            current_term = Term.objects.get(id=current_term_id)
            current_term_string = current_term.concatenated_term()
            current_phase = current_term.determine_phase()

            # Fetch the previous and next term if they exist
            try:
                previous_term = Term.objects.get(id=current_term_id - 1)
                previous_term_string = previous_term.concatenated_term()
            except Term.DoesNotExist:
                previous_term_string = "No previous term"

            try:
                next_term = Term.objects.get(id=current_term_id + 1)
                next_term_string = next_term.concatenated_term()
            except Term.DoesNotExist:
                next_term_string = "No next term"
        except Term.DoesNotExist:
            current_term_string = "No current term"
            current_phase = "No current phase"
            previous_term_string = "No previous term"
            next_term_string = "No next term"
    else:
        current_term_string = "No current term"
        current_phase = "No current phase"
        previous_term_string = "No previous term"
        next_term_string = "No next term"

    today = datetime.date.today()

    return render(request, 'reports/todays_date.html', {
        'today': today,
        'current_term': current_term_string,
        'previous_term': previous_term_string,
        'next_term': next_term_string,
        'current_phase': current_phase,
    })
