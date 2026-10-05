from django.contrib import admin
from .models import Expense, Income
from .models import Income


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
