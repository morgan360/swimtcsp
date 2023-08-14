from django.shortcuts import render
from datetime import timedelta, datetime
from lessons.models import Product

def lessons_cal_view(request):
    lessons = Product.objects.all()
    lesson_events = []

    today = datetime.now().date()
    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday",
                    "saturday", "sunday"]

    for lesson in lessons:
        day_offset = (lesson.day_of_week - today.weekday()) % 7
        start_date = today + timedelta(days=day_offset)

        # Loop through each day of the lesson and create a separate event for the specific day of the week
        for day in range(lesson.num_weeks * 7):
            event_date = start_date + timedelta(days=day)
            if event_date.weekday() == lesson.day_of_week:
                event = {
                    'title': lesson.name,
                    'start': event_date.strftime('%Y-%m-%d') + lesson.start_time.strftime('T%H:%M:%S'),
                    'end': event_date.strftime('%Y-%m-%d') + lesson.end_time.strftime('T%H:%M:%S'),
                }
                lesson_events.append(event)

    context = {
        'lesson_list_json': lesson_events,
    }

    return render(request, 'lessons_cal.html', context)
