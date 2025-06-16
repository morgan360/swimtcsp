from django.shortcuts import render

def timetable_grid(request):
    return render(request, "timetable/timetable_grid.html")