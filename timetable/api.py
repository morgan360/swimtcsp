from datetime import date, timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from lessons.models import Product
from swims.models import PublicSwimProduct
from .models import CalendarEvent
from lessons_bookings.models import Term
from schools_bookings.models import ScoTerm


@api_view(['GET'])
def public_timetable(request):
    start_str = request.GET.get('start')
    start = date.fromisoformat(start_str) if start_str else date.today()
    end = start + timedelta(days=6)

    products = PublicSwimProduct.objects.filter(available=True)
    events = []

    for offset in range(7):
        current_date = start + timedelta(days=offset)
        for product in products:
            if product.day_of_week == current_date.weekday():
                events.append({
                    "title": product.category.name,
                    "type": "swim",
                    "category": product.category.name.lower(),  # ← or .slug if preferred
                    "date": current_date.isoformat(),
                    "start": product.start_time.strftime('%H:%M'),
                    "end": product.end_time.strftime('%H:%M'),
                })

    return Response({
        "start": start,
        "end": end,
        "events": events,
    })


@api_view(['GET'])
def weekly_timetable(request):
    start_str = request.GET.get('start')
    start = date.fromisoformat(start_str) if start_str else date.today()
    end = start + timedelta(days=6)

    lesson_events = []
    products = Product.objects.filter(active=True)

    for offset in range(7):
        current_date = start + timedelta(days=offset)
        for product in products:
            if product.day_of_week == current_date.weekday():
                lesson_events.append({
                    "title": product.name,
                    "type": "lesson",
                    "category": product.category.slug,
                    "date": current_date.isoformat(),
                    "start": product.start_time.strftime('%H:%M'),
                    "end": product.end_time.strftime('%H:%M'),
                })

    return Response({
        "start": start,
        "end": end,
        "events": lesson_events,
    })


##### Calander ######


@api_view(['GET'])
def calendar_events(request):
    events = []

    # 1. Manual admin-defined events
    for event in CalendarEvent.objects.all():
        events.append({
            "title": event.title,
            "start": event.start_date.isoformat(),
            "end": event.end_date.isoformat() if event.end_date else event.start_date.isoformat(),
            "color": event.get_color(),
            "allDay": True,
            "extendedProps": {
                "category": event.category,
                "description": event.description,
            }
        })

    # 2. Dynamic Lesson Term events
    for term in Term.objects.all():
        label = term.concatenated_term() if hasattr(term, 'concatenated_term') else f"Term {term.id}"

        # Term duration
        events.append({
            "title": f"Lessons: {label}",
            "start": term.start_date.isoformat(),
            "end": term.end_date.isoformat(),
            "color": "#3B82F6",  # blue
            "allDay": True,
            "extendedProps": {
                "category": "lesson-term",
                "description": f"Lesson Term: {label}"
            }
        })

        # Rebooking phase
        if getattr(term, 'rebooking_date', None):
            events.append({
                "title": f"Rebooking Opens: {label}",
                "start": term.rebooking_date.isoformat(),
                "color": "#F59E0B",  # yellow
                "allDay": True,
                "extendedProps": {
                    "category": "lesson-rebooking",
                    "description": f"Rebooking for {label}"
                }
            })

        # Booking phase
        if getattr(term, 'booking_date', None):
            events.append({
                "title": f"Booking Opens: {label}",
                "start": term.booking_date.isoformat(),
                "color": "#84CC16",  # lime green
                "allDay": True,
                "extendedProps": {
                    "category": "lesson-booking",
                    "description": f"Booking opens for {label}"
                }
            })

    # 3. Dynamic School Terms
    for sterm in ScoTerm.objects.all():
        label = getattr(sterm, 'name', f"ScoTerm {sterm.id}")
        events.append({
            "title": f"School Term: {label}",
            "start": sterm.start_date.isoformat(),
            "end": sterm.end_date.isoformat(),
            "color": "#10B981",  # teal
            "allDay": True,
            "extendedProps": {
                "category": "school-term",
                "description": f"School Term: {label}"
            }
        })

    return Response(events)
