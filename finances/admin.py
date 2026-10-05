from django.contrib import admin
from .models import Expense, Income, Installment


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("source", "amount", "received_on", "owner")
    list_filter = ("received_on",)
    search_fields = ("source",)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "amount",
        "paid_on",
        "owner",
    )
    list_filter = ("category", "paid_on")
    search_fields = ("name",)

@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "monthly_amount",
        "first_due_on",
        "number_of_installments",
        "owner",
    )
    list_filter = ("first_due_on",)
    search_fields = ("name",)

