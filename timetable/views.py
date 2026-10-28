from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from swims.models import PublicSwimProduct

from .models import PageVisit
from .visits import count_visit
from .year import year_calendar


def timetable_grid(request):
    count_visit(request, PageVisit.TIMETABLE)
    return render(request, "timetable/timetable_grid.html", {
        "year": year_calendar(timezone.localdate()),
    })


# The tabs switch in the browser without loading a page, so timetable.js pings
# this when one is shown. Exempt from CSRF: it can only add one to a known
# counter, and navigator.sendBeacon sends no token.
@csrf_exempt
@require_POST
def tab_seen(request):
    count_visit(request, f"tab:{request.POST.get('tab', '')}")
    return HttpResponse(status=204)


def book_swim(request, product_id):
    """A Book button on the timetable or homepage card: counted here, then on to
    the booking page. A redirect rather than a ping, so clicks are counted
    without JavaScript and before the login page for anyone not signed in."""
    product = get_object_or_404(PublicSwimProduct, id=product_id, available=True)
    if request.GET.get('via') in ('timetable', 'home'):
        count_visit(request, f"book:{request.GET['via']}")
    return redirect('swims:product_detail', id=product.id, slug=product.slug)


def calendar_page(request):
    # The detailed FullCalendar view (school terms, booking pause), for staff.
    return render(request, 'timetable/calendar_overview.html')
