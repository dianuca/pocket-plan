from django.urls import path

from . import views

urlpatterns = [
    path("incomes/", views.income_list, name="income-list"),
]