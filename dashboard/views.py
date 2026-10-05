from decimal import Decimal
from datetime import date
import re

from django.http import HttpResponseBadRequest
from django.shortcuts import render
from .services import (
    calculate_expenses,
    installment_amount_for_month,
    remaining_installments,
)
from .forms import InstallmentPreviewForm

def monthly_summary(request):
    income = Decimal("5000.00")
    expense_items = [
        {"name": "Chirie", "amount": Decimal("2500.00")},
        {"name": "Utilități", "amount": Decimal("500.00")},
        {"name": "Abonamente", "amount": Decimal("200.00")},
    ]

    expenses = calculate_expenses(expense_items)
    
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

    installment_total = installment_amount_for_month(
        monthly_amount=Decimal("200.00"),
        first_month="2026-10",
        number_of_installments=3,
        selected_month=selected_month,
    )

    installments_remaining = remaining_installments(
        first_month="2026-10",
        number_of_installments=3,
        selected_month=selected_month,
    )

    expenses = calculate_expenses(expense_items) + installment_total

    context = {
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
        "selected_month": selected_month,
        "expense_items": expense_items,
        "installment_total": installment_total,
        "installments_remaining": installments_remaining,
    }

    return render(request, "dashboard/summary.html", context)

def installment_preview(request):
    preview = None

    if request.method == "POST":
        form = InstallmentPreviewForm(data=request.POST)

        if form.is_valid():
            data = form.cleaned_data

            preview = {
                "name": data["name"],
                "selected_month": data["selected_month"],
                "amount": installment_amount_for_month(
                    monthly_amount=data["monthly_amount"],
                    first_month=data["first_month"],
                    number_of_installments=data["number_of_installments"],
                    selected_month=data["selected_month"],
                ),
                "remaining": remaining_installments(
                    first_month=data["first_month"],
                    number_of_installments=data["number_of_installments"],
                    selected_month=data["selected_month"],
                ),
            }
    else:
        form = InstallmentPreviewForm()

    return render(
        request,
        "dashboard/installment_preview.html",
        {"form": form, "preview": preview},
    )