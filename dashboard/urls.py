from django.urls import path

from . import views

urlpatterns = [
    path("", views.monthly_summary, name="monthly-summary"),
    path(
        "installments/preview/",
        views.installment_preview,
        name="installment-preview",
    ),
]