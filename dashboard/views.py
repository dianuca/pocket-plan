from decimal import Decimal
from datetime import date
import re

from django.http import HttpResponseBadRequest
from django.shortcuts import render


def monthly_summary(request):
    income = Decimal("5000.00")
    expenses = Decimal("3200.00")

    selected_month = request.GET.get(
        "month",
        date.today().strftime("%Y-%m"),
    )
    
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", selected_month):
        return HttpResponseBadRequest("Lună invalidă. Folosește YYYY-MM.")

    try:
        date.fromisoformat(f"{selected_month}-01")
    except ValueError:
        return HttpResponseBadRequest("Luna selectată nu există.")

    context = {
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
        "selected_month": selected_month,
    }

    return render(request, "dashboard/summary.html", context)