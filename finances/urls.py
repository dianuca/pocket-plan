from django.urls import path

from . import views

urlpatterns = [
    path("incomes/", views.income_list, name="income-list"),
    path("incomes/<int:pk>/edit/",views.income_edit,name="income-edit",),
    path("incomes/<int:pk>/delete/",views.income_delete,name="income-delete",),
    path("expenses/", views.expense_list, name="expense-list"),
    path("expenses/<int:pk>/edit/",views.expense_edit,name="expense-edit",),
    path("expenses/<int:pk>/delete/",views.expense_delete,name="expense-delete",),
    path("installments/",views.installment_list,name="installment-list",),
    path("installments/<int:pk>/edit/",views.installment_edit,name="installment-edit",),
]