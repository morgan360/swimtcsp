from django.urls import path
from . import views

app_name = "finances"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("transactions-data/", views.transactions_data, name="transactions_data"),
    path("revenue/", views.revenue_report, name="revenue_report"),
    path("revenue/table/", views.revenue_report_table, name="revenue_report_table"),
    path("revenue/chart-data/", views.revenue_chart_data, name="revenue_chart_data"),
    path("revenue/export/csv/", views.revenue_export_csv, name="revenue_export_csv"),
    path("reconciliation/", views.reconciliation_dashboard, name="reconciliation"),
    path("reconciliation/table/", views.reconciliation_table, name="reconciliation_table"),
    path("reconciliation/verify/<str:order_type>/<int:order_id>/", views.reconciliation_verify, name="reconciliation_verify"),
    path("reconciliation/export/csv/", views.reconciliation_export_csv, name="reconciliation_export_csv"),
]
