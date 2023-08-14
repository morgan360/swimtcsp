from django.http import JsonResponse
from lessons.models import Product  # Adjust the import based on your model


def get_lessons(request):
    lessons = Product.objects.all()  # Query your lessons/products
    lesson_list = []

    for lesson in lessons:
        lesson_list.append({
            'title': lesson.name,
            'start': lesson.start_datetime.isoformat(),
            'end': lesson.end_datetime.isoformat(),
        })

    return JsonResponse(lesson_list, safe=False)
