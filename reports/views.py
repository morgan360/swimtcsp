from django.shortcuts import render
from django.http import HttpResponse
import datetime
from utils import terms_utils


def show_todays_date(request):
    term = terms_utils.get_current_term()
    today = datetime.date.today()
    return render(request, 'reports/todays_date.html', {'today': today, 'current_term': term})
