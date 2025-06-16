from datetime import date, timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from timetable.models import TimetableOverride
from lessons.models import Product
from swims.models import PublicSwimProduct
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

    # 📘 Generate lessons from Products
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
                    "date": current_date,
                    "start": product.start_time,
                    "end": product.end_time,
                })

    # 🧾 Timetable overrides
    override_items = TimetableOverride.objects.filter(date__range=(start, end))
    override_events = [
        {
            "title": override.title,
            "type": override.event_type,
            "date": override.date,
            "start": override.start_time,
            "end": override.end_time,
        }
        for override in override_items
    ]

    return Response({
        "start": start,
        "end": end,
        "events": lesson_events + override_events,
    })
