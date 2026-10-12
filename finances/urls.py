from django.urls import path

from . import views
from .savings import savings_account_edit, savings_delete, savings_edit, savings_history, savings_list

urlpatterns = [
    path("savings/", savings_list, name="savings-list"),
    path("savings/history/", savings_history, name="savings-history"),
    path("savings/initial/edit/", savings_account_edit, name="savings-account-edit"),
    path("savings/<int:pk>/edit/", savings_edit, name="savings-edit"),
    path("savings/<int:pk>/delete/", savings_delete, name="savings-delete"),
    path("incomes/", views.income_list, name="income-list"),
    path("incomes/<int:pk>/edit/",views.income_edit,name="income-edit",),
    path("incomes/<int:pk>/delete/",views.income_delete,name="income-delete",),
    path("expenses/", views.expense_list, name="expense-list"),
    path("expenses/<int:pk>/edit/",views.expense_edit,name="expense-edit",),
    path("expenses/<int:pk>/delete/",views.expense_delete,name="expense-delete",),
    path("installments/",views.installment_list,name="installment-list",),
    path("installments/<int:pk>/edit/",views.installment_edit,name="installment-edit",),
    path("installments/<int:pk>/delete/",views.installment_delete,name="installment-delete",),
]
