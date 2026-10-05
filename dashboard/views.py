from decimal import Decimal
from datetime import date
import re

from django.http import HttpResponseBadRequest
from django.shortcuts import render


def monthly_summary(request):
    income = Decimal("5000.00")
    expense_items = [
        {"name": "Chirie", "amount": Decimal("2500.00")},
        {"name": "Utilități", "amount": Decimal("500.00")},
        {"name": "Abonamente", "amount": Decimal("200.00")},
    ]

    expenses = sum(
        (item["amount"] for item in expense_items),
        Decimal("0.00"),
    )

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
        "expense_items": expense_items,
    }

    return render(request, "dashboard/summary.html", context)