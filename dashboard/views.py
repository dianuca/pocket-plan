from decimal import Decimal
from datetime import date
import re
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from .services import (
    calculate_expenses,
    installment_amount_for_month,
    remaining_installments,
)
from .forms import InstallmentPreviewForm
from django.db.models import Sum
from finances.models import Expense, Income, Installment


@login_required
def monthly_summary(request):
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
    year, month = map(int, selected_month.split("-"))
    income = Income.objects.filter(
        owner=request.user,
        received_on__year=year,
        received_on__month=month,
    ).aggregate(total=Sum("amount"))["total"]
    if income is None:
        income = Decimal("0.00")
    expense_items = list(
        Expense.objects.filter(
            owner=request.user,
            paid_on__year=year,
            paid_on__month=month,
        )
        .order_by("-paid_on", "-pk")
        .values("name", "amount")
    )
    installment_items = []
    installment_total = Decimal("0.00")

    installments = Installment.objects.filter(
        owner=request.user,
    ).order_by("name", "pk")

    for installment in installments:
        first_month = installment.first_due_on.strftime("%Y-%m")

        amount = installment_amount_for_month(
            monthly_amount=installment.monthly_amount,
            first_month=first_month,
            number_of_installments=installment.number_of_installments,
            selected_month=selected_month,
        )

        if amount == Decimal("0.00"):
            continue

        remaining = remaining_installments(
            first_month=first_month,
            number_of_installments=installment.number_of_installments,
            selected_month=selected_month,
        )

        installment_items.append({
            "name": installment.name,
            "amount": amount,
            "remaining": remaining,
        })
        installment_total += amount

    expenses = calculate_expenses(expense_items) + installment_total

    context = {
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
        "selected_month": selected_month,
        "expense_items": expense_items,
        "installment_items": installment_items,
        "installment_total": installment_total,
    }
    return render(request, "dashboard/summary.html", context)

@login_required
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


