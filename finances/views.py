from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse

from dashboard.forms import MonthField

from .forms import IncomeForm
from .models import Income
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError

@login_required
def income_list(request):
    selected_month = request.GET.get(
        "month",
        date.today().strftime("%Y-%m"),
    )

    try:
        selected_month = MonthField().clean(selected_month)
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")

    if request.method == "POST":
        form = IncomeForm(data=request.POST)

        if form.is_valid():
            income = form.save(commit=False)
            income.owner = request.user
            income.save()

            month = income.received_on.strftime("%Y-%m")
            url = reverse("income-list")
            return redirect(f"{url}?month={month}")
    else:
        form = IncomeForm(initial={
            "received_on": date.fromisoformat(f"{selected_month}-01"),
        })

    year, month = map(int, selected_month.split("-"))

    incomes = Income.objects.filter(
        owner=request.user,
        received_on__year=year,
        received_on__month=month,
    ).order_by("-received_on", "-pk")

    return render(
        request,
        "finances/income_list.html",
        {
            "form": form,
            "incomes": incomes,
            "selected_month": selected_month,
        },
    )

@login_required
def income_edit(request, pk):
    income = get_object_or_404(
        Income,
        pk=pk,
        owner=request.user,
    )

    if request.method == "POST":
        form = IncomeForm(data=request.POST, instance=income)

        if form.is_valid():
            income = form.save()

            month = income.received_on.strftime("%Y-%m")
            url = reverse("income-list")
            return redirect(f"{url}?month={month}")
    else:
        form = IncomeForm(instance=income)

    return render(
        request,
        "finances/income_edit.html",
        {"form": form, "income": income},
    )

@login_required
def income_delete(request, pk):
    income = get_object_or_404(
        Income,
        pk=pk,
        owner=request.user,
    )

    month = income.received_on.strftime("%Y-%m")
    cancel_url = f"{reverse('income-list')}?month={month}"

    if request.method == "POST":
        income.delete()
        return redirect(cancel_url)

    return render(
        request,
        "finances/income_confirm_delete.html",
        {
            "income": income,
            "cancel_url": cancel_url,
        },
    )
