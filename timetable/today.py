"""What is on at the pool on a given day, for the homepage strip."""
from django.db.models import Sum
from django.urls import reverse

from lessons.models import Product
from swims.models import PublicSwimProduct
from swims_orders.models import OrderItem as SwimOrderItem

from .closures import closure_for, closures_between, closures_on
from .models import CalendarEvent


def booked_swimmers(start, end):
    """Paid swimmers per (product id, date), counted as the dashboard's swims
    dial counts them (finances.views._live_dials)."""
    return {
        (row['order__product_id'], row['order__booking']): row['n']
        for row in SwimOrderItem.objects.filter(order__paid=True, order__booking__range=(start, end))
        .exclude(order__payment_status='refunded')
        .values('order__product_id', 'order__booking').annotate(n=Sum('quantity'))
    }


def places_left(product, day, booked):
    if product.num_places is None:
        return None
    return max(product.num_places - booked.get((product.id, day), 0), 0)


def at_the_pool(day, now_time=None):
    """The day's answer: closed (and why) or open, with its public swims.

    ``now_time`` marks swims that are over or on now; leave it out for another day.
    """
    closures = closures_between(day, day)
    swim_closure = closure_for('swim', day, closures)
    lesson_closure = closure_for('lesson', day, closures)
    booked = booked_swimmers(day, day)

    swims = []
    for product in (PublicSwimProduct.objects.filter(available=True, day_of_week=day.weekday())
                    .select_related('category').order_by('start_time')):
        state = ''
        if now_time is not None:
            if product.end_time <= now_time:
                state = 'over'
            elif product.start_time <= now_time:
                state = 'now'
        swims.append({
            'start': product.start_time,
            'end': product.end_time,
            'name': product.category.name,
            'places_left': places_left(product, day, booked),
            'book_url': reverse('swims:product_detail', args=[product.id, product.slug]),
            'state': state,
        })
    upcoming = [s for s in swims if s['state'] != 'over']
    if upcoming and now_time is not None and upcoming[0]['state'] != 'now':
        upcoming[0]['state'] = 'next'

    has_lessons = Product.objects.filter(active=True, day_of_week=day.weekday()).exists()
    whole = next((c for c in closures_on(day, closures) if c.affects == CalendarEvent.AFFECTS_ALL), None)
    return {
        'day': day,
        'closed': whole,
        'swim_closure': swim_closure,
        'lesson_closure': lesson_closure,
        'swims': [] if swim_closure else upcoming,
        'has_lessons': has_lessons and not lesson_closure,
        'swims_finished': bool(swims) and not upcoming and not swim_closure,
    }
