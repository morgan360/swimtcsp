from django.urls import path
from . import views

app_name = "anseo"

urlpatterns = [
    path(
        "take-roll/<int:product_id>/<int:term_id>/",
        views.take_roll,
        name="take_roll"
    ),
    path(
        "attendance-history/<int:product_id>/<int:term_id>/",
        views.attendance_history,
        name="attendance_history"
    ),
    path(
        "attendance-matrix/<int:product_id>/",
        views.attendance_matrix,
        name="attendance_matrix"
    ),
]
