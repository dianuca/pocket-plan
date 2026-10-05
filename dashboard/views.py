from decimal import Decimal

from django.shortcuts import render


def monthly_summary(request):
    income = Decimal("5000.00")
    expenses = Decimal("3200.00")

    context = {
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
    }

    return render(request, "dashboard/summary.html", context)