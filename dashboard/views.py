from datetime import date
import re
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.exceptions import ValidationError
from finances.models import Income, Expense, SavingsMovement
from .forms import MonthField
from django.shortcuts import render
from .services import (
    installment_amount_for_month,
    remaining_installments,
)
from .monthly import monthly_context
from .forms import InstallmentPreviewForm


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
    return render(request, "dashboard/summary.html", monthly_context(request.user, selected_month))

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




@login_required
def monthly_report(request):
    try:
        selected_month = MonthField().clean(request.GET.get("month", date.today().strftime("%Y-%m")))
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")
    return render(request, "dashboard/monthly_report.html", report_context(request.user, selected_month))


def report_context(owner, selected_month):
    year, month = map(int, selected_month.split("-"))
    context = monthly_context(owner, selected_month)
    context.update({
        "report_incomes": Income.objects.filter(owner=owner, received_on__year=year,
                                               received_on__month=month).order_by("received_on", "pk"),
        "report_expenses": Expense.objects.filter(owner=owner, paid_on__year=year,
                                                 paid_on__month=month).order_by("paid_on", "pk"),
        "report_transfers": SavingsMovement.objects.filter(owner=owner, occurred_on__year=year,
                                                           occurred_on__month=month).order_by("occurred_on", "pk"),
        "direct_expenses": context["expenses"] - context["installment_total"],
    })
    return context


@login_required
def monthly_report_pdf(request):
    from .pdf import build_monthly_report_pdf

    try:
        month = MonthField().clean(request.GET.get("month", date.today().strftime("%Y-%m")))
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")
    response = HttpResponse(build_monthly_report_pdf(report_context(request.user, month)), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pocketplan-{month}.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response

