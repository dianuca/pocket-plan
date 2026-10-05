from django.urls import path

from . import views

urlpatterns = [
    path("incomes/", views.income_list, name="income-list"),
    path("incomes/<int:pk>/edit/",views.income_edit,name="income-edit",),
    path("incomes/<int:pk>/delete/",views.income_delete,name="income-delete",),
]