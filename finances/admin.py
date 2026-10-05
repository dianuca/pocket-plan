from django.contrib import admin

from .models import Income


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("source", "amount", "received_on", "owner")
    list_filter = ("received_on",)
    search_fields = ("source",)