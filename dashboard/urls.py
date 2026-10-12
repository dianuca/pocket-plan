from django.urls import path

from . import views

urlpatterns = [
    path("report/pdf/", views.monthly_report_pdf, name="monthly-report-pdf"),
    path("report/", views.monthly_report, name="monthly-report"),
    path("", views.monthly_summary, name="monthly-summary"),
    path(
        "installments/preview/",
        views.installment_preview,
        name="installment-preview",
    ),
]
