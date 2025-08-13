from django.urls import path
from . import views

app_name = "instructors"
urlpatterns = [
    path("dashboard/", views.instructor_dashboard, name="instructor_dashboard"),
    path("progress/<int:swimling_id>/", views.evaluate_progress, name="evaluate_progress"),
    path('category-skill-matrix/', views.category_skill_matrix, name='category_skill_matrix'),
    path('report/<int:swimling_id>/', views.generate_skill_report, name='generate_skill_report'),
    path(
        "lesson/<int:lesson_id>/<int:term_id>/",
        views.lesson_swimlings,  # <-- view below
        name="evaluate_lesson_skills",  # <-- matches template
    ),]
