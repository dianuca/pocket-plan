from datetime import date
import re
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
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


