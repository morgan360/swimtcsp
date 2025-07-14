from django.urls import path
from . import views
app_name = "instructors"
urlpatterns = [
    path("dashboard/", views.instructor_dashboard, name="instructor_dashboard"),
    path("evaluate/<int:lesson_id>/<int:term_id>/skills/", views.evaluate_lesson_skills, name="evaluate_lesson_skills"),
]
